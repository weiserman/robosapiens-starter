"""Tests of the MCP server that need no SAP GUI: .venv\\Scripts\\python.exe -m unittest tools\\test_sap_mcp_server.py"""
import asyncio
import time
import unittest
from unittest import mock

from mcp import Client

import sap_mcp_server
from sap_mcp_server import SapWindow, build_server, robot_cell

SETTINGS = {"SAP_GUI_SYSTEM": "SID", "SAP_GUI_CLIENT": "100", "SAP_GUI_X64": "True"}


def window(**settings):
    result = SapWindow({**SETTINGS, **settings})
    result.sap = mock.MagicMock()
    result.robosapiens = mock.MagicMock()
    result.state = lambda: "state"
    return result


def call(target, tool, **arguments):
    async def run():
        async with Client(build_server(target)) as client:
            return await client.call_tool(tool, arguments)
    return asyncio.run(run())


def tools(target):
    async def run():
        async with Client(build_server(target)) as client:
            return [tool.name for tool in (await client.list_tools()).tools]
    return asyncio.run(run())


class ReadOnly(unittest.TestCase):
    def assert_refused(self, target, tool, **arguments):
        result = call(target, tool, **arguments)
        self.assertTrue(result.is_error)
        self.assertIn("Refused", result.content[0].text)
        self.assertEqual(target.robosapiens.method_calls, [])

    def test_refuses_saving_keys(self):
        for key in ("Ctrl+S", "ctrl + s", "F11"):
            self.assert_refused(window(), "press_key", key=key)

    def test_refuses_buttons_that_change_data(self):
        for name in ("Save", "Save   (Ctrl+S)", "Post", "Delete", "Buchen", "Löschen"):
            self.assert_refused(window(), "push_button", name=name)

    def test_refuses_menu_entries_that_change_data(self):
        self.assert_refused(window(), "select_menu_entry", path="Purchase Order/Save")

    def test_refuses_transactions_not_on_the_list(self):
        for code in ("MIGO", "/nME2N", "/nex", "ME2N/nMIGO"):
            self.assert_refused(window(), "start_transaction", code=code)

    def test_starts_transactions_on_the_list(self):
        target = window()
        target.sap.session.Info.Transaction = "ME2N"
        self.assertFalse(call(target, "start_transaction", code="me2n").is_error)
        target.robosapiens.execute_transaction.assert_called_once_with("/nme2n")
        self.assertEqual(target.steps, ["Execute Transaction    /nme2n"])

    def test_tells_when_a_transaction_did_not_start(self):
        target = window()
        target.sap.session.Info.Transaction = "SM04"
        result = call(target, "start_transaction", code="ME2N")
        self.assertIn("did not start", result.content[0].text)
        self.assertEqual(target.steps, [])

    def test_has_no_fill_cell(self):
        self.assertNotIn("fill_cell", tools(window()))

    def test_stays_read_only_when_the_setting_is_missing_or_unclear(self):
        self.assertFalse(SapWindow(SETTINGS).allow_changes)
        self.assertFalse(SapWindow({**SETTINGS, "SAP_MCP_ALLOW_CHANGES": "yes"}).allow_changes)


class AllowChanges(unittest.TestCase):
    def test_allows_what_read_only_refuses(self):
        target = window(SAP_MCP_ALLOW_CHANGES="True")
        self.assertFalse(call(target, "press_key", key="Ctrl+S").is_error)
        self.assertFalse(call(target, "push_button", name="Save").is_error)
        target.sap.session.Info.Transaction = "MIGO"
        self.assertFalse(call(target, "start_transaction", code="MIGO").is_error)
        self.assertIn("fill_cell", tools(target))


