*** Settings ***
Documentation     Starting point for SAP GUI tests, with RoboSAPiens: steps name the labels, buttons
...               and column titles you see on the screen, in the logon language.
...               If you are already logged on to the system in SAP Logon, the test uses that logon
...               in its own extra window. Otherwise it starts SAP Logon if needed, logs on with
...               SAP_GUI_USERNAME / SAP_GUI_PASSWORD, and logs off again at the end.
Resource          sap_system.resource
Library           Collections
Library           RoboSAPiens    x64=${SAP_GUI_X64}
Library           ../libraries/SapGui.py

*** Keywords ***
Open SAP Window
    [Documentation]    Gives the test its own SAP GUI window: RoboSAPiens keywords act on that window
    ...    until Close SAP GUI Session. Use this, not Connect To Running SAP on its own: that would
    ...    take over the window you are working in, and Close SAP or Disconnect From Server would
    ...    end your logon.
    ${window}=    Open SAP GUI Session    ${SAP_GUI_SYSTEM}    ${SAP_GUI_CLIENT}    ${SAP_LOGON_ENTRY}
    ...    ${SAP_GUI_USERNAME}    ${SAP_GUI_PASSWORD}    ${SAP_GUI_LANGUAGE}
    ${session}=    Connect To Running SAP    connection=${window}[connection]    client=${window}[client]
    ...    session_number=${window}[session_number]
    # SAP Logon can leave the connection name empty, then only the client tells systems apart
    Should Be Equal    ${session}[server]    ${SAP_GUI_SYSTEM}    Took over a window on the wrong system    values=False

Get Table Rows
    [Documentation]    Reads every row of the table on screen, top to bottom, into a list of
    ...    dictionaries keyed by the column titles given. Use exact titles, as Describe Screen shows.
    ...    Fails if the window has no table, so check the screen first when a list can come up empty.
    [Arguments]    @{columns}
    ${rows}=    Get Row Count
    @{lines}=    Create List
    FOR    ${row}    IN RANGE    1    ${rows} + 1
        ${line}=    Read Table Row    ${row}    @{columns}
        Append To List    ${lines}    ${line}
    END
    RETURN    ${lines}

Read Table Row
    [Documentation]    Reads one row. Flattened in the log: one Read Cell per cell adds up quickly.
    [Tags]    robot:flatten
    [Arguments]    ${row}    @{columns}
    ${line}=    Create Dictionary
    FOR    ${column}    IN    @{columns}
        ${value}=    Read Cell    ${row}    ${column}
        Set To Dictionary    ${line}    ${column}    ${{ $value.strip() }}
    END
    RETURN    ${line}
