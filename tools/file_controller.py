"""
File Management and Operations Controller for Orvix Universal Control.
Provides metadata inspection, hashing, batch renaming, archiving/extraction,
and duplicate file identification.
"""

import hashlib
import os
import re
import shutil
import tarfile
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional


def get_file_info(path: str) -> Dict[str, Any]:
    """Retrieves file or directory metadata including size, permissions, and timestamps."""
    clean_path = os.path.abspath(path.strip())
    if not os.path.exists(clean_path):
        return {"status": "NOT_FOUND", "path": clean_path, "error": "Path does not exist"}

    stat = os.stat(clean_path)
    is_dir = os.path.isdir(clean_path)

    return {
        "status": "SUCCESS",
        "path": clean_path,
        "name": os.path.basename(clean_path),
        "is_directory": is_dir,
        "is_file": os.path.isfile(clean_path),
        "size_bytes": stat.st_size if not is_dir else 0,
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": os.path.splitext(clean_path)[1] if not is_dir else None,
    }


def calculate_hash(path: str, algorithm: str = "sha256") -> Dict[str, Any]:
    """Computes cryptographic hash (sha256, md5, sha1) of a file."""
    clean_path = os.path.abspath(path.strip())
    if not os.path.isfile(clean_path):
        return {"status": "FAILED", "error": f"File '{clean_path}' not found or is a directory"}

    algo = algorithm.lower().strip()
    if algo == "sha256":
        hasher = hashlib.sha256()
    elif algo == "md5":
        hasher = hashlib.md5()
    elif algo == "sha1":
        hasher = hashlib.sha1()
    else:
        return {"status": "FAILED", "error": f"Unsupported hash algorithm: {algo}"}

    try:
        with open(clean_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return {
            "status": "SUCCESS",
            "path": clean_path,
            "algorithm": algo,
            "hash": hasher.hexdigest(),
        }
    except Exception as e:
        return {"status": "FAILED", "path": clean_path, "error": str(e)}


def batch_rename(directory: str, search_pattern: str, replacement: str) -> Dict[str, Any]:
    """
    Renames files in a directory matching search_pattern (regex or substring) with replacement.
    """
    clean_dir = os.path.abspath(directory.strip())
    if not os.path.isdir(clean_dir):
        return {"status": "FAILED", "error": f"Directory not found: {clean_dir}"}

    renamed = []
    regex = re.compile(search_pattern)

    for item in os.listdir(clean_dir):
        old_path = os.path.join(clean_dir, item)
        if not os.path.isfile(old_path):
            continue

        new_name = regex.sub(replacement, item)
        if new_name != item:
            new_path = os.path.join(clean_dir, new_name)
            try:
                os.rename(old_path, new_path)
                renamed.append({"old_name": item, "new_name": new_name})
            except Exception as e:
                pass

    return {
        "status": "SUCCESS",
        "directory": clean_dir,
        "renamed_count": len(renamed),
        "renamed": renamed,
    }


def compress_files(sources: List[str], output_path: str, format: str = "zip") -> Dict[str, Any]:
    """
    Compresses a list of files or directories into a .zip or .tar.gz archive.
    """
    clean_out = os.path.abspath(output_path.strip())
    fmt = format.lower().strip()

    try:
        if fmt == "zip":
            if not clean_out.endswith(".zip"):
                clean_out += ".zip"
            with zipfile.ZipFile(clean_out, "w", zipfile.ZIP_DEFLATED) as zf:
                for src in sources:
                    src_abs = os.path.abspath(src.strip())
                    if os.path.isdir(src_abs):
                        for root, _, files in os.walk(src_abs):
                            for f in files:
                                full_p = os.path.join(root, f)
                                arcname = os.path.relpath(full_p, os.path.dirname(src_abs))
                                zf.write(full_p, arcname)
                    elif os.path.isfile(src_abs):
                        zf.write(src_abs, os.path.basename(src_abs))
        elif fmt in ("tar", "tar.gz", "tgz"):
            if not (clean_out.endswith(".tar.gz") or clean_out.endswith(".tgz") or clean_out.endswith(".tar")):
                clean_out += ".tar.gz"
            mode = "w:gz" if "gz" in fmt or fmt == "tgz" else "w"
            with tarfile.open(clean_out, mode) as tf:
                for src in sources:
                    src_abs = os.path.abspath(src.strip())
                    tf.add(src_abs, arcname=os.path.basename(src_abs))
        else:
            return {"status": "FAILED", "error": f"Unsupported compression format: {format}"}

        size = os.path.getsize(clean_out)
        return {
            "status": "SUCCESS",
            "archive_path": clean_out,
            "size_bytes": size,
            "format": fmt,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def extract_archive(archive_path: str, destination: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts a .zip, .tar, .tar.gz, or .tgz archive to destination directory.
    """
    clean_arc = os.path.abspath(archive_path.strip())
    if not os.path.isfile(clean_arc):
        return {"status": "NOT_FOUND", "error": f"Archive file '{clean_arc}' not found"}

    dest = os.path.abspath(destination.strip()) if destination else os.path.dirname(clean_arc)
    os.makedirs(dest, exist_ok=True)

    try:
        if zipfile.is_zipfile(clean_arc):
            with zipfile.ZipFile(clean_arc, "r") as zf:
                zf.extractall(dest)
        elif tarfile.is_tarfile(clean_arc):
            with tarfile.open(clean_arc, "r:*") as tf:
                tf.extractall(dest)
        else:
            return {"status": "FAILED", "error": "Unsupported or unrecognized archive format"}

        return {
            "status": "SUCCESS",
            "archive_path": clean_arc,
            "destination": dest,
            "message": "Archive extracted successfully",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def find_duplicates(directory: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Discovers duplicate files within a directory based on size and SHA-256 hash.
    """
    clean_dir = os.path.abspath(directory.strip())
    if not os.path.isdir(clean_dir):
        return {"status": "NOT_FOUND", "error": f"Directory not found: {clean_dir}"}

    size_map: Dict[int, List[str]] = {}
    base_depth = clean_dir.rstrip(os.sep).count(os.sep)

    for root, dirs, files in os.walk(clean_dir):
        if (root.count(os.sep) - base_depth) > max_depth:
            del dirs[:]
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                if sz > 0:
                    size_map.setdefault(sz, []).append(fp)
            except OSError:
                continue

    # For files with identical sizes, compute hash
    duplicate_groups: List[Dict[str, Any]] = []
    for sz, paths in size_map.items():
        if len(paths) < 2:
            continue
        hash_map: Dict[str, List[str]] = {}
        for p in paths:
            h_res = calculate_hash(p, "sha256")
            if h_res.get("status") == "SUCCESS":
                h_val = h_res.get("hash")
                hash_map.setdefault(h_val, []).append(p)

        for h_val, dups in hash_map.items():
            if len(dups) > 1:
                duplicate_groups.append({
                    "hash": h_val,
                    "size_bytes": sz,
                    "count": len(dups),
                    "files": dups,
                })

    return {
        "status": "SUCCESS",
        "directory": clean_dir,
        "duplicate_groups_count": len(duplicate_groups),
        "duplicates": duplicate_groups,
    }
