#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$VaultPath,
    [string]$RuntimeRoot,
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

$paths = Resolve-InstallPaths -VaultPath $VaultPath -RuntimeRoot $RuntimeRoot
$obsidian = Find-ObsidianExecutable
if (-not $obsidian) {
    if (-not $InstallObsidian) {
        return [pscustomobject]@{
            Status = "obsidian_install_required"
            VaultPath = $paths.VaultPath
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
            Recovery = "Close and reopen Codex, then rerun this command with -EnableCommunityPlugin."
        }
    }
}

if (-not $EnableCommunityPlugin) {
    return [pscustomobject]@{
        Status = "community_plugin_consent_required"
        VaultPath = $paths.VaultPath
        Recovery = "This setup installs the pinned Obsidian Local REST API plugin on 127.0.0.1 only. Re-run with -EnableCommunityPlugin after reviewing that consent."
    }
}

Initialize-StarterVault -VaultPath $paths.VaultPath -AllowExistingEmptyVault:$AllowExistingEmptyVault | Out-Null
$installation = Install-PinnedLocalRestPlugin -VaultPath $paths.VaultPath -EnableCommunityPlugin -LockPath (Join-Path (Split-Path -Parent $bootstrapRoot) "dependencies.lock.json")
Save-RuntimeConfig -Paths $paths | Out-Null

if ($LaunchObsidian) {
    Start-Process -FilePath $obsidian -ArgumentList ("--vault `"{0}`"" -f $paths.VaultPath)
}

[pscustomobject]@{
    Status = if ($LaunchObsidian) { "launching_obsidian_run_doctor_next" } else { "installed_launch_obsidian_then_run_doctor" }
    VaultPath = $paths.VaultPath
    PluginId = $installation.PluginId
    PluginVersion = $installation.Version
    RuntimeConfigPath = $paths.RuntimeConfigPath
}
