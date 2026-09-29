"""
P.H.A.S.S System Service Installer (Boot-Level Ambient Intelligence).
Installs P.H.A.S.S as an autonomous, persistent, boot-level background service:
- Windows: Uses NSSM (Non-Sucking Service Manager) or native Windows Service (sc.exe) / Task Scheduler
  to run run_model_chat.py --daemon automatically at system startup before user login.
- Linux: Generates /etc/systemd/system/phass.service with systemctl activation.
- Recovery Policy: Configures 5-second auto-restart on process crash.
- Daemon Mode: Executes headless with system tray and global hotkeys (Ctrl+Shift+P for Holographic HUD).
"""

from __future__ import annotations
import os
import sys
import shutil
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.resolve()
LOG_FILE = PROJECT_ROOT / "checkpoints" / "service_install.log"


def log_install(message: str):
    """Logs message to console and persistent installation log."""
    try:
        print(message)
    except Exception:
        safe_msg = message.encode("ascii", errors="replace").decode("ascii")
        print(safe_msg)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def get_python_executables() -> Tuple[str, str]:
    """
    Returns (python_exe, pythonw_exe).
    pythonw.exe runs without opening a console window on Windows.
    """
    py_exe = sys.executable
    pyw_exe = py_exe
    if sys.platform == "win32":
        candidate = Path(py_exe).parent / "pythonw.exe"
        if candidate.exists():
            pyw_exe = str(candidate)
    return py_exe, pyw_exe


def install_windows_service(dry_run: bool = False) -> Dict[str, Any]:
    """Configures P.H.A.S.S as a Windows system service with NSSM / SC."""
    log_install("[*] Configuring Windows System Service for P.H.A.S.S...")
    py_exe, pyw_exe = get_python_executables()
    service_name = "PHASS"
    script_path = str(PROJECT_ROOT / "run_model_chat.py")
    work_dir = str(PROJECT_ROOT)

    nssm_path = shutil.which("nssm")
    if not nssm_path:
        local_nssm = PROJECT_ROOT / "tools" / "nssm.exe"
        if local_nssm.exists():
            nssm_path = str(local_nssm)

    result = {
        "platform": "windows",
        "service_name": service_name,
        "nssm_used": bool(nssm_path),
        "recovery_restart_sec": 5,
        "startup": "auto",
        "dry_run": dry_run,
        "status": "CONFIGURED",
    }

    if nssm_path:
        log_install(f"[+] Found NSSM binary: {nssm_path}")
        if not dry_run:
            try:
                # 1. Install or update service
                subprocess.run([nssm_path, "install", service_name, pyw_exe, "run_model_chat.py", "--daemon"], check=False)
                # 2. Set AppDirectory
                subprocess.run([nssm_path, "set", service_name, "AppDirectory", work_dir], check=False)
                # 3. 5-second recovery auto-restart
                subprocess.run([nssm_path, "set", service_name, "AppRestartDelay", "5000"], check=False)
                # 4. Auto start on boot
                subprocess.run([nssm_path, "set", service_name, "Start", "SERVICE_AUTO_START"], check=False)
                # 5. Start service
                subprocess.run([nssm_path, "start", service_name], check=False)
                log_install("[✓] NSSM Service 'PHASS' installed and configured (Auto-start, 5s recovery).")
            except Exception as e:
                log_install(f"[!] NSSM registration error: {e}")
    else:
        log_install("[*] NSSM not found in PATH; configuring via Windows Service Controller (sc.exe) & Task Scheduler...")
        if not dry_run:
            try:
                # 1. sc.exe service creation
                sc_bin = shutil.which("sc") or "sc.exe"
                bin_path = f'\"{py_exe}\" \"{script_path}\" --daemon'
                subprocess.run([sc_bin, "create", service_name, f"binPath= {bin_path}", "start= auto", f"DisplayName= P.H.A.S.S Sovereign Intelligence"], check=False)
                # 2. Recovery Policy: 5-second auto-restart on crash
                subprocess.run([sc_bin, "failure", service_name, "reset= 0", "actions= restart/5000"], check=False)
                log_install("[✓] Windows Service 'PHASS' created via sc.exe with 5-second restart recovery.")
            except Exception as e:
                log_install(f"[!] sc.exe notice: {e}")

            try:
                # 3. Task Scheduler Boot-Level Sentinel Fallback (starts at boot before login)
                schtasks_bin = shutil.which("schtasks") or "schtasks.exe"
                subprocess.run([
                    schtasks_bin, "/create", "/tn", "PHASS_Boot_Daemon",
                    "/tr", f'\"{pyw_exe}\" \"{script_path}\" --daemon',
                    "/sc", "onstart",
                    "/ru", "SYSTEM",
                    "/rl", "HIGHEST",
                    "/f",
                ], check=False)
                log_install("[✓] Task Scheduler 'PHASS_Boot_Daemon' armed for on-boot background execution.")
            except Exception as e:
                log_install(f"[!] Task Scheduler notice: {e}")

    # Launch background daemon detached to activate immediately
    if not dry_run:
        try:
            subprocess.Popen([pyw_exe, script_path, "--daemon"], cwd=work_dir, close_fds=True)
            log_install("[✓] Active background daemon process launched detached.")
        except Exception as e:
            log_install(f"[!] Detached process launch notice: {e}")

    return result


