"""
Universal Data Hub Central Resolver for P.H.A.S.S.
Decouples persistent data from the codebase to a user-specified physical disk.
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import Optional, Union


class DataHub:
    _instance = None
    _root: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self,
        config_path: str = "config/data_hub_config.json",
        default_path: Optional[str] = None,
        interactive: bool = True,
    ) -> Path:
        p_cfg = Path(config_path)
        if not p_cfg.exists():
            return self._prompt_user_for_path(config_path, default_path, interactive)
        try:
            with open(p_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_path = data.get("data_root")
                if not raw_path:
                    raw_path = default_path or ("W:/PHASS_MEMORY" if Path("W:/").exists() else "D:/PHASS_MEMORY")
                self._root = self._validate_root(raw_path)
        except Exception:
            self._root = self._validate_root(default_path or ("W:/PHASS_MEMORY" if Path("W:/").exists() else "D:/PHASS_MEMORY"))
        return self._root

    def _validate_root(self, path_str: Union[str, Path]) -> Path:
        root = Path(path_str)
        if root.drive and not Path(root.drive + "/").exists():
            alt_drive = "W:" if Path("W:/").exists() else "C:"
            print(f"[!] Warning: Target drive '{root.drive}' not mounted. Defaulting data root to '{alt_drive}/PHASS_MEMORY'.")
            root = Path(f"{alt_drive}/PHASS_MEMORY")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def resolve(self, *subpaths) -> Path:
        """Resolve a path relative to the data root (e.g., resolve('checkpoints', 'mind.db'))"""
        if self._root is None:
            self.initialize(interactive=False)
        res = self._root.joinpath(*subpaths)
        res.parent.mkdir(parents=True, exist_ok=True)
        return res

    @property
    def root(self) -> Path:
        if self._root is None:
            self.initialize(interactive=False)
        return self._root

    @property
    def is_migrated(self) -> bool:
        p_cfg = Path("config/data_hub_config.json")
        if p_cfg.exists():
            try:
                data = json.loads(p_cfg.read_text(encoding="utf-8"))
                return bool(data.get("migrated", False))
            except Exception:
                pass
        return False

    def set_migrated(self, status: bool = True, config_path: str = "config/data_hub_config.json"):
        p_cfg = Path(config_path)
        p_cfg.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if p_cfg.exists():
            try:
                data = json.loads(p_cfg.read_text(encoding="utf-8"))
            except Exception:
                pass
        data["data_root"] = str(self._root) if self._root else ("W:/PHASS_MEMORY" if Path("W:/").exists() else "D:/PHASS_MEMORY")
        data["migrated"] = status
        data["version"] = "1.0"
        p_cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _prompt_user_for_path(self, config_path: str, default_path: Optional[str] = None, interactive: bool = True) -> Path:
        # Non-interactive or testing check
        if not interactive or not sys.stdin.isatty():
            target = default_path or os.environ.get("PHASS_DATA_ROOT")
            if not target:
                target = "W:/PHASS_MEMORY" if Path("W:/").exists() else "D:/PHASS_MEMORY"
            root = self._validate_root(target)
            self._root = root
            self.set_migrated(False, config_path)
            return root

        print("🔍 P.H.A.S.S Data Hub Initialization")
        print("Please enter the full path where you want to store ALL your data (memories, logs, projects, models).")
        print("Example: D:/PHASS_MEMORY  or  W:/PHASS_MEMORY")
        try:
            path = input("Data Root Path: ").strip()
        except (EOFError, KeyboardInterrupt):
            path = ""
        if not path:
            path = default_path or ("W:/PHASS_MEMORY" if Path("W:/").exists() else "D:/PHASS_MEMORY")
        root = self._validate_root(path)
        self._root = root
        self.set_migrated(False, config_path)
        return root


# Singleton instance
data_hub = DataHub()