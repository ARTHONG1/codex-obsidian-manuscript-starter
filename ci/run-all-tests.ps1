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
    $stdout = if (Test-Path -LiteralPath $child.stdoutPath) { (Get-Content -Raw -LiteralPath $child.stdoutPath -Encoding UTF8).Trim() } else { "" }
    $stderr = if (Test-Path -LiteralPath $child.stderrPath) { (Get-Content -Raw -LiteralPath $child.stderrPath -Encoding UTF8).Trim() } else { "" }
    if (-not $summary) {
        $msg = if ($child.operationalFailure) { $child.message } elseif ($stderr) { $stderr } elseif ($stdout) { $stdout } else { "runner did not emit a JSON summary" }
        $summary = [ordered]@{ runner = $Name; operationalFailure = $true; timedOut = [bool]$child.timedOut; message = $msg }
    } elseif ([int]$child.exitCode -ne 0) {
        $failedLines = @($stdout -split "`r?`n" | Where-Object { $_ -match '^s*[-]' -or $_ -match 'Expected:' -or $_ -match 'at <ScriptBlock>' } | Select-Object -First 20)
        $summary | Add-Member -NotePropertyName failures -NotePropertyValue $failedLines -Force -ErrorAction SilentlyContinue
    }
    [pscustomobject]@{ runner = $Name; exitCode = [int]$child.exitCode; timedOut = [bool]$child.timedOut; counts = $summary }
}

try {
    $pythonResult = Invoke-ChildRunner -Name "python" -ScriptPath (Join-Path $PSScriptRoot "run-python-tests.ps1") -Arguments @{ PythonPath = $PythonPath; ExpectedSkipCount = $ExpectedPythonSkipCount }
    $records += $pythonResult
    $overallExit = [Math]::Max($overallExit, [int]$pythonResult.exitCode)

    $pesterPaths = @(
        "tests\InstallerContract.Tests.ps1",
        "tests\PythonRuntimeContract.Tests.ps1",
        "tests\SecretScan.Tests.ps1",
        "tests\BeginnerAcceptanceContract.Tests.ps1",
        "tests\OfficialInstallersContract.Tests.ps1",
        "tests\InstallerScenarioContract.Tests.ps1",
        "tests\ReleaseAcquisitionContract.Tests.ps1",
        "tests\BootstrapStateContract.Tests.ps1",
        "tests\CodexSkillBootstrap.Tests.ps1"
    ) | ForEach-Object { Join-Path $repoRoot $_ }

    foreach ($pPath in $pesterPaths) {
        $pName = "pester-" + (Split-Path -LeafBase $pPath)
        $pRes = Invoke-ChildRunner -Name $pName -ScriptPath (Join-Path $PSScriptRoot "run-pester-tests.ps1") -Arguments @{ Path = $pPath; ExpectedSkipCount = 0 }
        $records += $pRes
        if ($pRes.exitCode -ne 0) {
            $overallExit = [Math]::Max($overallExit, [int]$pRes.exitCode)
        }
    }
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

