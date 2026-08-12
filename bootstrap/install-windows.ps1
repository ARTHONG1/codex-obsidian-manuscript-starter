#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$VaultPath,
    [string]$RuntimeRoot,
    [string]$PublicationRoot,
    [switch]$InstallObsidian,
    [switch]$EnableCommunityPlugin,
    [switch]$AllowExistingEmptyVault,
    [switch]$LaunchObsidian
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bootstrapRoot = Split-Path -Parent $PSCommandPath
Import-Module (Join-Path $bootstrapRoot "lib\Environment.psm1") -Force
Import-Module (Join-Path $bootstrapRoot "lib\Vault.psm1") -Force
Import-Module (Join-Path $bootstrapRoot "lib\LocalRest.psm1") -Force
Import-Module (Join-Path $bootstrapRoot "lib\PublicationLibrary.psm1") -Force

$paths = Resolve-InstallPaths -VaultPath $VaultPath -RuntimeRoot $RuntimeRoot -PublicationRoot $PublicationRoot
$stage = Get-InstallStage -RuntimeRoot $paths.RuntimeRoot
if ($null -eq $stage) {
    Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "preflight" | Out-Null
}

$pythonState = Test-PythonRuntime
if (-not $pythonState.Ready) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "python_dependency_missing: Python 3.12 and Pillow==11.3.0/reportlab==4.4.3 are required. Install Python from https://www.python.org/downloads/windows/ and rerun this command."
    }
    if ($pythonState.Reason -eq "python_missing") {
        & winget.exe install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw "python_dependency_missing: Python installation did not complete; rerun after reviewing winget output." }
    }
    $pythonState = Test-PythonRuntime
    if (-not $pythonState.Ready) {
        $requirements = @(
            (Join-Path (Split-Path -Parent $bootstrapRoot) "requirements.txt"),
            (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $bootstrapRoot))) "requirements.txt")
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if (-not $requirements) { throw "python_dependency_missing: requirements.txt was not found in the packaged release." }
        & $pythonState.Python -m pip install --requirement $requirements --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { throw "python_dependency_missing: package installation failed; rerun the same command after reviewing pip output." }
        $pythonState = Test-PythonRuntime -PythonPath $pythonState.Python
    }
    if (-not $pythonState.Ready) { throw "python_dependency_missing: Pillow==11.3.0 and reportlab==4.4.3 are still unavailable." }
}
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "dependency_ready" | Out-Null

$obsidian = Find-ObsidianExecutable
if (-not $obsidian) {
    if (-not $InstallObsidian) {
        return [pscustomobject]@{
            Status = "obsidian_install_required"
            VaultPath = $paths.VaultPath
            PublicationRoot = $paths.PublicationRoot
            Recovery = "Re-run with -InstallObsidian after reviewing the Obsidian installation request."
        }
    }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is unavailable. Install Obsidian from https://obsidian.md/download, then run this command again."
    }
    & winget.exe install --id Obsidian.Obsidian --exact --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "Obsidian installation did not complete. Review the winget output and retry." }
    $obsidian = Find-ObsidianExecutable
    if (-not $obsidian) {
        return [pscustomobject]@{
            Status = "obsidian_install_completed_restart_required"
            VaultPath = $paths.VaultPath
            PublicationRoot = $paths.PublicationRoot
            Recovery = "Close and reopen Codex, then rerun this command with -EnableCommunityPlugin."
        }
    }
}

if (-not $EnableCommunityPlugin) {
    return [pscustomobject]@{
        Status = "community_plugin_consent_required"
        VaultPath = $paths.VaultPath
        PublicationRoot = $paths.PublicationRoot
        Recovery = "This setup installs the pinned Obsidian Local REST API plugin on 127.0.0.1 only. Re-run with -EnableCommunityPlugin after reviewing that consent."
    }
}

Initialize-StarterVault -VaultPath $paths.VaultPath -AllowExistingEmptyVault:$AllowExistingEmptyVault | Out-Null
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "vault_ready" | Out-Null
# On a resumed run, reuse only a fully hash-verified prior plugin installation. A partly
# written, changed, or foreign installation is never overwritten; the normal safe installer
# then stops with an actionable error instead.
$existingInstallation = Test-PinnedLocalRestPluginInstallation -VaultPath $paths.VaultPath
if ($existingInstallation.Ready) {
    Enable-PinnedLocalRestPlugin -VaultPath $paths.VaultPath -PluginId $existingInstallation.PluginId | Out-Null
    $installation = $existingInstallation
} else {
    # Let the module resolve the lock from its own bootstrap tree so the packaged plugin stays
    # self-contained. Passing an explicit parent-relative path here defeated that resolution.
    $installation = Install-PinnedLocalRestPlugin -VaultPath $paths.VaultPath -EnableCommunityPlugin
}
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "local_rest_ready" | Out-Null
Save-RuntimeConfig -Paths $paths | Out-Null
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "runtime_ready" | Out-Null
$publication = Initialize-PublicationLibrary -PublicationRoot $paths.PublicationRoot -VaultPath $paths.VaultPath

if ($LaunchObsidian) {
    Start-Process -FilePath $obsidian -ArgumentList ("--vault `"{0}`"" -f $paths.VaultPath)
}

[pscustomobject]@{
    Status = if ($LaunchObsidian) { "launching_obsidian_run_doctor_next" } else { "installed_launch_obsidian_then_run_doctor" }
    VaultPath = $paths.VaultPath
    PublicationRoot = $publication.Root
    PublicationLibraryStatus = $publication.Status
    VaultShortcutStatus = $publication.ShortcutStatus
    PluginId = $installation.PluginId
    PluginVersion = $installation.Version
    RuntimeConfigPath = $paths.RuntimeConfigPath
}
