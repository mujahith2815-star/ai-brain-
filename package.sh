#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================="
echo "          P.H.A.S.S SPHERE — LINUX STANDALONE PACKAGING SUITE"
echo "======================================================================="

PYTHON_BIN="$(which python3 || which python || echo "")"
if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3 was not found. Please install python3 and python3-pip."
    exit 1
fi

echo "[*] Ensuring PyInstaller is present..."
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null 2>&1 || true
"$PYTHON_BIN" -m pip install pyinstaller >/dev/null 2>&1 || true

echo "[*] Compiling Linux ELF standalone executable..."
"$PYTHON_BIN" build.py --platform linux --name phass_sphere --output-dir dist

if [ -f "dist/phass_sphere" ]; then
    chmod +x "dist/phass_sphere"
    echo "[*] Creating distributable tar.gz archive..."
    tar -czf "dist/phass_linux_x64.tar.gz" -C dist phass_sphere
    echo "[SUCCESS] Linux packaging complete: dist/phass_sphere & dist/phass_linux_x64.tar.gz"
else
    echo "[ERROR] Executable dist/phass_sphere was not produced."
    exit 1
fi
