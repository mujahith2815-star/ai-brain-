"""
Advanced File Organizer, Disk Space Analyzer & Duplicate Finder for P.H.A.S.S Sphere.
Provides smart categorization, disk usage breakdown, and duplicate file detection.
"""

from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


def analyze_disk_space(directory: str) -> Dict[str, Any]:
    """
    Analyzes disk space usage of a directory, breaking down sizes by file categories.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return {
            "status": "FAILED",
            "error": f"Directory does not exist: {directory}",
            "directory": directory,
        }

    total_bytes = 0
    file_count = 0
    category_sizes: Dict[str, int] = {
        "Documents": 0,
        "Images": 0,
        "Audio": 0,
        "Video": 0,
        "Code": 0,
        "Archives": 0,
        "Other": 0,
    }

    ext_map = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".xlsx", ".csv", ".pptx", ".md"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff"],
        "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
        "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".rs", ".go", ".json", ".yaml", ".sh", ".bat"],
        "Archives": [".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"],
    }

    large_files = []

    for root, _, files in os.walk(dir_path):
        # Skip hidden/git folders
        if any(ignored in root for ignored in [".git", "node_modules", "__pycache__"]):
            continue
        for f in files:
            p = Path(root) / f
            try:
                size = p.stat().st_size
                total_bytes += size
                file_count += 1

                ext = p.suffix.lower()
                categorized = False
                for cat, exts in ext_map.items():
                    if ext in exts:
                        category_sizes[cat] += size
                        categorized = True
                        break
                if not categorized:
                    category_sizes["Other"] += size

                if size > 10 * 1024 * 1024:  # > 10MB
                    large_files.append({"name": f, "path": str(p), "size_mb": round(size / (1024 * 1024), 2)})
            except Exception:
                continue

    return {
        "status": "SUCCESS",
        "directory": str(dir_path),
        "total_files": file_count,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "category_breakdown_mb": {cat: round(s / (1024 * 1024), 2) for cat, s in category_sizes.items()},
        "large_files_count": len(large_files),
        "large_files": sorted(large_files, key=lambda x: x["size_mb"], reverse=True)[:10],
    }


def find_duplicate_files(directory: str) -> Dict[str, Any]:
    """
    Finds identical duplicate files in a directory using SHA-256 hash comparison.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return {
            "status": "FAILED",
            "error": f"Directory does not exist: {directory}",
            "directory": directory,
        }

    hashes: Dict[str, List[str]] = {}
    duplicates: List[Dict[str, Any]] = []
    wasted_bytes = 0

    for root, _, files in os.walk(dir_path):
        if any(ignored in root for ignored in [".git", "node_modules", "__pycache__"]):
            continue
        for f in files:
            p = Path(root) / f
            try:
                # Fast size check first
                size = p.stat().st_size
                if size == 0:
                    continue

                # Hash content
                hasher = hashlib.sha256()
                with open(p, "rb") as file_obj:
                    while chunk := file_obj.read(65536):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()

                if file_hash in hashes:
                    hashes[file_hash].append(str(p))
                else:
                    hashes[file_hash] = [str(p)]
            except Exception:
                continue

    for f_hash, paths in hashes.items():
        if len(paths) > 1:
            try:
                single_size = os.path.getsize(paths[0])
                wasted = single_size * (len(paths) - 1)
                wasted_bytes += wasted
                duplicates.append({
                    "original": paths[0],
                    "duplicates": paths[1:],
                    "copy_count": len(paths) - 1,
                    "size_mb": round(single_size / (1024 * 1024), 3),
                })
            except Exception:
                continue

    return {
        "status": "SUCCESS",
        "directory": str(dir_path),
        "duplicate_groups_count": len(duplicates),
        "potential_reclaimed_mb": round(wasted_bytes / (1024 * 1024), 2),
        "duplicates": duplicates,
    }


def smart_file_organizer(directory: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Organizes messy directories by moving files into categorized subfolders
    (Documents, Images, Audio, Video, Archives, Code) with a safe dry-run preview mode.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return {
            "status": "FAILED",
            "error": f"Directory does not exist: {directory}",
            "directory": directory,
        }

    ext_map = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".xlsx", ".csv", ".pptx", ".md"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
        "Video": [".mp4", ".mkv", ".avi", ".mov", ".webm"],
        "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".sh", ".bat"],
    }

    planned_moves = []

    for item in dir_path.iterdir():
        if item.is_file():
            ext = item.suffix.lower()
            for category, exts in ext_map.items():
                if ext in exts:
                    dest_dir = dir_path / category
                    dest_path = dest_dir / item.name
                    planned_moves.append({
                        "file": str(item),
                        "destination_folder": str(dest_dir),
                        "category": category,
                    })
                    break

    if dry_run:
        return {
            "status": "SUCCESS",
            "mode": "DRY_RUN",
            "directory": str(dir_path),
            "files_to_organize": len(planned_moves),
            "moves_planned": planned_moves,
            "message": f"DRY RUN: Would organize {len(planned_moves)} files into subfolders. Set dry_run=False to execute.",
        }

    # Execute moves
    executed_moves = []
    errors = []
    for move in planned_moves:
        try:
            dest_dir = Path(move["destination_folder"])
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(move["file"], dest_dir / Path(move["file"]).name)
            executed_moves.append(move)
        except Exception as e:
            errors.append(f"Failed to move {move['file']}: {e}")

    return {
        "status": "SUCCESS",
        "mode": "EXECUTED",
        "directory": str(dir_path),
        "organized_count": len(executed_moves),
        "errors": errors,
        "message": f"Successfully organized {len(executed_moves)} files into categorized folders.",
    }
