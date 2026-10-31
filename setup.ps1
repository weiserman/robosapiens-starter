<#
.SYNOPSIS
    Sets up this folder for RoboSAPiens: virtual environment, packages and your SAP system settings.

.EXAMPLE
    .\setup.ps1 -System S4D -Client 100 -LogonEntry "S/4HANA Development"
#>
param(
    [string]$System = 'SID',
    [string]$Client = '100',
    # The entry's name exactly as SAP Logon shows it
    [string]$LogonEntry = 'My SAP Logon Entry',
    [string]$Language = 'EN'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Find-Python {
    foreach ($candidate in @(@('py', '-3'), @('python'))) {
        if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
        $launcher = $candidate[0]
        $launcherArgs = @($candidate | Select-Object -Skip 1)
        try {
            $ok = & $launcher @launcherArgs -c 'import sys; print(sys.version_info >= (3, 10))'
        } catch {
            continue
        }
        if ($ok -eq 'True') { return , $candidate }
    }
    throw 'Python 3.10 or later not found: install it from https://www.python.org/downloads/ and run this again'
}

Write-Host '1. Python packages'
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    $python = Find-Python
    $launcher = $python[0]
    $launcherArgs = @($python | Select-Object -Skip 1)
    & $launcher @launcherArgs -m venv .venv
    if ($LASTEXITCODE) { throw 'Could not create .venv' }
}
& '.venv\Scripts\python.exe' -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE) { throw 'pip install failed' }

Write-Host '2. SAP GUI'
$is64 = Test-Path "$env:ProgramFiles\SAP\FrontEnd\SAPGUI\saplogon.exe"
$is32 = (${env:ProgramFiles(x86)}) -and (Test-Path "${env:ProgramFiles(x86)}\SAP\FrontEnd\SAPGUI\saplogon.exe")
if ($is64) { Write-Host '   SAP GUI 64-bit found' }
elseif ($is32) { Write-Host '   SAP GUI 32-bit found' }
else { Write-Warning 'SAP GUI for Windows not found: install it before running tests' }

$securityKey = 'HKCU:\Software\SAP\SAPGUI Front\SAP Frontend Server\Security'
$security = Get-ItemProperty $securityKey -ErrorAction SilentlyContinue
if ($security -and ($security.PSObject.Properties.Name -contains 'UserScripting') -and ($security.UserScripting -eq 0)) {
    Write-Warning 'SAP GUI scripting is off: turn it on in SAP GUI Options > Accessibility & Scripting > Scripting'
}

Write-Host '3. System settings'
$settings = 'resources\sap_system.resource'
if (Test-Path $settings) {
    Write-Host "   Keeping your existing $settings"
} else {
    (Get-Content "$settings.example" -Raw).
        Replace('__SYSTEM__', $System).
        Replace('__CLIENT__', $Client).
        Replace('__LOGON_ENTRY__', $LogonEntry).
        Replace('__LANGUAGE__', $Language).
        Replace('__X64__', $(if ($is64) { 'True' } else { 'False' })) |
        Set-Content $settings -NoNewline
    Write-Host "   Wrote $settings"
    if ($System -eq 'SID') { Write-Warning "Put your system in $settings, or run setup.ps1 again with -System, -Client and -LogonEntry after deleting it" }
}

Write-Host '4. Check'
$env:PYTHONIOENCODING = 'utf-8'
& '.venv\Scripts\robot.exe' --dryrun --output NONE --log NONE --report NONE --console quiet tests
if ($LASTEXITCODE) { throw 'The test files do not load: see the errors above' }

Write-Host ''
Write-Host 'Setup finished. Next: log on to the system in SAP Logon, then run .\run_tests.ps1 -Include smoke'
Write-Host 'Claude Code will offer the read-only sap-gui MCP server when you open this folder.'
