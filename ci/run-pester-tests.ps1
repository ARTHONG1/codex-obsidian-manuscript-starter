[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Path,
    [int]$ExpectedSkipCount = 0
)

$ErrorActionPreference = "Stop"
$resultPath = Join-Path ([IO.Path]::GetTempPath()) ("pester-result-" + [guid]::NewGuid().ToString("N") + ".json")
try {
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        (Join-Path $PSScriptRoot "invoke-pester-owned.ps1"),
        "-ExpectedSkipCount", $ExpectedSkipCount, "-ResultPath", $resultPath
    )
    $arguments += @("-Path", ($Path -join ","))
    & C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe @arguments 2>&1 | ForEach-Object { $_ }
    $processExit = $LASTEXITCODE
    if (-not (Test-Path -LiteralPath $resultPath)) { throw "Pester runner did not write a result summary." }
    $summary = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
    foreach ($field in @("FailedCount", "SkippedCount", "PendingCount", "InconclusiveCount", "Successful")) {
        if ($null -eq $summary.$field) { throw "Pester summary is missing $field." }
    }
    $summary | ConvertTo-Json -Compress
    if ($summary.FailedCount -ne 0 -or $summary.PendingCount -ne 0 -or $summary.InconclusiveCount -ne 0 -or $summary.SkippedCount -ne $ExpectedSkipCount -or -not $summary.Successful) {
        exit 1
    }
    if ($processExit -ne 0) { exit 1 }
    exit 0
} finally {
    Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
}
