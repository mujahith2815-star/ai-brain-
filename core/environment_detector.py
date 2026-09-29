"""
Universal Environment & Hardware Profiler for Llama Assistant & P.H.A.S.S Sphere.
Detects:
1. OS, distribution (Ubuntu, Debian, Arch, Fedora, Alpine), Windows, macOS, and WSL.
2. Hardware resources: CPU cores, architecture, total/free RAM, and GPU/VRAM acceleration.
3. Package managers: apt, dnf, pacman, brew, winget, choco, pip, uv.
4. Runtimes: Python, Git, Ollama, Docker, FFmpeg, Curl.
5. Recommendation engine for optimal local Llama parameter tier (1B, 3B, 8B, 70B).
"""

from __future__ import annotations
import os
import sys
import shutil
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.core.env")


def is_wsl() -> bool:
    """Detects whether running inside Windows Subsystem for Linux (WSL)."""
    if platform.system().lower() != "linux":
        return False
    try:
        if Path("/proc/version").exists():
            version_text = Path("/proc/version").read_text().lower()
            return "microsoft" in version_text or "wsl" in version_text
    except Exception:
        pass
    return False


def detect_os() -> Dict[str, Any]:
    """Detects detailed operating system, kernel, and distribution information."""
    sys_name = platform.system()
    info = {
        "system": sys_name,
        "release": platform.release(),
        "version": platform.version(),
        "is_windows": sys_name == "Windows",
        "is_linux": sys_name == "Linux",
        "is_macos": sys_name == "Darwin",
        "is_wsl": is_wsl(),
        "distro": "N/A",
        "distro_id": "N/A",
    }

    if info["is_linux"]:
        # Inspect /etc/os-release
        os_release = Path("/etc/os-release")
        if os_release.exists():
            try:
                content = os_release.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.startswith("PRETTY_NAME="):
                        info["distro"] = line.split("=", 1)[1].strip('"\'')
                    elif line.startswith("ID="):
                        info["distro_id"] = line.split("=", 1)[1].strip('"\'')
            except Exception:
                pass
        if info["distro"] == "N/A":
            info["distro"] = "Generic Linux"

    elif info["is_windows"]:
        info["distro"] = f"Windows {platform.release()}"
        info["distro_id"] = "windows"

    elif info["is_macos"]:
        info["distro"] = f"macOS {platform.mac_ver()[0]}"
        info["distro_id"] = "macos"

    return info


def detect_hardware() -> Dict[str, Any]:
    """Detects CPU, RAM, GPU, and local disk resources."""
    cpu_cores = os.cpu_count() or 4
    arch = platform.machine() or "x86_64"

    ram_total_gb = 16.0
    ram_avail_gb = 8.0

    # 1. Try psutil
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_total_gb = round(mem.total / (1024**3), 2)
        ram_avail_gb = round(mem.available / (1024**3), 2)
    except ImportError:
        # Fallback for Linux /proc/meminfo
        if Path("/proc/meminfo").exists():
            try:
                meminfo = Path("/proc/meminfo").read_text()
                total_kb = 0
                avail_kb = 0
                for line in meminfo.splitlines():
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail_kb = int(line.split()[1])
                if total_kb > 0:
                    ram_total_gb = round(total_kb / (1024**2), 2)
                    ram_avail_gb = round(avail_kb / (1024**2), 2)
            except Exception:
                pass

    # Disk usage
    disk_total_gb, disk_used_gb, disk_free_gb = 100.0, 50.0, 50.0
    try:
        total, used, free = shutil.disk_usage(".")
        disk_total_gb = round(total / (1024**3), 2)
        disk_used_gb = round(used / (1024**3), 2)
        disk_free_gb = round(free / (1024**3), 2)
    except Exception:
        pass

    # GPU Detection
    gpu_name = "CPU Only (No dedicated accelerator detected)"
    has_nvidia = shutil.which("nvidia-smi") is not None
    if has_nvidia:
        try:
            res = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                gpu_name = f"NVIDIA: {res.stdout.strip().splitlines()[0]}"
        except Exception:
            gpu_name = "NVIDIA CUDA GPU"
    elif platform.system() == "Darwin" and "arm" in arch.lower():
        gpu_name = "Apple Silicon Metal Unified GPU"

    return {
        "cpu_cores": cpu_cores,
        "cpu_arch": arch,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_avail_gb,
        "disk_free_gb": disk_free_gb,
        "disk_total_gb": disk_total_gb,
        "gpu": gpu_name,
        "has_cuda": has_nvidia,
    }


def detect_package_managers() -> List[str]:
    """Scans for available system package managers."""
    candidates = ["apt", "apt-get", "dnf", "yum", "pacman", "zypper", "brew", "winget", "choco", "scoop", "pip", "uv"]
    found = []
    for tool in candidates:
        if shutil.which(tool) is not None:
            found.append(tool)
    return found


def detect_runtimes() -> Dict[str, bool]:
    """Checks for essential command-line runtimes and servers."""
    tools = ["python", "git", "ollama", "docker", "ffmpeg", "curl", "node"]
    status = {}
    for t in tools:
        status[t] = shutil.which(t) is not None
    return status


def recommend_llama_tier(hw: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Recommends the ideal Llama model tier based on available system hardware."""
    hw = hw or detect_hardware()
    ram = hw.get("ram_total_gb", 8.0)
    has_cuda = hw.get("has_cuda", False)

    if ram >= 64.0:
        return {
            "recommended_model": "llama3:70b",
            "tier": "HEAVYWEIGHT (70B)",
            "reason": f"System has {ram}GB RAM; fully capable of 70B quantized inference.",
        }
    elif ram >= 16.0 or has_cuda:
        return {
            "recommended_model": "llama3:8b",
            "tier": "SWEET SPOT (8B)",
            "reason": f"System has {ram}GB RAM / GPU; ideal balance of intelligence, speed, and tool calling.",
        }
    elif ram >= 8.0:
        return {
            "recommended_model": "llama3.2:3b",
            "tier": "LIGHTWEIGHT (3B)",
            "reason": f"System has {ram}GB RAM; optimized for low latency on consumer CPUs.",
        }
    else:
        return {
            "recommended_model": "llama3.2:1b",
            "tier": "ULTRA-COMPACT (1B)",
            "reason": f"System has {ram}GB RAM; suitable for resource-constrained edge machines.",
        }


def get_environment_report() -> Dict[str, Any]:
    """Generates an exhaustive diagnostic report of the host environment."""
    os_info = detect_os()
    hw_info = detect_hardware()
    pm_info = detect_package_managers()
    rt_info = detect_runtimes()
    rec = recommend_llama_tier(hw_info)

    return {
        "os": os_info,
        "hardware": hw_info,
        "package_managers": pm_info,
        "runtimes": rt_info,
        "recommendation": rec,
        "python_version": platform.python_version(),
    }
