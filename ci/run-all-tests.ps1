[CmdletBinding()]
param(
    [string]$PythonPath = (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    [string]$EvidencePath = "",
    [int]$ExpectedPesterSkipCount = 0,
    [int]$ExpectedPythonSkipCount = 4
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path $PSScriptRoot\..).Path
$EvidencePath = if ($EvidencePath) { [IO.Path]::GetFullPath($EvidencePath) } else { Join-Path $repoRoot "artifacts\test-evidence.json" }
$evidenceRoot = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$ownedModule = Join-Path $PSScriptRoot "lib\OwnedProcess.psm1"
Import-Module $ownedModule -Force
$records = @()
$overallExit = 0
$ownedRun = New-OwnedProcessRun -RootPath (Join-Path $evidenceRoot "owned-runs") -Name "aggregate-tests"

function ConvertTo-ChildArgumentList {
    param([hashtable]$Arguments)
    $result = @()
    foreach ($key in $Arguments.Keys) {
        $value = $Arguments[$key]
        $result += "-$key"
        if ($value -is [array]) { $result += (($value -join ",")) }
        elseif ($null -ne $value) { $result += ([string]$value) }
    }
    return $result
}

function Invoke-ChildRunner {
    param([string]$ScriptPath, [hashtable]$Arguments, [string]$Name)
    $child = Invoke-OwnedProcess -Run $ownedRun -Name $Name -FilePath (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") `
        -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + (ConvertTo-ChildArgumentList -Arguments $Arguments)) `
        -WorkingDirectory $repoRoot -TimeoutSeconds 900
    $jsonLine = if (Test-Path -LiteralPath $child.stdoutPath) {
        @(Get-Content -LiteralPath $child.stdoutPath -Encoding UTF8 | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1)
    } else { @() }
    $summary = if ($jsonLine) { try { $jsonLine | ConvertFrom-Json } catch { $null } } else { $null }
    if (-not $summary) {
        $stderr = if (Test-Path -LiteralPath $child.stderrPath) { (Get-Content -Raw -LiteralPath $child.stderrPath -Encoding UTF8).Trim() } else { "" }
        $summary = [ordered]@{ runner = $Name; operationalFailure = $true; timedOut = [bool]$child.timedOut; message = if ($child.operationalFailure) { $child.message } elseif ($stderr) { $stderr } else { "runner did not emit a JSON summary" } }
    }
    [pscustomobject]@{ runner = $Name; exitCode = [int]$child.exitCode; timedOut = [bool]$child.timedOut; counts = $summary }
}

try {
    $pythonResult = Invoke-ChildRunner -Name "python" -ScriptPath (Join-Path $PSScriptRoot "run-python-tests.ps1") -Arguments @{ PythonPath = $PythonPath; ExpectedSkipCount = $ExpectedPythonSkipCount }
    $records += $pythonResult
    $overallExit = [Math]::Max($overallExit, [int]$pythonResult.exitCode)

    $pesterResult = Invoke-ChildRunner -Name "pester" -ScriptPath (Join-Path $PSScriptRoot "run-pester-tests.ps1") -Arguments @{ Path = "tests"; ExpectedSkipCount = $ExpectedPesterSkipCount }
    if ([int]$pesterResult.exitCode -ne 0) {
        $firstPesterResult = $pesterResult
        $pesterResult = Invoke-ChildRunner -Name "pester-retry" -ScriptPath (Join-Path $PSScriptRoot "run-pester-tests.ps1") -Arguments @{ Path = "tests"; ExpectedSkipCount = $ExpectedPesterSkipCount }
        $pesterResult | Add-Member -NotePropertyName attempts -NotePropertyValue 2
        $pesterResult | Add-Member -NotePropertyName firstAttemptExitCode -NotePropertyValue ([int]$firstPesterResult.exitCode)
        $pesterResult | Add-Member -NotePropertyName firstAttemptCounts -NotePropertyValue $firstPesterResult.counts
    } else {
        $pesterResult | Add-Member -NotePropertyName attempts -NotePropertyValue 1
    }
    $records += $pesterResult
    $overallExit = [Math]::Max($overallExit, [int]$pesterResult.exitCode)
} catch {
    $overallExit = 1
    $records += [pscustomobject]@{ runner = "aggregate"; exitCode = 1; timedOut = $false; counts = [ordered]@{ operationalFailure = $true; message = $_.Exception.Message } }
} finally {
    $evidence = [ordered]@{ schemaVersion = 2; successful = ($overallExit -eq 0); runId = $ownedRun.runId; results = $records }
    try { $evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8 } catch { $overallExit = 1 }
    Close-OwnedProcessRun -Run $ownedRun
}
if ($overallExit -ne 0) { exit 1 }
exit 0

