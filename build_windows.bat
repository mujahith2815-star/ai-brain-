@echo off
REM =========================================================================
REM P.H.A.S.S SPHERE v8.0 ? Standalone Windows Executable Builder
REM Packages Llama Assistant into a standalone PE binary with PyInstaller
REM =========================================================================

echo [*] Starting P.H.A.S.S SPHERE Windows Build Pipeline...
python -c "import sys; print('[+] Python Version:', sys.version)"

REM Check PyInstaller
python -m pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing PyInstaller...
    python -m pip install pyinstaller
)

REM Execute cross-platform build engine
python build.py --clean

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================================================
    echo [+] BUILD SUCCESSFUL!
    echo [+] Windows Executable: dist\phass_sphere.exe
    echo =========================================================================
) else (
    echo.
    echo [-] Build encountered errors. Please inspect output above.
    exit /b 1
)