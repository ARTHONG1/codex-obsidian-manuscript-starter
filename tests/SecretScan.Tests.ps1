$repoRoot = Split-Path -Parent $PSScriptRoot
# Fixture classes covered by candidate archives: source PDF/DOCX/images and generated manuscript outputs.
# Tracked enumeration contract: git ls-files -z
$fixtureFiles = @("tests/SecretScan.Tests.ps1", "tests/test_release_privacy_contract.py")
$textExtensions = @(".md", ".txt", ".json", ".py", ".ps1", ".psm1", ".yaml", ".yml", ".toml", ".ini", ".cff", ".lock")

function Get-TrackedReleaseFiles {
    $raw = & git -C $repoRoot ls-files -z
    $items = [Text.Encoding]::UTF8.GetString([Text.Encoding]::Default.GetBytes(($raw -join ""))) -split "`0" |
        Where-Object { $_ -and ($_ -notin $fixtureFiles) }
    foreach ($relative in $items) {
        if ([IO.Path]::GetExtension($relative).ToLowerInvariant() -in $textExtensions) {
            $path = Join-Path $repoRoot $relative
            if (Test-Path -LiteralPath $path -PathType Leaf) { Get-Item -LiteralPath $path }
        }
    }
}

function Get-CandidateArchiveFiles {
    $candidateRoot = $env:CODEX_RELEASE_CANDIDATE
    if (-not $candidateRoot) { return @() }
    if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) { throw "candidate archive root does not exist" }
    Get-ChildItem -LiteralPath $candidateRoot -Recurse -File -Force
}

function Find-ReleasePrivacyViolations {
    $files = @(Get-TrackedReleaseFiles) + @(Get-CandidateArchiveFiles)
    $forbiddenNames = @("data.json", "*.pem", "*.key", "*.pfx", "*.p12", "*.pdf", "*.docx", "*.png", "*.jpg", "*.jpeg", "*.webp")
    $patterns = @(
        'ghp_[A-Za-z0-9]{30,}',
        'github_pat_[A-Za-z0-9_]{30,}',
        'sk-[A-Za-z0-9]{30,}',
        '(?i)bearer\s+[A-Za-z0-9._~+/=-]{24,}',
        'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY',
        '(?i)"apiKey"\s*:\s*"[A-Za-z0-9._=-]{24,}"',
        '(?i)(Users[\\/]+sample-account|sample-account[\\/]+)',
        '(?i)(candidate[-_ ]preview)'
    )
    foreach ($file in $files) {
        if ($forbiddenNames | Where-Object { $file.Name -like $_ }) {
            [pscustomobject]@{ File = $file.FullName; Reason = "forbidden name or source/output extension" }
            continue
        }
        if ($file.Length -gt 2MB) { continue }
        foreach ($match in @(Select-String -LiteralPath $file.FullName -Pattern $patterns -AllMatches -ErrorAction SilentlyContinue)) {
            [pscustomobject]@{ File = $file.FullName; Reason = "privacy marker at line $($match.LineNumber)" }
        }
    }
}

Describe "Public release secret and privacy contract" {
    It "has no tracked or candidate-archive privacy violations" {
        @(Find-ReleasePrivacyViolations) | Should BeNullOrEmpty
    }

    It "does not track generated Python bytecode in the public release" {
        $trackedBytecode = & git -C $repoRoot ls-files -- '*.pyc'
        @($trackedBytecode).Count | Should Be 0
    }
}
