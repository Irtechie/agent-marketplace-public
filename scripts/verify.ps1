$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$catalogPath = Join-Path $repoRoot 'catalog/skills.json'
$catalog = Get-Content -Raw -LiteralPath $catalogPath | ConvertFrom-Json

if ($catalog.schemaVersion -ne 1) {
    throw "Unsupported catalog schemaVersion: $($catalog.schemaVersion)"
}

$seen = @{}
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

    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $skillFile).Hash.ToLowerInvariant()
    if ($actual -ne $entry.sha256.ToLowerInvariant()) {
        throw "Hash mismatch for $($entry.id): expected $($entry.sha256), got $actual"
    }
}

Write-Output "Public marketplace verification passed: $($catalog.skills.Count) skill(s)."
