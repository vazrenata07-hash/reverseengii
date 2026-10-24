# Windows PowerShell 5.1. One launch of the currently installed APK.
param(
    [string]$Adb = '',
    [string]$Serial = '127.0.0.1:21503',
    [ValidateRange(10, 60)][int]$Seconds = 25
)
$ErrorActionPreference = 'Stop'
$utf8 = [Text.UTF8Encoding]::new($false)
$stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6)
$desktop = [Environment]::GetFolderPath('Desktop')
$outDir = Join-Path $desktop "youcine-mod-crash-$stamp"
$null = New-Item -ItemType Directory -Path $outDir
$remoteDir = "/data/local/tmp/ycmoddiag-$stamp"
$remoteScript = "$remoteDir.sh"
$running = $null
$failure = ''

function Save-Text([string]$Path, [string]$Text) {
    [IO.File]::WriteAllText($Path, $Text, $script:utf8)
}
function Quote-Native([string]$Value) {
    # Windows CommandLineToArgvW escaping, including trailing backslashes.
    return '"' + ([regex]::Replace($Value, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}
function Run-Adb {
    param([string[]]$Arguments, [string]$Name, [int]$Timeout = 15, [switch]$Global)
    $argv = @()
    if (-not $Global) { $argv += @('-s', $Serial) }
    $argv += $Arguments
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $script:AdbPath
    $info.Arguments = ($argv | ForEach-Object { Quote-Native $_ }) -join ' '
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    $script:running = $process
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $timedOut = -not $process.WaitForExit($Timeout * 1000)
        if ($timedOut) { try { $process.Kill() } catch {} }
        $null = $process.WaitForExit(3000)
        $text = ''
        if ($stdout.Wait(3000)) { $text += $stdout.Result }
        if ($stderr.Wait(3000)) { $text += "`r`nSTDERR:`r`n" + $stderr.Result }
        $code = -1
        if ($process.HasExited) { $code = $process.ExitCode }
        if ($timedOut) { $code = 124; $text += "`r`nCommand timed out after $Timeout seconds." }
        if ($Name) { Save-Text (Join-Path $outDir $Name) ("exit_code=$code`r`n" + $text) }
        return [pscustomobject]@{ Code = $code; Text = $text }
    } finally {
        if (-not $process.HasExited) { try { $process.Kill() } catch {} }
        $process.Dispose()
        $script:running = $null
    }
}

$collector = @'
#!/system/bin/sh
OUT="$1"
DURATION="$2"
PKG=com.world.youcinetv
mkdir -p "$OUT/processes" "$OUT/tombstones"
LOGPID=
LAUNCHPID=
DONE=0
finish() {
    [ "$DONE" = 1 ] && return
    DONE=1
    if [ -n "$LAUNCHPID" ] && [ ! -f "$OUT/launch-exit.txt" ]; then
        kill "$LAUNCHPID" 2>/dev/null
    fi
    [ -n "$LOGPID" ] && kill "$LOGPID" 2>/dev/null
    chmod -R a+rX "$OUT" 2>/dev/null
}
trap finish EXIT
trap 'exit 130' INT TERM
snapshot() {
    proc="$1"
    label="$2"
    dest="$OUT/processes/$proc"
    mkdir -p "$dest"
    cat "/proc/$proc/maps" > "$dest/maps-$label.txt" 2>&1
    {
        date
        cat /proc/uptime
        cat "/proc/$proc/status"
        echo '--- executable ---'
        readlink "/proc/$proc/exe"
        echo '--- command ---'
        tr '\000' ' ' < "/proc/$proc/cmdline"
        echo
        echo '--- wait and syscall ---'
        cat "/proc/$proc/wchan" "/proc/$proc/syscall"
    } > "$dest/state-$label.txt" 2>&1
}
{
    echo 'collector=original-mod-crash-v1'
    echo "duration_seconds=$DURATION"
    date
    id
    uname -a
    getenforce
    for prop in ro.build.version.release ro.build.version.sdk ro.build.fingerprint ro.product.model ro.product.cpu.abilist ro.product.cpu.abilist32 ro.product.cpu.abilist64 ro.dalvik.vm.native.bridge ro.enable.native.bridge.exec ro.enable.native.bridge.exec64; do
        echo "$prop=$(getprop "$prop")"
    done
    echo '--- APK SHA256 ---'
    pm path "$PKG"
    for apk in $(pm path "$PKG" | sed 's/^package://'); do sha256sum "$apk"; done
    echo '--- native translation libraries ---'
    ls -l /system/lib/libart.so /system/lib64/libart.so /system/lib/libnb.so /system/lib64/libnb.so /system/lib/libhoudini.so /system/lib64/libhoudini.so
} > "$OUT/environment.txt" 2>&1
dumpsys package "$PKG" > "$OUT/package.txt" 2>&1
ps -A > "$OUT/processes-before.txt" 2>&1
logcat -b crash -d -v threadtime > "$OUT/crash-before.txt" 2>&1
for file in /data/tombstones/tombstone_*; do
    [ -f "$file" ] && stat -c '%n %Y %s' "$file"
done > "$OUT/tombstones-before.txt" 2>&1

COMPONENT=
for category in android.intent.category.LEANBACK_LAUNCHER android.intent.category.LAUNCHER; do
    cmd package resolve-activity --brief -a android.intent.action.MAIN -c "$category" "$PKG" >> "$OUT/resolve-activity.txt" 2>&1
done
COMPONENT=$(sed -n '/^com\.world\.youcinetv\//p' "$OUT/resolve-activity.txt" | head -n 1 | tr -d '\r')
if [ -z "$COMPONENT" ]; then
    echo 'No launcher activity resolved; no app was launched.' > "$OUT/launch.txt"
    exit 3
fi

# All tags and buffers are captured: the third-party loader has no YCLean tags.
# Do not erase existing log buffers, app data or runtime-generated files.
logcat -b all -v threadtime -T 1 '*:V' > "$OUT/logcat-live.txt" 2>&1 &
LOGPID=$!
sleep 1
log -p i -t YCModDiag "BEGIN $OUT"
am force-stop "$PKG" > "$OUT/force-stop-before.txt" 2>&1
( am start -W -n "$COMPONENT" > "$OUT/launch.txt" 2>&1; echo "$?" > "$OUT/launch-exit.txt" ) &
LAUNCHPID=$!
END=$(( $(date +%s) + DURATION ))
TICK=0
SEEN=' '
while [ "$(date +%s)" -lt "$END" ]; do
    PIDS=$(pidof "$PKG" 2>/dev/null)
    echo "$(cat /proc/uptime) pids=$PIDS" >> "$OUT/process-timeline.txt"
    for proc in $PIDS; do
        case "$SEEN" in
            *" $proc "*) ;;
            *) snapshot "$proc" first; SEEN="$SEEN$proc ";;
        esac
        if [ "$TICK" = 4 ] || [ "$TICK" = 16 ] || [ "$TICK" = 40 ]; then
            snapshot "$proc" "tick-$TICK"
        fi
    done
    TICK=$(( TICK + 1 ))
    sleep 0.10
