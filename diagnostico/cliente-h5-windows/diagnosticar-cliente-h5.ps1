param([string]$ExePath)
$ErrorActionPreference = 'Stop'
$exitCode = 0
$port = 19288
$bundle = Join-Path $PSScriptRoot ('mint-cliente-h5-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$sourceDir = Join-Path $bundle 'fontes'; $null = New-Item -ItemType Directory -Path $sourceDir
$log = Join-Path $bundle ([IO.Path]::GetFileName($bundle)+'.txt'); $zip = $bundle+'.zip'
$utf8 = New-Object System.Text.UTF8Encoding($true)
$writer = New-Object System.IO.StreamWriter($log, $false, $utf8)
$script:socket = $null; $script:receiveTask = $null; $script:sequence = 0
$script:buffer = New-Object byte[] 65536
$script:partial = New-Object System.IO.MemoryStream
$script:requests = @{}; $script:jsErrors = 0; $script:networkErrors = 0
$script:scripts = @{}; $script:epoch = 0
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
function Source-Info($p) {
    try {
        $u = [uri]$p.url
        if ($u.Scheme -notin @('http','https') -or $p.hasSourceURL -or $p.isLiveEdit -or $p.scriptLanguage -ne 'JavaScript') { return $null }
        $own = $u.Host -match '(^|\.)888pg\.cc$'; $root = $u.AbsolutePath -eq '/'
        if ($root -and (-not $own -or $u.Query -or $u.Fragment)) { return $null }
        if (-not $root -and $u.AbsolutePath -notmatch '(?i)\.m?js$') { return $null }
        $priority = if ($root) {0} elseif ($u.AbsolutePath -match '(?i)vendor|polyfill') {3} elseif ($own) {1} else {2}
        return @{id=$p.scriptId; url=($u.Host+$u.AbsolutePath); priority=$priority; length=$p.length; line=$p.startLine; external=(-not $root); name=[IO.Path]::GetFileName($u.AbsolutePath)}
    } catch { return $null }
}
function Send-Cdp([string]$method, $parameters) {
    $script:sequence++
    $payload = @{id=$script:sequence; method=$method; params=$parameters} | ConvertTo-Json -Depth 8 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $segment = New-Object 'System.ArraySegment[byte]' -ArgumentList @(,$bytes)
    $script:socket.SendAsync($segment, [Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    return $script:sequence
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
        if ($script:partial.Length -gt 12582912) { throw 'Resposta de diagnostico grande demais; coleta interrompida.' }
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
        'Runtime.executionContextsCleared' { $script:scripts.Clear(); $script:epoch++ }
        'Debugger.scriptParsed' { $info = Source-Info $p; if ($info) { $script:scripts[$p.scriptId] = $info } }
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
function Command-Cdp([string]$method, $parameters, [int]$TimeoutMs=5000) {
    $id = Send-Cdp $method $parameters; $until = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs)
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
function Collect-SourceContexts {
    $epoch = $script:epoch; $deadline = [DateTime]::UtcNow.AddSeconds(45); $total = 0; $reads = 0; $fragments = 0; $saved = 0
    $candidates = @($script:scripts.Values | Where-Object { $_.length -le 3145728 } | Sort-Object { $_.priority }, { $_.length } | Select-Object -First 30)
    Write-Log ('FONTES: candidatos=' + $script:scripts.Count + '; selecionados=' + $candidates.Count + '. Limites: 30 fontes, 3 MiB/fonte, 20 MiB total, 45 s, 80 trechos. Documentos inline: somente trechos.')
    foreach ($item in $candidates) {
        $remaining = [int]($deadline-[DateTime]::UtcNow).TotalMilliseconds
        if ($remaining -le 0 -or $total -ge 20971520) { break }
        if ($script:epoch -ne $epoch) { Write-Log 'O site navegou durante a coleta; interrompendo fontes. Refaca o teste.'; break }
        try { $answer = Command-Cdp 'Debugger.getScriptSource' @{scriptId=$item.id} ([Math]::Min(5000,$remaining)); $reads++ }
        catch { Write-Log ('FONTE INDISPONIVEL: ' + $item.url); continue }
        if ($script:epoch -ne $epoch) { Write-Log 'O contexto mudou; fonte descartada.'; break }
        $source = [string]$answer.scriptSource; $bytes = [Text.Encoding]::UTF8.GetByteCount($source)
        if ($bytes -gt 3145728 -or ($total+$bytes) -gt 20971520) { continue }; $total += $bytes
        if ($item.external) {
            $name = [regex]::Replace($item.name,'[^A-Za-z0-9._-]','_'); if ($name.Length -gt 80) { $name=$name.Substring(0,80) }
            $name = $reads.ToString('00')+'_'+$name; [IO.File]::WriteAllText((Join-Path $sourceDir $name),$source,(New-Object Text.UTF8Encoding($false)))
            $saved++; Write-Log ('ARQUIVO '+$name+' <= '+$item.url+' ('+$bytes+' bytes)')
        }
        $primary = '\bisAppEnv\b|\bisVestEnv\b|\bSpeedPackage\b|\bjsBridge\b|APP-Android|\bVest\b|Mint Browser|\bmiui\b|\bmint\.(?:getVersionName|getVersionCode)'
        $hits = @([regex]::Matches($source,$primary))
        if ($hits.Count -gt 0) { $hits += @([regex]::Matches($source,'\bclientType\b|\bappType\b')) }
        elseif ($item.priority -le 1 -and $item.url -match '(?i)(index|main|lobby|commonchunk)') { $hits = @([regex]::Matches($source,'\bclientType\b|\bappType\b')) }
        $lastEnd = -1; $perScript = 0
        foreach ($hit in $hits) {
            if ($perScript -ge 6 -or $fragments -ge 80) { break }
            $start = [Math]::Max(0,$hit.Index-240); $end = [Math]::Min($source.Length,$hit.Index+720)
            if ($hit.Index -lt $lastEnd) { continue }; $lastEnd = $end
            $fragment = $source.Substring($start,$end-$start)
            $fragment = [regex]::Replace($fragment,'(?i)((?:["'']?(?:token|session|cookie|authorization|password|secret|userId|account)["'']?)\s*[:=]\s*)["''][^"'']*["'']','$1"[valor omitido]"')
            Write-Log ('FONTE ' + $item.url + ' linha-base=' + (1+[int]$item.line) + ' pos=' + $hit.Index + ' identificador=' + $hit.Value)
            Write-Log ('TRECHO: ' + (Safe-Text $fragment)); $perScript++; $fragments++
        }
        $source = $null; $answer = $null
    }
    Write-Log ('Fontes lidas=' + $reads + '; arquivos JS externos=' + $saved + '; bytes aceitos=' + $total + '; trechos=' + $fragments + '. Ausencia de trecho nao comprova ausencia do mecanismo.')
}
try {
    Write-Log 'Diagnostico local: erros, indicadores, arquivos JS externos carregados e trechos inline. Nada e enviado.'
    Write-Log 'Nao le cookies, cabecalhos, armazenamento ou corpos de requisicoes; nao despeja heap/sessao e nao altera flags ou pontes.'
    Write-Log 'Feche o Mint antes. Nao faca login nem jogue durante a coleta (25 s + ate 45 s de fontes).'
    Write-Log 'O ZIP contem codigo JS do site e pode conter constantes/URLs do proprio codigo. Revise antes de compartilhar. HTML completo e scripts inline completos nao sao salvos.'
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
    try { $script:socket.ConnectAsync($wsUri, $connectTimeout.Token).GetAwaiter().GetResult() } finally { $connectTimeout.Dispose() }
    $null = Command-Cdp 'Runtime.enable' @{}
    $null = Command-Cdp 'Log.enable' @{}
    $null = Command-Cdp 'Network.enable' @{}
    $null = Command-Cdp 'Page.enable' @{}
    $null = Command-Cdp 'Debugger.enable' @{maxScriptsCacheSize=20971520}
    $null = Command-Cdp 'Debugger.setSkipAllPauses' @{skip=$true}
    Write-Log 'Captura ativa; recarregando somente a aba 888pg.cc e observando por 25 segundos.'
    $null = Command-Cdp 'Page.reload' @{ignoreCache=$false}
    $until = [DateTime]::UtcNow.AddSeconds(25)
    while ([DateTime]::UtcNow -lt $until) { $message = Read-Cdp 250; if ($null -ne $message) { Process-Event $message } }
    $expression = @'
(()=>{let r={readyState:document.readyState};for(let n of ['jsBridge','__mintAdblockBridge','miui','mint','SpeedPackage','Android']){let d=Object.getOwnPropertyDescriptor(window,n),b=d&&d.value;r[n]={present:!!d,kind:d&&('value'in d)?typeof b:'accessor-or-absent',methods:b?Object.getOwnPropertyNames(b).filter(k=>{let q=Object.getOwnPropertyDescriptor(b,k);return q&&typeof q.value==='function'}).slice(0,40):[]}}let d=Object.getOwnPropertyDescriptor(window,'LOBBY_UTILS'),l=d&&d.value;r.LOBBY_UTILS={present:!!d};if(l)for(let k of ['isAppEnv','isVestEnv']){let q=Object.getOwnPropertyDescriptor(l,k),v=q&&q.value;r.LOBBY_UTILS[k]=!q?'absent':!('value'in q)?'accessor':typeof v==='boolean'?v:typeof v==='function'?{kind:'function',source:Function.prototype.toString.call(v).slice(0,600)}:typeof v}return r})()
'@
    $snapshot = Command-Cdp 'Runtime.evaluate' @{expression=$expression; returnByValue=$true}
    if ($snapshot.exceptionDetails) { Write-Log 'Nao foi possivel ler os indicadores JS.' }
    else { foreach ($property in $snapshot.result.value.PSObject.Properties) { Write-Log ('INDICADOR '+$property.Name+': '+(Safe-Text ($property.Value | ConvertTo-Json -Depth 6 -Compress))) } }
    Collect-SourceContexts
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
    try { Add-Type -AssemblyName System.IO.Compression.FileSystem; [IO.Compression.ZipFile]::CreateFromDirectory($bundle,$zip); Write-Host ('ZIP salvo em: '+$zip) }
    catch { Write-Host ('Nao foi possivel criar o ZIP. Arquivos locais em: '+$bundle); $exitCode=1 }
}
exit $exitCode
