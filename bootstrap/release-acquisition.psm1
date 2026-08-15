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
    $tagRequest = [Net.HttpWebRequest]::Create("https://api.github.com/repos/$Repository/git/ref/tags/$($release.tag_name)")
    $tagRequest.Method = 'GET'; $tagRequest.AllowAutoRedirect = $false; $tagRequest.UserAgent = 'codex-obsidian-release-acquisition'
    $tagResponse = $tagRequest.GetResponse()
    try { $tagRef = (New-Object IO.StreamReader($tagResponse.GetResponseStream())).ReadToEnd() | ConvertFrom-Json } finally { $tagResponse.Dispose() }
    $commit = [string]$tagRef.object.sha
    if ($commit -notmatch '^[0-9a-fA-F]{40}$') { Fail-Release 'release_commit_invalid' }
    [ordered]@{ Repository=$Repository; Version=$release.tag_name.Substring(1); Tag=$release.tag_name; Commit=$commit; ArchiveUrl=$asset.browser_download_url; ManifestUrl="https://github.com/$Repository/releases/download/$($release.tag_name)/release-manifest.json"; ChecksumsUrl="https://github.com/$Repository/releases/download/$($release.tag_name)/SHA256SUMS" }
}

function Get-VerifiedRelease {
    param([Parameter(Mandatory=$true)]$Release, [Parameter(Mandatory=$true)][string]$DownloadRoot)
    Test-ReleaseArchiveUrl $Release.ArchiveUrl | Out-Null
    foreach ($metadataUrl in @($Release.ManifestUrl, $Release.ChecksumsUrl)) {
        if ([string]$metadataUrl -notmatch "^https://github\.com/" -or [string]$metadataUrl -notmatch "/releases/download/v\d+\.\d+\.\d+/") { Fail-Release 'release_metadata_url_invalid' }
    }
    New-Item -ItemType Directory -Path $DownloadRoot -Force | Out-Null
    $archive = Join-Path $DownloadRoot ([IO.Path]::GetFileName(([Uri]$Release.ArchiveUrl).AbsolutePath))
    $archivePartial = "$archive.partial"
    try { Invoke-WebRequest -Uri $Release.ArchiveUrl -OutFile $archivePartial -UseBasicParsing; Move-Item -LiteralPath $archivePartial -Destination $archive -Force } finally { if (Test-Path -LiteralPath $archivePartial) { Remove-Item -LiteralPath $archivePartial -Force -ErrorAction SilentlyContinue } }
    $archiveHash = Get-ReleaseSha256 $archive
    if ($Release.ArchiveSha256 -and $archiveHash -ne [string]$Release.ArchiveSha256) { Fail-Release 'release_checksum_mismatch' }
    $checksums = Join-Path $DownloadRoot 'SHA256SUMS'
    $manifestPath = Join-Path $DownloadRoot 'release-manifest.json'
    foreach ($download in @(@($Release.ChecksumsUrl, $checksums), @($Release.ManifestUrl, $manifestPath))) {
        $partial = "$($download[1]).partial"
        try { Invoke-WebRequest -Uri $download[0] -OutFile $partial -UseBasicParsing; Move-Item -LiteralPath $partial -Destination $download[1] -Force } finally { if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue } }
    }
    $checksumLines = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($checksums)).Trim().Split("`n")
    $manifestLine = $checksumLines | Where-Object { $_ -match '  release-manifest\.json$' } | Select-Object -First 1
    if (-not $manifestLine -or $manifestLine -notmatch '^([0-9a-fA-F]{64})  release-manifest\.json$' -or $Matches[1].ToLowerInvariant() -ne (Get-ReleaseSha256 $manifestPath)) { Fail-Release 'release_manifest_checksum_mismatch' }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    Test-ReleaseManifest -Manifest $manifest -ExpectedRepository $Release.Repository | Out-Null
    if ([string]$manifest.archive -ne [IO.Path]::GetFileName($archive) -or [string]$manifest.archiveSha256 -ne $archiveHash -or [string]$manifest.commit -ne [string]$Release.Commit) { Fail-Release 'release_manifest_identity_mismatch' }
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        $names = @($zip.Entries | ForEach-Object FullName); Test-ReleaseZipMemberNames $names | Out-Null
        $manifestFiles = @{}; foreach ($file in @($manifest.files)) { $manifestFiles[[string]$file.name] = ([string]$file.sha256).ToLowerInvariant() }
        foreach ($entry in $zip.Entries) {
            $memory = New-Object IO.MemoryStream; $stream = $entry.Open(); try { $stream.CopyTo($memory) } finally { $stream.Dispose() }
            $actual = ([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($memory.ToArray())) -replace '-', '').ToLowerInvariant(); $memory.Dispose()
            if (-not $manifestFiles.ContainsKey($entry.FullName) -or $manifestFiles[$entry.FullName] -ne $actual) { Fail-Release 'release_file_checksum_mismatch' }
        }
        if ($manifestFiles.Count -ne $names.Count) { Fail-Release 'release_manifest_member_set_mismatch' }
    } finally { $zip.Dispose() }
    $root = Join-Path $DownloadRoot ([guid]::NewGuid().ToString('N'))
    try { [IO.Compression.ZipFile]::ExtractToDirectory($archive, $root) } catch { if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }; throw }
    [pscustomobject]@{ ReleaseRoot=$root; Archive=$archive; Manifest=$manifestPath }
}

Export-ModuleMember -Function Resolve-StableRelease, Get-VerifiedRelease, Test-ReleaseManifest, Test-ReleaseArchiveUrl, Test-ReleaseZipMemberNames
