# RoboSAPiens starter

A ready-to-use template for automating **SAP GUI for Windows** with [Robot Framework](https://robotframework.org/) and [RoboSAPiens](https://imbus.github.io/robotframework-robosapiens/). Tests name what a person sees on the screen, so people who don't code can read them:

```robot
Execute Transaction      ME2N
Fill Text Field          Purchasing document    ${po_number}
Press Key Combination    F8
${lines}=                Get Table Rows    Item    Still to be delivered (qty)
```

RoboSAPiens provides those keywords. This starter adds what you need around them to use it safely on a system you are also working on:

- **A window of the test's own.** Tests reuse your SAP logon in an extra window, and close only that window. RoboSAPiens alone would take over the window you are working in.
- **`.\inspect.ps1 ME2N`** prints the labels, fields, buttons and columns of a screen, so you don't have to guess locators.
- **`Get Table Rows`** reads a whole list into dictionaries.
- **One-command setup**, dated result folders and working examples.
- **A Claude Code skill** that lets Claude write tests the same way, including the mistakes to avoid.

## What you need

- Windows with **SAP GUI for Windows** (see [Tested on](#tested-on))
- **Python 3.10 or later**
- **SAP GUI scripting switched on in two places:**
  - in the client: SAP GUI Options > Accessibility & Scripting > Scripting > *Enable scripting*
  - on the server: profile parameter `sapgui/user_scripting = TRUE`, which your Basis team sets
- [GitHub CLI](https://cli.github.com/), if you want to create projects with the command below

> Only automate systems you are authorised to use. Your company may restrict SAP GUI scripting: check before you switch it on.

## Start a new project

Run these in PowerShell. Use your own system ID, client and SAP Logon entry name.

**1. Create the project from this template:**

```powershell
gh repo create my-sap-project --template weiserman/robosapiens-starter --private --clone
cd my-sap-project
```

Or press **Use this template** on GitHub, then clone your new repository.

**2. Set it up:**

```powershell
.\setup.ps1 -System S4D -Client 100 -LogonEntry "S/4HANA Development"
```

This creates `.venv`, installs the pinned packages, detects whether your SAP GUI is 64-bit, and writes your settings to `resources\sap_system.resource`, which git ignores.

**3. Log on** to that system in SAP Logon, as you normally do.

**4. Prove it works:**

```powershell
.\run_tests.ps1 -Include smoke
```

You will see an extra SAP window open and close, while your own window stays as it was. The result is in `results\<date>\report.html`.

## Add it to an existing project

```powershell
git clone https://github.com/weiserman/robosapiens-starter.git
.\robosapiens-starter\add-to-project.ps1 -Path C:\Projects\my-sap-project
cd C:\Projects\my-sap-project
.\setup.ps1 -System S4D -Client 100 -LogonEntry "S/4HANA Development"
```

Existing files are left alone. `requirements.txt` and `.gitignore` get the lines they are missing.

## Write your first test

**1. See what is on the screen:**

```powershell
.\inspect.ps1 ME2N
```

```text
Window: Purchasing Documents per Document Number
Button: Execute   (F8)
Label: Purchasing document
Field: EN_EBELN-LOW = ''
Label: Scope of List
Field: LISTU = 'ALV'
```

Use labels exactly as shown. They differ per system, language and industry: a retail system says Site and Article where others say Plant and Material.

**2. Add a test** in `tests\`, for example `tests\01_open_quantity.robot`:

```robot
*** Settings ***
Documentation     What is still to be delivered on a purchase order. Read-only.
Resource          ../resources/sap_gui.resource
Test Tags         read-only

*** Variables ***
${PO_NUMBER}      4500000001

*** Test Cases ***
Purchase Order Has Open Lines
    Open SAP Window
    TRY
        Execute Transaction    ME2N
        Fill Text Field    Purchasing document    ${PO_NUMBER}
        Fill Text Field    Scope of List    ALV
        Press Key Combination    F8
        ${screen}=    Describe Screen
        Log    ${screen}
        ${lines}=    Get Table Rows    Item    Short Text    Still to be delivered (qty)
    FINALLY
        Close SAP GUI Session
    END
    Should Not Be Empty    ${lines}
```

`Describe Screen` writes the list's real column titles to the log. Remove it once the test works. The `TRY`/`FINALLY` closes the window even if a step fails.

**3. Run it:**

```powershell
.\run_tests.ps1 tests\01_open_quantity.robot
```

As you add more, move each transaction's steps into a keyword in its own file, such as `resources\me2n.resource`, so tests stay short and a changed screen means changing one file.

## Rules worth knowing

These come from real failures. The [skill](.claude/skills/robosapiens/SKILL.md) has the full list.

| Do | Don't | Why |
|---|---|---|
| Start with `Open SAP Window` | Call `Connect To Running SAP` directly | It takes over your own window |
| End with `Close SAP GUI Session` | Use `Close SAP` or `Disconnect From Server` | `Close SAP` kills SAP Logon, and `Disconnect From Server` closes every window on your logon |
| Use `Press Key Combination    F8` | Use `Push Button    Execute` | It matches part of a name, and hit **Execute and Print** |
| Clear selection fields with `${EMPTY}` | Trust a selection screen's defaults | A remembered value can filter your results without any warning |
| Read tables top to bottom | Go back to an earlier row | `Read Cell` only scrolls down |
| Keep tests read-only, and tag any that post | Run posting tests by default | Tags let you exclude them: `robot --exclude posts-*` |

`Get Table Rows` makes one call per cell: 235 rows of 7 columns took 28 seconds, against 11 with direct scripting. That is fine for hundreds of rows, not for tens of thousands. Column names must be titles, not technical names.

## Use it with Claude Code

Projects made from this template already contain the skill in `.claude/skills/robosapiens`, so you can ask Claude directly:

> Add a test that checks PO 4500000001 in ME23N shows delivery date tomorrow

Claude inspects the screen, writes the keywords and runs them. To have the skill in every project, including brand-new ones, install it once for your user:

```powershell
git clone https://github.com/weiserman/robosapiens-starter.git
.\robosapiens-starter\install-skill.ps1
```

Then you can start a project by saying "set up RoboSAPiens for this project" and Claude will take it from there. The skill tells Claude to ask you to log on yourself rather than handle your SAP password.

## Running without a logged-on user

For unattended runs, set `SAP_GUI_USERNAME` and `SAP_GUI_PASSWORD` as environment variables, for example from your CI system's secret store. The test starts SAP Logon if needed, logs on through `${SAP_LOGON_ENTRY}`, and logs off at the end. Don't put passwords in files.

Settings can be changed for one run: `.venv\Scripts\robot.exe --variable SAP_GUI_CLIENT:200 tests`.

## What's in the repo

| Path | What it is | Change it? |
|---|---|---|
| `resources\sap_system.resource` | Your system, client and logon entry (created by setup, ignored by git) | Per system |
| `resources\sap_gui.resource` | `Open SAP Window`, `Get Table Rows` | Add shared keywords |
| `libraries\SapGui.py` | Python for the window, logon, `Describe Screen` and `SAP Number` | Rarely |
| `tests\` | Your tests; `00_connection.robot` is the smoke test | Yes |
| `tests\examples\` | A worked example to copy | Copy it |
| `tools\inspect_screen.robot` | Used by `inspect.ps1` | No |
| `.claude\skills\robosapiens\` | The Claude Code skill | If your conventions differ |
| `run_tests.ps1`, `inspect.ps1`, `setup.ps1` | Run, look, set up | Rarely |
| `add-to-project.ps1`, `install-skill.ps1` | Add to an existing project, install the skill | No |

## Troubleshooting

See [the troubleshooting table](.claude/skills/robosapiens/references/troubleshooting.md). The three most common:

- **`No SAP GUI logon to SID client 100`**: log on in SAP Logon, and check `resources\sap_system.resource`.
- **`text field ... could not be found`**: run `.\inspect.ps1 <transaction>` and copy the label exactly, including its capitals.
- **`running scripts is disabled on this system`**: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or ask IT.

## Upgrading RoboSAPiens

The version is pinned in `requirements.txt`. RoboSAPiens has no release notes, so change the version on purpose, run `.\setup.ps1`, and run your tests.

## Tested on

SAP GUI 8.00 64-bit, S/4HANA, Python 3.13, Robot Framework 7.5, RoboSAPiens 2.36.2, logon language EN. Other versions should work but have not been tried: 32-bit SAP GUI in particular. Issues and pull requests are welcome.

## License and credits

MIT, see [LICENSE](LICENSE). [RoboSAPiens](https://github.com/imbus/robotframework-robosapiens) is by imbus and is licensed under Apache-2.0. This is an independent project, not affiliated with SAP or imbus. SAP and SAP GUI are trademarks of SAP SE.
