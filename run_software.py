"""
P.H.A.S.S SPHERE — Master Native Desktop Software Launcher.
Launches the standalone desktop application.
"""

import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.version import get_version_banner
from gui.desktop_app import launch_desktop_gui

if __name__ == "__main__":
    print(f"\n{get_version_banner()}\n")
    try:
        launch_desktop_gui()
    except KeyboardInterrupt:
        print("\n[P.H.A.S.S] Desktop software exited.")
