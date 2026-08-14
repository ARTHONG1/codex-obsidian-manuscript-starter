Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSScriptRoot "PublicationLibrary.psm1") -Force

function ConvertTo-InstallPath {
    param([Parameter(Mandatory = $true)] [string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "A non-empty filesystem path is required."
    }
    $fullPath = [IO.Path]::GetFullPath($Path)
    $pathRoot = [IO.Path]::GetPathRoot($fullPath)
    if ([string]::Equals($fullPath.TrimEnd("\"), $pathRoot.TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)) {
        return $pathRoot
    }
    return $fullPath.TrimEnd("\")
}

function Test-InstallPathsOverlap {
    param(
        [Parameter(Mandatory = $true)] [string]$FirstPath,
        [Parameter(Mandatory = $true)] [string]$SecondPath
    )

    $first = ConvertTo-InstallPath -Path $FirstPath
    $second = ConvertTo-InstallPath -Path $SecondPath
    if ([string]::Equals($first, $second, [StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $first.StartsWith($second + "\", [StringComparison]::OrdinalIgnoreCase) -or
        $second.StartsWith($first + "\", [StringComparison]::OrdinalIgnoreCase)
}

function Assert-InstallPathSetIsSafe {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [AllowNull()] [string]$RuntimeRoot,
        [AllowNull()] [string]$PublicationRoot
    )

    $paths = [ordered]@{
        Vault = ConvertTo-InstallPath -Path $VaultPath
        Runtime = if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) { $null } else { ConvertTo-InstallPath -Path $RuntimeRoot }
        Publication = $null
    }
    if (-not [string]::IsNullOrWhiteSpace($PublicationRoot)) {
        $paths.Publication = Assert-PublicationRootIsSafe -PublicationRoot $PublicationRoot
    }

    $vaultDriveRoot = [IO.Path]::GetPathRoot($paths.Vault)
    if ([string]::Equals($paths.Vault.TrimEnd("\"), $vaultDriveRoot.TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)) {
        throw "VaultPath cannot be a drive root."
    }
    Assert-NoExistingReparsePoint -Path $paths.Vault
    if ($paths.Runtime) {
        Assert-NoExistingReparsePoint -Path $paths.Runtime
    }
    if ($paths.Publication) {
        Assert-NoExistingReparsePoint -Path $paths.Publication
    }

    $pairs = @(
        @{ First = "VaultPath"; FirstPath = $paths.Vault; Second = "RuntimeRoot"; SecondPath = $paths.Runtime },
        @{ First = "VaultPath"; FirstPath = $paths.Vault; Second = "PublicationRoot"; SecondPath = $paths.Publication },
        @{ First = "RuntimeRoot"; FirstPath = $paths.Runtime; Second = "PublicationRoot"; SecondPath = $paths.Publication }
    )
    foreach ($pair in $pairs) {
        if ([string]::IsNullOrWhiteSpace([string]$pair.FirstPath) -or [string]::IsNullOrWhiteSpace([string]$pair.SecondPath)) {
            continue
        }
        if (Test-InstallPathsOverlap -FirstPath $pair.FirstPath -SecondPath $pair.SecondPath) {
            throw "$($pair.First) and $($pair.Second) must not overlap."
        }
    }

    return [pscustomobject]@{
        VaultPath = $paths.Vault
        RuntimeRoot = $paths.Runtime
        PublicationRoot = $paths.Publication
    }
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
    $safe = Assert-InstallPathSetIsSafe -VaultPath $resolvedVault -RuntimeRoot $resolvedRuntime -PublicationRoot $resolvedPublication

    [pscustomobject]@{
        VaultPath = $safe.VaultPath
        RuntimeRoot = $safe.RuntimeRoot
        RuntimeConfigPath = Join-Path $safe.RuntimeRoot "runtime.json"
        RestDataPath = Join-Path $safe.VaultPath ".obsidian\plugins\obsidian-local-rest-api\data.json"
        PublicationRoot = $safe.PublicationRoot
    }
}

function Save-RuntimeConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [psobject]$Paths,
        [psobject]$PythonRuntime
    )

    $publicationRoot = $null
    $publicationProperty = $Paths.PSObject.Properties["PublicationRoot"]
    if ($publicationProperty) {
        $publicationRoot = [string]$publicationProperty.Value
    }
    $runtimeForValidation = [string]$Paths.RuntimeRoot
    if (-not [string]::Equals([IO.Path]::GetFileName([string]$Paths.RuntimeConfigPath), "runtime.json", [StringComparison]::OrdinalIgnoreCase)) {
        $runtimeForValidation = $null
    }
    $safe = Assert-InstallPathSetIsSafe -VaultPath ([string]$Paths.VaultPath) -RuntimeRoot $runtimeForValidation -PublicationRoot $publicationRoot
    $runtimeRoot = [IO.Path]::GetFullPath([string]$Paths.RuntimeRoot)
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    $payload = [ordered]@{
        schemaVersion = 2
        vaultPath = $safe.VaultPath
        restDataPath = [IO.Path]::GetFullPath([string]$Paths.RestDataPath)
        pythonExecutable = $null
        venvRoot = $null
        venvPythonExecutable = $null
        requirementsHash = $null
        lastCompletedStage = $null
    }
    if ($PythonRuntime) {
        $payload.pythonExecutable = Assert-AbsoluteRuntimePath -Path $PythonRuntime.BasePython -Name "pythonExecutable"
        $payload.venvRoot = Assert-AbsoluteRuntimePath -Path $PythonRuntime.VenvRoot -Name "venvRoot"
        $payload.venvPythonExecutable = Assert-AbsoluteRuntimePath -Path $PythonRuntime.Python -Name "venvPythonExecutable"
        if ([string]$PythonRuntime.RequirementsHash -notmatch "^[0-9a-fA-F]{64}$") {
            throw "requirementsHash must be a 64-character SHA-256 digest."
        }
        $payload.requirementsHash = ([string]$PythonRuntime.RequirementsHash).ToLowerInvariant()
    }
    if ($safe.PublicationRoot) {
        $payload.publicationRoot = $safe.PublicationRoot
    }
    Write-AtomicUtf8Json -Path $Paths.RuntimeConfigPath -Payload $payload
    return $Paths.RuntimeConfigPath
}

function Test-NoReparsePointInPath {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $false }
        }
        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) { break }
        $current = $parent
    }
    return $true
}

function Assert-AtomicParent {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    $parent = Split-Path -Parent $full
    if (-not $parent -or -not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Atomic destination parent does not exist."
    }
    if (-not (Test-NoReparsePointInPath -Path $parent)) {
        throw "Atomic destination parent contains a reparse point."
    }
    return $full
}

function Write-AtomicUtf8Json {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [object]$Payload
    )
    $full = Assert-AtomicParent -Path $Path
    $temp = Join-Path (Split-Path -Parent $full) (("." + [IO.Path]::GetFileName($full)) + "." + [guid]::NewGuid().ToString("N") + ".tmp")
    try {
        $json = $Payload | ConvertTo-Json -Depth 8
        $utf8 = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($temp, $json, $utf8)
        Move-Item -LiteralPath $temp -Destination $full -Force
    } finally {
        if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
    }
}

function Assert-AbsoluteRuntimePath {
    param([string]$Path, [string]$Name)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path)) {
        throw "$Name must be an absolute path."
    }
    return [IO.Path]::GetFullPath($Path)
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
    if (($config.schemaVersion -ne 1 -and $config.schemaVersion -ne 2) -or [string]::IsNullOrWhiteSpace($config.vaultPath) -or [string]::IsNullOrWhiteSpace($config.restDataPath)) {
        throw "Runtime configuration has an unsupported schema. Re-run bootstrap\\install-windows.ps1."
    }
    $vaultPath = [IO.Path]::GetFullPath([string]$config.vaultPath)
    $runtimeRoot = $null
    if ([string]::Equals([IO.Path]::GetFileName($RuntimeConfigPath), "runtime.json", [StringComparison]::OrdinalIgnoreCase)) {
        $runtimeRoot = [IO.Path]::GetFullPath((Split-Path -Parent $RuntimeConfigPath))
    }
    $restDataPath = [IO.Path]::GetFullPath([string]$config.restDataPath)
    $expectedRestDirectory = [IO.Path]::GetFullPath((Join-Path $vaultPath ".obsidian\\plugins\\obsidian-local-rest-api"))
    $actualRestDirectory = [IO.Path]::GetFullPath((Split-Path -Parent $restDataPath))
    if (-not [string]::Equals($actualRestDirectory.TrimEnd("\\"), $expectedRestDirectory.TrimEnd("\\"), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Runtime configuration points outside the selected vault. Re-run bootstrap\\install-windows.ps1."
    }
    $publicationRoot = $null
    $publicationProperty = $config.PSObject.Properties["publicationRoot"]
    if ($publicationProperty -and -not [string]::IsNullOrWhiteSpace([string]$publicationProperty.Value)) {
        $publicationRoot = [string]$publicationProperty.Value
    }
    $safe = Assert-InstallPathSetIsSafe -VaultPath $vaultPath -RuntimeRoot $runtimeRoot -PublicationRoot $publicationRoot
    $vaultPath = $safe.VaultPath
    $runtimeRoot = $safe.RuntimeRoot
    $publicationRoot = $safe.PublicationRoot
    if ($config.schemaVersion -eq 1) {
        return [pscustomobject]@{
            schemaVersion = 1
            vaultPath = $vaultPath
            restDataPath = $restDataPath
            publicationRoot = $publicationRoot
            pythonExecutable = $null
            venvRoot = $null
            venvPythonExecutable = $null
            requirementsHash = $null
            lastCompletedStage = $null
            NeedsMigration = $true
        }
    }
    foreach ($name in @("pythonExecutable", "venvRoot", "venvPythonExecutable")) {
        $property = $config.PSObject.Properties[$name]
        if ($property -and $null -ne $property.Value -and [string]$property.Value -notmatch "^[A-Za-z]:\\|^\\\\") {
            throw "Runtime configuration contains an invalid $name."
        }
    }
    if ($config.requirementsHash -and [string]$config.requirementsHash -notmatch "^[0-9a-fA-F]{64}$") {
        throw "Runtime configuration contains an invalid requirementsHash."
    }
    return [pscustomobject]@{
        schemaVersion = 2
        vaultPath = $vaultPath
        restDataPath = $restDataPath
        publicationRoot = $publicationRoot
        pythonExecutable = if ($config.pythonExecutable) { [IO.Path]::GetFullPath([string]$config.pythonExecutable) } else { $null }
        venvRoot = if ($config.venvRoot) { [IO.Path]::GetFullPath([string]$config.venvRoot) } else { $null }
        venvPythonExecutable = if ($config.venvPythonExecutable) { [IO.Path]::GetFullPath([string]$config.venvPythonExecutable) } else { $null }
        requirementsHash = if ($config.requirementsHash) { ([string]$config.requirementsHash).ToLowerInvariant() } else { $null }
        lastCompletedStage = if ($config.lastCompletedStage) { [string]$config.lastCompletedStage } else { $null }
        NeedsMigration = $false
    }
}

function Convert-RuntimeConfigV1ToV2 {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$RuntimeConfigPath,
        [Parameter(Mandatory = $true)] [psobject]$Paths,
        [Parameter(Mandatory = $true)] [psobject]$PythonRuntime
    )
    $full = [IO.Path]::GetFullPath($RuntimeConfigPath)
    $original = [IO.File]::ReadAllBytes($full)
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
    $backup = "$full.$stamp.v1.bak"
    [IO.File]::Copy($full, $backup, $false)
    try {
        Save-RuntimeConfig -Paths $Paths -PythonRuntime $PythonRuntime | Out-Null
        return $backup
    } catch {
        [IO.File]::WriteAllBytes($full, $original)
        throw
    }
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
        if ($state.schemaVersion -ne 2) { return $null }
        return $state
    } catch { return $null }
}

