"""MCP server that lets an AI assistant work through SAP GUI one step at a time, with RoboSAPiens.

Use it to explore a transaction before writing a test: every step reports where it landed, and
recorded_test turns the steps taken into a Robot Framework test.

It follows the rules of this starter, in code rather than in documentation:
- It works in a window of its own on the system in resources/sap_system.resource, and closes only
  that window. It has no tool to attach to, or close, anything else.
- It never logs on. The user logs on in SAP Logon, so no password passes through the assistant.
- It is read-only unless ${SAP_MCP_ALLOW_CHANGES} is True in sap_system.resource: only the
  transactions in resources/sap_mcp_transactions.txt start, saving and posting are refused, and
  fill_cell does not exist. This guards against mistakes. It is not a security boundary: for a
  guarantee, log on with a user that has display authorizations only.
"""
import asyncio
import concurrent.futures
import contextlib
import functools
import io
import json
import re
import sys
from pathlib import Path

import pythoncom
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from robot.running import ResourceFile
from RoboSAPiens import RoboSAPiens

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "libraries"))
from SapGui import SapGui  # noqa: E402

SETTINGS_FILE = ROOT / "resources" / "sap_system.resource"
TRANSACTIONS_FILE = ROOT / "resources" / "sap_mcp_transactions.txt"
SCREENSHOT_FILE = ROOT / "results" / "mcp" / "screen.png"

MAX_ROWS = 200
STEP_TIMEOUT = 120
TABLE_STEP = "${rows}=    Get Table Rows"
SAVING_KEYS = {"ctrl+s", "f11"}
# Names of commands that change data, also in German. Icon buttons are named by their tooltip.
CHANGING_NAMES = re.compile(r"\b(save|post|delete|book|release|approve|sichern|buchen|löschen|freigeben)\b",
                            re.IGNORECASE)


def read_settings(path=SETTINGS_FILE):
    """The variables of sap_system.resource by name, without the ${} around it."""
    variables = ResourceFile.from_file_system(path).variables
    return {variable.name[2:-1]: variable.value[0] if variable.value else "" for variable in variables}


def read_transactions(path=TRANSACTIONS_FILE):
    """The transactions that may start in read-only mode. Read on every use, so that a line the
    user adds works without restarting the server."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    return {line.split("#")[0].strip().upper() for line in lines} - {""}


def robot_cell(value):
    """``value`` as one cell of a Robot Framework test, which reads \\, ${}, = and runs of spaces itself."""
    value = str(value)
    if not value:
        return "${EMPTY}"
    value = value.replace("\\", "\\\\").replace("=", "\\=")
    value = re.sub(r"([$@&%]){", r"\\\1{", value)
    value = re.sub(r"^#", r"\\#", value)
    value = re.sub(r"(?<= ) ", "${SPACE}", value)
    return re.sub(r"^ | $", "${SPACE}", value)


class SapWindow:
    """The server's SAP window, with what was done in it so far."""

    def __init__(self, settings):
        self.system = settings["SAP_GUI_SYSTEM"]
        self.client = settings["SAP_GUI_CLIENT"]
        self.x64 = settings.get("SAP_GUI_X64", "True") == "True"
        self.allow_changes = settings.get("SAP_MCP_ALLOW_CHANGES") == "True"
        self.sap = SapGui()
        self.robosapiens = None
        self.steps = []

    # --- The window -------------------------------------------------------

    def open(self):
        if self.sap.session is not None and self._alive():
            return self.state()
        if self.robosapiens is None:
            self.robosapiens = RoboSAPiens(x64=self.x64)
        window = self.sap.open_sap_gui_session(self.system, self.client)
        session = self.robot("connect_to_running_sap", connection=window["connection"],
                             client=window["client"], session_number=window["session_number"])
        # SAP Logon can leave the connection name empty, then only the client tells systems apart
        if session["server"] != self.system:
            self.close()
            raise RuntimeError(f"Took over a window on {session['server']}, not {self.system}: "
                               "ask the user to close that logon")
        self.steps = []
        return self.state()

    def close(self):
        try:
            self.sap.close_sap_gui_session()
        except Exception:
            self.sap.session = None  # the user closed it

    def _alive(self):
        try:
            self.sap.session.Info
            return True
        except Exception:
            self.sap.session = None
            return False

    def require_window(self):
        if self.sap.session is None or not self._alive():
            raise RuntimeError("No SAP window: call open_window first")

    def state(self):
        session = self.sap.session
        status = session.findById("wnd[0]/sbar").Text
        return (f"Window: {session.ActiveWindow.Text}\nTransaction: {session.Info.Transaction}\n"
                f"Status bar: {status or '(empty)'}")

    # --- Steps ------------------------------------------------------------

    def robot(self, method, *args, **named):
        # RoboSAPiens prints a line per keyword, which must not reach the protocol on stdout
        with contextlib.redirect_stdout(io.StringIO()):
            return getattr(self.robosapiens, method)(*args, **named)

    def step(self, method, *args, **named):
        self.require_window()
        self.robot(method, *args, **named)
        self.record(method, *args, **named)
        return self.state()

    def record(self, method, *args, assign="", **named):
        keyword = getattr(RoboSAPiens, method).robot_name
        cells = [keyword, *map(robot_cell, args), *(f"{name}={value}" for name, value in named.items())]
        self.steps.append("    ".join([assign, *cells] if assign else cells))

    def record_table(self, columns):
        # Get Table Rows reads to the end of the table and rows above the visible area are not found,
        # so reads of one table become a single step
        cells = list(map(robot_cell, columns))
        if self.steps and self.steps[-1].startswith(TABLE_STEP):
            earlier = self.steps.pop().split("    ")[2:]
            cells = earlier + [cell for cell in cells if cell not in earlier]
        self.steps.append("    ".join([TABLE_STEP, *cells]))

    def recorded_test(self, name):
        tag = "posts-data" if self.allow_changes else "read-only"
        return "\n".join([
            "*** Settings ***",
            "Resource          ../resources/sap_gui.resource",
            f"Test Tags         {tag}",
            "",
            "*** Test Cases ***",
            name,
            "    Open SAP Window",
            "    TRY",
            *(f"        {step}" for step in self.steps),
            "    FINALLY",
            "        Close SAP GUI Session",
            "    END",
            "",
        ])

    # --- Read-only guards -------------------------------------------------

    def refuse(self, what):
        raise PermissionError(f"Refused: {what}, and this server is read-only on {self.system}. "
                              "Only the user can change that, in resources/sap_system.resource.")

    def check_transaction(self, code):
        if not self.allow_changes and code.upper() not in read_transactions():
            raise PermissionError(f"Refused: {code} is not in resources/sap_mcp_transactions.txt, the transactions "
                                  "that may run while read-only. If it only displays data, ask the user to add it.")

    def check_key(self, key):
        if not self.allow_changes and key.replace(" ", "").lower() in SAVING_KEYS:
            self.refuse(f"{key} saves")

    def check_name(self, name):
        if not self.allow_changes and CHANGING_NAMES.search(name):
            self.refuse(f"'{name}' can change data")


