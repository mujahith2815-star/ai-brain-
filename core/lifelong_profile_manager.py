"""
Lifelong Profile Manager for P.H.A.S.S / JARVIS.
Persists real user identity, favorite hardware platforms, and project history
in core/lifelong_profile.json. Synchronizes across Jarvis persona and preferences.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


class LifelongProfileManager:
    def __init__(self, profile_path: Optional[str] = None):
        if profile_path:
            self.profile_path = Path(profile_path)
        else:
            try:
                from core.data_hub import data_hub
                self.profile_path = data_hub.resolve("user", "lifelong_profile.json")
            except Exception:
                self.profile_path = Path(__file__).parent / "lifelong_profile.json"
        self.profile_data: Dict[str, Any] = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        target = self.profile_path
        if not target.exists():
            fallback = Path(__file__).parent / "lifelong_profile.json"
            if fallback.exists():
                target = fallback
        if target.exists():
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {
            "real_name": "M.Mohammed Mujahith",
            "favorite_microcontrollers": ["ESP32", "Arduino"],
            "project_history": [],
            "active_persona": "JARVIS",
        }

    def save_profile(self) -> bool:
        try:
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)
            self.profile_path.write_text(json.dumps(self.profile_data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    @property
    def real_name(self) -> str:
        return self.profile_data.get("real_name") or "M.Mohammed Mujahith"

    def set_real_name(self, name: str) -> str:
        clean = name.strip()
        self.profile_data["real_name"] = clean
        self.save_profile()
        # Synchronize with jarvis_persona and user_preferences
        try:
            from jarvis.persona import jarvis_persona
            jarvis_persona.set_user_name(clean)
        except Exception:
            pass
        try:
            from core.user_preferences import user_preferences
            user_preferences.set_custom_setting("user_name", clean)
        except Exception:
            pass
        return clean

    @property
    def favorite_microcontrollers(self) -> List[str]:
        return self.profile_data.get("favorite_microcontrollers", ["ESP32", "Arduino"])

    def add_favorite_microcontroller(self, mcu: str):
        mcus = self.favorite_microcontrollers
        if mcu not in mcus:
            mcus.append(mcu)
            self.profile_data["favorite_microcontrollers"] = mcus
            self.save_profile()

    @property
    def project_history(self) -> List[Dict[str, Any]]:
        return self.profile_data.get("project_history", [])

    def record_project(self, name: str, ptype: str = "firmware/hardware"):
        from datetime import datetime
        history = self.project_history
        history.append({
            "name": name,
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "type": ptype
        })
        self.profile_data["project_history"] = history
        self.save_profile()

    def get_startup_greeting(self, persona: Optional[str] = None) -> str:
        """Generates a Marvel-level startup greeting addressing user by real name."""
        p_name = (persona or self.profile_data.get("active_persona") or "JARVIS").upper()
        name = self.real_name
        fav_mcus = ", ".join(self.favorite_microcontrollers)

        if p_name == "FRIDAY":
            return (
                f"Good day, {name}. FRIDAY online and fully operational, Boss. "
                f"Hardware interfaces ({fav_mcus}) are primed. Ready when you are."
            )
        elif p_name == "EDITH":
            return (
                f"Security protocols initialized for {name}. EDITH tactical systems nominal. "
                f"Defense perimeter and hardware nodes ({fav_mcus}) online. Standing by for directives."
            )
        else:
            # Default JARVIS
            return (
                f"Good day, {name}. JARVIS online and all systems nominal, sir. "
                f"Hardware toolchains for {fav_mcus} are standing by. How may I be of service?"
            )


# Global singleton
lifelong_profile_manager = LifelongProfileManager()