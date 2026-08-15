$repoRoot = Split-Path -Parent $PSScriptRoot
$modulePath = Join-Path $repoRoot "bootstrap\lib\CodexSkills.psm1"

function New-SkillFixture {
    param([string]$Root, [bool]$FailSecondPromotion = $false)
    $sourceRoot = Join-Path $Root "release"
    $skillsRoot = Join-Path $Root "codex-skills"
    $setup = Join-Path $sourceRoot "setup"
    $publisher = Join-Path $sourceRoot "publisher"
    New-Item -ItemType Directory -Path $setup, $publisher, $skillsRoot -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $setup "SKILL.md") -Value "setup-v1" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $publisher "SKILL.md") -Value "publisher-v1" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $publisher "references.md") -Value "reference-v1" -Encoding UTF8
    $hash = { param($Path) (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
    $manifest = [ordered]@{
        schemaVersion = 1
        skills = @(
            [ordered]@{
                id = "obsidian-manuscript-setup"
                sourceRoot = "setup"
                destination = "obsidian-manuscript-setup"
                files = @([ordered]@{ path = "SKILL.md"; sha256 = & $hash (Join-Path $setup "SKILL.md") })
            },
            [ordered]@{
                id = "obsidian-manuscript-publisher"
                sourceRoot = "publisher"
                destination = "obsidian-manuscript-publisher"
                files = @(
                    [ordered]@{ path = "SKILL.md"; sha256 = & $hash (Join-Path $publisher "SKILL.md") },
                    [ordered]@{ path = "references.md"; sha256 = & $hash (Join-Path $publisher "references.md") }
                )
            }
        )
    }
    $manifestPath = Join-Path $sourceRoot "codex-skills-manifest.json"
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    if ($FailSecondPromotion) { Set-Content -LiteralPath (Join-Path $sourceRoot "fail-second-promotion.flag") -Value "1" -Encoding UTF8 }
    [pscustomobject]@{ SourceRoot = $sourceRoot; SkillsRoot = $skillsRoot; ManifestPath = $manifestPath }
}

Describe "Codex skill pair bootstrap contract" {
    BeforeAll {
        $script:moduleAvailable = Test-Path -LiteralPath $modulePath
        if ($script:moduleAvailable) { Import-Module $modulePath -Force }
    }

    It "requires the source manifest and exact member hashes before promotion" {
        $script:moduleAvailable | Should Be $true
        $fixture = New-SkillFixture -Root (Join-Path $TestDrive "verify")
        $verification = Test-CodexSkillSource -ReleaseRoot $fixture.SourceRoot -ManifestPath $fixture.ManifestPath
        $verification.Valid | Should Be $true
        $verification.Skills.Count | Should Be 2
    }

    It "rejects a changed skill member before touching destinations" {
        $script:moduleAvailable | Should Be $true
        $fixture = New-SkillFixture -Root (Join-Path $TestDrive "tamper")
        Add-Content -LiteralPath (Join-Path $fixture.SourceRoot "publisher\SKILL.md") -Value "tampered"
        { Install-VerifiedCodexSkillPair -ReleaseRoot $fixture.SourceRoot -CodexSkillsRoot $fixture.SkillsRoot -ManifestPath $fixture.ManifestPath } | Should Throw
        @(Get-ChildItem -LiteralPath $fixture.SkillsRoot -Force) | Should BeNullOrEmpty
    }

    It "installs both skills and preserves exact member bytes" {
        $script:moduleAvailable | Should Be $true
        $fixture = New-SkillFixture -Root (Join-Path $TestDrive "install")
        $result = Install-VerifiedCodexSkillPair -ReleaseRoot $fixture.SourceRoot -CodexSkillsRoot $fixture.SkillsRoot -ManifestPath $fixture.ManifestPath
        $result.Status | Should Be "installed"
        (Get-Content -Raw -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-setup\SKILL.md")) | Should Match "setup-v1"
        (Get-Content -Raw -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-publisher\references.md")) | Should Match "reference-v1"
    }

    It "rolls back both destinations when the second promotion fails" {
        $script:moduleAvailable | Should Be $true
        $fixture = New-SkillFixture -Root (Join-Path $TestDrive "rollback")
        New-Item -ItemType Directory -Path (Join-Path $fixture.SkillsRoot "obsidian-manuscript-setup"), (Join-Path $fixture.SkillsRoot "obsidian-manuscript-publisher") -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-setup\SKILL.md") -Value "old-setup" -Encoding UTF8
        Set-Content -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-publisher\SKILL.md") -Value "old-publisher" -Encoding UTF8
        Set-Content -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-publisher\references.md") -Value "old-reference" -Encoding UTF8
        { Install-VerifiedCodexSkillPair -ReleaseRoot $fixture.SourceRoot -CodexSkillsRoot $fixture.SkillsRoot -ManifestPath $fixture.ManifestPath -TestFailureAfterFirstPromotion } | Should Throw
        (Get-Content -Raw -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-setup\SKILL.md")) | Should Match "old-setup"
        (Get-Content -Raw -LiteralPath (Join-Path $fixture.SkillsRoot "obsidian-manuscript-publisher\SKILL.md")) | Should Match "old-publisher"
    }
}
