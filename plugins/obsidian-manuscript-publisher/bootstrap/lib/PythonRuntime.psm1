Set-StrictMode -Version 2.0

function ConvertTo-CanonicalPath {
    param([Parameter(Mandatory = $true)] [string]$Path)
    try { return [IO.Path]::GetFullPath($Path) } catch { return $null }
}

function Test-NoReparsePointInPath {
    param([Parameter(Mandatory = $true)] [string]$Path)
    try {
        $currentPath = ConvertTo-CanonicalPath $Path
        while (-not [string]::IsNullOrWhiteSpace($currentPath)) {
            $current = Get-Item -LiteralPath $currentPath -Force -ErrorAction Stop
            if (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                return $false
            }
            $parentPath = Split-Path -Parent $currentPath
            if ([string]::IsNullOrWhiteSpace($parentPath) -or
                [string]::Equals($parentPath, $currentPath, [StringComparison]::OrdinalIgnoreCase)) {
                break
            }
            $currentPath = $parentPath
        }
        return $true
    } catch {
        return $false
    }
}

function Test-CanonicalCandidate {
    param(
        [Parameter(Mandatory = $true)] [string]$Candidate,
        [Parameter(Mandatory = $true)] [scriptblock]$VersionProbe
    )

    $canonical = ConvertTo-CanonicalPath $Candidate
    if ([string]::IsNullOrWhiteSpace($canonical) -or
        -not [IO.Path]::IsPathRooted($canonical) -or
        -not (Test-Path -LiteralPath $canonical -PathType Leaf)) {
        return $null
    }
    try {
        if (-not (Test-NoReparsePointInPath $canonical)) {
            return $null
        }
    } catch {
        return $null
    }
    try {
        $probe = & $VersionProbe $canonical
        if ($null -eq $probe -or [int]$probe.ExitCode -ne 0 -or
            [int]$probe.Major -ne 3 -or [int]$probe.Minor -ne 12) {
            return $null
        }
        $reported = ConvertTo-CanonicalPath ([string]$probe.Executable)
        if ([string]::IsNullOrWhiteSpace($reported) -or
            -not [string]::Equals($canonical, $reported, [StringComparison]::OrdinalIgnoreCase)) {
            return $null
        }
        return [pscustomobject]@{
            Ready = $true
            Reason = "ready"
            Python = $canonical
            PythonVersion = "3.12"
            Source = $null
        }
    } catch {
        return $null
    }
}

function Invoke-DefaultCommandResolver {
    param([string]$Command, [string[]]$Arguments)
    try {
        $application = Get-Command ($Command + ".exe") -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if (-not $application) {
            return $null
        }
        if ($Command -eq "py") {
            $script = 'import sys; print(sys.executable)'
            $output = & $application.Source @Arguments "-c" $script 2>$null
            if ($LASTEXITCODE -eq 0 -and $output) {
                return ([string]($output | Select-Object -First 1)).Trim()
            }
        }
        return $application.Source
    } catch {}
    return $null
}

function Invoke-DefaultVersionProbe {
    param([string]$Candidate)
    $script = 'import json,sys; print(json.dumps({"major":sys.version_info[0],"minor":sys.version_info[1],"executable":sys.executable}))'
    try {
        $output = & $Candidate -c $script 2>$null
        $exitCode = $LASTEXITCODE
        if (-not $output) {
            return [pscustomobject]@{ ExitCode = $exitCode; Major = -1; Minor = -1; Executable = "" }
        }
        $json = ([string]($output | Select-Object -Last 1)) | ConvertFrom-Json
        return [pscustomobject]@{
            ExitCode = $exitCode
            Major = [int]$json.major
            Minor = [int]$json.minor
            Executable = [string]$json.executable
        }
    } catch {
        return [pscustomobject]@{ ExitCode = 1; Major = -1; Minor = -1; Executable = "" }
    }
}

