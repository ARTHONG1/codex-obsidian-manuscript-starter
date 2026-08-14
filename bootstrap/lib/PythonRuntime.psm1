Set-StrictMode -Version 2.0

function ConvertTo-CanonicalPath {
    param([Parameter(Mandatory = $true)] [string]$Path)
    try { return [IO.Path]::GetFullPath($Path) } catch { return $null }
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
        $output = & $Command @Arguments 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return ([string]($output | Select-Object -First 1)).Trim()
        }
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
    & $Executable @Arguments
    return [pscustomobject]@{ ExitCode = $LASTEXITCODE }
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

Export-ModuleMember -Function Find-Python312, Install-Python312
