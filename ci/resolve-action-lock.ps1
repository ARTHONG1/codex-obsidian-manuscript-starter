[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "action-lock.json"),
    [hashtable]$Allowlist,
    [scriptblock]$ApiInvoker
)

$ErrorActionPreference = "Stop"
if (-not $Allowlist) {
    $Allowlist = [ordered]@{
        "actions/checkout" = "v4.2.2"
        "actions/setup-python" = "v5.6.0"
        "actions/upload-artifact" = "v4.6.2"
        "gitleaks/gitleaks-action" = "v2.3.9"
    }
}

if (-not $ApiInvoker) {
    $ApiInvoker = {
        param([string]$Url)
        & gh api $Url --header "Accept: application/vnd.github+json"
        if ($LASTEXITCODE -ne 0) { throw "GitHub API lookup failed for $Url." }
    }
}

function Get-TagObject([string]$repository, [string]$ref, [scriptblock]$ApiInvoker) {
    # Dereference annotated tags through the tag object; response data is parsed, never executed.
    $apiBase = "https://api.github.com/repos/"
    $encodedRef = [Uri]::EscapeDataString($ref)
    $refEndpoint = "git/ref/tags/$encodedRef"
    $response = & $ApiInvoker "$apiBase$repository/$refEndpoint"
    $refObject = $response | ConvertFrom-Json
    if ($refObject.object.type -eq "commit") { return $refObject.object.sha }
    if ($refObject.object.type -ne "tag") { throw "Unexpected tag object type for $repository@$ref." }
    $tagResponse = & $ApiInvoker "$apiBase$repository/git/tags/$($refObject.object.sha)"
    $tagObject = $tagResponse | ConvertFrom-Json
    return $tagObject.object.sha
}

$resolved = [ordered]@{}
foreach ($repository in ($Allowlist.Keys | Sort-Object)) {
    $ref = $Allowlist[$repository]
    $sha = Get-TagObject $repository $ref $ApiInvoker
    if ($sha -notmatch '^[0-9a-f]{40}$') { throw "Resolved ref is not a 40-character commit SHA: $repository@$ref." }
    $resolved[$repository] = [ordered]@{
        repository = $repository
        reviewed_ref = $ref
        sha = $sha
    }
}

$target = [IO.Path]::GetFullPath($OutputPath)
$temporary = "$target.$([guid]::NewGuid().ToString('N')).tmp"
$resolved | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporary -Encoding UTF8
Move-Item -LiteralPath $temporary -Destination $target -Force
