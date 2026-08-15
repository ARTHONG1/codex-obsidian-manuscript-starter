$repoRoot = Split-Path -Parent $PSScriptRoot
$runnerPath = Join-Path $repoRoot "ci\run-installer-scenario.ps1"

Describe "Installer scenario runner contract" {
    It "exists and accepts only the approved scenarios" {
        Test-Path -LiteralPath $runnerPath -PathType Leaf | Should Be $true
        $source = Get-Content -Raw -LiteralPath $runnerPath -Encoding UTF8
        $source | Should Match "ValidateSet"
        foreach ($scenario in @("python311_selected", "python313_selected", "python_absent", "python312_ready", "restart_resume", "venv_reuse")) {
            $source | Should Match ([regex]::Escape($scenario))
        }
    }

    It "invokes production installer without forwarding the unsupported Scenario parameter" {
        $source = Get-Content -Raw -LiteralPath $runnerPath -Encoding UTF8
        $source | Should Match "install-windows\.ps1"
        $source | Should Not Match "install-windows\.ps1[^\r\n]*-Scenario"
        $source | Should Match "-VaultPath"
        $source | Should Match "-RuntimeRoot"
        $source | Should Match "-PublicationRoot"
    }

    It "keeps scenario state and installer roots below one temporary root" {
        $source = Get-Content -Raw -LiteralPath $runnerPath -Encoding UTF8
        $source | Should Match "GetTempPath"
        $source | Should Match "Remove-Item.*Recurse.*Force"
        $source | Should Match "INSTALLER_SCENARIO"
    }
}
