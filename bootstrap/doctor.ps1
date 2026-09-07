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
Import-Module (Join-Path $bootstrapRoot "lib\PublicationLibrary.psm1") -Force
Import-Module (Join-Path $bootstrapRoot "lib\PythonRuntime.psm1") -Force
$skillsModule = Join-Path $bootstrapRoot "lib\CodexSkills.psm1"
$hasSkillManifest = (Test-Path -LiteralPath (Join-Path $bootstrapRoot "codex-skills-manifest.json") -PathType Leaf) -and (Test-Path -LiteralPath $skillsModule -PathType Leaf)
if ($hasSkillManifest) { Import-Module $skillsModule -Force }
$stateModule = Join-Path $bootstrapRoot "lib\BootstrapState.psm1"
$hasSchemaV3 = Test-Path -LiteralPath $stateModule -PathType Leaf
if ($hasSchemaV3) { Import-Module $stateModule -Force }

$runtime = if ($RuntimeConfigPath) { Get-RuntimeConfig -RuntimeConfigPath $RuntimeConfigPath } else { Get-RuntimeConfig }
if ($runtime.NeedsMigration) { throw "runtime_migration_required: rerun the installer to migrate the managed runtime." }
$pythonState = Test-ManagedPythonRuntime -PythonPath $runtime.venvPythonExecutable `
    -RequirementsHash $runtime.requirementsHash -ProbePath (Join-Path $bootstrapRoot "verify_python_runtime.py")
if (-not $pythonState.Ready) { throw "python_dependency_missing: the recorded managed Python runtime failed verification; rerun the installer." }
if ($hasSkillManifest) {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
    $skillState = Test-CodexSkillInstallation -CodexSkillsRoot (Join-Path $codexHome "skills") -ManifestPath (Join-Path $bootstrapRoot "codex-skills-manifest.json")
    if (-not $skillState.Valid) { throw ("publisher_skill_not_ready: " + ($skillState.Errors -join "; ")) }
}
if (-not (Test-Path -LiteralPath $runtime.vaultPath -PathType Container)) { throw "Configured vault does not exist: $($runtime.vaultPath)" }
$publicationRoot = Resolve-PublicationRoot -PublicationRoot $runtime.publicationRoot
$publication = Test-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $runtime.vaultPath
Wait-ForLocalRest -DataPath $runtime.restDataPath -TimeoutSeconds $TimeoutSeconds | Out-Null
$health = Test-LocalRestRoundTrip -DataPath $runtime.restDataPath
$stageRuntimeRoot = if ($RuntimeConfigPath) { Split-Path -Parent $RuntimeConfigPath } else { Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript" }
if ($hasSchemaV3) {
    $statePath = Join-Path $stageRuntimeRoot "bootstrap-state.json"
    $state = if (Test-Path -LiteralPath $statePath -PathType Leaf) { Read-BootstrapState -Path $statePath } else {
        [pscustomobject]@{ schemaVersion = 3; stage = "runtime_ready"; skillsReady = $true; pythonReady = $true; obsidianReady = $true; doctorReady = $false }
    }
    $state.stage = "doctor_verified"
    $state.doctorReady = $true
    Write-BootstrapStateAtomic -Path $statePath -State $state
    $state.stage = "ready"
    Write-BootstrapStateAtomic -Path $statePath -State $state
} else {
    Set-InstallStage -RuntimeRoot $stageRuntimeRoot -Stage "doctor_verified" | Out-Null
    Set-InstallStage -RuntimeRoot $stageRuntimeRoot -Stage "ready" | Out-Null
}
[pscustomobject]@{
    Status = $health.Status
    VaultPath = $runtime.vaultPath
    PublicationRoot = $publication.Root
    PublicationLibraryStatus = $publication.Status
    VaultShortcutStatus = $publication.ShortcutStatus
    Port = $health.Port
    Checked = "create-read-delete temporary health note"
}
