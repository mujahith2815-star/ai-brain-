"""
First-Run Interactive Setup Wizard for Orvix Sphere.
Configures user preferences, model defaults, and runs system health checks.
"""

import sys
from pathlib import Path
from config.user_config import UserConfig
from diagnostics.doctor import SystemDoctor

def run_wizard():
    print("=================================================================")
    print("            ORVIX SPHERE FIRST-RUN ONBOARDING WIZARD             ")
    print("=================================================================")
    print("Welcome! Let's personalize your AI Autonomous Operating System.\n")

    cfg = UserConfig.load()

    name_in = input(f"Enter your preferred operator name [{cfg.user_name}]: ").strip()
    if name_in:
        cfg.user_name = name_in

    model_in = input(f"Default model identifier [{cfg.preferred_model}]: ").strip()
    if model_in:
        cfg.preferred_model = model_in

    watch_in = input("Enter watch folders (comma-separated) [knowledge/inbox, Downloads]: ").strip()
    if watch_in:
        cfg.watch_folders = [p.strip() for p in watch_in.split(",") if p.strip()]

    cfg.save()
    print("\n[✓] Configuration saved to config/user_config.json")
    print("\nRunning initial system diagnostic check...\n")

    doctor = SystemDoctor()
    print(doctor.format_report())
    print("\nSetup complete! You can now run 'python run_model_chat.py' or 'python -m web.launcher'.\n")

if __name__ == "__main__":
    run_wizard()
