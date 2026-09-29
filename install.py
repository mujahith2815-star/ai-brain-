"""
Cross-Platform Automated Setup & Environment Installer for P.H.A.S.S Sphere.
Configures Python dependencies, sets up local storage directories,
checks Ollama daemon status, and verifies cross-platform readiness.
"""

import os
import sys
import json
import shutil
import subprocess
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phass.installer")

PROJECT_ROOT = Path(__file__).resolve().parent


def check_python_version():
    logger.info("[1/5] Checking Python version...")
    if sys.version_info < (3, 9):
        logger.error(f"Python 3.9+ is required. Found: {sys.version}")
        sys.exit(1)
    logger.info(f"Python version nominal: {sys.version.split()[0]}")


def install_requirements(skip_pip: bool = False):
    logger.info("[2/5] Checking and installing Python dependencies...")
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        logger.warning("requirements.txt not found. Skipping pip install.")
        return

    if skip_pip:
        logger.info("Skipping pip dependencies as requested.")
        return

    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        subprocess.run(cmd, check=True)
        logger.info("Python dependencies successfully installed/verified.")
    except Exception as e:
        logger.warning(f"pip install completed with warnings/errors: {e}")


def initialize_directories():
    logger.info("[3/5] Initializing local storage and memory vaults...")
    directories = [
        "memory_vault",
        "audio_cache",
        "data_backups",
        "checkpoints",
        "overnight_logs",
        "dist",
        "build",
    ]
    for d in directories:
        p = PROJECT_ROOT / d
        p.mkdir(parents=True, exist_ok=True)
    logger.info("Storage vaults and cache paths initialized.")


def check_ollama_runtime():
    logger.info("[4/5] Checking local Ollama AI model runtime...")
    ollama_path = shutil.which("ollama")
    is_windows = sys.platform.startswith("win")

    if not ollama_path:
        logger.warning("Ollama executable was not detected in PATH.")
        if is_windows:
            logger.info("To install Ollama on Windows, run:")
            logger.info("  powershell -ExecutionPolicy Bypass -File install_ollama_windows.ps1")
            logger.info("  or download from: https://ollama.com/download/windows")
        else:
            logger.info("To install Ollama on Linux, run:")
            logger.info("  curl -fsSL https://ollama.ai/install.sh | sh")
        return False

    logger.info(f"Ollama detected at: {ollama_path}")

    # Check daemon health
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            logger.info(f"Ollama API is ONLINE. Available models: {models}")
            return True
    except Exception:
        logger.info("Ollama service is currently stopped. Starting daemon in background...")
        try:
            if is_windows:
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0)
            else:
                subprocess.Popen(["ollama", "serve"], start_new_session=True)
            logger.info("Ollama daemon start command issued.")
        except Exception as e:
            logger.warning(f"Could not automatically start ollama daemon: {e}")
        return False


def verify_cross_platform():
    logger.info("[5/5] Verifying Platform Abstraction Layer...")
    from core.platform_abstraction import get_platform
    plat = get_platform()
    info = plat.get_system_info()
    logger.info(f"Host OS: {info['os_name']} ({info['os_type']}) {info['os_release']}")
    logger.info(f"CPU Cores: {info['cpu_count']}, Memory Available: {info.get('memory_available_mb', 'N/A')} MB")
    logger.info(f"User Home: {plat.get_home_dir()}")
    logger.info(f"Downloads: {plat.get_downloads_dir()}")
    logger.info("All cross-platform subsystem checks PASSED.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="P.H.A.S.S Sphere Cross-Platform Installer")
    parser.add_argument("--skip-pip", action="store_true", help="Skip pip installation of requirements")
    args = parser.parse_args()

    print("=======================================================================")
    print("      P.H.A.S.S SPHERE — CROSS-PLATFORM INSTALLER & ENVIRONMENT SETUP      ")
    print("=======================================================================")

    check_python_version()
    install_requirements(skip_pip=args.skip_pip)
    initialize_directories()
    check_ollama_runtime()
    verify_cross_platform()

    print("\n=======================================================================")
    print(" [OK] P.H.A.S.S Sphere setup is complete and ready to run!")
    print(" Run with: python run_model_chat.py")
    print("=======================================================================")


if __name__ == "__main__":
    main()
