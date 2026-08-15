Set-StrictMode -Version Latest

function Test-SafeRelativePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([IO.Path]::IsPathRooted($Path)) { return $false }
    $normalized = $Path.Replace('\', '/')
    if ($normalized.StartsWith('/') -or $normalized -match '(^|/)\.\.(?:/|$)' -or $normalized -match '(^|/)\.\.(?:/|$)') { return $false }
    return $true
}

function Test-NoReparseAncestor {
    param([Parameter(Mandatory = $true)][string]$Path)
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $false }
        }
        $parent = Split-Path -Parent $current
        if ($parent -eq $current) { break }
        $current = $parent
    }
    return $true
}

function Read-CodexSkillManifest {
    param([Parameter(Mandatory = $true)][string]$ManifestPath)
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) { throw "Skill manifest is missing." }
    $manifest = Get-Content -Raw -LiteralPath $ManifestPath -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schemaVersion -ne 1 -or @($manifest.skills).Count -ne 2) { throw "Skill manifest has an unsupported shape." }
    foreach ($skill in @($manifest.skills)) {
        foreach ($member in @($skill.files)) {
            if (-not (Test-SafeRelativePath -Path ([string]$member.path))) { throw "Unsafe skill member path." }
            if ([string]$member.sha256 -notmatch '^[0-9a-fA-F]{64}$') { throw "Invalid skill member hash." }
        }
    }
    return $manifest
}

function Test-CodexSkillSource {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot,
        [Parameter(Mandatory = $true)][string]$ManifestPath
    )
    $errors = @()
    try { $manifest = Read-CodexSkillManifest -ManifestPath $ManifestPath } catch { return [pscustomobject]@{ Valid = $false; Skills = @(); Errors = @($_.Exception.Message) } }
    foreach ($skill in @($manifest.skills)) {
        $sourceRoot = Join-Path $ReleaseRoot ([string]$skill.sourceRoot)
        if (-not (Test-NoReparseAncestor -Path $sourceRoot)) { $errors += "$($skill.id): unsafe source root"; continue }
        foreach ($member in @($skill.files)) {
            $path = Join-Path $sourceRoot ([string]$member.path)
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { $errors += "$($skill.id): missing $($member.path)"; continue }
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
            if ($actual -ine ([string]$member.sha256)) { $errors += "$($skill.id): hash mismatch $($member.path)" }
        }
    }
    [pscustomobject]@{ Valid = (@($errors).Count -eq 0); Skills = @($manifest.skills); Errors = @($errors) }
}

function Copy-CodexSkillMembers {
    param([Parameter(Mandatory = $true)]$Skill, [Parameter(Mandatory = $true)][string]$ReleaseRoot, [Parameter(Mandatory = $true)][string]$Destination)
    $sourceRoot = Join-Path $ReleaseRoot ([string]$Skill.sourceRoot)
    foreach ($member in @($Skill.files)) {
        $source = Join-Path $sourceRoot ([string]$member.path)
        $target = Join-Path $Destination ([string]$member.path)
        $parent = Split-Path -Parent $target
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
}

function Install-VerifiedCodexSkillPair {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot,
        [Parameter(Mandatory = $true)][string]$CodexSkillsRoot,
        [Parameter(Mandatory = $true)][string]$ManifestPath,
        [scriptblock]$PromotionAction
    )
    $verification = Test-CodexSkillSource -ReleaseRoot $ReleaseRoot -ManifestPath $ManifestPath
    if (-not $verification.Valid) { throw (($verification.Errors -join '; ')) }
    if (-not (Test-NoReparseAncestor -Path $CodexSkillsRoot)) { throw "Codex skill destination is unsafe." }
    New-Item -ItemType Directory -Path $CodexSkillsRoot -Force | Out-Null
    $transactionId = [guid]::NewGuid().ToString('N')
    $stageRoot = Join-Path $CodexSkillsRoot ('.codex-skills-stage-' + $transactionId)
    $backupRoot = Join-Path $CodexSkillsRoot ('.codex-skills-backup-' + $transactionId)
    $promoted = @()
    $backups = @{}
    $promote = if ($PromotionAction) { $PromotionAction } else {
        { param($source, $destination) Move-Item -LiteralPath $source -Destination $destination }
    }
    try {
        New-Item -ItemType Directory -Path $stageRoot, $backupRoot -Force | Out-Null
        foreach ($skill in @($verification.Skills)) {
            $stage = Join-Path $stageRoot ([string]$skill.destination)
            Copy-CodexSkillMembers -Skill $skill -ReleaseRoot $ReleaseRoot -Destination $stage
            $backups[[string]$skill.destination] = $null
        }
        foreach ($skill in @($verification.Skills)) {
            $destination = Join-Path $CodexSkillsRoot ([string]$skill.destination)
            $backup = Join-Path $backupRoot ([string]$skill.destination)
            if (Test-Path -LiteralPath $destination) {
                Move-Item -LiteralPath $destination -Destination $backup
                $backups[[string]$skill.destination] = $backup
            }
        }
        $index = 0
        foreach ($skill in @($verification.Skills)) {
            $destination = Join-Path $CodexSkillsRoot ([string]$skill.destination)
            & $promote (Join-Path $stageRoot ([string]$skill.destination)) $destination
            $promoted += $destination
            $index++
        }
        [pscustomobject]@{ Status = 'installed'; TransactionId = $transactionId; SkillIds = @($verification.Skills | ForEach-Object id) }
    } catch {
        foreach ($path in $promoted) { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force } }
        foreach ($skill in @($verification.Skills)) {
            $destination = Join-Path $CodexSkillsRoot ([string]$skill.destination)
            $backup = $backups[[string]$skill.destination]
            if ($backup -and (Test-Path -LiteralPath $backup)) { Move-Item -LiteralPath $backup -Destination $destination }
        }
        throw
    } finally {
        if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $backupRoot) { Remove-Item -LiteralPath $backupRoot -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

function Test-CodexSkillInstallation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$CodexSkillsRoot,
        [Parameter(Mandatory = $true)][string]$ManifestPath
    )
    $manifest = Read-CodexSkillManifest -ManifestPath $ManifestPath
    $errors = @()
    foreach ($skill in @($manifest.skills)) {
        $destinationRoot = Join-Path $CodexSkillsRoot ([string]$skill.destination)
        if (-not (Test-NoReparseAncestor -Path $destinationRoot)) { $errors += "$($skill.id): unsafe destination"; continue }
        foreach ($member in @($skill.files)) {
            $path = Join-Path $destinationRoot ([string]$member.path)
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { $errors += "$($skill.id): missing $($member.path)"; continue }
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
            if ($actual -ne ([string]$member.sha256).ToLowerInvariant()) { $errors += "$($skill.id): hash mismatch $($member.path)" }
        }
    }
    [pscustomobject]@{ Valid = (@($errors).Count -eq 0); Errors = @($errors) }
}

Export-ModuleMember -Function Test-CodexSkillSource, Test-CodexSkillInstallation, Install-VerifiedCodexSkillPair
