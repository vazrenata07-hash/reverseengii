#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error This collector supports x86_64 only.
#endif

/* Passive observer: no ptrace attachment, signals, register writes or hooks. */
typedef unsigned long long address;
typedef struct { long nr; address arg[6], sp, ip; } sample;
typedef struct { pid_t tid; address ip, sp, caller; int valid; } last_sample;
static last_sample previous[2048];
static size_t previous_count;
static unsigned samples, syscall_reads, syscall_denied, memory_denied;
static const char *output;

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1000000000.0;
}

static pid_t find_process(const char *package) {
    DIR *dir = opendir("/proc");
    if (!dir) return -1;
    struct dirent *entry;
    pid_t found = -1;
    while ((entry = readdir(dir))) {
        char *end;
        long number = strtol(entry->d_name, &end, 10);
        if (*end || number <= 0 || number > INT32_MAX) continue;
        char path[96], command[256];
        snprintf(path, sizeof(path), "/proc/%ld/cmdline", number);
        FILE *file = fopen(path, "rb");
        if (!file) continue;
        size_t length = fread(command, 1, sizeof(command) - 1, file);
        fclose(file);
        command[length] = '\0';
        if (!strcmp(command, package)) { found = (pid_t)number; break; }
    }
    closedir(dir);
    return found;
}

static int read_syscall(pid_t tid, sample *s) {
    char path[96], line[512];
    snprintf(path, sizeof(path), "/proc/%d/syscall", tid);
    FILE *file = fopen(path, "r");
    if (!file) {
        if (errno == EACCES || errno == EPERM) ++syscall_denied;
        return 0;
    }
    char *result = fgets(line, sizeof(line), file);
    fclose(file);
    ++syscall_reads;
    if (!result) return 0;
    return sscanf(line, "%ld %llx %llx %llx %llx %llx %llx %llx %llx",
                  &s->nr, &s->arg[0], &s->arg[1], &s->arg[2], &s->arg[3],
                  &s->arg[4], &s->arg[5], &s->sp, &s->ip) == 9;
}

static ssize_t read_memory(pid_t pid, address remote, void *buffer, size_t length) {
    struct iovec local = { buffer, length };
    struct iovec source = { (void *)(uintptr_t)remote, length };
    ssize_t result = syscall(SYS_process_vm_readv, pid, &local, 1, &source, 1, 0);
    if (result < 0 && (errno == EPERM || errno == EACCES)) ++memory_denied;
    return result;
}

static address image_base(pid_t pid) {
    char path[96], line[2048];
    snprintf(path, sizeof(path), "/proc/%d/maps", pid);
    FILE *file = fopen(path, "r");
    if (!file) return 0;
    address base = 0;
    while (fgets(line, sizeof(line), file)) {
        address start, finish, offset;
        char permissions[8];
        if (strstr(line, "/libexec.so") &&
            sscanf(line, "%llx-%llx %7s %llx", &start, &finish, permissions, &offset) == 4 &&
            offset == 0 && strchr(permissions, 'x')) { base = start; break; }
    }
    fclose(file);
    return base;
}

static void copy_maps(pid_t pid) {
    char source[96], destination[1024];
    snprintf(source, sizeof(source), "/proc/%d/maps", pid);
    snprintf(destination, sizeof(destination), "%s/passive-native.maps", output);
    FILE *input = fopen(source, "r");
    if (!input) return;
    FILE *dest = fopen(destination, "w");
    if (dest) {
        char buffer[8192];
        size_t count;
        while ((count = fread(buffer, 1, sizeof(buffer), input)))
            if (fwrite(buffer, 1, count, dest) != count) break;
        fclose(dest);
    }
    fclose(input);
}

static int unchanged(pid_t tid, const sample *s, address caller) {
    last_sample *last = NULL;
    for (size_t i = 0; i < previous_count; ++i)
        if (previous[i].tid == tid) { last = &previous[i]; break; }
    if (!last) {
        if (previous_count == sizeof(previous) / sizeof(previous[0])) return 1;
        last = &previous[previous_count++];
        last->tid = tid;
    }
    int same = last->valid && last->ip == s->ip && last->sp == s->sp && last->caller == caller;
    last->valid = 1; last->ip = s->ip; last->sp = s->sp; last->caller = caller;
    return same;
}

