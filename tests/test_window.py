"""Unit tests for clicktool.window module."""
import unittest

try:
    from clicktool.window import resolve_hwnd_by_title
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


@unittest.skipUnless(PYWIN32_AVAILABLE, "pywin32 not installed")
class TestResolveHwndByTitle(unittest.TestCase):
    def test_exact_match(self):
        active_windows = [(100, "Notepad"), (200, "Chrome"), (300, "VS Code")]
        hwnd = resolve_hwnd_by_title("Chrome", active_windows)
        self.assertEqual(hwnd, 200)

    def test_substring_match(self):
        active_windows = [(100, "Untitled - Notepad"), (200, "Google Chrome"), (300, "VS Code")]
        hwnd = resolve_hwnd_by_title("Chrome", active_windows)
        self.assertEqual(hwnd, 200)

    def test_case_insensitive_substring(self):
        active_windows = [(100, "Untitled - Notepad"), (200, "Google Chrome")]
        hwnd = resolve_hwnd_by_title("chrome", active_windows)
        self.assertEqual(hwnd, 200)

    def test_no_match_returns_none(self):
        active_windows = [(100, "Notepad"), (200, "Chrome")]
        hwnd = resolve_hwnd_by_title("Firefox", active_windows)
        self.assertIsNone(hwnd)

    def test_empty_title_returns_none(self):
        active_windows = [(100, "Notepad")]
        hwnd = resolve_hwnd_by_title("", active_windows)
        self.assertIsNone(hwnd)

    def test_none_title_returns_none(self):
        active_windows = [(100, "Notepad")]
        hwnd = resolve_hwnd_by_title(None, active_windows)
        self.assertIsNone(hwnd)

    def test_exact_match_preferred_over_substring(self):
        active_windows = [(100, "Chrome"), (200, "Google Chrome")]
        hwnd = resolve_hwnd_by_title("Chrome", active_windows)
        self.assertEqual(hwnd, 100)  # Exact match wins


if __name__ == "__main__":
    unittest.main()
