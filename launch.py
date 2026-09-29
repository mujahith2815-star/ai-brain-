#!/usr/bin/env python3
"""
Universal Launcher Entrypoint for P.H.A.S.S Sphere & Llama Assistant.
Provides seamless execution across all interaction modes:
  --mode chat       Interactive terminal chat with real-time streaming & tools
  --mode cli        Direct command-line execution & batch directives
  --mode dashboard  Web & GUI holographic visual control dashboard
  --mode api        FastAPI / Pure-Python JSON REST API server
  --mode widget     Floating desktop overlay widget with push-to-talk
  --mode sentinel   Autonomous background proactive health & telemetry daemon
  --mode all        Starts REST API, background sentinel, and interactive chat
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phass.launcher")


def print_banner(mode: str, personality: str):
    banner = f"""
================================================================================
          P.H.A.S.S SPHERE ZENITH v8.0 — UNIVERSAL AUTONOMOUS SYSTEM
================================================================================
  • Mode:               {mode.upper()}
  • Persona:            {personality.upper()}
  • Environment:        Verified & Active
  • Brain Architecture: Primed (Primary + Hybrid Secondary + Mind Palace)
================================================================================
"""
    print(banner)


def launch_chat(personality: str, model: str):
    from core.personality_matrix import personality_matrix
    personality_matrix.set_personality(personality)
    from run_model_chat import main as chat_main
    chat_main()


def launch_cli():
    from phass_cli import main as cli_main
    cli_main()


def launch_dashboard(port: int):
    from run_model_dashboard import main as dash_main
    dash_main()


def launch_api(host: str, port: int):
    from core.omni_interface import omni_gateway
    print(f"[*] Starting Omni-Interface REST API on http://{host}:{port}")
    omni_gateway.start_api(host=host, port=port, in_thread=False)


def launch_widget():
    from core.omni_interface import DesktopWidget
    print("[*] Launching Floating Desktop Overlay Widget...")
    widget = DesktopWidget()
    widget.launch(in_thread=False)


def launch_sentinel():
    from core.proactive_engine import proactive_engine
    print("[*] Starting Autonomous Proactive Sentinel Daemon (Press Ctrl+C to stop)...")
    proactive_engine.start_background_sentinel(interval_seconds=60)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping Proactive Sentinel.")
        proactive_engine.stop_background_sentinel()


def launch_all(host: str, port: int, personality: str, model: str):
    from core.omni_interface import omni_gateway
    from core.proactive_engine import proactive_engine
    from core.personality_matrix import personality_matrix

    personality_matrix.set_personality(personality)
    print(f"[*] Initializing Background REST API on http://{host}:{port}...")
    omni_gateway.start_api(host=host, port=port, in_thread=True)

    print("[*] Engaging Autonomous Proactive Sentinel...")
    proactive_engine.start_background_sentinel(interval_seconds=120)

    print("[*] Launching Interactive Session...")
    from run_model_chat import main as chat_main
    chat_main()


def main():
    parser = argparse.ArgumentParser(description="P.H.A.S.S Sphere Universal Launcher")
    parser.add_argument(
        "--mode",
        choices=["chat", "cli", "dashboard", "api", "widget", "sentinel", "all"],
        default="chat",
        help="System runtime mode (default: chat)",
    )
    parser.add_argument(
        "--personality",
        choices=["default", "executive", "friendly", "creative", "late_night"],
        default="default",
        help="Initial persona mode (default: default)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="REST API host interface")
    parser.add_argument("--port", type=int, default=8000, help="REST API listening port")
    parser.add_argument("--model", default="llama3:8b", help="Target model identifier")

    args = parser.parse_args()

    # Ensure environment is initialized
    state_file = PROJECT_ROOT / "checkpoints" / "install_state.json"
    if not state_file.exists():
        from auto_install import main as auto_install_main
        auto_install_main()

    print_banner(args.mode, args.personality)

    if args.mode == "chat":
        launch_chat(args.personality, args.model)
    elif args.mode == "cli":
        launch_cli()
    elif args.mode == "dashboard":
        launch_dashboard(args.port)
    elif args.mode == "api":
        launch_api(args.host, args.port)
    elif args.mode == "widget":
        launch_widget()
    elif args.mode == "sentinel":
        launch_sentinel()
    elif args.mode == "all":
        launch_all(args.host, args.port, args.personality, args.model)


if __name__ == "__main__":
    main()
