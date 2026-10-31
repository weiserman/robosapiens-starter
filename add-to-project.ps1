<#
.SYNOPSIS
    Adds this starter to a project that already exists. Existing files are left alone.

.EXAMPLE
    .\add-to-project.ps1 -Path C:\Projects\my-sap-project
#>
param(
    [Parameter(Mandatory)]
    [string]$Path
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path $Path -PathType Container)) { throw "Folder not found: $Path" }

$files = @(
    'setup.ps1', 'run_tests.ps1', 'inspect.ps1', '.mcp.json',
    'libraries\SapGui.py',
    'resources\sap_gui.resource', 'resources\sap_system.resource.example', 'resources\sap_mcp_transactions.txt',
    'tests\00_connection.robot', 'tests\examples\01_read_a_table.robot',
    'tools\inspect_screen.robot', 'tools\sap_mcp_server.py', 'tools\test_sap_mcp_server.py'
)
$skill = Get-ChildItem '.claude\skills\robosapiens' -Recurse -File | ForEach-Object { Resolve-Path $_.FullName -Relative }
foreach ($file in @($files) + @($skill)) {
    $target = Join-Path $Path $file
    if (Test-Path $target) {
        Write-Host "   Skipped, already there: $file"
        if ($file -eq '.mcp.json') { Write-Host '   Copy the sap-gui entry from the starter''s .mcp.json into yours by hand' }
        continue
    }
    New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
    Copy-Item $file $target
    Write-Host "   Added: $file"
}

function Add-MissingLines($file, $lines) {
    $target = Join-Path $Path $file
    $existing = @()
    if (Test-Path $target) { $existing = @(Get-Content $target) }
    $missing = @($lines | Where-Object { $_ -and ($existing -notcontains $_) })
    if ($missing) {
        Add-Content $target $missing
        Write-Host "   Updated: $file"
    }
}

Add-MissingLines 'requirements.txt' (Get-Content 'requirements.txt')
Add-MissingLines '.gitignore' @('resources/sap_system.resource', '.venv/', '__pycache__/', 'results/')

Write-Host ''
Write-Host "Done. Next, in that folder: .\setup.ps1 -System SID -Client 100 -LogonEntry `"My SAP Logon Entry`""
