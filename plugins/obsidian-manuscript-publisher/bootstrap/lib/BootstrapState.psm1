Set-StrictMode -Version Latest

$script:AllowedStages = @("preflight", "skills_ready", "python_ready", "obsidian_ready", "runtime_ready", "doctor_verified", "ready")
$script:ForbiddenProperties = @("apiKey", "certificate", "privateKey", "token", "password", "conversation", "manuscript")

function Assert-StateShape {
    param([Parameter(Mandatory = $true)]$State)
    if ($null -eq $State -or [int]$State.schemaVersion -ne 3) { throw "Unsupported bootstrap state schema." }
    if ([string]$State.stage -notin $script:AllowedStages) { throw "Unsupported bootstrap state stage." }
    foreach ($property in $State.PSObject.Properties) {
        if ($property.Name -in $script:ForbiddenProperties) { throw "Bootstrap state contains a forbidden secret or user-data field." }
    }
}

function Read-BootstrapState {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Bootstrap state is missing." }
    try { $state = Get-Content -Raw -LiteralPath $Path -Encoding UTF8 | ConvertFrom-Json } catch { throw "Bootstrap state is invalid JSON." }
    Assert-StateShape -State $state
    return $state
}

function Write-BootstrapStateAtomic {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)]$State)
    $normalized = ($State | ConvertTo-Json -Depth 8 | ConvertFrom-Json)
    Assert-StateShape -State $normalized
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = Join-Path $parent ('.bootstrap-state-' + [guid]::NewGuid().ToString('N') + '.partial')
    try {
        $normalized | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporary -Encoding UTF8
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            $backup = Join-Path $parent ('.bootstrap-state-' + [guid]::NewGuid().ToString('N') + '.backup')
            try { [IO.File]::Replace($temporary, $Path, $backup, $true) } finally { Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue }
        } else {
            Move-Item -LiteralPath $temporary -Destination $Path
        }
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

function Resolve-NextBootstrapAction {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$State, [Parameter(Mandatory = $true)]$Probe)
    Assert-StateShape -State $State
    if (-not [bool]$Probe.skillsReady) { return [pscustomobject]@{ Name = "install_skills"; Reason = "skills_not_ready" } }
    if (-not [bool]$Probe.pythonReady) { return [pscustomobject]@{ Name = "install_python"; Reason = "python_not_ready" } }
    if (-not [bool]$Probe.obsidianReady) { return [pscustomobject]@{ Name = "start_obsidian"; Reason = "obsidian_not_ready" } }
    if (-not [bool]$Probe.doctorReady) { return [pscustomobject]@{ Name = "run_doctor"; Reason = "doctor_required" } }
    return [pscustomobject]@{ Name = "ready"; Reason = "doctor_verified" }
}

Export-ModuleMember -Function Read-BootstrapState, Write-BootstrapStateAtomic, Resolve-NextBootstrapAction
