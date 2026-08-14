[CmdletBinding()]
param(
    [string]$PythonPath = (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    [string]$EvidencePath = (Join-Path (Get-Location) "artifacts\test-evidence.json"),
    [int]$ExpectedPesterSkipCount = 0,
    [int]$ExpectedPythonSkipCount = 0
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path $PSScriptRoot\..).Path
$evidenceRoot = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$records = @()

$pythonOutput = & (Join-Path $PSScriptRoot "run-python-tests.ps1") -PythonPath $PythonPath -ExpectedSkipCount $ExpectedPythonSkipCount 2>&1
$pythonExit = $LASTEXITCODE
$pythonSummary = @($pythonOutput | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1) | ConvertFrom-Json
$records += [ordered]@{ runner = "python"; command = "ci/run-python-tests.ps1 -PythonPath <python312> -ExpectedSkipCount $ExpectedPythonSkipCount"; exitCode = $pythonExit; counts = $pythonSummary }

$pesterPaths = @("tests\InstallerContract.Tests.ps1", "tests\PythonRuntimeContract.Tests.ps1", "tests\SecretScan.Tests.ps1") | ForEach-Object { Join-Path $repoRoot $_ }
$pesterOutput = & (Join-Path $PSScriptRoot "run-pester-tests.ps1") -Path $pesterPaths -ExpectedSkipCount $ExpectedPesterSkipCount 2>&1
$pesterExit = $LASTEXITCODE
$pesterSummary = @($pesterOutput | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1) | ConvertFrom-Json
$records += [ordered]@{ runner = "pester"; command = "ci/run-pester-tests.ps1 -Path tests/*.Tests.ps1 -ExpectedSkipCount $ExpectedPesterSkipCount"; exitCode = $pesterExit; counts = $pesterSummary }

[ordered]@{ commands = @($records | ForEach-Object { $_.command }); results = $records } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
if ($pythonExit -ne 0 -or $pesterExit -ne 0) { exit 1 }
exit 0
