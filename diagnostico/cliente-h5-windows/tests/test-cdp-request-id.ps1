param([string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
public class RequestIdTestSocket {
    public string LastPayload;
    public bool CompleteSynchronously;
    public Task SendAsync(ArraySegment<byte> data, WebSocketMessageType type, bool end, CancellationToken token) {
        LastPayload = System.Text.Encoding.UTF8.GetString(data.Array, data.Offset, data.Count);
        return CompleteSynchronously ? Task.CompletedTask : Task.Delay(10);
    }
}
'@
$paths = @(
    'diagnostico/cliente-h5-windows/diagnosticar-cliente-h5.ps1',
    'src-windows-v24/diagnostico/diagnosticar-mint.ps1'
)
foreach ($relative in $paths) {
    $tokens = $null; $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $RepositoryRoot $relative), [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
    $function = $ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Send-Cdp'}, $true)
    if ($null -eq $function) { throw ('Missing Send-Cdp: ' + $relative) }
    Invoke-Expression $function.Extent.Text
    $script:sequence = 0
    $script:socket = New-Object RequestIdTestSocket
    foreach ($immediate in @($true, $false)) {
        $script:socket.CompleteSynchronously = $immediate
        $id = Send-Cdp 'Runtime.enable' @{}
        if (@($id).Count -ne 1 -or $id -isnot [int]) { throw ('CDP id polluted by async return value: ' + $relative) }
        $request = $script:socket.LastPayload | ConvertFrom-Json
        $response = [pscustomobject]@{ id = $request.id; result = @{} }
        if ($response.id -ne $id -or $request.method -ne 'Runtime.enable') { throw 'CDP response no longer matches its request' }
    }
    Write-Output ('PASS scalar request ID and matching response for immediate/delayed send: ' + $relative)
}
