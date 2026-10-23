# Coletor de integracao da v3.3.1. Compativel com Windows PowerShell 5.1.
# Nao instala APK, nao limpa dados/cache/logcat e nao solicita root.
param(
    [string]$Adb = '',
    [string]$Serial = '127.0.0.1:21503',
    [ValidateRange(15, 180)][int]$Seconds = 60,
    [switch]$SemReiniciar
)

$ErrorActionPreference = 'Stop'
$package = 'com.world.youcinetv'
$expectedSha = '133f1e0acc5e5fe1511a452f2eb612eb06d1c142453cd8bcb87d8afb18c1a22f'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$desktop = [Environment]::GetFolderPath('Desktop')
$outDir = Join-Path $desktop "youcine-rotina-$stamp"
$null = New-Item -ItemType Directory -Path $outDir
$utf8 = [Text.UTF8Encoding]::new($false)
$capture = $null
$complete = $false
$failure = ''
$marker = "YC_DIAG_START_$stamp"
$tags = @('YCLean:V', 'LSPlant:V', 'Dobby:V', 'AndroidRuntime:V', 'linker:V', 'libc:W', '*:S')
$livePath = Join-Path $outDir 'inicializacao.txt'

function Save-Text {
    param([string]$Name, [AllowEmptyString()][string]$Text)
    [IO.File]::WriteAllText((Join-Path $outDir $Name), $Text, $utf8)
}

function Invoke-AdbText {
    param([string[]]$AdbArguments, [switch]$AllowFailure, [switch]$WithoutSerial)
    $arguments = @()
    if (-not $WithoutSerial) { $arguments += @('-s', $Serial) }
    $arguments += $AdbArguments
    # ADB may write daemon/version messages to stderr even when it succeeds.
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
    param([string]$Name, [string[]]$AdbArguments)
    $result = Invoke-AdbText -AdbArguments $AdbArguments -AllowFailure
    Save-Text $Name ("exit_code=$($result.ExitCode)`r`n" + $result.Text)
    return $result
}

function Snapshot-Process {
    param([string]$Suffix)
    $result = Save-Adb "processo-$Suffix.txt" @('shell', 'pidof', $package)
    foreach ($processId in ($result.Text.Trim() -split '\s+')) {
        if ($processId -notmatch '^\d+$') { continue }
        $maps = Invoke-AdbText @('shell', 'cat', "/proc/$processId/maps") -AllowFailure
        if ($maps.ExitCode -eq 0) {
            $selected = @($maps.Text -split '\r?\n' | Where-Object {
                $_ -match 'libart\.so|libycidentity\.so|libexec\.so|libhoudini|libc\+\+|yc_hooks|yc_identity'
            })
            Save-Text "bibliotecas-$Suffix-$processId.txt" ($selected -join "`r`n")
        } else {
            Save-Text "bibliotecas-$Suffix-$processId.txt" ("Mapas indisponiveis para o usuario ADB; nenhuma elevacao foi solicitada.`r`n" + $maps.Text)
        }
    }
}

function Collect-ArtFiles {
    $directory = Join-Path $outDir 'art-sistema'
    $null = New-Item -ItemType Directory -Path $directory
    $report = [Collections.Generic.List[string]]::new()
    foreach ($bits in @('64', '32')) {
        $lib = 'lib'
        if ($bits -eq '64') { $lib = 'lib64' }
        $found = $false
        foreach ($path in @("/apex/com.android.art/$lib/libart.so", "/apex/com.android.runtime/$lib/libart.so", "/system/$lib/libart.so")) {
            $probe = Invoke-AdbText @('shell', 'test', '-r', $path) -AllowFailure
            if ($probe.ExitCode -ne 0) { continue }
            $destination = Join-Path $directory "libart-$bits.so"
            $pull = Invoke-AdbText @('pull', $path, $destination) -AllowFailure
            $report.Add("source=$path exit_code=$($pull.ExitCode)")
            $report.Add($pull.Text)
            if ($pull.ExitCode -eq 0) { $found = $true; break }
        }
        if (-not $found) { $report.Add("art_$bits=unavailable") }
    }
    Save-Text 'art-sistema.txt' ($report -join "`r`n")
}

