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

$resultPath = Join-Path ([IO.Path]::GetTempPath()) ("pester-result-" + [guid]::NewGuid().ToString("N") + ".json")
$pathListPath = Join-Path ([IO.Path]::GetTempPath()) ("pester-paths-" + [guid]::NewGuid().ToString("N") + ".json")
try {
    @($expandedPaths) | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $pathListPath -Encoding UTF8
    $invokeScript = Join-Path $PSScriptRoot "invoke-pester-owned.ps1"
    & C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File $invokeScript `
        -ExpectedSkipCount $ExpectedSkipCount -ResultPath $resultPath -PathListPath $pathListPath 2>&1 | ForEach-Object { $_ }
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
    Remove-Item -LiteralPath $pathListPath -Force -ErrorAction SilentlyContinue
}