function Find-Python312 {
    param(
        [string]$ExplicitPython,
        [scriptblock]$CommandResolver,
        [scriptblock]$VersionProbe,
        [string]$LocalAppDataRoot = $env:LOCALAPPDATA,
        [string]$ProgramFilesRoot = $env:ProgramFiles
    )

    if ($null -eq $CommandResolver) { $CommandResolver = ${function:Invoke-DefaultCommandResolver} }
    if ($null -eq $VersionProbe) { $VersionProbe = ${function:Invoke-DefaultVersionProbe} }

    $candidates = New-Object System.Collections.ArrayList
    $sources = New-Object System.Collections.ArrayList
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPython)) {
        [void]$candidates.Add($ExplicitPython)
        [void]$sources.Add("explicit")
    }
    $py = & $CommandResolver "py" @("-3.12")
    if ($py) { [void]$candidates.Add([string]$py); [void]$sources.Add("py -3.12") }
    $python = & $CommandResolver "python" @()
    if ($python) { [void]$candidates.Add([string]$python); [void]$sources.Add("python") }

    $known = @(
        @{ Root = $LocalAppDataRoot; Relative = "Programs\Python\Python312\python.exe"; Source = "known user path" },
        @{ Root = $LocalAppDataRoot; Relative = "Programs\Python\Python312-64\python.exe"; Source = "known user path" },
        @{ Root = $ProgramFilesRoot; Relative = "Python312\python.exe"; Source = "Program Files" },
        @{ Root = $ProgramFilesRoot; Relative = "Python312-64\python.exe"; Source = "Program Files" }
    )
    foreach ($entry in $known) {
        if (-not [string]::IsNullOrWhiteSpace($entry.Root)) {
            [void]$candidates.Add((Join-Path $entry.Root $entry.Relative))
            [void]$sources.Add($entry.Source)
        }
    }

    $seen = @{}
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        $canonical = ConvertTo-CanonicalPath ([string]$candidates[$i])
        if ([string]::IsNullOrWhiteSpace($canonical)) { continue }
        $key = $canonical.ToUpperInvariant()
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        $result = Test-CanonicalCandidate -Candidate $canonical -VersionProbe $VersionProbe
        if ($null -ne $result) {
            $result.Source = [string]$sources[$i]
            return $result
        }
    }

    return [pscustomobject]@{
        Ready = $false
        Reason = "python_312_not_found"
        Python = $null
        PythonVersion = $null
        Source = $null
    }
}

