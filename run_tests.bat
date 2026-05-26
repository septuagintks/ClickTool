@echo off
REM Click Tool Minified - One-Click Test Runner
REM Automatically sets up venv and runs pytest

setlocal
set "TEST_EXIT_CODE=0"

echo ========================================
echo Click Tool Minified Test Suite
echo ========================================
echo.

pushd "%~dp0" >nul
if errorlevel 1 (
    echo [ERROR] Failed to enter project directory: %~dp0
    exit /b 1
)

set "VENV_PYTHON=.venv\Scripts\python.exe"

REM Check if venv exists, create if not
if not exist "%VENV_PYTHON%" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo Make sure Python is installed and in PATH
        set "TEST_EXIT_CODE=1"
        goto finish
    )
    echo [SUCCESS] Virtual environment created
)

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment Python not found: %VENV_PYTHON%
    set "TEST_EXIT_CODE=1"
    goto finish
)

"%VENV_PYTHON%" -c "import sys; print('[INFO] Using Python: ' + sys.executable)"

REM Check if pytest is installed, install if not
"%VENV_PYTHON%" -c "import pytest" 2>nul
if errorlevel 1 (
    echo [INFO] pytest not found, installing dev dependencies...
    "%VENV_PYTHON%" -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dev dependencies
        set "TEST_EXIT_CODE=1"
        goto finish
    )
    echo [SUCCESS] Dev dependencies installed
)

REM Verify zero runtime dependencies
echo [INFO] Verifying zero runtime dependencies...
"%VENV_PYTHON%" -S -c "import sys; sys.path.insert(0, '.'); from clicktool_min import script, window, hotkey, winapi" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to import clicktool_min without external dependencies
    set "TEST_EXIT_CODE=1"
    goto finish
)
echo [OK] Zero runtime dependencies verified

REM Run tests
echo [INFO] Running test suite...
echo.
"%VENV_PYTHON%" -m pytest tests/ -v --tb=short -p no:cacheprovider

set TEST_EXIT_CODE=%errorlevel%

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo [SUCCESS] All tests passed!
) else (
    echo [FAILURE] Some tests failed. Exit code: %TEST_EXIT_CODE%
)

:finish
popd >nul
exit /b %TEST_EXIT_CODE%
