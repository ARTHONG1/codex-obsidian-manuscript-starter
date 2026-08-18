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
$bootstrapStateModule = Join-Path $bootstrapRoot "lib\BootstrapState.psm1"
$codexSkillsModule = Join-Path $bootstrapRoot "lib\CodexSkills.psm1"
$officialInstallersModule = Join-Path $bootstrapRoot "lib\OfficialInstallers.psm1"
$hasSchemaV3 = (Test-Path -LiteralPath $bootstrapStateModule -PathType Leaf)
$hasSkillTransaction = (Test-Path -LiteralPath $codexSkillsModule -PathType Leaf)
$hasOfficialInstallers = (Test-Path -LiteralPath $officialInstallersModule -PathType Leaf)
if ($hasSchemaV3) { Import-Module $bootstrapStateModule -Force }
if ($hasSkillTransaction) { Import-Module $codexSkillsModule -Force }
if ($hasOfficialInstallers) { Import-Module $officialInstallersModule -Force }

$paths = Resolve-InstallPaths -VaultPath $VaultPath -RuntimeRoot $RuntimeRoot -PublicationRoot $PublicationRoot
$bootstrapStatePath = Join-Path $paths.RuntimeRoot "bootstrap-state.json"
function Update-BeginnerBootstrapState {
    param([Parameter(Mandatory = $true)][string]$Stage, [hashtable]$Probe = @{})
    if (-not $hasSchemaV3) { return }
    $state = if (Test-Path -LiteralPath $bootstrapStatePath -PathType Leaf) {
        try { Read-BootstrapState -Path $bootstrapStatePath } catch { $null }
    } else { $null }
    if (-not $state) {
        $state = [pscustomobject]@{ schemaVersion = 3; stage = "preflight"; skillsReady = $false; pythonReady = $false; obsidianReady = $false; doctorReady = $false }
    }
    foreach ($key in $Probe.Keys) {
        $property = $state.PSObject.Properties[$key]
        if ($property) { $property.Value = [bool]$Probe[$key] } else { $state | Add-Member -NotePropertyName $key -NotePropertyValue ([bool]$Probe[$key]) }
    }
    $state.stage = $Stage
    Write-BootstrapStateAtomic -Path $bootstrapStatePath -State $state
}

Update-BeginnerBootstrapState -Stage "preflight"
$stage = Get-InstallStage -RuntimeRoot $paths.RuntimeRoot
if ($null -eq $stage) {
    Set-InstallStage -RuntimeRoot $paths.RuntimeRoot -Stage "preflight" | Out-Null
}

$base = Find-Python312
if (-not $base.Ready) {
    if ($base.Reason -eq "python_version_unsupported") {
        return [pscustomobject]@{
            Status = "python_version_unsupported"
            Recovery = "Install the supported Python 3.12 runtime and rerun the same installer command."
        }
    }
    $wingetCommand = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $wingetCommand) {
        if (-not $hasOfficialInstallers) {
            return [pscustomobject]@{ Status = "python_install_manual_required"; Recovery = "Install Python 3.12 or use a release containing the verified official installer module, then rerun the same request." }
        }
        $officialLock = Read-OfficialInstallerLock -Path (Join-Path $bootstrapRoot "official-installers.lock.json")
        $pythonInstaller = @($officialLock.installers | Where-Object { $_.product -eq "python" })[0]
        $artifact = Get-VerifiedOfficialInstallerArtifact -Entry $pythonInstaller -DestinationRoot (Join-Path $paths.RuntimeRoot "downloads")
        Invoke-VerifiedOfficialInstaller -ArtifactPath $artifact -Arguments @($pythonInstaller.arguments) | Out-Null
        return [pscustomobject]@{ Status = "python_installed_restart_required"; Recovery = "Restart Codex and rerun the same installer request." }
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
Update-BeginnerBootstrapState -Stage "python_ready" -Probe @{ pythonReady = $true }

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
    $wingetCommand = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($wingetCommand) {
        & $wingetCommand.Source install --id Obsidian.Obsidian --exact --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw "Obsidian installation did not complete. Review the winget output and retry." }
    } else {
        if (-not $hasOfficialInstallers) { throw "official_installer_module_missing" }
        $officialLock = Read-OfficialInstallerLock -Path (Join-Path $bootstrapRoot "official-installers.lock.json")
        $obsidianInstaller = @($officialLock.installers | Where-Object { $_.product -eq "obsidian" })[0]
        $artifact = Get-VerifiedOfficialInstallerArtifact -Entry $obsidianInstaller -DestinationRoot (Join-Path $paths.RuntimeRoot "downloads")
        Invoke-VerifiedOfficialInstaller -ArtifactPath $artifact -Arguments @($obsidianInstaller.arguments) | Out-Null
    }
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

if ($hasSkillTransaction) {
    $skillManifestPath = Join-Path $bootstrapRoot "codex-skills-manifest.json"
    if (-not (Test-Path -LiteralPath $skillManifestPath -PathType Leaf)) { throw "skill_manifest_missing" }
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
    $codexSkillsRoot = Join-Path $codexHome "skills"
    Install-VerifiedCodexSkillPair -ReleaseRoot (Split-Path -Parent $bootstrapRoot) -CodexSkillsRoot $codexSkillsRoot -ManifestPath $skillManifestPath | Out-Null
    Update-BeginnerBootstrapState -Stage "skills_ready" -Probe @{ skillsReady = $true }
}
Update-BeginnerBootstrapState -Stage "obsidian_ready" -Probe @{ obsidianReady = $true }
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
Update-BeginnerBootstrapState -Stage "runtime_ready" -Probe @{ pythonReady = $true; obsidianReady = $true; skillsReady = $hasSkillTransaction }
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
