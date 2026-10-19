param([string]$InputPath)
$ErrorActionPreference = 'Stop'
function Get-SafeUrl($value) {
    try {
        $u = [uri][string]$value
        if (-not $u.IsAbsoluteUri -or $u.Scheme -notin @('http','https')) { return $null }
        $segments = @($u.AbsolutePath.Split('/') | ForEach-Object {
            if ($_ -match '^\d{6,}$|^[a-zA-Z0-9_-]{24,}$|^[a-fA-F0-9]{8}-[a-fA-F0-9-]{27,}$|@|%40' -or $_.Length -gt 80) { '[id]' } else { $_ }
        })
        return $u.Scheme + '://' + $u.Authority + ($segments -join '/')
    } catch { return $null }
}
function Get-Number($value) {
    if ($value -is [byte] -or $value -is [int] -or $value -is [long] -or $value -is [double] -or $value -is [decimal]) {
        $n = [double]$value
        if (-not [double]::IsNaN($n) -and -not [double]::IsInfinity($n) -and $n -ge -1 -and $n -le 1000000000) { return $n }
    }
    return $null
}
try {
    if (-not $InputPath) {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Filter = 'Registro de rede (*.har)|*.har'
        $dialog.Title = 'Escolha o HAR exportado no DevTools'
        try {
            if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
            $InputPath = $dialog.FileName
        } finally { $dialog.Dispose() }
    }
    $file = Get-Item -LiteralPath $InputPath
    if ($file.PSIsContainer -or $file.Length -gt 134217728) { throw 'Arquivo invalido ou acima de 128 MiB.' }
    $har = [IO.File]::ReadAllText($file.FullName) | ConvertFrom-Json
    if ($null -eq $har.log.entries) { throw 'Formato HAR ausente.' }
    $entries = New-Object 'System.Collections.Generic.List[object]'
    foreach ($e in $har.log.entries) {
        $url = Get-SafeUrl $e.request.url
        if (-not $url) { continue }
        $timings = [ordered]@{}
        foreach ($key in @('blocked','dns','connect','ssl','send','wait','receive')) { $timings[$key] = Get-Number $e.timings.$key }
        $method = [string]$e.request.method
        if ($method -notin @('GET','POST','HEAD','PUT','PATCH','DELETE','OPTIONS','CONNECT')) { $method = 'OTHER' }
        $initiator = $null
        if ($e._initiator.type -in @('parser','script','preload','preflight','other','signedExchange')) { $initiator = $e._initiator.type }
        $frames = @($e._initiator.stack.callFrames | Select-Object -First 8 | ForEach-Object {
            $sourceUrl = Get-SafeUrl $_.url
            if ($sourceUrl) { [ordered]@{url=$sourceUrl; line=Get-Number $_.lineNumber; column=Get-Number $_.columnNumber} }
        })
        $when = $null; $parsed = [DateTimeOffset]::MinValue
        if ([DateTimeOffset]::TryParse([string]$e.startedDateTime,[ref]$parsed)) { $when = $parsed.ToString('o') }
        $status = Get-Number $e.response.status
        if ($null -ne $status -and ($status -lt 0 -or $status -gt 599)) { $status = $null }
        $mime = [string]$e.response.content.mimeType
        if ($mime -notmatch '^[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+$') { $mime = $null }
        $errorCode = $null
        $errorMatch = [regex]::Match([string]$e._error,'\bnet::ERR_[A-Z0-9_]+\b')
        if ($errorMatch.Success) { $errorCode = $errorMatch.Value }
        $redirect = Get-SafeUrl $e.response.redirectURL
        $entries.Add([ordered]@{
            started=$when; url=$url; method=$method; status=$status; durationMs=Get-Number $e.time
            timingsMs=$timings; bytes=Get-Number $e.response.bodySize; transferBytes=Get-Number $e.response._transferSize
            mime=$mime; initiator=$initiator; source=Get-SafeUrl $e._initiator.url; frames=$frames
            redirect=$redirect; error=$errorCode
            fromCache=($e._fromCache -eq $true -or $e.response._fromDiskCache -eq $true)
            fromServiceWorker=($e.response._fetchedViaServiceWorker -eq $true)
        })
    }
    if ($entries.Count -eq 0) { throw 'Sem requisicoes HTTP no arquivo.' }
    $output = Join-Path $file.DirectoryName ('mint-captcha-rede-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
    $result = [ordered]@{format='mint-network-metadata-v1'; note='Sem corpos, cabecalhos, cookies, query strings ou fragments. Dominios e caminhos continuam presentes.'; entries=@($entries.ToArray())}
    $json = $result | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($output,$json,(New-Object Text.UTF8Encoding($false)))
    Write-Host ('Pronto. Envie somente o arquivo JSON: ' + $output)
    Write-Host 'Revise dominios e caminhos: podem conter dados pessoais ou tokens nao reconhecidos. Nada foi enviado automaticamente.'
} catch {
    Write-Host 'Nao foi possivel ler esse HAR. Use um arquivo valido de ate 128 MiB, exportado na aba Rede.'
    exit 1
}
