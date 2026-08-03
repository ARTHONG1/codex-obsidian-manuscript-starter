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

$pythonState = Test-PythonRuntime
if (-not $pythonState.Ready) { throw "python_dependency_missing: Python 3.12 with Pillow==11.3.0 and reportlab==4.4.3 is required; rerun the installer or install the official Python package and retry." }

$runtime = if ($RuntimeConfigPath) { Get-RuntimeConfig -RuntimeConfigPath $RuntimeConfigPath } else { Get-RuntimeConfig }
if (-not (Test-Path -LiteralPath $runtime.vaultPath -PathType Container)) { throw "Configured vault does not exist: $($runtime.vaultPath)" }
$publicationRoot = Resolve-PublicationRoot -PublicationRoot $runtime.publicationRoot
$publication = Test-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $runtime.vaultPath
Wait-ForLocalRest -DataPath $runtime.restDataPath -TimeoutSeconds $TimeoutSeconds | Out-Null
$health = Test-LocalRestRoundTrip -DataPath $runtime.restDataPath
$stageRuntimeRoot = if ($RuntimeConfigPath) { Split-Path -Parent $RuntimeConfigPath } else { Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript" }
Set-InstallStage -RuntimeRoot $stageRuntimeRoot -Stage "doctor_verified" | Out-Null
Set-InstallStage -RuntimeRoot $stageRuntimeRoot -Stage "ready" | Out-Null
[pscustomobject]@{
    Status = $health.Status
    VaultPath = $runtime.vaultPath
    PublicationRoot = $publication.Root
    PublicationLibraryStatus = $publication.Status
    VaultShortcutStatus = $publication.ShortcutStatus
    Port = $health.Port
    Checked = "create-read-delete temporary health note"
}
