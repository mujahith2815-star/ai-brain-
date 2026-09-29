"""
Entrypoint to run the P.H.A.S.S Sphere Telemetry & Control Center Web Server.
"""

import uvicorn
import argparse
import sys
from pathlib import Path

# Ensure project root is in python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.settings import settings


def main():
    parser = argparse.ArgumentParser(description="P.H.A.S.S Sphere Web Control Center Launcher")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print("==================================================================")
    print("      P.H.A.S.S SPHERE — AUTONOMOUS PHYSICAL AI PLATFORM              ")
    print("      Model: ORB-7-ALPHA | Mode: OFFLINE-FIRST COGNITIVE CORE     ")
    print(f"      Control Center Dashboard: http://{args.host}:{args.port}    ")
    print("==================================================================")

    uvicorn.run(
        "interface.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
