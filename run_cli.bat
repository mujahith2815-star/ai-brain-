@echo off
setlocal
title Orvix Sphere — Interactive AI Terminal
echo ==============================================================================
echo              ORVIX SPHERE — INTERACTIVE AI TERMINAL ASSISTANT
echo ==============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Running setup.bat first...
    call setup.bat
)

.venv\Scripts\python.exe phass_cli.py
pause
