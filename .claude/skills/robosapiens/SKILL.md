---
name: robosapiens
description: Write and run SAP GUI for Windows automation with Robot Framework and RoboSAPiens, using the robosapiens-starter template. Use whenever the user wants to automate, script, test or read data from SAP GUI, drive a transaction such as ME2N, ME23N, MIGO, SE16 or VA03, replace manual SAP GUI checks, set up RoboSAPiens in a new or existing project, or fix a RoboSAPiens test, even if they only say "automate this SAP screen" and never name the library. Not for Fiori or browser apps, OData or RFC calls, or writing ABAP code.
---

# RoboSAPiens

Robot Framework tests that drive SAP GUI for Windows by the labels, buttons and column titles a person sees, so that a tester can read them. The starter adds what RoboSAPiens lacks: a window of the test's own and a way to look at a screen.

## 1. Get the project ready

Look for `resources/sap_gui.resource` in the project.

- **Found:** go to step 2. If `.venv` or `resources/sap_system.resource` is missing, run `.\setup.ps1` with `-System`, `-Client` and `-LogonEntry`.
- **New project:** create it from the template, then set it up:
  ```powershell
  gh repo create my-sap-project --template weiserman/robosapiens-starter --private --clone
  cd my-sap-project
  .\setup.ps1 -System SID -Client 100 -LogonEntry "Name in SAP Logon"
  ```
- **Existing project:** clone the starter next to it and run `.\add-to-project.ps1 -Path <project>`, then `.\setup.ps1` in the project.

Get the system ID, client and SAP Logon entry from the user. Ask the user to log on in SAP Logon themselves, because tests reuse that logon. Do not type or store their SAP password. Then run `.\run_tests.ps1 -Include smoke` to prove the setup before writing anything.

## 2. Find out what is on the screen

Do not write locators from memory: labels differ per system, language and industry. Retail systems say Site, Article and Supplier where others say Plant, Material and Vendor, and label case matters (`Purchasing document`).

```powershell
.\inspect.ps1 ME2N
```

This prints the transaction's first screen. For later screens, use the `sap-gui` MCP server if its tools are available: `open_window`, `start_transaction`, then `describe_screen` after each step. It works in its own window, and `recorded_test` turns the steps into a test. Run that test before trusting it: it reads whole tables, where you may have read a few rows, so a step that follows a read can behave differently. Without the server, add `Describe Screen` to a test after the step that reaches the screen and log the result, or use `Save Screenshot    LOG`.

The server is read-only unless the user sets `${SAP_MCP_ALLOW_CHANGES}` to True in `resources/sap_system.resource`. If it refuses a step, tell the user what was refused and why. Never change that setting or `resources/sap_mcp_transactions.txt` yourself, and restrict a selection before executing it: an empty ME2N ties up the window for minutes.

If this project's SAP system is connected through an ADT or MCP tool, reading the transaction's report and selection texts helps too, but the live screen wins.

## 3. Write the steps

Put each transaction's steps in a keyword in its own file, such as `resources/me2n.resource`, importing `sap_gui.resource`. Keep tests short and in business language. A test always has this shape, because the `FINALLY` closes the window even when a step fails:

```robot
*** Test Cases ***
Open Quantity Of A Purchase Order
    Open SAP Window
    TRY
        Execute Transaction    ME2N
        Fill Text Field    Purchasing document    ${po}
        Press Key Combination    F8
        ${lines}=    Get Table Rows    Item    Still to be delivered (qty)
    FINALLY
        Close SAP GUI Session
    END
    Should Not Be Empty    ${lines}
```

Read `references/keywords.md` for the keyword list and locator forms.

## 4. Rules that prevent real damage

Each of these comes from a failure on a real system.

- **Use `Open SAP Window`, never `Connect To Running SAP` on its own.** That keyword takes over the first session, which is the window the user is working in, and a transaction start there can lose their unsaved work.
- **Never use `Close SAP` or `Disconnect From Server` on a logon the test did not make.** `Close SAP` kills `saplogon.exe` whatever started it, despite what its documentation says, and `Disconnect From Server` closes every window on the connection. `Close SAP GUI Session` closes only the test's window.
- **Start a second transaction with `/n`.** From inside a transaction, `Execute Transaction    ME2N` does nothing and reports success, so the next steps act on the wrong screen. Use `Execute Transaction    /nME2N`.
- **Press keys rather than `Push Button` for commands.** `Push Button` matches part of a name by default, so `Push Button    Execute` hit "Execute and Print" and opened a print dialog. Use `Press Key Combination    F8`, or `exact=True`.
- **Default to read-only, and tag it.** Display transactions are safe to run freely. Before running anything that saves or posts, tell the user exactly what it changes and on which system, get their go-ahead, and tag the test (for example `posts-goods-movement`) so that it can be excluded.
- **Clear what a saved variant may bring along.** Selection screens remember values: a default site silently filtered one list. Clear each restricting field with `Fill Text Field    <label>    ${EMPTY}`, and range ends with `Document Date >> to`.

## 5. Tables

- `Get Table Rows` reads rows by column title into dictionaries. It makes one call per cell, so expect about 2.5 times the time of direct scripting: 235 rows of 7 columns took 28 seconds.
- Columns are found by title or tooltip only. Technical names such as `MGLIEF` do not work, and a column hidden by the user's ALV layout cannot be read.
- Read rows top to bottom. `Read Cell` scrolls down by itself but returns NotFound for a row above the visible area.
- Total and subtotal rows come back with an empty item: filter them out.
- SAP shows numbers as text: use `SAP Number`, and pass `decimal_separator=,` to the `SapGui` library import for 1.234,56 notation.
- `Get Row Count` fails with `IndexError: Replacement index 0 out of range` when the window has no table. The real cause is on screen, usually an empty result or a popup, so check the window title and `Read Statusbar` first.
- A classic ABAP list needs Accessibility Mode switched on in the SAP GUI options before table keywords work on it. Prefer the ALV layout where a transaction offers one.

## 6. When a test fails

Open `log.html` from the run's results folder. See `references/troubleshooting.md` for the failures seen so far. An unexpected popup is the most common cause: `Get Window Title` shows it.

## 7. Upgrades

RoboSAPiens is pinned in `requirements.txt` because it has no release notes and an upgrade has broken `Read Cell` before. Upgrade on purpose and rerun the tests.
