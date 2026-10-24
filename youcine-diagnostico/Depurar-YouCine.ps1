# Windows PowerShell 5.1. All device execution is performed by the user.
param(
    [string]$Adb = '',
    [string]$Serial = '127.0.0.1:21503',
    [ValidateRange(8, 45)][int]$Seconds = 12,
    [ValidateRange(1, 5)][int]$Repetitions = 3,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$package = 'com.world.youcinetv'
$expectedSha = '4eeeca609bba3113793e725e8842a51c5a429724b121f4016c76bca984a683fc'
$apkUrl = 'https://github.com/vazrenata07-hash/reverseengii/releases/download/yc-tv-1.15.4-lean-v3.4.2-debug/yc-tv-1.15.4-lean-v3.4.2-debug.apk'
$stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$outDir = Join-Path ([Environment]::GetFolderPath('Desktop')) "youcine-depuracao-$stamp"
$null = New-Item -ItemType Directory -Path $outDir
$utf8 = [Text.UTF8Encoding]::new($false)
$remoteBase = '/sdcard/Android/data/com.world.youcinetv/files/yc_lean'
$remoteControl = "$remoteBase/diagnostic.properties"
$controlTouched = $false
$hadControl = $false
$capture = $null
$failed = ''
$controlRestore = 'not-touched'
$results = [Collections.Generic.List[object]]::new()
$tags = @('YCLean:V', 'YCTrace:V', 'LSPlant:V', 'Dobby:V', 'AndroidRuntime:V', 'DEBUG:V', 'libc:V', 'linker:V', 'crash_dump64:V', 'crash_dump32:V', 'tombstoned:V', 'ActivityManager:I', '*:S')

function Save-Text {
    param([string]$Path, [AllowEmptyString()][string]$Text)
    [IO.File]::WriteAllText($Path, $Text, $utf8)
}
function Invoke-AdbText {
    param([string[]]$AdbArguments, [switch]$AllowFailure, [switch]$WithoutSerial)
    $arguments = @()
    if (-not $WithoutSerial) { $arguments += @('-s', $Serial) }
    $arguments += $AdbArguments
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $lines = @(& $script:AdbPath @arguments 2>&1 | ForEach-Object { $_.ToString() })
        $exitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    $text = $lines -join [Environment]::NewLine
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "ADB falhou ($exitCode): $($AdbArguments -join ' ')`r`n$text"
    }
    [pscustomobject]@{ ExitCode = $exitCode; Text = $text }
}
function Save-Adb {
    param([string]$Path, [string[]]$AdbArguments)
    $result = Invoke-AdbText -AdbArguments $AdbArguments -AllowFailure
    Save-Text $Path ("exit_code=$($result.ExitCode)`r`n" + $result.Text)
    return $result
}
function Stop-Capture {
    if ($script:capture) {
        try {
            if (-not $script:capture.HasExited) { $script:capture.Kill() }
            $null = $script:capture.WaitForExit(5000)
            $script:capture.Dispose()
        } finally { $script:capture = $null }
    }
}
function Get-ApkHash {
    param([string]$Destination)
    $result = Save-Adb $Destination @('shell', 'for apk in $(pm path com.world.youcinetv | sed "s/^package://"); do sha256sum "$apk"; done')
    $match = [regex]::Match($result.Text, '(?im)^([0-9a-f]{64})\s+\S*base\.apk\s*$')
    if ($match.Success) { return $match.Groups[1].Value.ToLowerInvariant() }
    return ''
}
function Get-Tombstones {
    param([string]$Destination)
    $result = Save-Adb $Destination @('shell', 'for f in /data/tombstones/tombstone_*; do [ -f "$f" ] && [ -r "$f" ] && stat -c "%n %Y %s" "$f" 2>/dev/null; done')
    $index = @{}
    foreach ($line in ($result.Text -split '\r?\n')) {
        $match = [regex]::Match($line.Trim(), '^(/data/tombstones/tombstone_[0-9]+)\s+([0-9]+)\s+([0-9]+)$')
        if ($match.Success) { $index[$match.Groups[1].Value] = $line.Trim() }
    }
    return $index
}
function Snapshot-Process {
    param([string]$Directory, [string]$Suffix)
    $state = Save-Adb (Join-Path $Directory "pid-$Suffix.txt") @('shell', 'pidof', $package)
    foreach ($processId in ($state.Text.Trim() -split '\s+')) {
        if ($processId -notmatch '^\d+$') { continue }
        $maps = Invoke-AdbText @('shell', 'cat', "/proc/$processId/maps") -AllowFailure
        Save-Text (Join-Path $Directory "maps-$Suffix-$processId.txt") $maps.Text
        $null = Save-Adb (Join-Path $Directory "status-$Suffix-$processId.txt") @('shell', 'cat', "/proc/$processId/status")
        $null = Save-Adb (Join-Path $Directory "wait-$Suffix-$processId.txt") @('shell', "cat /proc/$processId/wchan; cat /proc/$processId/stack 2>/dev/null; readlink /proc/$processId/exe")
    }
    return $state.Text
}
function Collect-Art {
    $directory = Join-Path $outDir 'art-sistema'
    $null = New-Item -ItemType Directory -Path $directory
    $report = [Collections.Generic.List[string]]::new()
    foreach ($bits in @('64', '32')) {
        $lib = 'lib'
        if ($bits -eq '64') { $lib = 'lib64' }
        foreach ($path in @("/apex/com.android.art/$lib/libart.so", "/apex/com.android.runtime/$lib/libart.so", "/system/$lib/libart.so")) {
            $probe = Invoke-AdbText @('shell', 'test', '-r', $path) -AllowFailure
            if ($probe.ExitCode -ne 0) { continue }
            $result = Invoke-AdbText @('pull', $path, (Join-Path $directory "libart-$bits.so")) -AllowFailure
            $report.Add("source=$path exit_code=$($result.ExitCode)")
            $report.Add($result.Text)
            if ($result.ExitCode -eq 0) { break }
        }
    }
    Save-Text (Join-Path $outDir 'art-sistema.txt') ($report -join "`r`n")
}

