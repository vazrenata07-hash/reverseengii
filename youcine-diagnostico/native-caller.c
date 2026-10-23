#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error This collector supports x86_64 only.
#endif

/* Observes syscalls; never changes registers, code, return values or signals. */
static volatile sig_atomic_t stopping;
static pid_t tids[2048];
static size_t tid_count;
static const char *output_dir;
static unsigned capture_count;

static void stop_requested(int sig) { (void)sig; stopping = 1; }

static double seconds_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + ts.tv_nsec / 1000000000.0;
}

static int tracked(pid_t tid) {
    for (size_t i = 0; i < tid_count; ++i) if (tids[i] == tid) return 1;
    return 0;
}

static void remember(pid_t tid) {
    if (tracked(tid)) return;
    if (tid_count < sizeof(tids) / sizeof(tids[0])) tids[tid_count++] = tid;
    else { puts("error=thread_capacity_exceeded"); stopping = 1; }
}

static void forget(pid_t tid) {
    for (size_t i = 0; i < tid_count; ++i) {
        if (tids[i] == tid) { tids[i] = tids[--tid_count]; return; }
    }
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

static int attach_thread(pid_t tid) {
    if (tracked(tid)) return 0;
    long options = PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACECLONE;
    if (ptrace(PTRACE_SEIZE, tid, 0, (void *)(uintptr_t)options) == -1) {
        printf("seize_failed tid=%d errno=%d message=%s\n", tid, errno, strerror(errno));
        return -1;
    }
    remember(tid);
    printf("attached tid=%d\n", tid);
    if (ptrace(PTRACE_INTERRUPT, tid, 0, 0) == -1)
        printf("interrupt_failed tid=%d errno=%d\n", tid, errno);
    return 0;
}

static void copy_maps(pid_t tid) {
    char source[96], destination[1024];
    snprintf(source, sizeof(source), "/proc/%d/maps", tid);
    snprintf(destination, sizeof(destination), "%s/native-%u-tid-%d.maps",
             output_dir, capture_count, tid);
    FILE *input = fopen(source, "rb");
    FILE *output = input ? fopen(destination, "wb") : NULL;
    if (!input || !output) {
        printf("maps_failed tid=%d errno=%d\n", tid, errno);
    } else {
        char buffer[8192];
        size_t count;
        while ((count = fread(buffer, 1, sizeof(buffer), input)))
            if (fwrite(buffer, 1, count, output) != count) break;
        printf("maps=%s\n", destination);
    }
    if (input) fclose(input);
    if (output) fclose(output);
}

static void capture(pid_t tid, const struct user_regs_struct *r, const char *name) {
    ++capture_count;
    printf("native_caller capture=%u tid=%d syscall=%s nr=%llu "
           "arg0=%llu arg1=%llu arg2=%llu user_ip=0x%llx user_sp=0x%llx\n",
           capture_count, tid, name, r->orig_rax, r->rdi, r->rsi, r->rdx, r->rip, r->rsp);
    printf("registers rax=0x%llx rbx=0x%llx rbp=0x%llx rcx=0x%llx "
           "r12=0x%llx r13=0x%llx r14=0x%llx r15=0x%llx\n",
           r->rax, r->rbx, r->rbp, r->rcx, r->r12, r->r13, r->r14, r->r15);
    /* Save only nearby instructions, no application data or stack contents. */
    unsigned long long start = r->rip >= 16 ? r->rip - 16 : r->rip;
    printf("code address=0x%llx bytes=", start);
    for (unsigned i = 0; i < 32; i += sizeof(long)) {
        errno = 0;
        long word = ptrace(PTRACE_PEEKTEXT, tid, (void *)(uintptr_t)(start + i), 0);
        if (word == -1 && errno) { printf("[unreadable:%d]", errno); break; }
        unsigned char bytes[sizeof(long)];
        memcpy(bytes, &word, sizeof(word));
        for (size_t j = 0; j < sizeof(bytes); ++j) printf("%02x", bytes[j]);
    }
    putchar('\n');
    copy_maps(tid);
}

static void inspect_syscall(pid_t tid) {
    struct user_regs_struct r;
    if (ptrace(PTRACE_GETREGS, tid, 0, &r) == -1) return;
    /* Linux x86_64 sets RAX to -ENOSYS at syscall-entry stops. */
    if ((long long)r.rax != -ENOSYS) return;
    if (r.orig_rax == SYS_kill) capture(tid, &r, "kill");
    else if (r.orig_rax == SYS_tkill) capture(tid, &r, "tkill");
    else if (r.orig_rax == SYS_tgkill) capture(tid, &r, "tgkill");
    else if (r.orig_rax == SYS_exit_group) capture(tid, &r, "exit_group");
}

static void detach_all(void) {
    for (size_t i = 0; i < tid_count; ++i) ptrace(PTRACE_INTERRUPT, tids[i], 0, 0);
    double deadline = seconds_now() + 1.0;
    while (tid_count && seconds_now() < deadline) {
        int status;
        pid_t tid = waitpid(-1, &status, __WALL | WNOHANG);
        if (tid <= 0) { if (tid < 0 && errno == ECHILD) break; usleep(1000); continue; }
        if (WIFSTOPPED(status)) {
            unsigned event = (unsigned)status >> 16;
            int sig = WSTOPSIG(status);
            if (event || sig == (SIGTRAP | 0x80)) sig = 0;
            if (ptrace(PTRACE_DETACH, tid, 0, (void *)(intptr_t)sig) == -1)
                printf("detach_failed tid=%d errno=%d\n", tid, errno);
        }
        forget(tid);
    }
    printf("cleanup_remaining=%zu (no EXITKILL option is used)\n", tid_count);
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != 4) { fprintf(stderr, "Usage: %s package output_directory seconds\n", argv[0]); return 2; }
    char *end;
    long duration = strtol(argv[3], &end, 10);
    if (*end || duration < 5 || duration > 30) return 2;
    output_dir = argv[2];
    signal(SIGINT, stop_requested);
    signal(SIGTERM, stop_requested);
    printf("native_collector=v1 arch=x86_64 uid=%d mode=ptrace_observe\n", getuid());
    double deadline = seconds_now() + duration;
    pid_t main_pid = -1;
    while (!stopping && seconds_now() < deadline) {
        main_pid = find_process(argv[1]);
        if (main_pid > 0) break;
        usleep(1000);
    }
    if (main_pid <= 0) { puts("error=target_not_found"); return 3; }
    printf("target_pid=%d\n", main_pid);
    if (attach_thread(main_pid) != 0) return 4;
    char task_path[96];
    snprintf(task_path, sizeof(task_path), "/proc/%d/task", main_pid);
    DIR *tasks = opendir(task_path);
    if (tasks) {
        struct dirent *task;
        while ((task = readdir(tasks))) {
            char *tail;
            long number = strtol(task->d_name, &tail, 10);
            if (!*tail && number > 0 && number <= INT32_MAX) attach_thread((pid_t)number);
        }
        closedir(tasks);
    }
    while (!stopping && tid_count && seconds_now() < deadline) {
        int status;
        pid_t tid = waitpid(-1, &status, __WALL | WNOHANG);
        if (tid < 0) { if (errno == EINTR) continue; printf("wait_failed errno=%d\n", errno); break; }
        if (tid == 0) { usleep(100); continue; }
        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            printf("thread_ended tid=%d exit=%d signal=%d\n", tid,
                   WIFEXITED(status) ? WEXITSTATUS(status) : -1,
                   WIFSIGNALED(status) ? WTERMSIG(status) : 0);
            forget(tid);
            continue;
        }
        if (!WIFSTOPPED(status)) continue;
        remember(tid);
        unsigned event = (unsigned)status >> 16;
        int sig = WSTOPSIG(status);
        if (event == PTRACE_EVENT_CLONE) {
            unsigned long child = 0;
            if (ptrace(PTRACE_GETEVENTMSG, tid, 0, &child) == 0 && child) remember((pid_t)child);
        }
        if (sig == (SIGTRAP | 0x80)) { inspect_syscall(tid); sig = 0; }
        else if (event) sig = 0;
        else printf("signal_stop tid=%d signal=%d\n", tid, sig);
        /* Deliver genuine signals unchanged and execute the original syscall. */
        if (ptrace(PTRACE_SYSCALL, tid, 0, (void *)(intptr_t)sig) == -1 && errno != ESRCH)
            printf("resume_failed tid=%d errno=%d\n", tid, errno);
    }
    detach_all();
    printf("native_capture_count=%u\n", capture_count);
    return 0;
}
