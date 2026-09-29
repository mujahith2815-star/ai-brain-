"""
Command knowledge loader for Orvix Universal Control.
Loads and indexes command definitions from windows_commands.json,
linux_commands.json, and universal_patterns.json.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

COMMANDS_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOWS_FILE = os.path.join(COMMANDS_DIR, "windows_commands.json")
LINUX_FILE = os.path.join(COMMANDS_DIR, "linux_commands.json")
PATTERNS_FILE = os.path.join(COMMANDS_DIR, "universal_patterns.json")

# In-memory cached commands
_COMMANDS_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_json_file(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[WARN] Error loading {file_path}: {e}")
        return []


def load_all_commands(force_reload: bool = False) -> List[Dict[str, Any]]:
    """Loads all commands from Windows, Linux, and Universal pattern datasets."""
    global _COMMANDS_CACHE
    if _COMMANDS_CACHE is not None and not force_reload:
        return _COMMANDS_CACHE

    all_cmds = []

    win_cmds = _load_json_file(WINDOWS_FILE)
    for c in win_cmds:
        c["source_file"] = "windows_commands.json"
        all_cmds.append(c)

    linux_cmds = _load_json_file(LINUX_FILE)
    for c in linux_cmds:
        c["source_file"] = "linux_commands.json"
        all_cmds.append(c)

    patterns = _load_json_file(PATTERNS_FILE)
    for p in patterns:
        if "name" not in p:
            p["name"] = p.get("pattern", "pattern")
        if "description" not in p:
            p["description"] = p.get("desc", "")
        if "shell" not in p:
            p["shell"] = "universal"
        if "category" not in p:
            p["category"] = "universal_patterns"
        if "syntax" not in p:
            p["syntax"] = p.get("windows") or p.get("linux") or ""
        p["source_file"] = "universal_patterns.json"
        all_cmds.append(p)

    _COMMANDS_CACHE = all_cmds
    return all_cmds


def get_command_by_name(name: str, shell: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Look up a command by exact or primary name (case-insensitive)."""
    cmds = load_all_commands()
    target = name.strip().lower()
    
    # 1. Exact match with shell preference
    for c in cmds:
        c_name = c.get("name", "").strip().lower()
        if c_name == target:
            if shell is None or c.get("shell", "").lower() == shell.lower():
                return c

    # 2. Match without shell filter
    for c in cmds:
        c_name = c.get("name", "").strip().lower()
        if c_name == target:
            return c

    # 3. Match aliases if present
    for c in cmds:
        aliases = [a.lower() for a in c.get("aliases", [])]
        if target in aliases:
            if shell is None or c.get("shell", "").lower() == shell.lower():
                return c

    return None


def search_commands(query: str, shell: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search commands by keyword match across name, description, tags, and syntax."""
    cmds = load_all_commands()
    q_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
    if not q_tokens:
        q_tokens = [query.lower().strip()]

    results = []
    for c in cmds:
        if shell:
            c_shell = c.get("shell", "").lower()
            if c_shell != shell.lower() and c_shell != "universal":
                continue

        score = 0
        name = c.get("name", "").lower()
        desc = c.get("description", "").lower()
        syntax = c.get("syntax", "").lower()
        tags = [t.lower() for t in c.get("tags", [])]
        category = c.get("category", "").lower()

        for token in q_tokens:
            if token == name:
                score += 15
            elif token in name:
                score += 8
            if token in tags:
                score += 6
            if token in desc:
                score += 3
            if token in category:
                score += 4
            if token in syntax:
                score += 2

        if score > 0:
            results.append((score, c))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:limit]]


def get_by_category(category: str, shell: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all commands in a given category."""
    cmds = load_all_commands()
    cat_lower = category.lower().strip()
    matches = []
    for c in cmds:
        if c.get("category", "").lower() == cat_lower:
            if shell is None or c.get("shell", "").lower() == shell.lower() or c.get("shell", "").lower() == "universal":
                matches.append(c)
    return matches


def get_by_shell(shell: str) -> List[Dict[str, Any]]:
    """Retrieve all commands for a specific shell (e.g. 'powershell', 'cmd', 'bash')."""
    cmds = load_all_commands()
    shell_lower = shell.lower().strip()
    return [c for c in cmds if c.get("shell", "").lower() == shell_lower or c.get("shell", "").lower() == "universal"]


def get_by_tag(tag: str, shell: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve commands annotated with a specific tag."""
    cmds = load_all_commands()
    tag_lower = tag.lower().strip()
    matches = []
    for c in cmds:
        tags = [t.lower() for t in c.get("tags", [])]
        if tag_lower in tags:
            if shell is None or c.get("shell", "").lower() == shell.lower() or c.get("shell", "").lower() == "universal":
                matches.append(c)
    return matches


def get_all_categories() -> List[str]:
    """Return sorted unique list of all command categories."""
    cmds = load_all_commands()
    categories = {c.get("category") for c in cmds if c.get("category")}
    return sorted(list(categories))


def get_command_summary() -> Dict[str, Any]:
    """Return summary statistics of available commands."""
    cmds = load_all_commands()
    by_shell: Dict[str, int] = {}
    by_category: Dict[str, int] = {}

    for c in cmds:
        sh = c.get("shell", "unknown")
        cat = c.get("category", "uncategorized")
        by_shell[sh] = by_shell.get(sh, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total_commands": len(cmds),
        "shells": by_shell,
        "categories": by_category,
    }
