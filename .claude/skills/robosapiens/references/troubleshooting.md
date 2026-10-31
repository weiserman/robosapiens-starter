# Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `No SAP GUI logon to SID client 100` | No logon on that system | Log on in SAP Logon, or check `resources/sap_system.resource` |
| `Took over a window on the wrong system` | Another system with the same client came first, and the SAP Logon connection name is blank | Close that logon, or log on to the right system first |
| `SAP Logon started but SAP GUI scripting is not available` | Scripting is off in the client | SAP GUI Options > Accessibility & Scripting > Scripting |
| `Scripting is not activated on the server side` | Profile parameter is off | Ask Basis to set `sapgui/user_scripting = TRUE` |
| `Could not connect to a running SAP instance` | Bitness mismatch | `${SAP_GUI_X64}` in `resources/sap_system.resource` must match SAP GUI: True for 64-bit |
| `SAP GUI did not open a new window` | SAP allows 6 windows per logon by default | Close one |
| `The text field with the locator ... could not be found` | Label differs from the screen, often in case or industry wording | `.\inspect.ps1 <tcode>`, and copy the label exactly |
| `NotFound: The cell with the locator '1, Column'` | Column title differs, is hidden by the layout, or the row is above the visible area | `Describe Screen` shows the titles. Read rows top to bottom |
| `IndexError: Replacement index 0 out of range` from `Get Row Count` | A RoboSAPiens message bug: the window has no table | Check `Get Window Title` and `Read Statusbar` |
| Window title is `Print Screen List` | A partial `Push Button` match hit Execute and Print | Use `Press Key Combination    F8`, and cancel the popup. Nothing prints until it is confirmed |
| A step works by hand but the list is empty or short | A saved variant or remembered value is filtering the list | Clear the selection field in the test |
| `Parsing '...\tests' failed` | `robot` was run from another folder | Use `.\run_tests.ps1`, which changes to the project folder itself |
| `running scripts is disabled on this system` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or ask IT |
| A step acts on the previous transaction's screen | `Execute Transaction` with a bare code from inside a transaction does nothing, without an error | Use `/nME2N` |
| `Refused: ... is not in resources/sap_mcp_transactions.txt` | The MCP server is read-only and the transaction is not listed | If it only displays data, the user adds it to the file. No restart needed |
| `Refused: ... this server is read-only` | The step would save or post | The user decides: `${SAP_MCP_ALLOW_CHANGES}` in `resources/sap_system.resource`, then a restart of the server |
| `SAP is still busy after 120 seconds` | A selection without restrictions, usually | Wait for the list to finish, then restrict the selection next time |
| The `sap-gui` server does not connect | `.venv` or `resources/sap_system.resource` is missing | Run `.\setup.ps1`, and approve the server when Claude Code asks |
| An extra SAP window stays open after a session | The server was stopped before it could close it | Close that window by hand |
