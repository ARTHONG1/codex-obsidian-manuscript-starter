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
    $scenarioBootstrap = Join-Path $Root "bootstrap"
    Copy-Item -LiteralPath (Join-Path $repoRoot "bootstrap") -Destination $scenarioBootstrap -Recurse -Force
    $installer = Join-Path $scenarioBootstrap "install-windows.ps1"

    $fakePythonRuntime = @'
function Find-Python312 {
    if ($env:INSTALLER_SCENARIO -eq "python_absent") {
        return [pscustomobject]@{ Ready = $false; Reason = "python_not_found" }
    }
    [pscustomobject]@{ Ready = $true; Python = "fake-python.exe"; PythonVersion = if ($env:INSTALLER_SCENARIO -eq "python311_selected") { "3.11" } elseif ($env:INSTALLER_SCENARIO -eq "python313_selected") { "3.13" } else { "3.12" } }
}
function Install-Python312 { [pscustomobject]@{ Status = "python_installed" } }
function New-VerifiedManagedVenv {
    param([string]$BasePython, [string]$RuntimeRoot, [string]$RequirementsLockPath, [string]$ProbePath)
    $venvRoot = Join-Path $RuntimeRoot "venv"
    New-Item -ItemType Directory -Path (Join-Path $venvRoot "Scripts") -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $venvRoot "scenario.txt") -Value $env:INSTALLER_SCENARIO -Encoding UTF8
    [pscustomobject]@{ Ready = $true; BasePython = $BasePython; Python = (Join-Path $venvRoot "Scripts\python.exe"); VenvRoot = $venvRoot; RequirementsHash = ("a" * 64); Reused = ($env:INSTALLER_SCENARIO -eq "venv_reuse"); Backup = $null }
}
function Test-ManagedPythonRuntime { param([string]$PythonPath, [string]$RequirementsHash, [string]$ProbePath); [pscustomobject]@{ Ready = $true; Reason = "ready"; Python = $PythonPath; RequirementsHash = $RequirementsHash } }
Export-ModuleMember -Function Find-Python312, Install-Python312, New-VerifiedManagedVenv, Test-ManagedPythonRuntime
'@
    Set-Content -LiteralPath (Join-Path $scenarioBootstrap "lib\PythonRuntime.psm1") -Value $fakePythonRuntime -Encoding UTF8

    $fakeRest = @'
function Install-PinnedLocalRestPlugin { [pscustomobject]@{ PluginId = "scenario-rest"; Version = "1.0.0" } }
function Test-PinnedLocalRestPluginInstallation { [pscustomobject]@{ Ready = $true } }
function Wait-ForLocalRest { [pscustomobject]@{ Status = "ready" } }
function Test-LocalRestRoundTrip { [pscustomobject]@{ Status = "ready"; Port = 27124 } }
Export-ModuleMember -Function Install-PinnedLocalRestPlugin, Test-PinnedLocalRestPluginInstallation, Wait-ForLocalRest, Test-LocalRestRoundTrip
'@
    Set-Content -LiteralPath (Join-Path $scenarioBootstrap "lib\LocalRest.psm1") -Value $fakeRest -Encoding UTF8

    if ($Scenario -eq "restart_resume") {
        New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
        [ordered]@{ stage = "venv_ready" } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot "install-stage.json") -Encoding UTF8
    }

    # The scenario is deliberately an orchestration concern. Production install-windows.ps1
    # has no -Scenario parameter; this runner supplies isolated roots and invokes its real API.
    & $installer -RuntimeRoot $runtimeRoot -VaultPath $vaultPath -PublicationRoot $publicationRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    if (-not $rootWasSupplied) {
        Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:INSTALLER_SCENARIO -ErrorAction SilentlyContinue
}
