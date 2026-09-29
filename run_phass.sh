#!/usr/bin/env bash
# P.H.A.S.S SPHERE - Linux & macOS Master Launcher

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 -c "import pytest, requests, numpy" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[!] Missing dependencies detected. Running auto-installer..."
    python3 setup_environment.py
fi

echo "[*] Starting P.H.A.S.S Sphere Native Desktop Application..."
python3 run_software.py
