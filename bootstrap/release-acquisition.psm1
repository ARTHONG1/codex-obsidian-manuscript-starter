Set-StrictMode -Version Latest

function Fail-Release([string]$Code) { throw $Code }

function Get-ReleaseSha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-ReleaseArchiveUrl([string]$ArchiveUrl) {
    if ($ArchiveUrl -match '/archive/refs/heads/|/archive/refs/tags/|/archive/') { Fail-Release 'branch_archive_rejected' }
    if ($ArchiveUrl -notmatch '^https://github\.com/[^/]+/[^/]+/releases/download/v[^/]+/.+\.zip$') { Fail-Release 'release_archive_url_invalid' }
    $true
}

function Test-ReleaseZipMemberNames([string[]]$Names) {
    $seen = @{}
    foreach ($name in $Names) {
        $normalized = $name.Replace('\', '/')
        if ($name -ne $normalized -or [IO.Path]::IsPathRooted($name) -or
            $normalized -match '(^|/)\.\.(/|$)|^[A-Za-z]:/' -or $normalized -match '[\x00-\x1f]') {
            Fail-Release 'unsafe_zip_path'
        }
        $key = $normalized.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { Fail-Release 'duplicate_or_case_collision' }
        if ($normalized -match '(?i)(^|/)[^/]+\.(exe|com|bat|cmd)$') { Fail-Release 'unexpected_executable' }
        $seen[$key] = $true
    }
    $true
}

function Test-ReleaseManifest {
    param([Parameter(Mandatory=$true)]$Manifest, [Parameter(Mandatory=$true)][string]$ExpectedRepository)
    if ([string]$Manifest.repository -ne $ExpectedRepository) { Fail-Release 'release_repository_mismatch' }
    if ([string]$Manifest.version -notmatch '^\d+\.\d+\.\d+$') { Fail-Release 'stable_release_required' }
    if ([string]$Manifest.tag -ne "v$($Manifest.version)") { Fail-Release 'release_tag_mismatch' }
    if ([string]$Manifest.commit -notmatch '^[0-9a-fA-F]{40}$') { Fail-Release 'release_commit_invalid' }
    if ([string]$Manifest.archiveSha256 -notmatch '^[0-9a-fA-F]{64}$') { Fail-Release 'release_checksum_invalid' }
    if ([string]$Manifest.archive -notmatch '^codex-obsidian-manuscript-starter-v\d+\.\d+\.\d+\.zip$') { Fail-Release 'release_archive_name_invalid' }
    $names = @($Manifest.files | ForEach-Object { [string]$_.name })
    foreach ($file in @($Manifest.files)) {
        if ([string]$file.name -eq '' -or [string]$file.sha256 -notmatch '^[0-9a-fA-F]{64}$') { Fail-Release 'release_file_checksum_invalid' }
    }
    Test-ReleaseZipMemberNames $names | Out-Null
    $true
}

function Resolve-StableRelease {
    param([Parameter(Mandatory=$true)][string]$Repository)
    if ($Repository -notmatch '^[^/]+/[^/]+$') { Fail-Release 'repository_invalid' }
    $uri = "https://api.github.com/repos/$Repository/releases/latest"
    $request = [Net.HttpWebRequest]::Create($uri)
    $request.Method = 'GET'; $request.AllowAutoRedirect = $false
    $request.UserAgent = 'codex-obsidian-release-acquisition'
    $response = $request.GetResponse()
    try { $release = (New-Object IO.StreamReader($response.GetResponseStream())).ReadToEnd() | ConvertFrom-Json } finally { $response.Dispose() }
    if ($release.prerelease -or $release.draft -or [string]$release.tag_name -notmatch '^v\d+\.\d+\.\d+$') { Fail-Release 'stable_release_required' }
    $asset = @($release.assets | Where-Object { $_.name -match '\.zip$' } | Select-Object -First 1)
    if (-not $asset) { Fail-Release 'release_archive_missing' }
    Test-ReleaseArchiveUrl $asset.browser_download_url | Out-Null
    [ordered]@{ Repository=$Repository; Version=$release.tag_name.Substring(1); Tag=$release.tag_name; Commit=[string]$release.target_commitish; ArchiveUrl=$asset.browser_download_url; ManifestUrl="https://github.com/$Repository/releases/download/$($release.tag_name)/release-manifest.json"; ChecksumsUrl="https://github.com/$Repository/releases/download/$($release.tag_name)/SHA256SUMS" }
}

function Get-VerifiedRelease {
    param([Parameter(Mandatory=$true)]$Release, [Parameter(Mandatory=$true)][string]$DownloadRoot)
    Test-ReleaseArchiveUrl $Release.ArchiveUrl | Out-Null
    New-Item -ItemType Directory -Path $DownloadRoot -Force | Out-Null
    $archive = Join-Path $DownloadRoot ([IO.Path]::GetFileName(([Uri]$Release.ArchiveUrl).AbsolutePath))
    Invoke-WebRequest -Uri $Release.ArchiveUrl -OutFile "$archive.partial" -UseBasicParsing
    Move-Item -LiteralPath "$archive.partial" -Destination $archive -Force
    $archiveHash = Get-ReleaseSha256 $archive
    if ($Release.ArchiveSha256 -and $archiveHash -ne [string]$Release.ArchiveSha256) { Fail-Release 'release_checksum_mismatch' }
    $checksums = Join-Path $DownloadRoot 'SHA256SUMS'
    $manifestPath = Join-Path $DownloadRoot 'release-manifest.json'
    Invoke-WebRequest -Uri $Release.ChecksumsUrl -OutFile "$checksums.partial" -UseBasicParsing
    Move-Item -LiteralPath "$checksums.partial" -Destination $checksums -Force
    Invoke-WebRequest -Uri $Release.ManifestUrl -OutFile "$manifestPath.partial" -UseBasicParsing
    Move-Item -LiteralPath "$manifestPath.partial" -Destination $manifestPath -Force
    $checksumLines = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($checksums)).Trim().Split("`n")
    $manifestLine = $checksumLines | Where-Object { $_ -match '  release-manifest\.json$' } | Select-Object -First 1
    if (-not $manifestLine -or $manifestLine -notmatch '^([0-9a-fA-F]{64})  release-manifest\.json$' -or $Matches[1].ToLowerInvariant() -ne (Get-ReleaseSha256 $manifestPath)) { Fail-Release 'release_manifest_checksum_mismatch' }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    Test-ReleaseManifest -Manifest $manifest -ExpectedRepository $Release.Repository | Out-Null
    if ([string]$manifest.archive -ne [IO.Path]::GetFileName($archive) -or [string]$manifest.archiveSha256 -ne $archiveHash) { Fail-Release 'release_manifest_archive_mismatch' }
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try { $names = @($zip.Entries | ForEach-Object FullName); Test-ReleaseZipMemberNames $names | Out-Null } finally { $zip.Dispose() }
    $root = Join-Path $DownloadRoot ([guid]::NewGuid().ToString('N'))
    [IO.Compression.ZipFile]::ExtractToDirectory($archive, $root)
    [pscustomobject]@{ ReleaseRoot=$root; Archive=$archive; Manifest=$manifestPath }
}

Export-ModuleMember -Function Resolve-StableRelease, Get-VerifiedRelease, Test-ReleaseManifest, Test-ReleaseArchiveUrl, Test-ReleaseZipMemberNames
