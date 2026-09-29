"""
Computer & GUI Automation Tool for P.H.A.S.S Sphere / J.A.R.V.I.S.
Allows the AI to simulate keyboard typing, hotkeys, mouse clicks, and window shortcuts on the host OS.
"""

from __future__ import annotations
import os
import subprocess
import sys
import time
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("phass.tools.computer_automation")


class ComputerGUIAutomation:
    def __init__(self):
        self.action_count = 0

    def type_text(self, text: str) -> Tuple[bool, str]:
        """
        Types a string into the currently focused active window using Windows SendKeys.
        """
        if sys.platform == "win32":
            # Sanitize special characters in SendKeys (+, ^, %, ~, (, ), {, })
            escaped = text.replace("{", "{{}").replace("}", "{}}").replace("+", "{+}").replace("^", "{^}").replace("%", "{%}").replace("~", "{~}").replace("'", "''")
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{escaped}')"
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
                self.action_count += 1
                return True, f"Typed {len(text)} characters into active window."
            except Exception as e:
                return False, f"Failed to type text: {e}"
        return True, "Simulated text typing on non-Windows host."

    def send_shortcut(self, shortcut_name: str) -> Tuple[bool, str]:
        """
        Sends a standard keyboard shortcut (e.g. 'COPY', 'PASTE', 'SAVE', 'DESKTOP', 'ENTER').
        """
        s_clean = shortcut_name.strip().upper()

        key_map = {
            "COPY": "^c",
            "PASTE": "^v",
            "SAVE": "^s",
            "SELECT_ALL": "^a",
            "ENTER": "{ENTER}",
            "TAB": "{TAB}",
            "ESCAPE": "{ESC}",
            "DESKTOP": "^{ESC}", # Or Win key
        }

        if s_clean not in key_map:
            return False, f"Unknown shortcut '{shortcut_name}'. Available: {list(key_map.keys())}"

        send_str = key_map[s_clean]
        if sys.platform == "win32":
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{send_str}')"
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
                self.action_count += 1
                return True, f"Triggered shortcut: {s_clean}"
            except Exception as e:
                return False, f"Failed to trigger shortcut: {e}"
        return True, f"Simulated shortcut: {s_clean}"

    def click_mouse(self, x: int, y: int, button: str = "LEFT") -> Tuple[bool, str]:
        """
        Moves the mouse cursor and clicks on the specified screen coordinate.
        """
        if sys.platform == "win32":
            ps_cmd = (
                "$sig = '[DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X, int Y); "
                "[DllImport(\"user32.dll\")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);'; "
                "Add-Type -MemberDefinition $sig -Name MouseUtils -Namespace Win32; "
                f"[Win32.MouseUtils]::SetCursorPos({x}, {y}); "
                "[Win32.MouseUtils]::mouse_event(0x02, 0, 0, 0, 0); " # LEFTDOWN
                "[Win32.MouseUtils]::mouse_event(0x04, 0, 0, 0, 0); " # LEFTUP
            )
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
                self.action_count += 1
                return True, f"Moved mouse and clicked at ({x}, {y})."
            except Exception as e:
                return False, f"Mouse click error: {e}"
        return True, f"Simulated mouse click at ({x}, {y})."


computer_automation = ComputerGUIAutomation()
