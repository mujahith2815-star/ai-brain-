@echo off
title P.H.A.S.S SPHERE - Master Launcher
echo [*] Verifying environment health...
python -c "import pytest, requests, numpy" >nul 2>&1
if errorlevel 1 (
    echo [!] Missing dependencies detected. Running auto-installer...
    python setup_environment.py
)

echo [*] Starting P.H.A.S.S Sphere Native Desktop Application...
python run_software.py
pause
