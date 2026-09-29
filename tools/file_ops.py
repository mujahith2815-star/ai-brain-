"""
Universal File Viewer, Editor & Patching Engine for P.H.A.S.S Sphere.
Enables viewing, editing, patching, searching, and managing any file across the filesystem.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("phass.tools.file_ops")


class UniversalFileManager:
    """
    Handles viewing, editing, writing, searching, and listing files.
    """

    def view_file(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        auto_search: bool = True,
        search_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Reads a file with line slicing. Lines are 1-indexed.
        If file does not exist at given path and auto_search=True,
        searches common locations (Desktop, Documents, Downloads, OneDrive, CWD).
        """
        path = Path(file_path).resolve()
        note = None

        if not path.exists():
            if not auto_search:
                return {
                    "success": False,
                    "status": "NOT_FOUND",
                    "error": f"File does not exist: {file_path}",
                    "content": "",
                }

            from tools.terminal_tools import find_file_smart
            filename = os.path.basename(file_path)
            matches = find_file_smart(filename, extra_paths=search_paths)

            if len(matches) == 1:
                path = Path(matches[0]).resolve()
                note = f"Found at {matches[0]} (searched from {file_path})"
            elif len(matches) > 1:
                return {
                    "success": False,
                    "status": "MULTIPLE_MATCHES",
                    "matches": matches,
                    "note": "Found multiple files. Which one?",
                    "content": "",
                }
            else:
                default_locations = [
                    os.path.expanduser("~/Desktop"),
                    os.path.expanduser("~/Documents"),
                    os.path.expanduser("~/Downloads"),
                    os.path.expanduser("~/OneDrive/Desktop"),
                    os.path.expanduser("~/OneDrive/Documents"),
                    os.getcwd(),
                ]
                all_searched = default_locations + (search_paths or [])
                return {
                    "success": False,
                    "status": "NOT_FOUND",
                    "searched_paths": all_searched,
                    "error": f"File does not exist: {file_path}",
                    "note": f"Could not find {filename}. Please provide the full path, or check the filename.",
                    "content": "",
                }

        if path.is_dir():
            return {"success": False, "error": f"Path is a directory, not a file: {file_path}", "content": ""}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_idx = max(1, start_line or 1) - 1
            e_idx = min(total_lines, end_line or total_lines)

            sliced_lines = lines[s_idx:e_idx]
            formatted_content = "".join([f"{i+1+s_idx}: {line}" for i, line in enumerate(sliced_lines)])

            res: Dict[str, Any] = {
                "success": True,
                "status": "SUCCESS",
                "path": str(path),
                "file_path": str(path),
                "total_lines": total_lines,
                "start_line": s_idx + 1,
                "end_line": e_idx,
                "content": formatted_content,
                "raw_text": "".join(sliced_lines),
            }
            if note:
                res["note"] = note
            return res
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {e}", "content": ""}

    def write_file(self, file_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """
        Writes or creates a new file. Creates parent directories automatically.
        """
        path = Path(file_path).resolve()
        if path.exists() and not overwrite:
            return {"success": False, "error": f"File already exists and overwrite is False: {file_path}"}

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "file_path": str(path), "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": f"Failed to write file: {e}"}

    def edit_file(self, file_path: str, target_snippet: str, replacement_snippet: str) -> Dict[str, Any]:
        """
        Performs surgical search-and-replace on a file.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"File does not exist: {file_path}"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if target_snippet not in content:
                return {
                    "success": False,
                    "error": "Target snippet was not found in the file. Ensure exact matching including whitespace.",
                }

            # Replace single instance
            new_content = content.replace(target_snippet, replacement_snippet, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "file_path": str(path),
                "message": "File successfully patched.",
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to edit file: {e}"}

    def list_directory(self, dir_path: str = ".", max_entries: int = 50) -> Dict[str, Any]:
        """
        Lists files and subdirectories in a directory with file sizes.
        """
        path = Path(dir_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"Directory does not exist: {dir_path}"}

        try:
            entries = []
            for item in sorted(path.iterdir()):
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else 0,
                    "path": str(item),
                })
                if len(entries) >= max_entries:
                    break

            return {
                "success": True,
                "dir_path": str(path),
                "total_entries": len(entries),
                "entries": entries,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list directory: {e}"}

    def search_in_files(
        self,
        dir_path: str = ".",
        query: str = "",
        extensions: Optional[List[str]] = None,
        max_matches: int = 30,
    ) -> Dict[str, Any]:
        """
        Searches for text pattern in files across directory.
        """
        path = Path(dir_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"Directory does not exist: {dir_path}"}

        matches = []
        ext_set = set(extensions) if extensions else None

        try:
            for root, _, files in os.walk(path):
                # Skip .git, cache folders
                if any(ignored in root for ignored in [".git", "__pycache__", ".pytest_cache", "venv"]):
                    continue

                for f in files:
                    file_ext = Path(f).suffix.lstrip(".")
                    if ext_set and file_ext not in ext_set:
                        continue

                    full_p = os.path.join(root, f)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as file_obj:
                            for line_no, line in enumerate(file_obj, start=1):
                                if query.lower() in line.lower():
                                    matches.append({
                                        "file": os.path.relpath(full_p, path),
                                        "line_number": line_no,
                                        "snippet": line.strip()[:120],
                                    })
                                    if len(matches) >= max_matches:
                                        return {"success": True, "query": query, "matches": matches}
                    except Exception:
                        continue

            return {"success": True, "query": query, "matches": matches}
        except Exception as e:
            return {"success": False, "error": f"Search failed: {e}"}

    def create_folder(self, folder_path: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new directory (and any necessary parent directories).
        Expands '~' or environment variables if present.
        """
        target = folder_path or path
        if not target:
            return {"success": False, "status": "FAILED", "error": "No folder path provided."}

        try:
            expanded = os.path.expandvars(os.path.expanduser(str(target)))
            p = Path(expanded).resolve()
            p.mkdir(parents=True, exist_ok=True)
            return {
                "success": True,
                "status": "SUCCESS",
                "folder_path": str(p),
                "path": str(p),
                "message": f"Folder created successfully at: {p}",
            }
        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "folder_path": str(target),
                "path": str(target),
                "error": f"Failed to create folder: {e}",
            }

    def delete_file(self, file_path: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Deletes a single file from the filesystem.
        """
        target = file_path or path
        if not target:
            return {"success": False, "status": "FAILED", "error": "No file path provided to delete."}

        try:
            exp = os.path.expandvars(os.path.expanduser(str(target)))
            p = Path(exp).resolve()
            if not p.exists():
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "file_path": str(p),
                    "path": str(p),
                    "message": f"File does not exist: {p}",
                }
            if p.is_file():
                p.unlink()
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "file_path": str(p),
                    "path": str(p),
                    "message": f"File successfully deleted: {p}",
                }
            else:
                return {
                    "success": False,
                    "status": "FAILED",
                    "file_path": str(p),
                    "path": str(p),
                    "error": f"Path is a directory, not a file: {p}",
                }
        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "file_path": str(target),
                "path": str(target),
                "error": f"Failed to delete file: {e}",
            }


file_manager = UniversalFileManager()