try {
    if ($Serial -notmatch '^[A-Za-z0-9_.:-]+$') { throw 'Serial ADB invalido.' }
    $candidates = @()
    if ($Adb) { $candidates += $Adb }
    else {
        $candidates += @((Join-Path (Get-Location).Path 'adb.exe'),
                         (Join-Path $PSScriptRoot 'adb.exe'),
                         'C:\Program Files\Microvirt\MEmu\adb.exe',
                         'C:\Program Files (x86)\Microvirt\MEmu\adb.exe')
        $command = Get-Command adb.exe -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $script:AdbPath = $null
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $script:AdbPath = (Resolve-Path -LiteralPath $candidate).Path
            break
        }
    }
    if (-not $script:AdbPath) { throw 'ADB nao encontrado. Execute na pasta do MEmu ou informe -Adb com o caminho de adb.exe.' }
    Save-Text 'coletor.txt' ("collector=identity-v1`r`nserial=$Serial`r`nadb=$script:AdbPath`r`nseconds=$Seconds`r`nrestart=$(-not $SemReiniciar)`r`nexpected_apk_sha256=$expectedSha`r`n")
    Write-Host 'Conectando ao MEmu...'
    $connected = $false
    $connections = [Collections.Generic.List[string]]::new()
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $result = Invoke-AdbText @('connect', $Serial) -WithoutSerial -AllowFailure
        $connections.Add($result.Text)
        $state = Invoke-AdbText @('get-state') -AllowFailure
        $connections.Add($state.Text)
        if ($state.ExitCode -eq 0 -and $state.Text.Trim() -eq 'device') { $connected = $true; break }
        Start-Sleep -Milliseconds 700
    }
    Save-Text 'conexao.txt' ($connections -join "`r`n")
    if (-not $connected) { throw 'MEmu nao respondeu no serial informado. Confira a porta ADB dessa instancia.' }
    $null = Save-Adb 'adb-versao.txt' @('version')
    $null = Save-Adb 'ambiente.txt' @('shell', 'id; uname -a; for p in ro.build.version.release ro.build.version.sdk ro.product.model ro.product.cpu.abilist ro.product.cpu.abilist32 ro.product.cpu.abilist64 ro.dalvik.vm.native.bridge ro.enable.native.bridge.exec ro.enable.native.bridge.exec64; do echo "$p=$(getprop "$p")"; done')
    $paths = Save-Adb 'apk-caminhos.txt' @('shell', 'pm', 'path', $package)
    if ($paths.ExitCode -ne 0 -or $paths.Text -notmatch '(?m)^package:') { throw 'YouCine nao encontrado nessa instancia do MEmu.' }
    $hashes = Save-Adb 'apk-sha256.txt' @('shell', 'for apk in $(pm path com.world.youcinetv | sed "s/^package://"); do sha256sum "$apk"; done')
    $null = Save-Adb 'pacote.txt' @('shell', 'dumpsys', 'package', $package)
    $null = Save-Adb 'providers-antes.txt' @('shell', 'dumpsys', 'activity', 'providers', $package)
    $null = Save-Adb 'historico-anterior.txt' (@('logcat', '-b', 'all', '-d', '-v', 'threadtime') + $tags)

    $capture = Start-Process -FilePath $script:AdbPath -ArgumentList (@('-s', $Serial, 'logcat', '-b', 'all', '-v', 'threadtime', '-T', '1') + $tags) -NoNewWindow -PassThru -RedirectStandardOutput $livePath -RedirectStandardError (Join-Path $outDir 'logcat-erros.txt')
    Start-Sleep -Milliseconds 500
    $null = Save-Adb 'marcador.txt' @('shell', 'log', '-p', 'i', '-t', 'YCLean', $marker)
    if (-not $SemReiniciar) {
        Write-Host 'Reabrindo o app, mantendo os dados...'
        $null = Save-Adb 'parada-inicial.txt' @('shell', 'am', 'force-stop', $package)
        $component = ''
        foreach ($category in @('android.intent.category.LEANBACK_LAUNCHER', 'android.intent.category.LAUNCHER')) {
            $resolved = Invoke-AdbText @('shell', 'cmd', 'package', 'resolve-activity', '--brief', '-a', 'android.intent.action.MAIN', '-c', $category, $package) -AllowFailure
            foreach ($line in ($resolved.Text -split '\r?\n')) {
                if ($line.Trim() -match '^com\.world\.youcinetv/[A-Za-z0-9_.$]+$') { $component = $line.Trim(); break }
            }
            if ($component) { break }
        }
        if (-not $component) { $component = "$package/com.interactive.brasiliptv.ui.activity.WelcomeActivity" }
        $null = Save-Adb 'abertura.txt' @('shell', 'am', 'start', '-n', $component)
    }
    Write-Host "Use o aplicativo e reproduza o aviso de expirado. Coleta automatica: $Seconds segundos."
    Write-Host 'Ao final, o app permanece aberto. Nao e necessario pausar o log manualmente.'
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $initialSnapshot = $false
    while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        if ($capture.HasExited) { throw 'O processo de logcat encerrou antes do fim. Veja logcat-erros.txt.' }
        if (-not $initialSnapshot -and $timer.Elapsed.TotalSeconds -ge 3) {
            Snapshot-Process 'inicio'
            $initialSnapshot = $true
        }
        $remaining = [Math]::Max(0, [int]($Seconds - $timer.Elapsed.TotalSeconds))
        Write-Progress -Activity 'Diagnostico YouCine' -Status "Reproduza o aviso. Faltam aproximadamente $remaining s." -PercentComplete ([Math]::Min(100, [int](100 * $timer.Elapsed.TotalSeconds / $Seconds)))
        Start-Sleep -Milliseconds 500
    }
    Write-Progress -Activity 'Diagnostico YouCine' -Completed
    Snapshot-Process 'fim'
    $null = Save-Adb 'providers-depois.txt' @('shell', 'dumpsys', 'activity', 'providers', $package)
    $null = Save-Adb 'tela-ativa.txt' @('shell', 'dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"')
    # Public runtime libraries permit offline ELF inspection if discovery fails.
    # No app-private session data or memory is copied.
    Write-Host 'Coletando as bibliotecas publicas do ART, quando disponiveis...'
    Collect-ArtFiles
    $complete = $true
} catch {
    $failure = $_.Exception.Message
    Save-Text 'falha-coleta.txt' ($_ | Out-String)
    Write-Host "Coleta parcial: $failure" -ForegroundColor Yellow
} finally {
    if ($capture) {
        try {
            if (-not $capture.HasExited) { $capture.Kill() }
            $null = $capture.WaitForExit(5000)
            $capture.Dispose()
        } catch { Save-Text 'falha-encerramento-logcat.txt' ($_ | Out-String) }
    }
    Write-Progress -Activity 'Diagnostico YouCine' -Completed
}

