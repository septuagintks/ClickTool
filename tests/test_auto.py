"""Unit tests for the auto-run entry point."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
ENTRY_PATH = ROOT_DIR / "clicktool.py"


def load_entry_module():
    spec = importlib.util.spec_from_file_location("clicktool_entry", ENTRY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(sys.platform != "win32", "Windows-only tests")
class TestRunAutoConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = load_entry_module()

    def write_config(self, data):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        with temp:
            json.dump(data, temp)
        self.addCleanup(lambda: Path(temp.name).unlink(missing_ok=True))
        return temp.name

    def log_messages(self, write_log_mock):
        return [call.args[1] for call in write_log_mock.call_args_list]

    def test_screen_key_action_runs_in_auto_mode(self):
        config_path = self.write_config({
            "mode": "screen",
            "loop": False,
            "global_interval": 0,
            "actions": [
                {"type": "key", "vk": 65, "key_name": "A"},
            ],
        })

        with (
            patch.object(self.entry, "perform_screen_key_action", return_value=True) as key_action,
            patch.object(self.entry, "perform_screen_mouse_action") as mouse_action,
            patch.object(self.entry, "write_auto_log") as write_log,
        ):
            result = self.entry.run_auto_config(config_path, "auto.log")

        self.assertEqual(result, 0)
        key_action.assert_called_once()
        mouse_action.assert_not_called()
        self.assertIn("ran screen key action key=A", self.log_messages(write_log))

    def test_window_key_action_runs_in_auto_mode(self):
        config_path = self.write_config({
            "mode": "window",
            "loop": False,
            "global_interval": 0,
            "target_windows": ["Notepad"],
            "actions": [
                {"type": "key", "vk": 65, "key_name": "A", "win_title": "Notepad"},
            ],
        })

        with (
            patch.object(self.entry, "wait_for_windows", return_value={"Notepad": 100}),
            patch.object(self.entry, "user32", SimpleNamespace(IsWindow=lambda hwnd: True)),
            patch.object(self.entry, "perform_window_key_action", return_value=True) as key_action,
            patch.object(self.entry, "perform_window_mouse_action") as mouse_action,
            patch.object(self.entry, "write_auto_log") as write_log,
        ):
            result = self.entry.run_auto_config(config_path, "auto.log")

        self.assertEqual(result, 0)
        key_action.assert_called_once()
        mouse_action.assert_not_called()
        self.assertIn("ran window key action title=Notepad key=A", self.log_messages(write_log))

    def test_unknown_action_is_skipped_and_not_counted_runnable(self):
        config_path = self.write_config({
            "mode": "screen",
            "loop": False,
            "global_interval": 0,
            "actions": [
                {"type": "unknown", "x": 10, "y": 20},
            ],
        })

        with (
            patch.object(self.entry, "perform_screen_key_action") as key_action,
            patch.object(self.entry, "perform_screen_mouse_action") as mouse_action,
            patch.object(self.entry, "write_auto_log") as write_log,
        ):
            result = self.entry.run_auto_config(config_path, "auto.log")

        self.assertEqual(result, 3)
        key_action.assert_not_called()
        mouse_action.assert_not_called()
        messages = self.log_messages(write_log)
        self.assertIn("unknown action type=unknown; skipped", messages)
        self.assertIn("no runnable actions; exit=3", messages)

    def test_screen_mouse_failure_is_logged(self):
        config_path = self.write_config({
            "mode": "screen",
            "loop": False,
            "global_interval": 0,
            "actions": [
                {"type": "click", "x": 10, "y": 20, "button": "left"},
            ],
        })

        with (
            patch.object(self.entry, "perform_screen_mouse_action", return_value=False),
            patch.object(self.entry, "write_auto_log") as write_log,
        ):
            result = self.entry.run_auto_config(config_path, "auto.log")

        self.assertEqual(result, 0)
        self.assertIn("failed screen action type=click x=10 y=20", self.log_messages(write_log))


if __name__ == "__main__":
    unittest.main()
