param([string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path)
$ErrorActionPreference = 'Stop'
$collector = Join-Path $RepositoryRoot 'diagnostico/cliente-h5-windows/diagnosticar-cliente-h5.ps1'
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($collector, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
foreach ($name in @('Source-Info', 'Collect-SourceContexts', 'Safe-Text')) {
    $definition = $ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name}, $true)
    if ($null -eq $definition) { throw ('Missing function: ' + $name) }
    Invoke-Expression $definition.Extent.Text
}
function Assert-True($condition, [string]$message) { if (-not $condition) { throw $message } }
function Write-Log([string]$message) { [void]$script:messages.Add($message) }
function Command-Cdp([string]$method, $parameters, [int]$TimeoutMs) {
    Assert-True ($method -eq 'Debugger.getScriptSource') 'Unexpected CDP command'
    [void]$script:reads.Add([string]$parameters.scriptId)
    return @{scriptSource=$script:bodies[[string]$parameters.scriptId]}
}
function Reset-Collection {
    Get-ChildItem -LiteralPath $sourceDir -File | Remove-Item -Force
    $script:scripts = @{}; $script:bodies = @{}; $script:epoch = 1
    $script:messages = [Collections.Generic.List[string]]::new()
    $script:reads = [Collections.Generic.List[string]]::new()
}
function Add-Source([string]$id, [string]$url, [string]$body, [int]$length = -1) {
    if ($length -lt 0) { $length = $body.Length }
    $parsed = [pscustomobject]@{scriptId=$id; url=$url; length=$length; startLine=0; hasSourceURL=$false; isLiveEdit=$false; scriptLanguage='JavaScript'}
    $info = Source-Info $parsed
    Assert-True ($null -ne $info) ('Fixture unexpectedly rejected: ' + $url)
    $script:scripts[$id] = $info; $script:bodies[$id] = $body
}
$sourceDir = Join-Path ([IO.Path]::GetTempPath()) ('mint-h5-source-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $sourceDir
try {
    Reset-Collection
    for ($i = 0; $i -lt 55; $i++) { Add-Source ([string]($i+1)) ('https://888pg.cc/assets/theme-0/helper' + $i.ToString('00') + '.js') 'const helper = 1;' }
    for ($i = 0; $i -lt 5; $i++) { Add-Source ([string](60+$i)) 'https://888pg.cc/' ('/* inline */' + ('i' * 4096)) }
    Add-Source '800' 'https://888pg.cc/assets/vendors/vendor-stable.BSTfaEwj.js' 'const vendor = 1;'
    $common = '/* isAppEnv Vest */' + ('c' * 7340032)
    $entry = '/* login contract */' + ('e' * 4194304)
    Add-Source '100' 'https://888pg.cc/assets/theme-0/commonChunk.EZ6HNUYg.js?old=1' $common
    Add-Source '300' 'https://888pg.cc/assets/theme-0/commonChunk.EZ6HNUYg.js?old=2' $common
    Add-Source '900' 'https://888PG.CC/assets/theme-0/commonChunk.EZ6HNUYg.js?current=1' $common
    Add-Source '901' 'https://888pg.cc/assets/theme-0/0_EntryLoginRegisterChunk.D7_g9aJ6.js' $entry
    foreach ($fixture in @(@('910','1_MineChunk.test.js'), @('911','index.test.js'), @('912','main.test.js'), @('913','lobby.test.js'))) {
        Add-Source $fixture[0] ('https://888pg.cc/assets/theme-0/' + $fixture[1]) 'const core = 1;'
    }
    # Reject oversized metadata before reading, and verify the UTF-8 byte gate
    # separately when the CDP character count is smaller than eight MiB.
    Add-Source '999' 'https://888pg.cc/assets/theme-0/commonChunk.oversized.js' 'oversized metadata' 8388609
    $wide = ([string][char]0x754c) * 3000000
    Add-Source '998' 'https://888pg.cc/assets/theme-0/aaa-byte-oversized.js' $wide
    Collect-SourceContexts
    Assert-True ($script:reads.Count -eq 30) 'The 30-source limit changed'
    Assert-True ($script:reads[0] -eq '900' -and $script:reads[1] -eq '901') 'The current common/login chunks were not read first'
    Assert-True (-not $script:reads.Contains('100') -and -not $script:reads.Contains('300')) 'Duplicate common contexts consumed reads or budget'
    Assert-True (-not $script:reads.Contains('999')) 'A source larger than eight MiB was requested'
    Assert-True ($script:reads.Contains('998')) 'UTF-8 byte-limit fixture was not exercised'
    Assert-True (-not $script:reads.Contains('800')) 'Vendor displaced relevant site sources'
    $files = @(Get-ChildItem -LiteralPath $sourceDir -File)
    $commonFiles = @($files | Where-Object Name -like '*commonChunk.EZ6HNUYg.js')
    $entryFiles = @($files | Where-Object Name -like '*0_EntryLoginRegisterChunk.D7_g9aJ6.js')
    Assert-True ($commonFiles.Count -eq 1 -and $entryFiles.Count -eq 1) 'Required chunks were evicted or duplicated'
    Assert-True ($commonFiles[0].Length -eq [Text.Encoding]::UTF8.GetByteCount($common)) 'Common chunk was not saved whole'
    Assert-True ($entryFiles[0].Length -eq [Text.Encoding]::UTF8.GetByteCount($entry)) 'Login chunk was not saved whole'
    Assert-True (@($files | Where-Object Name -like '*oversized*').Count -eq 0) 'An oversized source was saved'
    foreach ($id in @('910','911','912','913')) { Assert-True ($script:reads.IndexOf($id) -lt $script:reads.IndexOf('1')) 'Other core chunks were not prioritized over helpers' }
    Write-Output 'PASS required large chunks first, latest external context once, helper cap, core priority, and eight-MiB limits'

    Reset-Collection
    $inline = '<script>window.jsBridge = {};/*' + ('x' * 4096) + '*/</script>'
    Add-Source '10' 'https://888pg.cc/' $inline
    Add-Source '11' 'https://888pg.cc/' $inline
    Add-Source '12' 'https://888pg.cc/assets/vendors/vendor.test.js' 'const vendor = 1;'
    Collect-SourceContexts
    Assert-True ($script:reads.Contains('10') -and $script:reads.Contains('11')) 'Distinct inline scripts were deduplicated'
    Assert-True ($script:reads[2] -eq '12') 'Vendor was not last'
    Assert-True (@(Get-ChildItem -LiteralPath $sourceDir -File).Count -eq 1) 'An inline document was saved whole'
    Assert-True (@($script:messages | Where-Object { $_ -like 'TRECHO:*' }).Count -eq 2) 'Inline excerpts were not collected'
    Assert-True (-not (($script:messages -join "`n").Contains($inline))) 'Full inline content leaked into the log'
    Write-Output 'PASS separate inline contexts, excerpts only, and vendors last'
} finally { Remove-Item -LiteralPath $sourceDir -Recurse -Force }
