[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$CodexSkillsRoot,
    [string]$ManifestPath = (Join-Path $PSScriptRoot "codex-skills-manifest.json")
)

$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSScriptRoot "lib\CodexSkills.psm1") -Force
$result = Install-VerifiedCodexSkillPair -ReleaseRoot $ReleaseRoot -CodexSkillsRoot $CodexSkillsRoot -ManifestPath $ManifestPath
$result | ConvertTo-Json -Depth 8
