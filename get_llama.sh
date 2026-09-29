#!/usr/bin/env bash
# =============================================================================
# P.H.A.S.S SPHERE ZENITH v8.0 — LINUX / macOS ONE-COMMAND QUICKSTART
# Usage: curl -fsSL https://raw.githubusercontent.com/.../get_llama.sh | bash
# =============================================================================

set -e

echo "=== [P.H.A.S.S SPHERE ZENITH] Cross-Platform Deployment Engine ==="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 not detected. Please install Python 3.9+ using your package manager:"
    echo "    Ubuntu/Debian: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    echo "    Fedora/RHEL:   sudo dnf install -y python3 python3-pip"
    echo "    Arch Linux:    sudo pacman -S python python-pip"
    echo "    macOS:         brew install python"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[+] Detected Python ${PYTHON_VER}"

# Create or reuse virtual environment if desired
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    python3 -m venv .venv || true
fi

if [ -f ".venv/bin/activate" ]; then
    echo "[*] Activating virtual environment..."
    source .venv/bin/activate
fi

# Run zero-touch auto installer
python3 auto_install.py

# Launch interactive session
python3 launch.py --mode chat
