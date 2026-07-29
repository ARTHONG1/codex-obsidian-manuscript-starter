#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RuntimeConfigPath,
    [int]$TimeoutSeconds = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bootstrapRoot = Split-Path -Parent $PSCommandPath
Import-Module (Join-Path $bootstrapRoot "lib\Environment.psm1") -Force
Import-Module (Join-Path $bootstrapRoot "lib\LocalRest.psm1") -Force

$runtime = if ($RuntimeConfigPath) { Get-RuntimeConfig -RuntimeConfigPath $RuntimeConfigPath } else { Get-RuntimeConfig }
if (-not (Test-Path -LiteralPath $runtime.vaultPath -PathType Container)) { throw "Configured vault does not exist: $($runtime.vaultPath)" }
Wait-ForLocalRest -DataPath $runtime.restDataPath -TimeoutSeconds $TimeoutSeconds | Out-Null
$health = Test-LocalRestRoundTrip -DataPath $runtime.restDataPath
[pscustomobject]@{
    Status = $health.Status
    VaultPath = $runtime.vaultPath
    Port = $health.Port
    Checked = "create-read-delete temporary health note"
}
