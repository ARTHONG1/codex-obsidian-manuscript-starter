Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Written before any other vault content so an interrupted run stays recognisable as ours.
$script:ProvisioningMarkerName = ".codex-obsidian-manuscript-vault.json"
$script:ProvisioningOwner = "codex-obsidian-manuscript-starter"

function Get-StarterVaultMarkerPath {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)] [string]$VaultPath)

    return (Join-Path (Join-Path $VaultPath "_system") $script:ProvisioningMarkerName)
}

function Test-IsStarterVault {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)] [string]$VaultPath)

    # Provenance, not naming convention. A user vault that merely happens to share these folder
    # names is NOT ours, and an install interrupted any time after the marker landed IS ours.
    $markerPath = Get-StarterVaultMarkerPath -VaultPath $VaultPath
    if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) { return $false }
    try {
        $marker = Get-Content -Raw -LiteralPath $markerPath | ConvertFrom-Json
    }
    catch { return $false }
    $createdBy = $marker.PSObject.Properties["createdBy"]
    if (-not $createdBy) { return $false }
    return ([string]$createdBy.Value -eq $script:ProvisioningOwner)
}

function Initialize-StarterVault {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [switch]$AllowExistingEmptyVault
    )

    $target = [IO.Path]::GetFullPath($VaultPath)
    $reprovisioning = $false
    if (Test-Path -LiteralPath $target) {
        $children = @(Get-ChildItem -LiteralPath $target -Force)
        if ($children.Count -gt 0) {
            if (Test-IsStarterVault -VaultPath $target) {
                $reprovisioning = $true
            }
            else {
                throw ("Vault target is not empty and will not be overwritten: {0}`n" -f $target) +
                      "이 폴더의 파일은 삭제하지 않습니다. 이 버전은 전용 새 빈 폴더에만 설치할 수 있습니다. " +
                      "-VaultPath 에 아직 존재하지 않는 새 폴더 경로(예: Documents\Codex-Wiki-New)를 지정해 다시 실행하세요."
            }
        }
        if (-not $reprovisioning -and -not $AllowExistingEmptyVault) {
            throw ("Vault target already exists: {0}`n" -f $target) +
                  "비어 있음을 확인했다면 -AllowExistingEmptyVault 를 붙여 다시 실행하세요. " +
                  "비어 있지 않다면 전용 새 빈 폴더 경로를 지정하세요."
        }
    }
    else {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
    }

    # Claim ownership first, so a crash immediately after this point is still retryable.
    New-Item -ItemType Directory -Path (Join-Path $target "_system") -Force | Out-Null
    $markerPath = Get-StarterVaultMarkerPath -VaultPath $target
    if (-not (Test-Path -LiteralPath $markerPath)) {
        Set-Content -LiteralPath $markerPath -Encoding UTF8 -NoNewline -Value ('{"createdBy":"' + $script:ProvisioningOwner + '","schemaVersion":1}')
    }

    $folders = @("01 Projects", "02 Templates", "03 Assets", "_system", ".obsidian")
    foreach ($folder in $folders) {
        New-Item -ItemType Directory -Path (Join-Path $target $folder) -Force | Out-Null
    }

    # Seed only when absent, so re-running never overwrites user edits.
    $seeds = [ordered]@{
        "00 Home.md" = "# Codex Obsidian Manuscript`n`nCodex에게 프로젝트 등록을 요청해 원고 재료를 시작합니다.`n"
        "02 Templates\conversation-material-card.md" = "# 대화 원고 재료 카드`n`n## 핵심 사실`n`n## 원고 후보 문장`n`n## 편집 메모`n"
        "02 Templates\원고 단위 템플릿.md" = "# 챕터 제목`n`n[이번 챕터에서는]`n"
        "_system\manuscript-projects.json" = '{"projects":[]}'
        ".obsidian\app.json" = '{"restrictedMode":true}'
        ".obsidian\community-plugins.json" = '[]'
    }
    foreach ($relative in $seeds.Keys) {
        $seedPath = Join-Path $target $relative
        if (-not (Test-Path -LiteralPath $seedPath)) {
            Set-Content -LiteralPath $seedPath -Encoding UTF8 -Value $seeds[$relative]
        }
    }

    return [pscustomobject]@{ VaultPath = $target; Created = (-not $reprovisioning); Reprovisioned = $reprovisioning }
}

Export-ModuleMember -Function Initialize-StarterVault, Test-IsStarterVault, Get-StarterVaultMarkerPath
