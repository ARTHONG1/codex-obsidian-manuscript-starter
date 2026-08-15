[CmdletBinding()]
param(
    [string[]]$Path,
    [string]$PathListPath,
    [int]$ExpectedSkipCount = 0,
    [Parameter(Mandatory = $true)]
    [string]$ResultPath
)

$ErrorActionPreference = "Stop"
Import-Module Pester -RequiredVersion 3.4.0
if ($PathListPath -and (Test-Path -LiteralPath $PathListPath)) {
    $scriptPaths = Get-Content -Raw -LiteralPath $PathListPath -Encoding UTF8 | ConvertFrom-Json
} elseif ($Path) {
    $scriptPaths = @($Path | ForEach-Object { $_ -split "," } | Where-Object { $_ } | ForEach-Object { $_ })
} else {
    throw "No test paths provided to invoke-pester-owned."
}
$result = Invoke-Pester -Script $scriptPaths -PassThru
$summary = [ordered]@{
    TotalCount = [int]$result.TotalCount
    PassedCount = [int]$result.PassedCount
    FailedCount = [int]$result.FailedCount
    SkippedCount = [int]$result.SkippedCount
    PendingCount = [int]$result.PendingCount
    InconclusiveCount = [int]$result.InconclusiveCount
    Successful = ([int]$result.FailedCount -eq 0 -and [int]$result.PendingCount -eq 0 -and [int]$result.InconclusiveCount -eq 0 -and [int]$result.SkippedCount -eq $ExpectedSkipCount)
}
$summary | ConvertTo-Json -Compress | Set-Content -LiteralPath $ResultPath -Encoding UTF8
if (-not $summary.Successful) { exit 1 }
exit 0