static void inspect(pid_t pid, pid_t tid, address base) {
    sample first = {0}, after = {0};
    if (!read_syscall(tid, &first)) return;
    if (first.nr != SYS_nanosleep && first.nr != SYS_clock_nanosleep) return;
    int known_sleep = base && first.ip == base + 0x38d29;
    address stack[128];
    ssize_t bytes = read_memory(pid, first.sp, stack, sizeof(stack));
    address caller = 0;
    /* Original TV 1.15.4 x86_64: push rbx; sub rsp,0x30; nanosleep. */
    if (known_sleep && bytes >= 64) caller = stack[7];
    if (!read_syscall(tid, &after) || after.nr != first.nr ||
        after.ip != first.ip || after.sp != first.sp || after.arg[0] != first.arg[0]) return;
    if (unchanged(tid, &first, caller)) return;
    ++samples;
    printf("passive_sample at=%.6f sample=%u tid=%d nr=%ld user_ip=0x%llx user_sp=0x%llx "
           "image_base=0x%llx known_native_sleep=%d stack_read=%zd\n",
           now(), samples, tid, first.nr, first.ip, first.sp, base, known_sleep, bytes);
    struct { int64_t sec, nsec; } request;
    address request_address = first.arg[first.nr == SYS_nanosleep ? 0 : 2];
    if (read_memory(pid, request_address, &request, sizeof(request)) == sizeof(request))
        printf("sleep_request tid=%d sec=%lld nsec=%lld\n", tid,
               (long long)request.sec, (long long)request.nsec);
    if (known_sleep && caller) {
        unsigned char instruction[5];
        int verified = 0;
        if (caller >= 5 && read_memory(pid, caller - 5, instruction, 5) == 5 && instruction[0] == 0xe8) {
            int32_t displacement;
            memcpy(&displacement, instruction + 1, sizeof(displacement));
            verified = caller + (int64_t)displacement == base + 0x38ce0;
        }
        printf("native_sleep_caller tid=%d return_ip=0x%llx elf_offset=0x%llx verified_direct_call=%d\n",
               tid, caller, caller >= base ? caller - base : 0, verified);
    }
    /* Emit only values pointing into the loader's code, never raw stack data. */
    if (base && bytes > 0) {
        unsigned count = 0;
        for (size_t i = 0; i < (size_t)bytes / sizeof(stack[0]) && count < 16; ++i) {
            if (stack[i] >= base + 0x37fd0 && stack[i] < base + 0xdd9f0) {
                printf("code_pointer_candidate tid=%d stack_offset=0x%zx elf_offset=0x%llx\n",
                       tid, i * sizeof(stack[0]), stack[i] - base);
                ++count;
            }
        }
    }
    copy_maps(pid);
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != 4) return 2;
    char *end;
    long duration = strtol(argv[3], &end, 10);
    if (*end || duration < 5 || duration > 30) return 2;
    output = argv[2];
    printf("native_collector=v2 mode=passive_proc_and_readv uid=%d\n", getuid());
    double deadline = now() + duration;
    pid_t pid = -1;
    while (now() < deadline && (pid = find_process(argv[1])) <= 0) usleep(1000);
    if (pid <= 0) { puts("error=target_not_found"); return 3; }
    printf("target_pid=%d\n", pid);
    char path[96];
    snprintf(path, sizeof(path), "/proc/%d/task", pid);
    address base = 0;
    while (now() < deadline) {
        DIR *tasks = opendir(path);
        if (!tasks) { printf("target_gone errno=%d at=%.6f\n", errno, now()); break; }
        if (!base) base = image_base(pid);
        struct dirent *task;
        while ((task = readdir(tasks))) {
            char *tail;
            long number = strtol(task->d_name, &tail, 10);
            if (!*tail && number > 0 && number <= INT32_MAX) inspect(pid, (pid_t)number, base);
        }
        closedir(tasks);
        usleep(5000);
    }
    printf("passive_samples=%u syscall_reads=%u syscall_permission_denied=%u memory_permission_denied=%u\n",
           samples, syscall_reads, syscall_denied, memory_denied);
    return 0;
}
