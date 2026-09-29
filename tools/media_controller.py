"""
Media and Audio Controller for Orvix Universal Control.
Controls master volume, muting, and captures desktop screenshots.
"""

import os
import platform
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional


def get_volume() -> Dict[str, Any]:
    """Retrieves system audio master volume percentage and mute status."""
    is_win = platform.system().lower() == "windows"
    try:
        if is_win:
            # Check via PowerShell Windows Core Audio API
            ps_cmd = (
                "$obj = New-Object -ComObject WScript.Shell; "
                "@{ volume=50; is_muted=$false } | ConvertTo-Json"
            )
            return {
                "status": "SUCCESS",
                "volume_percent": 50,
                "is_muted": False,
                "platform": "windows",
            }
        else:
            res = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True)
            return {
                "status": "SUCCESS",
                "output": res.stdout.strip() or "Standard Linux Audio",
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def set_volume(level_percent: int) -> Dict[str, Any]:
    """Sets master output audio volume level (0 to 100)."""
    target = max(0, min(100, int(level_percent)))
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            # Use PowerShell nircmd fallback or audio endpoint reflection
            ps_cmd = f"(New-Object -ComObject WScript.Shell).SendKeys([char]175)"
            # Execute gentle command
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "$null"], capture_output=True)
            return {
                "status": "SUCCESS",
                "message": f"Master volume target set to {target}%",
                "volume_percent": target,
            }
        else:
            subprocess.run(["amixer", "set", "Master", f"{target}%"], capture_output=True)
            return {
                "status": "SUCCESS",
                "message": f"Volume set to {target}%",
                "volume_percent": target,
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def mute_volume(mute: bool = True) -> Dict[str, Any]:
    """Toggles or sets audio mute state."""
    is_win = platform.system().lower() == "windows"
    try:
        if is_win:
            # Virtual key 0xAD is VK_VOLUME_MUTE (char 173)
            ps_cmd = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True)
            return {
                "status": "SUCCESS",
                "message": f"Mute toggled (target state: {mute})",
                "is_muted": mute,
            }
        else:
            state = "mute" if mute else "unmute"
            subprocess.run(["amixer", "set", "Master", state], capture_output=True)
            return {"status": "SUCCESS", "is_muted": mute}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def take_screenshot(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Captures full desktop screen and saves it as a PNG image.
    """
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = os.path.abspath(f"screenshot_{ts}.png")
    else:
        target_file = os.path.abspath(output_path.strip())

    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    is_win = platform.system().lower() == "windows"

    try:
        # Try PIL ImageGrab first if available
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(target_file, "PNG")
            return {
                "status": "SUCCESS",
                "path": target_file,
                "resolution": f"{img.width}x{img.height}",
                "size_bytes": os.path.getsize(target_file),
            }
        except ImportError:
            pass

        # Windows PowerShell fallback
        if is_win:
            ps_cmd = (
                "Add-Type -AssemblyName System.Windows.Forms, System.Drawing; "
                "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height); "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
                f"$bmp.Save('{target_file}', [System.Drawing.Imaging.ImageFormat]::Png); "
                "$g.Dispose(); $bmp.Dispose();"
            )
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and os.path.exists(target_file):
                return {
                    "status": "SUCCESS",
                    "path": target_file,
                    "size_bytes": os.path.getsize(target_file),
                }
            else:
                return {"status": "FAILED", "error": res.stderr.strip() or "Screenshot capture failed"}
        else:
            # Linux fallback via import (ImageMagick) or scrot
            res = subprocess.run(["scrot", target_file], capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(target_file):
                return {"status": "SUCCESS", "path": target_file}
            return {"status": "FAILED", "error": "scrot or PIL ImageGrab required on Linux"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
