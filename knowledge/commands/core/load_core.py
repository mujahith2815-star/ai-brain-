"""
Core Command Catalog Loader for Layer 1 Command Intelligence.
Loads and caches pre-indexed, high-value command definitions (~520 commands)
across PowerShell, CMD, Linux Bash, and Cross-Platform developer tools.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

CORE_DIR = os.path.dirname(os.path.abspath(__file__))

_CORE_CACHE: Optional[List[Dict[str, Any]]] = None
_CORE_BY_NAME: Optional[Dict[str, Dict[str, Any]]] = None


def load_core_commands(force_reload: bool = False) -> List[Dict[str, Any]]:
    """
    Loads all core command catalogs from disk, deduplicates by command name,
    and tags each record with source="core".
    """
    global _CORE_CACHE, _CORE_BY_NAME
    if _CORE_CACHE is not None and not force_reload:
        return _CORE_CACHE

    filenames = [
        "windows_powershell.json",
        "windows_cmd.json",
        "linux_bash.json",
        "cross_platform.json",
    ]

    by_name: Dict[str, Dict[str, Any]] = {}
    commands: List[Dict[str, Any]] = []

    for fname in filenames:
        fpath = os.path.join(CORE_DIR, fname)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        name = item.get("name", "").strip()
                        if not name:
                            continue
                        name_key = name.lower()
                        # Deduplicate by name (first wins or combines tags)
                        if name_key not in by_name:
                            record = dict(item)
                            record["source"] = "core"
                            record.setdefault("shell", "cross-platform")
                            record.setdefault("category", "general")
                            record.setdefault("safety", "safe")
                            record.setdefault("tags", [])
                            by_name[name_key] = record
                            commands.append(record)
                        else:
                            # Merge tags if existing
                            existing_tags = set(by_name[name_key].get("tags", []))
                            new_tags = set(item.get("tags", []))
                            by_name[name_key]["tags"] = list(existing_tags | new_tags)
        except Exception as e:
            print(f"[load_core] Warning loading {fname}: {e}")

    _CORE_CACHE = commands
    _CORE_BY_NAME = by_name
    return _CORE_CACHE


def get_core_command(name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a core command definition by exact name (case-insensitive)."""
    if _CORE_BY_NAME is None:
        load_core_commands()
    if _CORE_BY_NAME is None:
        return None
    return _CORE_BY_NAME.get(name.strip().lower())


def search_core_commands(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Performs keyword, description, and tag matching across core commands.
    Returns ranked list of matching command dicts.
    """
    commands = load_core_commands()
    q_tokens = re.findall(r"\w+", query.lower())
    if not q_tokens:
        return commands[:limit]

    scored: List[tuple[float, Dict[str, Any]]] = []
    for cmd in commands:
        score = 0.0
        name = cmd.get("name", "").lower()
        desc = cmd.get("description", "").lower()
        cat = cmd.get("category", "").lower()
        tags = [t.lower() for t in cmd.get("tags", [])]
        syntax = cmd.get("syntax", "").lower()

        for t in q_tokens:
            if t == name:
                score += 15.0
            elif t in name:
                score += 8.0
            if t in tags:
                score += 5.0
            if t in cat:
                score += 4.0
            if t in desc:
                score += 2.0
            if t in syntax:
                score += 1.0

        if score > 0.0:
            scored.append((score, cmd))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def get_core_categories() -> List[str]:
    """Returns sorted list of distinct categories in the core catalog."""
    commands = load_core_commands()
    cats = {c.get("category", "general") for c in commands if c.get("category")}
    return sorted(list(cats))


def get_core_by_category(category: str) -> List[Dict[str, Any]]:
    """Returns all core commands in a specified category."""
    commands = load_core_commands()
    target = category.strip().lower()
    return [c for c in commands if c.get("category", "").lower() == target]
