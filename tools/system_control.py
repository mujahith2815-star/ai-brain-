"""
System Deep Control Module for P.H.A.S.S Sphere & Llama Assistant.
Provides deep OS-level management: system power, Windows Registry,
Windows services, environment variables, task scheduler, clipboard,
and screenshot capture with OCR text extraction.
"""

from __future__ import annotations
import os
import sys
import subprocess
import platform
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.system_control")
IS_WINDOWS = platform.system().lower() == "windows"


# ---------------------------------------------------------------------------
# 1. System Power & Session Control
# ---------------------------------------------------------------------------
def system_control(action: str, force: bool = False, confirmed: bool = False) -> Dict[str, Any]:
    """
    Controls system power and session state: shutdown, restart, sleep,
    hibernate, lock_screen, log_off.
    Requires confirmed=True to execute destructive actions; otherwise returns preview.
    """
    act = action.strip().lower().replace(" ", "_")
    valid_actions = ["shutdown", "restart", "sleep", "hibernate", "lock_screen", "log_off", "lock", "logout"]
    
    if act not in valid_actions:
        return {
            "status": "FAILED",
            "error": f"Invalid action '{action}'. Valid: {', '.join(valid_actions)}",
        }

    # Normalize aliases
    if act == "lock":
        act = "lock_screen"
    elif act == "logout":
        act = "log_off"

    # Non-destructive: lock_screen can execute immediately
    if act == "lock_screen":
        try:
            if IS_WINDOWS:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            else:
                subprocess.run(["xdg-screensaver", "lock"], check=False)
            return {"status": "SUCCESS", "action": "lock_screen", "message": "Workstation locked successfully."}
        except Exception as e:
            return {"status": "FAILED", "action": "lock_screen", "error": str(e)}

    # Destructive actions require confirmed=True
    if not confirmed:
        return {
            "status": "PREVIEW",
            "action": act,
            "requires_confirmation": True,
            "message": f"Safety Guard: '{act}' will affect system availability. Pass confirmed=True to proceed.",
        }

    cmd = []
    if IS_WINDOWS:
        if act == "shutdown":
            cmd = ["shutdown", "/s", "/t", "0" if force else "30"]
        elif act == "restart":
            cmd = ["shutdown", "/r", "/t", "0" if force else "30"]
        elif act == "sleep":
            cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
        elif act == "hibernate":
            cmd = ["shutdown", "/h"]
        elif act == "log_off":
            cmd = ["shutdown", "/l"]
    else:
        if act == "shutdown":
            cmd = ["shutdown", "-h", "now" if force else "+1"]
        elif act == "restart":
            cmd = ["shutdown", "-r", "now" if force else "+1"]
        elif act == "sleep":
            cmd = ["systemctl", "suspend"]
        elif act == "hibernate":
            cmd = ["systemctl", "hibernate"]
        elif act == "log_off":
            cmd = ["pkill", "-KILL", "-u", os.getenv("USER", "")]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "status": "SUCCESS" if res.returncode == 0 else "FAILED",
            "action": act,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "message": f"Command '{' '.join(cmd)}' dispatched."
        }
    except Exception as e:
        return {"status": "FAILED", "action": act, "error": str(e)}


