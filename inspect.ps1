<#
.SYNOPSIS
    Prints the labels, fields, buttons and table columns on a transaction's first screen. Read-only.

.EXAMPLE
    .\inspect.ps1 ME2N
#>
param(
    [Parameter(Mandatory)]
    [string]$Transaction
)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
& '.venv\Scripts\robot.exe' --outputdir results\inspect --variable "TRANSACTION:$Transaction" tools\inspect_screen.robot
exit $LASTEXITCODE
