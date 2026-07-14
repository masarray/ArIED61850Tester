# Copyright 2026 Ari Sulistiono
# SPDX-License-Identifier: GPL-3.0-or-later
<#
.SYNOPSIS
  Verifies that the ArIED application tree contains no prohibited build payload,
  confidential evidence, external IEC 61850 stack material, or proprietary-tool assets.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$IgnoredDirectoryNames = @(
    ".git", ".vs", "bin", "obj", "out", "artifacts", ".artifacts", "dist",
    "evidence", "captures", "pcaps", "reports", "logs", ".idea", ".dotnet_home",
    "TestResults", "coverage", "publish", "release"
)

$ForbiddenFilePatterns = @(
    "*.dll", "*.exe", "*.pdb", "*.deps.json", "*.runtimeconfig.json",
    "*.nupkg", "*.snupkg", "*.pcap", "*.pcapng", "*.etl", "*.binlog",
    "*.log", "*.tmp", "*.cache", "*.suo", "*.user", "*.rsuser",
    "*.pdf", "*.chm", "*.hlp"
)

$ForbiddenThirdPartyFilePatterns = @(
    "*libiec61850*", "*iedscout*", "*ied scout*", "*svscout*", "*sv scout*",
    "*stationscout*", "*station scout*", "*omicron*", "*mz-automation*"
)

$ForbiddenTextPatterns = @(
    "libiec61850", "MZ Automation", "IEDScout", "IED Scout",
    "StationScout", "Station Scout", "SVScout", "SV Scout", "OMICRON_CMC",
    "C:\Users\", "C:\Program Files\dotnet\sdk", "blocked in the current sandbox", "_wpftmp"
)

$AllowedLegalReferenceFiles = @(
    "THIRD_PARTY_NOTICES.md",
    "docs/CLEAN_ROOM_AND_INTEROPERABILITY_POLICY.md",
    "docs/THIRD_PARTY_CLEAN_ROOM_AUDIT_2026-07-14.md"
)

$Problems = New-Object System.Collections.Generic.List[string]

function Get-RepoRelativePath {
    param([Parameter(Mandatory=$true)][string]$Path)

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    return $fullPath.Substring($RepoRoot.Length).TrimStart(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar).Replace('\', '/')
}

function Test-InRepoWorktree {
    param([Parameter(Mandatory=$true)][string]$Path)

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    if (-not $fullPath.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }

    $relative = Get-RepoRelativePath -Path $fullPath
    return -not ($relative -eq ".git" -or $relative.StartsWith(".git/", [System.StringComparison]::OrdinalIgnoreCase))
}

function Test-IsIgnoredGeneratedPath {
    param([Parameter(Mandatory=$true)][string]$Path)

    $relative = Get-RepoRelativePath -Path $Path
    if ([string]::IsNullOrWhiteSpace($relative)) { return $false }

    foreach ($part in ($relative -split '[\\/]+')) {
        if ($IgnoredDirectoryNames -contains $part) { return $true }
    }
    return $false
}

function Test-IsAllowedLegalReference {
    param([Parameter(Mandatory=$true)][string]$Path)

    return $AllowedLegalReferenceFiles -contains (Get-RepoRelativePath -Path $Path)
}

foreach ($pattern in $ForbiddenFilePatterns) {
    Get-ChildItem -Path $RepoRoot -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue |
        Where-Object { (Test-InRepoWorktree $_.FullName) -and -not (Test-IsIgnoredGeneratedPath $_.FullName) } |
        ForEach-Object { $Problems.Add("Forbidden file: $($_.FullName)") }
}

Get-ChildItem -Path $RepoRoot -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { (Test-InRepoWorktree $_.FullName) -and -not (Test-IsIgnoredGeneratedPath $_.FullName) } |
    ForEach-Object {
        $file = $_
        foreach ($pattern in $ForbiddenThirdPartyFilePatterns) {
            if ($file.Name -like $pattern -and -not (Test-IsAllowedLegalReference $file.FullName)) {
                $Problems.Add("Forbidden third-party-named file: $($file.FullName)")
                break
            }
        }
    }

$textFiles = Get-ChildItem -Path $RepoRoot -Recurse -Force -File -Include *.md,*.cs,*.xml,*.xaml,*.ps1,*.cmd,*.yml,*.yaml,*.html,*.css,*.js,*.json,*.props,*.sln,*.slnx,*.txt -ErrorAction SilentlyContinue |
    Where-Object { (Test-InRepoWorktree $_.FullName) -and -not (Test-IsIgnoredGeneratedPath $_.FullName) }

foreach ($file in $textFiles) {
    if ($file.FullName -like "*scripts\verify-source-clean.ps1") { continue }
    if (Test-IsAllowedLegalReference $file.FullName) { continue }

    $content = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($pattern in $ForbiddenTextPatterns) {
        if ($content -match [regex]::Escape($pattern)) {
            $Problems.Add("Forbidden text '$pattern': $($file.FullName)")
        }
    }
}

if ($Problems.Count -gt 0) {
    foreach ($problem in $Problems) {
        Write-Host "ERROR: $problem" -ForegroundColor Red
    }
    throw "ArIED source tree failed clean-room validation with $($Problems.Count) problem(s)."
}

Write-Host "ArIED source tree passed clean-room and third-party contamination checks." -ForegroundColor Green
