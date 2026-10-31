*** Settings ***
Documentation     Run this first: proves Robot Framework, RoboSAPiens and SAP GUI work together.
...               Read-only. Log on to the system in SAP Logon first, or set SAP_GUI_USERNAME and
...               SAP_GUI_PASSWORD as environment variables.
Resource          ../resources/sap_gui.resource
Test Tags         read-only    smoke

*** Test Cases ***
Test Gets Its Own SAP Window
    Open SAP Window
    TRY
        ${title}=    Get Window Title
        Should Not Be Empty    ${title}
        Log To Console    \nConnected: the test's window shows "${title}"
        Save Screenshot    LOG
    FINALLY
        Close SAP GUI Session
    END
