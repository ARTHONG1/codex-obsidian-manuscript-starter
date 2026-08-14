$repoRoot = Split-Path -Parent $PSScriptRoot

Describe "Public release secret and privacy contract" {
    It "does not ship private Local REST configuration or certificate files" {
        $forbiddenNames = @("data.json", "*.pem", "*.key", "*.pfx")
        $forbidden = Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force |
            Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' } |
            Where-Object {
                $name = $_.Name
                $forbiddenNames | Where-Object { $name -like $_ }
            }
        @($forbidden).Count | Should Be 0
    }

    It "does not track generated Python bytecode in the public release" {
        $trackedBytecode = & git -C $repoRoot ls-files -- '*.pyc'
        @($trackedBytecode).Count | Should Be 0
    }

    It "does not contain author-specific paths or PEM private keys" {
        $userProfile = [Environment]::GetFolderPath("UserProfile")
        $authorPathPattern = [regex]::Escape($userProfile)
        $files = Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force |
            Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' -and $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and $_.Length -lt 1MB } |
            Where-Object {
                $relativePath = $_.FullName.Substring($repoRoot.Length).TrimStart([char]92, [char]47)
                & git -C $repoRoot check-ignore --quiet -- $relativePath
                $LASTEXITCODE -ne 0
            }
        $matches = foreach ($file in $files) {
            Select-String -LiteralPath $file.FullName -Pattern "$authorPathPattern|BEGIN (RSA |EC )?PRIVATE KEY|`"apiKey`"\s*:\s*`"[0-9a-f]{32,}`"" -AllMatches -ErrorAction SilentlyContinue
        }
        @($matches).Count | Should Be 0
    }
}
