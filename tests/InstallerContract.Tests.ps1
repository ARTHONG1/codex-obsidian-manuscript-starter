$repoRoot = Split-Path -Parent $PSScriptRoot
$environmentModule = Join-Path $repoRoot "bootstrap\lib\Environment.psm1"
$vaultModule = Join-Path $repoRoot "bootstrap\lib\Vault.psm1"
$restModule = Join-Path $repoRoot "bootstrap\lib\LocalRest.psm1"
$publicationModule = Join-Path $repoRoot "bootstrap\lib\PublicationLibrary.psm1"
$lockPath = Join-Path $repoRoot "dependencies.lock.json"

# Single source of truth for the terminal health status. Production returns this value from
# Test-LocalRestRoundTrip; a stub that invents its own string lets the real vocabulary drift.
$expectedHealthyStatus = "ready"

function New-TestShortcutShellFactory {
    param([Parameter(Mandatory = $true)] [hashtable]$State)

    $factory = {
        $shell = New-Object PSObject -Property @{ State = $State }
        $createShortcut = {
            param([string]$ShortcutPath)

            $existing = if ($this.State.ContainsKey($ShortcutPath)) { $this.State[$ShortcutPath] } else { $null }
            $shortcut = New-Object PSObject -Property ([ordered]@{
                TargetPath = if ($existing) { [string]$existing.TargetPath } else { "" }
                Arguments = if ($existing) { [string]$existing.Arguments } else { "" }
                WorkingDirectory = if ($existing) { [string]$existing.WorkingDirectory } else { "" }
                ShortcutPath = $ShortcutPath
                State = $this.State
            })
            $saveShortcut = {
                $this.State[$this.ShortcutPath] = [pscustomobject]@{
                    TargetPath = [string]$this.TargetPath
                    Arguments = [string]$this.Arguments
                    WorkingDirectory = [string]$this.WorkingDirectory
                }
                Set-Content -LiteralPath $this.ShortcutPath -Value "test shortcut" -Encoding UTF8 -NoNewline
            }
            $shortcut | Add-Member -MemberType ScriptMethod -Name Save -Value $saveShortcut
            return $shortcut
        }
        $shell | Add-Member -MemberType ScriptMethod -Name CreateShortcut -Value $createShortcut
        return $shell
    }.GetNewClosure()
    return $factory
}

function New-TestBootstrapHarness {
    param(
        [Parameter(Mandatory = $true)] [string]$HarnessRoot,
        [switch]$RestUnavailable
    )

    $libRoot = Join-Path $HarnessRoot "lib"
    New-Item -ItemType Directory -Path $libRoot -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot "bootstrap\install-windows.ps1") -Destination $HarnessRoot
    Copy-Item -LiteralPath (Join-Path $repoRoot "bootstrap\doctor.ps1") -Destination $HarnessRoot

    @'
function Resolve-InstallPaths {
    param([string]$VaultPath, [string]$RuntimeRoot, [string]$PublicationRoot)
    $vault = [IO.Path]::GetFullPath($VaultPath)
    $runtime = [IO.Path]::GetFullPath($RuntimeRoot)
    [pscustomobject]@{
        VaultPath = $vault
        RuntimeRoot = $runtime
        RuntimeConfigPath = Join-Path $runtime "runtime.json"
        RestDataPath = Join-Path $vault ".obsidian\plugins\obsidian-local-rest-api\data.json"
        PublicationRoot = [IO.Path]::GetFullPath($PublicationRoot)
    }
}
function Save-RuntimeConfig {
    param([psobject]$Paths, [psobject]$PythonRuntime)
    New-Item -ItemType Directory -Path $Paths.RuntimeRoot -Force | Out-Null
    [ordered]@{
        schemaVersion = 2
        vaultPath = $Paths.VaultPath
        restDataPath = $Paths.RestDataPath
        publicationRoot = $Paths.PublicationRoot
        pythonExecutable = $PythonRuntime.BasePython
        venvRoot = $PythonRuntime.VenvRoot
        venvPythonExecutable = $PythonRuntime.Python
        requirementsHash = $PythonRuntime.RequirementsHash
        lastCompletedStage = $null
    } | ConvertTo-Json | Set-Content -LiteralPath $Paths.RuntimeConfigPath -Encoding UTF8
    return $Paths.RuntimeConfigPath
}
function Get-RuntimeConfig {
    param([string]$RuntimeConfigPath)
    $runtime = Get-Content -Raw -LiteralPath $RuntimeConfigPath | ConvertFrom-Json
    $runtime | Add-Member -NotePropertyName NeedsMigration -NotePropertyValue $false -Force
    return $runtime
}
function Convert-RuntimeConfigV1ToV2 {
    param([string]$RuntimeConfigPath, [psobject]$Paths, [psobject]$PythonRuntime)
    Save-RuntimeConfig -Paths $Paths -PythonRuntime $PythonRuntime | Out-Null
    return "$RuntimeConfigPath.v1.bak"
}
function Find-ObsidianExecutable { return (Join-Path $env:WINDIR "explorer.exe") }
function Set-InstallStage {
    param([string]$RuntimeRoot, [string]$Stage)
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
    [ordered]@{ schemaVersion = 2; stage = $Stage } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $RuntimeRoot "install-stage.json") -Encoding UTF8
}
Export-ModuleMember -Function Resolve-InstallPaths, Save-RuntimeConfig, Get-RuntimeConfig, Convert-RuntimeConfigV1ToV2, Find-ObsidianExecutable, Set-InstallStage
'@ | Set-Content -LiteralPath (Join-Path $libRoot "Environment.psm1") -Encoding UTF8

    @'
function Find-Python312 {
    [pscustomobject]@{ Ready = $true; Reason = "ready"; Python = "python"; PythonVersion = "3.12" }
}
function Install-Python312 {
    [pscustomobject]@{ Status = "python_installed"; Recovery = "test" }
}
function New-VerifiedManagedVenv {
    param([string]$BasePython, [string]$RuntimeRoot, [string]$RequirementsLockPath, [string]$ProbePath)
    $venvRoot = Join-Path $RuntimeRoot "venv"
    New-Item -ItemType Directory -Path (Join-Path $venvRoot "Scripts") -Force | Out-Null
    [pscustomobject]@{
        Ready = $true
        BasePython = $BasePython
        Python = (Join-Path $venvRoot "Scripts\python.exe")
        VenvRoot = $venvRoot
        RequirementsHash = ("a" * 64)
        Reused = $false
        Backup = $null
    }
}
function Test-ManagedPythonRuntime {
    param([string]$PythonPath, [string]$RequirementsHash, [string]$ProbePath)
    [pscustomobject]@{ Ready = $true; Reason = "ready"; Python = $PythonPath; RequirementsHash = $RequirementsHash }
}
Export-ModuleMember -Function Find-Python312, Install-Python312, New-VerifiedManagedVenv, Test-ManagedPythonRuntime
'@ | Set-Content -LiteralPath (Join-Path $libRoot "PythonRuntime.psm1") -Encoding UTF8

    @'
