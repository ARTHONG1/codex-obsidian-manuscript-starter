Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-LocalRestLockPath {
    [CmdletBinding()]
    param([string]$BootstrapRoot)

    # The lock must resolve from inside the bootstrap tree that is actually shipped, so the
    # packaged plugin stays self-contained. The parent location is only a legacy fallback.
    $candidates = @(
        (Join-Path $BootstrapRoot "dependencies.lock.json"),
        (Join-Path (Split-Path -Parent $BootstrapRoot) "dependencies.lock.json")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $candidates[0]
}

function Get-LocalRestLock {
    [CmdletBinding()]
    param([string]$LockPath = (Resolve-LocalRestLockPath -BootstrapRoot (Split-Path -Parent $PSScriptRoot)))

    if (-not (Test-Path -LiteralPath $LockPath)) { throw "Dependency lock file is missing: $LockPath" }
    $lock = Get-Content -Raw -LiteralPath $LockPath | ConvertFrom-Json
    if ($lock.schemaVersion -ne 1 -or $null -eq $lock.localRest) { throw "Dependency lock file has an unsupported schema." }
    if ([string]$lock.localRest.version -notmatch '^\d+\.\d+\.\d+$') { throw "Local REST version is not pinned." }
    foreach ($asset in @($lock.localRest.assets)) {
        if ([string]$asset.url -notmatch '^https://') { throw "Dependency URL must use HTTPS." }
        if ([string]$asset.sha256 -notmatch '^[0-9a-f]{64}$' -or [string]$asset.sha256 -match '^0{64}$') { throw "Dependency SHA-256 is invalid." }
    }
    return $lock.localRest
}

function Assert-LocalRestPluginTargetIsSafe {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [Parameter(Mandatory = $true)] [string]$PluginId
    )

    $target = Join-Path $VaultPath (".obsidian\\plugins\\" + $PluginId)
    if (Test-Path -LiteralPath $target) {
        throw ("Local REST plugin is already present and will not be overwritten: {0}`n" -f $target) +
              "기존 API 키와 설정을 덮어쓰지 않기 위해 중단했습니다. 이 버전은 전용 새 빈 보관함에만 설치할 수 있습니다. " +
              "-VaultPath 에 아직 존재하지 않는 새 폴더 경로를 지정해 다시 실행하세요."
    }
    return $target
}

function Set-EnabledCommunityPlugin {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$EnabledPath,
        [Parameter(Mandatory = $true)] [string]$PluginId
    )

    # Obsidian requires a flat JSON array of plugin-id strings. Wrapping a deserialised empty
    # array in @() yields a one-element array whose element is itself an empty array, which
    # serialises to an object literal and silently disables every community plugin. Build an
    # explicitly typed string list instead, and always force array shape on the way out.
    $enabled = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $EnabledPath) {
        $existing = Get-Content -Raw -LiteralPath $EnabledPath | ConvertFrom-Json
        foreach ($entry in @($existing)) {
            if ($entry -is [string] -and -not [string]::IsNullOrWhiteSpace($entry)) {
                if (-not $enabled.Contains([string]$entry)) { $enabled.Add([string]$entry) }
            }
        }
    }
    if (-not $enabled.Contains([string]$PluginId)) { $enabled.Add([string]$PluginId) }

    $payload = "[" + (($enabled | ForEach-Object { ConvertTo-Json -InputObject $_ }) -join ",") + "]"
    Set-Content -LiteralPath $EnabledPath -Value $payload -Encoding UTF8 -NoNewline
    return $enabled.ToArray()
}

