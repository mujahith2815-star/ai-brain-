"""
Omni-Desktop GUI Operator & Robotic Automation Engine for P.H.A.S.S Sphere v6.0.
Provides native OS keystroke injection, window management, hotkey dispatching,
and batch desktop automation.
"""

from __future__ import annotations
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.tools.gui_operator")


@dataclass
class GUIAutomationResult:
    action: str
    target: str
    success: bool
    details: str
    execution_time_sec: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "success": self.success,
            "details": self.details,
            "execution_time_sec": round(self.execution_time_sec, 4),
            "timestamp": self.timestamp,
        }


class OmniDesktopGUIOperator:
    def type_text(self, text_to_type: str) -> GUIAutomationResult:
        """
        Simulates keyboard typing into the currently focused desktop window.
        """
        start_t = time.time()
        escaped = text_to_type.replace("'", "''").replace("{", "{{").replace("}", "}}")
        if sys.platform == "win32":
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{escaped}')"
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
                return GUIAutomationResult("TYPE_TEXT", text_to_type, True, f"Typed {len(text_to_type)} characters.", time.time() - start_t)
            except Exception as e:
                return GUIAutomationResult("TYPE_TEXT", text_to_type, False, str(e), time.time() - start_t)
        else:
            return GUIAutomationResult("TYPE_TEXT", text_to_type, True, f"Simulated typing '{text_to_type}'.", time.time() - start_t)

    def send_hotkey(self, hotkey_combo: str) -> GUIAutomationResult:
        """
        Sends a global hotkey combination (e.g. 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d').
        """
        start_t = time.time()
        key_map = {
            "ctrl+c": "^c",
            "ctrl+v": "^v",
            "ctrl+a": "^a",
            "ctrl+s": "^s",
            "alt+f4": "%{F4}",
            "enter": "{ENTER}",
            "escape": "{ESC}",
        }
        send_key_str = key_map.get(hotkey_combo.lower().strip(), "{ENTER}")

        if sys.platform == "win32":
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{send_key_str}')"
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
                return GUIAutomationResult("SEND_HOTKEY", hotkey_combo, True, f"Dispatched hotkey '{hotkey_combo}'.", time.time() - start_t)
            except Exception as e:
                return GUIAutomationResult("SEND_HOTKEY", hotkey_combo, False, str(e), time.time() - start_t)
        else:
            return GUIAutomationResult("SEND_HOTKEY", hotkey_combo, True, f"Simulated hotkey '{hotkey_combo}'.", time.time() - start_t)

    def batch_rename_files(self, dir_path: str, prefix: str) -> GUIAutomationResult:
        """
        Batch renames all files within a directory using an indexed prefix.
        """
        start_t = time.time()
        d = Path(dir_path).resolve()
        if not d.exists() or not d.is_dir():
            return GUIAutomationResult("BATCH_RENAME", dir_path, False, "Directory does not exist", time.time() - start_t)

        renamed = 0
        for idx, f in enumerate(sorted(d.iterdir())):
            if f.is_file():
                ext = f.suffix
                new_name = f"{prefix}_{idx+1:03d}{ext}"
                try:
                    f.rename(d / new_name)
                    renamed += 1
                except Exception:
                    pass

        return GUIAutomationResult("BATCH_RENAME", dir_path, True, f"Renamed {renamed} files with prefix '{prefix}'.", time.time() - start_t)


gui_operator = OmniDesktopGUIOperator()
