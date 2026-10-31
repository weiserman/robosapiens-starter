*** Settings ***
Documentation     Worked example: run a transaction and read its list. Read-only.
...               SM04 lists the users logged on to this system, so it has at least you in it.
...               Column titles can differ per release: .\inspect.ps1 SM04 shows yours.
...               Copy this file to start a test of your own.
Resource          ../../resources/sap_gui.resource
Test Tags         read-only    example

*** Test Cases ***
SM04 Lists The Logged On User
    Open SAP Window
    TRY
        Execute Transaction    SM04
        ${users}=    Get Table Rows    Client    User ID
    FINALLY
        Close SAP GUI Session
    END
    Should Not Be Empty    ${users}
    Log To Console    \n${{ len($users) }} row(s), first user: ${users}[0][User ID]
