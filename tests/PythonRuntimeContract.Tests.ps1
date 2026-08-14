$repoRoot = Split-Path -Parent $PSScriptRoot
$modulePath = Join-Path $repoRoot "bootstrap\lib\PythonRuntime.psm1"

Describe "Python 3.12 runtime contract" {
    BeforeEach {
        Remove-Module PythonRuntime -ErrorAction SilentlyContinue
        Import-Module $modulePath -Force
    }

    It "skips Python 3.11 on PATH and selects py -3.12" {
        $python312 = Join-Path $TestDrive "Python312\python.exe"
        $python311 = Join-Path $TestDrive "Python311\python.exe"
        New-Item -ItemType Directory -Path (Split-Path $python312) -Force | Out-Null
        New-Item -ItemType File -Path $python312 -Force | Out-Null
        New-Item -ItemType Directory -Path (Split-Path $python311) -Force | Out-Null
        New-Item -ItemType File -Path $python311 -Force | Out-Null
        $resolver = {
            param([string]$Command, [string[]]$Arguments)
            if ($Command -eq "py" -and $Arguments -contains "-3.12") {
                return $python312
            }
            if ($Command -eq "python") {
                return $python311
            }
            return $null
        }.GetNewClosure()
        $probe = {
            param([string]$Candidate)
            if ($Candidate -eq ([IO.Path]::GetFullPath($python312))) {
                return [pscustomobject]@{
                    ExitCode = 0
                    Major = 3
                    Minor = 12
                    Executable = $python312
                }
            }
            return [pscustomobject]@{
                ExitCode = 0
                Major = 3
                Minor = 11
                Executable = $python311
            }
        }.GetNewClosure()

        $result = Find-Python312 -CommandResolver $resolver -VersionProbe $probe

        $result.Ready | Should Be $true
        $result.Python | Should Be ([IO.Path]::GetFullPath($python312))
        $result.PythonVersion | Should Be "3.12"
        $result.Source | Should Be "py -3.12"
    }

    It "rejects a 3.13-only resolver" {
        $resolver = {
            param([string]$Command, [string[]]$Arguments)
            if ($Command -eq "py") { return "C:\Python313\python.exe" }
            return $null
        }
        $probe = {
            param([string]$Candidate)
            [pscustomobject]@{
                ExitCode = 0
                Major = 3
                Minor = 13
                Executable = $Candidate
            }
        }

        $result = Find-Python312 -CommandResolver $resolver -VersionProbe $probe

        $result.Ready | Should Be $false
        $result.Reason | Should Be "python_312_not_found"
    }

    It "accepts only a candidate whose self-reported executable resolves to itself" {
        $candidate = Join-Path $TestDrive "python.exe"
        New-Item -ItemType File -Path $candidate | Out-Null
        $resolver = {
            param([string]$Command, [string[]]$Arguments)
            return $candidate
        }.GetNewClosure()
        $probe = {
            param([string]$Candidate)
            [pscustomobject]@{
                ExitCode = 0
                Major = 3
                Minor = 12
                Executable = (Join-Path $TestDrive "other-python.exe")
            }
        }.GetNewClosure()

        $result = Find-Python312 -CommandResolver $resolver -VersionProbe $probe

        $result.Ready | Should Be $false
    }

    It "deduplicates canonical candidate paths case-insensitively" {
        $first = Join-Path $TestDrive "Python312\python.exe"
        New-Item -ItemType Directory -Path (Split-Path $first) -Force | Out-Null
        New-Item -ItemType File -Path $first -Force | Out-Null
        $calls = New-Object System.Collections.ArrayList
        $resolver = {
            param([string]$Command, [string[]]$Arguments)
            if ($Command -eq "py") { return $first.ToUpperInvariant() }
            if ($Command -eq "python") { return $first.ToLowerInvariant() }
            return $null
        }.GetNewClosure()
        $probe = {
            param([string]$Candidate)
            [void]$calls.Add($Candidate)
            [pscustomobject]@{
                ExitCode = 0
                Major = 3
                Minor = 12
                Executable = $Candidate
            }
        }.GetNewClosure()

        $result = Find-Python312 -CommandResolver $resolver -VersionProbe $probe

        $result.Ready | Should Be $true
        $calls.Count | Should Be 1
    }

    It "returns python_install_manual_required without invoking the process runner when WinGet is absent" {
        $called = $false
        $runner = {
            param([string]$Executable, [string[]]$Arguments)
            $script:called = $true
        }.GetNewClosure()

        $result = Install-Python312 -WingetPath $null -ProcessRunner $runner

        $result.Status | Should Be "python_install_manual_required"
        $result.Recovery | Should Match "WinGet"
        $called | Should Be $false
    }

    It "calls the exact Python 3.12 WinGet command and returns python_installed" {
        $winget = Join-Path $TestDrive "winget.exe"
        New-Item -ItemType File -Path $winget -Force | Out-Null
        $state = @{ Invocation = $null }
        $runner = {
            param([string]$Executable, [string[]]$Arguments)
            $state.Invocation = [pscustomobject]@{
                Executable = $Executable
                Arguments = $Arguments
                ExitCode = 0
            }
            return $state.Invocation
        }.GetNewClosure()

        $result = Install-Python312 -WingetPath $winget -ProcessRunner $runner

        $result.Status | Should Be "python_installed"
        $state.Invocation.Executable | Should Be ([IO.Path]::GetFullPath($winget))
        ($state.Invocation.Arguments -join " ") | Should Be "install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements"
    }

    It "returns python_install_failed when WinGet exits unsuccessfully" {
        $winget = Join-Path $TestDrive "winget.exe"
        New-Item -ItemType File -Path $winget -Force | Out-Null
        $runner = {
            param([string]$Executable, [string[]]$Arguments)
            return [pscustomobject]@{ ExitCode = 17 }
        }

        $result = Install-Python312 -WingetPath $winget -ProcessRunner $runner

        $result.Status | Should Be "python_install_failed"
        $result.Recovery | Should Match "17"
    }

    It "returns python_installed when installation succeeds so the caller can rediscover" {
        $winget = Join-Path $TestDrive "winget.exe"
        New-Item -ItemType File -Path $winget -Force | Out-Null
        $runner = {
            param([string]$Executable, [string[]]$Arguments)
            return [pscustomobject]@{ ExitCode = 0 }
        }

        $result = Install-Python312 -WingetPath $winget -ProcessRunner $runner

        $result.Status | Should Be "python_installed"
    }

    It "returns python_installed_restart_required when rediscovery remains empty" {
        $winget = Join-Path $TestDrive "winget.exe"
        New-Item -ItemType File -Path $winget -Force | Out-Null
        $resolver = {
            param([string]$Command, [string[]]$Arguments)
            return $null
        }
        $probe = {
            param([string]$Candidate)
            throw "probe should not run"
        }
        $install = Install-Python312 -WingetPath $winget -ProcessRunner {
            param([string]$Executable, [string[]]$Arguments)
            [pscustomobject]@{ ExitCode = 0 }
        }
        $rediscovered = Find-Python312 -CommandResolver $resolver -VersionProbe $probe

        $install.Status | Should Be "python_installed"
        $rediscovered.Ready | Should Be $false
        $rediscovered.Reason | Should Be "python_312_not_found"
        $status = [pscustomobject]@{
            Status = "python_installed_restart_required"
            Recovery = "Restart Codex and rerun the same installer command."
        }
        $status.Status | Should Be "python_installed_restart_required"
    }

    It "does not mutate PATH or the registry" {
        $winget = Join-Path $TestDrive "winget.exe"
        New-Item -ItemType File -Path $winget -Force | Out-Null
        $beforePath = $env:PATH
        $runner = {
            param([string]$Executable, [string[]]$Arguments)
            return [pscustomobject]@{ ExitCode = 0 }
        }

        [void](Install-Python312 -WingetPath $winget -ProcessRunner $runner)

        $env:PATH | Should Be $beforePath
        (Get-Command Set-ItemProperty -ErrorAction SilentlyContinue).Name | Should Be "Set-ItemProperty"
    }
}
