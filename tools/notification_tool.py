"""
Desktop Notification Controller for Orvix Universal Control.
Dispatches native OS desktop toast/balloon notifications.
"""

import platform
import subprocess
from typing import Any, Dict


def show_notification(title: str, message: str, duration_sec: int = 5) -> Dict[str, Any]:
    """
    Displays a native desktop notification toast with title and message.
    """
    clean_title = title.replace("'", "''").strip()
    clean_msg = message.replace("'", "''").strip()
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            ms = duration_sec * 1000
            ps_cmd = (
                "[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                "$notify = New-Object System.Windows.Forms.NotifyIcon; "
                "$notify.Icon = [System.Drawing.SystemIcons]::Information; "
                "$notify.Visible = $true; "
                f"$notify.ShowBalloonTip({ms}, '{clean_title}', '{clean_msg}', [System.Windows.Forms.ToolTipIcon]::Info); "
                "Start-Sleep -Milliseconds 100; "
                "$notify.Dispose();"
            )
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "status": "SUCCESS",
                "title": title,
                "message": message,
                "duration_seconds": duration_sec,
            }
        else:
            subprocess.Popen(
                ["notify-send", title, message, f"-t", str(duration_sec * 1000)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {
                "status": "SUCCESS",
                "title": title,
                "message": message,
                "duration_seconds": duration_sec,
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
