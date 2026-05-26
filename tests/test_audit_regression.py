"""
Audit Regression Tests

This module contains tests for historically fixed bugs to prevent regression.
Each test documents the original issue and verifies the fix remains in place.
"""

import unittest
from clicktool.script import (
    infer_script_mode,
    normalize_script_data,
    coerce_bool,
)


class TestAuditRegression(unittest.TestCase):
    """Tests for fixed bugs that must never regress."""

    def test_target_windows_string_type_trap(self):
        """
        Bug: target_windows: "Notepad" (string instead of list) was incorrectly
        triggering window mode, then normalized to empty list, causing exit 3.

        Fix: infer_script_mode now validates target_windows is a non-empty list.
        """
        # String type should not trigger window mode
        data = {"target_windows": "Notepad", "screen_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")

        # None should not trigger window mode
        data = {"target_windows": None, "screen_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")

        # Empty list should not trigger window mode
        data = {"target_windows": [], "screen_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")

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

    def test_pure_background_normalized_in_script_data(self):
        """
        Bug: pure_background_window_click was not coerced during normalization,
        allowing string values to pass through to execution layer.

        Fix: normalize_script_data now always coerces pure_background_window_click.
        """
        data = {
            "settings": {
                "pure_background_window_click": "false"
            }
        }
        normalized = normalize_script_data(data)
        # Should be coerced to boolean False, not string "false"
        self.assertIsInstance(normalized["settings"]["pure_background_window_click"], bool)
        self.assertFalse(normalized["settings"]["pure_background_window_click"])

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
        # Should not crash during normalization
        try:
            normalized = normalize_script_data(data)
            # Valid actions should be preserved
            self.assertIsInstance(normalized["actions"], list)
        except Exception as e:
            self.fail(f"normalize_script_data crashed with non-dict actions: {e}")

    def test_target_windows_with_actions_infers_window(self):
        """
        Bug: Configs with target_windows + actions (no window_positions) were
        misidentified as screen mode.

        Fix: infer_script_mode now checks target_windows in addition to window_positions.
        """
        data = {
            "target_windows": ["Notepad"],
            "actions": [
                {"type": "click", "x": 100, "y": 200}
            ]
        }
        self.assertEqual(infer_script_mode(data), "window")

    def test_single_target_window_auto_fills_win_title(self):
        """
        Bug: Actions without win_title in single-window configs caused exit 3
        because no hwnd could be resolved.

        Fix: When only one target_window exists, actions auto-fill win_title.
        Note: This is tested at the execution layer, here we verify the inference.
        """
        # Single target window should infer window mode
        data = {
            "target_windows": ["Notepad"],
            "actions": [{"type": "click", "x": 100, "y": 200}]
        }
        self.assertEqual(infer_script_mode(data), "window")

    def test_window_client_area_only_migration(self):
        """
        Bug: Old field window_client_area_only was not migrated to
        pure_background_window_click during normalization.

        Fix: normalize_script_data migrates the old field and removes it.
        """
        data = {
            "settings": {
                "window_client_area_only": True
            }
        }
        normalized = normalize_script_data(data)
        # Old field should be removed
        self.assertNotIn("window_client_area_only", normalized["settings"])
        # New field should be set with inverted value
        self.assertIn("pure_background_window_click", normalized["settings"])
        self.assertTrue(normalized["settings"]["pure_background_window_click"])


class TestModeInferenceEdgeCases(unittest.TestCase):
    """Edge cases for mode inference logic."""

    def test_explicit_mode_overrides_all_inference(self):
        """Explicit mode field should always take precedence."""
        # Explicit screen mode even with window_positions
        data = {"mode": "screen", "window_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "screen")

        # Explicit window mode even with no window indicators
        data = {"mode": "window", "screen_positions": [{"x": 100, "y": 200}]}
        self.assertEqual(infer_script_mode(data), "window")

    def test_window_positions_takes_precedence_over_target_windows(self):
        """window_positions is checked before target_windows."""
        data = {
            "window_positions": [{"x": 100, "y": 200}],
            "target_windows": []  # Empty, but window_positions exists
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


if __name__ == "__main__":
    unittest.main()