done
for proc in $(pidof "$PKG" 2>/dev/null); do snapshot "$proc" final; done
log -p i -t YCModDiag "END $OUT"
sleep 1
kill "$LOGPID" 2>/dev/null
wait "$LOGPID" 2>/dev/null
LOGPID=
logcat -b crash -d -v threadtime > "$OUT/crash-after.txt" 2>&1
ps -A > "$OUT/processes-after.txt" 2>&1
for file in /data/tombstones/tombstone_*; do
    [ -f "$file" ] || continue
    line=$(stat -c '%n %Y %s' "$file" 2>/dev/null)
    echo "$line" >> "$OUT/tombstones-after.txt"
    if ! grep -Fxq "$line" "$OUT/tombstones-before.txt"; then
        # Keep new/changed dumps belonging to this app only.
        if head -n 100 "$file" | grep -Fq "$PKG"; then
            cp "$file" "$OUT/tombstones/" 2>> "$OUT/collection-errors.txt"
        fi
    fi
done
dumpsys activity activities > "$OUT/activities.txt" 2>&1
dumpsys activity processes > "$OUT/activity-processes.txt" 2>&1
dumpsys meminfo "$PKG" > "$OUT/meminfo.txt" 2>&1
dumpsys dropbox > "$OUT/dropbox-index.txt" 2>&1
dmesg | tail -n 700 > "$OUT/kernel-last.txt" 2>&1
echo 'Collection finished. App data and installed APK were not modified.'
'@

