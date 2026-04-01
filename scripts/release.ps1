Param(
  [Parameter(Mandatory = $false)]
  [string]$Version = "",

  [Parameter(Mandatory = $false)]
  [string]$LatestDir = "C:\Users\gingt\Desktop\Work\Mod Manager 7DTD Latest",

  [Parameter(Mandatory = $false)]
  [string]$Configuration = "Release",

  [Parameter(Mandatory = $false)]
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repoRoot "winforms\7dtd-mod-loadorder-manager\7dtd-mod-loadorder-manager.csproj"
$outDir = Join-Path $repoRoot "winforms\7dtd-mod-loadorder-manager\bin\$Configuration\net7.0-windows"

[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseApprovedVerbs', '', Justification = 'Local helper used only by this script.')]
function New-DirectoryIfMissing {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

Write-Host "RepoRoot: $repoRoot"
Write-Host "Project:  $project"
Write-Host "Output:   $outDir"
Write-Host "Latest:   $LatestDir"

if (-not $SkipBuild) {
  Write-Host "Building ($Configuration)..."
  dotnet build $project -c $Configuration
}

if (-not (Test-Path $outDir)) {
  throw "Build output folder not found: $outDir"
}

New-DirectoryIfMissing -Path $LatestDir

Write-Host "Syncing build output -> Latest (replace)..."
# Mirror build output into Latest
Robocopy $outDir $LatestDir /MIR /R:2 /W:1 /NFL /NDL /NP | Out-Null

if ([string]::IsNullOrWhiteSpace($Version)) {
  Write-Host "Done. Latest updated. (No version snapshot created; pass -Version 1.9 to snapshot.)"
  exit 0
}

$parent = Split-Path -Parent $LatestDir
$versionDir = Join-Path $parent ("Mod Manager 7DTD " + $Version)

Write-Host "Creating version snapshot: $versionDir"
if (Test-Path $versionDir) {
  throw "Version folder already exists: $versionDir"
}

Copy-Item -Path $LatestDir -Destination $versionDir -Recurse

$oldExe = Join-Path $versionDir "7dtd-mod-loadorder-manager.exe"
$newExe = Join-Path $versionDir ("Mod Manager 7DTD " + $Version + ".exe")

if (Test-Path $oldExe) {
  Rename-Item -Path $oldExe -NewName (Split-Path $newExe -Leaf)
  Write-Host "Renamed EXE -> $(Split-Path $newExe -Leaf)"
}
else {
  Write-Host "WARNING: Expected EXE not found to rename: $oldExe"
}

Write-Host "Done. Latest updated + version snapshot created." 