function Install-PinnedLocalRestPlugin {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [switch]$EnableCommunityPlugin,
        [string]$LockPath
    )

    if (-not $EnableCommunityPlugin) {
        throw "Community plugin installation requires explicit -EnableCommunityPlugin consent."
    }
    if (-not (Test-Path -LiteralPath $VaultPath -PathType Container)) { throw "VaultPath does not exist: $VaultPath" }
    $dependency = if ($LockPath) { Get-LocalRestLock -LockPath $LockPath } else { Get-LocalRestLock }
    $obsidianPath = Join-Path $VaultPath ".obsidian"
    $pluginsPath = Join-Path $obsidianPath "plugins"
    $target = Assert-LocalRestPluginTargetIsSafe -VaultPath $VaultPath -PluginId $dependency.pluginId
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ("codex-obsidian-rest-" + [guid]::NewGuid().ToString("N"))
    $staging = Join-Path $pluginsPath ("." + $dependency.pluginId + ".staging-" + [guid]::NewGuid().ToString("N"))

    try {
        New-Item -ItemType Directory -Path $temporary, $staging -Force | Out-Null
        foreach ($asset in @($dependency.assets)) {
            $download = Join-Path $temporary $asset.name
            Invoke-WebRequest -Uri $asset.url -OutFile $download -UseBasicParsing
            $actual = (Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -ne $asset.sha256) { throw "Checksum mismatch for $($asset.name)." }
            Move-Item -LiteralPath $download -Destination (Join-Path $staging $asset.name) -Force
        }
        $manifest = Get-Content -Raw -LiteralPath (Join-Path $staging "manifest.json") | ConvertFrom-Json
        if ($manifest.id -ne $dependency.pluginId) { throw "Downloaded manifest has an unexpected plugin id." }
        New-Item -ItemType Directory -Path $pluginsPath -Force | Out-Null
        Move-Item -LiteralPath $staging -Destination $target

        $appPath = Join-Path $obsidianPath "app.json"
        $app = if (Test-Path -LiteralPath $appPath) { Get-Content -Raw -LiteralPath $appPath | ConvertFrom-Json } else { [pscustomobject]@{} }
        $app | Add-Member -NotePropertyName restrictedMode -NotePropertyValue $false -Force
        $app | ConvertTo-Json | Set-Content -LiteralPath $appPath -Encoding UTF8 -NoNewline

        $enabledPath = Join-Path $obsidianPath "community-plugins.json"
        # Suppress the helper's return value: leaking it into the output stream would make this
        # function emit a collection instead of the single summary object callers index into.
        Set-EnabledCommunityPlugin -EnabledPath $enabledPath -PluginId $dependency.pluginId | Out-Null
        return [pscustomobject]@{ PluginId = $dependency.pluginId; Version = $dependency.version; Path = $target }
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
        if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
    }
}

function Wait-ForLocalRest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$DataPath,
        [int]$TimeoutSeconds = 45
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ("codex-obsidian-ready-" + [guid]::NewGuid().ToString("N"))
    try {
        New-Item -ItemType Directory -Path $temporary -Force | Out-Null
        $certificatePath = Join-Path $temporary "local-rest-ca.pem"
        while ([DateTime]::UtcNow -lt $deadline) {
            if (Test-Path -LiteralPath $DataPath) {
                $data = Get-Content -Raw -LiteralPath $DataPath | ConvertFrom-Json
                $port = [int]$data.port
                # StrictMode turns a missing property into a terminating error, so probe for it.
                $cryptoProperty = $data.PSObject.Properties["crypto"]
                $certificate = if ($cryptoProperty -and $null -ne $cryptoProperty.Value) { [string]$cryptoProperty.Value.cert } else { "" }
                if ($port -gt 0 -and $port -lt 65536 -and -not [string]::IsNullOrWhiteSpace($certificate)) {
                    [IO.File]::WriteAllText($certificatePath, $certificate, [Text.UTF8Encoding]::new($false))
                    & curl.exe --fail --silent --show-error --proto "=https" --max-redirs 0 --cacert $certificatePath "https://127.0.0.1:$port/" 2>$null | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        return [pscustomobject]@{ DataPath = $DataPath; Port = $port }
                    }
                }
            }
            Start-Sleep -Milliseconds 500
        }
        throw "Local REST API did not become ready before the deadline. Keep Obsidian open and retry the doctor command."
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    }
}

function Get-LocalRestConnection {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)] [string]$DataPath)

    if (-not (Test-Path -LiteralPath $DataPath -PathType Leaf)) { throw "Local REST API configuration is missing: $DataPath" }
    $data = Get-Content -Raw -LiteralPath $DataPath | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$data.apiKey)) { throw "Local REST API configuration does not contain an API key." }
    $cryptoProperty = $data.PSObject.Properties["crypto"]
    $certificate = if ($cryptoProperty -and $null -ne $cryptoProperty.Value) { [string]$cryptoProperty.Value.cert } else { "" }
    if ([string]::IsNullOrWhiteSpace($certificate)) { throw "Local REST API configuration does not contain a public certificate." }
    $port = [int]$data.port
    if ($port -lt 1 -or $port -gt 65535) { throw "Local REST API configuration has an invalid port." }
    return [pscustomobject]@{ ApiKey = [string]$data.apiKey; Certificate = $certificate; Port = $port; BaseUrl = "https://127.0.0.1:$port" }
}

