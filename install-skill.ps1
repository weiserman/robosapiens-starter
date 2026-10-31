<#
.SYNOPSIS
    Installs the Claude Code skill for all your projects, in ~\.claude\skills\robosapiens.
    Run it again to update. Projects made from this template already have the skill.
#>
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$target = Join-Path $HOME '.claude\skills\robosapiens'
New-Item -ItemType Directory -Force $target | Out-Null
Copy-Item '.claude\skills\robosapiens\*' $target -Recurse -Force
Write-Host "Skill installed in $target"
