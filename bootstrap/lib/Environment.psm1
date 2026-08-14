Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSScriptRoot "PublicationLibrary.psm1") -Force

function Test-InstallPathsOverlap {
    param(
        [Parameter(Mandatory = $true)] [string]$FirstPath,
        [Parameter(Mandatory = $true)] [string]$SecondPath
    )

    $first = [IO.Path]::GetFullPath($FirstPath).TrimEnd("\")
    $second = [IO.Path]::GetFullPath($SecondPath).TrimEnd("\")
    if ([string]::Equals($first, $second, [StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $first.StartsWith($second + "\", [StringComparison]::OrdinalIgnoreCase) -or
        $second.StartsWith($first + "\", [StringComparison]::OrdinalIgnoreCase)
}

function Resolve-InstallPaths {
    [CmdletBinding()]
    param(
        [string]$VaultPath,
        [string]$RuntimeRoot,
        [string]$PublicationRoot
    )

    if ([string]::IsNullOrWhiteSpace($VaultPath)) {
        $documents = [Environment]::GetFolderPath("MyDocuments")
        $VaultPath = Join-Path $documents "Codex Obsidian Manuscript"
    }
    if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
        $RuntimeRoot = Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript"
    }

    $resolvedVault = [IO.Path]::GetFullPath($VaultPath)
    $resolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
    $resolvedPublication = Resolve-PublicationRoot -PublicationRoot $PublicationRoot
    $root = [IO.Path]::GetPathRoot($resolvedVault)
    if ($resolvedVault.TrimEnd("\\") -eq $root.TrimEnd("\\")) {
        throw "VaultPath cannot be a drive root."
    }

    if (Test-InstallPathsOverlap -FirstPath $resolvedVault -SecondPath $resolvedPublication) {
        throw "PublicationRoot and VaultPath must not overlap."
    }

    [pscustomobject]@{
        VaultPath = $resolvedVault
        RuntimeRoot = $resolvedRuntime
        RuntimeConfigPath = Join-Path $resolvedRuntime "runtime.json"
        RestDataPath = Join-Path $resolvedVault ".obsidian\plugins\obsidian-local-rest-api\data.json"
        PublicationRoot = $resolvedPublication
    }
}

function Save-RuntimeConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [psobject]$Paths
    )

    New-Item -ItemType Directory -Path $Paths.RuntimeRoot -Force | Out-Null
    $payload = [ordered]@{
        schemaVersion = 1
        vaultPath = [IO.Path]::GetFullPath([string]$Paths.VaultPath)
        restDataPath = [IO.Path]::GetFullPath([string]$Paths.RestDataPath)
    }
    $publicationProperty = $Paths.PSObject.Properties["PublicationRoot"]
    if ($publicationProperty -and -not [string]::IsNullOrWhiteSpace([string]$publicationProperty.Value)) {
        $publicationRoot = Resolve-PublicationRoot -PublicationRoot ([string]$publicationProperty.Value)
        if (Test-InstallPathsOverlap -FirstPath $payload.vaultPath -SecondPath $publicationRoot) {
            throw "PublicationRoot and VaultPath must not overlap."
        }
        $payload.publicationRoot = $publicationRoot
    }
    $payload = $payload | ConvertTo-Json
    Set-Content -LiteralPath $Paths.RuntimeConfigPath -Value $payload -Encoding UTF8 -NoNewline
    return $Paths.RuntimeConfigPath
}

function Get-RuntimeConfig {
    [CmdletBinding()]
    param(
        [string]$RuntimeConfigPath = (Join-Path (Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript") "runtime.json")
    )

    if (-not (Test-Path -LiteralPath $RuntimeConfigPath -PathType Leaf)) {
        throw "Runtime configuration is missing. Run bootstrap\\install-windows.ps1 before using the manuscript skill."
    }
    $config = Get-Content -Raw -LiteralPath $RuntimeConfigPath | ConvertFrom-Json
    if ($config.schemaVersion -ne 1 -or [string]::IsNullOrWhiteSpace($config.vaultPath) -or [string]::IsNullOrWhiteSpace($config.restDataPath)) {
        throw "Runtime configuration has an unsupported schema. Re-run bootstrap\\install-windows.ps1."
    }
    $vaultPath = [IO.Path]::GetFullPath([string]$config.vaultPath)
    $restDataPath = [IO.Path]::GetFullPath([string]$config.restDataPath)
    $expectedRestDirectory = [IO.Path]::GetFullPath((Join-Path $vaultPath ".obsidian\\plugins\\obsidian-local-rest-api"))
    $actualRestDirectory = [IO.Path]::GetFullPath((Split-Path -Parent $restDataPath))
    if (-not [string]::Equals($actualRestDirectory.TrimEnd("\\"), $expectedRestDirectory.TrimEnd("\\"), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Runtime configuration points outside the selected vault. Re-run bootstrap\\install-windows.ps1."
    }
    $publicationRoot = $null
    $publicationProperty = $config.PSObject.Properties["publicationRoot"]
    if ($publicationProperty -and -not [string]::IsNullOrWhiteSpace([string]$publicationProperty.Value)) {
        $publicationRoot = Resolve-PublicationRoot -PublicationRoot ([string]$publicationProperty.Value)
        if (Test-InstallPathsOverlap -FirstPath $vaultPath -SecondPath $publicationRoot) {
            throw "Runtime configuration overlaps the selected vault. Re-run bootstrap\\install-windows.ps1."
        }
    }
    return [pscustomobject]@{ schemaVersion = 1; vaultPath = $vaultPath; restDataPath = $restDataPath; publicationRoot = $publicationRoot }
}

function Find-ObsidianExecutable {
    [CmdletBinding()]
    param(
        [string]$LocalAppDataRoot = $env:LOCALAPPDATA,
        [string]$ProgramFilesRoot = $env:ProgramFiles,
        [string]$ProgramFilesX86Root = ${env:ProgramFiles(x86)}
    )

    $candidates = @(
        (Join-Path $LocalAppDataRoot "Programs\Obsidian\Obsidian.exe"),
        (Join-Path $LocalAppDataRoot "Obsidian\Obsidian.exe"),
        (Join-Path $ProgramFilesRoot "Obsidian\Obsidian.exe")
    )
    if (-not [string]::IsNullOrWhiteSpace($ProgramFilesX86Root)) {
        $candidates += (Join-Path $ProgramFilesX86Root "Obsidian\Obsidian.exe")
    }
    return $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

function Get-InstallStagePath {
    param([Parameter(Mandatory = $true)] [string]$RuntimeRoot)
    return Join-Path ([IO.Path]::GetFullPath($RuntimeRoot)) "install-stage.json"
}

function Get-InstallStage {
    param([Parameter(Mandatory = $true)] [string]$RuntimeRoot)
    $path = Get-InstallStagePath -RuntimeRoot $RuntimeRoot
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
    try {
        $state = Get-Content -Raw -LiteralPath $path -Encoding UTF8 | ConvertFrom-Json
        if ($state.schemaVersion -ne 1) { return $null }
        return $state
    } catch { return $null }
}

function Set-InstallStage {
    param(
        [Parameter(Mandatory = $true)] [string]$RuntimeRoot,
        [Parameter(Mandatory = $true)] [ValidateSet("preflight","dependency_ready","vault_ready","local_rest_ready","runtime_ready","doctor_verified","ready")] [string]$Stage
    )
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
    $path = Get-InstallStagePath -RuntimeRoot $RuntimeRoot
    $tmp = "$path.$PID.tmp"
    [ordered]@{ schemaVersion = 1; stage = $Stage; updatedUtc = [DateTime]::UtcNow.ToString("o") } |
        ConvertTo-Json | Set-Content -LiteralPath $tmp -Encoding UTF8 -NoNewline
    Move-Item -LiteralPath $tmp -Destination $path -Force
    return $path
}

function Test-PythonRuntime {
    param([string]$PythonPath)
    $command = if ($PythonPath) { Get-Command $PythonPath -ErrorAction SilentlyContinue } else { Get-Command python -ErrorAction SilentlyContinue }
    if (-not $command) {
        return [pscustomobject]@{ Ready = $false; Reason = "python_missing"; Python = $null; Missing = @(); Mismatched = @{} }
    }
    $probe = Join-Path (Split-Path -Parent $PSScriptRoot) "verify_python_runtime.py"
    try {
        $json = (& $command.Source $probe 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) { throw "probe_failed" }
        $result = $json | ConvertFrom-Json
        return [pscustomobject]@{
            Ready = [bool]$result.ready
            Reason = [string]$result.reason
            Python = [string]$result.python
            PythonVersion = [string]$result.python_version
            Expected = $result.expected
            Actual = $result.actual
            Missing = @($result.missing)
            Mismatched = $result.mismatched
        }
    } catch {
        return [pscustomobject]@{ Ready = $false; Reason = "runtime_probe_failed"; Python = $command.Source; Missing = @(); Mismatched = @{} }
    }
}

Export-ModuleMember -Function Resolve-InstallPaths, Save-RuntimeConfig, Get-RuntimeConfig, Find-ObsidianExecutable, Get-InstallStagePath, Get-InstallStage, Set-InstallStage, Test-PythonRuntime