# Analyze only records after this run's marker, never old successful messages.
$fresh = ''
$markerSeen = $false
if (Test-Path -LiteralPath $livePath) {
    $content = [IO.File]::ReadAllText($livePath, [Text.Encoding]::UTF8)
    $position = $content.IndexOf($marker, [StringComparison]::Ordinal)
    if ($position -ge 0) {
        $markerSeen = $true
        $lineEnd = $content.IndexOf("`n", $position)
        if ($lineEnd -ge 0) { $fresh = $content.Substring($lineEnd + 1) }
    }
}
$installedHash = ''
$hashPath = Join-Path $outDir 'apk-sha256.txt'
if (Test-Path -LiteralPath $hashPath) {
    $match = [regex]::Match([IO.File]::ReadAllText($hashPath), '(?im)^([0-9a-f]{64})\s+\S*base\.apk\s*$')
    if ($match.Success) { $installedHash = $match.Groups[1].Value.ToLowerInvariant() }
}
$status = [ordered]@{
    collector = 'identity-v1'
    collection_complete = $complete
    collection_error = $failure
    fresh_marker_seen = $markerSeen
    expected_apk_sha256 = $expectedSha
    installed_apk_sha256 = $installedHash
    exact_v331_apk_confirmed = ($installedHash -eq $expectedSha)
    provider_entered = ($fresh -match 'v3\.3(?:\.1)? identity provider entered')
    runtime_ready = ($fresh -match 'ART identity runtime ready=true')
    runtime_failure_reported = ($fresh -match 'ART identity runtime ready=false|ART identity runtime unavailable|ART identity runtime could not load|ART symbols unavailable|ART hook initialization ready=0')
    art_discovery_reported = ($fresh -match 'ART discovery phdr=')
    art_symbols_parsed = ($fresh -match 'ART symbols parsed=[1-9][0-9]*')
    art_symbols_unavailable = ($fresh -match 'ART symbols unavailable')
    preinstall_hook_installed = ($fresh -match 'Request fingerprint hook installed: com\.request\.bean\.PreInstallAuthBean')
    sntoken_hook_installed = ($fresh -match 'Request fingerprint hook installed: com\.request\.bean\.SnTokenBean')
    preinstall_callback_used = ($fresh -match 'Fresh request fingerprint applied: com\.request\.bean\.PreInstallAuthBean')
    sntoken_callback_used = ($fresh -match 'Fresh request fingerprint applied: com\.request\.bean\.SnTokenBean')
    properties_hook_installed = ($fresh -match 'Properties persistence rule installed:')
    properties_callback_used = ($fresh -match 'Properties persistence callback skipped:')
    constructor_failure_reported = ($fresh -match 'Request identity rule not installed|Request identity class unavailable')
    properties_failure_reported = ($fresh -match 'Properties rule skipped:|Properties rule discovery failed|Properties rule unavailable|Properties writer hook rejected')
}
Save-Text 'etapas.json' ($status | ConvertTo-Json -Depth 4)
$summary = [Collections.Generic.List[string]]::new()
$summary.Add('DIAGNOSTICO DE INTEGRACAO YOUCINE V3.3.1')
$summary.Add("Coleta completa: $complete")
$summary.Add("Marcador da execucao encontrado: $markerSeen")
if ($failure) { $summary.Add("Erro de coleta: $failure") }
if ($installedHash) {
    $summary.Add("APK instalado corresponde exatamente a v3.3.1 publicada: $($status.exact_v331_apk_confirmed)")
} else { $summary.Add('Hash do APK base indisponivel: a versao exata nao foi confirmada.') }
if (-not $markerSeen) {
    $summary.Add('Nao foi possivel delimitar os logs novos. Os indicadores abaixo nao comprovam falha ou sucesso do app.')
}
foreach ($key in @('provider_entered', 'runtime_ready', 'runtime_failure_reported', 'art_discovery_reported', 'art_symbols_parsed', 'art_symbols_unavailable', 'preinstall_hook_installed', 'sntoken_hook_installed', 'preinstall_callback_used', 'sntoken_callback_used', 'properties_hook_installed', 'properties_callback_used', 'constructor_failure_reported', 'properties_failure_reported')) {
    $summary.Add("${key}: $($status[$key])")
}
$summary.Add('false significa que o evento nao foi observado nesta janela; nao prova a causa sozinho.')
$summary.Add('Instalar um callback nao comprova sua execucao; executar o callback nao comprova concessao de VIP pelo servidor.')
$summary.Add('--- Mensagens de integracao desta execucao ---')
foreach ($line in ($fresh -split '\r?\n' | Where-Object { $_ -match 'YCLean\s*:|LSPlant\s*:|Dobby\s*:' } | Select-Object -First 200)) {
    $summary.Add($line)
}
Save-Text 'RESUMO.txt' ($summary -join "`r`n")
$zipPath = "$outDir.zip"
Compress-Archive -Path (Join-Path $outDir '*') -DestinationPath $zipPath
Write-Host "`nArquivo para enviar: $zipPath" -ForegroundColor Green
Write-Host "Resumo: $(Join-Path $outDir 'RESUMO.txt')"
if (-not $complete) { exit 1 }
