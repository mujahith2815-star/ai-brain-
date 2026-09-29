#!/usr/bin/env bash
set -e

echo "================================================================="
echo "              ORVIX SPHERE SYSTEM INSTALLER (LINUX)              "
echo "================================================================="

# 1. Verify Python
echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Please install python3 (>=3.10)."
    exit 1
fi

# 2. Virtual Environment
echo "[2/4] Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Dependencies
echo "[3/4] Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Database Initialization
echo "[4/4] Initializing databases..."
python -c "from knowledge.sqlite_store import KnowledgeStore; KnowledgeStore(); print('[✓] SQLite databases ready.')"

echo ""
echo "[★] Orvix Sphere installed successfully."
echo "Start chat:          python run_model_chat.py"
echo "Start web dashboard: python -m web.launcher"
