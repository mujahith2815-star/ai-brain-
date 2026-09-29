"""
Orvix Sphere First Run Setup & Diagnostics Wizard (v1.4.0).
Runs diagnostics on W: drive storage, Ollama installation, Qwen2.5-7B model, and Gemini API key.
"""

from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.user_config import is_w_drive_available, ensure_storage_directories, MODELS_ROOT, OLLAMA_HOME
from tools.ollama_setup import check_ollama_installed, install_ollama, configure_ollama_home, is_ollama_service_running, start_ollama_service
from tools.qwen_downloader import is_qwen_downloaded, download_qwen_model
from tools.gemini_engine import gemini_engine
from tools.model_router import model_router


def run_first_run_wizard(auto_fix: bool = False) -> Dict[str, Any]:
    """Runs the 5-step initialization and verification wizard."""
    print("=" * 68)
    print("      ORVIX SPHERE — FIRST RUN HYBRID SETUP & HARDWARE WIZARD       ")
    print("=" * 68)
    print()

    results: Dict[str, Any] = {}

    # Step 1: Check W: Drive
    print("[1/5] Checking W: drive storage architecture...")
    w_ok = is_w_drive_available()
    results["w_drive_available"] = w_ok
    if w_ok:
        paths = ensure_storage_directories()
        print(f"  ✓ W: drive accessible and writable.")
        print(f"    - Models Directory: {MODELS_ROOT}")
        print(f"    - Ollama Data:     {OLLAMA_HOME}")
    else:
        print("  ⚠️ W: drive not detected or not writable.")
        print("    Fell back to C: disk where free disk space is limited.")

    # Step 2: Check Ollama Installation
    print("\n[2/5] Checking Ollama daemon installation...")
    ollama_installed = check_ollama_installed()
    results["ollama_installed"] = ollama_installed
    if ollama_installed:
        print("  ✓ Ollama executable detected.")
    else:
        print("  ⚠️ Ollama is not installed.")
        if auto_fix:
            print("    Attempting automatic install via winget...")
            install_ollama()
        else:
            print("    To install Ollama, run: winget install Ollama.Ollama")

    # Step 3: Check Ollama Daemon Service & Qwen Model on W:
    print("\n[3/5] Checking Ollama service and Qwen2.5-7B model on W: drive...")
    if ollama_installed:
        if not is_ollama_service_running():
            print("    Ollama service stopped. Starting background service...")
            start_ollama_service()

        qwen_ok = is_qwen_downloaded()
        results["qwen_ready"] = qwen_ok
        if qwen_ok:
            print("  ✓ Qwen2.5-7B-Instruct verified on W: drive.")
        else:
            print("  ⚠️ Qwen2.5-7B model not yet downloaded.")
            if auto_fix:
                print("    Initiating Qwen download to W: drive...")
                download_qwen_model()
            else:
                print("    To download Qwen, run: python run_model_chat.py -c '/qwen-download'")
    else:
        results["qwen_ready"] = False
        print("  ⚠️ Skipped model check because Ollama is not installed.")

    # Step 4: Check Gemini API Key
    print("\n[4/5] Checking Google Gemini Cloud API Key...")
    gemini_avail = gemini_engine.is_available()
    results["gemini_ready"] = gemini_avail
    if gemini_avail:
        print("  ✓ Google Gemini 2.0 Flash is configured and reachable.")
    else:
        print("  ⚠️ GEMINI_API_KEY environment variable is not set.")
        print("    Get your free key at: https://aistudio.google.com/apikey")
        print("    Then set it in PowerShell:")
        print("      [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-key', 'User')")

    # Step 5: Engine Diagnostics & Recommendation
    print("\n[5/5] Testing dual-engine connectivity & routing...")
    t_res = model_router.test_engines()
    g = t_res.get("gemini", {})
    q = t_res.get("qwen", {})
    results["engine_test"] = t_res

    print(f"  • Gemini Flash (Cloud): {'✅ ONLINE' if g.get('available') else '⚠️ OFFLINE'}")
    print(f"  • Qwen2.5-7B (Local W:): {'✅ READY' if q.get('available') else '⚠️ OFFLINE'}")
    print(f"  • Current Router Mode:  {model_router.current_mode.upper()}")

    print("\n" + "=" * 68)
    print("                    SETUP SUMMARY & STATUS                          ")
    print("=" * 68)
    if g.get("available") and q.get("available"):
        print("🎉 EXCELLENT! Both cloud and local engines are fully operational.")
        print("   • Gemini 2.0 Flash handles complex multi-step reasoning instantly.")
        print("   • Qwen2.5-7B handles offline fallback running locally on W: drive.")
    elif g.get("available"):
        print("⚡ Cloud engine is ready! Local Qwen engine is currently offline.")
        print("   Run '/qwen-download' inside chat to activate local offline fallback.")
    elif q.get("available"):
        print("🔒 Local Qwen engine on W: is ready! Cloud Gemini is offline.")
        print("   Set GEMINI_API_KEY to activate free cloud reasoning.")
    else:
        print("⚠️ Both engines need configuration. Please follow the instructions above.")

    print("\nStart Orvix Chat with:")
    print("  .\\.venv\\Scripts\\python.exe run_model_chat.py\n")
    return results


if __name__ == "__main__":
    auto = "--fix" in sys.argv
    run_first_run_wizard(auto_fix=auto)
