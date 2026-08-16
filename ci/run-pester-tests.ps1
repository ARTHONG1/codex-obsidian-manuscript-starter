[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Path,
    [int]$ExpectedSkipCount = 0
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path $PSScriptRoot\..).Path
$expandedPaths = @()
foreach ($entry in $Path) {
    $subPaths = @($entry -split "," | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() })
    foreach ($p in $subPaths) {
        $full = if (Test-Path -LiteralPath $p) { (Resolve-Path -LiteralPath $p).Path } else { Join-Path $repoRoot $p }
        if (Test-Path -LiteralPath $full) {
            $item = Get-Item -LiteralPath $full
            if ($item.PSIsContainer) {
                $expandedPaths += Get-ChildItem -LiteralPath $item.FullName -Filter "*.Tests.ps1" -File | Select-Object -ExpandProperty FullName
            } else {
                $expandedPaths += $item.FullName
            }
        } else {
            $expandedPaths += $p
        }
    }
}

Import-Module Pester -RequiredVersion 3.4.0
$result = Invoke-Pester -Script $expandedPaths -PassThru
$summary = [ordered]@{
    TotalCount = [int]$result.TotalCount
    PassedCount = [int]$result.PassedCount
    FailedCount = [int]$result.FailedCount
    SkippedCount = [int]$result.SkippedCount
    PendingCount = [int]$result.PendingCount
    InconclusiveCount = [int]$result.InconclusiveCount
    Successful = ([int]$result.FailedCount -eq 0 -and [int]$result.PendingCount -eq 0 -and [int]$result.InconclusiveCount -eq 0 -and [int]$result.SkippedCount -eq $ExpectedSkipCount)
}
$summary | ConvertTo-Json -Compress
if (-not $summary.Successful) {
    exit 1
}
exit 0

