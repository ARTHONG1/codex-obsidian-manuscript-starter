Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:PublicationFolderName = "옵시디언 원고"
$script:PublicationIndexName = "00 원고 목록.html"
$script:PublicationUsageName = "00 사용 방법.txt"
$script:VaultShortcutName = "00 Obsidian 보관함 폴더.lnk"
$script:ManagedPublicationGuideHeader = "[Codex Obsidian Manuscript - managed publication guide]"
$script:ManagedPublicationIndexMarker = "<!-- Codex Obsidian Manuscript - managed publication index -->"

function ConvertTo-NormalizedFullPath {
    param([Parameter(Mandatory = $true)] [string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "A non-empty filesystem path is required."
    }

    $fullPath = [IO.Path]::GetFullPath($Path)
    $pathRoot = [IO.Path]::GetPathRoot($fullPath)
    if ([string]::Equals($fullPath.TrimEnd("\"), $pathRoot.TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)) {
        return $pathRoot
    }
    return $fullPath.TrimEnd("\")
}

function Test-PathIsWithinOrEqual {
    param(
        [Parameter(Mandatory = $true)] [string]$Candidate,
        [Parameter(Mandatory = $true)] [string]$Parent
    )

    $candidatePath = ConvertTo-NormalizedFullPath -Path $Candidate
    $parentPath = ConvertTo-NormalizedFullPath -Path $Parent
    if ([string]::Equals($candidatePath, $parentPath, [StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $candidatePath.StartsWith($parentPath.TrimEnd("\") + "\", [StringComparison]::OrdinalIgnoreCase)
}

function Assert-NoExistingReparsePoint {
    param([Parameter(Mandatory = $true)] [string]$Path)

    $current = ConvertTo-NormalizedFullPath -Path $Path
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Publication paths cannot contain symbolic links, junctions, or reparse points: $current"
            }
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or [string]::Equals($parent, $current, [StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $current = $parent
    }
}

function Assert-PublicationRootIsSafe {
    param(
        [Parameter(Mandatory = $true)] [string]$PublicationRoot,
        [string]$VaultPath
    )

    $root = ConvertTo-NormalizedFullPath -Path $PublicationRoot
    $driveRoot = [IO.Path]::GetPathRoot($root)
    if ([string]::Equals($root.TrimEnd("\"), $driveRoot.TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)) {
        throw "PublicationRoot cannot be a filesystem root."
    }

    $userProfile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    if (-not [string]::IsNullOrWhiteSpace($userProfile)) {
        $profileRoot = ConvertTo-NormalizedFullPath -Path $userProfile
        if ([string]::Equals($root, $profileRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "PublicationRoot cannot be the user profile root."
        }
    }

    Assert-NoExistingReparsePoint -Path $root
    if (-not [string]::IsNullOrWhiteSpace($VaultPath)) {
        $vault = ConvertTo-NormalizedFullPath -Path $VaultPath
        Assert-NoExistingReparsePoint -Path $vault
        if ((Test-PathIsWithinOrEqual -Candidate $root -Parent $vault) -or (Test-PathIsWithinOrEqual -Candidate $vault -Parent $root)) {
            throw "PublicationRoot and VaultPath must not overlap."
        }
    }
    return $root
}

function Resolve-PublicationRoot {
    [CmdletBinding()]
    param(
        [string]$PublicationRoot,
        [string]$DesktopPath
    )

    if (-not [string]::IsNullOrWhiteSpace($PublicationRoot)) {
        return Assert-PublicationRootIsSafe -PublicationRoot $PublicationRoot
    }

    $desktop = if (-not [string]::IsNullOrWhiteSpace($DesktopPath)) {
        [IO.Path]::GetFullPath($DesktopPath)
    } else {
        [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    }
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        throw "Windows Desktop known-folder resolution returned an empty path."
    }
    return Assert-PublicationRootIsSafe -PublicationRoot (Join-Path $desktop $script:PublicationFolderName)
}

function Get-ExpectedShortcutValues {
    param([Parameter(Mandatory = $true)] [string]$VaultPath)

    $vault = ConvertTo-NormalizedFullPath -Path $VaultPath
    return [pscustomobject]@{
        TargetPath = [IO.Path]::GetFullPath((Join-Path $env:WINDIR "explorer.exe"))
        Arguments = '"' + $vault + '"'
        WorkingDirectory = [IO.Path]::GetFullPath((Split-Path -Parent $vault))
    }
}

function New-ShortcutShell {
    param([scriptblock]$ShellFactory)

    if ($ShellFactory) {
        return & $ShellFactory
    }
    return New-Object -ComObject WScript.Shell
}

function Test-ShortcutMatches {
    param(
        [Parameter(Mandatory = $true)] [object]$Shortcut,
        [Parameter(Mandatory = $true)] [psobject]$Expected
    )

    return [string]::Equals([string]$Shortcut.TargetPath, [string]$Expected.TargetPath, [StringComparison]::OrdinalIgnoreCase) -and
        [string]::Equals([string]$Shortcut.Arguments, [string]$Expected.Arguments, [StringComparison]::Ordinal) -and
        [string]::Equals(([string]$Shortcut.WorkingDirectory).TrimEnd("\"), ([string]$Expected.WorkingDirectory).TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)
}

function New-VaultFolderShortcut {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$PublicationRoot,
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [scriptblock]$ShellFactory
    )

    $root = Assert-PublicationRootIsSafe -PublicationRoot $PublicationRoot -VaultPath $VaultPath
    if (Test-Path -LiteralPath $root -PathType Leaf) {
        throw "PublicationRoot points to a file: $root"
    }
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        New-Item -ItemType Directory -Path $root | Out-Null
    }
    Assert-NoExistingReparsePoint -Path $root

    $shortcutPath = Join-Path $root $script:VaultShortcutName
    $expected = Get-ExpectedShortcutValues -VaultPath $VaultPath
    $shell = New-ShortcutShell -ShellFactory $ShellFactory
    $shortcut = $shell.CreateShortcut($shortcutPath)

    if (Test-Path -LiteralPath $shortcutPath -PathType Leaf) {
        Assert-NoExistingReparsePoint -Path $shortcutPath
        if (-not (Test-ShortcutMatches -Shortcut $shortcut -Expected $expected)) {
            throw "An unmanaged Vault shortcut already exists and will not be overwritten: $shortcutPath"
        }
        return [pscustomobject]@{ Path = $shortcutPath; Status = "ready" }
    }

    $shortcut.TargetPath = $expected.TargetPath
    $shortcut.Arguments = $expected.Arguments
    $shortcut.WorkingDirectory = $expected.WorkingDirectory
    $shortcut.Save()
    return [pscustomobject]@{ Path = $shortcutPath; Status = "created" }
}

function Get-PublicationUsageContent {
    return @"
$($script:ManagedPublicationGuideHeader)
검증 완료 원고 출판함 사용 방법

1. 각 원고의 01 본문-복사용.txt 내용을 복사합니다.
2. 이미지-삽입순서.md를 확인해 images 폴더의 번호 이미지를 차례로 올립니다.
3. HTML과 PDF는 미리보기와 인쇄 확인에만 사용합니다.

이 폴더는 검증된 출판본을 모아 보는 파생 출판함입니다. Obsidian 보관함 원본은 이동하거나 변경하지 않습니다.
"@
}

function Get-EmptyPublicationIndexContent {
    return @"
$($script:ManagedPublicationIndexMarker)
<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>옵시디언 원고</title></head>
<body><h1>검증 완료 원고 출판함</h1><p>검증된 원고를 출판하면 여기에 표시됩니다.</p></body>
</html>
"@
}

function Get-ManagedRootFileStatus {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [string]$Marker
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return "missing"
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return "invalid"
    }

    try {
        Assert-NoExistingReparsePoint -Path $Path
        $content = [string](Get-Content -Raw -LiteralPath $Path -Encoding UTF8 -ErrorAction Stop)
    } catch {
        return "invalid"
    }

    if ($content.StartsWith($Marker, [StringComparison]::Ordinal)) {
        return "ready"
    }
    return "unmanaged"
}

function Initialize-PublicationLibrary {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$PublicationRoot,
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [scriptblock]$ShellFactory
    )

    $root = Assert-PublicationRootIsSafe -PublicationRoot $PublicationRoot -VaultPath $VaultPath
    if (Test-Path -LiteralPath $root -PathType Leaf) {
        throw "PublicationRoot points to a file: $root"
    }

    # Check an existing shortcut before creating or changing any managed root file.
    if (Test-Path -LiteralPath $root -PathType Container) {
        $existingShortcutPath = Join-Path $root $script:VaultShortcutName
        if (Test-Path -LiteralPath $existingShortcutPath -PathType Leaf) {
            $shell = New-ShortcutShell -ShellFactory $ShellFactory
            $existingShortcut = $shell.CreateShortcut($existingShortcutPath)
            $expected = Get-ExpectedShortcutValues -VaultPath $VaultPath
            if (-not (Test-ShortcutMatches -Shortcut $existingShortcut -Expected $expected)) {
                throw "An unmanaged Vault shortcut already exists and will not be overwritten: $existingShortcutPath"
            }
        }
    }

    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        New-Item -ItemType Directory -Path $root | Out-Null
    }
    $shortcut = New-VaultFolderShortcut -PublicationRoot $root -VaultPath $VaultPath -ShellFactory $ShellFactory
    $usagePath = Join-Path $root $script:PublicationUsageName
    $indexPath = Join-Path $root $script:PublicationIndexName
    $usageStatus = Get-ManagedRootFileStatus -Path $usagePath -Marker $script:ManagedPublicationGuideHeader
    $indexStatus = Get-ManagedRootFileStatus -Path $indexPath -Marker $script:ManagedPublicationIndexMarker

    if ($usageStatus -eq "missing") {
        Set-Content -LiteralPath $usagePath -Value (Get-PublicationUsageContent) -Encoding UTF8 -NoNewline
        $usageStatus = "ready"
    }
    if ($indexStatus -eq "missing") {
        Set-Content -LiteralPath $indexPath -Value (Get-EmptyPublicationIndexContent) -Encoding UTF8 -NoNewline
        $indexStatus = "ready"
    }

    return [pscustomobject]@{
        Root = $root
        Status = if ($usageStatus -eq "ready" -and $indexStatus -eq "ready") { "ready" } else { "incomplete" }
        UsageStatus = $usageStatus
        IndexStatus = $indexStatus
        ShortcutStatus = $shortcut.Status
    }
}

function Test-PublicationLibrary {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$PublicationRoot,
        [Parameter(Mandatory = $true)] [string]$VaultPath,
        [scriptblock]$ShellFactory
    )

    $root = Assert-PublicationRootIsSafe -PublicationRoot $PublicationRoot -VaultPath $VaultPath
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        return [pscustomobject]@{
            Root = $root
            Status = "missing"
            UsageStatus = "missing"
            IndexStatus = "missing"
            ShortcutStatus = "missing"
        }
    }

    $usageStatus = Get-ManagedRootFileStatus -Path (Join-Path $root $script:PublicationUsageName) -Marker $script:ManagedPublicationGuideHeader
    $indexStatus = Get-ManagedRootFileStatus -Path (Join-Path $root $script:PublicationIndexName) -Marker $script:ManagedPublicationIndexMarker
    $shortcutPath = Join-Path $root $script:VaultShortcutName
    $shortcutStatus = "missing"

    if (Test-Path -LiteralPath $shortcutPath -PathType Leaf) {
        try {
            Assert-NoExistingReparsePoint -Path $shortcutPath
            $shell = New-ShortcutShell -ShellFactory $ShellFactory
            $shortcut = $shell.CreateShortcut($shortcutPath)
            $expected = Get-ExpectedShortcutValues -VaultPath $VaultPath
            $shortcutStatus = if (Test-ShortcutMatches -Shortcut $shortcut -Expected $expected) { "ready" } else { "unmanaged" }
        } catch {
            $shortcutStatus = "invalid"
        }
    }

    $status = if ($usageStatus -eq "ready" -and $indexStatus -eq "ready" -and $shortcutStatus -eq "ready") { "ready" } else { "incomplete" }
    return [pscustomobject]@{
        Root = $root
        Status = $status
        UsageStatus = $usageStatus
        IndexStatus = $indexStatus
        ShortcutStatus = $shortcutStatus
    }
}

Export-ModuleMember -Function Resolve-PublicationRoot, Initialize-PublicationLibrary, New-VaultFolderShortcut, Test-PublicationLibrary, Assert-NoExistingReparsePoint, Assert-PublicationRootIsSafe
