"""
Ollama Setup, Configuration, and Daemon Management Utility for Orvix Sphere.
Ensures Ollama is installed, configured with OLLAMA_MODELS on W: drive, and actively running.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from config.user_config import OLLAMA_HOME, is_w_drive_available

logger = logging.getLogger("orvix.tools.ollama_setup")

DEFAULT_OLLAMA_MODELS_PATH = os.path.normpath(f"{OLLAMA_HOME}/models")
OLLAMA_API_BASE = "http://localhost:11434"


def check_ollama_installed() -> bool:
    """Checks whether the ollama executable is installed and available."""
    if shutil.which("ollama") is not None:
        return True

    candidate_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
        Path("C:/Users") / os.environ.get("USERNAME", "") / "AppData/Local/Programs/Ollama/ollama.exe",
    ]
    return any(p.exists() for p in candidate_paths)


def install_ollama() -> bool:
    """Installs Ollama using Windows winget package manager."""
    logger.info("Attempting to install Ollama via winget...")
    try:
        proc = subprocess.run(
            ["winget", "install", "Ollama.Ollama", "--accept-source-agreements", "--accept-package-agreements"],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode == 0:
            logger.info("Ollama installed successfully via winget.")
            return True
        logger.warning(f"Winget install returned exit code {proc.returncode}: {proc.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to run winget to install Ollama: {e}")
        return False


def configure_ollama_home(target_path: Optional[str] = None) -> bool:
    """
    Configures the OLLAMA_MODELS environment variable so models are stored on the W: drive.
    Updates current process environment and persists to Windows User environment variables.
    """
    models_dir = target_path or DEFAULT_OLLAMA_MODELS_PATH
    norm_path = os.path.normpath(models_dir)

    try:
        os.makedirs(norm_path, exist_ok=True)
        os.environ["OLLAMA_MODELS"] = norm_path

        # Persist to User Environment on Windows via PowerShell
        ps_cmd = f'[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "{norm_path}", "User")'
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            timeout=10,
            check=False,
        )
        logger.info(f"Configured OLLAMA_MODELS to: {norm_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure OLLAMA_MODELS: {e}")
        return False


def is_ollama_service_running() -> bool:
    """Checks if Ollama HTTP daemon is responding on localhost:11434."""
    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama_service() -> bool:
    """Ensures the Ollama daemon is running in the background."""
    if is_ollama_service_running():
        logger.debug("Ollama daemon is already running.")
        return True

    logger.info("Starting Ollama background daemon ('ollama serve')...")
    try:
        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        for _ in range(20):
            time.sleep(0.5)
            if is_ollama_service_running():
                logger.info("Ollama background service successfully started.")
                return True
        logger.warning("Ollama serve was spawned but did not respond within timeout.")
        return False
    except Exception as e:
        logger.error(f"Failed to spawn Ollama service: {e}")
        return False


def list_models() -> List[Dict[str, Any]]:
    """Retrieves list of downloaded models from Ollama."""
    if not is_ollama_service_running():
        return []

    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("models", [])
    except Exception as e:
        logger.warning(f"Error fetching Ollama models list: {e}")
        return []
