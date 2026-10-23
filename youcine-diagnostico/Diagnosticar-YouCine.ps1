param(
    [string]$Adb = 'C:\Program Files\Microvirt\MEmu\adb.exe',
    [string]$Serial = '127.0.0.1:21503',
    [ValidateRange(5, 30)][int]$Seconds = 12
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Adb)) { throw "ADB nao encontrado: $Adb" }
if ($Serial -notmatch '^[A-Za-z0-9_.:-]+$') { throw 'Serial ADB invalido.' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$desktop = [Environment]::GetFolderPath('Desktop')
$outDir = Join-Path $desktop "youcine-diagnostico-$stamp"
$null = New-Item -ItemType Directory -Path $outDir
$remoteDir = "/data/local/tmp/ycdiag-$stamp"
$remoteScript = "/data/local/tmp/ycdiag-$stamp.sh"
$collectorPath = Join-Path $outDir 'collector.sh'

function Invoke-AdbChecked {
    param([string[]]$Arguments)
    & $Adb -s $Serial @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ADB falhou: $($Arguments -join ' ')" }
}

# No APK is installed or modified. Kernel tracing uses a dedicated instance.
$collector = @'
#!/system/bin/sh
OUT="$1"
DURATION="$2"
PKG=com.world.youcinetv
ACT=com.interactive.brasiliptv.ui.activity.WelcomeActivity
umask 022
mkdir -p "$OUT/maps"
REPORT="$OUT/environment.txt"
TRACE_INSTANCE=
TRACE_BASE=
PROBE_GROUP=
LOGPID=
FINISHED=0

finish() {
    [ "$FINISHED" = 1 ] && return
    FINISHED=1
    if [ -n "$TRACE_INSTANCE" ]; then
        echo 0 > "$TRACE_INSTANCE/tracing_on" 2>/dev/null
        cat "$TRACE_INSTANCE/trace" > "$OUT/kernel-trace.txt" 2>/dev/null
        for e in syscalls/sys_enter_kill syscalls/sys_enter_tgkill signal/signal_generate; do
            [ -e "$TRACE_INSTANCE/events/$e/enable" ] && echo 0 > "$TRACE_INSTANCE/events/$e/enable" 2>/dev/null
        done
        if [ -n "$PROBE_GROUP" ]; then
            echo 0 > "$TRACE_INSTANCE/events/$PROBE_GROUP/kill_user/enable" 2>/dev/null
        fi
        rmdir "$TRACE_INSTANCE" 2>/dev/null
    fi
    if [ -n "$PROBE_GROUP" ]; then
        if (echo "-:$PROBE_GROUP/kill_user" >> "$TRACE_BASE/kprobe_events") 2>> "$OUT/native-probe-errors.txt"; then
            echo 'native_ip_probe_removed=true' >> "$REPORT"
        else
            echo 'native_ip_probe_removed=false' >> "$REPORT"
        fi
    fi
    [ -n "$LOGPID" ] && kill "$LOGPID" 2>/dev/null
    am force-stop "$PKG" > "$OUT/stop.txt" 2>&1
    if [ "$(id -u)" = 0 ]; then
        dmesg 2>/dev/null | grep -iE 'youcine|lowmemory|out of memory|sigkill|houdini|seccomp|avc:.*denied' | tail -n 150 > "$OUT/kernel-messages.txt"
    fi
    chmod -R a+rX "$OUT" 2>/dev/null
    echo "Coleta concluida: $OUT"
}
trap finish EXIT
trap 'exit 130' INT TERM

{
    echo 'collector_version=2-native-ip'
    date
    id
    uname -a
    for p in ro.build.version.release ro.build.version.sdk ro.product.cpu.abilist ro.product.cpu.abilist32 ro.product.cpu.abilist64 ro.dalvik.vm.native.bridge ro.enable.native.bridge.exec ro.enable.native.bridge.exec64 ro.product.model; do
        echo "$p=$(getprop "$p")"
    done
    echo "selinux=$(getenforce 2>/dev/null)"
    echo '--- installed APK ---'
    pm path "$PKG"
    for apk in $(pm path "$PKG" | sed 's/^package://'); do
        sha256sum "$apk" 2>/dev/null
    done
    dumpsys package "$PKG" | grep -E 'versionCode=|versionName=|primaryCpuAbi=|secondaryCpuAbi=|codePath=|userId=' | head -n 15
} > "$REPORT" 2>&1

if [ "$(id -u)" = 0 ]; then
    for base in /sys/kernel/tracing /sys/kernel/debug/tracing; do
        if [ -d "$base/instances" ]; then
            instance="$base/instances/ycdiag_$$"
            if mkdir "$instance" 2>/dev/null; then
                TRACE_INSTANCE="$instance"
                TRACE_BASE="$base"
                break
            fi
        fi
    done
fi

if [ -n "$TRACE_INSTANCE" ]; then
    echo 'trace_instance=available' >> "$REPORT"
    echo 0 > "$TRACE_INSTANCE/tracing_on" 2>/dev/null
    echo 256 > "$TRACE_INSTANCE/buffer_size_kb" 2>/dev/null
    echo > "$TRACE_INSTANCE/trace" 2>/dev/null
    if [ -e "$TRACE_INSTANCE/options/userstacktrace" ]; then
        echo 1 > "$TRACE_INSTANCE/options/userstacktrace" 2>/dev/null
        echo "userstacktrace=$(cat "$TRACE_INSTANCE/options/userstacktrace")" >> "$REPORT"
    else
        echo 'userstacktrace=unavailable' >> "$REPORT"
    fi
    if [ -e "$TRACE_INSTANCE/options/sym-userobj" ]; then
        echo 1 > "$TRACE_INSTANCE/options/sym-userobj" 2>/dev/null
    fi
    for e in syscalls/sys_enter_kill syscalls/sys_enter_tgkill signal/signal_generate; do
        event="$TRACE_INSTANCE/events/$e"
        if [ -e "$event/enable" ]; then
            if grep -q 'field:.* sig;' "$event/format"; then
                echo 'sig == 9 || sig == 6' > "$event/filter" 2>/dev/null
            fi
            echo 1 > "$event/enable" 2>/dev/null
            echo "event=$e enabled=$(cat "$event/enable")" >> "$REPORT"
            echo "--- $e ---" >> "$OUT/event-formats.txt"
            cat "$event/format" >> "$OUT/event-formats.txt"
        else
            echo "event=$e unavailable" >> "$REPORT"
        fi
    done

    # x86_64 Linux 4.19 syscall wrappers receive struct pt_regs * in %di.
    # pt_regs: si=104, di=112, ip=128, sp=152. The saved user IP points
    # immediately after the syscall instruction, even with no unwind data.
    # This observes syscall entry without attaching a debugger or tracing ptrace.
    if [ "$(uname -m)" = x86_64 ] && [ -w "$TRACE_BASE/kprobe_events" ]; then
        group="ycdiag_$$"
        definition="p:$group/kill_user __x64_sys_kill user_ip=+128(%di):x64 user_sp=+152(%di):x64 target=+112(%di):s64 sig=+104(%di):u32"
        if (echo "$definition" >> "$TRACE_BASE/kprobe_events") 2>> "$OUT/native-probe-errors.txt"; then
            PROBE_GROUP="$group"
            event="$TRACE_INSTANCE/events/$PROBE_GROUP/kill_user"
            if (echo 'sig == 9 || sig == 6' > "$event/filter" && echo 1 > "$event/enable") 2>> "$OUT/native-probe-errors.txt"; then
                echo "native_ip_probe=enabled symbol=__x64_sys_kill event=$PROBE_GROUP/kill_user" >> "$REPORT"
                echo '--- native kill caller ---' >> "$OUT/event-formats.txt"
                cat "$event/format" >> "$OUT/event-formats.txt"
            else
                echo 'native_ip_probe=enable_failed' >> "$REPORT"
            fi
        else
            echo 'native_ip_probe=registration_failed' >> "$REPORT"
        fi
    else
        echo 'native_ip_probe=unavailable (requires x86_64 and writable kprobe_events)' >> "$REPORT"
    fi
    echo 1 > "$TRACE_INSTANCE/tracing_on" 2>/dev/null
else
    echo 'trace_instance=unavailable' >> "$REPORT"
    echo 'Exact native caller requires root and kernel tracing support; logcat alone cannot establish it.' >> "$REPORT"
fi

# Start after existing logs without erasing any log buffer.
logcat -b all -v threadtime -T 1 YCLean:V AndroidRuntime:V libc:V DEBUG:V linker:V ActivityManager:I Zygote:I '*:S' > "$OUT/logcat.txt" 2>&1 &
LOGPID=$!
am force-stop "$PKG" > "$OUT/start.txt" 2>&1
am start -n "$PKG/$ACT" >> "$OUT/start.txt" 2>&1
END=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$END" ]; do
    for pid in $(pidof "$PKG" 2>/dev/null); do
        case "$pid" in ''|*[!0-9]*) continue ;; esac
        tmp="$OUT/maps/$pid.tmp"
        if cat "/proc/$pid/maps" > "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
            mv "$tmp" "$OUT/maps/$pid.maps"
        else
            rm -f "$tmp"
        fi
        if [ ! -f "$OUT/maps/$pid.status" ]; then
            grep -E '^(Name|State|Tgid|Pid|PPid|TracerPid|Uid):' "/proc/$pid/status" > "$OUT/maps/$pid.status" 2>/dev/null
        fi
    done
    sleep 0.02
