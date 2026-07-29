Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Initialize-StarterVault {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [switch]$AllowExistingEmptyVault
    )

    $target = [IO.Path]::GetFullPath($VaultPath)
    if (Test-Path -LiteralPath $target) {
        $children = @(Get-ChildItem -LiteralPath $target -Force)
        if ($children.Count -gt 0) {
            throw "Vault target is not empty and will not be overwritten: $target"
        }
        if (-not $AllowExistingEmptyVault) {
            throw "Vault target already exists. Re-run with -AllowExistingEmptyVault only after confirming it is empty: $target"
        }
    }
    else {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
    }

    $folders = @("01 Projects", "02 Templates", "03 Assets", "_system", ".obsidian")
    foreach ($folder in $folders) {
        New-Item -ItemType Directory -Path (Join-Path $target $folder) -Force | Out-Null
    }

    Set-Content -LiteralPath (Join-Path $target "00 Home.md") -Encoding UTF8 -Value "# Codex Obsidian Manuscript`n`nCodex에게 프로젝트 등록을 요청해 원고 재료를 시작합니다.`n"
    Set-Content -LiteralPath (Join-Path $target "02 Templates\conversation-material-card.md") -Encoding UTF8 -Value "# 대화 원고 재료 카드`n`n## 핵심 사실`n`n## 원고 후보 문장`n`n## 편집 메모`n"
    Set-Content -LiteralPath (Join-Path $target "02 Templates\원고 단위 템플릿.md") -Encoding UTF8 -Value "# 챕터 제목`n`n[이번 챕터에서는]`n"
    Set-Content -LiteralPath (Join-Path $target "_system\manuscript-projects.json") -Encoding UTF8 -Value '{"projects":[]}'
    Set-Content -LiteralPath (Join-Path $target ".obsidian\app.json") -Encoding UTF8 -Value '{"restrictedMode":true}'
    Set-Content -LiteralPath (Join-Path $target ".obsidian\community-plugins.json") -Encoding UTF8 -Value '[]'

    return [pscustomobject]@{ VaultPath = $target; Created = $true }
}

Export-ModuleMember -Function Initialize-StarterVault
