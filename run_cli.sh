#!/usr/bin/env bash
# ==============================================================================
# Orvix Sphere — Interactive AI Terminal (Linux / macOS)
# ==============================================================================

set -e

if [ ! -f ".venv/bin/python" ]; then
    echo "[!] Virtual environment not found. Running ./setup.sh first..."
    ./setup.sh
fi

.venv/bin/python phass_cli.py
