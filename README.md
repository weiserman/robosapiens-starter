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
- **[Instructions for the recorder](#record-steps-by-hand)**, so you can click through a flow and turn it into a safe test.
- **One-command setup**, dated result folders and working examples.
- **A Claude Code skill** that lets Claude write tests the same way, including the mistakes to avoid.
- **A read-only [MCP server](#mcp-server-let-claude-work-through-sap-live)** that lets Claude work through SAP screens live, then turn the steps into a test.

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

**5. If you use Claude Code,** open it in this folder and approve the `sap-gui` server. See [the MCP server](#mcp-server-let-claude-work-through-sap-live).

## Add it to an existing project

```powershell
git clone https://github.com/weiserman/robosapiens-starter.git
.\robosapiens-starter\add-to-project.ps1 -Path C:\Projects\my-sap-project
cd C:\Projects\my-sap-project
.\setup.ps1 -System S4D -Client 100 -LogonEntry "S/4HANA Development"
```

Existing files are left alone. `requirements.txt` and `.gitignore` get the lines they are missing. This also adds the [MCP server](#add-it-to-a-project-you-already-have).

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

If the list comes back shorter than expected, a remembered value is probably filtering it: selection screens can pre-fill fields such as the plant. Check what `.\inspect.ps1 ME2N` shows and clear those fields with `Fill Text Field    <label>    ${EMPTY}`.

**3. Run it:**

```powershell
.\run_tests.ps1 tests\01_open_quantity.robot
```

As you add more, move each transaction's steps into a keyword in its own file, such as `resources\me2n.resource`, so tests stay short and a changed screen means changing one file.

Prefer to click through a flow yourself? [Record it by hand](#record-steps-by-hand) and turn the recording into a test.

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

## MCP server: let Claude work through SAP live

`.\inspect.ps1` only shows a transaction's first screen. The `sap-gui` MCP server lets Claude go further, one step at a time: fill a selection, execute it, look at the list, open a row, and turn the steps into a test.

### Set it up in a new project

There is nothing separate to install. `.\setup.ps1` installs what the server needs, and `.mcp.json` tells Claude Code how to start it.

**1. Run `.\setup.ps1`,** as in [Start a new project](#start-a-new-project).

**2. Log on** to the system in SAP Logon. The server never logs on: it uses your logon, in a window of its own.

**3. Open Claude Code in the project folder,** and approve `sap-gui` when it asks. It has to be that folder, because `.mcp.json` uses paths relative to it.

**4. Check that it connects:**

```powershell
claude mcp get sap-gui
```

You should see `Status: ✓ Connected`.

**5. Ask Claude:**

> Look at what ME2N shows for PO 4500000001 and write a test that reads the open quantities

| If | Do this |
|---|---|
| It says `Failed to connect` | Run `.\setup.ps1`: `.venv` or `resources\sap_system.resource` is missing |
| You rejected it by mistake | Run `claude mcp reset-project-choices` in the project folder, then reopen Claude Code |
| Claude says there is no SAP logon | Log on in SAP Logon, on the system and client in `resources\sap_system.resource` |

### Add it to a project you already have

Projects don't update themselves, including those made from an earlier version of this template. Get the latest starter, add its new files, then run setup to install the MCP SDK. Setup keeps your existing settings.

```powershell
git clone https://github.com/weiserman/robosapiens-starter.git
.\robosapiens-starter\add-to-project.ps1 -Path C:\Projects\my-sap-project
cd C:\Projects\my-sap-project
.\setup.ps1
```

If the project already has a `.mcp.json`, `add-to-project.ps1` leaves it alone, so add the `sap-gui` entry from this repo's `.mcp.json` to it yourself. Then continue from step 2 above.

### Use it from another MCP client

Other clients need full paths. Add this to the client's MCP settings, with your project's folder:

```json
{
  "mcpServers": {
    "sap-gui": {
      "command": "C:\\Projects\\my-sap-project\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Projects\\my-sap-project\\tools\\sap_mcp_server.py"]
    }
  }
}
```

The server starts this way from any folder, but only Claude Code has been tried as the client.

### What it can do

| Tool | What it does |
|---|---|
| `open_window`, `close_window` | Opens and closes a window of its own, on the system in `sap_system.resource` |
| `describe_screen`, `screenshot` | Shows Claude the labels, fields, buttons, tabs and columns, or a picture |
| `start_transaction`, `press_key`, `push_button`, `select_tab`, `select_menu_entry` | Moves around |
| `fill_field`, `tick_checkbox`, `untick_checkbox`, `select_radio_button`, `select_dropdown_entry` | Fills in a screen |
| `read_field`, `read_table`, `double_click_cell` | Reads, and opens a row |
| `recorded_test` | Returns the steps so far as a Robot Framework test |

Run a recorded test before you rely on it. It reads whole tables where Claude may have read a few rows, so a step after a read can behave differently.

### What it is allowed to do

**It is read-only unless you change that:**

- It only starts the transactions in `resources\sap_mcp_transactions.txt`. Add display transactions there, one per line. It takes effect without a restart.
- It refuses `Ctrl+S` and `F11`, and buttons and menu entries with names such as Save, Post or Delete.
- It never logs on, has no tool that takes a password, and cannot touch your own windows.

This guards against mistakes, but it is not a security boundary: a display transaction can still lead somewhere unexpected, and a button can be named in a way the list misses. For a guarantee, log on with a user that has display authorizations only.

To let Claude save and post on a test system, set `${SAP_MCP_ALLOW_CHANGES}` to `True` in `resources\sap_system.resource` and restart the server. All transactions then start, the refusals stop, and a `fill_cell` tool appears. Never do this on a production system.

The server closes its window when it stops. If it is stopped abruptly, close the leftover window by hand.

## Record steps by hand

RoboSAPiens includes a recorder: you work in SAP as usual, and it writes the steps as a test. Use it when it's quicker to show a flow than to describe it, especially for people who don't write tests.

| To | Use |
|---|---|
| See a transaction's first screen | `.\inspect.ps1 ME2N` |
| Have Claude explore screens, read-only | [The MCP server](#mcp-server-let-claude-work-through-sap-live) |
| Show a flow yourself, with your own clicks | The recorder |

**Read this first:**

- **Everything you do really happens.** The recorder only watches, so nothing makes it read-only: Save saves and Post posts. Record on a test system.
- **It only records your first SAP window,** the first window of your first logon, even if you're working in another one.
- **Don't run a recording as it is.** It starts SAP Logon, takes over your first window, and ends with `Close SAP`, which closes SAP Logon and every window in it. Convert it first, as shown below.
- **Keep a selection restricted.** A list with nothing filled in, such as an empty ME2N, can tie up a window for minutes and end in a short dump.
- **Keep recordings out of git.** The HTML report has screenshots of your screens. `results\` is ignored, so record there.

### Make a recording

**1. Log on** in SAP Logon. If you have several windows open, do the steps in the first one you opened.

**2. Start the recorder** from the project folder. For 32-bit SAP GUI, use `robosapiens.exe` instead.

```powershell
New-Item -ItemType Directory -Force results\recordings
cd results\recordings
..\..\.venv\Scripts\robosapiens-x64.exe --record
```

**3. Name the test.** Type `new`, a test name such as `PO Open Lines`, and the language `en`. This is also the only time it asks for them.

**4. Type `start`,** and wait for `Connected to the current session.`

**5. Work in SAP.** Type transactions, fill fields and press keys as you normally would. To check a result, type a keyword in the recorder window, with at least two spaces between the parts:

```text
${title}   Get Window Title
```

**6. Type `stop`, `save`, then `exit`.** `stop` and `start` also pause and resume a recording, and `save` only works while stopped.

You'll find two files in `results\recordings`: `PO_Open_Lines.robot`, and `PO_Open_Lines.html`, which shows each step with a screenshot.

| Command | What it does | When |
|---|---|---|
| `new` | Asks for the test name and language | First |
| `start` | Starts or resumes recording | After `new` |
| `stop` | Stops recording | While recording |
| `save` | Writes the files to the current folder | After `stop` |
| `${result}   Keyword   argument` | Adds a keyword call to the recording | While recording |
| `help` | Lists the commands available right now | Any time |
| `exit` | Closes the recorder, without saving | Any time |

### Turn it into a test

A recording looks like this:

```robot
*** Settings ***
Library    RoboSAPiens    x64=True
Test Setup    Open SAP    C:\\Program Files\\SAP\\FrontEnd\\SAPGUI\\saplogon.exe
Test Teardown    Close SAP


*** Test Cases ***
PO Open Lines
    Connect to running SAP
    # Window: SAP Easy Access
    Execute Transaction    /nme2n    with_command_field=True
    # Window: Purchasing Documents per Document Number
    Fill Text Field    Purchasing Document Number    4500000001
    Push Button    Execute (F8)    exact=True
    # Window: Purchasing Documents by Document Number
    Double-click Cell    4500000001    Pur. Doc.
    # Window: Standard PO 4500000001
    Push Button    Back    exact=True
    # Window: Purchasing Documents by Document Number
    Push Button    Back    exact=True
    ${title}    Get Window Title
```

Save a copy in `tests\`, replace the `*** Settings ***` section, and put the steps between `Open SAP Window` and `Close SAP GUI Session`. Those replace `Connect to running SAP`, `Open SAP` and `Close SAP`:

```robot
*** Settings ***
Resource          ../resources/sap_gui.resource
Test Tags         read-only

*** Test Cases ***
PO Open Lines
    Open SAP Window
    TRY
        Execute Transaction    /nme2n    with_command_field=True
        Fill Text Field    Purchasing Document Number    4500000001
        Push Button    Execute (F8)    exact=True
        Double-click Cell    4500000001    Pur. Doc.
        Push Button    Back    exact=True
        Push Button    Back    exact=True
        ${title}    Get Window Title
    FINALLY
        Close SAP GUI Session
    END
```

Then tidy it up:

- **Add what you didn't change.** The recorder only records what you touched. If a screen remembered a value such as the site, the test depends on it, so set it or clear it with `Fill Text Field    <label>    ${EMPTY}`.
- **Add checks.** A recording only repeats steps: it doesn't check a result until you add something like `Should Be Equal`.
- **Replace test data,** such as the PO number, with variables.
- **Tag anything that saves or posts,** for example `posts-goods-movement`, and don't use `read-only`.

Run it with `.\run_tests.ps1 tests\po_open_lines.robot`. You can also ask Claude: "Turn `results\recordings\PO_Open_Lines.robot` into a test".

### Record reusable keywords

To group steps into named keywords, start the recorder with `--record-keywords`:

```powershell
..\..\.venv\Scripts\robosapiens-x64.exe --record-keywords
```

Each `start` and `stop` then records one keyword, and `stop` asks for its name, unless nothing happened. `save` writes the `.robot` file with no HTML report. Convert it in the same way. So far this mode has only been tried without any clicks in SAP, while the plain `--record` steps above come from a real recording.

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
| `resources\sap_mcp_transactions.txt` | Transactions the MCP server may start while read-only | Add display transactions |
| `tools\sap_mcp_server.py`, `.mcp.json` | The MCP server, and how Claude Code starts it | Rarely |
| `tools\test_sap_mcp_server.py` | Its tests, which need no SAP GUI | If you change the server |
| `.claude\skills\robosapiens\` | The Claude Code skill | If your conventions differ |
| `run_tests.ps1`, `inspect.ps1`, `setup.ps1` | Run, look, set up | Rarely |
| `add-to-project.ps1`, `install-skill.ps1` | Add to an existing project, install the skill | No |

## Troubleshooting

See [the troubleshooting table](.claude/skills/robosapiens/references/troubleshooting.md). The three most common:

- **`No SAP GUI logon to SID client 100`**: log on in SAP Logon, and check `resources\sap_system.resource`.
- **`text field ... could not be found`**: run `.\inspect.ps1 <transaction>` and copy the label exactly, including its capitals.
- **`running scripts is disabled on this system`**: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or ask IT.

## Upgrading RoboSAPiens

The version is pinned in `requirements.txt`. RoboSAPiens has no release notes, so change the version on purpose, run `.\setup.ps1`, and run your tests. The MCP server calls RoboSAPiens directly, so run its tests too: `cd tools`, then `..\.venv\Scripts\python.exe -m unittest test_sap_mcp_server`.

## Tested on

SAP GUI 8.00 64-bit, S/4HANA, Python 3.13, Robot Framework 7.5, RoboSAPiens 2.36.2, MCP SDK 2.3.0, logon language EN. Other versions should work but have not been tried: 32-bit SAP GUI in particular. Issues and pull requests are welcome.

## License and credits

MIT, see [LICENSE](LICENSE). [RoboSAPiens](https://github.com/imbus/robotframework-robosapiens) is by imbus and is licensed under Apache-2.0. This is an independent project, not affiliated with SAP or imbus. SAP and SAP GUI are trademarks of SAP SE.
