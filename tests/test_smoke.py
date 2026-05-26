"""
Smoke Tests for Minified Branch

Basic sanity checks to ensure the project is in a runnable state.
These tests should be fast and catch obvious breakage.

CRITICAL: These tests verify ZERO runtime dependencies.
"""

import unittest
import sys
import os
import tempfile
import json


class TestZeroRuntimeDependencies(unittest.TestCase):
    """Verify that the minified branch has zero runtime dependencies."""

    def test_no_pywin32_import(self):
        """Ensure pywin32 is NOT imported in source code."""
        clicktool_min_dir = os.path.join(os.path.dirname(__file__), "..", "clicktool_min")
        if not os.path.exists(clicktool_min_dir):
            self.skipTest("clicktool_min directory not found")

        forbidden_imports = ["win32api", "win32con", "win32gui", "pywintypes"]

        for filename in os.listdir(clicktool_min_dir):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(clicktool_min_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            for forbidden in forbidden_imports:
                with self.subTest(file=filename, import_name=forbidden):
                    self.assertNotIn(f"import {forbidden}", content,
                                   f"{filename} imports {forbidden} - violates zero dependency rule")
                    self.assertNotIn(f"from {forbidden}", content,
                                   f"{filename} imports from {forbidden} - violates zero dependency rule")

    def test_ctypes_only_for_windows_api(self):
        """Verify that only ctypes (stdlib) is used for Windows API."""
        clicktool_min_dir = os.path.join(os.path.dirname(__file__), "..", "clicktool_min")
        if not os.path.exists(clicktool_min_dir):
            self.skipTest("clicktool_min directory not found")

        # winapi.py should use ctypes
        winapi_path = os.path.join(clicktool_min_dir, "winapi.py")
        if os.path.exists(winapi_path):
            with open(winapi_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("from ctypes", content, "winapi.py should use ctypes")
            self.assertIn("windll", content, "winapi.py should use ctypes.windll")


class TestImportSmoke(unittest.TestCase):
    """Test that all modules can be imported without errors."""

    def test_import_main_module(self):
        """Main clicktoolm.py should be importable."""
        try:
            import clicktoolm
        except ImportError as e:
            self.fail(f"Failed to import clicktoolm: {e}")

    def test_import_script_module(self):
        """clicktool_min.script should be importable."""
        try:
            from clicktool_min import script
        except ImportError as e:
            self.fail(f"Failed to import clicktool_min.script: {e}")

    def test_import_window_module(self):
        """clicktool_min.window should be importable."""
        try:
            from clicktool_min import window
        except ImportError as e:
            self.fail(f"Failed to import clicktool_min.window: {e}")

    def test_import_hotkey_module(self):
        """clicktool_min.hotkey should be importable."""
        try:
            from clicktool_min import hotkey
        except ImportError as e:
            self.fail(f"Failed to import clicktool_min.hotkey: {e}")

    def test_import_winapi_module(self):
        """clicktool_min.winapi should be importable."""
        try:
            from clicktool_min import winapi
        except ImportError as e:
            self.fail(f"Failed to import clicktool_min.winapi: {e}")

    def test_no_circular_imports(self):
        """Verify no circular import issues."""
        try:
            from clicktool_min import script, window, hotkey, winapi, ui
        except ImportError as e:
            self.fail(f"Circular import or missing dependency detected: {e}")


class TestSyntaxSmoke(unittest.TestCase):
    """Test that all Python files have valid syntax."""

    def test_main_file_syntax(self):
        """clicktoolm.py should have valid syntax."""
        import py_compile
        try:
            py_compile.compile("clicktoolm.py", doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in clicktoolm.py: {e}")

    def test_all_module_files_syntax(self):
        """All .py files in clicktool_min/ should have valid syntax."""
        import py_compile
        clicktool_min_dir = os.path.join(os.path.dirname(__file__), "..", "clicktool_min")
        if not os.path.exists(clicktool_min_dir):
            self.skipTest("clicktool_min directory not found")

        for filename in os.listdir(clicktool_min_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(clicktool_min_dir, filename)
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
        result = subprocess.run(
            [sys.executable, "clicktoolm.py", "auto", "nonexistent_config.json"],
            capture_output=True,
            timeout=5
        )
        # Should exit with error code (not 0)
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_json_config_returns_error(self):
        """Running with invalid JSON should return error exit code."""
        import subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "clicktoolm.py", "auto", temp_path],
                capture_output=True,
                timeout=5
            )
            # Should exit with error code
            self.assertNotEqual(result.returncode, 0)
        finally:
            os.unlink(temp_path)


class TestDependencySmoke(unittest.TestCase):
    """Test that required dependencies are available."""

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

    def test_no_external_dependencies_in_stdlib(self):
        """Verify all imports are from stdlib or local modules."""
        import sys
        import importlib

        # Import all modules
        from clicktool_min import script, window, hotkey, winapi

        # Check that no third-party packages are loaded
        third_party_packages = []
        for module_name in sys.modules:
            # Skip builtins, stdlib, and our own modules
            if module_name.startswith(('_', 'clicktool_min', 'tests')):
                continue
            if '.' in module_name:
                root = module_name.split('.')[0]
            else:
                root = module_name

            # Check if it's a stdlib module
            try:
                spec = importlib.util.find_spec(root)
                if spec and spec.origin:
                    # Stdlib modules are in Python's lib directory
                    if 'site-packages' in spec.origin:
                        third_party_packages.append(root)
            except (ImportError, AttributeError, ValueError):
                pass

        # Filter out pytest and test-related packages
        third_party_packages = [p for p in third_party_packages
                               if not p.startswith(('pytest', '_pytest', 'pluggy', 'py'))]

        if third_party_packages:
            self.fail(f"Third-party packages detected: {third_party_packages}")


class TestConfigValidationSmoke(unittest.TestCase):
    """Test basic config validation."""

    def test_infer_mode_minimal_config(self):
        """infer_script_mode should handle minimal config."""
        from clicktool_min.script import infer_script_mode
        data = {"actions": []}
        try:
            result = infer_script_mode(data)
            self.assertIn(result, ["screen", "window"])
        except Exception as e:
            self.fail(f"infer_script_mode failed on minimal config: {e}")

    def test_infer_mode_preserves_valid_data(self):
        """infer_script_mode should work with valid data."""
        from clicktool_min.script import infer_script_mode
        data = {
            "mode": "screen",
            "actions": [{"type": "click", "x": 100, "y": 200}]
        }
        result = infer_script_mode(data)
        self.assertEqual(result, "screen")


if __name__ == "__main__":
    unittest.main()
