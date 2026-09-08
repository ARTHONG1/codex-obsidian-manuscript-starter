$repoRoot = Split-Path -Parent $PSScriptRoot
$ownedProcessModule = Join-Path $repoRoot "ci\lib\OwnedProcess.psm1"

Describe "Owned process runner contract" {
    BeforeAll {
        $runRoot = Join-Path ([IO.Path]::GetTempPath()) ("owned-test-" + [guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
        $script:ownedModuleAvailable = Test-Path -LiteralPath $ownedProcessModule
        if ($script:ownedModuleAvailable) {
            Import-Module $ownedProcessModule -Force
        }
    }

    AfterAll {
        Start-Sleep -Milliseconds 300
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        if ($runRoot -and (Test-Path -LiteralPath $runRoot)) {
            for ($i = 0; $i -lt 5; $i++) {
                try { Remove-Item -LiteralPath $runRoot -Recurse -Force -ErrorAction Stop; break } catch { Start-Sleep -Milliseconds 200 }
            }
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
            "-NoProfile", "-Command", "Start-Sleep -Seconds 600"
        ) -PassThru -WindowStyle Hidden
        $run = New-OwnedProcessRun -RootPath $runRoot -Name "timeout"
        $descendantMarker = Join-Path $run.runRoot 'timeout-descendant.pid'
        $descendantCode = '$PID | Set-Content -LiteralPath ''' + $descendantMarker.Replace("'", "''") + '''; Start-Sleep -Seconds 600'
        $descendantEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($descendantCode))
        try {
            $result = Invoke-OwnedProcess -Run $run -Name "timeout-child" -FilePath "powershell.exe" `
                -ArgumentList @("-NoProfile", "-EncodedCommand", $descendantEncoded) `
                -WorkingDirectory $runRoot -TimeoutSeconds 5
            $result.timedOut | Should Be $true
            Test-Path -LiteralPath $descendantMarker | Should Be $true
            $descendantPid = [int](Get-Content -Raw -LiteralPath $descendantMarker)
            Start-Sleep -Milliseconds 200
            Get-Process -Id $sentinel.Id -ErrorAction SilentlyContinue | Should Not BeNullOrEmpty
            Test-RunOwnedPidAlive -LedgerPath $run.ledgerPath | Should Be $false
            [bool](Get-Process -Id $descendantPid -ErrorAction SilentlyContinue) | Should Be $false
        } finally {
            Close-OwnedProcessRun -Run $run
            # RED must not leave the deliberately leaked synthetic descendant alive.
            if (Test-Path -LiteralPath $descendantMarker) {
                $cleanupPid = [int](Get-Content -Raw -LiteralPath $descendantMarker)
                $cleanupProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$cleanupPid"
                if ($cleanupProcess -and $result -and $cleanupProcess.ParentProcessId -eq $result.rootPid -and $cleanupProcess.CommandLine.Contains($descendantEncoded)) {
                    Stop-Process -Id $cleanupPid -Force -ErrorAction SilentlyContinue
                }
            }
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


