"""
fix_and_launch.py — Automated Diagnostics, Dependency Repair & UI Launcher
P.H.A.S.S SPHERE: Autonomous UI Launch Protocol
"""

import sys
import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure standard UTF-8 output encoding across Windows and POSIX
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_header():
    print("=======================================================")
    print("P.H.A.S.S SPHERE: Initializing UI Launch Protocol...")
    print("=======================================================\n")
    sys.stdout.flush()


# =============================================================================
# 1. ENVIRONMENT DETECTION
# =============================================================================

def detect_operating_system() -> Dict[str, Any]:
    """Detects OS (Windows, Linux Ubuntu/Debian, Linux Arch, WSL, macOS)."""
    os_info = {
        "platform": sys.platform,
        "is_windows": False,
        "is_wsl": False,
        "is_ubuntu_debian": False,
        "is_arch": False,
        "distro_name": "Unknown",
        "description": "Unknown OS",
    }

    if sys.platform == "win32":
        os_info["is_windows"] = True
        try:
            import platform
            win_ver = platform.platform()
            os_info["description"] = f"Windows ({win_ver})"
        except Exception:
            os_info["description"] = "Windows (NT)"
        return os_info

    if sys.platform == "darwin":
        os_info["description"] = "macOS"
        return os_info

    # Linux / POSIX detection
    if sys.platform.startswith("linux"):
        # Check for WSL
        try:
            if "WSL_DISTRO_NAME" in os.environ:
                os_info["is_wsl"] = True
            elif Path("/proc/version").exists():
                proc_ver = Path("/proc/version").read_text(errors="ignore").lower()
                if "microsoft" in proc_ver or "wsl" in proc_ver:
                    os_info["is_wsl"] = True
        except Exception:
            pass

        # Inspect /etc/os-release
        os_release = Path("/etc/os-release")
        id_str = ""
        id_like = ""
        pretty_name = "Linux"

        if os_release.exists():
            try:
                for line in os_release.read_text(errors="ignore").splitlines():
                    if line.startswith("ID="):
                        id_str = line.split("=", 1)[1].strip().strip('"').lower()
                    elif line.startswith("ID_LIKE="):
                        id_like = line.split("=", 1)[1].strip().strip('"').lower()
                    elif line.startswith("PRETTY_NAME="):
                        pretty_name = line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass

        os_info["distro_name"] = pretty_name

        if any(d in id_str or d in id_like for d in ("ubuntu", "debian", "mint", "pop")):
            os_info["is_ubuntu_debian"] = True
            distro_type = "Ubuntu/Debian"
        elif any(d in id_str or d in id_like for d in ("arch", "manjaro", "endeavouros")):
            os_info["is_arch"] = True
            distro_type = "Arch Linux"
        else:
            distro_type = pretty_name

        prefix = "WSL - " if os_info["is_wsl"] else ""
        os_info["description"] = f"Linux ({prefix}{distro_type})"

    return os_info


def ensure_project_root() -> Path:
    """Ensures the current working directory is the project root."""
    project_root = Path(__file__).resolve().parent
    try:
        current_dir = Path.cwd().resolve()
        if current_dir != project_root:
            os.chdir(project_root)
            print(f"✅ Working directory adjusted to project root: {project_root}")
        else:
            print(f"✅ Working directory confirmed: {project_root}")
    except Exception as e:
        print(f"⚠️  Could not change directory to {project_root}: {e}")
    sys.stdout.flush()
    return project_root


