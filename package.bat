@echo off
setlocal enabledelayedexpansion

echo =======================================================================
echo          P.H.A.S.S SPHERE — WINDOWS STANDALONE PACKAGING SUITE
echo =======================================================================

cd /d "%~dp0"

echo [*] Detecting Python environment...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python was not found in PATH. Please install Python 3.9+ first.
    exit /b 1
)

echo [*] Installing PyInstaller and build dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1

echo [*] Building Windows Standalone Executable...
python build.py --platform windows --name phass_sphere --output-dir dist

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Windows packaging complete! Binary located in dist\phass_sphere.exe
) else (
    echo [ERROR] Build failed with status %ERRORLEVEL%
)

endlocal
