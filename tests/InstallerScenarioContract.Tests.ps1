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

    It "configures distinct runtime conditions instead of only labeling scenarios" {
        $source = Get-Content -Raw -LiteralPath $runnerPath -Encoding UTF8
        foreach ($condition in @("python311_selected", "python313_selected", "python_absent", "python312_ready", "restart_resume", "venv_reuse")) {
            $source | Should Match ([regex]::Escape("$condition"))
        }
        $source | Should Match "PythonRuntime\.psm1"
        $source | Should Match "Set-Content.*PythonRuntime"
        $source | Should Match "restart_resume"
        $source | Should Match "venv_reuse"
    }

    It "does not remove a caller-supplied root" {
        $source = Get-Content -Raw -LiteralPath $runnerPath -Encoding UTF8
        $source | Should Match "rootWasSupplied"
        $source | Should Match ([regex]::Escape('if (-not $rootWasSupplied)'))
        $source | Should Match ([regex]::Escape('Remove-Item -LiteralPath $Root -Recurse -Force'))
        $source | Should Match "restart_resume"
    }

    It "preserves a pre-existing caller root at runtime" {
        $callerRoot = Join-Path $TestDrive "caller-root"
        New-Item -ItemType Directory -Path $callerRoot -Force | Out-Null
        $marker = Join-Path $callerRoot "caller-marker.txt"
        Set-Content -LiteralPath $marker -Value "keep" -Encoding UTF8
        & pwsh -NoProfile -File $runnerPath -Scenario python_absent -Root $callerRoot | Out-Null
        $LASTEXITCODE | Should Be 0
        Test-Path -LiteralPath $marker -PathType Leaf | Should Be $true
        (Get-Content -Raw -LiteralPath $marker).Trim() | Should Be "keep"
    }

    It "proves the supported and unsupported runtime scenarios have distinct outcomes" {
        $unsupported = & pwsh -NoProfile -File $runnerPath -Scenario python311_selected
        $ready = & pwsh -NoProfile -File $runnerPath -Scenario python312_ready
        $unsupportedJson = ($unsupported | Select-Object -Last 1 | ConvertFrom-Json)
        $readyJson = ($ready | Select-Object -Last 1 | ConvertFrom-Json)
        $unsupportedJson.Status | Should Be "python_version_unsupported"
        $readyJson.Status | Should Be "community_plugin_consent_required"
        $unsupportedJson.Status | Should Not Be $readyJson.Status
    }

    It "proves venv reuse starts from a pre-existing marker" {
        $result = & pwsh -NoProfile -File $runnerPath -Scenario venv_reuse
        $json = ($result | Select-Object -Last 1 | ConvertFrom-Json)
        $json.VenvReused | Should Be $true
    }
}