try {
    if ($Serial -notmatch '^[A-Za-z0-9_.:-]+$') { throw 'Serial ADB invalido.' }
    $candidates = @()
    if ($Adb) { $candidates += $Adb } else {
        $candidates += @((Join-Path (Get-Location).Path 'adb.exe'), (Join-Path $PSScriptRoot 'adb.exe'), 'C:\Program Files\Microvirt\MEmu\adb.exe', 'C:\Program Files (x86)\Microvirt\MEmu\adb.exe')
        $command = Get-Command adb.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $script:AdbPath = ''
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $script:AdbPath = (Resolve-Path -LiteralPath $candidate).Path; break }
    }
    if (-not $script:AdbPath) { throw 'ADB nao encontrado. Rode na pasta do MEmu ou informe -Adb.' }
    Save-Text (Join-Path $outDir 'collector-info.txt') "collector=original-mod-crash-v1`r`nserial=$Serial`r`nadb=$script:AdbPath`r`nseconds=$Seconds`r`n"
    $null = Run-Adb -Arguments @('version') -Name 'adb-version.txt' -Global
    if ($Serial -match ':') { $null = Run-Adb -Arguments @('connect', $Serial) -Name 'connect.txt' -Global }
    $state = Run-Adb -Arguments @('get-state') -Name 'device-state.txt'
    if ($state.Code -ne 0 -or $state.Text -notmatch '(?m)^device\s*$') { throw 'MEmu indisponivel. Confira se a instancia esta ligada e se a porta e 21503.' }
    $installed = Run-Adb -Arguments @('shell', 'pm path com.world.youcinetv') -Name 'installed-apk.txt'
    if ($installed.Text -notmatch 'package:') { throw 'O app com.world.youcinetv nao esta instalado nesta instancia.' }
    $identity = Run-Adb -Arguments @('shell', 'id') -Name 'shell-access.txt'
    $rootMode = 'shell'
    if ($identity.Text -notmatch 'uid=0\(') {
        foreach ($probe in @('su -c id', 'su 0 id')) {
            $result = Run-Adb -Arguments @('shell', $probe) -Timeout 4
            if ($result.Text -match 'uid=0\(') {
                if ($probe -eq 'su -c id') { $rootMode = 'su-c' } else { $rootMode = 'su-0' }
                break
            }
        }
    }
    Save-Text (Join-Path $outDir 'root-mode.txt') $rootMode
    $collectorPath = Join-Path $outDir 'collector.sh'
    Save-Text $collectorPath ($collector -replace "`r`n", "`n")
    $push = Run-Adb -Arguments @('push', $collectorPath, $remoteScript) -Name 'push.txt'
    if ($push.Code -ne 0) { throw 'Nao foi possivel enviar o coletor ao MEmu.' }
    $shellCommand = "sh $remoteScript $remoteDir $Seconds"
    if ($rootMode -eq 'su-c') { $shellCommand = "su -c '$shellCommand'" }
    if ($rootMode -eq 'su-0') { $shellCommand = "su 0 $shellCommand" }
    Write-Host "O app sera aberto uma vez. Aguarde $Seconds segundos sem fechar esta janela."
    $collected = Run-Adb -Arguments @('shell', $shellCommand) -Name 'collection.txt' -Timeout ($Seconds + 55)
    if ($collected.Code -ne 0) { $failure = 'Coleta parcial. Veja collection.txt.' }
    $pulled = Run-Adb -Arguments @('pull', $remoteDir, (Join-Path $outDir 'device')) -Name 'pull.txt' -Timeout 35
    if ($pulled.Code -ne 0) { $failure += ' Falha ao copiar parte da coleta; veja pull.txt.' }
    # ART is needed to resolve native stack offsets on this specific Android.
    $libDir = Join-Path $outDir 'system-libraries'
    $null = New-Item -ItemType Directory -Path $libDir
    foreach ($bits in @('32', '64')) {
        $lib = 'lib'
        if ($bits -eq '64') { $lib = 'lib64' }
        foreach ($source in @("/system/$lib/libart.so", "/apex/com.android.runtime/$lib/libart.so", "/apex/com.android.art/$lib/libart.so")) {
            $exists = Run-Adb -Arguments @('shell', "test -r $source") -Timeout 4
            if ($exists.Code -ne 0) { continue }
            $result = Run-Adb -Arguments @('pull', $source, (Join-Path $libDir "libart-$bits.so")) -Name "pull-art-$bits.txt" -Timeout 20
            if ($result.Code -eq 0) { break }
        }
        foreach ($name in @('libnb.so', 'libhoudini.so')) {
            $source = "/system/$lib/$name"
            $exists = Run-Adb -Arguments @('shell', "test -r $source") -Timeout 4
            if ($exists.Code -eq 0) {
                $null = Run-Adb -Arguments @('pull', $source, (Join-Path $libDir "$bits-$name")) -Name "pull-$bits-$name.txt" -Timeout 20
            }
        }
    }
} catch {
    $failure = $_.Exception.Message
} finally {
    if ($failure) { Save-Text (Join-Path $outDir 'ERROR.txt') $failure; Write-Host $failure }
    $summary = @('Coletor: original-mod-crash-v1', "Serial: $Serial", "Erro de coleta: $failure", 'Uma abertura automatica. Nenhum APK instalado, nenhum dado do app apagado.')
    $summary += 'Hashes conhecidos: mod original=cf725dbfa652671f925a517ab9e42e8bafcbff8fdc6e0b600d573c3e87a8f51e; compat-v1=02759bc8e1580fc392e1dd6fb545018eb95de713601a88f89ad8597c392e7bc1'
    $logs = @(Get-ChildItem -LiteralPath $outDir -Recurse -Filter 'logcat-live.txt')
    foreach ($log in $logs) {
        $hits = @(Select-String -LiteralPath $log.FullName -Pattern 'FATAL EXCEPTION|Fatal signal|Abort message|ModCompat|backtrace:|SIGSEGV|SIGABRT|UnsatisfiedLinkError|VerifyError|NoSuchMethodError|has died|ANR in' | Select-Object -Last 65)
        $summary += 'Trechos do log (podem incluir outros processos; conferir PID e horario):'
        $summary += @($hits | ForEach-Object { $_.Line })
    }
    Save-Text (Join-Path $outDir 'RESUMO.txt') ($summary -join "`r`n")
    $zip = "$outDir.zip"
    try {
        Compress-Archive -Path (Join-Path $outDir '*') -DestinationPath $zip -CompressionLevel Optimal
        Write-Host "`nEnvie este arquivo: $zip" -ForegroundColor Green
    } catch { Write-Host "Nao foi possivel compactar. A coleta esta em: $outDir" }
}
