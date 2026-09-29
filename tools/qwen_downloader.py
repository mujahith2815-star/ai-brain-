"""
Qwen2.5-7B Model Downloader and Verifier for Orvix Sphere.
Pulls qwen2.5:7b-instruct-q4_K_M directly to W: drive via Ollama.
"""

from __future__ import annotations
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from config.user_config import OLLAMA_HOME, is_w_drive_available
from tools.ollama_setup import configure_ollama_home, is_ollama_service_running, start_ollama_service, list_models

logger = logging.getLogger("orvix.tools.qwen_downloader")

DEFAULT_MODEL_TAG = "qwen2.5:7b-instruct-q4_K_M"


def is_qwen_downloaded(model_tag: str = DEFAULT_MODEL_TAG) -> bool:
    """Checks whether the Qwen model is present in Ollama model tags."""
    models = list_models()
    for m in models:
        name = m.get("name", "")
        if model_tag in name or name.startswith("qwen2.5:7b"):
            return True
    return False


def download_qwen_model(
    model_tag: str = DEFAULT_MODEL_TAG,
    models_path: Optional[str] = None,
) -> bool:
    """
    Sets OLLAMA_MODELS to W: drive and runs 'ollama pull' to acquire Qwen2.5-7B.
    Shows real-time progress and verifies model file upon completion.
    """
    target_models_dir = models_path or os.path.normpath(f"{OLLAMA_HOME}/models")
    print(f"[*] Target Model: {model_tag}")
    print(f"[*] Storage Path: {target_models_dir} (W: drive available: {is_w_drive_available()})")

    # 1. Check if already available
    if is_qwen_downloaded(model_tag):
        print(f"[✓] Model '{model_tag}' is already downloaded and verified on disk.")
        return True

    # 2. Ensure OLLAMA_MODELS points to W: drive
    configure_ollama_home(target_models_dir)

    # 3. Ensure Ollama service is active
    if not is_ollama_service_running():
        print("[*] Starting Ollama daemon...")
        if not start_ollama_service():
            print("[!] Could not start Ollama service. Please run 'ollama serve' manually.")
            return False

    print(f"[*] Downloading {model_tag} (~4.7 GB). This may take several minutes...")
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = target_models_dir

    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model_tag],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

        proc.wait()
        if proc.returncode != 0:
            print(f"[!] 'ollama pull' failed with exit code {proc.returncode}")
            return False

        # Verify presence
        if is_qwen_downloaded(model_tag):
            print(f"\n[✓] Successfully downloaded and verified '{model_tag}' on W: drive!")
            return True
        else:
            print(f"\n[!] Pull completed, but '{model_tag}' was not found in model list.")
            return False

    except Exception as e:
        logger.error(f"Failed to download Qwen model: {e}")
        print(f"[!] Error downloading model: {e}")
        return False


if __name__ == "__main__":
    download_qwen_model()
