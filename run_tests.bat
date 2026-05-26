@echo off
REM Click Tool - One-Click Test Runner
REM Automatically sets up venv and runs pytest

setlocal

echo ========================================
echo Click Tool Test Suite
echo ========================================
echo.

REM Check if venv exists, create if not
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo Make sure Python is installed and in PATH
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

REM Use venv Python directly (don't rely on activate.bat which may have stale paths)
set VENV_PYTHON=.venv\Scripts\python.exe

REM Check if pytest is installed, install if not
%VENV_PYTHON% -c "import pytest" 2>nul
if errorlevel 1 (
    echo [INFO] pytest not found, installing dev dependencies...
    %VENV_PYTHON% -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dev dependencies
        exit /b 1
    )
    echo [SUCCESS] Dev dependencies installed
)

REM Run tests
echo [INFO] Running test suite...
echo.
%VENV_PYTHON% -m pytest tests/ -v --tb=short

set TEST_EXIT_CODE=%errorlevel%

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo [SUCCESS] All tests passed!
) else (
    echo [FAILURE] Some tests failed. Exit code: %TEST_EXIT_CODE%
)

exit /b %TEST_EXIT_CODE%
