"""
User Preferences Memory Management for P.H.A.S.S / NICON.
Stores and persists user favorite directories, frequently used commands,
and custom operational preferences in JSON format.
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.llama_config import llama_config

logger = logging.getLogger("phass.core.user_preferences")


class UserPreferencesManager:
    """Manages persistent user preferences, favorite directories, and common commands."""

    def __init__(self, file_path: Optional[str] = None):
        if file_path:
            self.file_path = Path(file_path)
        else:
            try:
                from core.data_hub import data_hub
                self.file_path = data_hub.resolve("user", "preferences.json")
            except Exception:
                self.file_path = Path(llama_config.preferences_path)
        self.preferences: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Loads preferences from JSON file or initializes defaults."""
        target_path = self.file_path
        if not target_path.exists():
            legacy_path = Path(llama_config.preferences_path)
            if legacy_path.exists():
                target_path = legacy_path
            else:
                return {
                    "favorite_directories": [],
                    "common_commands": [],
                    "custom_settings": {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": None,
                }
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"favorite_directories": [], "common_commands": [], "custom_settings": {}}
                return data
        except Exception as e:
            logger.warning(f"Could not load preferences from {target_path}: {e}")
            return {
                "favorite_directories": [],
                "common_commands": [],
                "custom_settings": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": None,
            }

    def save(self) -> bool:
        """Saves current preferences to disk if save_memory is enabled."""
        if not llama_config.save_memory:
            logger.debug("save_memory is disabled; skipping preferences write.")
            return False

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.preferences["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.preferences, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save preferences to {self.file_path}: {e}")
            return False

    def add_favorite_directory(self, directory: str) -> bool:
        """Adds a directory path to the user's favorite directories list."""
        clean = os.path.normpath(directory.strip())
        favs = self.preferences.setdefault("favorite_directories", [])
        if clean not in favs:
            favs.append(clean)
            return self.save()
        return True

    def remove_favorite_directory(self, directory: str) -> bool:
        """Removes a directory from the user's favorite directories list."""
        clean = os.path.normpath(directory.strip())
        favs = self.preferences.get("favorite_directories", [])
        if clean in favs:
            favs.remove(clean)
            return self.save()
        return False

    def get_favorite_directories(self) -> List[str]:
        """Returns list of recorded favorite directories."""
        return list(self.preferences.get("favorite_directories", []))

    def add_common_command(self, command: str) -> bool:
        """Records a commonly used command."""
        cmd = command.strip()
        cmds = self.preferences.setdefault("common_commands", [])
        if cmd not in cmds:
            cmds.append(cmd)
            return self.save()
        return True

    def remove_common_command(self, command: str) -> bool:
        """Removes a common command."""
        cmd = command.strip()
        cmds = self.preferences.get("common_commands", [])
        if cmd in cmds:
            cmds.remove(cmd)
            return self.save()
        return False

    def get_common_commands(self) -> List[str]:
        """Returns list of recorded common commands."""
        return list(self.preferences.get("common_commands", []))

    def set_custom_setting(self, key: str, value: Any) -> bool:
        """Sets an arbitrary user preference setting."""
        self.preferences.setdefault("custom_settings", {})[key] = value
        return self.save()

    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves an arbitrary user preference setting."""
        return self.preferences.get("custom_settings", {}).get(key, default)

    def clear(self) -> bool:
        """Resets all preferences to empty."""
        self.preferences = {
            "favorite_directories": [],
            "common_commands": [],
            "custom_settings": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": None,
        }
        return self.save()


# Global singleton instance
user_preferences = UserPreferencesManager()