done
exit 0
'@

[IO.File]::WriteAllText($collectorPath, ($collector -replace "`r`n", "`n"), [Text.UTF8Encoding]::new($false))

Write-Host 'Conectando ao MEmu...'
& $Adb connect $Serial
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel conectar ao MEmu.' }
Invoke-AdbChecked -Arguments @('get-state')
Invoke-AdbChecked -Arguments @('push', $collectorPath, $remoteScript)

$rootMode = 'none'
$probePreference = $ErrorActionPreference
try {
    # A missing su binary is a probe result, not a fatal collection error.
    $ErrorActionPreference = 'Continue'
    $identity = (& $Adb -s $Serial shell id 2>&1 | Out-String)
    if ($identity -match 'uid=0\(') {
        $rootMode = 'adb'
    } else {
        $identity = (& $Adb -s $Serial shell 'su -c id' 2>&1 | Out-String)
        if ($identity -match 'uid=0\(') {
            $rootMode = 'su-c'
        } else {
            $identity = (& $Adb -s $Serial shell 'su 0 id' 2>&1 | Out-String)
            if ($identity -match 'uid=0\(') { $rootMode = 'su-0' }
        }
    }
} finally {
    $ErrorActionPreference = $probePreference
}

Write-Host "Acesso root: $rootMode"
Write-Host "Abrindo o aplicativo e coletando por aproximadamente $Seconds segundos..."
Write-Host 'Coletor v2: tenta capturar o endereco de usuario da syscall kill no kernel x86_64.'
Write-Host 'O aplicativo sera encerrado ao final para parar o ciclo de reinicios.'
$command = "sh $remoteScript $remoteDir $Seconds"
if ($rootMode -eq 'su-c') { $command = "su -c '$command'" }
if ($rootMode -eq 'su-0') { $command = "su 0 $command" }
Invoke-AdbChecked -Arguments @('shell', $command)

