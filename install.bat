@echo off
title P.H.A.S.S Sphere Auto-Installer
echo =======================================================
echo          P.H.A.S.S SPHERE — 1-CLICK WINDOWS INSTALLER
echo =======================================================

echo [*] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python is not found on PATH. Please install Python 3.10+ from python.org.
    pause
    exit /b 1
)

echo [*] Installing and upgrading pip requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [*] Provisioning runtime directories and system checks...
python setup_environment.py

echo.
echo =======================================================
echo [+] Installation Complete! Launching P.H.A.S.S Sphere...
echo =======================================================
pause
