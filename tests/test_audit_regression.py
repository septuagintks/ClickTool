"""
Audit Regression Tests for Minified Branch

This module contains tests for historically fixed bugs to prevent regression.
Each test documents the original issue and verifies the fix remains in place.

Note: These tests are adapted for the minified branch which uses ctypes instead of pywin32.
"""

import unittest
from clicktool_min.script import (
    infer_script_mode,
    coerce_bool,
)


class TestAuditRegression(unittest.TestCase):
    """Tests for fixed bugs that must never regress."""

    def test_actions_with_win_title_infers_window_mode(self):
        """
        Bug: Configs with only unified actions containing win_title were
        misidentified as screen mode, causing window clicks to execute as screen clicks.

        Fix: infer_script_mode now scans actions for win_title field.
        """
        data = {
            "actions": [
                {"type": "click", "x": 100, "y": 200, "win_title": "Notepad"},
                {"type": "click", "x": 300, "y": 400, "win_title": "Notepad"}
            ]
        }
        self.assertEqual(infer_script_mode(data), "window")

    def test_pure_background_window_click_string_false_coercion(self):
        """
        Bug: pure_background_window_click: "false" (string) was treated as truthy,
        causing the setting to be enabled when it should be disabled.

        Fix: coerce_bool now properly converts string "false" to False.
        """
        # String "false" should coerce to False
        self.assertFalse(coerce_bool("false", True))
        self.assertFalse(coerce_bool("False", True))
        self.assertFalse(coerce_bool("FALSE", True))
        self.assertFalse(coerce_bool("0", True))

        # String "true" should coerce to True
        self.assertTrue(coerce_bool("true", False))
        self.assertTrue(coerce_bool("True", False))
        self.assertTrue(coerce_bool("TRUE", False))
        self.assertTrue(coerce_bool("1", False))

    def test_non_dict_action_does_not_crash(self):
        """
        Bug: Non-dict actions in the actions list could cause crashes during iteration.

        Fix: Action processing now validates each action is a dict before accessing fields.
        """
        data = {
            "actions": [
                {"type": "click", "x": 100, "y": 200},
                "invalid_string_action",
                None,
                123,
                {"type": "click", "x": 300, "y": 400}
            ]
        }
        # Should not crash during mode inference
        try:
            mode = infer_script_mode(data)
            # Should default to screen since no valid win_title found
            self.assertEqual(mode, "screen")
        except Exception as e:
            self.fail(f"infer_script_mode crashed with non-dict actions: {e}")


class TestModeInferenceEdgeCases(unittest.TestCase):
    """Edge cases for mode inference logic."""

    def test_explicit_mode_overrides_all_inference(self):
        """Explicit mode field should always take precedence."""
        # Explicit screen mode even with window_positions
        data = {"mode": "screen", "window_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")

        # Explicit window mode even with no window indicators
        data = {"mode": "window", "actions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_window_positions_takes_precedence(self):
        """window_positions is checked before actions."""
        data = {
            "window_positions": [{"x": 100, "y": 200}],
            "actions": [{"x": 300, "y": 400}]  # No win_title
        }
        self.assertEqual(infer_script_mode(data), "window")

    def test_mixed_actions_with_and_without_win_title(self):
        """Actions with at least one win_title should infer window mode."""
        data = {
            "actions": [
                {"type": "click", "x": 100, "y": 200},  # No win_title
                {"type": "click", "x": 300, "y": 400, "win_title": "Notepad"},  # Has win_title
                {"type": "wait", "ms": 1000}  # Wait action
            ]
        }
        self.assertEqual(infer_script_mode(data), "window")

    def test_empty_actions_defaults_to_screen(self):
        """Empty actions list should default to screen mode."""
        self.assertEqual(infer_script_mode({"actions": []}), "screen")

    def test_actions_not_list_defaults_to_screen(self):
        """Non-list actions should default to screen mode."""
        self.assertEqual(infer_script_mode({"actions": "invalid"}), "screen")
        self.assertEqual(infer_script_mode({"actions": None}), "screen")


class TestBooleanCoercionEdgeCases(unittest.TestCase):
    """Edge cases for boolean coercion."""

    def test_whitespace_in_string_values(self):
        """Whitespace should be stripped before evaluation."""
        self.assertTrue(coerce_bool("  true  ", False))
        self.assertFalse(coerce_bool("  false  ", True))
        self.assertTrue(coerce_bool("\ttrue\n", False))

    def test_mixed_case_variations(self):
        """All case variations should work."""
        for val in ["true", "True", "TRUE", "tRuE"]:
            self.assertTrue(coerce_bool(val, False), f"Failed for: {val}")
        for val in ["false", "False", "FALSE", "fAlSe"]:
            self.assertFalse(coerce_bool(val, True), f"Failed for: {val}")

    def test_numeric_zero_and_one(self):
        """Numeric 0 and 1 should work as bool."""
        self.assertFalse(coerce_bool(0, True))
        self.assertTrue(coerce_bool(1, False))
        self.assertFalse(coerce_bool(0.0, True))
        self.assertTrue(coerce_bool(1.0, False))

    def test_non_zero_numbers_are_truthy(self):
        """Non-zero numbers should be truthy."""
        self.assertTrue(coerce_bool(42, False))
        self.assertTrue(coerce_bool(-1, False))
        self.assertTrue(coerce_bool(3.14, False))


if __name__ == "__main__":
    unittest.main()
