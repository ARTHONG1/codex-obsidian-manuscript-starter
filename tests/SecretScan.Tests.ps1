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
    if (Test-Path -LiteralPath $candidateRoot -PathType Leaf) {
        return @(Get-Item -LiteralPath $candidateRoot)
    }
    if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) { throw "candidate archive root does not exist" }
    Get-ChildItem -LiteralPath $candidateRoot -Recurse -File -Force
}

function Find-ReleasePrivacyViolations {
    param([IO.FileInfo[]]$AdditionalFiles = @())
    $files = @(Get-TrackedReleaseFiles) + @(Get-CandidateArchiveFiles) + @($AdditionalFiles)
    $forbiddenNames = @("data.json", "*.pem", "*.key", "*.pfx", "*.p12", "*.pdf", "*.docx", "*.png", "*.jpg", "*.jpeg", "*.webp")
    $profileRoot = '(?i)(?:[A-Z]:[\\/]Users[\\/][^\\/:]+[\\/](?:AppData|Documents|Desktop)|[\\/]Users[\\/][^\\/:]+[\\/]Library[\\/]Application Support)(?:[\\/]|$)'
    $patterns = @(
        'ghp_[A-Za-z0-9]{30,}',
        'github_pat_[A-Za-z0-9_]{30,}',
        'sk-[A-Za-z0-9]{30,}',
        '(?i)bearer\s+[A-Za-z0-9._~+/=-]{24,}',
        'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY',
        '(?i)"apiKey"\s*:\s*"[A-Za-z0-9._=-]{24,}"',
        $profileRoot,
        '(?i)(candidate[-_ ]preview)'
    )
    foreach ($file in $files) {
        if ($file.Extension -ieq ".zip") {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [IO.Compression.ZipFile]::OpenRead($file.FullName)
            try {
                foreach ($member in $archive.Entries) {
                    $name = $member.FullName.Replace("\", "/")
                    $normalized = $name.TrimStart("/")
                    if ($name.StartsWith("/") -or $name -match '^[A-Za-z]:/' -or ($normalized -split "/" | Where-Object { $_ -eq ".." })) {
                        [pscustomobject]@{ File = "$($file.FullName)!$name"; Reason = "unsafe member path" }
                        continue
                    }
                    if ($forbiddenNames | Where-Object { [IO.Path]::GetFileName($name) -like $_ }) {
                        [pscustomobject]@{ File = "$($file.FullName)!$name"; Reason = "forbidden name or source/output extension" }
                        continue
                    }
                    if ($member.Length -le 2MB) {
                        $reader = [IO.StreamReader]::new($member.Open())
                        try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
                        foreach ($match in @(Select-String -InputObject $content -Pattern $patterns -AllMatches)) {
                            [pscustomobject]@{ File = "$($file.FullName)!$name"; Reason = "privacy marker in archive member" }
                        }
                    }
                }
            } finally {
                $archive.Dispose()
            }
            continue
        }
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

    It "detects a synthetic non-default Windows user profile path" {
        $fixtures = @(
            (Join-Path $TestDrive "windows-profile-fixture.txt"),
            (Join-Path $TestDrive "macos-profile-fixture.txt")
        )
        Set-Content -LiteralPath $fixtures[0] -Value "C:\Users\release-auditor\AppData\Roaming\secret.json" -Encoding UTF8
        Set-Content -LiteralPath $fixtures[1] -Value "/Users/release-auditor/Library/Application Support/secret.json" -Encoding UTF8
        $findings = @(Find-ReleasePrivacyViolations -AdditionalFiles $fixtures)
        foreach ($fixture in $fixtures) {
            @($findings | Where-Object File -eq $fixture) | Should Not BeNullOrEmpty
        }
    }

    It "scans ZIP members before extraction" {
        $archive = Join-Path $TestDrive "candidate.zip"
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [IO.Compression.ZipFile]::Open($archive, [IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($entry in @(
                @{ Name = "safe/readme.txt"; Value = "safe" },
                @{ Name = "../escape.txt"; Value = "unsafe member" },
                @{ Name = "C:/absolute.txt"; Value = "unsafe member" },
                @{ Name = "source.pdf"; Value = "source" },
                @{ Name = "data.json"; Value = '{"apiKey":"synthetic-secret-value"}' }
            )) {
                $item = $zip.CreateEntry($entry.Name)
                $writer = [IO.StreamWriter]::new($item.Open())
                try { $writer.Write($entry.Value) } finally { $writer.Dispose() }
            }
        } finally {
            $zip.Dispose()
        }
        @(Find-ReleasePrivacyViolations -AdditionalFiles @($archive)) |
            Where-Object Reason -match "unsafe member|forbidden|privacy marker" |
            Should Not BeNullOrEmpty
    }
}
