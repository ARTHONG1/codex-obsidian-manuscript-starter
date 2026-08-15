$repoRoot = Split-Path -Parent $PSScriptRoot
$ownedProcessModule = Join-Path $repoRoot "ci\lib\OwnedProcess.psm1"

Describe "Owned process runner contract" {
    BeforeAll {
        $runRoot = Join-Path $TestDrive "owned-run"
        New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
        $script:ownedModuleAvailable = Test-Path -LiteralPath $ownedProcessModule
        if ($script:ownedModuleAvailable) {
            Import-Module $ownedProcessModule -Force
        }
    }

    It "requires a run-scoped Job Object and ledger" {
        $script:ownedModuleAvailable | Should Be $true
        $run = New-OwnedProcessRun -RootPath $runRoot -Name "contract"
        try {
            $run.runId | Should Not BeNullOrEmpty
            Test-Path -LiteralPath $run.ledgerPath | Should Be $true
            $run.jobHandle | Should Not BeNullOrEmpty
        } finally {
            Close-OwnedProcessRun -Run $run
        }
    }

    It "captures a successful child without leaking its output outside the run root" {
        $script:ownedModuleAvailable | Should Be $true
        $run = New-OwnedProcessRun -RootPath $runRoot -Name "success"
        try {
            $result = Invoke-OwnedProcess -Run $run -Name "success-child" -FilePath "powershell.exe" `
                -ArgumentList @("-NoProfile", "-Command", "Write-Output success") `
                -WorkingDirectory $runRoot -TimeoutSeconds 10
            $result.exitCode | Should Be 0
            $result.timedOut | Should Be $false
            Test-Path -LiteralPath $result.stdoutPath | Should Be $true
            (Get-Content -Raw -LiteralPath $result.stdoutPath) | Should Match "success"
            $ledger = Get-Content -Raw -LiteralPath $run.ledgerPath | ConvertFrom-Json
            @($ledger.entries | Where-Object { $_.name -eq "success-child" -and $_.pid }) | Should Not BeNullOrEmpty
        } finally {
            Close-OwnedProcessRun -Run $run
        }
    }

    It "terminates a timed-out child tree while preserving an unrelated process" {
        $script:ownedModuleAvailable | Should Be $true
        $sentinel = Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-NoProfile", "-Command", "Start-Sleep -Seconds 120"
        ) -PassThru -WindowStyle Hidden
        $run = New-OwnedProcessRun -RootPath $runRoot -Name "timeout"
        try {
            $result = Invoke-OwnedProcess -Run $run -Name "timeout-child" -FilePath "powershell.exe" `
                -ArgumentList @("-NoProfile", "-Command", "Start-Sleep -Seconds 120") `
                -WorkingDirectory $runRoot -TimeoutSeconds 1
            $result.timedOut | Should Be $true
            Start-Sleep -Milliseconds 200
            Get-Process -Id $sentinel.Id -ErrorAction SilentlyContinue | Should Not BeNullOrEmpty
            Test-RunOwnedPidAlive -LedgerPath $run.ledgerPath | Should Be $false
        } finally {
            Close-OwnedProcessRun -Run $run
            Stop-Process -Id $sentinel.Id -Force -ErrorAction SilentlyContinue
        }
    }

    It "returns an operational failure and still closes the owned run" {
        $script:ownedModuleAvailable | Should Be $true
        $run = New-OwnedProcessRun -RootPath $runRoot -Name "failure"
        try {
            $result = Invoke-OwnedProcess -Run $run -Name "missing-child" -FilePath "powershell.exe" `
                -ArgumentList ([string[]]@()) -WorkingDirectory (Join-Path $runRoot "missing-working-directory") -TimeoutSeconds 2
            $result.operationalFailure | Should Be $true
            Test-RunOwnedPidAlive -LedgerPath $run.ledgerPath | Should Be $false
        } finally {
            Close-OwnedProcessRun -Run $run
        }
    }
}
