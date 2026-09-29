"""
Clipboard Tool for Orvix Universal Control.
Reads and writes text content to/from the system clipboard.
"""

import platform
import subprocess
from typing import Any, Dict


def get_clipboard_text() -> Dict[str, Any]:
    """Retrieves current textual content from the system clipboard."""
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return {
                    "status": "SUCCESS",
                    "text": res.stdout.rstrip("\r\n"),
                    "length": len(res.stdout),
                }
            return {"status": "FAILED", "error": res.stderr.strip() or "Failed to read clipboard"}
        else:
            # Try xclip then xsel
            res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return {"status": "SUCCESS", "text": res.stdout}
            res2 = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True, timeout=5)
            if res2.returncode == 0:
                return {"status": "SUCCESS", "text": res2.stdout}
            return {"status": "FAILED", "error": "xclip or xsel required on Linux"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def set_clipboard_text(text: str) -> Dict[str, Any]:
    """Writes text content to the system clipboard."""
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            # Pass via stdin to Set-Clipboard to avoid escaping issues
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "Set-Clipboard -Value ($input | Out-String).TrimEnd()"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(input=text, timeout=5)
            if proc.returncode == 0:
                return {"status": "SUCCESS", "message": "Text copied to clipboard", "length": len(text)}
            return {"status": "FAILED", "error": stderr.strip() or "Set-Clipboard failed"}
        else:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True)
            proc.communicate(input=text, timeout=5)
            return {"status": "SUCCESS", "message": "Text copied to clipboard", "length": len(text)}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