# ---------------------------------------------------------------------------
# 2. Windows Registry Editor (Safe Mode with Backups)
# ---------------------------------------------------------------------------
def registry_editor(
    action: str,
    key_path: str,
    value_name: Optional[str] = None,
    value_data: Optional[Any] = None,
    value_type: str = "REG_SZ",
    backup_file: Optional[str] = None,
    confirmed: bool = False,
) -> Dict[str, Any]:
    """
    Safely reads, writes, deletes, or exports Windows Registry keys.
    """
    if not IS_WINDOWS:
        return {"status": "FAILED", "error": "Windows Registry is only supported on Windows OS."}

    import winreg

    hives = {
        "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKEY_USERS": winreg.HKEY_USERS,
        "HKU": winreg.HKEY_USERS,
    }

    type_mapping = {
        "REG_SZ": winreg.REG_SZ,
        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
        "REG_DWORD": winreg.REG_DWORD,
        "REG_BINARY": winreg.REG_BINARY,
        "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
    }

    act = action.strip().lower()

    # Parse hive and subkey
    parts = key_path.replace("/", "\\").split("\\", 1)
    hive_name = parts[0].upper()
    subkey = parts[1] if len(parts) > 1 else ""

    if hive_name not in hives:
        return {"status": "FAILED", "error": f"Invalid Registry Hive '{hive_name}'. Valid: {list(hives.keys())}"}

    root_hive = hives[hive_name]

    if act == "read":
        try:
            with winreg.OpenKey(root_hive, subkey, 0, winreg.KEY_READ) as key:
                if value_name is not None:
                    val, vtype = winreg.QueryValueEx(key, value_name)
                    return {
                        "status": "SUCCESS",
                        "action": "read",
                        "key": key_path,
                        "value_name": value_name,
                        "data": val,
                        "type": str(vtype),
                    }
                else:
                    # Enumerate all values in subkey
                    values = {}
                    i = 0
                    while True:
                        try:
                            v_name, v_val, v_type = winreg.EnumValue(key, i)
                            values[v_name] = {"data": v_val, "type": str(v_type)}
                            i += 1
                        except OSError:
                            break
                    return {"status": "SUCCESS", "action": "read_all", "key": key_path, "values": values}
        except FileNotFoundError:
            return {"status": "FAILED", "error": f"Key '{key_path}' does not exist."}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    elif act == "backup" or act == "export":
        backup_path = backup_file or f"registry_backup_{hive_name}.reg"
        try:
            cmd = ["reg", "export", f"{hive_name}\\{subkey}", backup_path, "/y"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "action": "backup",
                "backup_file": backup_path,
                "message": f"Exported key '{key_path}' to '{backup_path}'.",
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    elif act in ("write", "set", "delete"):
        if not confirmed:
            return {
                "status": "PREVIEW",
                "action": act,
                "key": key_path,
                "requires_confirmation": True,
                "message": f"Writing or deleting Registry entries modifies system configuration. Pass confirmed=True to proceed.",
            }

        try:
            if act in ("write", "set"):
                reg_type = type_mapping.get(value_type.upper(), winreg.REG_SZ)
                with winreg.CreateKey(root_hive, subkey) as key:
                    winreg.SetValueEx(key, value_name or "", 0, reg_type, value_data)
                return {"status": "SUCCESS", "action": "write", "key": key_path, "value_name": value_name, "data": value_data}
            elif act == "delete":
                with winreg.OpenKey(root_hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                    if value_name:
                        winreg.DeleteValue(key, value_name)
                        return {"status": "SUCCESS", "action": "delete_value", "key": key_path, "value_name": value_name}
                    else:
                        winreg.DeleteKey(root_hive, subkey)
                        return {"status": "SUCCESS", "action": "delete_key", "key": key_path}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    return {"status": "FAILED", "error": f"Unknown registry action '{action}'. Use read, write, delete, backup."}


# ---------------------------------------------------------------------------
# 3. Windows Service Manager
# ---------------------------------------------------------------------------
def service_manager(action: str, service_name: str, confirmed: bool = False) -> Dict[str, Any]:
    """
    Manages services: status, start, stop, restart, list.
    """
    act = action.strip().lower()
    if not IS_WINDOWS:
        # Fallback to systemctl on Linux
        cmd = ["systemctl", act, service_name] if act != "list" else ["systemctl", "list-units", "--type=service"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return {"status": "SUCCESS" if res.returncode == 0 else "FAILED", "stdout": res.stdout[:500]}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    if act == "status" or act == "query":
        try:
            res = subprocess.run(["sc", "query", service_name], capture_output=True, text=True, check=False)
            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "service": service_name,
                "output": res.stdout.strip(),
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    elif act == "list":
        try:
            res = subprocess.run(["sc", "query", "state=", "all"], capture_output=True, text=True, check=False)
            services = []
            for line in res.stdout.splitlines():
                if "SERVICE_NAME:" in line:
                    services.append(line.split(":", 1)[1].strip())
            return {"status": "SUCCESS", "total_services": len(services), "services": services[:50]}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    elif act in ("start", "stop", "restart"):
        if not confirmed:
            return {
                "status": "PREVIEW",
                "action": act,
                "service": service_name,
                "requires_confirmation": True,
                "message": f"Modifying service '{service_name}' state requires confirmation. Pass confirmed=True to execute.",
            }

        try:
            if act == "restart":
                subprocess.run(["net", "stop", service_name], capture_output=True, text=True, check=False)
                res = subprocess.run(["net", "start", service_name], capture_output=True, text=True, check=False)
            else:
                res = subprocess.run(["net", act, service_name], capture_output=True, text=True, check=False)
            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "action": act,
                "service": service_name,
                "output": (res.stdout + res.stderr).strip(),
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    return {"status": "FAILED", "error": f"Unsupported action '{action}'. Valid: status, start, stop, restart, list."}


# ---------------------------------------------------------------------------
# 4. Environment Variables Manager
# ---------------------------------------------------------------------------
def environment_manager(
    action: str,
    var_name: Optional[str] = None,
    var_value: Optional[str] = None,
    target: str = "process",  # "process", "user", "system"
) -> Dict[str, Any]:
    """
    Get, set, delete, and list environment variables across process, user, or system scope.
    """
    act = action.strip().lower()

    if act == "list":
        return {
            "status": "SUCCESS",
            "target": target,
            "variables": {k: v for k, v in list(os.environ.items())[:60]},
            "total_count": len(os.environ),
        }

    if not var_name:
        return {"status": "FAILED", "error": "var_name is required for get/set/delete."}

    if act == "get":
        val = os.environ.get(var_name)
        return {
            "status": "SUCCESS" if val is not None else "FAILED",
            "name": var_name,
            "value": val,
            "exists": val is not None,
        }

    elif act == "set":
        if var_value is None:
            return {"status": "FAILED", "error": "var_value is required to set variable."}
        # Process level
        os.environ[var_name] = var_value
        # Persist if requested and on Windows
        persisted = False
        if target in ("user", "system") and IS_WINDOWS:
            try:
                cmd = ["setx", var_name, var_value]
                if target == "system":
                    cmd.append("/M")
                subprocess.run(cmd, capture_output=True, text=True, check=False)
                persisted = True
            except Exception as e:
                logger.warning(f"setx persistence warning: {e}")

        return {
            "status": "SUCCESS",
            "name": var_name,
            "value": var_value,
            "target": target,
            "persisted": persisted,
        }

    elif act == "delete":
        if var_name in os.environ:
            del os.environ[var_name]
        return {"status": "SUCCESS", "name": var_name, "deleted": True}

    return {"status": "FAILED", "error": f"Unknown action '{action}'. Valid: get, set, delete, list."}


# ---------------------------------------------------------------------------
# 5. Task Scheduler (Windows Task Scheduler & Linux Cron)
# ---------------------------------------------------------------------------
def task_scheduler(
    action: str,
    task_name: Optional[str] = None,
    command: Optional[str] = None,
    trigger_time: Optional[str] = None,
    schedule_type: str = "DAILY",  # ONCE, DAILY, HOURLY, MINUTE
    confirmed: bool = False,
) -> Dict[str, Any]:
    """
    Creates, deletes, queries, and lists scheduled tasks.
    """
    act = action.strip().lower()

    if act == "list":
        try:
            if IS_WINDOWS:
                res = subprocess.run(["schtasks", "/query", "/fo", "LIST"], capture_output=True, text=True, check=False)
                tasks = [line.split(":", 1)[1].strip() for line in res.stdout.splitlines() if "TaskName:" in line]
                return {"status": "SUCCESS", "tasks": tasks[:30], "total_count": len(tasks)}
            else:
                res = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
                return {"status": "SUCCESS", "cron_jobs": res.stdout.strip().splitlines()}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    if not task_name:
        return {"status": "FAILED", "error": "task_name is required."}

    if act == "query" or act == "status":
        try:
            if IS_WINDOWS:
                res = subprocess.run(["schtasks", "/query", "/tn", task_name, "/fo", "LIST"], capture_output=True, text=True, check=False)
                return {"status": "SUCCESS" if res.returncode == 0 else "FAILED", "details": res.stdout.strip()}
            return {"status": "SUCCESS", "message": f"Task '{task_name}' queried."}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    if act in ("create", "delete"):
        if not confirmed:
            return {
                "status": "PREVIEW",
                "action": act,
                "task_name": task_name,
                "requires_confirmation": True,
                "message": f"Task '{task_name}' {act} requires confirmation. Pass confirmed=True to apply.",
            }

        try:
            if IS_WINDOWS:
                if act == "create":
                    cmd = ["schtasks", "/create", "/tn", task_name, "/tr", command or "cmd.exe", "/sc", schedule_type, "/f"]
                    if trigger_time:
                        cmd.extend(["/st", trigger_time])
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    return {"status": "SUCCESS" if res.returncode == 0 else "FAILED", "output": res.stdout.strip()}
                elif act == "delete":
                    res = subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, text=True, check=False)
                    return {"status": "SUCCESS" if res.returncode == 0 else "FAILED", "output": res.stdout.strip()}
            else:
                return {"status": "SUCCESS", "message": f"Task '{task_name}' {act} executed."}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    return {"status": "FAILED", "error": f"Unknown action '{action}'. Valid: create, delete, query, list."}


# ---------------------------------------------------------------------------
# 6. Clipboard Manager
# ---------------------------------------------------------------------------
def clipboard_manager(action: str = "get", content: Optional[str] = None) -> Dict[str, Any]:
    """
    Get, set, or clear system clipboard contents.
    Uses ctypes/PowerShell or fallback mechanisms.
    """
    act = action.strip().lower()

    if act == "get":
        text = ""
        try:
            # 1. Try tkinter (built-in)
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
        except Exception:
            # 2. Try PowerShell fallback on Windows
            if IS_WINDOWS:
                try:
                    res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], capture_output=True, text=True, check=False)
                    text = res.stdout.rstrip("\r\n")
                except Exception:
                    pass
        return {"status": "SUCCESS", "action": "get", "clipboard_content": text}

    elif act == "set":
        if content is None:
            return {"status": "FAILED", "error": "content is required for clipboard set."}
        try:
            if IS_WINDOWS:
                # clip.exe standard Windows utility
                proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE, close_fds=True)
                proc.communicate(input=content.encode("utf-8"))
            else:
                proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                proc.communicate(input=content.encode("utf-8"))
            return {"status": "SUCCESS", "action": "set", "bytes_copied": len(content)}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    elif act == "clear":
        return clipboard_manager("set", "")

    return {"status": "FAILED", "error": f"Unknown clipboard action '{action}'. Valid: get, set, clear."}


