$repoRoot = Split-Path -Parent $PSScriptRoot
$modulePath = Join-Path $repoRoot "bootstrap\lib\BootstrapState.psm1"

Describe "Bootstrap state v3 contract" {
    BeforeAll {
        $script:moduleAvailable = Test-Path -LiteralPath $modulePath
        if ($script:moduleAvailable) { Import-Module $modulePath -Force }
    }

    It "writes and reads only an approved schema-v3 state" {
        $script:moduleAvailable | Should Be $true
        $path = Join-Path $TestDrive "bootstrap-state.json"
        $state = [ordered]@{
            schemaVersion = 3
            stage = "skills_ready"
            releaseId = "v0.6.0"
            skillsSha256 = "a" * 64
            restartRequired = $false
        }
        Write-BootstrapStateAtomic -Path $path -State $state
        $loaded = Read-BootstrapState -Path $path
        $loaded.schemaVersion | Should Be 3
        $loaded.stage | Should Be "skills_ready"
        @($loaded.PSObject.Properties | Where-Object { $_.Name -eq "apiKey" }) | Should BeNullOrEmpty
    }

    It "rejects truncated or secret-bearing state" {
        $script:moduleAvailable | Should Be $true
        $path = Join-Path $TestDrive "unsafe-state.json"
        Set-Content -LiteralPath $path -Value '{"schemaVersion":3,"stage":"skills_ready"' -Encoding UTF8
        { Read-BootstrapState -Path $path } | Should Throw
        $secretState = @{ schemaVersion = 3; stage = "ready"; apiKey = "synthetic-secret" }
        { Write-BootstrapStateAtomic -Path $path -State $secretState } | Should Throw
    }

    It "moves backward when a real probe disproves a recorded stage" {
        $script:moduleAvailable | Should Be $true
        $state = [pscustomobject]@{ schemaVersion = 3; stage = "ready"; skillsReady = $true; pythonReady = $true; obsidianReady = $true; doctorReady = $true }
        $probe = [pscustomobject]@{ skillsReady = $true; pythonReady = $true; obsidianReady = $false; doctorReady = $false }
        $action = Resolve-NextBootstrapAction -State $state -Probe $probe
        $action.Name | Should Be "start_obsidian"
    }

    It "returns doctor as the only path to ready" {
        $script:moduleAvailable | Should Be $true
        $state = [pscustomobject]@{ schemaVersion = 3; stage = "runtime_ready" }
        $probe = [pscustomobject]@{ skillsReady = $true; pythonReady = $true; obsidianReady = $true; doctorReady = $false }
        (Resolve-NextBootstrapAction -State $state -Probe $probe).Name | Should Be "run_doctor"
    }
}
