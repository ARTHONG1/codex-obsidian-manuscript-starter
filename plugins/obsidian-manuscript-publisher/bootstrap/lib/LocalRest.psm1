Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-LocalRestLock {
    [CmdletBinding()]
    param([string]$LockPath = (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "dependencies.lock.json"))

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
        throw "Local REST plugin is already present and will not be overwritten: $target"
    }
    return $target
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
        $enabled = if (Test-Path -LiteralPath $enabledPath) { @(Get-Content -Raw -LiteralPath $enabledPath | ConvertFrom-Json) } else { @() }
        if ($enabled -notcontains $dependency.pluginId) { $enabled += $dependency.pluginId }
        $enabled | ConvertTo-Json | Set-Content -LiteralPath $enabledPath -Encoding UTF8 -NoNewline
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
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $DataPath) {
            $data = Get-Content -Raw -LiteralPath $DataPath | ConvertFrom-Json
            $port = [int]$data.port
            if ($port -gt 0 -and $port -lt 65536) {
                & curl.exe --fail --silent --show-error --insecure "https://127.0.0.1:$port/" 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    return [pscustomobject]@{ DataPath = $DataPath; Port = $port }
                }
            }
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Local REST API did not become ready before the deadline. Keep Obsidian open and retry the doctor command."
}

function Get-LocalRestConnection {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)] [string]$DataPath)

    if (-not (Test-Path -LiteralPath $DataPath -PathType Leaf)) { throw "Local REST API configuration is missing: $DataPath" }
    $data = Get-Content -Raw -LiteralPath $DataPath | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$data.apiKey)) { throw "Local REST API configuration does not contain an API key." }
    $port = [int]$data.port
    if ($port -lt 1 -or $port -gt 65535) { throw "Local REST API configuration has an invalid port." }
    return [pscustomobject]@{ ApiKey = [string]$data.apiKey; Port = $port; BaseUrl = "https://127.0.0.1:$port" }
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
        $escapedKey = $Connection.ApiKey.Replace('\\', '\\\\').Replace('"', '\\"')
        @(
            "insecure",
            "silent",
            "show-error",
            "fail",
            "header = `"Authorization: Bearer $escapedKey`""
        ) | Set-Content -LiteralPath $configPath -Encoding ASCII

        $arguments = @("--config", $configPath, "--request", $Method, "--output", $responsePath)
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
    $name = ".codex-install-health-" + [guid]::NewGuid().ToString("N") + ".md"
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

Export-ModuleMember -Function Get-LocalRestLock, Assert-LocalRestPluginTargetIsSafe, Install-PinnedLocalRestPlugin, Wait-ForLocalRest, Test-LocalRestRoundTrip
