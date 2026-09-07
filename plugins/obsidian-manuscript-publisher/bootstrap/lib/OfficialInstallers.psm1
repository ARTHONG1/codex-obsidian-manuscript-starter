Set-StrictMode -Version Latest

function Read-OfficialInstallerLock {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "official_installer_lock_missing" }
    try { $lock = Get-Content -Raw -LiteralPath $Path -Encoding UTF8 | ConvertFrom-Json } catch { throw "official_installer_lock_invalid" }
    if ($lock.schemaVersion -ne 1 -or @($lock.installers).Count -lt 2) { throw "official_installer_lock_unsupported" }
    foreach ($entry in @($lock.installers)) {
        $uri = [Uri]$entry.url
        if ($uri.Scheme -ne "https" -or $uri.Host -notin @("www.python.org", "github.com")) { throw "official_installer_url_not_allowed" }
        if ([string]$entry.sha256 -notmatch '^[0-9a-f]{64}$') { throw "official_installer_hash_invalid" }
        if ([string]$entry.architecture -ne "x64" -or [string]::IsNullOrWhiteSpace([string]$entry.signerSubjectContains)) { throw "official_installer_metadata_invalid" }
        if (@($entry.arguments).Count -eq 0) { throw "official_installer_arguments_missing" }
    }
    return $lock
}

function Get-VerifiedOfficialInstallerArtifact {
    param(
        [Parameter(Mandatory = $true)]$Entry,
        [Parameter(Mandatory = $true)][string]$DestinationRoot,
        [scriptblock]$Downloader,
        [scriptblock]$SignatureReader
    )
    $uri = [Uri]$Entry.url
    if ($uri.Scheme -ne "https" -or $uri.Host -notin @("www.python.org", "github.com")) { throw "official_installer_url_not_allowed" }
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    $safeName = ([IO.Path]::GetFileName($uri.AbsolutePath) -replace '[^A-Za-z0-9._-]', '_')
    $partial = Join-Path $DestinationRoot ($safeName + ".partial")
    $final = Join-Path $DestinationRoot $safeName
    try {
        if ($Downloader) { & $Downloader $uri.AbsoluteUri $partial } else { Invoke-WebRequest -Uri $uri.AbsoluteUri -OutFile $partial -UseBasicParsing }
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $partial).Hash.ToLowerInvariant()
        if ($hash -ne ([string]$Entry.sha256).ToLowerInvariant()) { throw "official_installer_hash_mismatch" }
        $signature = if ($SignatureReader) { & $SignatureReader $partial } else { Get-AuthenticodeSignature -LiteralPath $partial }
        if ([string]$signature.Status -ne "Valid" -or [string]$signature.SignerCertificate.Subject -notlike ("*" + [string]$Entry.signerSubjectContains + "*")) { throw "official_installer_signature_invalid" }
        Move-Item -LiteralPath $partial -Destination $final -Force
        return $final
    } catch {
        Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        throw
    }
}

function Invoke-VerifiedOfficialInstaller {
    param(
        [Parameter(Mandatory = $true)][string]$ArtifactPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [scriptblock]$Launcher
    )
    if (-not (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)) { throw "official_installer_artifact_missing" }
    if ($Launcher) { return & $Launcher $ArtifactPath $Arguments }
    $process = Start-Process -FilePath $ArtifactPath -ArgumentList $Arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "official_installer_exit_failed" }
    return [pscustomobject]@{ Status = "installed"; ExitCode = $process.ExitCode }
}

Export-ModuleMember -Function Read-OfficialInstallerLock, Get-VerifiedOfficialInstallerArtifact, Invoke-VerifiedOfficialInstaller