function Invoke-LoopbackRestRequest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [psobject]$Connection,
        [Parameter(Mandatory = $true)] [ValidateSet("GET", "PUT", "DELETE")] [string]$Method,
        [Parameter(Mandatory = $true)] [string]$Uri,
        [byte[]]$Body
    )

    if ($Uri -notmatch '^https://127\.0\.0\.1:\d+/vault/') { throw "Only the local 127.0.0.1 vault endpoint is allowed." }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ("codex-obsidian-health-" + [guid]::NewGuid().ToString("N"))
    try {
        New-Item -ItemType Directory -Path $temporary -Force | Out-Null
        $configPath = Join-Path $temporary "curl.conf"
        $responsePath = Join-Path $temporary "response.bin"
        $certificatePath = Join-Path $temporary "local-rest-ca.pem"
        [IO.File]::WriteAllText($certificatePath, [string]$Connection.Certificate, [Text.UTF8Encoding]::new($false))
        $escapedKey = $Connection.ApiKey.Replace('\\', '\\\\').Replace('"', '\\"')
        @(
            "silent",
            "show-error",
            "fail",
            "header = `"Authorization: Bearer $escapedKey`""
        ) | Set-Content -LiteralPath $configPath -Encoding ASCII

        $arguments = @(
            "--config", $configPath,
            "--cacert", $certificatePath,
            "--proto", "=https",
            "--max-redirs", "0",
            "--request", $Method,
            "--output", $responsePath
        )
        if ($null -ne $Body) {
            $bodyPath = Join-Path $temporary "request.bin"
            [IO.File]::WriteAllBytes($bodyPath, $Body)
            $arguments += @("--header", "Content-Type: text/markdown; charset=utf-8", "--data-binary", "@$bodyPath")
        }
        $arguments += $Uri
        & curl.exe @arguments 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Local REST API request failed for $Method $Uri." }
        if (Test-Path -LiteralPath $responsePath) { return [IO.File]::ReadAllBytes($responsePath) }
        return [byte[]]@()
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    }
}

function Test-LocalRestRoundTrip {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)] [string]$DataPath)

    $connection = Get-LocalRestConnection -DataPath $DataPath
    # Local REST API 5.x rejects hidden dot-prefixed vault paths with 404 even though
    # ordinary vault paths are writable. Keep the health note temporary and unique,
    # but use a normal filename so the diagnostic tests the real write/read/delete path.
    $name = "Codex-install-health-" + [guid]::NewGuid().ToString("N") + ".md"
    $relativePath = "_system/$name"
    $uri = $connection.BaseUrl + "/vault/" + $relativePath
    $payload = [Text.Encoding]::UTF8.GetBytes("# Codex connection check`n`n" + [guid]::NewGuid().ToString("N") + "`n")
    try {
        Invoke-LoopbackRestRequest -Connection $connection -Method PUT -Uri $uri -Body $payload | Out-Null
        $readback = Invoke-LoopbackRestRequest -Connection $connection -Method GET -Uri $uri
        if (-not [Linq.Enumerable]::SequenceEqual([byte[]]$payload, [byte[]]$readback)) {
            throw "Local REST API readback did not match the temporary health note."
        }
        Invoke-LoopbackRestRequest -Connection $connection -Method DELETE -Uri $uri | Out-Null
        return [pscustomobject]@{ Status = "ready"; Port = $connection.Port }
    }
    finally {
        try { Invoke-LoopbackRestRequest -Connection $connection -Method DELETE -Uri $uri | Out-Null } catch { }
    }
}

Export-ModuleMember -Function Resolve-LocalRestLockPath, Get-LocalRestLock, Assert-LocalRestPluginTargetIsSafe, Set-EnabledCommunityPlugin, Install-PinnedLocalRestPlugin, Wait-ForLocalRest, Test-LocalRestRoundTrip
