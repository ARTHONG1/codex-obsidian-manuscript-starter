[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Fail([string]$Message) { throw "release build failed: $Message" }
function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path))) -replace "-", "").ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Normalize([string]$Path) {
    $normalized = $Path -replace "\\", "/"
    while ($normalized.StartsWith("./")) { $normalized = $normalized.Substring(2) }
    return $normalized
}
function Sort-Ordinal([string[]]$Values) {
    $list = New-Object 'System.Collections.Generic.List[string]'
    foreach ($value in $Values) { [void]$list.Add($value) }
    $list.Sort([StringComparer]::Ordinal)
    return @($list)
}
function Is-Allowed([string]$Path, [string[]]$Patterns) {
    $normalized = Normalize $Path
    foreach ($pattern in $Patterns) {
        $regex = "^" + [regex]::Escape((Normalize $pattern)).Replace("\*\*", ".*").Replace("\*", "[^/]*") + "$"
        if ($normalized -match $regex) { return $true }
    }
    return $false
}
function Is-Forbidden([string]$Path) {
    $lower = (Normalize $Path).ToLowerInvariant()
    return $lower -match '(^|/)(\.git|\.worktrees|\.planning|__pycache__|node_modules|artifacts|outputs?|vault|backups?)(/|$)' -or
        $lower -match '(^|/)(data\.json|.*\.(pdf|docx|png|jpg|jpeg|webp|pem|key|pfx|zip))$'
}
function Test-Privacy([string]$Path, [byte[]]$Bytes) {
    $lower = (Normalize $Path).ToLowerInvariant()
    if ($lower -match '(^|/)(data\.json|.*\.(pem|key|pfx))$') { return $true }
    if ($Bytes.Length -gt 2MB) { return $false }
    $text = [Text.Encoding]::UTF8.GetString($Bytes).ToLowerInvariant()
    return $text -match 'bearer\s+[a-z0-9._-]{12,}|-----begin (rsa|ec|openssh|private) key-----|github_pat_[a-z0-9_]{20,}|ghp_[a-z0-9]{20,}|sk-[a-z0-9]{20,}'
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$output = [IO.Path]::GetFullPath($OutputRoot)
$allowlistPath = Join-Path $source "ci\release-allowlist.txt"
if (-not (Test-Path -LiteralPath (Join-Path $source ".git"))) { Fail "SourceRoot must be a Git worktree." }
if (-not (Test-Path -LiteralPath $allowlistPath)) { Fail "release allowlist is missing." }
$patterns = @(Get-Content -LiteralPath $allowlistPath | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } | ForEach-Object { $_.Trim() })
$tracked = @(& git -C $source ls-files -z)
if ($LASTEXITCODE -ne 0) { Fail "git ls-files failed." }
$trackedText = ($tracked -join "")
$files = @($trackedText -split "`0" | Where-Object { $_ })
if ($files.Count -eq 0) { Fail "no tracked files found." }
$required = @(
    "ci/release-allowlist.txt", "dependencies.lock.json", "requirements.lock.txt",
    "INSTALL_PROMPT.md", "LICENSE", "README.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md",
    "CITATION.cff", "docs/INSTALL_GUIDE.md", "docs/TROUBLESHOOTING.md", "docs/RELEASE.md",
    "plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json"
)
foreach ($requiredFile in $required) {
    if ($files -notcontains $requiredFile) { Fail "required release file is not tracked: $requiredFile" }
}
$candidates = @($files | Where-Object { Is-Allowed $_ $patterns })
foreach ($candidate in $candidates) {
    if (Is-Forbidden $candidate) { Fail "forbidden release member: $candidate" }
}
if ($candidates.Count -eq 0) { Fail "allowlist selected no files." }
$candidates = Sort-Ordinal $candidates

$plugin = Join-Path $source "plugins\obsidian-manuscript-publisher\.codex-plugin\plugin.json"
$pluginJson = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($plugin)) | ConvertFrom-Json
if ($pluginJson.version -ne $Version) { Fail "plugin version $($pluginJson.version) does not match requested $Version." }
New-Item -ItemType Directory -Path $output -Force | Out-Null
$archivePath = Join-Path $output "codex-obsidian-manuscript-starter-v$Version.zip"
if (Test-Path -LiteralPath $archivePath) { Remove-Item -LiteralPath $archivePath -Force }
$archive = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($relative in $candidates) {
        $bytes = [IO.File]::ReadAllBytes((Join-Path $source ($relative -replace "/", "\")))
        if (Test-Privacy $relative $bytes) { Fail "privacy marker or secret-like file: $relative" }
        $entry = $archive.CreateEntry((Normalize $relative), [IO.Compression.CompressionLevel]::Optimal)
        $stream = $entry.Open()
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
    }
} finally { $archive.Dispose() }
$hash = Get-Sha256 $archivePath
$commit = (& git -C $source rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-fA-F]{40}$') { Fail "unable to resolve immutable commit." }
$remote = (& git -C $source config --get remote.origin.url).Trim()
$repository = 'ARTHONG1/codex-obsidian-manuscript-starter'
if ($remote -match 'github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$') { $repository = $Matches[1] }
$fileEntries = @(
    foreach ($relative in $candidates) {
        [ordered]@{ name = (Normalize $relative); sha256 = (Get-Sha256 (Join-Path $source ($relative -replace '/', '\'))) }
    }
)
$manifest = [ordered]@{
    schemaVersion = 1; repository = $repository; version = $Version; tag = "v$Version"; commit = $commit
    archive = [IO.Path]::GetFileName($archivePath); archiveSha256 = $hash; files = $fileEntries
}
$manifestPath = Join-Path $output 'release-manifest.json'
$manifestJson = $manifest | ConvertTo-Json -Depth 6 -Compress
[IO.File]::WriteAllText($manifestPath, $manifestJson, (New-Object Text.UTF8Encoding($false)))
$manifestHash = Get-Sha256 $manifestPath
Set-Content -LiteralPath (Join-Path $output "SHA256SUMS") -Value "$hash  $([IO.Path]::GetFileName($archivePath))`n$manifestHash  release-manifest.json" -Encoding ASCII
Write-Output $archivePath