function Set-InstallStage {
    param(
        [Parameter(Mandatory = $true)] [string]$RuntimeRoot,
        [Parameter(Mandatory = $true)] [ValidateSet("preflight","base_python_ready","venv_ready","dependencies_ready","dependency_ready","vault_ready","local_rest_ready","runtime_ready","doctor_verified","ready")] [string]$Stage
    )
    if ($Stage -eq "dependency_ready") { $Stage = "dependencies_ready" }
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
    $path = Get-InstallStagePath -RuntimeRoot $RuntimeRoot
    $updatedUtc = [DateTime]::UtcNow.ToString("o")
    Write-AtomicUtf8Json -Path $path -Payload ([ordered]@{ schemaVersion = 2; stage = $Stage; updatedUtc = $updatedUtc })
    $runtimePath = Join-Path ([IO.Path]::GetFullPath($RuntimeRoot)) "runtime.json"
    if (Test-Path -LiteralPath $runtimePath -PathType Leaf) {
        $runtime = Get-RuntimeConfig -RuntimeConfigPath $runtimePath
        if ($runtime.schemaVersion -eq 2) {
            $runtime.lastCompletedStage = $Stage
            Write-AtomicUtf8Json -Path $runtimePath -Payload ([ordered]@{
                schemaVersion = 2
                vaultPath = $runtime.vaultPath
                restDataPath = $runtime.restDataPath
                publicationRoot = $runtime.publicationRoot
                pythonExecutable = $runtime.pythonExecutable
                venvRoot = $runtime.venvRoot
                venvPythonExecutable = $runtime.venvPythonExecutable
                requirementsHash = $runtime.requirementsHash
                lastCompletedStage = $Stage
            })
        }
    }
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

Export-ModuleMember -Function Resolve-InstallPaths, Assert-InstallPathSetIsSafe, Save-RuntimeConfig, Get-RuntimeConfig, Convert-RuntimeConfigV1ToV2, Find-ObsidianExecutable, Get-InstallStagePath, Get-InstallStage, Set-InstallStage, Test-PythonRuntime
