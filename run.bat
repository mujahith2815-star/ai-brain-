@echo off
setlocal
title Orvix Sphere — Web Dashboard
echo ==============================================================================
echo                 ORVIX SPHERE — WEB DASHBOARD LAUNCHER
echo ==============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Running setup.bat first...
    call setup.bat
)

echo [*] Starting Orvix Sphere Zenith Dashboard at http://127.0.0.1:8000 ...
echo [*] Press Ctrl+C in this window to stop the server.
echo.

.venv\Scripts\python.exe -m web.launcher
pause
