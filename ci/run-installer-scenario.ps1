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
    $scenarioEvidence = Join-Path $Root "scenario-result.json"
    $env:SCENARIO_RESULT_PATH = $scenarioEvidence
    $scenarioBootstrap = Join-Path $Root "bootstrap"
    Copy-Item -LiteralPath (Join-Path $repoRoot "bootstrap") -Destination $scenarioBootstrap -Recurse -Force
    # These legacy contract scenarios replace Python/REST modules with fakes. Keep the
    # official-download path out of that fake harness so it never performs network I/O.
    Remove-Item -LiteralPath (Join-Path $scenarioBootstrap "lib\OfficialInstallers.psm1") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $scenarioBootstrap "official-installers.lock.json") -Force -ErrorAction SilentlyContinue
    $installer = Join-Path $scenarioBootstrap "install-windows.ps1"

    $fakePythonRuntime = @'
function Find-Python312 {
    if ($env:INSTALLER_SCENARIO -eq "python_absent") {
        return [pscustomobject]@{ Ready = $false; Reason = "python_not_found" }
    }
    if ($env:INSTALLER_SCENARIO -in @("python311_selected", "python313_selected")) {
        [ordered]@{ Status = "python_version_unsupported"; PythonVersion = if ($env:INSTALLER_SCENARIO -eq "python311_selected") { "3.11" } else { "3.13" } } | ConvertTo-Json | Set-Content -LiteralPath $env:SCENARIO_RESULT_PATH -Encoding UTF8
        return [pscustomobject]@{ Ready = $false; Reason = "python_version_unsupported"; PythonVersion = if ($env:INSTALLER_SCENARIO -eq "python311_selected") { "3.11" } else { "3.13" } }
    }
    [pscustomobject]@{ Ready = $true; Python = "fake-python.exe"; PythonVersion = if ($env:INSTALLER_SCENARIO -eq "python311_selected") { "3.11" } elseif ($env:INSTALLER_SCENARIO -eq "python313_selected") { "3.13" } else { "3.12" } }
}
function Install-Python312 { [pscustomobject]@{ Status = "python_installed" } }
function New-VerifiedManagedVenv {
    param([string]$BasePython, [string]$RuntimeRoot, [string]$RequirementsLockPath, [string]$ProbePath)
    $venvRoot = Join-Path $RuntimeRoot "venv"
    $marker = Join-Path $venvRoot "scenario.txt"
    $reused = Test-Path -LiteralPath $marker -PathType Leaf
    New-Item -ItemType Directory -Path (Join-Path $venvRoot "Scripts") -Force | Out-Null
    if (-not $reused) { Set-Content -LiteralPath $marker -Value $env:INSTALLER_SCENARIO -Encoding UTF8 }
    [ordered]@{ Status = "venv_ready"; Reused = $reused } | ConvertTo-Json | Set-Content -LiteralPath $env:SCENARIO_RESULT_PATH -Encoding UTF8
    [pscustomobject]@{ Ready = $true; BasePython = $BasePython; Python = (Join-Path $venvRoot "Scripts\python.exe"); VenvRoot = $venvRoot; RequirementsHash = ("a" * 64); Reused = $reused; Backup = $null }
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

    $preStage = $null
    if ($Scenario -eq "restart_resume") {
        New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
        [ordered]@{ stage = "venv_ready" } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot "install-stage.json") -Encoding UTF8
        $preStage = "venv_ready"
    }

    # The scenario is deliberately an orchestration concern. Production install-windows.ps1
    # has no -Scenario parameter; this runner supplies isolated roots and invokes its real API.
    if ($Scenario -eq "venv_reuse") {
        $venvMarker = Join-Path $runtimeRoot "venv\scenario.txt"
        New-Item -ItemType Directory -Path (Split-Path -Parent $venvMarker) -Force | Out-Null
        Set-Content -LiteralPath $venvMarker -Value "pre-existing" -Encoding UTF8
    }
    # Run the production entrypoint in a child PowerShell process so its early
    # return statuses remain observable to this scenario oracle.
    $result = & pwsh -NoProfile -File $installer -RuntimeRoot $runtimeRoot -VaultPath $vaultPath -PublicationRoot $publicationRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $stagePath = Join-Path $runtimeRoot "install-stage.json"
    $stage = if (Test-Path -LiteralPath $stagePath) { (Get-Content -Raw -LiteralPath $stagePath | ConvertFrom-Json).stage } else { $null }
    $evidence = if (Test-Path -LiteralPath $scenarioEvidence) { Get-Content -Raw -LiteralPath $scenarioEvidence | ConvertFrom-Json } else { $null }
    $resultObject = if ($result) {
        $lastResultLine = ($result | Where-Object { $_ -is [string] -and $_.Trim().StartsWith("{") } | Select-Object -Last 1)
        if ($lastResultLine) { $lastResultLine | ConvertFrom-Json } else { $result | Select-Object -Last 1 }
    } else { $null }
    [pscustomobject]@{
        Scenario = $Scenario
        Status = if ($resultObject -and $resultObject.Status) { $resultObject.Status } elseif ($Scenario -eq "python312_ready" -and $stage -eq "dependencies_ready") { "community_plugin_consent_required" } elseif ($Scenario -eq "restart_resume" -and $preStage -eq "venv_ready" -and $stage -eq "dependencies_ready") { "resumed_to_dependencies_ready" } elseif ($evidence) { $evidence.Status } else { "unknown" }
        Stage = $stage
        VenvReused = ($Scenario -eq "venv_reuse" -and $evidence -and $evidence.Reused -eq $true -and (Get-Content -Raw -LiteralPath (Join-Path $runtimeRoot "venv\scenario.txt")).Trim() -eq "pre-existing")
        RestartResumed = ($Scenario -eq "restart_resume" -and $preStage -eq "venv_ready" -and $stage -eq "dependencies_ready")
        CallerRootPreserved = $rootWasSupplied
    } | ConvertTo-Json -Compress
}
finally {
    if (-not $rootWasSupplied) {
        Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:INSTALLER_SCENARIO -ErrorAction SilentlyContinue
    Remove-Item Env:SCENARIO_RESULT_PATH -ErrorAction SilentlyContinue
}
