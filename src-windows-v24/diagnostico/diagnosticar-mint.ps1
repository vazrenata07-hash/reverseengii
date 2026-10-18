param([string]$ExePath)
$ErrorActionPreference = 'Stop'
$exitCode = 0
$port = 19288
$log = Join-Path $PSScriptRoot ('mint-diagnostico-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
$utf8 = New-Object System.Text.UTF8Encoding($true)
$writer = New-Object System.IO.StreamWriter($log, $false, $utf8)
$script:socket = $null; $script:receiveTask = $null; $script:sequence = 0
$script:buffer = New-Object byte[] 65536
$script:partial = New-Object System.IO.MemoryStream
$script:requests = @{}; $script:jsErrors = 0; $script:networkErrors = 0
function Write-Log([string]$message) {
    $writer.WriteLine(('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $message)); $writer.Flush()
    Write-Host $message
}
function Safe-Text([string]$value) {
    $value = [regex]::Replace($value, '(?i)(?:https?|wss?)://[^\s<>"'']+', {
        param($m)
        try { $u = [uri]$m.Value; return $u.Scheme + '://' + $u.Host + $u.AbsolutePath }
        catch { return '[URL omitida]' }
    })
    if ($value.Length -gt 1600) { return $value.Substring(0, 1600) + ' [truncado]' }
    return $value
}
function Get-HostOnly([string]$url) { try { return ([uri]$url).Host } catch { return '[host desconhecido]' } }
function Send-Cdp([string]$method, $parameters) {
    $script:sequence++
    $payload = @{id=$script:sequence; method=$method; params=$parameters} | ConvertTo-Json -Depth 8 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $segment = New-Object 'System.ArraySegment[byte]' -ArgumentList @(,$bytes)
    [void]$script:socket.SendAsync($segment, [Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    return [int]$script:sequence
}
function Read-Cdp([int]$waitMs) {
    $until = [DateTime]::UtcNow.AddMilliseconds($waitMs)
    do {
        if ($null -eq $script:receiveTask) {
            $segment = New-Object 'System.ArraySegment[byte]' -ArgumentList @(,$script:buffer)
            $script:receiveTask = $script:socket.ReceiveAsync($segment, [Threading.CancellationToken]::None)
        }
        $remaining = [Math]::Max(1, [int]($until - [DateTime]::UtcNow).TotalMilliseconds)
        if (-not $script:receiveTask.Wait($remaining)) { return $null }
        $part = $script:receiveTask.GetAwaiter().GetResult(); $script:receiveTask = $null
        if ($part.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'O Mint encerrou a conexao de diagnostico.' }
        $script:partial.Write($script:buffer, 0, $part.Count)
        if ($script:partial.Length -gt 4194304) { throw 'Resposta de diagnostico grande demais; coleta interrompida.' }
        if ($part.EndOfMessage) {
            $json = [Text.Encoding]::UTF8.GetString($script:partial.ToArray()); $script:partial.SetLength(0)
            return ($json | ConvertFrom-Json)
        }
    } while ([DateTime]::UtcNow -lt $until)
    return $null
}
function Process-Event($message) {
    $p = $message.params
    switch ($message.method) {
        'Runtime.exceptionThrown' {
            $script:jsErrors++; $detail = $p.exceptionDetails
            $description = if ($detail.exception.description) { $detail.exception.description } else { $detail.text }
            Write-Log ('ERRO JS: ' + (Safe-Text $description))
        }
        'Log.entryAdded' {
            if ($p.entry.level -eq 'error') { Write-Log ('LOG ERRO: ' + (Safe-Text $p.entry.text)) }
        }
        'Network.requestWillBeSent' { $script:requests[$p.requestId] = Get-HostOnly $p.request.url }
        'Network.responseReceived' {
            if ([int]$p.response.status -ge 400) {
                $script:networkErrors++; Write-Log ('HTTP ' + $p.response.status + ': ' + (Get-HostOnly $p.response.url))
            }
        }
        'Network.loadingFailed' {
            $script:networkErrors++; $hostName = $script:requests[$p.requestId]
            Write-Log ('REDE FALHOU: ' + $hostName + ' - ' + (Safe-Text $p.errorText) + ' (tipo: ' + $p.type + ')')
            $script:requests.Remove($p.requestId)
        }
        'Network.loadingFinished' { $script:requests.Remove($p.requestId) }
    }
}
function Command-Cdp([string]$method, $parameters) {
    [int]$id = Send-Cdp $method $parameters; $until = [DateTime]::UtcNow.AddSeconds(5)
    do {
        $message = Read-Cdp 250
        if ($null -ne $message) {
            if ($message.id -eq $id) {
                if ($message.error) { throw ('CDP ' + $method + ': ' + (Safe-Text $message.error.message)) }
                return $message.result
            }
            Process-Event $message
        }
    } while ([DateTime]::UtcNow -lt $until)
    throw ('Sem resposta do Mint ao comando ' + $method)
}
try {
    Write-Log 'Diagnostico local. Nao coleta cookies, cabecalhos, armazenamento nem corpos de requisicoes.'
    Write-Log 'Feche o Mint antes de executar. Nao faca login nem jogue durante os 25 segundos da coleta.'
    if (-not $ExePath) {
        $exe = Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'Mint*.exe' | Where-Object { -not $_.PSIsContainer } |
            Sort-Object @{Expression={if ($_.Name -match '(?i)v24') {0} elseif ($_.Name -match '(?i)v23') {1} else {2}}}, Name | Select-Object -First 1
        if ($null -eq $exe) { throw 'EXE nao encontrado. Coloque estes dois scripts na mesma pasta do Mint V24 ou V23.' }
        $ExePath = $exe.FullName
    }
    $ExePath = (Resolve-Path -LiteralPath $ExePath).Path
    $running = @(Get-Process | Where-Object { $_.ProcessName -like 'Mint-Browser*' -or $_.ProcessName -eq 'MintBrowser' })
    if ($running.Count -gt 0) { throw 'O Mint ja esta aberto. Feche todas as janelas e execute este diagnostico novamente.' }
    $listeners = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if (@($listeners | Where-Object { $_.Port -eq $port }).Count -gt 0) { throw ('A porta local ' + $port + ' esta ocupada. Feche o programa que a utiliza e tente novamente. Nenhum processo foi encerrado.') }
    Write-Log ('Executavel: ' + [IO.Path]::GetFileName($ExePath))
    $previousArguments = $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
    try {
        $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = ($previousArguments + ' --remote-debugging-port=' + $port + ' --remote-debugging-address=127.0.0.1').Trim()
        Start-Process -FilePath $ExePath -WorkingDirectory ([IO.Path]::GetDirectoryName($ExePath)) | Out-Null
    } finally { $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $previousArguments }
    Write-Log 'Aguardando a aba 888pg.cc. Conclua apenas o aviso inicial do Mint, se aparecer.'
    $target = $null; $until = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $targets = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/json/list') -TimeoutSec 2
            $target = $targets | Where-Object { $_.type -eq 'page' -and (Get-HostOnly $_.url) -match '(^|\.)888pg\.cc$' } | Select-Object -First 1
        } catch { }
        if ($null -eq $target) { Start-Sleep -Milliseconds 500 }
    } while ($null -eq $target -and [DateTime]::UtcNow -lt $until)
    if ($null -eq $target) { throw 'Nenhuma aba 888pg.cc foi encontrada em 60 segundos. Confirme que o Mint abriu o site e execute novamente com todas as janelas do Mint fechadas.' }
    $wsUri = [uri]$target.webSocketDebuggerUrl
    if ($wsUri.Scheme -ne 'ws' -or $wsUri.Host -notin @('127.0.0.1','localhost','[::1]','::1') -or $wsUri.Port -ne $port) { throw 'O endereco de diagnostico retornado nao e o loopback esperado.' }
    $script:socket = New-Object Net.WebSockets.ClientWebSocket
    $connectTimeout = New-Object Threading.CancellationTokenSource
    $connectTimeout.CancelAfter(5000)
    try { [void]$script:socket.ConnectAsync($wsUri, $connectTimeout.Token).GetAwaiter().GetResult() } finally { $connectTimeout.Dispose() }
    $null = Command-Cdp 'Runtime.enable' @{}
    $null = Command-Cdp 'Log.enable' @{}
    $null = Command-Cdp 'Network.enable' @{}
    $null = Command-Cdp 'Page.enable' @{}
    Write-Log 'Captura ativa; recarregando somente a aba 888pg.cc e observando por 25 segundos.'
    $null = Command-Cdp 'Page.reload' @{ignoreCache=$false}
    $until = [DateTime]::UtcNow.AddSeconds(25)
    while ([DateTime]::UtcNow -lt $until) { $message = Read-Cdp 250; if ($null -ne $message) { Process-Event $message } }
    $expression = @'
(()=>{let r={readyState:document.readyState};for(let n of ['jsBridge','__mintAdblockBridge']){let b=window[n];r[n]={present:!!b,methods:b?Object.getOwnPropertyNames(b).filter(k=>typeof b[k]==='function'):[]}}let l=window.LOBBY_UTILS;r.LOBBY_UTILS={present:!!l};if(l)for(let k of ['isAppEnv','isVestEnv']){let v=l[k];r.LOBBY_UTILS[k]=(typeof v==='boolean'||typeof v==='number')?v:typeof v}return r})()
'@
    $snapshot = Command-Cdp 'Runtime.evaluate' @{expression=$expression; returnByValue=$true}
    if ($snapshot.exceptionDetails) { Write-Log 'Nao foi possivel ler os indicadores JS.' }
    else { Write-Log ('INDICADORES: ' + ($snapshot.result.value | ConvertTo-Json -Depth 6 -Compress)) }
    Write-Log ('Coleta concluida. Excecoes JS: ' + $script:jsErrors + '; falhas HTTP/rede: ' + $script:networkErrors + '.')
    Write-Log 'Se nao houve erro, o log nao comprova que o site concluiu a inicializacao.'
    Write-Log 'Feche o Mint agora para encerrar a porta de diagnostico local.'
} catch {
    Write-Log ('DIAGNOSTICO INTERROMPIDO: ' + (Safe-Text $_.Exception.Message))
    Write-Log 'Feche o Mint antes de tentar novamente.'
    $exitCode = 1
} finally {
    if ($null -ne $script:socket) { $script:socket.Abort(); $script:socket.Dispose() }
    $script:partial.Dispose(); $writer.Dispose()
    Write-Host ('Log salvo em: ' + $log)
}
exit $exitCode
