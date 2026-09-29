"""
Standalone Web Dashboard Launcher for Orvix Sphere.
Starts FastAPI server via Uvicorn and launches the default web browser.
"""

import sys
import time
import webbrowser
import threading
from pathlib import Path
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")

def main():
    print("[*] Launching Orvix Sphere Zenith Web Dashboard on http://127.0.0.1:8000...")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
