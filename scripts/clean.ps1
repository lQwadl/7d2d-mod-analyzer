Param(
    [Parameter(Mandatory = $false)]
    [switch]$IncludeVenv
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$paths = @(
    (Join-Path $repoRoot "__pycache__"),
    (Join-Path $repoRoot ".pytest_cache"),
    (Join-Path $repoRoot ".ruff_cache"),
    (Join-Path $repoRoot "build"),
    (Join-Path $repoRoot "dist"),
    (Join-Path $repoRoot ".vs")
)

if ($IncludeVenv) {
    $paths += (Join-Path $repoRoot ".venv")
}

foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "Removing: $p"
        Remove-Item -LiteralPath $p -Recurse -Force
    }
}

Write-Host "Clean complete."
