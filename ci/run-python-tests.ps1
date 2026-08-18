[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,
    [string[]]$TestName = @(),
    [string]$TestRoot = "",
    [int]$ExpectedSkipCount = 0
)

$ErrorActionPreference = "Stop"
if (-not $TestRoot) { $TestRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$root = (Resolve-Path -LiteralPath $TestRoot).Path
$runner = Join-Path $PSScriptRoot "run_unittest.py"

$version = & $PythonPath -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne "3.12") {
    throw "Python 3.12 is required; received '$($version.Trim())'."
}

$arguments = @($runner, "--root", $root)
foreach ($name in $TestName) { $arguments += @("--test-name", $name) }
$stdoutPath = Join-Path ([IO.Path]::GetTempPath()) ("python-tests-" + [guid]::NewGuid().ToString("N") + ".out")
$stderrPath = Join-Path ([IO.Path]::GetTempPath()) ("python-tests-" + [guid]::NewGuid().ToString("N") + ".err")
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $PythonPath @arguments 1> $stdoutPath 2> $stderrPath
$ErrorActionPreference = $previousErrorAction
$exitCode = $LASTEXITCODE
$summaryLine = @(Get-Content -LiteralPath $stdoutPath | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1)
if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath | Write-Output }
Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
if (-not $summaryLine) { throw "Python runner did not emit a JSON summary." }

$summary = $summaryLine | ConvertFrom-Json
if ($null -eq $summary.testsRun -or $null -eq $summary.failures -or $null -eq $summary.errors -or $null -eq $summary.skipped -or $null -eq $summary.successful) {
    throw "Python runner summary is missing required counts."
}
$summary.successful = ($summary.failures -eq 0 -and $summary.errors -eq 0 -and $summary.skipped -eq $ExpectedSkipCount)
$summary | ConvertTo-Json -Compress
if ($summary.failures -ne 0 -or $summary.errors -ne 0 -or $summary.skipped -ne $ExpectedSkipCount -or -not $summary.successful) {
    exit 1
}
if ($exitCode -ne 0) { exit 1 }
exit 0
