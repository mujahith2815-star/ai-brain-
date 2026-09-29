#!/usr/bin/env bash
# P.H.A.S.S Sphere 1-Click Linux / macOS Environment Installer

set -e

echo "======================================================="
echo "       P.H.A.S.S SPHERE — 1-CLICK LINUX/MACOS INSTALLER    "
echo "======================================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is not installed. Please install python3 (apt-get install python3 / brew install python)."
    exit 1
fi

echo "[*] Creating virtual environment (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

echo "[*] Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[*] Running environment bootstrapper..."
python3 setup_environment.py

echo ""
echo "======================================================="
echo "[+] Installation Complete! Use './run_phass.sh' to start."
echo "======================================================="