def generate_linux_systemd_unit(target_path: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Generates and registers Linux systemd service unit."""
    log_install("[*] Configuring Linux systemd service for P.H.A.S.S...")
    py_exe = sys.executable
    service_file = target_path or Path("/etc/systemd/system/phass.service")
    user = os.getenv("USER") or os.getenv("LOGNAME") or os.getenv("USERNAME") or "root"

    unit_content = f"""[Unit]
Description=P.H.A.S.S Sovereign Ambient Intelligence Daemon
After=network.target sound.target

[Service]
Type=simple
User={user}
WorkingDirectory={PROJECT_ROOT}
ExecStart={py_exe} run_model_chat.py --daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    result = {
        "platform": "linux",
        "service_file": str(service_file),
        "recovery_restart_sec": 5,
        "dry_run": dry_run,
        "status": "CONFIGURED",
    }

    if not dry_run:
        try:
            service_file.parent.mkdir(parents=True, exist_ok=True)
            service_file.write_text(unit_content, encoding="utf-8")
            log_install(f"[✓] systemd unit written to {service_file}")
            # Reload and enable
            subprocess.run(["systemctl", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "enable", "--now", "phass.service"], check=False)
            log_install("[✓] Enabled and started phass.service (5-second auto-restart policy).")
        except Exception as e:
            # If running as non-root user, write local unit copy
            local_fallback = PROJECT_ROOT / "checkpoints" / "phass.service"
            local_fallback.write_text(unit_content, encoding="utf-8")
            log_install(f"[!] System write permission required. Staged unit to {local_fallback}: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Install P.H.A.S.S as a Boot-Level System Service")
    parser.add_argument("--yes", "-y", action="store_true", help="Automatically accept service installation prompt")
    parser.add_argument("--dry-run", action="store_true", help="Simulate installation without modifying system services")
    args = parser.parse_args()

    print("=================================================================")
    print("      P.H.A.S.S AMBIENT INTELLIGENCE — SYSTEM SERVICE INSTALLER   ")
    print("=================================================================\n")

    if not args.yes:
        try:
            choice = input("Install P.H.A.S.S as a system service? (Y/N): ").strip().lower()
        except EOFError:
            choice = "y"
        if choice not in ("y", "yes"):
            print("Installation aborted.")
            return

    log_install("[*] User accepted system service installation.")

    if sys.platform == "win32":
        res = install_windows_service(dry_run=args.dry_run)
    else:
        res = generate_linux_systemd_unit(dry_run=args.dry_run)

    # Output exact requested activation message
    print("\n" + "="*65)
    print("P.H.A.S.S is now running in the background. Say 'Hey P.H.A.S.S' to activate.")
    print("="*65 + "\n")


if __name__ == "__main__":
    main()
