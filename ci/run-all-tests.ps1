[CmdletBinding()]
param(
    [string]$PythonPath = (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    [string]$EvidencePath = "",
    [int]$ExpectedPesterSkipCount = 0,
    [int]$ExpectedPythonSkipCount = 4
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path $PSScriptRoot\..).Path
$EvidencePath = if ($EvidencePath) { [IO.Path]::GetFullPath($EvidencePath) } else { Join-Path $repoRoot "artifacts\test-evidence.json" }
$evidenceRoot = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$records = @()
$overallExit = 0

function Invoke-ChildRunner {
    param([string]$ScriptPath, [hashtable]$Arguments, [string]$Name)
    $output = @()
    $exitCode = 1
    $failure = $null
    try {
        $output = @(& $ScriptPath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    } catch {
        $failure = $_.Exception.Message
        $exitCode = 1
    }
    $jsonLine = @($output | Where-Object { $_ -is [string] -and $_ -match '^\s*\{' } | Select-Object -Last 1)
    $summary = if ($jsonLine) { try { $jsonLine | ConvertFrom-Json } catch { $null } } else { $null }
    if (-not $summary) {
        $summary = [ordered]@{ runner = $Name; operationalFailure = $true; message = if ($failure) { $failure } else { "runner did not emit a JSON summary" } }
    }
    [pscustomobject]@{ runner = $Name; exitCode = $exitCode; counts = $summary }
}

$pythonResult = Invoke-ChildRunner -Name "python" -ScriptPath (Join-Path $PSScriptRoot "run-python-tests.ps1") -Arguments @{ PythonPath = $PythonPath; ExpectedSkipCount = $ExpectedPythonSkipCount }
$records += $pythonResult
$overallExit = [Math]::Max($overallExit, [int]$pythonResult.exitCode)

$pesterPaths = @(
    "tests\InstallerContract.Tests.ps1",
    "tests\PythonRuntimeContract.Tests.ps1",
    "tests\SecretScan.Tests.ps1",
    "tests\TestRunnerContract.Tests.ps1"
) | ForEach-Object { Join-Path $repoRoot $_ }
$pesterResult = Invoke-ChildRunner -Name "pester" -ScriptPath (Join-Path $PSScriptRoot "run-pester-tests.ps1") -Arguments @{ Path = $pesterPaths; ExpectedSkipCount = $ExpectedPesterSkipCount }
$records += $pesterResult
$overallExit = [Math]::Max($overallExit, [int]$pesterResult.exitCode)

$evidence = [ordered]@{ schemaVersion = 1; successful = ($overallExit -eq 0); results = $records }
try { $evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8 } catch { $overallExit = 1; throw }
if ($overallExit -ne 0) { exit 1 }
exit 0
