# Copyright 2026 Ari Sulistiono
# SPDX-License-Identifier: GPL-3.0-or-later
<#
.SYNOPSIS
  Verifies that every Git-tracked ArIED path is free from prohibited binaries,
  captures, confidential evidence, external IEC 61850 stack material, and
  proprietary-tool assets.

.DESCRIPTION
  The gate scans Git-tracked files rather than ignoring directories by name.
  A committed capture, manual, log, or product asset therefore cannot bypass the
  check by being placed below folders such as evidence, captures, logs, or a
  product-named directory. Untracked local build output is naturally excluded.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$ForbiddenFilePatterns = @(
    "*.dll", "*.exe", "*.pdb", "*.deps.json", "*.runtimeconfig.json",
    "*.nupkg", "*.snupkg", "*.pcap", "*.pcapng", "*.etl", "*.binlog",
    "*.log", "*.tmp", "*.cache", "*.suo", "*.user", "*.rsuser",
    "*.pdf", "*.chm", "*.hlp"
)

# Match the complete repo-relative path so a product-named directory cannot hide
# an otherwise generic file such as assets/vendor-name/logo.png.
$ForbiddenThirdPartyPathPatterns = @(
    "*libiec61850*", "*iedscout*", "*ied scout*", "*svscout*", "*sv scout*",
    "*stationscout*", "*station scout*", "*omicron*", "*mz-automation*"
)

$ForbiddenTextPatterns = @(
    "libiec61850", "MZ Automation", "IEDScout", "IED Scout",
    "StationScout", "Station Scout", "SVScout", "SV Scout", "OMICRON_CMC",
    "C:\Users\", "C:\Program Files\dotnet\sdk", "blocked in the current sandbox", "_wpftmp"
)

$TextExtensions = @(
    ".md", ".cs", ".xml", ".xaml", ".ps1", ".cmd", ".yml", ".yaml",
    ".html", ".css", ".js", ".json", ".props", ".targets", ".sln", ".slnx", ".txt"
)

$AllowedLegalReferenceFiles = @(
    "THIRD_PARTY_NOTICES.md",
    "docs/CLEAN_ROOM_AND_INTEROPERABILITY_POLICY.md",
    "docs/THIRD_PARTY_CLEAN_ROOM_AUDIT_2026-07-14.md"
)

$Problems = New-Object System.Collections.Generic.List[string]

function Normalize-RelativePath {
    param([Parameter(Mandatory=$true)][string]$Path)
    return $Path.Replace('\', '/').TrimStart('/')
}

function Test-IsAllowedLegalReference {
    param([Parameter(Mandatory=$true)][string]$RelativePath)
    return $AllowedLegalReferenceFiles -contains (Normalize-RelativePath $RelativePath)
}

function Get-TrackedRelativePaths {
    $paths = @(& git -C $RepoRoot ls-files)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to enumerate Git-tracked files for clean-room verification."
    }

    return @(
        $paths |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { Normalize-RelativePath $_ }
    )
}

foreach ($relative in (Get-TrackedRelativePaths)) {
    $platformRelative = $relative.Replace([char]'/', [IO.Path]::DirectorySeparatorChar)
    $fullPath = Join-Path $RepoRoot $platformRelative

    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        $Problems.Add("Tracked path is missing from the worktree: $relative")
        continue
    }

    foreach ($pattern in $ForbiddenFilePatterns) {
        if ($relative -like $pattern) {
            $Problems.Add("Forbidden tracked file: $relative")
            break
        }
    }

    if (-not (Test-IsAllowedLegalReference $relative)) {
        foreach ($pattern in $ForbiddenThirdPartyPathPatterns) {
            if ($relative -like $pattern) {
                $Problems.Add("Forbidden third-party-named path: $relative")
                break
            }
        }
    }

    if ($relative -eq "scripts/verify-source-clean.ps1") { continue }
    if (Test-IsAllowedLegalReference $relative) { continue }
    if ($TextExtensions -notcontains [IO.Path]::GetExtension($relative).ToLowerInvariant()) { continue }

    $content = Get-Content -LiteralPath $fullPath -Raw -ErrorAction SilentlyContinue
    foreach ($pattern in $ForbiddenTextPatterns) {
        if ($content -match [regex]::Escape($pattern)) {
            $Problems.Add("Forbidden text '$pattern': $relative")
        }
    }
}

if ($Problems.Count -gt 0) {
    foreach ($problem in ($Problems | Sort-Object -Unique)) {
        Write-Host "ERROR: $problem" -ForegroundColor Red
    }
    throw "ArIED source tree failed clean-room validation with $($Problems.Count) problem(s)."
}

Write-Host "All Git-tracked ArIED content passed clean-room and third-party contamination checks." -ForegroundColor Green