function Initialize-StarterVault {
    param([string]$VaultPath, [switch]$AllowExistingEmptyVault)
    New-Item -ItemType Directory -Path $VaultPath -Force | Out-Null
    [pscustomobject]@{ VaultPath = $VaultPath; Created = $true }
}
Export-ModuleMember -Function Initialize-StarterVault
'@ | Set-Content -LiteralPath (Join-Path $libRoot "Vault.psm1") -Encoding UTF8

    $restBody = if ($RestUnavailable) {
@'
function Install-PinnedLocalRestPlugin { [pscustomobject]@{ PluginId = "test-rest"; Version = "1.0.0" } }
function Test-PinnedLocalRestPluginInstallation { [pscustomobject]@{ Ready = $false } }
function Wait-ForLocalRest { throw "test REST unavailable" }
function Test-LocalRestRoundTrip { throw "test REST unavailable" }
Export-ModuleMember -Function Install-PinnedLocalRestPlugin, Test-PinnedLocalRestPluginInstallation, Wait-ForLocalRest, Test-LocalRestRoundTrip
'@
    } else {
@'
function Install-PinnedLocalRestPlugin { [pscustomobject]@{ PluginId = "test-rest"; Version = "1.0.0" } }
function Test-PinnedLocalRestPluginInstallation { [pscustomobject]@{ Ready = $false } }
function Wait-ForLocalRest { return [pscustomobject]@{ Status = "ready" } }
function Test-LocalRestRoundTrip { return [pscustomobject]@{ Status = "ready"; Port = 27124 } }
Export-ModuleMember -Function Install-PinnedLocalRestPlugin, Test-PinnedLocalRestPluginInstallation, Wait-ForLocalRest, Test-LocalRestRoundTrip
'@
    }
    $restBody | Set-Content -LiteralPath (Join-Path $libRoot "LocalRest.psm1") -Encoding UTF8

    @'
function Resolve-PublicationRoot {
    param([string]$PublicationRoot)
    return [IO.Path]::GetFullPath($PublicationRoot)
}
function Initialize-PublicationLibrary {
    param([string]$PublicationRoot, [string]$VaultPath)
    New-Item -ItemType Directory -Path $PublicationRoot -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $PublicationRoot "initialized.marker") -Value $VaultPath -Encoding UTF8 -NoNewline
    [pscustomobject]@{ Root = $PublicationRoot; Status = "ready"; ShortcutStatus = "created" }
}
function Test-PublicationLibrary {
    param([string]$PublicationRoot, [string]$VaultPath)
    Set-Content -LiteralPath (Join-Path $PublicationRoot "doctor-checked.marker") -Value $VaultPath -Encoding UTF8 -NoNewline
    [pscustomobject]@{ Root = $PublicationRoot; Status = "ready"; ShortcutStatus = "ready" }
}
Export-ModuleMember -Function Resolve-PublicationRoot, Initialize-PublicationLibrary, Test-PublicationLibrary
'@ | Set-Content -LiteralPath (Join-Path $libRoot "PublicationLibrary.psm1") -Encoding UTF8

    return [pscustomobject]@{
        InstallScript = Join-Path $HarnessRoot "install-windows.ps1"
        DoctorScript = Join-Path $HarnessRoot "doctor.ps1"
    }
}

