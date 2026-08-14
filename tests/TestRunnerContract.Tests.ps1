$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonRunner = Join-Path $repoRoot "ci\run-python-tests.ps1"
$pesterRunner = Join-Path $repoRoot "ci\run-pester-tests.ps1"
$aggregateRunner = Join-Path $repoRoot "ci\run-all-tests.ps1"

function Invoke-ChildPowerShell {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FilePath @ArgumentList 2>&1
    [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output -join [Environment]::NewLine)
    }
}

function Resolve-Python312 {
    $candidates = @(
        (Get-Command python.exe -ErrorAction SilentlyContinue).Source,
        (Get-Command py.exe -ErrorAction SilentlyContinue).Source,
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if ((Split-Path -Leaf $candidate) -ieq "py.exe") {
            $resolved = & $candidate -3.12 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved) { return $resolved.Trim() }
        } elseif (Test-Path -LiteralPath $candidate) {
            $version = & $candidate -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $version.Trim() -eq "3.12") { return $candidate }
        }
    }

    throw "A Python 3.12 interpreter is required for runner contract tests."
}

Describe "Test runner contracts" {
    It "includes this contract in the aggregate Pester suite" {
        $aggregate = Get-Content -Raw -LiteralPath $aggregateRunner
        $aggregate | Should Match "tests\\TestRunnerContract\.Tests\.ps1"
    }

    It "reports a passing Python module as success with explicit counts" {
        $root = Join-Path $TestDrive "python-pass"
        New-Item -ItemType Directory -Path $root -Force | Out-Null
        @'
import unittest

class PassTests(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)
'@ | Set-Content -LiteralPath (Join-Path $root "test_pass.py") -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pythonRunner -ArgumentList @(
            "-PythonPath", (Resolve-Python312),
            "-TestName", "test_pass.PassTests.test_passes",
            "-TestRoot", $root
        )

        $result.ExitCode | Should Be 0
        $result.Output | Should Match '"testsRun"\s*:\s*1'
        $result.Output | Should Match '"failures"\s*:\s*0'
        $result.Output | Should Match '"successful"\s*:\s*true'
    }

    It "fails a Python module with a failed test" {
        $root = Join-Path $TestDrive "python-fail"
        New-Item -ItemType Directory -Path $root -Force | Out-Null
        @'
import unittest

class FailTests(unittest.TestCase):
    def test_fails(self):
        self.fail("expected failure")
'@ | Set-Content -LiteralPath (Join-Path $root "test_fail.py") -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pythonRunner -ArgumentList @(
            "-PythonPath", (Resolve-Python312),
            "-TestName", "test_fail.FailTests.test_fails",
            "-TestRoot", $root
        )

        $result.ExitCode | Should Be 1
        $result.Output | Should Match '"failures"\s*:\s*1'
        $result.Output | Should Match '"successful"\s*:\s*false'
    }

    It "fails a Python module with an unexpected skip" {
        $root = Join-Path $TestDrive "python-skip"
        New-Item -ItemType Directory -Path $root -Force | Out-Null
        @'
import unittest

class SkipTests(unittest.TestCase):
    @unittest.skip("unexpected")
    def test_skips(self):
        self.assertTrue(True)
'@ | Set-Content -LiteralPath (Join-Path $root "test_skip.py") -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pythonRunner -ArgumentList @(
            "-PythonPath", (Resolve-Python312),
            "-TestName", "test_skip.SkipTests.test_skips",
            "-TestRoot", $root
        )

        $result.ExitCode | Should Be 1
        $result.Output | Should Match '"skipped"\s*:\s*1'
        $result.Output | Should Match '"successful"\s*:\s*false'
    }

    It "passes a Pester file with no result failures" {
        $path = Join-Path $TestDrive "pester-pass.Tests.ps1"
        @'
Describe "synthetic pass" {
    It "passes" {
        $true | Should Be $true
    }
}
'@ | Set-Content -LiteralPath $path -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pesterRunner -ArgumentList @(
            "-Path", $path,
            "-ExpectedSkipCount", "0"
        )

        $result.ExitCode | Should Be 0
        $result.Output | Should Match '"FailedCount"\s*:\s*0'
    }

    It "fails a Pester file with an assertion failure" {
        $path = Join-Path $TestDrive "pester-fail.Tests.ps1"
        @'
Describe "synthetic failure" {
    It "fails" {
        $false | Should Be $true
    }
}
'@ | Set-Content -LiteralPath $path -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pesterRunner -ArgumentList @(
            "-Path", $path,
            "-ExpectedSkipCount", "0"
        )

        $result.ExitCode | Should Be 1
        $result.Output | Should Match '"FailedCount"\s*:\s*1'
    }

    It "fails a Pester file with an unexpected skip" {
        $path = Join-Path $TestDrive "pester-skip.Tests.ps1"
        @'
Describe "synthetic skip" {
    It "skips" -Skip {
        $true | Should Be $true
    }
}
'@ | Set-Content -LiteralPath $path -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pesterRunner -ArgumentList @(
            "-Path", $path,
            "-ExpectedSkipCount", "0"
        )

        $result.ExitCode | Should Be 1
        $result.Output | Should Match '"SkippedCount"\s*:\s*1'
    }

    It "uses Pester result counts when Invoke-Pester returns a successful host result object" {
        $path = Join-Path $TestDrive "pester-owned-result.Tests.ps1"
        @'
Describe "synthetic owned result" {
    It "fails while the host remains successful" {
        $false | Should Be $true
    }
}
'@ | Set-Content -LiteralPath $path -Encoding UTF8

        $result = Invoke-ChildPowerShell -FilePath $pesterRunner -ArgumentList @(
            "-Path", $path,
            "-ExpectedSkipCount", "0"
        )

        $result.ExitCode | Should Be 1
        $result.Output | Should Match '"FailedCount"\s*:\s*1'
    }
}
