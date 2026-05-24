"""Unit tests for clicktool.script module."""
import unittest
from clicktool.script import (
    coerce_non_negative_int,
    coerce_wheel_delta,
    normalize_mouse_action,
    infer_script_mode,
)


class TestCoerceNonNegativeInt(unittest.TestCase):
    def test_valid_int(self):
        self.assertEqual(coerce_non_negative_int(42, 10), 42)
        self.assertEqual(coerce_non_negative_int(0, 10), 0)

    def test_negative_returns_zero(self):
        # coerce_non_negative_int clamps negative to 0, not default
        self.assertEqual(coerce_non_negative_int(-5, 10), 0)

    def test_string_valid(self):
        self.assertEqual(coerce_non_negative_int("123", 10), 123)

    def test_string_invalid_returns_default(self):
        self.assertEqual(coerce_non_negative_int("abc", 10), 10)
        self.assertEqual(coerce_non_negative_int("", 10), 10)

    def test_none_returns_default(self):
        self.assertEqual(coerce_non_negative_int(None, 10), 10)


class TestCoerceWheelDelta(unittest.TestCase):
    def test_valid_int(self):
        self.assertEqual(coerce_wheel_delta(3, -1), 3)
        self.assertEqual(coerce_wheel_delta(-2, -1), -2)

    def test_string_valid(self):
        self.assertEqual(coerce_wheel_delta("5", -1), 5)
        self.assertEqual(coerce_wheel_delta("-3", -1), -3)

    def test_invalid_returns_default(self):
        self.assertEqual(coerce_wheel_delta("abc", -1), -1)
        self.assertEqual(coerce_wheel_delta(None, -1), -1)


class TestNormalizeMouseAction(unittest.TestCase):
    def test_click_action(self):
        action = {"type": "click", "x": "10", "y": "20", "button": "left"}
        normalize_mouse_action(action)
        self.assertEqual(action["x"], 10)
        self.assertEqual(action["y"], 20)
        self.assertEqual(action["button"], "left")

    def test_wheel_action(self):
        action = {"type": "wheel", "x": "15", "y": "25", "delta": "-1"}
        normalize_mouse_action(action)
        self.assertEqual(action["x"], 15)
        self.assertEqual(action["y"], 25)
        self.assertEqual(action["delta"], -1)

    def test_missing_fields_get_defaults(self):
        action = {"type": "click"}
        normalize_mouse_action(action)
        self.assertEqual(action["x"], 0)
        self.assertEqual(action["y"], 0)
        self.assertEqual(action["button"], "left")


class TestInferScriptMode(unittest.TestCase):
    def test_explicit_mode(self):
        self.assertEqual(infer_script_mode({"mode": "window"}), "window")
        self.assertEqual(infer_script_mode({"mode": "screen"}), "screen")

    def test_infer_from_window_positions(self):
        data = {"window_positions": [{"type": "click"}]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_target_windows_alone_not_enough(self):
        # infer_script_mode only checks window_positions, not target_windows
        data = {"target_windows": ["Notepad"]}
        self.assertEqual(infer_script_mode(data), "screen")

    def test_default_to_screen(self):
        self.assertEqual(infer_script_mode({}), "screen")


if __name__ == "__main__":
    unittest.main()
