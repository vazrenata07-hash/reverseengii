param([string]$ExePath)
$ErrorActionPreference = 'Stop'
$port = 19288; $exitCode = 0; $writer = $null; $script:stage = 'preparacao'
$script:socket = $null; $script:receiveTask = $null; $script:sequence = 0
$script:buffer = New-Object byte[] 65536; $script:partial = New-Object IO.MemoryStream
$script:requests = @{}
function Write-Log([string]$message) {
    $writer.WriteLine(('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $message)); $writer.Flush()
    Write-Host $message
}
function Get-SdkHost([string]$url) {
    try {
        $u = [uri]$url
        if ($u.Scheme -notin @('http','https')) { return $null }
        if (($u.Host -match '(^|\.)888pg\.cc$' -and $u.AbsolutePath -ceq '/libs/rc/gt@5/gt.js') -or
            $u.Host -match '(^|\.)(geetest|geeguard)\.com$') { return $u.Host.ToLowerInvariant() }
    } catch { }
    return $null
}
function Get-NetError([string]$text) {
    $m = [regex]::Match($text, '\bnet::ERR_[A-Z0-9_]+\b')
    if ($m.Success) { return $m.Value }; return 'erro-rede-sem-codigo'
}
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
        if ($part.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'Conexao encerrada.' }
        $script:partial.Write($script:buffer, 0, $part.Count)
        if ($script:partial.Length -gt 8388608) { throw 'Limite de mensagem.' }
        if ($part.EndOfMessage) {
            $json = [Text.Encoding]::UTF8.GetString($script:partial.ToArray()); $script:partial.SetLength(0)
            return ($json | ConvertFrom-Json)
        }
    } while ([DateTime]::UtcNow -lt $until)
    return $null
}
function Finish-Request($p, [string]$outcome) {
    $r = $script:requests[$p.requestId]; if (-not $r) { return }
    $elapsed = [Math]::Max(0, [Math]::Round(1000 * ([double]$p.timestamp - $r.start)))
    Write-Log ('SDK host=' + $r.hostName + '; http=' + $r.status + '; ms=' + $elapsed + '; resultado=' + $outcome)
    $script:requests.Remove($p.requestId)
}
function Process-Event($message) {
    $p = $message.params
    switch ($message.method) {
        'Network.requestWillBeSent' {
            $hostName = Get-SdkHost $p.request.url
            $script:requests.Remove($p.requestId)
            if ($hostName) { $script:requests[$p.requestId] = @{hostName=$hostName; start=[double]$p.timestamp; status=0} }
        }
        'Network.responseReceived' {
            if ($script:requests.ContainsKey($p.requestId)) { $script:requests[$p.requestId].status = [int]$p.response.status }
        }
        'Network.loadingFinished' { Finish-Request $p 'concluido' }
        'Network.loadingFailed' { Finish-Request $p (Get-NetError $p.errorText) }
        'Runtime.exceptionThrown' {
            $d = $p.exceptionDetails; $hostName = Get-SdkHost $d.url
            if (-not $hostName -and $d.stackTrace.callFrames.Count -gt 0) { $hostName = Get-SdkHost $d.stackTrace.callFrames[0].url }
            if ($hostName) {
                $kind = [string]$d.exception.className
                if ($kind -notin @('Error','ReferenceError','TypeError','RangeError','SyntaxError','EvalError','URIError','AggregateError','DOMException')) { $kind = 'CustomError' }
                Write-Log ('EXCECAO SDK host=' + $hostName + '; classe=' + $kind)
            }
        }
        'Log.entryAdded' {
            $hostName = Get-SdkHost $p.entry.url
            if ($hostName -and $p.entry.level -eq 'error') {
                $code = Get-NetError $p.entry.text
                if ($code -ne 'erro-rede-sem-codigo') { Write-Log ('LOG SDK host=' + $hostName + '; codigo=' + $code) }
            }
        }
    }
}
function Command-Cdp([string]$method, $parameters, [int]$TimeoutMs=5000) {
    [int]$id = Send-Cdp $method $parameters; $until = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs)
    do {
        $message = Read-Cdp 250
        if ($null -ne $message) {
            if ($message.id -eq $id) {
                if ($message.error) { throw 'Comando CDP recusado.' }; return $message.result
            }
            Process-Event $message
        }
    } while ([DateTime]::UtcNow -lt $until)
    throw 'Comando CDP sem resposta.'
}
function Write-Snapshot([string]$label) {
    $expression = @'
(()=>({initGeeGuard:typeof window.initGeeGuard==='function',documentComplete:document.readyState==='complete',documentInteractive:document.readyState==='interactive',online:navigator.onLine===true,secureContext:window.isSecureContext===true,cryptoSubtle:typeof crypto!=='undefined'&&!!crypto.subtle,worker:typeof Worker==='function',gt5Script:Array.from(document.scripts).some(s=>{try{return new URL(s.src,location.href).pathname==='/libs/rc/gt@5/gt.js'}catch{return false}})}))()
'@
    $answer = Command-Cdp 'Runtime.evaluate' @{expression=$expression; returnByValue=$true}
    if ($answer.exceptionDetails) { Write-Log ('INDICADORES ' + $label + ': indisponiveis'); return }
    foreach ($key in @('initGeeGuard','documentComplete','documentInteractive','online','secureContext','cryptoSubtle','worker','gt5Script')) {
        $value = $answer.result.value.$key
        if ($value -is [bool]) { Write-Log ('INDICADOR ' + $label + ' ' + $key + '=' + $value) }
    }
}
try {
    if (-not $ExePath) {
        $exe = Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'Mint-Browser-Windows-v*.exe' | Where-Object { -not $_.PSIsContainer -and $_.Name -match '^Mint-Browser-Windows-v\d+(?:[-_. ]|$)' } |
            Sort-Object @{Expression={if ($_.Name -match '(?i)(?:^|[-_ ])v(\d+)(?:[-_. ]|$)') {[int]$Matches[1]} else {0}}; Descending=$true}, Name | Select-Object -First 1
        if ($null -eq $exe) { Write-Host 'EXE ausente. Coloque BAT e PS1 na pasta do Mint V25 (ou versao mais recente).'; exit 1 }
        $ExePath = $exe.FullName
    }
    $ExePath = (Resolve-Path -LiteralPath $ExePath).Path
    $running = @(Get-Process | Where-Object { $_.ProcessName -like 'Mint-Browser*' -or $_.ProcessName -eq 'MintBrowser' })
    if ($running.Count -gt 0) { Write-Host 'Feche todas as janelas do Mint e execute novamente. Nenhuma coleta foi iniciada.'; exit 1 }
    $listeners = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if (@($listeners | Where-Object { $_.Port -eq $port }).Count -gt 0) { Write-Host 'Porta local 19288 ocupada. Feche o diagnostico anterior. Nenhum processo foi encerrado.'; exit 1 }
    $log = Join-Path $PSScriptRoot ('mint-sdk-cadastro-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.txt')
    $writer = New-Object IO.StreamWriter($log, $false, (New-Object Text.UTF8Encoding($true)))
    Write-Log 'Diagnostico SDK cadastro v1. Observacao local, sem recarga ou envio de formulario.'
    Write-Log 'Nao grava corpos, cabecalhos, cookies, armazenamento, tokens, identificadores ou console.'
    Write-Log 'Indicador SDK ausente pode significar que o formulario ainda nao o solicitou; nao comprova falha.'
    Write-Log ('Executavel: ' + [IO.Path]::GetFileName($ExePath))
    $script:stage = 'abertura do Mint'; $previousArguments = $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
    try {
        $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = ($previousArguments + ' --remote-debugging-port=' + $port + ' --remote-debugging-address=127.0.0.1').Trim()
        Start-Process -FilePath $ExePath -WorkingDirectory ([IO.Path]::GetDirectoryName($ExePath)) | Out-Null
    } finally { $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $previousArguments }
    Write-Log 'Aguardando a aba 888pg.cc. Conclua apenas o aviso inicial do Mint, se houver.'
    $script:stage = 'localizacao da aba'; $target = $null; $until = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $targets = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/json/list') -TimeoutSec 2
            $target = $targets | Where-Object { $_.type -eq 'page' -and ([uri]$_.url).Host -match '(^|\.)888pg\.cc$' } | Select-Object -First 1
        } catch { }
        if ($null -eq $target) { Start-Sleep -Milliseconds 500 }
    } while ($null -eq $target -and [DateTime]::UtcNow -lt $until)
    if ($null -eq $target) { throw 'Aba ausente.' }
    $script:stage = 'conexao local'; $wsUri = [uri]$target.webSocketDebuggerUrl
    if ($wsUri.Scheme -ne 'ws' -or $wsUri.Host -notin @('127.0.0.1','localhost','[::1]','::1') -or $wsUri.Port -ne $port) { throw 'Endereco local inesperado.' }
    $script:socket = New-Object Net.WebSockets.ClientWebSocket; $cancel = New-Object Threading.CancellationTokenSource
    $cancel.CancelAfter(5000)
    try { [void]$script:socket.ConnectAsync($wsUri, $cancel.Token).GetAwaiter().GetResult() } finally { $cancel.Dispose() }
    $script:stage = 'ativacao da observacao'
    $null = Command-Cdp 'Runtime.enable' @{}; $null = Command-Cdp 'Log.enable' @{}; $null = Command-Cdp 'Network.enable' @{}
    Write-Snapshot 'inicial'
    Write-Log 'CAPTURA ATIVA: abra somente o formulario de cadastro. Nao preencha, nao envie e nao crie conta.'
    Write-Log 'Aguardando 60 segundos. Nao recarregue a pagina. O SDK pode ja estar carregado antes da observacao.'
    $script:stage = 'observacao'; $until = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $until) { $message = Read-Cdp 250; if ($null -ne $message) { Process-Event $message } }
    Write-Snapshot 'final'
    Write-Log ('Recursos SDK ainda pendentes: ' + $script:requests.Count)
    Write-Log 'Concluido. Ausencia de falha do SDK nao explica nem libera uma rejeicao do servidor.'
    Write-Log 'Feche o Mint para encerrar a porta de diagnostico local.'
} catch {
    $exitCode = 1
    $message = 'Diagnostico interrompido durante ' + $script:stage + '. Feche o Mint e confira se os scripts estao junto do EXE.'
    if ($writer) { Write-Log $message } else { Write-Host $message }
} finally {
    if ($null -ne $script:socket) { $script:socket.Abort(); $script:socket.Dispose() }
    $script:partial.Dispose()
    if ($writer) { $writer.Dispose(); Write-Host ('TXT salvo em: ' + $log) }
}
exit $exitCode
