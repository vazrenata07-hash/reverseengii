param([Parameter(Mandatory=$true)][string]$Source)
$ErrorActionPreference = 'Stop'
$path = (Resolve-Path -LiteralPath $Source).Path
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
foreach($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)){Invoke-Expression $node.Extent.Text}
$writer=New-Object IO.StringWriter; $script:requests=@{}
$secret='SECRET_TOKEN_PASSWORD_DEVICE_ID'
function Event([string]$method,$p){Process-Event ([pscustomobject]@{method=$method;params=($p | ConvertTo-Json -Depth 12 | ConvertFrom-Json)})}
if((Get-SdkHost 'https://evil.com/libs/rc/gt@5/gt.js') -or (Get-SdkHost 'https://geetest.com.evil.com/x')){throw 'Allowlist too broad'}
if((Get-SdkHost 'https://888pg.cc/libs/rc/gt@5/gt.js?secret=x') -ne '888pg.cc'){throw 'First-party SDK absent'}
if((Get-SdkHost 'https://static.geetest.com/path') -ne 'static.geetest.com'){throw 'Allowed SDK host absent'}
Event 'Network.requestWillBeSent' @{requestId='secretCDPId';timestamp=1;request=@{url="https://static.geetest.com/$secret.js?token=$secret";headers=@{secret=$secret};postData=$secret}}
Event 'Network.responseReceived' @{requestId='secretCDPId';response=@{status=200;url="https://static.geetest.com/$secret";headers=@{secret=$secret}}}
Event 'Network.loadingFinished' @{requestId='secretCDPId';timestamp=1.125}
Event 'Network.requestWillBeSent' @{requestId='failed';timestamp=2;request=@{url="https://888pg.cc/libs/rc/gt@5/gt.js?token=$secret"}}
Event 'Network.loadingFailed' @{requestId='failed';timestamp=2.5;errorText="net::ERR_CONNECTION_RESET $secret"}
Event 'Runtime.consoleAPICalled' @{args=@(@{value=$secret})}
Event 'Runtime.exceptionThrown' @{exceptionDetails=@{url="https://static.geetest.com/$secret";text=$secret;exception=@{className=$secret;description=$secret}}}
Event 'Runtime.exceptionThrown' @{exceptionDetails=@{url="https://evil.com/$secret";text=$secret;exception=@{className='TypeError';description=$secret}}}
Event 'Log.entryAdded' @{entry=@{level='error';url="https://static.geetest.com/$secret";text="$secret net::ERR_NAME_NOT_RESOLVED token=$secret"}}
Event 'Log.entryAdded' @{entry=@{level='error';url="https://static.geetest.com/$secret";text=$secret}}
Event 'Log.entryAdded' @{entry=@{level='error';url='https://evil.com/sdk.js';text="net::ERR_FAILED $secret"}}
function Command-Cdp([string]$method,$parameters){
    if($method -ne 'Runtime.evaluate'){throw 'Unexpected snapshot method'}
    $script:snapshotExpression=$parameters.expression
    return [pscustomobject]@{result=[pscustomobject]@{value=[pscustomobject]@{initGeeGuard=$true;online=$false;gt5Script=$true;secret='SECRET_TOKEN_PASSWORD_DEVICE_ID';worker='SECRET_TOKEN_PASSWORD_DEVICE_ID'}}}
}
Write-Snapshot 'inicial'
$log=$writer.ToString()
if($log -match "$secret|secretCDPId|evil\.com|\?|/path|token=|description="){throw ('Sensitive content in log: '+$log)}
foreach($expected in @('http=200; ms=125; resultado=concluido','net::ERR_CONNECTION_RESET','classe=CustomError','net::ERR_NAME_NOT_RESOLVED','initGeeGuard=True','online=False','gt5Script=True')){if(-not $log.Contains($expected)){throw ('Expected status absent: '+$expected)}}
if($script:requests.Count){throw 'Finished request state retained'}
if($script:snapshotExpression -match 'initGeeGuard\s*\(|GEE_TOKEN|fetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|document\.cookie'){throw 'Snapshot invokes sensitive function or reads session'}
$methods=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Command-Cdp'},$true) | ForEach-Object {$_.CommandElements[1].Value} | Sort-Object -Unique)
if(($methods -join ',') -cne 'Log.enable,Network.enable,Runtime.enable,Runtime.evaluate'){throw ('Unexpected CDP operations: '+($methods -join ','))}
Add-Type -TypeDefinition @'
using System;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
public class PassiveDiagnosticSocket {
 public string LastPayload; public bool Immediate;
 public Task SendAsync(ArraySegment<byte> data, WebSocketMessageType type, bool end, CancellationToken token) {
  LastPayload=System.Text.Encoding.UTF8.GetString(data.Array,data.Offset,data.Count);
  return Immediate ? Task.CompletedTask : Task.Delay(10);
 }
}
'@
$script:sequence=0; $script:socket=New-Object PassiveDiagnosticSocket
foreach($immediate in @($true,$false)){
    $script:socket.Immediate=$immediate; $id=Send-Cdp 'Runtime.enable' @{}
    if(@($id).Count -ne 1 -or $id -isnot [int]){throw 'Request id polluted'}
    $sent=$script:socket.LastPayload | ConvertFrom-Json
    if($sent.id -ne $id -or $sent.method -ne 'Runtime.enable'){throw 'Request ID mismatch'}
}
'PASS syntax, allowlist, secret exclusion, enum-only errors, boolean-only snapshot, no active CDP operations, immediate/delayed transport request IDs'