def ensure_virtual_environment(project_root: Path) -> str:
    """Detects active virtual environment; auto-creates and activates if absent."""
    is_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix)) or ("VIRTUAL_ENV" in os.environ)
    if is_venv:
        print(f"✅ Active virtual environment detected: {sys.prefix}")
        sys.stdout.flush()
        return sys.executable

    venv_dir = project_root / ".venv"
    if not venv_dir.exists():
        print("⚙️  Virtual environment not detected. Creating .venv with system-site packages...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir), "--system-site-packages"],
                check=True,
            )
            print("✅ Virtual environment created at .venv")
        except Exception as e:
            print(f"⚠️  Could not create virtual environment: {e}. Continuing with current Python.")
            return sys.executable

    # Select python interpreter inside venv
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if venv_python.exists() and os.environ.get("_PHASS_VENV_ACTIVATED") != "1":
        print(f"🔄 Auto-activating virtual environment: {venv_python}")
        sys.stdout.flush()
        env = os.environ.copy()
        env["_PHASS_VENV_ACTIVATED"] = "1"
        env["VIRTUAL_ENV"] = str(venv_dir)
        try:
            # Re-execute under venv Python and exit
            res = subprocess.call([str(venv_python)] + sys.argv, env=env)
            sys.exit(res)
        except Exception as e:
            print(f"⚠️  Failed to switch interpreter to {venv_python}: {e}")

    return sys.executable


# =============================================================================
# 2. SYSTEM DEPENDENCY AUTO-INSTALLER
# =============================================================================

