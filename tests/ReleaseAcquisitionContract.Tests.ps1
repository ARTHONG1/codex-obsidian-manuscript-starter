Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot '..\bootstrap\release-acquisition.psm1') -Force

Describe 'immutable release acquisition contract' {
    BeforeEach {
        $manifest = [pscustomobject]@{
            schemaVersion = 1
            repository = 'ARTHONG1/codex-obsidian-manuscript-starter'
            version = '0.5.2'
            tag = 'v0.5.2'
            commit = ('a' * 40)
            archive = 'codex-obsidian-manuscript-starter-v0.5.2.zip'
            archiveSha256 = ('b' * 64)
            files = @([pscustomobject]@{ name = 'README.md'; sha256 = ('c' * 64) })
        }
    }

    function New-TestZip {
        param(
            [Parameter(Mandatory=$true)][string]$Path,
            [Parameter(Mandatory=$true)]$Members
        )
        Add-Type -AssemblyName System.IO.Compression
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [IO.Compression.ZipFile]::Open($Path, [IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($member in @($Members)) {
                $bytes = [Text.Encoding]::UTF8.GetBytes([string]$member.Content)
                $entry = $archive.CreateEntry([string]$member.Name)
                $stream = $entry.Open()
                try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
            }
        } finally {
            $archive.Dispose()
        }
    }

    function Get-TestBytesSha256([string]$Text) {
        $sha = [Security.Cryptography.SHA256]::Create()
        try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))) -replace '-', '').ToLowerInvariant() }
        finally { $sha.Dispose() }
    }

    function Save-TestReleaseFixture {
        param(
            [Parameter(Mandatory=$true)][string]$Root,
            [string[]]$ManifestNames = @('README.md'),
            [hashtable]$ZipMembers = @{ 'README.md' = 'safe readme' },
            [switch]$MismatchedHash
        )
        New-Item -ItemType Directory -Path $Root -Force | Out-Null
        $archive = Join-Path $Root 'codex-obsidian-manuscript-starter-v0.5.2.zip'
        $entries = @(
            foreach ($name in $ZipMembers.Keys) {
                [pscustomobject]@{ Name = $name; Content = $ZipMembers[$name] }
            }
        )
        New-TestZip -Path $archive -Members $entries
        $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        $files = @(
            foreach ($name in $ManifestNames) {
                $content = if ($ZipMembers.ContainsKey($name)) { $ZipMembers[$name] } else { 'manifest only' }
                $hash = if ($MismatchedHash -and $name -eq 'README.md') { '0' * 64 } else { Get-TestBytesSha256 $content }
                [pscustomobject]@{ name = $name; sha256 = $hash }
            }
        )
        $releaseManifest = [ordered]@{
            schemaVersion = 1
            repository = 'ARTHONG1/codex-obsidian-manuscript-starter'
            version = '0.5.2'
            tag = 'v0.5.2'
            commit = ('a' * 40)
            archive = 'codex-obsidian-manuscript-starter-v0.5.2.zip'
            archiveSha256 = $archiveHash
            files = $files
        }
        $manifestPath = Join-Path $Root 'release-manifest.json.source'
        [IO.File]::WriteAllText($manifestPath, ($releaseManifest | ConvertTo-Json -Depth 6 -Compress), (New-Object Text.UTF8Encoding($false)))
        $manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $checksumsPath = Join-Path $Root 'SHA256SUMS.source'
        Set-Content -LiteralPath $checksumsPath -Value "$archiveHash  codex-obsidian-manuscript-starter-v0.5.2.zip`n$manifestHash  release-manifest.json" -Encoding ASCII
        [pscustomobject]@{ Archive=$archive; Manifest=$manifestPath; Checksums=$checksumsPath; ArchiveSha256=$archiveHash }
    }

    function New-TestRelease {
        param([Parameter(Mandatory=$true)]$Fixture)
        [pscustomobject]@{
            Repository = 'ARTHONG1/codex-obsidian-manuscript-starter'
            Version = '0.5.2'
            Tag = 'v0.5.2'
            Commit = ('a' * 40)
            ArchiveUrl = 'https://github.com/ARTHONG1/codex-obsidian-manuscript-starter/releases/download/v0.5.2/codex-obsidian-manuscript-starter-v0.5.2.zip'
            ManifestUrl = 'https://github.com/ARTHONG1/codex-obsidian-manuscript-starter/releases/download/v0.5.2/release-manifest.json'
            ChecksumsUrl = 'https://github.com/ARTHONG1/codex-obsidian-manuscript-starter/releases/download/v0.5.2/SHA256SUMS'
            ArchiveSha256 = $Fixture.ArchiveSha256
        }
    }

    function Mock-TestDownloads {
        param([Parameter(Mandatory=$true)]$Fixture)
        $global:ReleaseAcquisitionTestFixture = $Fixture
        Mock Invoke-WebRequest -ModuleName release-acquisition {
            if ($Uri -match 'release-manifest\.json$') {
                Copy-Item -LiteralPath $global:ReleaseAcquisitionTestFixture.Manifest -Destination $OutFile -Force
            } elseif ($Uri -match 'SHA256SUMS$') {
                Copy-Item -LiteralPath $global:ReleaseAcquisitionTestFixture.Checksums -Destination $OutFile -Force
            } elseif ($Uri -match '\.zip$') {
                Copy-Item -LiteralPath $global:ReleaseAcquisitionTestFixture.Archive -Destination $OutFile -Force
            } else {
                throw "unexpected uri $Uri"
            }
        }
    }

    It 'accepts an internally consistent stable manifest' {
        { Test-ReleaseManifest -Manifest $manifest -ExpectedRepository $manifest.repository } | Should Not Throw
    }

    It 'rejects a manifest whose repository differs from the requested repository' {
        { Test-ReleaseManifest -Manifest $manifest -ExpectedRepository 'other/repository' } |
            Should Throw 'release_repository_mismatch'
    }

    It 'rejects prerelease metadata' {
        $manifest.version = '0.5.2-rc1'
        { Test-ReleaseManifest -Manifest $manifest -ExpectedRepository $manifest.repository } |
            Should Throw 'stable_release_required'
    }

    It 'rejects a branch archive URL' {
        { Test-ReleaseArchiveUrl -ArchiveUrl 'https://github.com/ARTHONG1/codex-obsidian-manuscript-starter/archive/refs/heads/main.zip' } |
            Should Throw 'branch_archive_rejected'
    }

    It 'rejects unsafe, duplicate, and executable archive members' {
        foreach ($names in @(
            @('README.md', '../escape.txt'),
            @('README.md', 'README.md'),
            @('README.md', 'readme.md'),
            @('README.md', 'bin/setup.exe')
        )) {
            $threw = $false
            try { Test-ReleaseZipMemberNames -Names $names | Out-Null } catch { $threw = $true }
            $threw | Should Be $true
        }
    }

    It 'resolves lightweight tag refs to exact commit identity' {
        $ref = [pscustomobject]@{
            ref = 'refs/tags/v0.5.2'
            url = 'https://api.github.com/repos/ARTHONG1/codex-obsidian-manuscript-starter/git/refs/tags/v0.5.2'
            object = [pscustomobject]@{ type = 'commit'; sha = ('1' * 40) }
        }
        Resolve-GitObjectCommit -Repository 'ARTHONG1/codex-obsidian-manuscript-starter' -Tag 'v0.5.2' -RefObject $ref -ObjectResolver { throw 'should not dereference lightweight tags' } |
            Should Be ('1' * 40)
    }

    It 'dereferences annotated tag objects until a commit is reached' {
        $tagSha = ('2' * 40)
        $commit = ('3' * 40)
        $ref = [pscustomobject]@{
            ref = 'refs/tags/v0.5.2'
            url = 'https://api.github.com/repos/ARTHONG1/codex-obsidian-manuscript-starter/git/refs/tags/v0.5.2'
            object = [pscustomobject]@{ type = 'tag'; sha = $tagSha }
        }
        $objects = @{
            $tagSha = [pscustomobject]@{
                sha = $tagSha
                url = "https://api.github.com/repos/ARTHONG1/codex-obsidian-manuscript-starter/git/tags/$tagSha"
                object = [pscustomobject]@{ type = 'commit'; sha = $commit }
            }
        }
        Resolve-GitObjectCommit -Repository 'ARTHONG1/codex-obsidian-manuscript-starter' -Tag 'v0.5.2' -RefObject $ref -ObjectResolver { param($sha) $objects[$sha] } |
            Should Be $commit
    }

    It 'rejects tag cycles, non-commit terminals, mismatched identity, and excessive dereference depth' {
        $repository = 'ARTHONG1/codex-obsidian-manuscript-starter'
        $tag = 'v0.5.2'
        $tagSha = ('4' * 40)
        $ref = [pscustomobject]@{
            ref = 'refs/tags/v0.5.2'
            url = "https://api.github.com/repos/$repository/git/refs/tags/v0.5.2"
            object = [pscustomobject]@{ type = 'tag'; sha = $tagSha }
        }
        { Resolve-GitObjectCommit -Repository $repository -Tag $tag -RefObject $ref -ObjectResolver {
                [pscustomobject]@{ sha = $tagSha; url = "https://api.github.com/repos/$repository/git/tags/$tagSha"; object = [pscustomobject]@{ type = 'tag'; sha = $tagSha } }
            } } | Should Throw 'release_tag_cycle'
        { Resolve-GitObjectCommit -Repository $repository -Tag $tag -RefObject $ref -ObjectResolver {
                [pscustomobject]@{ sha = $tagSha; url = "https://api.github.com/repos/$repository/git/tags/$tagSha"; object = [pscustomobject]@{ type = 'tree'; sha = ('5' * 40) } }
            } } | Should Throw 'release_tag_target_invalid'
            $badRef = [pscustomobject]@{ ref = 'refs/tags/v0.5.1'; url = "https://api.github.com/repos/$repository/git/refs/tags/v0.5.1"; object = [pscustomobject]@{ type = 'commit'; sha = ('6' * 40) } }
        { Resolve-GitObjectCommit -Repository $repository -Tag $tag -RefObject $badRef -ObjectResolver { throw 'unused' } } |
            Should Throw 'release_tag_identity_mismatch'
        { Resolve-GitObjectCommit -Repository $repository -Tag $tag -RefObject $ref -ObjectResolver {
                param($sha)
                $next = ([int]::Parse($sha.Substring(0, 1)) + 1).ToString() * 40
                [pscustomobject]@{ sha = $sha; url = "https://api.github.com/repos/$repository/git/tags/$sha"; object = [pscustomobject]@{ type = 'tag'; sha = $next } }
            } } | Should Throw 'release_tag_depth_exceeded'
    }

    It 'rejects release metadata URLs outside the exact repository and tag path' {
        $fixture = Save-TestReleaseFixture -Root $TestDrive
        $release = New-TestRelease -Fixture $fixture
        $release.ManifestUrl = 'https://github.com/other/repository/releases/download/v0.5.2/release-manifest.json'
        Mock-TestDownloads -Fixture $fixture
        { Get-VerifiedRelease -Release $release -DownloadRoot (Join-Path $TestDrive 'downloads') } |
            Should Throw 'release_metadata_url_invalid'
    }

    It 'rejects modified, extra, and missing release members by manifest equality and hashes' {
        $cases = @(
            @{ Fixture = (Save-TestReleaseFixture -Root (Join-Path $TestDrive 'modified') -MismatchedHash); Error = 'release_file_checksum_mismatch' },
            @{ Fixture = (Save-TestReleaseFixture -Root (Join-Path $TestDrive 'extra-manifest') -ManifestNames @('README.md','docs/extra.md')); Error = 'release_manifest_member_set_mismatch' },
            @{ Fixture = (Save-TestReleaseFixture -Root (Join-Path $TestDrive 'missing-manifest') -ManifestNames @() -ZipMembers @{ 'README.md' = 'safe readme' }); Error = 'release_manifest_member_set_mismatch' }
        )
        foreach ($case in $cases) {
            $release = New-TestRelease -Fixture $case.Fixture
            Mock-TestDownloads -Fixture $case.Fixture
            { Get-VerifiedRelease -Release $release -DownloadRoot (Join-Path $TestDrive ([guid]::NewGuid().ToString('N'))) } |
                Should Throw $case.Error
        }
    }

    It 'removes stale partial files and failed extraction residue while preserving unrelated root contents' {
        $downloadRoot = Join-Path $TestDrive 'cleanup-downloads'
        New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $downloadRoot 'codex-obsidian-manuscript-starter-v0.5.2.zip.partial') -Value 'stale' -Encoding ASCII
        $fixture = Save-TestReleaseFixture -Root (Join-Path $TestDrive 'cleanup-fixture')
        $release = New-TestRelease -Fixture $fixture
        Mock Invoke-WebRequest -ModuleName release-acquisition { throw 'download failed' }
        { Get-VerifiedRelease -Release $release -DownloadRoot $downloadRoot } | Should Throw
        Test-Path -LiteralPath (Join-Path $downloadRoot 'codex-obsidian-manuscript-starter-v0.5.2.zip.partial') |
            Should Be $false

        $conflictRoot = Join-Path $TestDrive 'conflict-fixture'
        $conflictFixture = Save-TestReleaseFixture -Root $conflictRoot -ManifestNames @('README.md','bootstrap/conflict','bootstrap/conflict/child.txt') -ZipMembers @{
            'README.md' = 'safe readme'
            'bootstrap/conflict' = 'file first'
            'bootstrap/conflict/child.txt' = 'child'
        }
        $release = New-TestRelease -Fixture $conflictFixture
        Set-Content -LiteralPath (Join-Path $downloadRoot 'keep.txt') -Value 'keep' -Encoding ASCII
        Mock-TestDownloads -Fixture $conflictFixture
        { Get-VerifiedRelease -Release $release -DownloadRoot $downloadRoot } | Should Throw
        Test-Path -LiteralPath (Join-Path $downloadRoot 'keep.txt') | Should Be $true
        @((Get-ChildItem -LiteralPath $downloadRoot -Directory -ErrorAction SilentlyContinue)).Count | Should Be 0
    }

    AfterEach {
        Remove-Variable -Name ReleaseAcquisitionTestFixture -Scope Global -ErrorAction SilentlyContinue
    }
}
