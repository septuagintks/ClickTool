"""Unit tests for clicktool.hotkey module."""
import unittest
from clicktool.hotkey import normalize_hotkey_text, hotkey_from_event


class TestNormalizeHotkeyText(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(normalize_hotkey_text(""), "")
        self.assertEqual(normalize_hotkey_text("   "), "")

    def test_single_key(self):
        self.assertEqual(normalize_hotkey_text("a"), "A")
        self.assertEqual(normalize_hotkey_text("F1"), "F1")

    def test_modifier_plus_key(self):
        self.assertEqual(normalize_hotkey_text("ctrl+a"), "Ctrl+A")
        self.assertEqual(normalize_hotkey_text("SHIFT+F5"), "Shift+F5")
        self.assertEqual(normalize_hotkey_text("alt+tab"), "Alt+Tab")

    def test_multiple_modifiers(self):
        self.assertEqual(normalize_hotkey_text("ctrl+shift+a"), "Ctrl+Shift+A")
        self.assertEqual(normalize_hotkey_text("ctrl+alt+delete"), "Ctrl+Alt+Delete")

    def test_whitespace_handling(self):
        self.assertEqual(normalize_hotkey_text(" ctrl + a "), "Ctrl+A")
        self.assertEqual(normalize_hotkey_text("ctrl  +  shift  +  f"), "Ctrl+Shift+F")

    def test_case_insensitive(self):
        self.assertEqual(normalize_hotkey_text("CTRL+ALT+A"), "Ctrl+Alt+A")
        # Note: "Escape" is canonicalized to "Esc" by the hotkey system
        self.assertEqual(normalize_hotkey_text("shift+esc"), "Shift+Esc")


class TestHotkeyFromEvent(unittest.TestCase):
    def test_single_key(self):
        class MockEvent:
            keysym = "a"
            state = 0
        self.assertEqual(hotkey_from_event(MockEvent()), "A")

    def test_ctrl_modifier(self):
        class MockEvent:
            keysym = "a"
            state = 0x4  # Control
        self.assertEqual(hotkey_from_event(MockEvent()), "Ctrl+A")

    def test_shift_modifier(self):
        class MockEvent:
            keysym = "f"
            state = 0x1  # Shift
        self.assertEqual(hotkey_from_event(MockEvent()), "Shift+F")

    def test_alt_modifier(self):
        class MockEvent:
            keysym = "tab"
            state = 0x8  # Alt (not 0x20000)
        self.assertEqual(hotkey_from_event(MockEvent()), "Alt+Tab")

    def test_multiple_modifiers(self):
        class MockEvent:
            keysym = "delete"
            state = 0x4 | 0x8  # Ctrl+Alt
        self.assertEqual(hotkey_from_event(MockEvent()), "Ctrl+Alt+Delete")


if __name__ == "__main__":
    unittest.main()
