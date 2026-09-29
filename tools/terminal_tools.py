"""
Universal Terminal and Command Execution Tools for Orvix Sphere.
Provides run_terminal, chain_commands, find_file, pipe_command,
translate_command, explain_command, suggest_command, lookup_command, and search_commands_tool.
"""

import os
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

from knowledge.commands import (
    get_command_by_name,
    search_commands,
    log_command,
    load_all_commands,
)
from .shell_safety import ShellSafety
from .shell_detector import ShellDetector


def run_terminal(
    command: str,
    shell: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Executes a shell command safely, capturing stdout, stderr, exit code,
    and recording metrics to command history for self-learning.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return {"status": "FAILED", "error": "Command is empty", "exit_code": -1}

    # Safety check
    safety_check = ShellSafety.check_command(cmd_clean)
    if not safety_check["allowed"]:
        return {
            "status": "BLOCKED",
            "error": safety_check["reason"],
            "risk_level": safety_check["risk_level"],
            "command": cmd_clean,
        }

    working_dir = cwd or os.getcwd()
    exec_args = ShellDetector.build_execution_args(cmd_clean, shell_override=shell)
    shell_name = shell or ShellDetector.detect_shell_for_command(cmd_clean)

    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(
            exec_args,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        exit_code = proc.returncode
        status = "SUCCESS" if exit_code == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        exit_code = -1
        status = "TIMEOUT"
        stderr = (stderr or "") + f"\nCommand timed out after {timeout} seconds."
    except Exception as e:
        stdout = ""
        stderr = str(e)
        exit_code = -1
        status = "FAILED"

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Log to persistent SQLite command history
    try:
        log_command(
            command=cmd_clean,
            shell=shell_name,
            working_dir=working_dir,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time_ms=duration_ms,
        )
    except Exception:
        pass

    return {
        "status": status,
        "command": cmd_clean,
        "shell": shell_name,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": duration_ms,
        "working_dir": working_dir,
    }


def chain_commands(
    commands: List[str],
    stop_on_error: bool = True,
    cwd: Optional[str] = None,
    timeout_per_cmd: int = 30,
) -> Dict[str, Any]:
    """
    Executes multiple commands sequentially.
    If stop_on_error is True, halts immediately when a command produces non-zero exit.
    """
    results: List[Dict[str, Any]] = []
    overall_success = True

    for cmd in commands:
        res = run_terminal(cmd, cwd=cwd, timeout=timeout_per_cmd)
        results.append(res)
        if res.get("status") != "SUCCESS":
            overall_success = False
            if stop_on_error:
                break

    return {
        "status": "SUCCESS" if overall_success else "FAILED",
        "total_executed": len(results),
        "total_requested": len(commands),
        "results": results,
    }


def find_file(
    pattern: str,
    search_path: Optional[str] = None,
    max_depth: int = 5,
    file_type: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Searches for files matching pattern across directories up to max_depth.
    Never gives up prematurely; inspects available parent directories if path doesn't exist.
    """
    root_path = search_path or os.getcwd()
    if not os.path.exists(root_path):
        # Graceful fallback: check parent directory
        parent = os.path.dirname(os.path.abspath(root_path))
        if os.path.exists(parent):
            root_path = parent
        else:
            root_path = os.getcwd()

    root_path = os.path.abspath(root_path)
    pattern_regex = re.compile(re.escape(pattern).replace(r"\*", ".*").replace(r"\?", "."), re.IGNORECASE)
    
    matches: List[Dict[str, Any]] = []
    base_depth = root_path.rstrip(os.sep).count(os.sep)

    for dirpath, dirnames, filenames in os.walk(root_path):
        current_depth = dirpath.count(os.sep) - base_depth
        if current_depth > max_depth:
            del dirnames[:]
            continue

        # Check directories if file_type != "file"
        if file_type != "file":
            for d in dirnames:
                if pattern_regex.search(d):
                    full_path = os.path.join(dirpath, d)
                    matches.append({
                        "name": d,
                        "path": full_path,
                        "type": "directory",
                    })
                    if len(matches) >= limit:
                        break

        # Check files if file_type != "directory"
        if file_type != "directory":
            for f in filenames:
                if pattern_regex.search(f):
                    full_path = os.path.join(dirpath, f)
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0
                    matches.append({
                        "name": f,
                        "path": full_path,
                        "type": "file",
                        "size_bytes": size,
                    })
                    if len(matches) >= limit:
                        break

        if len(matches) >= limit:
            break

    return {
        "status": "SUCCESS",
        "pattern": pattern,
        "searched_path": root_path,
        "total_found": len(matches),
        "matches": matches,
    }


def pipe_command(
    command1: str,
    command2: str,
    shell: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Pipes stdout of command1 into stdin of command2.
    """
    cmd1_clean = command1.strip()
    cmd2_clean = command2.strip()

    for cmd in (cmd1_clean, cmd2_clean):
        check = ShellSafety.check_command(cmd)
        if not check["allowed"]:
            return {"status": "BLOCKED", "error": check["reason"], "command": cmd}

    t0 = time.perf_counter()
    args1 = ShellDetector.build_execution_args(cmd1_clean, shell_override=shell)
    args2 = ShellDetector.build_execution_args(cmd2_clean, shell_override=shell)

    try:
        p1 = subprocess.Popen(args1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p2 = subprocess.Popen(args2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits
        stdout2, stderr2 = p2.communicate(timeout=timeout)
        stderr1 = p1.stderr.read()
        p1.wait(timeout=5)
        
        exit_code = p2.returncode
        status = "SUCCESS" if exit_code == 0 and p1.returncode == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
        stdout2, stderr2 = "", "Piped command execution timed out"
        exit_code = -1
    except Exception as e:
        status = "FAILED"
        stdout2, stderr2 = "", str(e)
        exit_code = -1

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "status": status,
        "command": f"{cmd1_clean} | {cmd2_clean}",
        "exit_code": exit_code,
        "stdout": stdout2,
        "stderr": (stderr1 if "stderr1" in locals() else "") + (stderr2 or ""),
        "duration_ms": duration_ms,
    }


def translate_command(command: str, target_shell: str) -> Dict[str, Any]:
    """
    Translates a command from one shell dialect (PowerShell, Bash, CMD) to another
    using cross-platform knowledge base equivalents.
    """
    cmd_clean = command.strip()
    target_lower = target_shell.strip().lower()
    source_cmd = get_command_by_name(cmd_clean.split()[0] if cmd_clean.split() else cmd_clean)

    if not source_cmd:
        # Try finding via search
        matches = search_commands(cmd_clean, limit=1)
        if matches:
            source_cmd = matches[0]

    if not source_cmd:
        return {
            "status": "NOT_FOUND",
            "message": f"Could not find translation for command: '{cmd_clean}'",
        }

    equiv = None
    if target_lower in ("powershell", "pwsh"):
        equiv = source_cmd.get("windows_equivalent")
    elif target_lower in ("bash", "sh", "linux"):
        equiv = source_cmd.get("linux_equivalent") or source_cmd.get("name")
    elif target_lower == "cmd":
        equiv = source_cmd.get("windows_equivalent")

    return {
        "status": "SUCCESS",
        "original_command": cmd_clean,
        "source_shell": source_cmd.get("shell"),
        "target_shell": target_shell,
        "translation": equiv or source_cmd.get("syntax"),
        "description": source_cmd.get("description"),
        "examples": source_cmd.get("examples", []),
    }


def explain_command(command: str) -> Dict[str, Any]:
    """
    Deconstructs a command into its primary binary, options/flags, and arguments,
    providing documentation for each recognized flag from the knowledge base.
    """
    cmd_clean = command.strip()
    tokens = cmd_clean.split()
    if not tokens:
        return {"status": "FAILED", "error": "Command is empty"}

    cmd_name = tokens[0]
    info = get_command_by_name(cmd_name)
    known_flags = info.get("flags", {}) if info else {}

    flags_found: Dict[str, str] = {}
    args_found: List[str] = []

    for token in tokens[1:]:
        if token.startswith("-") or token.startswith("/"):
            flag_desc = known_flags.get(token) or known_flags.get(token.lstrip("-/"))
            flags_found[token] = flag_desc or "Flag / Option parameter"
        else:
            args_found.append(token)

    return {
        "status": "SUCCESS",
        "command": cmd_clean,
        "base_command": cmd_name,
        "description": info.get("description", "Generic system command") if info else "Unknown command",
        "shell": info.get("shell", "generic") if info else "auto",
        "category": info.get("category", "system") if info else "system",
        "recognized_flags": flags_found,
        "arguments": args_found,
        "safety_level": info.get("safety", "caution") if info else "caution",
    }


def suggest_command(intent: str) -> Dict[str, Any]:
    """
    Recommends the best shell command(s) for a natural language goal.
    """
    results = search_commands(intent, limit=5)
    suggestions = []
    for r in results:
        suggestions.append({
            "name": r.get("name"),
            "shell": r.get("shell"),
            "category": r.get("category"),
            "syntax": r.get("syntax"),
            "description": r.get("description"),
            "example": r.get("examples", [{}])[0].get("cmd") if r.get("examples") else r.get("syntax"),
        })

    return {
        "status": "SUCCESS",
        "intent": intent,
        "suggested_count": len(suggestions),
        "suggestions": suggestions,
    }


def lookup_command(name: str, shell: Optional[str] = None) -> Dict[str, Any]:
    """
    Looks up full documentation for a command by name.
    """
    cmd = get_command_by_name(name, shell=shell)
    if not cmd:
        return {"status": "NOT_FOUND", "message": f"Command '{name}' not found in knowledge base."}
    return {"status": "SUCCESS", "command": cmd}


def search_commands_tool(query: str, shell: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Searches command knowledge base for matching tools and commands.
    """
    results = search_commands(query, shell=shell, limit=limit)
    return {
        "status": "SUCCESS",
        "query": query,
        "count": len(results),
        "results": results,
    }


def find_file_smart(filename: str, extra_paths: Optional[List[str]] = None) -> List[str]:
    """
    Smart search: checks common user folders recursively (max depth 3).
    Returns list of unique full paths matching filename.
    Skips system/hidden directories (AppData, .git, node_modules, __pycache__, .venv).
    Enforces a 5-second timeout per location.
    Logs every search operation to logs/file_search.log.
    """
    from pathlib import Path
    target_name = os.path.basename(filename).strip()
    if not target_name:
        return []

    default_paths = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/OneDrive/Desktop"),
        os.path.expanduser("~/OneDrive/Documents"),
        os.getcwd(),
    ]
    raw_search_paths = default_paths + (extra_paths or [])

    seen_roots = set()
    search_paths: List[str] = []
    for p in raw_search_paths:
        if not p:
            continue
        resolved = os.path.normpath(os.path.abspath(p))
        if resolved.lower() not in seen_roots and os.path.exists(resolved) and os.path.isdir(resolved):
            seen_roots.add(resolved.lower())
            search_paths.append(resolved)

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    log_file = log_dir / "file_search.log"

    results: List[str] = []
    seen_results = set()
    skip_dirs = {"appdata", ".git", "node_modules", "__pycache__", ".venv", "$recycle.bin"}

    for root in search_paths:
        t_start = time.time()
        root_matches: List[str] = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # 5-second timeout per location
                if time.time() - t_start > 5.0:
                    break

                # Prune system/hidden folders in-place
                dirnames[:] = [
                    d for d in dirnames
                    if d.lower() not in skip_dirs and not d.startswith(".")
                ]

                # Check search depth limit (max depth 3)
                rel_path = os.path.relpath(dirpath, root)
                depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
                if depth >= 3:
                    dirnames[:] = []  # Do not descend deeper
                if depth > 3:
                    continue

                for f in filenames:
                    if f.lower() == target_name.lower():
                        full_p = os.path.normpath(os.path.join(dirpath, f))
                        if full_p.lower() not in seen_results:
                            seen_results.add(full_p.lower())
                            root_matches.append(full_p)
                            results.append(full_p)
        except Exception:
            pass

        elapsed = time.time() - t_start
        try:
            log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SEARCH target='{target_name}' root='{root}' matches={len(root_matches)} elapsed={round(elapsed, 3)}s\n"
            with open(log_file, "a", encoding="utf-8") as lf:
                lf.write(log_line)
        except Exception:
            pass

    return results