class Steps(unittest.TestCase):
    def test_buttons_match_the_whole_name(self):
        target = window()
        call(target, "push_button", name="Execute")
        target.robosapiens.push_button.assert_called_once_with("Execute", exact=True)

    def test_buttons_can_be_named_as_describe_screen_shows_them(self):
        target = window()
        call(target, "push_button", name="Execute   (F8)")
        target.robosapiens.push_button.assert_called_once_with("Execute (F8)", exact=True)

    def test_needs_an_open_window(self):
        target = window()
        target.sap.session = None
        result = call(target, "fill_field", label="Site", value="1005")
        self.assertTrue(result.is_error)
        self.assertIn("open_window", result.content[0].text)

    def test_tells_when_there_is_no_table(self):
        target = window()
        target.robosapiens.count_table_rows.side_effect = IndexError("Replacement index 0 out of range")
        result = call(target, "read_table", columns=["Item"])
        self.assertIn("No table on this screen", result.content[0].text)

    def test_tells_when_sap_stays_busy(self):
        target = window()
        target.robosapiens.press_key_combination.side_effect = lambda key: time.sleep(0.2)
        with mock.patch.object(sap_mcp_server, "STEP_TIMEOUT", 0.01):
            result = call(target, "press_key", key="F8")
        self.assertIn("still busy", result.content[0].text)

    def test_reads_at_most_200_rows(self):
        target = window()
        target.robosapiens.count_table_rows.return_value = 1000
        target.robosapiens.read_cell.return_value = " x "
        call(target, "read_table", columns=["Item"], max_rows=5000)
        self.assertEqual(target.robosapiens.read_cell.call_count, 200)


class Recording(unittest.TestCase):
    def test_uses_real_robot_keyword_names(self):
        target = window()
        for tool, arguments in (("press_key", {"key": "F8"}), ("select_tab", {"name": "Delivery"}),
                                ("tick_checkbox", {"label": "Open"}), ("select_menu_entry", {"path": "System/Status"}),
                                ("double_click_cell", {"row": 1, "column": "Item"})):
            call(target, tool, **arguments)
        self.assertEqual(target.steps, ["Press Key Combination    F8", "Select Tab    Delivery", "Tick Checkbox    Open",
                                        "Select Menu Entry    System/Status", "Double-click Cell    1    Item"])

    def test_reads_of_one_table_become_one_step(self):
        target = window()
        target.robosapiens.count_table_rows.return_value = 5
        target.robosapiens.read_cell.return_value = "x"
        call(target, "read_table", columns=["Item", "Site"], max_rows=2)
        call(target, "read_table", columns=["Site", "Article"], first_row=3)
        self.assertEqual(target.steps, ["${rows}=    Get Table Rows    Item    Site    Article"])

    def test_leaves_out_steps_that_failed(self):
        target = window()
        target.robosapiens.fill_text_field.side_effect = RuntimeError("not found")
        call(target, "fill_field", label="Site", value="1005")
        self.assertEqual(target.steps, [])

    def test_writes_a_test_of_the_starters_shape(self):
        target = window()
        target.steps = ["Execute Transaction    SM04"]
        self.assertEqual(target.recorded_test("Users"), "\n".join([
            "*** Settings ***", "Resource          ../resources/sap_gui.resource", "Test Tags         read-only", "",
            "*** Test Cases ***", "Users", "    Open SAP Window", "    TRY", "        Execute Transaction    SM04",
            "    FINALLY", "        Close SAP GUI Session", "    END", ""]))

    def test_escapes_cells(self):
        self.assertEqual(robot_cell(""), "${EMPTY}")
        self.assertEqual(robot_cell("plain text"), "plain text")
        self.assertEqual(robot_cell("a  b"), "a ${SPACE}b")
        self.assertEqual(robot_cell(" a "), "${SPACE}a${SPACE}")
        self.assertEqual(robot_cell("${x}"), "\\${x}")
        self.assertEqual(robot_cell("a=b"), "a\\=b")
        self.assertEqual(robot_cell("C:\\x"), "C:\\\\x")
        self.assertEqual(robot_cell("#1"), "\\#1")


class Settings(unittest.TestCase):
    def test_reads_the_example_file(self):
        path = sap_mcp_server.ROOT / "resources" / "sap_system.resource.example"
        settings = sap_mcp_server.read_settings(path.with_suffix(".example"))
        self.assertEqual(settings["SAP_MCP_ALLOW_CHANGES"], "False")
        self.assertEqual(settings["SAP_GUI_SYSTEM"], "__SYSTEM__")

    def test_transaction_list_has_no_comments(self):
        transactions = sap_mcp_server.read_transactions()
        self.assertIn("ME2N", transactions)
        self.assertNotIn("MIGO", transactions)
        self.assertFalse([code for code in transactions if " " in code or "#" in code])


if __name__ == "__main__":
    unittest.main()