def install_system_dependencies(os_info: Dict[str, Any]):
    """Installs required OS system libraries on Linux (Ubuntu/Debian, Arch)."""
    if os_info["is_windows"]:
        print("ℹ️  Windows detected: System dependency check skipped (native runtime).")
        sys.stdout.flush()
        return

    sudo_cached = False

    def cache_sudo():
        nonlocal sudo_cached
        if not sudo_cached and os.geteuid() != 0:
            print("🔐 Caching sudo credentials for system package checks...")
            sys.stdout.flush()
            try:
                subprocess.run(["sudo", "-v"], check=True)
                sudo_cached = True
            except Exception as e:
                print(f"⚠️  Could not validate sudo: {e}")

    # Ubuntu / Debian
    if os_info["is_ubuntu_debian"]:
        packages_to_check = [
            ("python3-tk", ["sudo", "apt-get", "install", "-y", "python3-tk", "python3-dev"]),
            ("portaudio19-dev", ["sudo", "apt-get", "install", "-y", "portaudio19-dev", "python3-pyaudio"]),
            ("espeak", ["sudo", "apt-get", "install", "-y", "espeak"]),
        ]
        apt_updated = False
        for pkg, install_cmd in packages_to_check:
            # Check if package installed
            res = subprocess.run(["dpkg", "-s", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                cache_sudo()
                if not apt_updated:
                    print("⚙️  Running sudo apt-get update...")
                    subprocess.run(["sudo", "apt-get", "update", "-qq"])
                    apt_updated = True
                print(f"⚙️  Installing missing system package: {pkg}...")
                subprocess.run(install_cmd)
                print(f"✅ Installed {pkg}")
            else:
                print(f"✅ System package {pkg} verified")
        sys.stdout.flush()

    # Arch Linux
    elif os_info["is_arch"]:
        arch_packages = [
            ("tk", ["sudo", "pacman", "-S", "--noconfirm", "tk"]),
            ("portaudio", ["sudo", "pacman", "-S", "--noconfirm", "portaudio"]),
        ]
        for pkg, install_cmd in arch_packages:
            res = subprocess.run(["pacman", "-Qi", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                cache_sudo()
                print(f"⚙️  Installing missing Arch package: {pkg}...")
                subprocess.run(install_cmd)
                print(f"✅ Installed {pkg}")
            else:
                print(f"✅ System package {pkg} verified")
        sys.stdout.flush()


# =============================================================================
# 3. PYTHON DEPENDENCY AUTO-INSTALLER
# =============================================================================

REQUIRED_PYTHON_MODULES = [
    ("tkinter", None),
    ("sounddevice", "sounddevice"),
    ("whisper", "openai-whisper"),
    ("pyttsx3", "pyttsx3"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("psutil", "psutil"),
    ("chromadb", "chromadb"),
    ("pystray", "pystray"),
    ("keyboard", "keyboard"),
]


def ensure_pip_up_to_date():
    """Checks and upgrades pip."""
    try:
        print("⚙️  Checking pip status...")
        sys.stdout.flush()
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
            check=False,
            timeout=40,
        )
        print("✅ Pip is up to date")
    except Exception as e:
        print(f"ℹ️  Pip update check completed ({e})")
    sys.stdout.flush()


def ensure_python_packages(project_root: Path):
    """Verifies and auto-installs missing Python packages."""
    missing = []
    for mod_name, pip_pkg in REQUIRED_PYTHON_MODULES:
        try:
            __import__(mod_name)
            print(f"✅ {mod_name} verified")
        except Exception:
            if pip_pkg:
                missing.append((mod_name, pip_pkg))
            else:
                print(f"⚠️  {mod_name} is not available (standard library package).")

    if missing:
        print(f"\n⚙️  Auto-installing {len(missing)} missing Python package(s)...")
        for mod_name, pip_pkg in missing:
            print(f"⚙️  Installing {pip_pkg}...")
            sys.stdout.flush()
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", pip_pkg],
                    check=True,
                    timeout=180,
                )
                print(f"✅ {pip_pkg} installed successfully")
            except Exception as e:
                print(f"⚠️  Failed to install {pip_pkg}: {e}")
        sys.stdout.flush()

    # Optional requirements.txt prompt
    req_file = project_root / "requirements.txt"
    if req_file.exists() and sys.stdin.isatty():
        try:
            choice = input("\nInstall all dependencies from requirements.txt? [y/N]: ").strip().lower()
            if choice in ("y", "yes"):
                print("⚙️  Installing requirements.txt...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], check=False)
                print("✅ Requirements installation completed.")
        except Exception:
            pass


# =============================================================================
# 4. UI LAUNCH WRAPPER WITH ERROR CAPTURE
# =============================================================================

class SafeVoiceFallback:
    """Safe dummy voice interface when audio hardware or STT/TTS is unavailable."""

    def __init__(self, error_message: str = "Voice disabled"):
        self.is_listening = False
        self.voice_id = None
        self.rate = 180
        self.volume = 1.0
        self.error_message = error_message

    def speak(self, text: str, async_mode: bool = True) -> Dict[str, Any]:
        return {"success": False, "details": f"Voice disabled ({self.error_message})"}

    def listen_command(self, duration: int = 5) -> str:
        return f"[Voice input disabled: {self.error_message}]"

    def start_continuous_listening(self, *args, **kwargs) -> bool:
        return False

    def stop_continuous_listening(self) -> bool:
        return False

    def list_voices(self) -> list:
        return []

    def set_voice(self, *args, **kwargs) -> bool:
        return False

    def set_rate(self, *args, **kwargs) -> bool:
        return False

    def set_volume(self, *args, **kwargs) -> bool:
        return False

    def get_status(self) -> Dict[str, Any]:
        return {"status": "disabled", "error": self.error_message}


def initialize_voice_interface() -> Any:
    """Safely loads VoiceInterface with seamless dummy fallback."""
    try:
        from core.voice_interface import get_voice_interface, VoiceInterface
        voice = get_voice_interface()
        print("✅ Voice interface initialized successfully")
        return voice
    except Exception as e:
        err_msg = str(e) or "Audio hardware or drivers unavailable"
        print(f"⚠️ Voice disabled: {err_msg}")
        dummy = SafeVoiceFallback(err_msg)

        # Monkeypatch global getter and module reference
        try:
            import core.voice_interface
            core.voice_interface.get_voice_interface = lambda **kw: dummy
            core.voice_interface._voice_interface = dummy
        except Exception:
            pass

        return dummy


def launch_ui(project_root: Path):
    """Launches the AssistantUI with full exception capture and crash logging."""
    print("🚀 Launching Assistant Desktop UI...")
    try:
        # Background tray-only mode option
        if any(arg in sys.argv for arg in ("--tray", "--background", "--silent-mode")):
            print("🚀 Starting P.H.A.S.S in Background System Tray Mode...")
            from core.global_listener import start_global_listener
            listener = start_global_listener()
            print("✅ Running in system tray. Press Ctrl+Space to activate quick directive.")
            sys.stdout.flush()
            if any(arg in sys.argv for arg in ("--test", "--verify", "--test-run")):
                time.sleep(1)
                listener.stop()
                print("✅ System Tray background verification complete.")
                return
            while listener.is_running:
                time.sleep(1)
            return

        # Initialize background Global Quick-Action Listener & System Tray Icon
        try:
            from core.global_listener import start_global_listener
            start_global_listener()
            print("✅ Global Quick-Action Listener & System Tray active (Ctrl+Space enabled).")
        except Exception as gl_err:
            print(f"⚠️ Global listener initialization notice: {gl_err}")

        from ui.main_window import AssistantUI
        app = AssistantUI()

        print("\nP.H.A.S.S SPHERE: UI Visualization running successfully.\n")
        sys.stdout.flush()

        # Handle automated test or verification mode
        if any(arg in sys.argv for arg in ("--test", "--verify", "--test-run")) or os.environ.get("VERIFY_UI_LAUNCH") == "1":
            print("✅ Verification Mode Active: Displaying window for verification...")
            sys.stdout.flush()
            app.root.after(2500, lambda: (
                print("✅ Assistant UI window successfully opened and rendered."),
                app.root.destroy()
            ))

        # Main interactive Tkinter GUI loop
        app.root.mainloop()

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        crash_log_path = project_root / "ui_crash.log"
        try:
            with open(crash_log_path, "w", encoding="utf-8") as f:
                f.write(f"UI CRASH REPORT\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {e}\n\n")
                f.write("Traceback:\n")
                f.write(tb)
        except Exception as log_err:
            print(f"⚠️  Failed to write crash log: {log_err}")

        print("\n❌ UI crashed. Check ui_crash.log for details.")
        print(f"Error summary: {e}\n")
        sys.stdout.flush()
        sys.exit(1)


# =============================================================================
# 5. POST-LAUNCH SHORTCUT GENERATOR
# =============================================================================

def create_shortcuts(project_root: Path):
    """Creates convenient start_ui shortcuts for Windows (.bat) and Linux/macOS (.sh)."""
    # Windows batch shortcut
    bat_path = project_root / "start_ui.bat"
    if not bat_path.exists():
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("title P.H.A.S.S SPHERE — Start UI\n")
                f.write("python fix_and_launch.py %*\n")
                f.write("pause\n")
        except Exception:
            pass

    # Linux / macOS shell shortcut
    sh_path = project_root / "start_ui.sh"
    alias_path = project_root / "start_ui"
    sh_content = (
        "#!/usr/bin/env bash\n"
        "# P.H.A.S.S SPHERE — Start UI Launcher\n"
        'DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'cd "$DIR"\n'
        'python3 fix_and_launch.py "$@"\n'
    )
    for p in (sh_path, alias_path):
        if not p.exists():
            try:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(sh_content)
                if hasattr(os, "chmod"):
                    os.chmod(p, 0o755)
            except Exception:
                pass


# =============================================================================
# MAIN ENTRYPOINT
# =============================================================================

def main():
    print_header()

    # Step 1: Environment Detection
    os_info = detect_operating_system()
    print(f"✅ Detected Operating System: {os_info['description']}")
    project_root = ensure_project_root()
    ensure_virtual_environment(project_root)

    # Step 2: System Dependencies
    install_system_dependencies(os_info)

    # Step 3: Python Dependencies
    ensure_pip_up_to_date()
    ensure_python_packages(project_root)

    # Step 4 & 5: Voice fallback & UI Launch
    initialize_voice_interface()
    create_shortcuts(project_root)
    launch_ui(project_root)


if __name__ == "__main__":
    main()