try {
    if ($Serial -notmatch '^[A-Za-z0-9_.:-]+$') { throw 'Serial ADB invalido.' }
    $candidates = @()
    if ($Adb) { $candidates += $Adb }
    else {
        $candidates += @((Join-Path (Get-Location).Path 'adb.exe'), (Join-Path $PSScriptRoot 'adb.exe'), 'C:\Program Files\Microvirt\MEmu\adb.exe', 'C:\Program Files (x86)\Microvirt\MEmu\adb.exe')
        $command = Get-Command adb.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $script:AdbPath = $null
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $script:AdbPath = (Resolve-Path -LiteralPath $candidate).Path; break }
    }
    if (-not $script:AdbPath) { throw 'ADB nao encontrado. Execute na pasta do MEmu ou informe -Adb.' }
    Save-Text (Join-Path $outDir 'coletor.txt') ("collector=phase-debug-v1`r`nserial=$Serial`r`nadb=$script:AdbPath`r`nexpected_sha256=$expectedSha`r`nseconds_per_phase=$Seconds`r`n")
    Write-Host 'Conectando ao MEmu...'
    $connected = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $null = Invoke-AdbText @('connect', $Serial) -WithoutSerial -AllowFailure
        $state = Invoke-AdbText @('get-state') -AllowFailure
        if ($state.ExitCode -eq 0 -and $state.Text.Trim() -eq 'device') { $connected = $true; break }
        Start-Sleep -Milliseconds 700
    }
    if (-not $connected) { throw 'MEmu nao respondeu. Confira a porta dessa instancia.' }
    $null = Save-Adb (Join-Path $outDir 'ambiente.txt') @('shell', 'id; date; uname -a; for p in ro.build.version.release ro.build.version.sdk ro.product.model ro.product.cpu.abilist ro.product.cpu.abilist32 ro.product.cpu.abilist64 ro.dalvik.vm.native.bridge; do echo "$p=$(getprop "$p")"; done')
    $null = Save-Adb (Join-Path $outDir 'adb-versao.txt') @('version')
    $beforeHash = Get-ApkHash (Join-Path $outDir 'apk-antes.txt')
    if ($beforeHash -ne $expectedSha) {
        if ($SkipInstall) { throw 'O APK instalado nao corresponde a build de depuracao. Retire -SkipInstall.' }
        Write-Host 'Baixando a build de depuracao e conferindo SHA-256...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $download = Join-Path ([Environment]::GetFolderPath('Desktop')) 'yc-tv-v3.4.2-debug.apk'
        if (-not (Test-Path -LiteralPath $download) -or (Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash -ne $expectedSha) {
            Invoke-WebRequest -UseBasicParsing -Uri $apkUrl -OutFile $download
        }
        if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash -ne $expectedSha) { throw 'SHA-256 do download diverge da build publicada.' }
        Write-Host 'Instalando atualizacao com os dados preservados...'
        $install = Invoke-AdbText @('install', '-r', $download) -AllowFailure
        Save-Text (Join-Path $outDir 'instalacao.txt') $install.Text
        if ($install.ExitCode -ne 0 -or $install.Text -notmatch '(?m)^Success\s*$') { throw 'A atualizacao nao foi instalada. Veja instalacao.txt. Nenhum app foi desinstalado.' }
    }
    $actualHash = Get-ApkHash (Join-Path $outDir 'apk-depuracao.txt')
    if ($actualHash -ne $expectedSha) { throw 'Nao foi possivel confirmar o hash exato do APK instalado. A comparacao nao sera iniciada.' }
    $null = Save-Adb (Join-Path $outDir 'pacote.txt') @('shell', 'dumpsys', 'package', $package)
    $null = Invoke-AdbText @('shell', 'am', 'force-stop', $package)
    $null = Invoke-AdbText @('shell', "mkdir -p $remoteBase")
    $probe = Invoke-AdbText @('shell', 'test', '-f', $remoteControl) -AllowFailure
    if ($probe.ExitCode -eq 0) {
        $null = Invoke-AdbText @('pull', $remoteControl, (Join-Path $outDir 'controle-anterior.properties'))
        $hadControl = $true
    }
    $controlTouched = $true
    $component = ''
    foreach ($category in @('android.intent.category.LEANBACK_LAUNCHER', 'android.intent.category.LAUNCHER')) {
        $resolved = Invoke-AdbText @('shell', 'cmd', 'package', 'resolve-activity', '--brief', '-a', 'android.intent.action.MAIN', '-c', $category, $package) -AllowFailure
        foreach ($line in ($resolved.Text -split '\r?\n')) {
            if ($line.Trim() -match '^com\.world\.youcinetv/[A-Za-z0-9_.$]+$') { $component = $line.Trim(); break }
        }
        if ($component) { break }
    }
    if (-not $component) { $component = "$package/com.interactive.brasiliptv.ui.activity.WelcomeActivity" }
    $groups = @(
        @{ Label = '01-off-before'; Mode = 'off' },
        @{ Label = '02-boundary'; Mode = 'boundary' },
        @{ Label = '03-runtime'; Mode = 'runtime' },
        @{ Label = '04-beans'; Mode = 'beans' },
        @{ Label = '05-properties'; Mode = 'properties' },
        @{ Label = '06-full'; Mode = 'full' },
        @{ Label = '07-off-after'; Mode = 'off' }
    )
    $phases = @()
    foreach ($group in $groups) {
        for ($attempt = 1; $attempt -le $Repetitions; $attempt++) {
            $phases += @{ Label = "$($group.Label)-try$attempt"; Mode = $group.Mode; Group = $group.Label; Attempt = $attempt }
        }
    }
    Write-Host "Serao $($phases.Count) aberturas automaticas ($Repetitions por fase). Mantenha esta instancia do MEmu disponivel."
    foreach ($phase in $phases) {
        $label = $phase.Label
        $mode = $phase.Mode
        $run = "$stamp-$label"
        $directory = Join-Path $outDir $label
        $null = New-Item -ItemType Directory -Path $directory
        Write-Host "Fase $label - $Seconds segundos"
        $null = Invoke-AdbText @('shell', 'am', 'force-stop', $package)
        $controlPath = Join-Path $directory 'diagnostic.properties'
        Save-Text $controlPath ("mode=$mode`nrun=$run`n")
        $null = Invoke-AdbText @('push', $controlPath, $remoteControl)
        $null = Save-Adb (Join-Path $directory 'controle-lido-pelo-adb.txt') @('shell', 'cat', $remoteControl)
        $before = Get-Tombstones (Join-Path $directory 'tombstones-antes.txt')
        $null = Save-Adb (Join-Path $directory 'crash-antes.txt') @('logcat', '-b', 'crash', '-d', '-v', 'threadtime', '*:V')
        $livePath = Join-Path $directory 'logcat.txt'
        $script:capture = Start-Process -FilePath $script:AdbPath -ArgumentList (@('-s', $Serial, 'logcat', '-b', 'all', '-v', 'threadtime', '-T', '1') + $tags) -NoNewWindow -PassThru -RedirectStandardOutput $livePath -RedirectStandardError (Join-Path $directory 'logcat-erros.txt')
        Start-Sleep -Milliseconds 400
        $marker = "YC_PHASE_$run"
        $null = Invoke-AdbText @('shell', 'log', '-p', 'i', '-t', 'YCTrace', $marker) -AllowFailure
        $null = Save-Adb (Join-Path $directory 'abertura.txt') @('shell', 'am', 'start', '-n', $component)
        $timer = [Diagnostics.Stopwatch]::StartNew()
        $sampled = $false
        while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
            if ($script:capture.HasExited) { throw "Logcat encerrou na fase $label." }
            if (-not $sampled -and $timer.Elapsed.TotalSeconds -ge 1) {
                $null = Snapshot-Process $directory 'inicio'
                $sampled = $true
            }
            Write-Progress -Activity 'Depuracao por fases' -Status $label -PercentComplete ([int](100 * ([array]::IndexOf($phases, $phase) + [Math]::Min(1, $timer.Elapsed.TotalSeconds / $Seconds)) / $phases.Count))
            Start-Sleep -Milliseconds 500
        }
        $endPids = Snapshot-Process $directory 'fim'
        $focus = Save-Adb (Join-Path $directory 'foco.txt') @('shell', 'dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"')
        $null = Save-Adb (Join-Path $directory 'crash-depois.txt') @('logcat', '-b', 'crash', '-d', '-v', 'threadtime', '*:V')
        $after = Get-Tombstones (Join-Path $directory 'tombstones-depois.txt')
        $tombstoneCount = 0
        foreach ($path in ($after.Keys | Sort-Object)) {
            if ($before.ContainsKey($path) -and $before[$path] -eq $after[$path]) { continue }
            $body = Invoke-AdbText @('shell', 'cat', $path) -AllowFailure
            if ($body.ExitCode -ne 0 -or $body.Text -notmatch 'com\.world\.youcinetv') { continue }
            Save-Text (Join-Path $directory ((Split-Path -Leaf $path) + '.txt')) $body.Text
            if (++$tombstoneCount -ge 5) { break }
        }
        $tracePath = Join-Path $directory 'trace.jsonl'
        $tracePull = Invoke-AdbText @('pull', "$remoteBase/trace-$run.jsonl", $tracePath) -AllowFailure
        Save-Text (Join-Path $directory 'diario-coleta.txt') $tracePull.Text
        $inventory = Invoke-AdbText @('pull', "$remoteBase/classes-$run.txt", (Join-Path $directory 'classes.txt')) -AllowFailure
        Save-Text (Join-Path $directory 'classes-coleta.txt') $inventory.Text
        Stop-Capture
        $records = @()
        if (Test-Path -LiteralPath $tracePath) {
            foreach ($line in [IO.File]::ReadAllLines($tracePath, [Text.Encoding]::UTF8)) {
                try { $record = $line | ConvertFrom-Json; if ($record.run -eq $run) { $records += $record } }
                catch { Save-Text (Join-Path $directory 'diario-parse-aviso.txt') $_.Exception.Message }
            }
        }
        $fresh = ''
        $log = [IO.File]::ReadAllText($livePath, [Text.Encoding]::UTF8)
        $position = $log.IndexOf($marker, [StringComparison]::Ordinal)
        if ($position -ge 0) {
            $lineEnd = $log.IndexOf("`n", $position)
            if ($lineEnd -ge 0) { $fresh = $log.Substring($lineEnd + 1) }
        }
        $actualMode = ''
        if ($records.Count -gt 0) { $actualMode = $records[0].mode }
        $errors = @($records | Where-Object { $_.event -in @('application-oncreate-threw', 'uncaught-java', 'engine-failed', 'engine-linkage-failed', 'rules-phase-failed') })
        $lastEvent = ''
        if ($records.Count -gt 0) { $lastEvent = $records[-1].event + ': ' + $records[-1].detail }
        $result = [pscustomobject][ordered]@{
            phase = $label; group = $phase.Group; attempt = $phase.Attempt; run = $run; requested_mode = $mode; observed_mode = $actualMode
            valid_mode_journal = ($records.Count -gt 0 -and $actualMode -eq $mode)
            fresh_log_marker = ($position -ge 0)
            pids = @($records | ForEach-Object { $_.pid } | Sort-Object -Unique)
            process_alive_at_end = ($endPids.Trim() -match '^\d+(\s+\d+)*$')
            app_in_focus = ($focus.Text -match 'com\.world\.youcinetv')
            application_entered = (@($records | Where-Object { $_.event -eq 'application-oncreate-enter' }).Count -gt 0)
            application_returned = (@($records | Where-Object { $_.event -eq 'application-oncreate-return' }).Count -gt 0)
            engine_entered = (@($records | Where-Object { $_.event -eq 'engine-enter' }).Count -gt 0)
            engine_ready = (@($records | Where-Object { $_.event -eq 'engine-load-return' -and $_.detail -match 'ready=true' }).Count -gt 0)
            properties_installed = (@($records | Where-Object { $_.event -eq 'properties-hook-installed' }).Count -gt 0)
            beans_installed_count = @($records | Where-Object { $_.event -eq 'bean-hook-installed' }).Count
            activity_resumed = (@($records | Where-Object { $_.event -eq 'activity-resumed' }).Count -gt 0)
            java_exception_recorded = (@($errors | Where-Object { $_.event -in @('application-oncreate-threw', 'uncaught-java') }).Count -gt 0)
            java_fatal_for_package_in_log = ($fresh -match 'FATAL EXCEPTION' -and $fresh -match 'Process: com\.world\.youcinetv[,\s]')
            native_backtrace_for_package_in_log = ($fresh -match '>>> com\.world\.youcinetv <<<|Cmdline: com\.world\.youcinetv')
            new_app_tombstones = $tombstoneCount
            last_event = $lastEvent
            errors = @($errors | Select-Object event, detail, stack)
        }
        $results.Add($result)
        Save-Text (Join-Path $directory 'resultado.json') ($result | ConvertTo-Json -Depth 8)
        Save-Text (Join-Path $outDir 'resultados.json') (ConvertTo-Json -InputObject @($results.ToArray()) -Depth 10)
    }
    Write-Progress -Activity 'Depuracao por fases' -Completed
    Write-Host 'Coletando as bibliotecas publicas do ART...'
    Collect-Art
} catch {
    $failed = $_.Exception.Message
    Save-Text (Join-Path $outDir 'falha-coleta.txt') ($_ | Out-String)
    Write-Host "Coleta parcial: $failed" -ForegroundColor Yellow
} finally {
    try { Stop-Capture } catch { Save-Text (Join-Path $outDir 'falha-logcat-final.txt') ($_ | Out-String) }
    if ($controlTouched) {
        try {
            $null = Invoke-AdbText @('shell', 'am', 'force-stop', $package) -AllowFailure
            if ($hadControl) {
                $restore = Invoke-AdbText @('push', (Join-Path $outDir 'controle-anterior.properties'), $remoteControl) -AllowFailure
            } else {
                $restore = Invoke-AdbText @('shell', 'rm', '-f', $remoteControl) -AllowFailure
            }
            Save-Text (Join-Path $outDir 'restauracao-controle.txt') ("exit_code=$($restore.ExitCode)`r`n" + $restore.Text)
            if ($restore.ExitCode -eq 0) { $controlRestore = 'success' }
            else { $controlRestore = 'failed'; Write-Host 'Falha ao restaurar o arquivo de controle. Veja restauracao-controle.txt.' -ForegroundColor Yellow }
        } catch { $controlRestore = 'failed'; Save-Text (Join-Path $outDir 'falha-restauracao.txt') ($_ | Out-String) }
    }
    Write-Progress -Activity 'Depuracao por fases' -Completed
}

