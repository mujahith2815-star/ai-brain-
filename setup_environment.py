"""
Universal Cross-Platform Environment Setup & Bootstrapper for P.H.A.S.S Sphere.
Run this script on any system (Windows, macOS, Linux) to automatically configure
the environment, install all dependencies, and verify operational readiness.
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is in pythonpath
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from core.auto_environment_installer import auto_environment_installer

def main():
    print("=======================================================")
    print("      P.H.A.S.S SPHERE — AUTO ENVIRONMENT BOOTSTRAPPER     ")
    print("=======================================================")
    print("[*] Detecting host architecture and hardware...")
    
    report = auto_environment_installer.auto_provision_environment(run_pip_install=True)
    print(auto_environment_installer.format_readiness_report_text(report))
    print("=======================================================")
    print("[+] Environment successfully initialized and verified!")
    print("[+] You can now launch P.H.A.S.S using 'python run_software.py' or 'python phass_cli.py'")

if __name__ == "__main__":
    main()
