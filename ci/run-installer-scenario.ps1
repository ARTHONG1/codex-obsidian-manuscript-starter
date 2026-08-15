[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("python311_selected", "python313_selected", "python_absent", "python312_ready", "restart_resume", "venv_reuse")]
    [string]$Scenario,
    [string]$Root
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$rootWasSupplied = -not [string]::IsNullOrWhiteSpace($Root)
if (-not $rootWasSupplied) {
    $Root = Join-Path ([IO.Path]::GetTempPath()) ("codex-installer-" + [guid]::NewGuid().ToString("N"))
}

New-Item -ItemType Directory -Path $Root -Force | Out-Null
$env:INSTALLER_SCENARIO = $Scenario
try {
    $runtimeRoot = Join-Path $Root "runtime"
    $vaultPath = Join-Path $Root "vault"
    $publicationRoot = Join-Path $Root "publication"
    $installer = Join-Path $repoRoot "bootstrap\install-windows.ps1"

    # The scenario is deliberately an orchestration concern. Production install-windows.ps1
    # has no -Scenario parameter; this runner supplies isolated roots and invokes its real API.
    & $installer -RuntimeRoot $runtimeRoot -VaultPath $vaultPath -PublicationRoot $publicationRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:INSTALLER_SCENARIO -ErrorAction SilentlyContinue
}
