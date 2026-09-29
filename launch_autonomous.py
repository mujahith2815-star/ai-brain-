"""
Autonomous Mode Launcher for P.H.A.S.S Llama Assistant
Launches the assistant in zero-touch autonomous mode.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variable for autonomous execution
os.environ["LLAMA_AUTONOMOUS"] = "true"

def main():
    print("=" * 60)
    print("🤖 STARTING P.H.A.S.S LLAMA ASSISTANT IN FULL AUTONOMOUS MODE")
    print("   • Zero-touch execution active")
    print("   • Interruptions disabled except for true emergencies")
    print("   • Automations & Reports workspaces enabled")
    print("=" * 60)

    from ui.main_window import AssistantUI
    app = AssistantUI()
    app.autonomous_mode = True
    app.run()

if __name__ == "__main__":
    main()
