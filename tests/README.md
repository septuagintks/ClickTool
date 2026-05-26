# Click Tool Minified Test Suite Documentation

This document describes the test suite structure and testing strategy for the Click Tool Minified branch.

## Critical Principle: ZERO Runtime Dependencies

**The minified branch has ZERO runtime dependencies.** All Windows API interactions use `ctypes` (Python stdlib), not `pywin32`.

- ✅ Runtime: Pure Python + ctypes
- ✅ Testing: pytest (dev-only)
- ❌ Never import: pywin32, win32api, win32con, win32gui

## Test Structure

### Directory Layout
```
click-tool-minified-dev/
├── clicktool_min/           # Source code (ZERO dependencies)
│   ├── __init__.py
│   ├── script.py
│   ├── hotkey.py
│   ├── window.py
│   ├── winapi.py           # ctypes-based Windows API
│   ├── ui.py
│   └── paths.py
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_script.py      # Pure logic tests
│   ├── test_hotkey.py      # Pure logic tests
│   ├── test_audit_regression.py  # Regression tests
│   ├── test_smoke.py       # Smoke tests + zero-dependency verification
│   └── README.md           # This file
├── clicktoolm.py            # Entry point
├── requirements.txt         # EMPTY (zero runtime dependencies)
├── requirements-dev.txt     # pytest (dev-only)
└── run_tests.bat            # One-click test runner
```

## Test Categories

### 1. Pure Logic Tests (Platform-Independent)
**Files:** `test_script.py`, `test_hotkey.py`

These tests verify core algorithms that don't depend on Windows APIs:
- Configuration mode inference (`infer_script_mode`)
- Boolean coercion (`coerce_bool`)
- Integer coercion (`coerce_non_negative_int`, `coerce_optional_non_negative_int`)
- Hotkey text formatting (`normalize_hotkey_text`)
- Action type validation (`is_position_action`)

**Run on:** Any platform with Python 3.x

### 2. Audit Regression Tests
**File:** `test_audit_regression.py`

Tests for historically fixed bugs to prevent regression:
- Actions with `win_title` inferring window mode
- String "false" coercing to boolean False
- Non-dict actions not causing crashes
- Mode inference edge cases
- Boolean coercion edge cases

**Adapted from main branch:** These tests focus on pure logic that applies to both branches.

### 3. Smoke Tests + Zero-Dependency Verification
**File:** `test_smoke.py`

Fast sanity checks with **critical zero-dependency verification**:

#### Zero-Dependency Tests (CRITICAL)
- ✅ No pywin32 imports in source code
- ✅ Only ctypes used for Windows API
- ✅ No third-party packages loaded at runtime

#### Standard Smoke Tests
- Import tests (no circular dependencies)
- Syntax validation (all .py files compile)
- CLI error handling (nonexistent config, invalid JSON)
- Dependency availability (ctypes.windll)
- Basic config validation

## Running Tests

### Quick Run (All Tests)
```bash
run_tests.bat
```

This script:
1. Activates `.venv`
2. Checks pytest installation
3. **Verifies zero runtime dependencies**
4. Runs pytest with verbose output

### Manual Run with pytest
```bash
# Activate venv
.venv\Scripts\activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_smoke.py -v

# Run zero-dependency verification only
pytest tests/test_smoke.py::TestZeroRuntimeDependencies -v

# Run pure logic tests only
pytest tests/test_script.py tests/test_hotkey.py -v

# Run audit regression tests
pytest tests/test_audit_regression.py -v
```

## Setting Up Development Environment

### First-Time Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dev dependencies (pytest ONLY)
pip install -r requirements-dev.txt
```

### Verify Zero Dependencies
```bash
# This should work WITHOUT installing anything beyond stdlib
python -c "from clicktool_min import script, window, hotkey, winapi"
```

If this fails, the zero-dependency principle is violated.

## Test Development Guidelines

### Critical Rules for Minified Branch

1. **Never import pywin32 in source code**
   - Use `ctypes.windll` instead
   - All Windows API calls go through `winapi.py`

2. **Tests can use pytest, source cannot**
   - pytest is a dev dependency, not runtime
   - Source code must run on bare Python + stdlib

3. **Keep tests pure logic focused**
   - No real Windows API calls in unit tests
   - Mock Windows API interactions if needed
   - Focus on algorithm correctness

### Writing Tests

Same guidelines as main branch, but with extra focus on:
- Verifying no external dependencies
- Testing ctypes-based implementations
- Ensuring cross-platform test skipping

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

## Differences from Main Branch

| Aspect | Main Branch | Minified Branch |
|--------|-------------|-----------------|
| **Runtime Deps** | pywin32 | ZERO (ctypes only) |
| **Windows API** | win32api, win32gui | ctypes.windll |
| **Source Dir** | `clicktool/` | `clicktool_min/` |
| **Entry Point** | `clicktool.py` | `clicktoolm.py` |
| **Test Focus** | Full coverage | Pure logic + zero-dep verification |
| **requirements.txt** | `pywin32>=305` | Empty (comment only) |

## Coverage Goals

### Current Coverage Areas
- ✅ Configuration mode inference
- ✅ Boolean and integer coercion
- ✅ Hotkey formatting
- ✅ Action type validation
- ✅ Historical bug regression
- ✅ **Zero-dependency verification**

### Not Covered (Manual Testing)
- ❌ GUI rendering (tkinter UI)
- ❌ Actual mouse/keyboard input
- ❌ Real window interaction
- ❌ ctypes Windows API calls (mocked in tests)

## Continuous Integration

The test suite is designed for CI:

1. **Zero-dependency verification runs first**
   - Fails fast if external deps detected
   - Critical for maintaining minified principle

2. **Fast feedback**
   - Smoke tests < 5 seconds
   - Pure logic tests < 10 seconds

3. **Platform detection**
   - Tests skip gracefully on non-Windows

4. **Clear exit codes**
   - Non-zero on any failure

## Troubleshooting

### "Module not found" errors
Ensure you're in the project root:
```bash
cd "E:/AMLY/works/python works/click-tool-minified-dev"
.venv\Scripts\activate
```

### "pytest not found"
Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

### Zero-dependency test fails
Check for accidental pywin32 imports:
```bash
grep -r "import win32" clicktool_min/
grep -r "from win32" clicktool_min/
```

### Tests pass but source won't run
Verify no hidden dependencies:
```bash
python -c "import sys; sys.path.insert(0, '.'); from clicktool_min import script"
```

## Maintaining Zero Dependencies

### Before Every Commit
1. Run zero-dependency smoke tests
2. Verify no pywin32 imports
3. Test source imports without venv

### Code Review Checklist
- [ ] No `import win32*` in source
- [ ] No `from win32*` in source
- [ ] All Windows API via `ctypes.windll`
- [ ] `requirements.txt` remains empty
- [ ] Tests pass with only stdlib

### Adding New Features
1. Implement using ctypes, not pywin32
2. Add pure logic tests
3. Run zero-dependency verification
4. Document any new ctypes usage

## Future Enhancements

1. **Coverage reporting:** Add pytest-cov for metrics
2. **ctypes mock library:** Standardize Windows API mocking
3. **Performance tests:** Benchmark ctypes vs pywin32
4. **Cross-platform CI:** Test on Linux (should skip gracefully)
5. **Packaging tests:** Verify standalone executable has no deps

## Philosophy

The minified branch exists to prove that **powerful Windows automation requires zero external dependencies**. Every test reinforces this principle. If a test requires pywin32, it doesn't belong here—move it to the main branch or rewrite it with ctypes.

**Zero dependencies isn't a constraint—it's a feature.**
