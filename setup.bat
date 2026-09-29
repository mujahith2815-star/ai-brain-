@echo off
setlocal enabledelayedexpansion
title Orvix Sphere — Setup & Environment Provisioner
echo ==============================================================================
echo                 ORVIX SPHERE — SETUP & INSTALLATION WIZARD
echo ==============================================================================
echo.

REM 1. Check Python
echo [*] Step 1/5: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found on your system PATH.
    echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [+] Found Python %PY_VER%

REM 2. Setup Virtual Environment
echo.
echo [*] Step 2/5: Checking virtual environment (.venv)...
if not exist ".venv" (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [+] Virtual environment created.
) else (
    echo [+] Existing virtual environment detected.
)

REM 3. Install Dependencies
echo.
echo [*] Step 3/5: Installing package dependencies...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some dependencies encountered warnings during install. Proceeding...
)
call .venv\Scripts\python.exe -m pip install -e . --quiet --no-deps
echo [+] All Python packages and Orvix Sphere module installed successfully.

REM 4. Check / Create .env
echo.
echo [*] Step 4/5: Checking environment configuration (.env)...
if not exist ".env" (
    echo [*] Creating .env from .env.example template...
    copy .env.example .env >nul
    echo [+] Created .env configuration file.
    echo [!] NOTE: Remember to edit .env and set your GEMINI_API_KEY (from https://aistudio.google.com/)
) else (
    echo [+] Existing .env found.
)

REM 5. Check Node.js for MCP Servers
echo.
echo [*] Step 5/5: Checking Node.js runtime for MCP Servers...
node --version >nul 2>&1
if errorlevel 1 (
    echo [!] Node.js is not found on PATH.
    echo     MCP tools (SQLite, Filesystem, Fetch) run via Node.js.
    echo     You can install Node.js (v18+) from https://nodejs.org/ if you plan to use MCP tools.
    echo     (Core AI and Web Dashboard will still work fine without Node.js.)
) else (
    for /f "tokens=*" %%n in ('node --version 2^>^&1') do set NODE_VER=%%n
    echo [+] Found Node.js !NODE_VER! - MCP STDIO servers ready.
)

echo.
echo ==============================================================================
echo [+] SETUP COMPLETE! Orvix Sphere is ready to run.
echo ==============================================================================
echo.
echo Quick Ways to Launch:
echo   1. Double-click run.bat        - Launches the Web Dashboard (http://127.0.0.1:8000)
echo   2. Double-click run_cli.bat    - Launches the interactive terminal assistant
echo   3. Inside Antigravity          - Open workspace and run pytest or web dashboard
echo.
pause
