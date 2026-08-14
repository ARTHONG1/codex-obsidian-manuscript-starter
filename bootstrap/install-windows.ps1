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
Import-Module (Join-Path $bootstrapRoot "lib\PythonRuntime.psm1") -Force

$paths = Resolve-InstallPaths -VaultPath $VaultPath -RuntimeRoot $RuntimeRoot -PublicationRoot $PublicationRoot
$stage = Get-InstallStage -RuntimeRoot $paths.RuntimeRoot
if ($null -eq $stage) {
    Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "preflight" | Out-Null
}

$base = Find-Python312
if (-not $base.Ready) {
    $wingetCommand = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $wingetCommand) {
        return [pscustomobject]@{
            Status = "python_install_manual_required"
            Recovery = "Install Python 3.12 or WinGet, then rerun the same installer command."
        }
    }
    $install = Install-Python312 -WingetPath $wingetCommand.Source
    if ($install.Status -ne "python_installed") {
        return $install
    }
    $base = Find-Python312
    if (-not $base.Ready) {
        return [pscustomobject]@{
            Status = "python_installed_restart_required"
            Recovery = "Restart Codex and rerun the same installer command."
        }
    }
}
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "base_python_ready" | Out-Null

$lockPath = Join-Path (Split-Path -Parent $bootstrapRoot) "requirements.lock.txt"
$managed = New-VerifiedManagedVenv -BasePython $base.Python -RuntimeRoot $paths.RuntimeRoot `
    -RequirementsLockPath $lockPath -ProbePath (Join-Path $bootstrapRoot "verify_python_runtime.py")
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "venv_ready" | Out-Null
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "dependencies_ready" | Out-Null

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
$runtime = if (Test-Path -LiteralPath $paths.RuntimeConfigPath -PathType Leaf) {
    Get-RuntimeConfig -RuntimeConfigPath $paths.RuntimeConfigPath
} else {
    $null
}
if ($runtime -and $runtime.NeedsMigration) {
    Convert-RuntimeConfigV1ToV2 -RuntimeConfigPath $paths.RuntimeConfigPath -Paths $paths -PythonRuntime $managed | Out-Null
} else {
    Save-RuntimeConfig -Paths $paths -PythonRuntime $managed | Out-Null
}
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "runtime_ready" | Out-Null
$publication = Initialize-PublicationLibrary -PublicationRoot $paths.PublicationRoot -VaultPath $paths.VaultPath
Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "ready" | Out-Null

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
