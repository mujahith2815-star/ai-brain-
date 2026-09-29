"""
Launcher for the P.H.A.S.S Sphere v8.0 Cherry-Red Dark-Theme AI Model Dashboard.
Starts the local server and automatically opens the user's web browser.
"""

import sys
import time
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from ui.cherry_model_dashboard import cherry_dashboard_server

def main():
    print("=================================================================")
    print("   P.H.A.S.S SPHERE v8.0 — CHERRY-RED AI MODEL NEURAL DASHBOARD     ")
    print("=================================================================")
    port = cherry_dashboard_server.start()
    url = f"http://127.0.0.1:{port}"
    print(f"[+] Server online:          {url}")
    print(f"[+] Multi-Window UI:        Enabled (Split 50/50, 4-Grid Snap)")
    print(f"[+] Acrylic Backdrop Blur:  Enabled (blur(16px))")
    print(f"[+] Dynamic Neon Glow:      Cherry-Red (#ff003c) & Crimson (#d90429)")
    print(f"[*] Opening browser to {url}...")
    
    try:
        webbrowser.open(url)
    except Exception:
        pass

    print("\n[!] Press Ctrl+C in this terminal to shutdown the dashboard.\n")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Stopping dashboard server...")
        cherry_dashboard_server.stop()
        print("[+] Dashboard stopped.")

if __name__ == "__main__":
    main()
