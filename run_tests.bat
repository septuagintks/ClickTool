@echo off
REM Click Tool - One-Click Test Runner
REM Activates venv and runs pytest with coverage

setlocal

echo ========================================
echo Click Tool Test Suite
echo ========================================
echo.

REM Check if venv exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv
    echo Please create it first: python -m venv .venv
    echo Then install dependencies: .venv\Scripts\pip install -r requirements-dev.txt
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo [ERROR] pytest not found in virtual environment
    echo Please install dev dependencies: pip install -r requirements-dev.txt
    exit /b 1
)

REM Run tests
echo [INFO] Running test suite...
echo.
python -m pytest tests/ -v --tb=short

set TEST_EXIT_CODE=%errorlevel%

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo [SUCCESS] All tests passed!
) else (
    echo [FAILURE] Some tests failed. Exit code: %TEST_EXIT_CODE%
)

exit /b %TEST_EXIT_CODE%
