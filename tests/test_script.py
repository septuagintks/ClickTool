"""Unit tests for clicktool_min.script module."""
import unittest
from clicktool_min.script import (
    infer_script_mode,
    coerce_bool,
    coerce_non_negative_int,
    coerce_optional_non_negative_int,
    is_position_action,
)


class TestCoerceBool(unittest.TestCase):
    def test_bool_values(self):
        self.assertTrue(coerce_bool(True, False))
        self.assertFalse(coerce_bool(False, True))

    def test_string_true_values(self):
        self.assertTrue(coerce_bool("true", False))
        self.assertTrue(coerce_bool("True", False))
        self.assertTrue(coerce_bool("TRUE", False))
        self.assertTrue(coerce_bool("1", False))
        self.assertTrue(coerce_bool("yes", False))
        self.assertTrue(coerce_bool("on", False))

    def test_string_false_values(self):
        self.assertFalse(coerce_bool("false", True))
        self.assertFalse(coerce_bool("False", True))
        self.assertFalse(coerce_bool("FALSE", True))
        self.assertFalse(coerce_bool("0", True))
        self.assertFalse(coerce_bool("no", True))
        self.assertFalse(coerce_bool("off", True))

    def test_numeric_values(self):
        self.assertTrue(coerce_bool(1, False))
        self.assertFalse(coerce_bool(0, True))
        self.assertTrue(coerce_bool(42, False))

    def test_none_returns_default(self):
        self.assertTrue(coerce_bool(None, True))
        self.assertFalse(coerce_bool(None, False))

    def test_invalid_string_returns_default(self):
        self.assertTrue(coerce_bool("invalid", True))
        self.assertFalse(coerce_bool("invalid", False))


class TestCoerceNonNegativeInt(unittest.TestCase):
    def test_valid_positive_int(self):
        self.assertEqual(coerce_non_negative_int(42, 0), 42)
        self.assertEqual(coerce_non_negative_int("100", 0), 100)

    def test_zero(self):
        self.assertEqual(coerce_non_negative_int(0, 10), 0)
        self.assertEqual(coerce_non_negative_int("0", 10), 0)

    def test_negative_clamped_to_zero(self):
        self.assertEqual(coerce_non_negative_int(-5, 0), 0)
        self.assertEqual(coerce_non_negative_int("-10", 0), 0)

    def test_invalid_returns_default(self):
        self.assertEqual(coerce_non_negative_int("invalid", 42), 42)
        self.assertEqual(coerce_non_negative_int(None, 42), 42)


class TestCoerceOptionalNonNegativeInt(unittest.TestCase):
    def test_valid_positive_int(self):
        self.assertEqual(coerce_optional_non_negative_int(42), 42)
        self.assertEqual(coerce_optional_non_negative_int("100"), 100)

    def test_zero(self):
        self.assertEqual(coerce_optional_non_negative_int(0), 0)

    def test_negative_returns_none(self):
        self.assertIsNone(coerce_optional_non_negative_int(-5))
        self.assertIsNone(coerce_optional_non_negative_int("-10"))

    def test_none_returns_none(self):
        self.assertIsNone(coerce_optional_non_negative_int(None))

    def test_invalid_returns_none(self):
        self.assertIsNone(coerce_optional_non_negative_int("invalid"))


class TestInferScriptMode(unittest.TestCase):
    def test_explicit_mode(self):
        self.assertEqual(infer_script_mode({"mode": "window"}), "window")
        self.assertEqual(infer_script_mode({"mode": "screen"}), "screen")

    def test_infer_from_window_positions(self):
        data = {"window_positions": [{"type": "click"}]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_infer_from_actions_with_win_title(self):
        data = {"actions": [{"type": "click", "x": 100, "y": 200, "win_title": "Notepad"}]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_target_windows_infers_window_mode(self):
        # Non-empty list of target_windows infers window mode
        data = {"target_windows": ["Notepad"]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_target_windows_empty_or_invalid_infers_screen(self):
        # Empty list or invalid types don't infer window mode
        self.assertEqual(infer_script_mode({"target_windows": []}), "screen")
        self.assertEqual(infer_script_mode({"target_windows": "Notepad"}), "screen")
        self.assertEqual(infer_script_mode({"target_windows": None}), "screen")

    def test_default_to_screen(self):
        self.assertEqual(infer_script_mode({}), "screen")

    def test_actions_without_win_title_defaults_to_screen(self):
        data = {"actions": [{"type": "click", "x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")


class TestIsPositionAction(unittest.TestCase):
    def test_click_is_position_action(self):
        self.assertTrue(is_position_action({"type": "click"}))

    def test_wheel_is_position_action(self):
        self.assertTrue(is_position_action({"type": "wheel"}))

    def test_wait_is_not_position_action(self):
        self.assertFalse(is_position_action({"type": "wait"}))

    def test_key_is_not_position_action(self):
        self.assertFalse(is_position_action({"type": "key"}))

    def test_default_type_is_click(self):
        self.assertTrue(is_position_action({}))


if __name__ == "__main__":
    unittest.main()
