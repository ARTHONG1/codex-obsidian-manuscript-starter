#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ScenarioSet,
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$EvidencePath
)

$ErrorActionPreference = "Stop"
$allowed = @("codex_only", "no_winget", "restart_resume", "path_collision", "interrupted_download", "tampered_release", "delayed_rest", "previous_skill_rollback")
$evidence = [ordered]@{ schemaVersion = 1; status = "failed"; scenarios = @(); interactionCount = 0 }
try {
    $set = Get-Content -Raw -LiteralPath $ScenarioSet -Encoding UTF8 | ConvertFrom-Json
    if ($set.schemaVersion -ne 1) { throw "acceptance_scenario_schema_invalid" }
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    foreach ($scenario in @($set.scenarios)) {
        $id = [string]$scenario.id
        if ($id -notin $allowed) { throw "acceptance_scenario_not_allowed" }
        $scenarioRoot = Join-Path $Root $id
        New-Item -ItemType Directory -Path $scenarioRoot -Force | Out-Null
        $evidence.scenarios += [ordered]@{ id = $id; status = "requires_disposable_windows"; evidenceRoot = $id }
    }
    $evidence.status = "contract_ready"
} catch {
    $evidence.status = "failed"
    $evidence.errorCode = $_.Exception.Message -replace '[^A-Za-z0-9_.-]', '_'
} finally {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($EvidencePath))
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
}
if ($evidence.status -ne "contract_ready") { exit 1 }
