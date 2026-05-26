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

    def test_no_pywin32_import_via_ast(self):
        """Ensure pywin32 is NOT imported in source code using AST parsing."""
        import ast
        clicktool_min_dir = os.path.join(os.path.dirname(__file__), "..", "clicktool_min")
        if not os.path.exists(clicktool_min_dir):
            self.skipTest("clicktool_min directory not found")

        forbidden_modules = ["win32api", "win32con", "win32gui", "pywintypes"]

        for filename in os.listdir(clicktool_min_dir):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(clicktool_min_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read(), filename=filename)
                except SyntaxError:
                    continue  # Skip files with syntax errors

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        with self.subTest(file=filename, import_type="import", module=alias.name):
                            self.assertNotIn(alias.name, forbidden_modules,
                                           f"{filename} imports {alias.name} - violates zero dependency rule")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        with self.subTest(file=filename, import_type="from", module=node.module):
                            self.assertNotIn(node.module, forbidden_modules,
                                           f"{filename} imports from {node.module} - violates zero dependency rule")

    def test_clean_subprocess_import(self):
        """Verify modules can be imported in a clean subprocess without external dependencies."""
        import subprocess
        # Use -S to skip site-packages, ensuring only stdlib is available
        result = subprocess.run(
            [sys.executable, "-S", "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from clicktool_min import script, window, hotkey, winapi"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            self.fail(f"Failed to import clicktool_min in clean subprocess:\n"
                     f"stdout: {result.stdout.decode()}\n"
                     f"stderr: {result.stderr.decode()}")

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
        # Use isolated temp directory to avoid real user logs/locks
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env['LOCALAPPDATA'] = tmpdir
            result = subprocess.run(
                [sys.executable, "clicktoolm.py", "--auto", "--config", "nonexistent_config.json"],
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
                    [sys.executable, "clicktoolm.py", "--auto", "--config", temp_path],
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
                    [sys.executable, "clicktoolm.py", "--auto", "--config", temp_path],
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