def build_server(window):
    # COM objects belong to the thread that made them, so all of SAP runs on this one thread
    worker = concurrent.futures.ThreadPoolExecutor(max_workers=1, initializer=pythoncom.CoInitialize)

    def on_worker(function):
        @functools.wraps(function)
        async def run(*args, **named):
            call = functools.partial(function, *args, **named)
            try:
                step = asyncio.get_running_loop().run_in_executor(worker, call)
                return await asyncio.wait_for(step, STEP_TIMEOUT)
            except TimeoutError:
                raise ToolError(f"SAP is still busy after {STEP_TIMEOUT} seconds, probably on a large list. The step "
                                "keeps running and later steps wait for it: tell the user. Next time restrict "
                                "the selection first.") from None
            except Exception as error:  # the SDK hides the text of any other exception
                raise ToolError(str(error)) from error
        return run

    @contextlib.asynccontextmanager
    async def close_window_at_the_end(_):
        try:
            yield
        finally:
            # No time limit: the window can only close once SAP has finished the step it is on
            await asyncio.get_running_loop().run_in_executor(worker, window.close)
            worker.shutdown()

    server = MCPServer(
        "sap-gui",
        lifespan=close_window_at_the_end,
        instructions=(
            f"Drives SAP GUI on {window.system} client {window.client} in a window of its own. Call open_window "
            "first and describe_screen before acting on a screen: labels differ per system and language, so never "
            "guess them. Call close_window when done, and recorded_test to turn the steps into a Robot Framework "
            "test. "
            + ("This server can save and post: tell the user what a step changes before taking it."
               if window.allow_changes else "It is read-only: if a step is refused, tell the user why.")
        ),
    )

    def tool(read_only=False):
        def register(function):
            annotations = ToolAnnotations(readOnlyHint=read_only, destructiveHint=window.allow_changes and not read_only)
            return server.tool(annotations=annotations)(on_worker(function))
        return register

    @tool()
    def open_window() -> str:
        """Opens this server's own SAP window on the configured system, using the logon the user already
        has. Never logs on: if there is no logon, ask the user to log on in SAP Logon. Starts a new recording."""
        return window.open()

    @tool()
    def close_window() -> str:
        """Closes this server's SAP window. The user's own windows stay as they are."""
        window.close()
        return "Closed. recorded_test still returns the steps."

    @tool(read_only=True)
    def describe_screen() -> str:
        """Lists what the window shows now, popups included: labels, fields, buttons, tabs and table columns."""
        window.require_window()
        return f"{window.state()}\n\n{window.sap.describe_screen()}"

    @tool(read_only=True)
    def screenshot() -> Image:
        """Returns a picture of the window. Use it when describe_screen does not explain what is going on."""
        window.require_window()
        SCREENSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        window.robot("save_screenshot", str(SCREENSHOT_FILE))
        return Image(data=SCREENSHOT_FILE.read_bytes(), format="png")

    @tool()
    def start_transaction(code: str) -> str:
        """Starts a transaction, such as ME2N, without any prefix."""
        window.check_transaction(code)
        window.require_window()
        # /n leaves the current transaction: from inside one, SAP ignores a bare code without a message
        window.robot("execute_transaction", f"/n{code}")
        if window.sap.session.Info.Transaction != code.upper():
            raise RuntimeError(f"{code} did not start.\n{window.state()}")
        window.record("execute_transaction", f"/n{code}")
        return window.state()

    @tool()
    def fill_field(label: str, value: str) -> str:
        """Fills a text field. An empty value clears it: selection screens remember values, so clear what could
        filter the result. Besides a label, the locator can be 'Unique label >> to' for a range end, or the
        technical name describe_screen shows."""
        return window.step("fill_text_field", label, value)

    @tool(read_only=True)
    def read_field(label: str) -> str:
        """Reads a text field."""
        window.require_window()
        value = window.robot("read_text_field", label)
        window.record("read_text_field", label, assign="${value}=")
        return value

    @tool()
    def press_key(key: str) -> str:
        """Presses a key or combination, such as Enter, F3 (back) or F8 (execute). Prefer this to push_button
        for commands that have a key. Restrict a selection before executing it: an unrestricted list can tie up
        the window for minutes."""
        window.check_key(key)
        return window.step("press_key_combination", key)

    @tool()
    def push_button(name: str) -> str:
        """Pushes a button by its full name or tooltip, as describe_screen shows it."""
        window.check_name(name)
        # RoboSAPiens reads a tooltip such as "Execute   (F8)" with single spaces
        return window.step("push_button", " ".join(name.split()), exact=True)

    @tool()
    def select_tab(name: str) -> str:
        """Selects a tab by its name or tooltip."""
        return window.step("activate_tab", name)

    @tool()
    def select_menu_entry(path: str) -> str:
        """Selects a menu entry, with / between levels, such as System/User Profile/Own Data."""
        window.check_name(path)
        return window.step("select_menu_item", path)

    @tool()
    def select_radio_button(label: str) -> str:
        """Selects a radio button."""
        return window.step("select_radio_button", label)

    @tool()
    def tick_checkbox(label: str) -> str:
        """Ticks a checkbox."""
        return window.step("tick_check_box", label)

    @tool()
    def untick_checkbox(label: str) -> str:
        """Unticks a checkbox."""
        return window.step("untick_check_box", label)

    @tool()
    def select_dropdown_entry(label: str, entry: str) -> str:
        """Selects an entry of a dropdown menu."""
        return window.step("select_combo_box_entry", label, entry)

    @tool(read_only=True)
    def read_table(columns: list[str], first_row: int = 1, max_rows: int = 50) -> str:
        """Reads rows of the table on screen by exact column title, from 1, at most 200 at a time. Read top to
        bottom: rows above the visible area are not found, so a later call needs a higher first_row."""
        window.require_window()
        try:
            total = int(window.robot("count_table_rows"))
        except IndexError:  # how RoboSAPiens reports that the window has no table
            raise RuntimeError(f"No table on this screen.\n{window.state()}") from None
        last = min(total, first_row + min(max_rows, MAX_ROWS) - 1)
        rows = [{column: window.robot("read_cell", str(row), column).strip() for column in columns}
                for row in range(first_row, last + 1)]
        window.record_table(columns)
        return json.dumps({"total_rows": total, "first_row": first_row, "rows": rows}, ensure_ascii=False)

    @tool()
    def double_click_cell(row: int, column: str) -> str:
        """Double-clicks a table cell, which opens the row's detail in many lists."""
        return window.step("double_click_cell", str(row), column)

    if window.allow_changes:
        @tool()
        def fill_cell(row: int, column: str, value: str) -> str:
            """Fills a table cell. Changes the document when it is saved."""
            return window.step("fill_cell", str(row), column, value)

    @tool(read_only=True)
    def recorded_test(name: str = "Recorded Steps") -> str:
        """Returns the steps taken since open_window as a Robot Framework test, for a .robot file in tests/. Run it
        before relying on it: it reads whole tables, so a row used after a read can be above the visible area."""
        return window.recorded_test(name)

    return server


def main():
    if not SETTINGS_FILE.exists():
        sys.exit(f"{SETTINGS_FILE} not found: run .\\setup.ps1 first")
    build_server(SapWindow(read_settings())).run()


if __name__ == "__main__":
    main()
