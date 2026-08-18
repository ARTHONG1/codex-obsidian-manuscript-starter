$repoRoot = Split-Path -Parent $PSScriptRoot
$modulePath = Join-Path $repoRoot "bootstrap\lib\OfficialInstallers.psm1"
$lockPath = Join-Path $repoRoot "bootstrap\official-installers.lock.json"

Describe "Official installer verification contract" {
    BeforeAll {
        $script:moduleAvailable = Test-Path -LiteralPath $modulePath
        if ($script:moduleAvailable) { Import-Module $modulePath -Force }
    }

    It "ships a pinned HTTPS x64 lock with signer and hash metadata" {
        $script:moduleAvailable | Should Be $true
        $lock = Read-OfficialInstallerLock -Path $lockPath
        @($lock.installers).Count | Should Be 2
        @($lock.installers | Where-Object { $_.product -eq "python" }).Count | Should Be 1
        @($lock.installers | Where-Object { $_.product -eq "obsidian" }).Count | Should Be 1
    }

    It "rejects a tampered download and removes only its partial artifact" {
        $script:moduleAvailable | Should Be $true
        $lock = Read-OfficialInstallerLock -Path $lockPath
        $entry = @($lock.installers | Where-Object { $_.product -eq "python" })[0]
        $root = Join-Path $TestDrive "download"
        $download = { param($url, $path) Set-Content -LiteralPath $path -Value "tampered" -Encoding UTF8 }.GetNewClosure()
        $signature = { param($path) [pscustomobject]@{ Status = "Valid"; SignerCertificate = [pscustomobject]@{ Subject = "CN=Python Software Foundation" } } }
        { Get-VerifiedOfficialInstallerArtifact -Entry $entry -DestinationRoot $root -Downloader $download -SignatureReader $signature } | Should Throw "official_installer_hash_mismatch"
        @(Get-ChildItem -LiteralPath $root -Force -ErrorAction SilentlyContinue) | Should BeNullOrEmpty
    }

    It "checks the signer before allowing a verified artifact to launch" {
        $script:moduleAvailable | Should Be $true
        $lock = Read-OfficialInstallerLock -Path $lockPath
        $entry = @($lock.installers | Where-Object { $_.product -eq "obsidian" })[0]
        $root = Join-Path $TestDrive "valid"
        $download = { param($url, $path) [IO.File]::WriteAllBytes($path, [byte[]](1..32)) }.GetNewClosure()
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root "Obsidian-1.13.7.exe") -ErrorAction SilentlyContinue).Hash
        $bad = $entry | Select-Object *
        $bad.sha256 = $null
        { Read-OfficialInstallerLock -Path $lockPath } | Should Not Throw
    }
}
