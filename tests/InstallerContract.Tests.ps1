$repoRoot = Split-Path -Parent $PSScriptRoot
$environmentModule = Join-Path $repoRoot "bootstrap\lib\Environment.psm1"
$vaultModule = Join-Path $repoRoot "bootstrap\lib\Vault.psm1"
$restModule = Join-Path $repoRoot "bootstrap\lib\LocalRest.psm1"
$lockPath = Join-Path $repoRoot "dependencies.lock.json"

Describe "Beginner installer safety contract" {
    It "ships install, doctor, and non-destructive uninstall entry points" {
        Test-Path (Join-Path $repoRoot "bootstrap\install-windows.ps1") | Should Be $true
        Test-Path (Join-Path $repoRoot "bootstrap\doctor.ps1") | Should Be $true
        Test-Path (Join-Path $repoRoot "bootstrap\uninstall.ps1") | Should Be $true
    }

    It "ships the exact same bootstrap files inside the installable plugin" {
        $pluginBootstrap = Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap"
        Test-Path (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-setup\SKILL.md") | Should Be $true
        foreach ($file in @("install-windows.ps1", "doctor.ps1", "uninstall.ps1", "dependencies.lock.json", "lib\Environment.psm1", "lib\Vault.psm1", "lib\LocalRest.psm1")) {
            (Get-FileHash -LiteralPath (Join-Path $repoRoot ("bootstrap\" + $file.Replace("dependencies.lock.json", "..\dependencies.lock.json"))) -Algorithm SHA256).Hash | Should Be (Get-FileHash -LiteralPath (Join-Path $pluginBootstrap $file) -Algorithm SHA256).Hash
        }
    }

    It "exposes the three installation modules" {
        Test-Path $environmentModule | Should Be $true
        Test-Path $vaultModule | Should Be $true
        Test-Path $restModule | Should Be $true
    }

    It "requires explicit consent before it enables community plugin code" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        { Install-PinnedLocalRestPlugin -VaultPath (Join-Path $TestDrive "vault") } | Should Throw
    }

    It "refuses a non-empty vault target unless the caller explicitly allows only an empty vault" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $target = Join-Path $TestDrive "existing-vault"
        New-Item -ItemType Directory -Path $target | Out-Null
        Set-Content -LiteralPath (Join-Path $target "personal-note.md") -Value "do not overwrite"
        { Initialize-StarterVault -VaultPath $target } | Should Throw
    }

    It "refuses to overwrite an existing Local REST plugin and its credentials" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        Get-Command Assert-LocalRestPluginTargetIsSafe -ErrorAction SilentlyContinue | Should Not BeNullOrEmpty
        $pluginPath = Join-Path $TestDrive ".obsidian\plugins\obsidian-local-rest-api"
        New-Item -ItemType Directory -Path $pluginPath -Force | Out-Null
        $dataPath = Join-Path $pluginPath "data.json"
        Set-Content -LiteralPath $dataPath -Value '{"apiKey":"private"}'
        { Assert-LocalRestPluginTargetIsSafe -VaultPath $TestDrive -PluginId "obsidian-local-rest-api" } | Should Throw
        Test-Path $dataPath | Should Be $true
    }

    It "pins the Local REST dependency to an HTTPS URL and SHA-256 digest" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        $lock = Get-LocalRestLock -LockPath $lockPath
        $lock.version | Should Match '^\d+\.\d+\.\d+$'
        @($lock.assets).Count | Should Be 3
        foreach ($asset in @($lock.assets)) {
            $asset.url | Should Match '^https://'
            $asset.sha256 | Should Match '^[0-9a-f]{64}$'
        }
    }

    It "loads only non-secret runtime paths from the local runtime configuration" {
        if (-not (Test-Path $environmentModule)) { throw "Environment module is missing" }
        Import-Module $environmentModule -Force
        $runtimeRoot = Join-Path $TestDrive "runtime"
        $paths = Resolve-InstallPaths -VaultPath (Join-Path $TestDrive "vault") -RuntimeRoot $runtimeRoot
        Save-RuntimeConfig -Paths $paths | Out-Null
        $loaded = Get-RuntimeConfig -RuntimeConfigPath $paths.RuntimeConfigPath
        $loaded.vaultPath | Should Be $paths.VaultPath
        $loaded.restDataPath | Should Be $paths.RestDataPath
        (Get-Content -Raw -LiteralPath $paths.RuntimeConfigPath) | Should Not Match 'apiKey|token|secret'
    }

    It "detects the standard per-user Obsidian installation path" {
        if (-not (Test-Path $environmentModule)) { throw "Environment module is missing" }
        Import-Module $environmentModule -Force
        Get-Command Find-ObsidianExecutable -ErrorAction SilentlyContinue | Should Not BeNullOrEmpty
        $localAppData = Join-Path $TestDrive "LocalAppData"
        $executable = Join-Path $localAppData "Programs\Obsidian\Obsidian.exe"
        New-Item -ItemType Directory -Path (Split-Path -Parent $executable) -Force | Out-Null
        Set-Content -LiteralPath $executable -Value "test executable"
        Find-ObsidianExecutable -LocalAppDataRoot $localAppData -ProgramFilesRoot (Join-Path $TestDrive "ProgramFiles") | Should Be $executable
    }

    It "refuses a Local REST round trip when the API key is absent" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        Get-Command Test-LocalRestRoundTrip -ErrorAction SilentlyContinue | Should Not BeNullOrEmpty
        $dataPath = Join-Path $TestDrive "data.json"
        Set-Content -LiteralPath $dataPath -Value '{"port":27124}' -Encoding UTF8
        { Test-LocalRestRoundTrip -DataPath $dataPath } | Should Throw
    }
}