function Invoke-DefaultProcessRunner {
    param([string]$Executable, [string[]]$Arguments)
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $process.StartInfo.FileName = $Executable
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    $process.StartInfo.Arguments = (($Arguments | ForEach-Object {
        $value = [string]$_
        if ($value -match '[\s"]') { '"' + ($value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"' } else { $value }
    }) -join " ")
    if (-not $process.Start()) { throw "Process start failed." }
    $output = $process.StandardOutput.ReadToEnd()
    $errorOutput = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    return [pscustomobject]@{ Output = $output; Error = $errorOutput; ExitCode = $process.ExitCode }
}

function Get-ManagedVenvPaths {
    param([Parameter(Mandatory = $true)] [string]$RuntimeRoot)
    $root = ConvertTo-CanonicalPath $RuntimeRoot
    if ([string]::IsNullOrWhiteSpace($root) -or -not [IO.Path]::IsPathRooted($root) -or
        -not (Test-Path -LiteralPath $root -PathType Container) -or
        -not (Test-NoReparsePointInPath $root)) {
        throw "Runtime root is unsafe."
    }
    $active = ConvertTo-CanonicalPath (Join-Path $root "venv")
    $candidate = ConvertTo-CanonicalPath (Join-Path $root ("venv.candidate-" + [guid]::NewGuid().ToString("N")))
    foreach ($path in @($active, $candidate)) {
        if (-not $path.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -and
            -not [string]::Equals($path, $root, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Managed path escaped runtime root."
        }
        if ((Test-Path -LiteralPath $path) -and -not (Test-NoReparsePointInPath $path)) {
            throw "Managed path is a reparse point."
        }
    }
    return [pscustomobject]@{
        ActiveRoot = $active
        ActivePython = ConvertTo-CanonicalPath (Join-Path $active "Scripts\python.exe")
        CandidateRoot = $candidate
    }
}

function Get-RequirementsHash {
    param([Parameter(Mandatory = $true)] [string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Requirements lock not found." }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-ManagedPythonRuntime {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonPath,
        [Parameter(Mandatory = $true)] [string]$RequirementsHash,
        [Parameter(Mandatory = $true)] [string]$ProbePath,
        [scriptblock]$ProcessRunner
    )
    if ($RequirementsHash -notmatch '^[0-9a-f]{64}$') { throw "Invalid requirements hash." }
    if ($null -eq $ProcessRunner) { $ProcessRunner = ${function:Invoke-DefaultProcessRunner} }
    try {
        $result = & $ProcessRunner $PythonPath @($ProbePath, "--requirements-hash", $RequirementsHash)
        if ($null -eq $result -or [int]$result.ExitCode -ne 0) {
            throw "Probe exited unsuccessfully."
        }
        $json = [string]$result.Output
        $probe = $json | ConvertFrom-Json
        $probe | Add-Member -NotePropertyName RequirementsHash -NotePropertyValue ([string]$probe.requirements_hash) -Force
        return $probe
    } catch {
        return [pscustomobject]@{ Ready = $false; Reason = "probe_failed"; RequirementsHash = $null }
    }
}

function Remove-OwnedDirectory {
    param([string]$Root, [string]$Path)
    $canonicalRoot = ConvertTo-CanonicalPath $Root
    $canonicalPath = ConvertTo-CanonicalPath $Path
    if ([string]::IsNullOrWhiteSpace($canonicalRoot) -or [string]::IsNullOrWhiteSpace($canonicalPath) -or
        -not $canonicalPath.StartsWith($canonicalRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-NoReparsePointInPath $canonicalPath)) {
        throw "Managed cleanup path is unsafe."
    }
    if (Test-Path -LiteralPath $canonicalPath) {
        Remove-Item -LiteralPath $canonicalPath -Recurse -Force
    }
}

function New-VerifiedManagedVenv {
    param(
        [Parameter(Mandatory = $true)] [string]$BasePython,
        [Parameter(Mandatory = $true)] [string]$RuntimeRoot,
        [Parameter(Mandatory = $true)] [string]$RequirementsLockPath,
        [Parameter(Mandatory = $true)] [scriptblock]$ProcessRunner,
        [string]$ProbePath = (Join-Path (Split-Path $PSScriptRoot -Parent) "verify_python_runtime.py")
    )
    $paths = Get-ManagedVenvPaths -RuntimeRoot $RuntimeRoot
    $hash = Get-RequirementsHash -Path $RequirementsLockPath
    $active = $paths.ActiveRoot
    $activePython = $paths.ActivePython
    if (Test-Path -LiteralPath $activePython -PathType Leaf) {
        $existing = Test-ManagedPythonRuntime -PythonPath $activePython -RequirementsHash $hash -ProbePath $ProbePath -ProcessRunner $ProcessRunner
        if ($existing.Ready -and [string]$existing.RequirementsHash -eq $hash) {
            return [pscustomobject]@{ Ready = $true; BasePython = $BasePython; Python = $activePython; VenvRoot = $active; RequirementsHash = $hash; Reused = $true; Backup = $null }
        }
    }
    $candidate = $paths.CandidateRoot
    $candidatePython = ConvertTo-CanonicalPath (Join-Path $candidate "Scripts\python.exe")
    $backup = ConvertTo-CanonicalPath (Join-Path (Split-Path $active -Parent) ("venv.backup-" + [guid]::NewGuid().ToString("N")))
    if (-not (Test-NoReparsePointInPath (Split-Path -Parent $backup))) { throw "Backup parent is unsafe." }
    $wasPromoted = $false
    try {
        $r = & $ProcessRunner $BasePython @("-m", "venv", $candidate)
        if ($null -eq $r -or [int]$r.ExitCode -ne 0) { throw "venv creation failed." }
        $r = & $ProcessRunner $candidatePython @("-m", "pip", "install", "--disable-pip-version-check", "--require-hashes", "--only-binary=:all:", "-r", $RequirementsLockPath)
        if ($null -eq $r -or [int]$r.ExitCode -ne 0) { throw "dependency installation failed." }
        $candidateProbe = Test-ManagedPythonRuntime -PythonPath $candidatePython -RequirementsHash $hash -ProbePath $ProbePath -ProcessRunner $ProcessRunner
        if (-not $candidateProbe.Ready -or [string]$candidateProbe.RequirementsHash -ne $hash) { throw "candidate verification failed." }
        if (Test-Path -LiteralPath $active) {
            if (-not (Test-NoReparsePointInPath $active)) { throw "Active runtime is unsafe." }
            Move-Item -LiteralPath $active -Destination $backup
        }
        if (Test-Path -LiteralPath $candidate) {
            if (-not (Test-NoReparsePointInPath $candidate)) { throw "Candidate runtime is unsafe." }
        } elseif (-not (Test-NoReparsePointInPath (Split-Path -Parent $candidate))) {
            throw "Candidate parent is unsafe."
        }
        Move-Item -LiteralPath $candidate -Destination $active
        $wasPromoted = $true
        $promoted = Test-ManagedPythonRuntime -PythonPath $activePython -RequirementsHash $hash -ProbePath $ProbePath -ProcessRunner $ProcessRunner
        if (-not $promoted.Ready -or [string]$promoted.RequirementsHash -ne $hash) { throw "post-promotion verification failed." }
        if (Test-Path -LiteralPath $backup) { Remove-OwnedDirectory (Split-Path -Parent $active) $backup }
        $backup = $null
        return [pscustomobject]@{ Ready = $true; BasePython = $BasePython; Python = $activePython; VenvRoot = $active; RequirementsHash = $hash; Reused = $false; Backup = $backup }
    } catch {
        if ($wasPromoted -and (Test-Path -LiteralPath $active)) {
            Remove-OwnedDirectory (Split-Path -Parent $active) $active
        }
        if (Test-Path -LiteralPath $backup) {
            if (-not (Test-NoReparsePointInPath $backup)) { throw "Backup runtime is unsafe." }
            Move-Item -LiteralPath $backup -Destination $active
        }
        if (Test-Path -LiteralPath $candidate) { Remove-OwnedDirectory (Split-Path -Parent $active) $candidate }
        throw
    }
}

function Install-Python312 {
    param(
        [string]$WingetPath,
        [scriptblock]$ProcessRunner
    )

    if ([string]::IsNullOrWhiteSpace($WingetPath)) {
        return [pscustomobject]@{
            Status = "python_install_manual_required"
            Recovery = "Install WinGet, then rerun the installer."
        }
    }
    try {
        $winget = if ([IO.Path]::IsPathRooted($WingetPath)) {
            $WingetPath
        } else {
            $command = Get-Command $WingetPath -CommandType Application -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($command) { $command.Source } else { $null }
        }
        $canonical = ConvertTo-CanonicalPath $winget
        if ([string]::IsNullOrWhiteSpace($canonical) -or
            -not (Test-Path -LiteralPath $canonical -PathType Leaf) -or
            -not (Test-NoReparsePointInPath $canonical)) {
            return [pscustomobject]@{
                Status = "python_install_manual_required"
                Recovery = "Install WinGet, then rerun the installer."
            }
        }
        $WingetPath = $canonical
    } catch {
        return [pscustomobject]@{
            Status = "python_install_manual_required"
            Recovery = "Install WinGet, then rerun the installer."
        }
    }
    if ($null -eq $ProcessRunner) { $ProcessRunner = ${function:Invoke-DefaultProcessRunner} }

    $arguments = @("install", "--id", "Python.Python.3.12", "--exact", "--accept-source-agreements", "--accept-package-agreements")
    try {
        $result = & $ProcessRunner $WingetPath $arguments
        if ($null -ne $result -and [int]$result.ExitCode -eq 0) {
            return [pscustomobject]@{
                Status = "python_installed"
                Recovery = "Rediscover Python 3.12 before continuing."
            }
        }
        $exitCode = if ($null -eq $result) { "unknown" } else { [string]$result.ExitCode }
        return [pscustomobject]@{
            Status = "python_install_failed"
            Recovery = "WinGet exited with code $exitCode. Rerun the installer or install Python 3.12 manually."
        }
    } catch {
        return [pscustomobject]@{
            Status = "python_install_failed"
            Recovery = "WinGet failed: $($_.Exception.Message)"
        }
    }
}

function Get-PythonRuntimeDeferredStatus {
    param([Parameter(Mandatory = $true)] [string]$PythonPath)
    return [pscustomobject]@{
        Status = "python_runtime_install_deferred"
        Reason = "managed_venv_install_deferred"
        Python = $PythonPath
        Recovery = "Managed virtual-environment installation is deferred to Task 3/5. Rerun the installer after that task is available."
    }
}

Export-ModuleMember -Function Find-Python312, Install-Python312, Get-PythonRuntimeDeferredStatus, Get-ManagedVenvPaths, New-VerifiedManagedVenv, Test-ManagedPythonRuntime
