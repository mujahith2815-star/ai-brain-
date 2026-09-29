#!/usr/bin/env bash
# =========================================================================
# P.H.A.S.S SPHERE v8.0 ? Standalone Linux Executable & Distribution Builder
# Packages Llama Assistant into a standalone ELF binary and .tar.gz bundle
# =========================================================================

set -e

echo "[*] Initializing P.H.A.S.S SPHERE Linux Build Pipeline..."
python3 -c "import sys; print('[+] Python Version:', sys.version)"

# Check PyInstaller
if ! python3 -m pip show pyinstaller > /dev/null 2>&1; then
    echo "[*] Installing PyInstaller..."
    python3 -m pip install pyinstaller
fi

# Execute cross-platform build engine
python3 build.py --clean

# Package into distribution archive
mkdir -p dist/packages
ARCH=$(uname -m)
BUNDLE_NAME="phass_sphere-v8.0.0-linux-${ARCH}"

if [ -f "dist/phass_sphere" ]; then
    echo "[*] Packaging bundle: dist/packages/${BUNDLE_NAME}.tar.gz"
    tar -czf "dist/packages/${BUNDLE_NAME}.tar.gz" -C dist phass_sphere
    echo "========================================================================="
    echo "[+] Linux ELF Executable: dist/phass_sphere"
    echo "[+] Tarball Bundle:       dist/packages/${BUNDLE_NAME}.tar.gz"
    echo "========================================================================="
else
    echo "[-] Binary dist/phass_sphere was not found."
    exit 1
fi