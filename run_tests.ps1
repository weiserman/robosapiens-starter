<#
.SYNOPSIS
    Runs tests and keeps the results in their own dated folder under results\.

.EXAMPLE
    .\run_tests.ps1                     # everything in tests\
    .\run_tests.ps1 -Include smoke      # one tag
    .\run_tests.ps1 tests\examples      # one folder or file
#>
param(
    [string]$Path = 'tests',
    [string]$Include
)
Set-Location $PSScriptRoot
$outdir = "results\$(Get-Date -Format 'yyyy-MM-dd_HHmmss')"
$tags = @()
if ($Include) { $tags = @('--include', $Include) }

$env:PYTHONIOENCODING = 'utf-8'
& '.venv\Scripts\robot.exe' --outputdir $outdir @tags $Path
$result = $LASTEXITCODE

Write-Host ''
Write-Host "Report: $PSScriptRoot\$outdir\report.html"
exit $result
