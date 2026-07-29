Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-InstallPaths {
    [CmdletBinding()]
    param(
        [string]$VaultPath,
        [string]$RuntimeRoot
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
    $root = [IO.Path]::GetPathRoot($resolvedVault)
    if ($resolvedVault.TrimEnd("\\") -eq $root.TrimEnd("\\")) {
        throw "VaultPath cannot be a drive root."
    }

    [pscustomobject]@{
        VaultPath = $resolvedVault
        RuntimeRoot = $resolvedRuntime
        RuntimeConfigPath = Join-Path $resolvedRuntime "runtime.json"
        RestDataPath = Join-Path $resolvedVault ".obsidian\plugins\obsidian-local-rest-api\data.json"
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
        vaultPath = $Paths.VaultPath
        restDataPath = $Paths.RestDataPath
    } | ConvertTo-Json
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
    return [pscustomobject]@{ schemaVersion = 1; vaultPath = $vaultPath; restDataPath = $restDataPath }
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

Export-ModuleMember -Function Resolve-InstallPaths, Save-RuntimeConfig, Get-RuntimeConfig, Find-ObsidianExecutable