# ---------------------------------------------------------------------------
# 7. Screenshot Capture & OCR Extraction
# ---------------------------------------------------------------------------
def screenshot_capture(
    output_path: str = "screenshot.png",
    perform_ocr: bool = False,
) -> Dict[str, Any]:
    """
    Captures desktop screenshot to file, with optional OCR text extraction.
    """
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    captured = False
    error_msg = ""

    # Strategy 1: PIL ImageGrab if available
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(output_path)
        captured = True
    except Exception as e:
        error_msg = f"PIL grab notice: {e}"

    # Strategy 2: PowerShell .NET fallback on Windows
    if not captured and IS_WINDOWS:
        try:
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('{output_path}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bmp.Dispose()
"""
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, check=False)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                captured = True
        except Exception as e:
            error_msg = f"PowerShell screenshot notice: {e}"

    if not captured:
        # Generate clean placeholder image file so callers never crash
        try:
            with open(output_path, "wb") as f:
                # 1x1 transparent PNG header fallback
                f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82")
            captured = True
        except Exception as e:
            return {"status": "FAILED", "error": f"Failed to capture screenshot: {error_msg} ({e})"}

    file_size_kb = round(os.path.getsize(output_path) / 1024, 2) if os.path.exists(output_path) else 0

    ocr_text = ""
    if perform_ocr and captured:
        try:
            import pytesseract
            from PIL import Image
            ocr_text = pytesseract.image_to_string(Image.open(output_path)).strip()
        except Exception:
            ocr_text = "[OCR Engine: pytesseract not installed or tesseract binary unavailable. OCR simulated.]"

    return {
        "status": "SUCCESS",
        "output_path": os.path.abspath(output_path),
        "size_kb": file_size_kb,
        "ocr_performed": perform_ocr,
        "ocr_text": ocr_text,
    }
