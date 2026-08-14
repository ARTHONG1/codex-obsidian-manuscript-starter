[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [Parameter(Mandatory = $true)]
    [string]$Checksums,
    [Parameter(Mandatory = $true)]
    [string]$TestRoot
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Fail([string]$Message) { throw "release verification failed: $Message" }
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
        $lower -match '(^|/)(data\.json|.*\.(pdf|docx|png|jpg|jpeg|webp|pem|key|pfx))$'
}
function Test-Privacy([string]$Path, [byte[]]$Bytes) {
    $lower = (Normalize $Path).ToLowerInvariant()
    if ($lower -match '(^|/)(data\.json|.*\.(pem|key|pfx))$') { return $true }
    if ($Bytes.Length -gt 2MB) { return $false }
    $text = [Text.Encoding]::UTF8.GetString($Bytes).ToLowerInvariant()
    return $text -match 'bearer\s+[a-z0-9._-]{12,}|-----begin (rsa|ec|openssh|private) key-----|github_pat_[a-z0-9_]{20,}|ghp_[a-z0-9]{20,}|sk-[a-z0-9]{20,}'
}
if (-not (Test-Path -LiteralPath $Archive)) { Fail "archive is missing." }
if (-not (Test-Path -LiteralPath $Checksums)) { Fail "checksums are missing." }
$line = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Checksums).Path)).Trim()
if ($line -notmatch '^([0-9a-fA-F]{64})  (.+)$') { Fail "invalid SHA256SUMS format." }
$expectedHash = $Matches[1].ToLowerInvariant()
$expectedName = $Matches[2]
if ([IO.Path]::GetFileName($Archive) -ne $expectedName) { Fail "checksum basename does not match archive." }
$actualHash = Get-Sha256 (Resolve-Path -LiteralPath $Archive).Path
if ($actualHash -ne $expectedHash) { Fail "archive checksum mismatch." }

$patterns = @(
    ".agents/plugins/marketplace.json", ".github/workflows/windows-ci.yml", "bootstrap/**",
    "ci/action-lock.json", "ci/run-*.ps1", "ci/release-allowlist.txt", "dependencies.lock.json",
    "INSTALL_PROMPT.md", "LICENSE", "README.md", "requirements.lock.txt", "SECURITY.md",
    "THIRD_PARTY_NOTICES.md", "CITATION.cff", "docs/INSTALL_GUIDE.md", "docs/USAGE_GUIDE.md",
    "docs/TROUBLESHOOTING.md", "docs/RELEASE.md", "docs/RELEASE_NOTES_v0.5.2.md",
    "plugins/obsidian-manuscript-publisher/**"
)
$zip = [IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Archive).Path)
$members = @()
$bytesByName = @{}
try {
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        $normalized = Normalize $name
        if ($name -ne $normalized -or [IO.Path]::IsPathRooted($name) -or $normalized -match '(^|/)\.\.(/|$)' -or $normalized -match '^[A-Za-z]:/') { Fail "unsafe ZIP member: $name" }
        if ($normalized -ne $name -or $normalized -match '[\x00-\x1f]') { Fail "non-normalized ZIP member: $name" }
        if (Is-Forbidden $normalized -or -not (Is-Allowed $normalized $patterns)) { Fail "member outside release policy: $name" }
        if ($bytesByName.ContainsKey($normalized.ToLowerInvariant())) { Fail "duplicate or case-colliding member: $name" }
        $memory = New-Object IO.MemoryStream
        $entryStream = $entry.Open()
        try { $entryStream.CopyTo($memory) } finally { $entryStream.Close() }
        $bytes = $memory.ToArray()
        $memory.Close()
        if (Test-Privacy $normalized $bytes) { Fail "privacy marker or forbidden content: $name" }
        $bytesByName[$normalized.ToLowerInvariant()] = $bytes
        $members += $normalized
    }
} finally { $zip = $null }
$sortedMembers = Sort-Ordinal $members
if (($sortedMembers -join "`n") -ne ($members -join "`n")) { Fail "members are not sorted." }
$required = @(
    "ci/release-allowlist.txt", "dependencies.lock.json", "requirements.lock.txt",
    "INSTALL_PROMPT.md", "LICENSE", "README.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md",
    "CITATION.cff", "docs/INSTALL_GUIDE.md", "docs/USAGE_GUIDE.md", "docs/TROUBLESHOOTING.md",
    "docs/RELEASE.md", "docs/RELEASE_NOTES_v0.5.2.md",
    "plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json"
)
foreach ($requiredFile in $required) {
    if (-not ($members -contains $requiredFile)) { Fail "missing required member: $requiredFile" }
}
$pluginKey = ($bytesByName.Keys | Where-Object { $_ -eq "plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json" } | Select-Object -First 1)
$plugin = [Text.Encoding]::UTF8.GetString($bytesByName[$pluginKey])
$pluginJson = $plugin | ConvertFrom-Json
if ($pluginJson.version -ne "0.5.2") { Fail "bootstrap identity/version is not v0.5.2." }
$manifestKey = ($bytesByName.Keys | Where-Object { $_ -eq "ci/release-allowlist.txt" } | Select-Object -First 1)
$manifest = [Text.Encoding]::UTF8.GetString($bytesByName[$manifestKey])
if ($manifest -notmatch "plugins/obsidian-manuscript-publisher/\*\*") { Fail "release allowlist identity is incomplete." }
$lockRoot = $bytesByName[("dependencies.lock.json").ToLowerInvariant()]
$lockBootstrap = $bytesByName[("bootstrap/dependencies.lock.json").ToLowerInvariant()]
$lockPlugin = $bytesByName[("plugins/obsidian-manuscript-publisher/bootstrap/dependencies.lock.json").ToLowerInvariant()]
if (-not ($lockRoot -and $lockBootstrap -and $lockPlugin)) { Fail "dependency lock copies are incomplete." }
if (([Convert]::ToBase64String($lockRoot) -ne [Convert]::ToBase64String($lockBootstrap)) -or
    ([Convert]::ToBase64String($lockRoot) -ne [Convert]::ToBase64String($lockPlugin))) { Fail "dependency lock copies differ." }
$target = [IO.Path]::GetFullPath($TestRoot)
if (Test-Path -LiteralPath $target) { Fail "clean install root must not already exist." }
New-Item -ItemType Directory -Path $target | Out-Null
try {
    [IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Archive).Path, $target)
    if (-not (Test-Path -LiteralPath (Join-Path $target "plugins\obsidian-manuscript-publisher\.codex-plugin\plugin.json"))) { Fail "clean install smoke failed." }
    $escaped = Join-Path (Split-Path -Parent $target) "escape.txt"
    if (Test-Path -LiteralPath $escaped) { Fail "extraction escaped its root." }
} catch {
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    throw
}
Write-Output ([ordered]@{ archive = [IO.Path]::GetFileName($Archive); sha256 = $actualHash; members = $members.Count } | ConvertTo-Json -Compress)
