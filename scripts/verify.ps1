$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$catalogPath = Join-Path $repoRoot 'catalog/skills.json'
$catalog = Get-Content -Raw -LiteralPath $catalogPath | ConvertFrom-Json

if ($catalog.schemaVersion -ne 1) {
    throw "Unsupported catalog schemaVersion: $($catalog.schemaVersion)"
}

$seen = @{}
$expected = @('interactive-workflow-workbench', 'pr-review-workbench')

function Get-PackageHash([string]$SkillDir) {
    $files = Get-ChildItem -LiteralPath $SkillDir -Recurse -File |
        Where-Object { $_.Extension -ne '.pyc' -and $_.FullName -notmatch '[\\/]__pycache__[\\/]' } |
        Sort-Object FullName
    $builder = [System.Text.StringBuilder]::new()
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($SkillDir.Length).TrimStart('\', '/').Replace('\', '/')
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        [void]$builder.Append($relative).Append("`n").Append($hash).Append("`n")
    }
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($builder.ToString())
    $digest = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([System.BitConverter]::ToString($digest)).Replace('-', '').ToLowerInvariant()
}

foreach ($entry in $catalog.skills) {
    if (-not $entry.id -or -not $entry.path -or -not $entry.license -or -not $entry.sha256) {
        throw 'Each skill requires id, path, license, and sha256.'
    }
    if ($seen.ContainsKey($entry.id)) {
        throw "Duplicate skill id: $($entry.id)"
    }
    $seen[$entry.id] = $true

    $skillDir = Join-Path $repoRoot $entry.path
    $skillFile = Join-Path $skillDir 'SKILL.md'
    if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf)) {
        throw "Missing SKILL.md for $($entry.id)"
    }

    $actual = Get-PackageHash $skillDir
    if ($actual -ne $entry.sha256.ToLowerInvariant()) {
        throw "Hash mismatch for $($entry.id): expected $($entry.sha256), got $actual"
    }
}

$actualIds = @($catalog.skills | ForEach-Object { $_.id } | Sort-Object)
$expectedIds = @($expected | Sort-Object)
if (($actualIds -join "`n") -ne ($expectedIds -join "`n")) {
    throw "Catalog must contain exactly: $($expectedIds -join ', ')"
}

Write-Output "Skill marketplace verification passed: $($catalog.skills.Count) skill(s)."
