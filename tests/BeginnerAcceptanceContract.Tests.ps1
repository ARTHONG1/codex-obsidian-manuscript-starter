$repoRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repoRoot "ci\run-beginner-install-acceptance.ps1"
$scenarioSet = Join-Path $repoRoot "acceptance\windows\scenarios.json"

Describe "Beginner Windows acceptance contract" {
    It "defines the eight required isolated scenarios" {
        Test-Path -LiteralPath $runner | Should Be $true
        $set = Get-Content -Raw -LiteralPath $scenarioSet -Encoding UTF8 | ConvertFrom-Json
        @($set.scenarios).Count | Should Be 8
        @($set.scenarios | Where-Object { $_.requires -eq "disposable_windows" }).Count | Should BeGreaterThan 0
    }

    It "always emits sanitized evidence in a caller-owned temporary root" {
        $root = Join-Path $TestDrive "acceptance-root"
        $evidence = Join-Path $TestDrive "evidence\result.json"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -ScenarioSet $scenarioSet -Root $root -EvidencePath $evidence
        $LASTEXITCODE | Should Be 0
        Test-Path -LiteralPath $evidence | Should Be $true
        $result = Get-Content -Raw -LiteralPath $evidence | ConvertFrom-Json
        $result.status | Should Be "contract_ready"
        @($result.PSObject.Properties.Name -contains "apiKey") | Should Be $false
        @($result.PSObject.Properties.Name -contains "certificate") | Should Be $false
    }
}
