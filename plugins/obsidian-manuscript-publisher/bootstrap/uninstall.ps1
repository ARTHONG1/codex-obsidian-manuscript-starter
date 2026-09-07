#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript"),
    [switch]$RemoveRuntimeConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)
$defaultRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "CodexObsidianManuscript"))
if (-not [string]::Equals($runtimeRoot.TrimEnd("\\"), $defaultRoot.TrimEnd("\\"), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Only the default CodexObsidianManuscript runtime directory may be modified by this script."
}
$configPath = Join-Path $runtimeRoot "runtime.json"
if (-not (Test-Path -LiteralPath $configPath)) {
    return [pscustomobject]@{ Status = "runtime_config_already_absent" }
}
if (-not $RemoveRuntimeConfig) {
    return [pscustomobject]@{
        Status = "no_changes_made"
        Recovery = "Re-run with -RemoveRuntimeConfig to forget only the local vault connection. This command never deletes notes, the vault, or the Obsidian plugin."
    }
}
Remove-Item -LiteralPath $configPath -Force
[pscustomobject]@{
    Status = "runtime_config_removed"
    Note = "The vault, notes, and Obsidian plugin were left unchanged."
}
