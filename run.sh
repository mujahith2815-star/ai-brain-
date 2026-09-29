#!/usr/bin/env bash
# ==============================================================================
# Orvix Sphere — Web Dashboard Launcher (Linux / macOS)
# ==============================================================================

set -e

if [ ! -f ".venv/bin/python" ]; then
    echo "[!] Virtual environment not found. Running ./setup.sh first..."
    ./setup.sh
fi

echo "[*] Starting Orvix Sphere Zenith Dashboard at http://127.0.0.1:8000 ..."
echo "[*] Press Ctrl+C to stop the server."
echo ""

.venv/bin/python -m web.launcher