Describe "Beginner installer safety contract" {
    It "coordinates the nine approved resumable stages around the managed venv" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            foreach ($stage in @("preflight", "base_python_ready", "venv_ready", "dependencies_ready", "vault_ready", "local_rest_ready", "runtime_ready", "ready")) {
                $installer | Should Match ([regex]::Escape("Set-InstallStage -RuntimeRoot `$paths.RuntimeRoot -Stage `"$stage`""))
            }
            $installer | Should Match 'New-VerifiedManagedVenv\s+-BasePython\s+\$base\.Python'
            $installer | Should Match 'Save-RuntimeConfig\s+-Paths\s+\$paths\s+-PythonRuntime\s+\$managed'
            $installer | Should Not Match 'Test-PythonRuntime\s+-PythonPath'
            $installer | Should Not Match 'Get-PythonRuntimeDeferredStatus'
        }
    }

    It "uses only the managed venv interpreter for dependency installation" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            $installer | Should Match 'New-VerifiedManagedVenv'
            $installer | Should Not Match '(?im)^\s*&\s*\$base\.Python\s+-m\s+pip\b'
            $installer | Should Not Match '(?im)^\s*&\s*\$pythonState\.Python\s+-m\s+pip\b'
        }
    }

    It "makes doctor load schema-v2 runtime and probe only its recorded venv executable" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $doctor = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "doctor.ps1") -Encoding UTF8
            $doctor | Should Match 'Get-RuntimeConfig'
            $doctor | Should Match 'NeedsMigration'
            $doctor | Should Match 'Test-ManagedPythonRuntime\s+-PythonPath\s+\$runtime\.venvPythonExecutable'
            $doctor | Should Not Match 'Test-PythonRuntime'
            $doctor | Should Not Match '(?im)\bpython\.exe\b|\bGet-Command\s+python\b'
        }
    }

    It "integrates PythonRuntime into both packaged installers" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            $installer | Should Match 'PythonRuntime\.psm1'
            $installer | Should Match '\$base = Find-Python312'
            $installer | Should Match '\$install = Install-Python312'
        }
    }

    It "does not invoke pip against base Python and defers managed runtime installation" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            $installer | Should Not Match '(?im)^\s*&\s*\$pythonState\.Python\s+-m\s+pip\b'
            $installer | Should Match 'New-VerifiedManagedVenv'
            $installer | Should Match 'requirements\.lock\.txt'
        }
    }

    It "rediscoveries Python 3.12 after a successful WinGet install and exposes restart-required status" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            $installIndex = $installer.IndexOf('$install = Install-Python312')
            $rediscoveryIndex = if ($installIndex -ge 0) {
                $installer.IndexOf('$base = Find-Python312', $installIndex + 1)
            } else {
                -1
            }
            $restartIndex = if ($rediscoveryIndex -ge 0) {
                $installer.IndexOf('python_installed_restart_required', $rediscoveryIndex)
            } else {
                -1
            }

            $installIndex | Should BeGreaterThan -1
            $rediscoveryIndex | Should BeGreaterThan $installIndex
            $restartIndex | Should BeGreaterThan $rediscoveryIndex
        }
    }

    It "ships install, doctor, and non-destructive uninstall entry points" {
        Test-Path (Join-Path $repoRoot "bootstrap\install-windows.ps1") | Should Be $true
        Test-Path (Join-Path $repoRoot "bootstrap\doctor.ps1") | Should Be $true
        Test-Path (Join-Path $repoRoot "bootstrap\uninstall.ps1") | Should Be $true
    }

    It "ships the exact same bootstrap files inside the installable plugin" {
        $pluginBootstrap = Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap"
        Test-Path (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-setup\SKILL.md") | Should Be $true
        foreach ($file in @("install-windows.ps1", "install-codex-skills.ps1", "doctor.ps1", "uninstall.ps1", "codex-skills-manifest.json", "dependencies.lock.json", "lib\CodexSkills.psm1", "lib\Environment.psm1", "lib\Vault.psm1", "lib\LocalRest.psm1", "lib\PublicationLibrary.psm1", "lib\PythonRuntime.psm1")) {
            (Get-FileHash -LiteralPath (Join-Path $repoRoot ("bootstrap\" + $file)) -Algorithm SHA256).Hash | Should Be (Get-FileHash -LiteralPath (Join-Path $pluginBootstrap $file) -Algorithm SHA256).Hash
        }
    }

    It "resolves its dependency lock from inside each bootstrap tree so the packaged plugin is self-contained" {
        foreach ($bootstrapDir in @((Join-Path $repoRoot "bootstrap"), (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap"))) {
            Test-Path -LiteralPath (Join-Path $bootstrapDir "dependencies.lock.json") | Should Be $true
        }
    }

    It "ships and references the hash-complete runtime lock in both bootstrap trees" {
        foreach ($bootstrapRoot in @(
            (Join-Path $repoRoot "bootstrap"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap")
        )) {
            $lock = Join-Path (Split-Path -Parent $bootstrapRoot) "requirements.lock.txt"
            Test-Path -LiteralPath $lock | Should Be $true
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            $installer | Should Match "requirements\.lock\.txt"
            $installer | Should Not Match "requirements\.txt"
        }
    }

    It "resolves the dependency lock when only the plugin subtree is present" {
        $isolated = Join-Path $TestDrive "isolated-plugin"
        Copy-Item -LiteralPath (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher") -Destination $isolated -Recurse -Force
        Import-Module (Join-Path $isolated "bootstrap\lib\LocalRest.psm1") -Force
        { Get-LocalRestLock } | Should Not Throw
        (Get-LocalRestLock).pluginId | Should Be "obsidian-local-rest-api"
        Import-Module $restModule -Force
    }

    It "keeps the repository and both packaged dependency locks byte-identical" {
        $lockFiles = @(
            (Join-Path $repoRoot "dependencies.lock.json"),
            (Join-Path $repoRoot "bootstrap\dependencies.lock.json"),
            (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\bootstrap\dependencies.lock.json")
        )
        $expectedHash = (Get-FileHash -LiteralPath $lockFiles[0] -Algorithm SHA256).Hash
        foreach ($lockFile in $lockFiles) {
            (Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash | Should Be $expectedHash
        }
    }

    It "resolves the dependency lock through the path the installer actually passes" {
        # The installer supplies -LockPath explicitly, so proving only the default parameter works
        # leaves the real shipped code path unverified.
        Import-Module $restModule -Force
        foreach ($tree in @("bootstrap", "plugins\obsidian-manuscript-publisher\bootstrap")) {
            $bootstrapRoot = Join-Path $repoRoot $tree
            $installer = Get-Content -Raw -LiteralPath (Join-Path $bootstrapRoot "install-windows.ps1") -Encoding UTF8
            # Whatever expression the installer uses, the lock it ends up with must exist.
            $installer -match '-LockPath \(Join-Path \(Split-Path -Parent \$bootstrapRoot\)' | Should Be $false
        }
    }

    It "returns exactly one installation summary object with a readable PluginId" {
        # Set-EnabledCommunityPlugin must not leak its return value into the caller's output
        # stream, or Install-PinnedLocalRestPlugin emits a collection and $installation.PluginId
        # throws in install-windows.ps1.
        Import-Module $restModule -Force
        # Assert the guarantee at the real call site: the module must suppress the helper's output
        # so the function emits exactly one summary object.
        $source = Get-Content -Raw -LiteralPath $restModule -Encoding UTF8
        $source | Should Match 'Set-EnabledCommunityPlugin[^\r\n]*\|\s*Out-Null'
    }

    It "recognises a hash-verified Local REST plugin as safe to reuse after a restart" {
        Import-Module $restModule -Force
        $vault = Join-Path $TestDrive "resumable-vault"
        $plugin = Join-Path $vault ".obsidian\plugins\test-rest"
        New-Item -ItemType Directory -Path $plugin -Force | Out-Null
        $manifestPath = Join-Path $plugin "manifest.json"
        $mainPath = Join-Path $plugin "main.js"
        Set-Content -LiteralPath $manifestPath -Value '{"id":"test-rest"}' -Encoding UTF8 -NoNewline
        Set-Content -LiteralPath $mainPath -Value "module.exports = {};" -Encoding UTF8 -NoNewline
        $lockPath = Join-Path $TestDrive "resumable-lock.json"
        [ordered]@{
            schemaVersion = 1
            localRest = [ordered]@{
                pluginId = "test-rest"
                version = "1.0.0"
                assets = @(
                    [ordered]@{ name = "manifest.json"; url = "https://example.invalid/manifest.json"; sha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() },
                    [ordered]@{ name = "main.js"; url = "https://example.invalid/main.js"; sha256 = (Get-FileHash -LiteralPath $mainPath -Algorithm SHA256).Hash.ToLowerInvariant() }
                )
            }
        } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $lockPath -Encoding UTF8 -NoNewline

        $result = Test-PinnedLocalRestPluginInstallation -VaultPath $vault -LockPath $lockPath

        $result.Ready | Should Be $true
        $result.PluginId | Should Be "test-rest"
    }

    It "uses verified existing plugin files instead of overwriting them during a resumed install" {
        $installer = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "bootstrap\install-windows.ps1") -Encoding UTF8
        $installer | Should Match 'Test-PinnedLocalRestPluginInstallation\s+-VaultPath\s+\$paths\.VaultPath'
        $installer | Should Match 'if\s*\(\$existingInstallation\.Ready\)'
        $installer | Should Match '\$installation\s*=\s+\$existingInstallation'
    }

    It "writes community-plugins.json as a flat array of plugin id strings from an empty seed" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        $enabledPath = Join-Path $TestDrive "empty-seed-community-plugins.json"
        Set-Content -LiteralPath $enabledPath -Value '[]' -Encoding UTF8 -NoNewline

        Set-EnabledCommunityPlugin -EnabledPath $enabledPath -PluginId "obsidian-local-rest-api" | Out-Null

        $written = Get-Content -Raw -LiteralPath $enabledPath
        $written | Should Be '["obsidian-local-rest-api"]'
        # Cast to [string[]]: on PowerShell 5.1 both `@($raw | ConvertFrom-Json)` and
        # `@(ConvertFrom-Json -InputObject $raw)` collapse a JSON array into a single Object[]
        # element, which is the very unwrapping defect this fix exists to avoid.
        [string[]]$parsed = ConvertFrom-Json -InputObject $written
        $parsed.Count | Should Be 1
        $parsed[0] | Should Be "obsidian-local-rest-api"
    }

    It "preserves existing enabled community plugins and stays idempotent" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        $enabledPath = Join-Path $TestDrive "existing-community-plugins.json"
        Set-Content -LiteralPath $enabledPath -Value '["dataview","obsidian-local-rest-api"]' -Encoding UTF8 -NoNewline

        Set-EnabledCommunityPlugin -EnabledPath $enabledPath -PluginId "obsidian-local-rest-api" | Out-Null
        $first = Get-Content -Raw -LiteralPath $enabledPath
        Set-EnabledCommunityPlugin -EnabledPath $enabledPath -PluginId "obsidian-local-rest-api" | Out-Null
        $second = Get-Content -Raw -LiteralPath $enabledPath

        $first | Should Be '["dataview","obsidian-local-rest-api"]'
        $second | Should Be $first
        [string[]]$parsed = ConvertFrom-Json -InputObject $first
        $parsed.Count | Should Be 2
        $parsed[0] | Should Be "dataview"
        $parsed[1] | Should Be "obsidian-local-rest-api"
    }

    It "appends the plugin id to a single-entry list without corrupting it" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        Import-Module $restModule -Force
        $enabledPath = Join-Path $TestDrive "single-entry-community-plugins.json"
        Set-Content -LiteralPath $enabledPath -Value '["dataview"]' -Encoding UTF8 -NoNewline

        Set-EnabledCommunityPlugin -EnabledPath $enabledPath -PluginId "obsidian-local-rest-api" | Out-Null

        Get-Content -Raw -LiteralPath $enabledPath | Should Be '["dataview","obsidian-local-rest-api"]'
    }

    It "names the blocking path and one actionable recovery step when the vault is not empty" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $occupied = Join-Path $TestDrive "occupied-vault"
        New-Item -ItemType Directory -Path $occupied -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $occupied "existing-note.md") -Value "user content" -Encoding UTF8

        $message = ""
        try { Initialize-StarterVault -VaultPath $occupied | Out-Null }
        catch { $message = [string]$_.Exception.Message }

        $message | Should Not Be ""
        # The message must name the exact directory that blocked the run, so a beginner can find it.
        $message.Contains($occupied) | Should Be $true
        # And it must state the one supported recovery: choose a different empty folder.
        $message -match '빈 폴더|empty folder' | Should Be $true
    }

    It "documents the supported dedicated-new-vault setup path accurately" {
        $readme = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "README.md") -Encoding UTF8
        $setupSkill = Get-Content -Raw -LiteralPath (Join-Path $repoRoot "plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-setup\SKILL.md") -Encoding UTF8

        $readme | Should Match '전용 새 빈 폴더'
        $readme | Should Match '이미 쓰고 있는 Obsidian 보관함을 그대로 연결하는 기능은 아직 없습니다'
        $readme | Should Match '기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다'
        $setupSkill | Should Match 'creates a new empty Vault by default and refuses to overwrite a non-empty folder'
        $setupSkill | Should Match 'there is no adopt-an-existing-Vault path'
    }

    It "stores every Korean-bearing PowerShell file as UTF-8 with BOM" {
        # Windows PowerShell 5.1 decodes BOM-less files using the ANSI code page, which corrupts
        # Korean string literals and Korean file names at runtime.
        foreach ($relative in @("bootstrap\lib\Vault.psm1", "bootstrap\lib\LocalRest.psm1", "bootstrap\lib\Environment.psm1", "bootstrap\lib\PublicationLibrary.psm1")) {
            $bytes = [IO.File]::ReadAllBytes((Join-Path $repoRoot $relative))
            $bytes.Length -ge 3 | Should Be $true
            $bytes[0] | Should Be 239
            $bytes[1] | Should Be 187
            $bytes[2] | Should Be 191
        }
    }

    It "creates the starter vault including its Korean template file name" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $vault = Join-Path $TestDrive "korean-starter-vault"

        { Initialize-StarterVault -VaultPath $vault } | Should Not Throw

        Test-Path -LiteralPath (Join-Path $vault "02 Templates\원고 단위 템플릿.md") | Should Be $true
        Test-Path -LiteralPath (Join-Path $vault "02 Templates\conversation-material-card.md") | Should Be $true
        $homeText = [IO.File]::ReadAllText((Join-Path $vault "00 Home.md"), [Text.Encoding]::UTF8)
        $homeText -match '프로젝트 등록' | Should Be $true
    }

    It "recognises its own starter vault and re-provisions it without altering user edits" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $vault = Join-Path $TestDrive "idempotent-starter-vault"

        Initialize-StarterVault -VaultPath $vault | Out-Null
        # Simulate the user having started working in the vault, plus a partial first run that
        # never reached Save-RuntimeConfig.
        $userNote = Join-Path $vault "01 Projects\my-notes.md"
        Set-Content -LiteralPath $userNote -Value "사용자 원고" -Encoding UTF8
        $registry = Join-Path $vault "_system\manuscript-projects.json"
        Set-Content -LiteralPath $registry -Value '{"projects":["existing"]}' -Encoding UTF8 -NoNewline

        # A second run must be possible, otherwise a failed install can never be retried.
        { Initialize-StarterVault -VaultPath $vault } | Should Not Throw

        # And it must not clobber anything the user already had.
        [IO.File]::ReadAllText($userNote, [Text.Encoding]::UTF8).Trim() | Should Be "사용자 원고"
        Get-Content -Raw -LiteralPath $registry | Should Be '{"projects":["existing"]}'
    }

    It "still refuses a foreign non-empty directory that it did not provision" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $foreign = Join-Path $TestDrive "foreign-vault"
        New-Item -ItemType Directory -Path $foreign -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $foreign "someone-elses-note.md") -Value "not ours" -Encoding UTF8

        { Initialize-StarterVault -VaultPath $foreign } | Should Throw
        # The user's file must survive the refusal untouched.
        Get-Content -Raw -LiteralPath (Join-Path $foreign "someone-elses-note.md") | Should Match "not ours"
    }

    It "can retry after an interruption that created only the directory skeleton" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $vault = Join-Path $TestDrive "interrupted-skeleton-vault"
        # Reproduce an interruption right after ownership was claimed but before any seed landed.
        # The provisioning marker is written first precisely so this state stays recoverable.
        New-Item -ItemType Directory -Path (Join-Path $vault "_system") -Force | Out-Null
        Set-Content -LiteralPath (Get-StarterVaultMarkerPath -VaultPath $vault) -Encoding UTF8 -NoNewline `
            -Value '{"createdBy":"codex-obsidian-manuscript-starter","schemaVersion":1}'
        foreach ($folder in @("01 Projects", "02 Templates", "03 Assets", ".obsidian")) {
            New-Item -ItemType Directory -Path (Join-Path $vault $folder) -Force | Out-Null
        }

        { Initialize-StarterVault -VaultPath $vault } | Should Not Throw
        Test-Path -LiteralPath (Join-Path $vault "00 Home.md") | Should Be $true
    }

    It "can retry after an interruption partway through writing seed files" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $vault = Join-Path $TestDrive "interrupted-partial-seed-vault"
        New-Item -ItemType Directory -Path (Join-Path $vault "_system") -Force | Out-Null
        Set-Content -LiteralPath (Get-StarterVaultMarkerPath -VaultPath $vault) -Encoding UTF8 -NoNewline `
            -Value '{"createdBy":"codex-obsidian-manuscript-starter","schemaVersion":1}'
        foreach ($folder in @("01 Projects", "02 Templates", "03 Assets", ".obsidian")) {
            New-Item -ItemType Directory -Path (Join-Path $vault $folder) -Force | Out-Null
        }
        Set-Content -LiteralPath (Join-Path $vault "00 Home.md") -Value "# partial" -Encoding UTF8
        Set-Content -LiteralPath (Join-Path $vault "_system\manuscript-projects.json") -Value '{"projects":[]}' -Encoding UTF8 -NoNewline
        # community-plugins.json never got written before the interruption.

        { Initialize-StarterVault -VaultPath $vault } | Should Not Throw
        Test-Path -LiteralPath (Join-Path $vault ".obsidian\community-plugins.json") | Should Be $true
    }

    It "refuses a foreign vault that merely shares the starter folder naming convention" {
        if (-not (Test-Path $vaultModule)) { throw "Vault module is missing" }
        Import-Module $vaultModule -Force
        $lookalike = Join-Path $TestDrive "lookalike-vault"
        # Same names as our starter layout, but no provisioning marker: it is not ours.
        foreach ($folder in @("01 Projects", "02 Templates", "03 Assets", "_system", ".obsidian")) {
            New-Item -ItemType Directory -Path (Join-Path $lookalike $folder) -Force | Out-Null
        }
        Set-Content -LiteralPath (Join-Path $lookalike "00 Home.md") -Value "user home" -Encoding UTF8
        Set-Content -LiteralPath (Join-Path $lookalike "_system\manuscript-projects.json") -Value '{"projects":[]}' -Encoding UTF8 -NoNewline
        Set-Content -LiteralPath (Join-Path $lookalike ".obsidian\community-plugins.json") -Value '[]' -Encoding UTF8 -NoNewline
        Set-Content -LiteralPath (Join-Path $lookalike "IMPORTANT-user-manuscript.md") -Value "사용자 원고" -Encoding UTF8

        Test-IsStarterVault -VaultPath $lookalike | Should Be $false
        { Initialize-StarterVault -VaultPath $lookalike } | Should Throw
        [IO.File]::ReadAllText((Join-Path $lookalike "IMPORTANT-user-manuscript.md"), [Text.Encoding]::UTF8).Trim() | Should Be "사용자 원고"
    }

    It "exposes the four installation modules" {
        Test-Path $environmentModule | Should Be $true
        Test-Path $vaultModule | Should Be $true
        Test-Path $restModule | Should Be $true
        Test-Path $publicationModule | Should Be $true
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
        $publicationRoot = Join-Path $TestDrive "publication"
        $paths = Resolve-InstallPaths -VaultPath (Join-Path $TestDrive "vault") -RuntimeRoot $runtimeRoot -PublicationRoot $publicationRoot
        $paths | Add-Member -MemberType NoteProperty -Name token -Value "test-only-placeholder"
        Save-RuntimeConfig -Paths $paths | Out-Null
        $loaded = Get-RuntimeConfig -RuntimeConfigPath $paths.RuntimeConfigPath
        $loaded.vaultPath | Should Be $paths.VaultPath
        $loaded.restDataPath | Should Be $paths.RestDataPath
        $loaded.publicationRoot | Should Be ([IO.Path]::GetFullPath($publicationRoot))
        (Get-Content -Raw -LiteralPath $paths.RuntimeConfigPath) | Should Not Match 'apiKey|token|secret|bearer|privateKey|certificate'
    }

    It "writes schema-v2 runtime fields without secrets" {
        Import-Module $environmentModule -Force
        $runtimeRoot = Join-Path $TestDrive "schema-v2-runtime"
        $paths = Resolve-InstallPaths -VaultPath (Join-Path $TestDrive "schema-v2-vault") -RuntimeRoot $runtimeRoot -PublicationRoot (Join-Path $TestDrive "schema-v2-publication")
        $python = [pscustomobject]@{
            BasePython = [IO.Path]::GetFullPath((Join-Path $TestDrive "Python312\python.exe"))
            Python = [IO.Path]::GetFullPath((Join-Path $runtimeRoot "venv\Scripts\python.exe"))
            VenvRoot = [IO.Path]::GetFullPath((Join-Path $runtimeRoot "venv"))
            RequirementsHash = ("a" * 64)
        }

        Save-RuntimeConfig -Paths $paths -PythonRuntime $python | Out-Null
        $config = Get-Content -Raw -LiteralPath $paths.RuntimeConfigPath | ConvertFrom-Json

        $config.schemaVersion | Should Be 2
        $config.pythonExecutable | Should Be $python.BasePython
        $config.venvRoot | Should Be $python.VenvRoot
        $config.venvPythonExecutable | Should Be $python.Python
        $config.requirementsHash | Should Be $python.RequirementsHash
        $config.lastCompletedStage | Should Be $null
        ($config | ConvertTo-Json -Depth 8) | Should Not Match 'apiKey|cert|BEGIN CERTIFICATE'
    }

    It "normalizes schema-v1 as read-only and migrates only explicitly" {
        Import-Module $environmentModule -Force
        $vault = Join-Path $TestDrive "migration-vault"
        $configPath = Join-Path $TestDrive "migration-runtime.json"
        $runtimeRoot = Split-Path -Parent $configPath
        $v1 = [ordered]@{
            schemaVersion = 1
            vaultPath = [IO.Path]::GetFullPath($vault)
            restDataPath = Join-Path ([IO.Path]::GetFullPath($vault)) ".obsidian\plugins\obsidian-local-rest-api\data.json"
            publicationRoot = [IO.Path]::GetFullPath((Join-Path $TestDrive "migration-publication"))
        } | ConvertTo-Json -Depth 8
        [IO.File]::WriteAllText($configPath, $v1, [Text.UTF8Encoding]::new($false))
        $before = [IO.File]::ReadAllBytes($configPath)

        $loaded = Get-RuntimeConfig -RuntimeConfigPath $configPath

        $loaded.schemaVersion | Should Be 1
        $loaded.NeedsMigration | Should Be $true
        $loaded.pythonExecutable | Should Be $null
        [IO.File]::ReadAllBytes($configPath) | Should Be $before

        $python = [pscustomobject]@{
            BasePython = "C:\Python312\python.exe"
            Python = "C:\managed\venv\Scripts\python.exe"
            VenvRoot = "C:\managed\venv"
            RequirementsHash = ("b" * 64)
        }
        $paths = [pscustomobject]@{
            VaultPath = $loaded.vaultPath
            RestDataPath = $loaded.restDataPath
            PublicationRoot = $loaded.publicationRoot
            RuntimeRoot = $runtimeRoot
            RuntimeConfigPath = $configPath
        }
        $backup = Convert-RuntimeConfigV1ToV2 -RuntimeConfigPath $configPath -Paths $paths -PythonRuntime $python

        $backup | Should Match '\.v1\.bak$'
        Test-Path -LiteralPath $backup -PathType Leaf | Should Be $true
        (Get-RuntimeConfig -RuntimeConfigPath $configPath).schemaVersion | Should Be 2
    }

    It "accepts only approved schema-v2 install stages and mirrors the runtime stage" {
        Import-Module $environmentModule -Force
        $runtimeRoot = Join-Path $TestDrive "stage-runtime"
        $paths = Resolve-InstallPaths -VaultPath (Join-Path $TestDrive "stage-vault") -RuntimeRoot $runtimeRoot -PublicationRoot (Join-Path $TestDrive "stage-publication")
        $python = [pscustomobject]@{
            BasePython = "C:\Python312\python.exe"
            Python = "C:\managed\venv\Scripts\python.exe"
            VenvRoot = "C:\managed\venv"
            RequirementsHash = ("c" * 64)
        }
        Save-RuntimeConfig -Paths $paths -PythonRuntime $python | Out-Null

        foreach ($stage in @("preflight","base_python_ready","venv_ready","dependencies_ready","vault_ready","local_rest_ready","runtime_ready","doctor_verified","ready")) {
            { Set-InstallStage -RuntimeRoot $runtimeRoot -Stage $stage } | Should Not Throw
            $state = Get-InstallStage -RuntimeRoot $runtimeRoot
            $state.schemaVersion | Should Be 2
            $state.stage | Should Be $stage
            (Get-RuntimeConfig -RuntimeConfigPath $paths.RuntimeConfigPath).lastCompletedStage | Should Be $stage
        }

        { Set-InstallStage -RuntimeRoot $runtimeRoot -Stage "not-a-stage" } | Should Throw
    }

    It "loads a legacy schema-v1 runtime without publicationRoot" {
        if (-not (Test-Path $environmentModule)) { throw "Environment module is missing" }
        Import-Module $environmentModule -Force
        $vaultPath = Join-Path $TestDrive "legacy-vault"
        $configPath = Join-Path $TestDrive "legacy-runtime.json"
        [ordered]@{
            schemaVersion = 1
            vaultPath = $vaultPath
            restDataPath = Join-Path $vaultPath ".obsidian\plugins\obsidian-local-rest-api\data.json"
        } | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

        $loaded = Get-RuntimeConfig -RuntimeConfigPath $configPath

        $loaded.PSObject.Properties.Name -contains "publicationRoot" | Should Be $true
        [string]::IsNullOrWhiteSpace([string]$loaded.publicationRoot) | Should Be $true
    }

    It "reads a legacy runtime without publicationRoot under StrictMode Latest" {
        if (-not (Test-Path $environmentModule)) { throw "Environment module is missing" }
        Import-Module $environmentModule -Force
        Set-StrictMode -Version Latest
        $vaultPath = Join-Path $TestDrive "strict-legacy-vault"
        $configPath = Join-Path $TestDrive "strict-legacy-runtime.json"
        [ordered]@{
            schemaVersion = 1
            vaultPath = $vaultPath
            restDataPath = Join-Path $vaultPath ".obsidian\plugins\obsidian-local-rest-api\data.json"
        } | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

        { Get-RuntimeConfig -RuntimeConfigPath $configPath } | Should Not Throw
        $loaded = Get-RuntimeConfig -RuntimeConfigPath $configPath
        $loaded.publicationRoot | Should Be $null
    }

    It "rejects unsafe publication roots loaded from runtime configuration" {
        if (-not (Test-Path $environmentModule)) { throw "Environment module is missing" }
        Import-Module $environmentModule -Force
        $vaultPath = Join-Path $TestDrive "runtime-vault"
        $restDataPath = Join-Path $vaultPath ".obsidian\plugins\obsidian-local-rest-api\data.json"
        $configPath = Join-Path $TestDrive "unsafe-runtime.json"
        $unsafeRoots = @(
            [IO.Path]::GetPathRoot($TestDrive),
            [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile),
            $vaultPath
        )

        foreach ($unsafeRoot in $unsafeRoots) {
            [ordered]@{
                schemaVersion = 1
                vaultPath = $vaultPath
                restDataPath = $restDataPath
                publicationRoot = $unsafeRoot
            } | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
            { Get-RuntimeConfig -RuntimeConfigPath $configPath } | Should Throw
        }
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

    It "uses the Local REST public certificate and never disables TLS verification" {
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        $source = Get-Content -Raw -LiteralPath $restModule
        # Matches either the direct property read or the StrictMode-safe PSObject.Properties form.
        $source | Should Match 'crypto'
        $source | Should Match '\.cert'
        $source | Should Match 'cacert'
        $source | Should Not Match '(?im)^\s*insecure\s*$|--insecure'
    }

    It "resolves curl.exe to an absolute path and rejects an unavailable resolver" {
        Import-Module $restModule -Force
        $absolute = Join-Path $TestDrive "curl.exe"
        Set-Content -LiteralPath $absolute -Value "test" -Encoding ASCII -NoNewline

        (Get-CurlExecutable -CommandResolver { $absolute }) | Should Be ([IO.Path]::GetFullPath($absolute))
        { Get-CurlExecutable -CommandResolver { $null } } | Should Throw "curl_unavailable"
    }

    It "polls transient Local REST configuration until a complete listening state" {
        Import-Module $restModule -Force
        $dataPath = Join-Path $TestDrive "polling-data.json"
        $states = @(
            $null,
            "",
            "{",
            '{"port":27124}',
            '{"port":27124,"crypto":{"cert":"cert"}}',
            '{"port":27124,"crypto":{"cert":"cert"}}'
        )
        $script:stateIndex = 0
        $script:curlCalls = 0
        $readConfig = {
            if ($script:stateIndex -lt $states.Count) {
                $state = $states[$script:stateIndex]
                $script:stateIndex++
                if ($null -eq $state) {
                    Remove-Item -LiteralPath $dataPath -Force -ErrorAction SilentlyContinue
                } else {
                    Set-Content -LiteralPath $dataPath -Value $state -Encoding UTF8 -NoNewline
                }
            }
            return $true
        }
        $curl = {
            param($Executable, $Arguments)
            $script:curlCalls++
            if ($script:stateIndex -lt 6) { throw "not listening yet" }
            return 0
        }

        $result = Wait-ForLocalRest -DataPath $dataPath -TimeoutSeconds 3 `
            -CommandResolver { (Join-Path $TestDrive "curl.exe") } `
            -ReadinessReader $readConfig -CurlInvoker $curl

        $result.Port | Should Be 27124
        $script:curlCalls | Should BeGreaterThan 0
        $script:stateIndex | Should Be 6
    }

    It "fails closed at the Local REST readiness deadline without secrets" {
        Import-Module $restModule -Force
        $dataPath = Join-Path $TestDrive "timeout-data.json"
        Set-Content -LiteralPath $dataPath -Value '{"apiKey":"secret","port":27124,"crypto":{"cert":"private-looking"}}' -Encoding UTF8
        try {
            Wait-ForLocalRest -DataPath $dataPath -TimeoutSeconds 1 `
                -CommandResolver { throw "curl.exe missing secret=secret" } `
                -ReadinessReader { $true } -CurlInvoker { param($Executable, $Arguments) throw "connection refused" }
            throw "expected timeout"
        } catch {
            $_.Exception.Message | Should Match '^local_rest_not_ready:'
            $_.Exception.Message | Should Not Match 'secret|private-looking|curl.exe missing'
            $_.Exception.Message | Should Match 'Keep Obsidian open, verify the Local REST plugin is enabled, and rerun doctor'
        }
    }

    It "rejects invalid ports and missing certificates before curl" {
        Import-Module $restModule -Force
        foreach ($payload in @(
            '{"port":0,"crypto":{"cert":"cert"}}',
            '{"port":65536,"crypto":{"cert":"cert"}}',
            '{"port":27124}',
            '{"port":27124,"crypto":{"cert":""}}'
        )) {
            $dataPath = Join-Path $TestDrive ("invalid-" + [guid]::NewGuid().ToString("N") + ".json")
            Set-Content -LiteralPath $dataPath -Value $payload -Encoding UTF8
            { Wait-ForLocalRest -DataPath $dataPath -TimeoutSeconds 1 `
                -CommandResolver { Join-Path $TestDrive "curl.exe" } `
                -ReadinessReader { $true } -CurlInvoker { throw "must not run" } } | Should Throw "local_rest_not_ready"
        }
    }

    It "agrees with production on the terminal health status vocabulary" {
        # The harness stubs the network boundary, so without this the suite could assert a status
        # string that production is incapable of returning.
        if (-not (Test-Path $restModule)) { throw "LocalRest module is missing" }
        $source = Get-Content -Raw -LiteralPath $restModule -Encoding UTF8
        $source | Should Match ('Status = "' + $expectedHealthyStatus + '"')
    }

    It "runs doctor through the real runtime and publication modules, not stubs" {
        # Closes the seam the stub harness leaves open: real Get-RuntimeConfig path re-validation
        # and real Test-PublicationLibrary must both work through doctor.ps1.
        foreach ($module in @($environmentModule, $publicationModule)) {
            if (-not (Test-Path $module)) { throw "module is missing: $module" }
        }
        Import-Module $environmentModule -Force
        Import-Module $publicationModule -Force

        $vaultPath = Join-Path $TestDrive "real-doctor-vault"
        New-Item -ItemType Directory -Path (Join-Path $vaultPath ".obsidian\plugins\obsidian-local-rest-api") -Force | Out-Null
        $runtimeRoot = Join-Path $TestDrive "real-doctor-runtime"
        New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
        $runtimePath = Join-Path $runtimeRoot "runtime.json"

        # Legacy shape: no publicationRoot key. This is the shape on the maintainer's own machine.
        [ordered]@{
            schemaVersion = 1
            vaultPath = [IO.Path]::GetFullPath($vaultPath)
            restDataPath = Join-Path ([IO.Path]::GetFullPath($vaultPath)) ".obsidian\plugins\obsidian-local-rest-api\data.json"
        } | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding UTF8

        $config = Get-RuntimeConfig -RuntimeConfigPath $runtimePath
        $config.VaultPath | Should Be ([IO.Path]::GetFullPath($vaultPath))
        # The legacy shape must be READ without throwing. PublicationRoot is intentionally left
        # unset here and resolved by the caller, so assert the read succeeded rather than
        # inventing a value the function does not promise.
        $config.RestDataPath | Should Be (Join-Path ([IO.Path]::GetFullPath($vaultPath)) ".obsidian\plugins\obsidian-local-rest-api\data.json")
        $config.PSObject.Properties["PublicationRoot"] | Should Not BeNullOrEmpty
        # And a resolvable publication root is still obtainable for the legacy shape.
        [string]::IsNullOrWhiteSpace([string](Resolve-PublicationRoot)) | Should Be $false
    }

    It "initializes the selected publication library and reports its root after installation" {
        $harness = New-TestBootstrapHarness -HarnessRoot (Join-Path $TestDrive "install-harness")
        $vaultPath = Join-Path $TestDrive "install-vault"
        $runtimeRoot = Join-Path $TestDrive "install-runtime"
        $publicationRoot = Join-Path $TestDrive "install-publication"

        $result = & $harness.InstallScript -VaultPath $vaultPath -RuntimeRoot $runtimeRoot -PublicationRoot $publicationRoot -EnableCommunityPlugin

        $result.PublicationRoot | Should Be ([IO.Path]::GetFullPath($publicationRoot))
        Test-Path -LiteralPath (Join-Path $publicationRoot "initialized.marker") -PathType Leaf | Should Be $true
        (Get-Content -Raw -LiteralPath (Join-Path $publicationRoot "initialized.marker")) | Should Be ([IO.Path]::GetFullPath($vaultPath))
        (Get-Content -Raw -LiteralPath (Join-Path $runtimeRoot "runtime.json")) | Should Not Match 'apiKey|token|secret|bearer'
    }

    It "reports publication-library and shortcut health independently in doctor output" {
        $harness = New-TestBootstrapHarness -HarnessRoot (Join-Path $TestDrive "doctor-harness")
        $vaultPath = Join-Path $TestDrive "doctor-vault"
        $publicationRoot = Join-Path $TestDrive "doctor-publication"
        $runtimePath = Join-Path $TestDrive "doctor-runtime.json"
        New-Item -ItemType Directory -Path $vaultPath, $publicationRoot -Force | Out-Null
        [ordered]@{
            schemaVersion = 2
            vaultPath = [IO.Path]::GetFullPath($vaultPath)
            restDataPath = Join-Path ([IO.Path]::GetFullPath($vaultPath)) ".obsidian\plugins\obsidian-local-rest-api\data.json"
            publicationRoot = [IO.Path]::GetFullPath($publicationRoot)
            pythonExecutable = "C:\Python312\python.exe"
            venvRoot = "C:\managed\venv"
            venvPythonExecutable = "C:\managed\venv\Scripts\python.exe"
            requirementsHash = ("a" * 64)
        } | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding UTF8

        $result = & $harness.DoctorScript -RuntimeConfigPath $runtimePath -TimeoutSeconds 1

        $result.Status | Should Be $expectedHealthyStatus
        $result.PublicationRoot | Should Be ([IO.Path]::GetFullPath($publicationRoot))
        $result.PublicationLibraryStatus | Should Be "ready"
        $result.VaultShortcutStatus | Should Be "ready"
        Test-Path -LiteralPath (Join-Path $publicationRoot "doctor-checked.marker") -PathType Leaf | Should Be $true
    }

    It "checks but never rebuilds the publication library when Local REST is unavailable" {
        $harness = New-TestBootstrapHarness -HarnessRoot (Join-Path $TestDrive "doctor-rest-failure") -RestUnavailable
        $vaultPath = Join-Path $TestDrive "failure-vault"
        $publicationRoot = Join-Path $TestDrive "failure-publication"
        $runtimePath = Join-Path $TestDrive "failure-runtime.json"
        New-Item -ItemType Directory -Path $vaultPath, $publicationRoot -Force | Out-Null
        $sentinelPath = Join-Path $publicationRoot "user-content.txt"
        Set-Content -LiteralPath $sentinelPath -Value "preserve me" -Encoding UTF8 -NoNewline
        [ordered]@{
            schemaVersion = 2
            vaultPath = [IO.Path]::GetFullPath($vaultPath)
            restDataPath = Join-Path ([IO.Path]::GetFullPath($vaultPath)) ".obsidian\plugins\obsidian-local-rest-api\data.json"
            publicationRoot = [IO.Path]::GetFullPath($publicationRoot)
            pythonExecutable = "C:\Python312\python.exe"
            venvRoot = "C:\managed\venv"
            venvPythonExecutable = "C:\managed\venv\Scripts\python.exe"
            requirementsHash = ("a" * 64)
        } | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding UTF8

        { & $harness.DoctorScript -RuntimeConfigPath $runtimePath -TimeoutSeconds 1 } | Should Throw

        Test-Path -LiteralPath (Join-Path $publicationRoot "doctor-checked.marker") -PathType Leaf | Should Be $true
        Get-Content -Raw -LiteralPath $sentinelPath | Should Be "preserve me"
        Test-Path -LiteralPath (Join-Path $publicationRoot "initialized.marker") | Should Be $false
    }
}

Describe "Desktop publication library safety contract" {
    It "rejects equality and nesting for every install-root pair" {
        Import-Module $environmentModule -Force
        $root = Join-Path $TestDrive "install-root-overlap"
        $other = Join-Path $TestDrive "install-root-other"
        New-Item -ItemType Directory -Path $root, $other -Force | Out-Null

        foreach ($case in @(
            @{ Name = "Vault equals Runtime"; Vault = $root; Runtime = $root; Publication = $other },
            @{ Name = "Vault contains Runtime"; Vault = $root; Runtime = (Join-Path $root "runtime"); Publication = $other },
            @{ Name = "Runtime contains Vault"; Vault = (Join-Path $root "vault"); Runtime = $root; Publication = $other },
            @{ Name = "Vault equals Publication"; Vault = $root; Runtime = $other; Publication = $root },
            @{ Name = "Vault contains Publication"; Vault = $root; Runtime = $other; Publication = (Join-Path $root "publication") },
            @{ Name = "Publication contains Vault"; Vault = (Join-Path $root "vault"); Runtime = $other; Publication = $root },
            @{ Name = "Runtime equals Publication"; Vault = $other; Runtime = $root; Publication = $root },
            @{ Name = "Runtime contains Publication"; Vault = $other; Runtime = $root; Publication = (Join-Path $root "publication") },
            @{ Name = "Publication contains Runtime"; Vault = $other; Runtime = (Join-Path $root "runtime"); Publication = $root }
        )) {
            $threw = $false
            try {
                Assert-InstallPathSetIsSafe -VaultPath $case.Vault -RuntimeRoot $case.Runtime -PublicationRoot $case.Publication
            } catch {
                $threw = $true
            }
            $threw | Should Be $true
        }
    }

    It "rejects symbolic-link and junction aliases before accepting the install-root set" {
        Import-Module $environmentModule -Force
        $root = Join-Path $TestDrive "install-reparse"
        $vault = Join-Path $root "vault"
        $runtime = Join-Path $root "runtime"
        $publication = Join-Path $root "publication"
        New-Item -ItemType Directory -Path $vault, $runtime, $publication -Force | Out-Null

        foreach ($kind in @("SymbolicLink", "Junction")) {
            $alias = Join-Path $root ("vault-" + $kind.ToLowerInvariant())
            try {
                New-Item -ItemType $kind -Path $alias -Target $vault -ErrorAction Stop | Out-Null
            } catch {
                Write-Warning "SKIPPED: Windows does not permit $kind creation in this test environment."
                continue
            }

            $threw = $false
            try {
                Assert-InstallPathSetIsSafe -VaultPath $alias -RuntimeRoot $runtime -PublicationRoot $publication
            } catch {
                $threw = $true
            }
            $threw | Should Be $true
        }
    }

    It "resolves the default publication root below the Windows Desktop known folder" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $desktop = Join-Path $TestDrive "Redirected Desktop"

        Resolve-PublicationRoot -DesktopPath $desktop | Should Be (Join-Path ([IO.Path]::GetFullPath($desktop)) "옵시디언 원고")
    }

    It "rejects filesystem and user-profile roots" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force

        { Resolve-PublicationRoot -PublicationRoot ([IO.Path]::GetPathRoot($TestDrive)) } | Should Throw
        { Resolve-PublicationRoot -PublicationRoot ([Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)) } | Should Throw
    }

    It "rejects a publication root that overlaps the configured Vault" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $vaultPath = Join-Path $TestDrive "vault"

        { Initialize-PublicationLibrary -PublicationRoot $vaultPath -VaultPath $vaultPath } | Should Throw
        { Initialize-PublicationLibrary -PublicationRoot (Join-Path $vaultPath "publication") -VaultPath $vaultPath } | Should Throw
        { Initialize-PublicationLibrary -PublicationRoot $TestDrive -VaultPath (Join-Path $TestDrive "nested-vault") } | Should Throw
    }

    It "creates only the publication root files and an exact Explorer shortcut" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $publicationRoot = Join-Path $TestDrive "옵시디언 원고"
        $vaultPath = Join-Path $TestDrive "Vault With Spaces"
        New-Item -ItemType Directory -Path $vaultPath -Force | Out-Null
        $shortcutState = @{}
        $shellFactory = New-TestShortcutShellFactory -State $shortcutState

        $initialized = Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory $shellFactory

        $initialized.Root | Should Be ([IO.Path]::GetFullPath($publicationRoot))
        Test-Path -LiteralPath (Join-Path $publicationRoot "00 원고 목록.html") -PathType Leaf | Should Be $true
        Test-Path -LiteralPath (Join-Path $publicationRoot "00 사용 방법.txt") -PathType Leaf | Should Be $true
        (Get-Content -Raw -LiteralPath (Join-Path $publicationRoot "00 사용 방법.txt")).StartsWith(
            "[Codex Obsidian Manuscript - managed publication guide]"
        ) | Should Be $true
        (Get-Content -Raw -LiteralPath (Join-Path $publicationRoot "00 원고 목록.html")).StartsWith(
            "<!-- Codex Obsidian Manuscript - managed publication index -->"
        ) | Should Be $true
        $shortcutPath = Join-Path $publicationRoot "00 Obsidian 보관함 폴더.lnk"
        Test-Path -LiteralPath $shortcutPath -PathType Leaf | Should Be $true
        @((Get-ChildItem -LiteralPath $publicationRoot -Force)).Count | Should Be 3
        $shortcutState[$shortcutPath].TargetPath | Should Be ([IO.Path]::GetFullPath((Join-Path $env:WINDIR "explorer.exe")))
        $shortcutState[$shortcutPath].Arguments | Should Be ('"' + [IO.Path]::GetFullPath($vaultPath) + '"')
        $shortcutState[$shortcutPath].WorkingDirectory | Should Be ([IO.Path]::GetFullPath((Split-Path -Parent $vaultPath)))

        $health = Test-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory $shellFactory
        $health.Status | Should Be "ready"
        $health.UsageStatus | Should Be "ready"
        $health.IndexStatus | Should Be "ready"
        $health.ShortcutStatus | Should Be "ready"
    }

    It "preserves and reports an existing unmanaged usage file" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $publicationRoot = Join-Path $TestDrive "existing-usage"
        $vaultPath = Join-Path $TestDrive "usage-vault"
        New-Item -ItemType Directory -Path $publicationRoot, $vaultPath -Force | Out-Null
        $usagePath = Join-Path $publicationRoot "00 사용 방법.txt"
        Set-Content -LiteralPath $usagePath -Value "사용자가 작성한 파일" -Encoding UTF8 -NoNewline
        $shortcutState = @{}

        $initialized = Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory (New-TestShortcutShellFactory -State $shortcutState)
        $health = Test-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory (New-TestShortcutShellFactory -State $shortcutState)

        Get-Content -Raw -LiteralPath $usagePath | Should Be "사용자가 작성한 파일"
        $initialized.Status | Should Be "incomplete"
        $initialized.UsageStatus | Should Be "unmanaged"
        $initialized.IndexStatus | Should Be "ready"
        $health.Status | Should Be "incomplete"
        $health.UsageStatus | Should Be "unmanaged"
        $health.IndexStatus | Should Be "ready"
    }

    It "preserves and reports an existing unmanaged index file" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $publicationRoot = Join-Path $TestDrive "existing-index"
        $vaultPath = Join-Path $TestDrive "index-vault"
        New-Item -ItemType Directory -Path $publicationRoot, $vaultPath -Force | Out-Null
        $indexPath = Join-Path $publicationRoot "00 원고 목록.html"
        $userIndex = '<!doctype html><html><body>사용자가 작성한 색인</body></html>'
        Set-Content -LiteralPath $indexPath -Value $userIndex -Encoding UTF8 -NoNewline
        $shortcutState = @{}

        $initialized = Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory (New-TestShortcutShellFactory -State $shortcutState)
        $health = Test-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory (New-TestShortcutShellFactory -State $shortcutState)

        Get-Content -Raw -LiteralPath $indexPath | Should Be $userIndex
        $initialized.Status | Should Be "incomplete"
        $initialized.UsageStatus | Should Be "ready"
        $initialized.IndexStatus | Should Be "unmanaged"
        $health.Status | Should Be "incomplete"
        $health.UsageStatus | Should Be "ready"
        $health.IndexStatus | Should Be "unmanaged"
    }

    It "refuses to replace an existing unmanaged shortcut" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $publicationRoot = Join-Path $TestDrive "existing-shortcut"
        $vaultPath = Join-Path $TestDrive "shortcut-vault"
        New-Item -ItemType Directory -Path $publicationRoot, $vaultPath -Force | Out-Null
        $shortcutPath = Join-Path $publicationRoot "00 Obsidian 보관함 폴더.lnk"
        Set-Content -LiteralPath $shortcutPath -Value "user shortcut" -Encoding UTF8 -NoNewline
        $shortcutState = @{
            $shortcutPath = [pscustomobject]@{
                TargetPath = "C:\Other\program.exe"
                Arguments = ""
                WorkingDirectory = "C:\Other"
            }
        }

        { Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory (New-TestShortcutShellFactory -State $shortcutState) } | Should Throw

        Get-Content -Raw -LiteralPath $shortcutPath | Should Be "user shortcut"
        Test-Path -LiteralPath (Join-Path $publicationRoot "00 사용 방법.txt") | Should Be $false
        Test-Path -LiteralPath (Join-Path $publicationRoot "00 원고 목록.html") | Should Be $false
    }

    It "is idempotent when its shortcut already targets the exact Vault" {
        if (-not (Test-Path $publicationModule)) { throw "PublicationLibrary module is missing" }
        Import-Module $publicationModule -Force
        $publicationRoot = Join-Path $TestDrive "idempotent-publication"
        $vaultPath = Join-Path $TestDrive "idempotent-vault"
        New-Item -ItemType Directory -Path $vaultPath -Force | Out-Null
        $shortcutState = @{}
        $shellFactory = New-TestShortcutShellFactory -State $shortcutState

        Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory $shellFactory | Out-Null
        { Initialize-PublicationLibrary -PublicationRoot $publicationRoot -VaultPath $vaultPath -ShellFactory $shellFactory } | Should Not Throw

        @((Get-ChildItem -LiteralPath $publicationRoot -Force)).Count | Should Be 3
    }
}