$summary = [Collections.Generic.List[string]]::new()
$summary.Add('DEPURACAO YOUCINE - COMPARACAO DE ETAPAS')
$summary.Add("Build esperada: v3.4.2-debug / SHA256 $expectedSha")
$summary.Add("Execucoes concluidas: $($results.Count) / $(7 * $Repetitions)")
$summary.Add("Restauracao do controle: $controlRestore")
if ($failed) { $summary.Add("Falha da coleta: $failed") }
$summary.Add('fase | modo confirmado | vivo ao final | foco no app | Application retornou | motor pronto | excecao Java | tombstones')
foreach ($result in $results) {
    $summary.Add("$($result.phase) | $($result.valid_mode_journal) | $($result.process_alive_at_end) | $($result.app_in_focus) | $($result.application_returned) | $($result.engine_ready) | $($result.java_exception_recorded -or $result.java_fatal_for_package_in_log) | $($result.new_app_tombstones)")
    $summary.Add("  ultima etapa: $($result.last_event)")
    foreach ($errorRecord in $result.errors) { $summary.Add("  $($errorRecord.event): $($errorRecord.detail)") }
}
$summary.Add('OFF usa carregador/imagem originais, provider e diario; nao usa motor nem fronteira Instrumentation.')
$summary.Add('OFF nao e uma execucao do APK original intacto. RUNTIME inicializa hooks internos do motor, sem hooks de app.')
$summary.Add('O diario confirma o modo realmente lido. Fases sem diario correspondente nao sao conclusivas.')
$summary.Add('Processo vivo nao comprova UI funcional. Ausencia de fatal nao prova encerramento normal.')
$summary.Add('A ordem e os mesmos dados/caches podem influenciar os resultados. Compare OFF inicial e final.')
$summary.Add('Nenhum dado/cache/logcat foi limpo. O APK de depuracao permanece instalado, com padrao OFF. O app foi encerrado no final e o arquivo de controle anterior foi restaurado quando possivel.')
Save-Text (Join-Path $outDir 'RESUMO.txt') ($summary -join "`r`n")
$zipPath = "$outDir.zip"
Compress-Archive -Path (Join-Path $outDir '*') -DestinationPath $zipPath
Write-Host "`nArquivo para enviar: $zipPath" -ForegroundColor Green
Write-Host "Resumo: $(Join-Path $outDir 'RESUMO.txt')"
if ($failed) { exit 1 }
