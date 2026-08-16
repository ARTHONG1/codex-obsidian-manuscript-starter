Set-StrictMode -Version Latest

if (-not ('CodexOwnedProcess.Native' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace CodexOwnedProcess {
    public static class Native {
        private const int JobObjectExtendedLimitInformation = 9;
        private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000;
        private const uint JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x0800;
        private const uint JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x1000;

        [StructLayout(LayoutKind.Sequential)]
        private struct IO_COUNTERS {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
            public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
            public IO_COUNTERS IoInfo;
            public UIntPtr ProcessMemoryLimit;
            public UIntPtr PeakProcessMemoryUsed;
            public UIntPtr JobMemoryLimit;
            public UIntPtr PeakJobMemoryUsed;
        }

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(IntPtr hJob, int infoType, IntPtr info, uint infoLength);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool TerminateJobObject(IntPtr hJob, uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        public static IntPtr CreateKillOnCloseJob() {
            IntPtr job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateJobObject failed.");
            var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK;
            IntPtr buffer = Marshal.AllocHGlobal(Marshal.SizeOf(info));
            try {
                Marshal.StructureToPtr(info, buffer, false);
                if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation, buffer, (uint)Marshal.SizeOf(info))) {
                    throw new Win32Exception(Marshal.GetLastWin32Error(), "SetInformationJobObject failed.");
                }
                return job;
            } catch {
                CloseHandle(job);
                throw;
            } finally {
                Marshal.FreeHGlobal(buffer);
            }
        }

        public static void Assign(IntPtr job, Process process) {
            if (!AssignProcessToJobObject(job, process.Handle)) {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "AssignProcessToJobObject failed.");
            }
        }

        public static void Terminate(IntPtr job, uint exitCode) {
            if (job != IntPtr.Zero) { TerminateJobObject(job, exitCode); }
        }

        public static void Close(IntPtr job) {
            if (job != IntPtr.Zero) { CloseHandle(job); }
        }
    }
}
'@
}

function ConvertTo-WindowsArgument {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value)
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Write-OwnedLedger {
    param([Parameter(Mandatory = $true)]$Run)
    [ordered]@{ schemaVersion = 1; runId = $Run.runId; entries = @($Run.entries) } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Run.ledgerPath -Encoding UTF8
}

function New-OwnedProcessRun {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RootPath,
        [Parameter(Mandatory = $true)][string]$Name
    )
    New-Item -ItemType Directory -Path $RootPath -Force | Out-Null
    $runId = [guid]::NewGuid().ToString('N')
    $runRoot = Join-Path $RootPath ("owned-" + $runId)
    New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
    $run = [pscustomobject]@{
        runId = $runId
        name = $Name
        runRoot = $runRoot
        ledgerPath = Join-Path $runRoot 'process-ledger.json'
        jobHandle = [CodexOwnedProcess.Native]::CreateKillOnCloseJob()
        entries = @()
        closed = $false
    }
    Write-OwnedLedger -Run $run
    return $run
}