$deviceDir = Join-Path $outDir 'device'
Invoke-AdbChecked -Arguments @('pull', $remoteDir, $deviceDir)

$summary = [Collections.Generic.List[string]]::new()
$summary.Add("Root mode: $rootMode")
$environment = Get-ChildItem -Path $outDir -Recurse -Filter 'environment.txt' | Select-Object -First 1
if ($environment) {
    $summary.Add('--- Environment ---')
    $summary.Add((Get-Content -LiteralPath $environment.FullName -Raw))
}
$log = Get-ChildItem -Path $outDir -Recurse -Filter 'logcat.txt' | Select-Object -First 1
if ($log) {
    $content = Get-Content -LiteralPath $log.FullName -Raw
    $summary.Add('Application process deaths: ' + [regex]::Matches($content, 'Process com\.world\.youcinetv \(pid \d+\) has died').Count)
    $summary.Add('--- Unique initializer messages ---')
    Get-Content -LiteralPath $log.FullName | Where-Object { $_ -match 'YCLean\s*:' } |
        ForEach-Object { $_ -replace '^.*YCLean\s*:\s*', '' } |
        Group-Object | ForEach-Object { $summary.Add("$($_.Count) x $($_.Name)") }
}
$trace = Get-ChildItem -Path $outDir -Recurse -Filter 'kernel-trace.txt' | Select-Object -First 1
if ($trace) {
    $summary.Add('--- First native termination events and stack addresses ---')
    $hits = Select-String -LiteralPath $trace.FullName -Pattern 'kill_user|user_ip=|sys_enter_kill|sys_enter_tgkill|sys_kill|sys_tgkill|signal_generate|kill:|tgkill:|user_stack|=>|<-User' |
        Select-Object -First 120
    foreach ($hit in $hits) { $summary.Add($hit.Line) }
    $summary.Add('The complete kernel trace and process maps are included. Event addresses do not by themselves prove the reason for termination.')
} else {
    $summary.Add('Kernel trace unavailable. To locate the caller, root and ftrace support are needed; no native cause is inferred from logcat alone.')
}
$summaryPath = Join-Path $outDir 'RESUMO.txt'
[IO.File]::WriteAllLines($summaryPath, $summary, [Text.UTF8Encoding]::new($false))
$zipPath = "$outDir.zip"
Compress-Archive -Path (Join-Path $outDir '*') -DestinationPath $zipPath
Write-Host "`nArquivo para enviar: $zipPath"
Write-Host "Resumo: $summaryPath"
if ($rootMode -eq 'none') {
    Write-Host 'Para a captura nativa, ative root nas configuracoes do MEmu e execute novamente.'
}
