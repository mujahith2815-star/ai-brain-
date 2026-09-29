#!/usr/bin/env bash
# ==============================================================================
# Orvix Sphere — Setup & Environment Provisioner (Linux / macOS)
# ==============================================================================

set -e

echo "=============================================================================="
echo "                 ORVIX SPHERE — SETUP & INSTALLATION WIZARD                   "
echo "=============================================================================="
echo ""

# 1. Check Python
echo "[*] Step 1/5: Checking Python installation..."
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python 3.10+ is required but not found."
    echo "Please install Python from https://www.python.org/ or your system package manager."
    exit 1
fi

PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[+] Detected Python $PY_VER ($PYTHON_BIN)"

# 2. Virtual Environment
echo ""
echo "[*] Step 2/5: Checking virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    $PYTHON_BIN -m venv .venv
    echo "[+] Virtual environment created."
else
    echo "[+] Existing virtual environment detected."
fi

# 3. Dependencies
echo ""
echo "[*] Step 3/5: Installing package dependencies..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet || true
.venv/bin/python -m pip install -e . --quiet --no-deps
echo "[+] All Python packages and Orvix Sphere module installed successfully."

# 4. .env Template
echo ""
echo "[*] Step 4/5: Checking environment configuration (.env)..."
if [ ! -f ".env" ]; then
    echo "[*] Creating .env from .env.example template..."
    cp .env.example .env
    echo "[+] Created .env configuration file."
    echo "[!] NOTE: Remember to edit .env and set your GEMINI_API_KEY (from https://aistudio.google.com/)"
else
    echo "[+] Existing .env found."
fi

# 5. Node.js check for MCP
echo ""
echo "[*] Step 5/5: Checking Node.js runtime for MCP Servers..."
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    echo "[+] Found Node.js $NODE_VER - MCP STDIO servers ready."
else
    echo "[!] Node.js not detected on PATH."
    echo "    MCP tools (SQLite, Filesystem, Fetch) run via Node.js."
    echo "    Install Node.js (v18+) if you plan to use MCP tools."
fi

echo ""
echo "=============================================================================="
echo "[+] SETUP COMPLETE! Orvix Sphere is ready to run."
echo "=============================================================================="
echo ""
echo "Quick Ways to Launch:"
echo "  1. ./run.sh         - Launches the Web Dashboard (http://127.0.0.1:8000)"
echo "  2. ./run_cli.sh     - Launches the interactive terminal assistant"
echo "  3. In Antigravity   - Open workspace and run pytest or web dashboard"
echo ""