function Invoke-OwnedProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Run,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][ValidateRange(1, 86400)][int]$TimeoutSeconds
    )
    $safeName = ($Name -replace '[^A-Za-z0-9_.-]', '_')
    $stdoutPath = Join-Path $Run.runRoot ($safeName + '.stdout.txt')
    $stderrPath = Join-Path $Run.runRoot ($safeName + '.stderr.txt')
    $entry = [pscustomobject][ordered]@{ name = $Name; pid = $null; status = 'starting'; error = $null; stdoutPath = 'owned/' + (Split-Path -Leaf $stdoutPath); stderrPath = 'owned/' + (Split-Path -Leaf $stderrPath) }
    $Run.entries += $entry
    Write-OwnedLedger -Run $Run
    $started = [DateTime]::UtcNow
    $process = $null
    $gate = $null
    try {
        $gateName = "Local\CodexOwned-" + [guid]::NewGuid().ToString('N')
        $gate = New-Object System.Threading.EventWaitHandle($false, [Threading.EventResetMode]::ManualReset, $gateName)
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        $gateScript = '$event=[Threading.EventWaitHandle]::OpenExisting($env:CODEX_OWNED_GATE); try { $event.WaitOne() | Out-Null; $args=@($env:CODEX_OWNED_ARGS_JSON | ConvertFrom-Json); & $env:CODEX_OWNED_FILE @args; exit $LASTEXITCODE } finally { if ($event) { $event.Dispose() } }'
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($gateScript))
        $info.Arguments = "-NoProfile -NonInteractive -EncodedCommand $encoded"
        $info.WorkingDirectory = $WorkingDirectory
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.EnvironmentVariables['CODEX_OWNED_GATE'] = $gateName
        $info.EnvironmentVariables['CODEX_OWNED_FILE'] = $FilePath
        $info.EnvironmentVariables['CODEX_OWNED_ARGS_JSON'] = (@($ArgumentList) | ConvertTo-Json -Compress)
        $info.EnvironmentVariables['PSModulePath'] = "$($env:SystemRoot)\System32\WindowsPowerShell\v1.0\Modules;$($env:ProgramFiles)\WindowsPowerShell\Modules"
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $info
        if (-not $process.Start()) { throw "Process did not start." }
        $entry.pid = $process.Id
        $entry.status = 'running'
        Write-OwnedLedger -Run $Run
        [CodexOwnedProcess.Native]::Assign($Run.jobHandle, $process)
        $gate.Set() | Out-Null
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $completed = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $completed) {
            $entry.status = 'timed_out'
            [CodexOwnedProcess.Native]::Terminate($Run.jobHandle, 124)
            $process.WaitForExit(2000) | Out-Null
            $entry.status = 'terminated'
            $outText = if ($stdoutTask.AsyncWaitHandle.WaitOne(1000)) { $stdoutTask.Result } else { "" }
            $errText = if ($stderrTask.AsyncWaitHandle.WaitOne(1000)) { $stderrTask.Result } else { "" }
            [IO.File]::WriteAllText($stdoutPath, $outText, [Text.Encoding]::UTF8)
            [IO.File]::WriteAllText($stderrPath, $errText, [Text.Encoding]::UTF8)
            Write-OwnedLedger -Run $Run
            return [pscustomobject]@{ name = $Name; rootPid = $process.Id; exitCode = 124; timedOut = $true; durationMs = ([int]([DateTime]::UtcNow - $started).TotalMilliseconds); stdoutPath = $stdoutPath; stderrPath = $stderrPath; operationalFailure = $false }
        }
        [IO.File]::WriteAllText($stdoutPath, $stdoutTask.Result, [Text.Encoding]::UTF8)
        [IO.File]::WriteAllText($stderrPath, $stderrTask.Result, [Text.Encoding]::UTF8)
        $entry.status = if ($process.ExitCode -eq 0) { 'completed' } else { 'failed' }
        Write-OwnedLedger -Run $Run
        return [pscustomobject]@{ name = $Name; rootPid = $process.Id; exitCode = $process.ExitCode; timedOut = $false; durationMs = ([int]([DateTime]::UtcNow - $started).TotalMilliseconds); stdoutPath = $stdoutPath; stderrPath = $stderrPath; operationalFailure = $false }
    } catch {
        if ($process -and -not $process.HasExited) { [CodexOwnedProcess.Native]::Terminate($Run.jobHandle, 1) }
        $entry.status = 'operational_failure'
        $entry.error = 'owned_process_operational_failure'
        Write-OwnedLedger -Run $Run
        return [pscustomobject]@{ name = $Name; rootPid = if ($process) { $process.Id } else { $null }; exitCode = 1; timedOut = $false; durationMs = ([int]([DateTime]::UtcNow - $started).TotalMilliseconds); stdoutPath = $stdoutPath; stderrPath = $stderrPath; operationalFailure = $true; message = 'owned_process_operational_failure' }
    } finally {
        if ($gate) { $gate.Dispose() }
        if ($process) { $process.Dispose() }
    }
}

function Test-RunOwnedPidAlive {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$LedgerPath)
    if (-not (Test-Path -LiteralPath $LedgerPath)) { return $false }
    $ledger = Get-Content -Raw -LiteralPath $LedgerPath | ConvertFrom-Json
    $entries = @($ledger.entries)
    foreach ($entry in $entries) {
        if ($entry.pid -and (Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue)) { return $true }
    }
    return $false
}

function Close-OwnedProcessRun {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Run)
    if (-not $Run.closed) {
        [CodexOwnedProcess.Native]::Close($Run.jobHandle)
        $Run.closed = $true
        Write-OwnedLedger -Run $Run
    }
}

Export-ModuleMember -Function New-OwnedProcessRun, Invoke-OwnedProcess, Test-RunOwnedPidAlive, Close-OwnedProcessRun



