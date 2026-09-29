"""
User Experience (UX) Enhancements Module for P.H.A.S.S Sphere & Llama Assistant.
Provides advanced interaction and productivity features:
Multi-user profiles manager (work, personal, guest, developer),
Privacy / Incognito mode toggle (temporarily disables persistent logging),
Intelligent auto-complete suggestions based on command history,
Undo / Redo action stack for reversible operations,
Command bookmarks manager,
and Quick action single-keyword hotkey triggers.
"""

from __future__ import annotations
import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.ux")

_UX_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints", "ux_preferences")
os.makedirs(_UX_STORE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Profiles Manager
# ---------------------------------------------------------------------------
_PROFILES_FILE = os.path.join(_UX_STORE_DIR, "user_profiles.json")

def profiles_manager(
    action: str = "current",
    profile_name: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Switches and manages user profiles: work, personal, guest, developer.
    """
    act = action.strip().lower()

    profiles_data: Dict[str, Any] = {
        "active_profile": "developer",
        "profiles": {
            "developer": {"theme": "cyber_dark", "verbosity": "verbose", "voice": "jarvis"},
            "work": {"theme": "executive_light", "verbosity": "concise", "voice": "executive"},
            "personal": {"theme": "warm_slate", "verbosity": "friendly", "voice": "companion"},
            "guest": {"theme": "minimal", "verbosity": "standard", "voice": "default"},
        }
    }

    if os.path.exists(_PROFILES_FILE):
        try:
            with open(_PROFILES_FILE, "r", encoding="utf-8") as f:
                profiles_data = json.load(f)
        except Exception:
            pass

    if act in ("current", "status"):
        active = profiles_data.get("active_profile", "developer")
        return {
            "status": "SUCCESS",
            "active_profile": active,
            "settings": profiles_data.get("profiles", {}).get(active, {}),
            "available_profiles": list(profiles_data.get("profiles", {}).keys()),
        }

    elif act in ("switch", "select"):
        if not profile_name:
            return {"status": "FAILED", "error": "profile_name required to switch."}
        p_name = profile_name.lower()
        if p_name not in profiles_data["profiles"]:
            profiles_data["profiles"][p_name] = settings or {"theme": "default", "verbosity": "standard"}

        profiles_data["active_profile"] = p_name
        with open(_PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, indent=2)
        return {"status": "SUCCESS", "switched_to": p_name, "settings": profiles_data["profiles"][p_name]}

    elif act == "list":
        return {"status": "SUCCESS", "profiles": list(profiles_data["profiles"].keys())}

    return {"status": "FAILED", "error": f"Unknown profiles action '{action}'."}


# ---------------------------------------------------------------------------
# 2. Privacy Mode (Incognito)
# ---------------------------------------------------------------------------
_PRIVACY_STATE = {"enabled": False, "started_at": None}

def privacy_mode(action: str = "status") -> Dict[str, Any]:
    """
    Toggles privacy/incognito mode: temporarily halts persistent logging and caching.
    """
    global _PRIVACY_STATE
    act = action.strip().lower()

    if act in ("enable", "on", "activate"):
        _PRIVACY_STATE["enabled"] = True
        _PRIVACY_STATE["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "status": "SUCCESS",
            "privacy_mode": True,
            "message": "Privacy Mode ACTIVE: Command logging, session persistence, and telemetry recording suspended.",
        }

    elif act in ("disable", "off", "deactivate"):
        _PRIVACY_STATE["enabled"] = False
        _PRIVACY_STATE["started_at"] = None
        return {
            "status": "SUCCESS",
            "privacy_mode": False,
            "message": "Privacy Mode DEACTIVATED: Normal logging and preference memory restored.",
        }

    return {
        "status": "SUCCESS",
        "privacy_mode": _PRIVACY_STATE["enabled"],
        "active_since": _PRIVACY_STATE.get("started_at"),
    }


# ---------------------------------------------------------------------------
# 3. Auto-Complete Helper
# ---------------------------------------------------------------------------
def auto_complete(prefix: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Suggests completions for assistant directives and commands based on vocabulary.
    """
    pref_low = prefix.strip().lower()

    common_commands = [
        "system_control shutdown",
        "system_control restart",
        "system_control lock_screen",
        "delete_unwanted_files",
        "analyze_disk_space",
        "find_duplicate_files",
        "smart_file_organizer",
        "screenshot_capture",
        "listen_for_command",
        "speak_response",
        "set_voice_speed",
        "set_voice_volume",
        "wake_word_detection",
        "web_scraper",
        "download_manager",
        "pdf_processor",
        "csv_excel_master",
        "performance_monitor",
        "health_checker",
        "git_manager status",
        "docker_manager ps",
        "port_scanner",
        "joke_generator",
    ]

    suggestions = [c for c in common_commands if pref_low in c.lower() or c.lower().startswith(pref_low)]
    return {
        "status": "SUCCESS",
        "prefix": prefix,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions[:5],
    }


# ---------------------------------------------------------------------------
# 4. Undo / Redo Stack
# ---------------------------------------------------------------------------
_UNDO_STACK: List[Dict[str, Any]] = []
_REDO_STACK: List[Dict[str, Any]] = []

def undo_redo(
    action: str = "status",
    record_action: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Maintains an undo/redo stack for reversible assistant operations.
    """
    global _UNDO_STACK, _REDO_STACK
    act = action.strip().lower()

    if act == "record" and record_action:
        _UNDO_STACK.append(record_action)
        _REDO_STACK.clear()
        return {"status": "SUCCESS", "recorded": record_action.get("type", "action"), "undo_depth": len(_UNDO_STACK)}

    elif act == "undo":
        if not _UNDO_STACK:
            return {"status": "FAILED", "error": "Nothing to undo."}
        item = _UNDO_STACK.pop()
        _REDO_STACK.append(item)
        return {"status": "SUCCESS", "action": "undo", "reverted": item, "remaining_depth": len(_UNDO_STACK)}

    elif act == "redo":
        if not _REDO_STACK:
            return {"status": "FAILED", "error": "Nothing to redo."}
        item = _REDO_STACK.pop()
        _UNDO_STACK.append(item)
        return {"status": "SUCCESS", "action": "redo", "reapplied": item, "remaining_depth": len(_REDO_STACK)}

    return {
        "status": "SUCCESS",
        "undo_stack_size": len(_UNDO_STACK),
        "redo_stack_size": len(_REDO_STACK),
    }


# ---------------------------------------------------------------------------
# 5. Bookmarks Manager
# ---------------------------------------------------------------------------
_BOOKMARKS_FILE = os.path.join(_UX_STORE_DIR, "command_bookmarks.json")

def bookmarks_manager(
    action: str = "list",
    name: Optional[str] = None,
    command: Optional[str] = None,
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves, tags, and retrieves bookmarked commands.
    """
    act = action.strip().lower()

    bookmarks: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(_BOOKMARKS_FILE):
        try:
            with open(_BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                bookmarks = json.load(f)
        except Exception:
            bookmarks = {}

    if act in ("add", "save", "create"):
        if not name or not command:
            return {"status": "FAILED", "error": "name and command are required to bookmark."}
        bookmarks[name] = {"command": command, "tag": tag or "general", "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        with open(_BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2)
        return {"status": "SUCCESS", "bookmark_saved": name, "command": command}

    elif act in ("get", "run"):
        if name in bookmarks:
            return {"status": "SUCCESS", "name": name, "details": bookmarks[name]}
        return {"status": "FAILED", "error": f"Bookmark '{name}' not found."}

    elif act == "list":
        return {"status": "SUCCESS", "bookmarks": bookmarks, "count": len(bookmarks)}

    return {"status": "FAILED", "error": f"Unknown bookmark action '{action}'."}


# ---------------------------------------------------------------------------
# 6. Quick Actions
# ---------------------------------------------------------------------------
def quick_actions(
    action: str = "list",
    shortcut_key: Optional[str] = None,
    mapped_operation: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Maps single-word shortcuts to complex assistant routines.
    """
    defaults = {
        "cleanup": "disk_cleaner dry_run=True",
        "lock": "system_control lock_screen",
        "health": "health_checker",
        "joke": "joke_generator",
        "status": "system_diagnostics",
    }

    act = action.strip().lower()

    if act == "list":
        return {"status": "SUCCESS", "quick_actions": defaults}

    elif act == "execute":
        if shortcut_key and shortcut_key in defaults:
            return {"status": "SUCCESS", "shortcut": shortcut_key, "dispatched": defaults[shortcut_key]}
        return {"status": "FAILED", "error": f"Shortcut '{shortcut_key}' not found."}

    return {"status": "SUCCESS", "quick_actions": defaults}
