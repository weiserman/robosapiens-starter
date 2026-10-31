"""Robot Framework keyword library that gets a SAP GUI for Windows window for a test (SAP GUI Scripting).

The screens themselves are driven with RoboSAPiens (see resources/sap_gui.resource). This library
does what RoboSAPiens has no keyword for: it gives the test a window of its own and closes only that.
Open SAP GUI Session reuses a logon you already have to the system, in its own extra window so
the window you work in is not touched. Without one it starts SAP Logon if needed and logs on
with the user and password it is given; Close SAP GUI Session then logs off again.
Needs SAP GUI scripting enabled (SAP GUI Options > Accessibility & Scripting > Scripting) and
on the server (profile parameter sapgui/user_scripting = TRUE).
"""
import os
import subprocess
import time

import win32com.client
from robot.api import logger
from robot.api.deco import keyword, library

SAP_LOGON_EXE = r"SAP\FrontEnd\SAPGUI\saplogon.exe"


@library(scope="SUITE")
class SapGui:
    def __init__(self, decimal_separator="."):
        # SAP user setting "Decimal notation": "." for 1,234.56 (X), "," for 1.234,56
        self.decimal_separator = decimal_separator
        self.session = None
        self._connection = None
        self._logged_on_by_test = False

    # --- Session ---------------------------------------------------------

    @keyword
    def open_sap_gui_session(self, system, client, logon_entry="", user="", password="",
                             language="EN", timeout=30):
        """Gets a SAP GUI window on ``system``/``client`` for the test to use.

        Reuses an existing logon (in a new window) when there is one. Otherwise logs on through
        the SAP Logon entry ``logon_entry`` with ``user`` and ``password``.

        Returns the ``connection``, ``client`` and ``session_number`` of the window, which is what
        RoboSAPiens' Connect To Running SAP needs to take that window over.
        """
        engine = self._scripting_engine(int(timeout))
        for connection in self._children(engine):
            for session in self._children(connection):
                info = session.Info
                if info.SystemName == system and info.Client == str(client) and info.User:
                    self._create_session(connection, session, int(timeout))
                    return self._window()
        if not (logon_entry and user and password):
            raise AssertionError(f"No SAP GUI logon to {system} client {client}, and no SAP GUI user "
                                 "and password to log on with: log on in SAP Logon, or set SAP_GUI_USERNAME and "
                                 "SAP_GUI_PASSWORD as environment variables")
        self._log_on(engine, logon_entry, client, user, password, language)
        return self._window()

    def _window(self):
        sessions = [s.Id for s in self._children(self._connection)]
        return {"connection": self._connection.Description, "client": self.session.Info.Client,
                "session_number": sessions.index(self.session.Id) + 1}

    @keyword
    def close_sap_gui_session(self):
        """Closes the test's SAP GUI window, logging off if the test logged on itself."""
        if self.session is None:
            return
        if self._logged_on_by_test:
            self._connection.CloseConnection()
        else:
            self._connection.CloseSession(self.session.Id)
        self.session = None

    def _scripting_engine(self, timeout):
        """The SAP GUI scripting engine, starting SAP Logon first when it is not running."""
        end = time.time() + timeout
        started = False
        while True:
            try:
                return win32com.client.GetObject("SAPGUI").GetScriptingEngine
            except Exception as error:
                if not started:
                    subprocess.Popen([self._sap_logon_exe()])
                    started = True
                elif time.time() > end:
                    raise AssertionError("SAP Logon started but SAP GUI scripting is not available: switch it on "
                                         f"in SAP GUI Options > Accessibility & Scripting ({error})")
                time.sleep(1)

    @staticmethod
    def _sap_logon_exe():
        for root in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
            path = os.path.join(root, SAP_LOGON_EXE)
            if os.path.exists(path):
                return path
        raise AssertionError("SAP Logon is not running and saplogon.exe was not found: start SAP Logon")

    def _log_on(self, engine, logon_entry, client, user, password, language):
        try:
            connection = engine.OpenConnection(logon_entry, True)
        except Exception as error:
            raise AssertionError(f"Could not open SAP Logon entry '{logon_entry}': {error}")
        self._connection, self.session = connection, connection.Children(0)
        self._logged_on_by_test = True
        self._set_field("txtRSYST-MANDT", client)
        self._set_field("txtRSYST-BNAME", user)
        self._set_field("pwdRSYST-BCODE", password)
        self._set_field("txtRSYST-LANGU", language, required=False)
        self.session.findById("wnd[0]").sendVKey(0)
        # dialogs after the logon screen: multiple logon, system messages, copyright
        for _ in range(5):
            if self._exists("wnd[0]/usr/pwdRSYST-NCODE"):
                self.close_sap_gui_session()
                raise AssertionError(f"SAP asks a new password for {user}: log on by hand once to change it")
            if self._exists("wnd[0]/usr/txtRSYST-BNAME"):
                message = self.session.findById("wnd[0]/sbar").Text
                self.close_sap_gui_session()
                raise AssertionError(f"SAP GUI logon as {user} failed: {message}")
            if not self._exists("wnd[1]"):
                break
            if self._exists("wnd[1]/usr/radMULTI_LOGON_OPT2"):
                # "Continue with this logon, without ending any other logons"
                self.session.findById("wnd[1]/usr/radMULTI_LOGON_OPT2").Select()
            self.session.findById("wnd[1]").sendVKey(0)
        info = self.session.Info
        logger.info(f"Logged on to {info.SystemName} {info.Client} as {info.User} via '{logon_entry}'")

    def _exists(self, element_id):
        return self.session.findById(element_id, False) is not None

    def _create_session(self, connection, session, timeout):
        before = {s.Id for s in self._children(connection)}
        session.CreateSession()
        end = time.time() + timeout
        while time.time() < end:
            new = [s for s in self._children(connection) if s.Id not in before]
            if new and not new[0].Busy:
                self._connection, self.session = connection, new[0]
                self._logged_on_by_test = False
                info = self.session.Info
                logger.info(f"SAP GUI window opened on {info.SystemName} {info.Client} as {info.User} "
                            "(existing logon)")
                return
            time.sleep(0.5)
        raise AssertionError("SAP GUI did not open a new window: close one if 6 are already open")

    # --- Values ----------------------------------------------------------

    @keyword("SAP Number")
    def sap_number(self, text):
        """Converts a number as SAP GUI shows it, such as ``1,234.50`` or ``12-``, to a number."""
        thousands = "," if self.decimal_separator == "." else "."
        text = text.replace(thousands, "").replace(" ", "").replace(self.decimal_separator, ".")
        if text.endswith("-"):
            text = "-" + text[:-1]
        value = float(text or 0)
        return int(value) if value.is_integer() else value

    # --- Looking at a screen ----------------------------------------------

    @keyword
    def describe_screen(self):
        """Returns what the test's window shows, for writing RoboSAPiens steps: labels, fields,
        buttons, tabs and table columns. Run it after any step to see what the next one can use.
        """
        window = self.session.ActiveWindow
        lines = [f"Window: {window.Text}"]
        self._describe(window, lines)
        return "\n".join(lines)

    def _describe(self, element, lines):
        for child in self._children(element):
            kind = child.Type
            if kind in ("GuiMenubar", "GuiTitlebar"):
                continue
            if kind == "GuiStatusbar":
                if child.Text:
                    lines.append(f"Status bar: {child.Text}")
            elif kind == "GuiShell" and child.SubType == "GridView":
                self._describe_grid(child, lines)
            elif kind == "GuiTableControl":
                columns = [child.Columns.Item(i).Title for i in range(child.Columns.Count)]
                lines.append(f"Table ({child.RowCount} rows), columns: {columns}")
            elif kind in ("GuiTextField", "GuiCTextField", "GuiPasswordField"):
                if not child.Changeable:
                    if child.Text.strip():
                        lines.append(f"Label: {child.Text}")
                else:
                    value = "*****" if kind == "GuiPasswordField" else child.Text
                    lines.append(f"Field: {child.Name} = {value!r}")
            elif kind == "GuiLabel":
                if child.Text.strip():
                    lines.append(f"Label: {child.Text}")
            elif kind in ("GuiButton", "GuiTab", "GuiRadioButton", "GuiCheckBox", "GuiComboBox"):
                name = child.Text.strip() or child.Tooltip.strip()
                if name:
                    lines.append(f"{kind[3:]}: {name}")
            if child.ContainerType and kind != "GuiShell":
                self._describe(child, lines)

    @staticmethod
    def _describe_grid(grid, lines):
        order = grid.ColumnOrder
        titles = [grid.GetColumnTitles(order[i])[0].strip() for i in range(grid.ColumnCount)]
        lines.append(f"Table ({grid.RowCount} rows), columns: {titles}")

    # --- Helpers ---------------------------------------------------------

    def _set_field(self, field_id, value, required=True):
        try:
            self.session.findById(f"wnd[0]/usr/{field_id}").Text = value
        except Exception:
            if required:
                raise AssertionError(f"Field {field_id} not found on the {self.session.Info.Transaction} screen")

    @staticmethod
    def _children(element):
        children = element.Children
        return [children(i) for i in range(children.Count)]
