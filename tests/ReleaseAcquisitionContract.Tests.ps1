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
}
