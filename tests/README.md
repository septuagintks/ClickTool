# Click Tool Test Suite Documentation

This document describes the test suite structure and testing strategy for the Click Tool project.

## Test Structure

### Directory Layout
```
tests/
├── __init__.py
├── test_script.py           # Pure logic: config normalization, mode inference
├── test_hotkey.py           # Pure logic: hotkey parsing and formatting
├── test_window.py           # Platform-dependent: window resolution (requires pywin32)
├── test_auto.py             # Platform-dependent: auto-run entry point (requires Windows)
├── test_audit_regression.py # Regression tests for fixed bugs
└── test_smoke.py            # Basic sanity checks
```

## Test Categories

### 1. Pure Logic Tests (Platform-Independent)
**Files:** `test_script.py`, `test_hotkey.py`

These tests verify core algorithms that don't depend on Windows APIs:
- Configuration normalization (`normalize_script_data`)
- Mode inference (`infer_script_mode`)
- Boolean coercion (`coerce_bool`)
- Hotkey text formatting (`normalize_hotkey_text`)
- Action validation

**Run on:** Any platform with Python 3.x

### 2. Platform-Dependent Tests
**Files:** `test_window.py`, `test_auto.py`

These tests require Windows and pywin32:
- Window handle resolution
- Auto-run execution flow
- Windows API interactions

**Protection:** Use `@unittest.skipIf(sys.platform != "win32", "Windows-only")` or `@unittest.skipUnless(PYWIN32_AVAILABLE, "pywin32 not installed")`

### 3. Audit Regression Tests
**File:** `test_audit_regression.py`

Tests for historically fixed bugs to prevent regression. Each test documents:
- The original bug
- The fix that was applied
- The verification that ensures it stays fixed

**Critical bugs covered:**
- `target_windows` string type trap (caused exit 3)
- `pure_background_window_click` string "false" treated as truthy
- Actions with `win_title` not inferring window mode
- Non-dict actions causing crashes
- Hotkey conflicts clearing UI state

### 4. Smoke Tests
**File:** `test_smoke.py`

Fast sanity checks to catch obvious breakage:
- Import tests (no circular dependencies)
- Syntax validation (all .py files compile)
- CLI error handling (nonexistent config, invalid JSON)
- Dependency availability (pywin32, ctypes)
- Basic config normalization

## Running Tests

### Quick Run (All Tests)
```bash
run_tests.bat
```

### Manual Run with pytest
```bash
# Activate venv
.venv\Scripts\activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_audit_regression.py -v

# Run specific test class
pytest tests/test_audit_regression.py::TestAuditRegression -v

# Run specific test method
pytest tests/test_audit_regression.py::TestAuditRegression::test_target_windows_string_type_trap -v
```

### Run Only Pure Logic Tests (Platform-Independent)
```bash
pytest tests/test_script.py tests/test_hotkey.py -v
```

### Run Only Smoke Tests
```bash
pytest tests/test_smoke.py -v
```

## Test Development Guidelines

### When to Add Tests

1. **Before fixing a bug:** Write a failing test that reproduces the bug
2. **After fixing a bug:** Ensure the test passes and add it to audit regression
3. **When adding a feature:** Write tests for the new behavior
4. **When refactoring:** Ensure existing tests still pass

### Test Naming Conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Feature>` (e.g., `TestAuditRegression`)
- Test methods: `test_<what_it_tests>` (e.g., `test_target_windows_string_type_trap`)

### Writing Good Tests

1. **One assertion per concept:** Test one thing at a time
2. **Clear failure messages:** Use descriptive assertion messages
3. **Document the why:** Add docstrings explaining what bug/feature is being tested
4. **Use subTest for variations:** When testing multiple similar cases
5. **Mock external dependencies:** Use `unittest.mock.patch` for Windows APIs in unit tests

### Platform-Dependent Test Pattern

```python
import sys
import unittest

@unittest.skipIf(sys.platform != "win32", "Windows-only tests")
class TestWindowsFeature(unittest.TestCase):
    def test_something(self):
        # Test code that requires Windows
        pass
```

Or for optional dependencies:

```python
try:
    from clicktool.window import some_function
    DEPENDENCY_AVAILABLE = True
except ImportError:
    DEPENDENCY_AVAILABLE = False

@unittest.skipUnless(DEPENDENCY_AVAILABLE, "Dependency not installed")
class TestOptionalFeature(unittest.TestCase):
    def test_something(self):
        # Test code that requires the dependency
        pass
```

## Coverage Goals

### Current Coverage Areas
- ✅ Configuration normalization
- ✅ Mode inference (all paths)
- ✅ Boolean coercion
- ✅ Hotkey formatting
- ✅ Window resolution logic
- ✅ Auto-run execution flow
- ✅ Historical bug regression

### Not Covered (Manual Testing)
- ❌ GUI rendering (tkinter UI)
- ❌ Actual mouse/keyboard input
- ❌ Real window interaction
- ❌ Global hotkey registration

These require manual testing or integration tests with real Windows environment.

## Continuous Integration

The test suite is designed to work in CI environments:

1. **Fast feedback:** Smoke tests run first (< 5 seconds)
2. **Platform detection:** Tests skip gracefully on non-Windows
3. **Dependency isolation:** Tests don't require GUI or user interaction
4. **Clear exit codes:** Non-zero exit on any failure

## Troubleshooting

### "pywin32 not installed" errors
```bash
pip install -r requirements-dev.txt
```

### "Module not found" errors
Ensure you're in the project root and venv is activated:
```bash
cd "E:\AMLY\works\python works\click-tool"
.venv\Scripts\activate
```

### Tests hang or timeout
Check for:
- Infinite loops in test code
- Missing mocks for blocking operations
- Real Windows API calls that wait for user input

### Import errors in tests
Verify the project structure:
```
click-tool/
├── clicktool/        # Package directory
│   ├── __init__.py
│   ├── script.py
│   └── ...
├── clicktool.py      # Entry point
└── tests/            # Test directory
    └── ...
```

## Future Enhancements

1. **Coverage reporting:** Add pytest-cov for coverage metrics
2. **Performance tests:** Add benchmarks for critical paths
3. **Integration tests:** Add end-to-end tests with real configs
4. **Mutation testing:** Use mutmut to verify test quality
5. **Property-based testing:** Use hypothesis for edge case discovery
