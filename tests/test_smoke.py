"""
Smoke Tests

Basic sanity checks to ensure the project is in a runnable state.
These tests should be fast and catch obvious breakage.
"""

import unittest
import sys
import os
import tempfile
import json
import importlib.util


class TestImportSmoke(unittest.TestCase):
    """Test that all modules can be imported without errors."""

    def test_import_entry_point(self):
        """Entry point clicktool.py should be importable."""
        try:
            spec = importlib.util.spec_from_file_location("clicktool_entry", "clicktool.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            self.fail(f"Failed to import clicktool.py entry point: {e}")

    def test_import_script_module(self):
        """clicktool.script should be importable."""
        try:
            from clicktool import script
        except ImportError as e:
            self.fail(f"Failed to import clicktool.script: {e}")

    def test_import_window_module(self):
        """clicktool.window should be importable."""
        try:
            from clicktool import window
        except ImportError as e:
            self.fail(f"Failed to import clicktool.window: {e}")

    def test_import_hotkey_module(self):
        """clicktool.hotkey should be importable."""
        try:
            from clicktool import hotkey
        except ImportError as e:
            self.fail(f"Failed to import clicktool.hotkey: {e}")

    def test_no_circular_imports(self):
        """Verify no circular import issues."""
        try:
            from clicktool import script, window, hotkey, ui
        except ImportError as e:
            self.fail(f"Circular import or missing dependency detected: {e}")


class TestSyntaxSmoke(unittest.TestCase):
    """Test that all Python files have valid syntax."""

    def test_main_file_syntax(self):
        """clicktool.py should have valid syntax."""
        import py_compile
        try:
            py_compile.compile("clicktool.py", doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in clicktool.py: {e}")

    def test_all_module_files_syntax(self):
        """All .py files in clicktool/ should have valid syntax."""
        import py_compile
        clicktool_dir = os.path.join(os.path.dirname(__file__), "..", "clicktool")
        if not os.path.exists(clicktool_dir):
            self.skipTest("clicktool directory not found")

        for filename in os.listdir(clicktool_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(clicktool_dir, filename)
                with self.subTest(file=filename):
                    try:
                        py_compile.compile(filepath, doraise=True)
                    except py_compile.PyCompileError as e:
                        self.fail(f"Syntax error in {filename}: {e}")


class TestCLISmoke(unittest.TestCase):
    """Test basic CLI functionality."""

    def test_nonexistent_config_returns_error(self):
        """Running with nonexistent config should return error exit code."""
        import subprocess
        # Use isolated temp directory to avoid real user logs/locks
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env['LOCALAPPDATA'] = tmpdir
            result = subprocess.run(
                [sys.executable, "clicktool.py", "--auto", "--config", "nonexistent_config.json"],
                capture_output=True,
                timeout=5,
                env=env
            )
            # Should exit with error code 2 (file not found)
            self.assertEqual(result.returncode, 2)

    def test_invalid_json_config_returns_error(self):
        """Running with invalid JSON should return error exit code."""
        import subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                env = os.environ.copy()
                env['LOCALAPPDATA'] = tmpdir
                result = subprocess.run(
                    [sys.executable, "clicktool.py", "--auto", "--config", temp_path],
                    capture_output=True,
                    timeout=5,
                    env=env
                )
                # Should exit with error code 2 (JSON decode error)
                self.assertEqual(result.returncode, 2)
        finally:
            os.unlink(temp_path)

    def test_empty_config_returns_error(self):
        """Running with empty config should return error exit code."""
        import subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                env = os.environ.copy()
                env['LOCALAPPDATA'] = tmpdir
                result = subprocess.run(
                    [sys.executable, "clicktool.py", "--auto", "--config", temp_path],
                    capture_output=True,
                    timeout=5,
                    env=env
                )
                # Should exit with error code 3 (no runnable actions)
                self.assertEqual(result.returncode, 3)
        finally:
            os.unlink(temp_path)


class TestDependencySmoke(unittest.TestCase):
    """Test that required dependencies are available."""

    @unittest.skipIf(sys.platform != "win32", "Windows-only dependency")
    def test_pywin32_available(self):
        """pywin32 should be available on Windows."""
        try:
            import win32api
            import win32con
            import win32gui
        except ImportError as e:
            self.fail(f"pywin32 not available: {e}")

    @unittest.skipIf(sys.platform != "win32", "Windows-only dependency")
    def test_ctypes_windll_available(self):
        """ctypes.windll should be available on Windows."""
        try:
            from ctypes import windll
            # Try accessing user32
            user32 = windll.user32
            self.assertIsNotNone(user32)
        except Exception as e:
            self.fail(f"ctypes.windll not available: {e}")


class TestConfigValidationSmoke(unittest.TestCase):
    """Test basic config validation."""

    def test_normalize_minimal_config(self):
        """normalize_script_data should handle minimal config."""
        from clicktool.script import normalize_script_data
        data = {"actions": []}
        try:
            result = normalize_script_data(data)
            self.assertIsInstance(result, dict)
            self.assertIn("settings", result)
        except Exception as e:
            self.fail(f"normalize_script_data failed on minimal config: {e}")

    def test_normalize_preserves_valid_data(self):
        """normalize_script_data should preserve valid data."""
        from clicktool.script import normalize_script_data
        data = {
            "mode": "screen",
            "actions": [{"type": "click", "x": 100, "y": 200}],
            "settings": {"pure_background_window_click": False}
        }
        result = normalize_script_data(data)
        self.assertEqual(result["mode"], "screen")
        self.assertEqual(len(result["actions"]), 1)
        self.assertFalse(result["settings"]["pure_background_window_click"])


if __name__ == "__main__":
    unittest.main()
