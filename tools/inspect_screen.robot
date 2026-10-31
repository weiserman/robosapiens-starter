*** Settings ***
Documentation     Prints the first screen of a transaction: use .\inspect.ps1 ME2N. Read-only.
Resource          ../resources/sap_gui.resource

*** Variables ***
${TRANSACTION}    SESSION_MANAGER

*** Test Cases ***
Describe First Screen
    Open SAP Window
    TRY
        Execute Transaction    ${TRANSACTION}
        ${screen}=    Describe Screen
        Log To Console    \n${screen}
    FINALLY
        Close SAP GUI Session
    END
