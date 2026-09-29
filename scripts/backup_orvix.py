"""
Automatic Backup System for Orvix Sphere (v1.4.3).
Backs up critical Orvix data (knowledge/, config/, proactive/triggers.json, logs/errors.db)
to W:\\PHASS_MEMORY\\backups\\YYYYMMDD\\.
Enforces a 7-day rolling retention policy, logs to logs/backup.log,
and strictly excludes models/ to preserve disk space.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure stdout/stderr handles UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Default target directories
DEFAULT_W_BACKUP = Path("W:/PHASS_MEMORY/backups")
DATE_PATTERN = re.compile(r"^\d{8}$")


def get_project_root() -> Path:
    """Returns the root directory of the Orvix Sphere project."""
    return Path(__file__).resolve().parent.parent


def get_backup_root(custom_root: Optional[str] = None) -> Path:
    """
    Resolves the backup storage root:
    1. custom_root if provided
    2. W:/PHASS_MEMORY/backups if W: drive is mounted
    3. Fallback to <project_root>/backups
    """
    if custom_root:
        p = Path(custom_root).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if os.path.exists("W:/"):
        DEFAULT_W_BACKUP.mkdir(parents=True, exist_ok=True)
        return DEFAULT_W_BACKUP

    local_backup = get_project_root() / "backups"
    local_backup.mkdir(parents=True, exist_ok=True)
    return local_backup


def _log_backup_event(event_type: str, details: Dict[str, Any], project_root: Optional[Path] = None) -> None:
    """Appends an audit entry to logs/backup.log."""
    try:
        root = project_root or get_project_root()
        logs_dir = root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "backup.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] {event_type.upper()}: " + ", ".join(f"{k}={v}" for k, v in details.items()) + "\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to write to backup.log: {e}\n")


def _get_dir_stats(path: Path) -> Tuple[int, int]:
    """Computes total file count and size in bytes for a directory."""
    total_files = 0
    total_bytes = 0
    if not path.exists():
        return (0, 0)
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total_bytes += os.path.getsize(fp)
                    total_files += 1
                except OSError:
                    pass
    return (total_files, total_bytes)


def prune_backups(backup_root: Optional[Path] = None, keep_days: int = 7) -> int:
    """
    Enforces rolling retention policy: retains the newest `keep_days` daily backup folders,
    pruning older YYYYMMDD directories. Returns number of pruned backup folders.
    """
    root = backup_root or get_backup_root()
    if not root.exists():
        return 0

    daily_folders: List[Tuple[str, Path]] = []
    for item in root.iterdir():
        if item.is_dir() and DATE_PATTERN.match(item.name):
            daily_folders.append((item.name, item))

    # Sort descending by date (newest first)
    daily_folders.sort(key=lambda x: x[0], reverse=True)

    pruned_count = 0
    if len(daily_folders) > keep_days:
        to_delete = daily_folders[keep_days:]
        for date_str, folder_path in to_delete:
            try:
                shutil.rmtree(folder_path, ignore_errors=True)
                pruned_count += 1
                _log_backup_event("PRUNE", {"date": date_str, "path": str(folder_path)})
            except Exception as e:
                sys.stderr.write(f"Failed to prune old backup {folder_path}: {e}\n")

    return pruned_count


def create_backup(
    backup_root: Optional[str] = None,
    force: bool = False,
    project_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a daily backup of critical Orvix data to <backup_root>/<YYYYMMDD>/.
    Items backed up:
      - knowledge/
      - config/
      - proactive/triggers.json
      - logs/errors.db
    Models directory is explicitly ignored.
    Skips if backup for today already exists (unless force=True).
    Prunes backups older than 7 days.
    """
    p_root = Path(project_root).resolve() if project_root else get_project_root()
    b_root = get_backup_root(backup_root)
    today_str = datetime.now().strftime("%Y%m%d")
    target_dir = b_root / today_str

    # 1. Skip check
    if target_dir.exists() and not force:
        stats = _get_dir_stats(target_dir)
        _log_backup_event("SKIP", {"date": today_str, "reason": "Already exists for today", "path": str(target_dir)}, p_root)
        return {
            "status": "SKIPPED",
            "date": today_str,
            "path": str(target_dir),
            "message": f"Backup for today ({today_str}) already exists. Use force=True to overwrite.",
            "total_files": stats[0],
            "total_bytes": stats[1],
            "size_mb": round(stats[1] / (1024 * 1024), 2),
        }

    # If force and exists, clean target directory before copying
    if target_dir.exists() and force:
        shutil.rmtree(target_dir, ignore_errors=True)

    target_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    copied_items: List[str] = []

    # 2. Copy knowledge/
    src_knowledge = p_root / "knowledge"
    if src_knowledge.exists() and src_knowledge.is_dir():
        dst_knowledge = target_dir / "knowledge"
        shutil.copytree(
            src_knowledge,
            dst_knowledge,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.tmp"),
        )
        copied_items.append("knowledge")

    # 3. Copy config/
    src_config = p_root / "config"
    if src_config.exists() and src_config.is_dir():
        dst_config = target_dir / "config"
        shutil.copytree(
            src_config,
            dst_config,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        copied_items.append("config")

    # 4. Copy proactive/triggers.json
    src_triggers = p_root / "proactive" / "triggers.json"
    if src_triggers.exists():
        dst_proactive = target_dir / "proactive"
        dst_proactive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_triggers, dst_proactive / "triggers.json")
        # Also copy to root of backup for convenience
        shutil.copy2(src_triggers, target_dir / "triggers.json")
        copied_items.append("proactive/triggers.json")

    # 5. Copy logs/errors.db (safely handling active lock)
    src_errors_db = p_root / "logs" / "errors.db"
    if src_errors_db.exists():
        dst_logs = target_dir / "logs"
        dst_logs.mkdir(parents=True, exist_ok=True)
        try:
            # Use sqlite3 online backup if possible, else copy2
            import sqlite3
            with sqlite3.connect(str(src_errors_db)) as src_conn:
                with sqlite3.connect(str(dst_logs / "errors.db")) as dst_conn:
                    src_conn.backup(dst_conn)
        except Exception:
            shutil.copy2(src_errors_db, dst_logs / "errors.db")
        copied_items.append("logs/errors.db")

    duration = round(time.time() - t0, 3)
    file_count, total_bytes = _get_dir_stats(target_dir)
    size_mb = round(total_bytes / (1024 * 1024), 2)

    # 6. Write backup manifest
    manifest = {
        "backup_date": today_str,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "created_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": file_count,
        "total_bytes": total_bytes,
        "size_mb": size_mb,
        "items_backed_up": copied_items,
        "source_project": str(p_root),
        "duration_seconds": duration,
    }
    with open(target_dir / "backup_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 7. Prune backups older than 7 days
    pruned = prune_backups(b_root, keep_days=7)

    # 8. Log audit record
    _log_backup_event(
        "CREATE",
        {
            "date": today_str,
            "status": "SUCCESS",
            "files": file_count,
            "size_mb": size_mb,
            "path": str(target_dir),
            "pruned": pruned,
            "duration": f"{duration}s",
        },
        p_root,
    )

    return {
        "status": "SUCCESS",
        "date": today_str,
        "path": str(target_dir),
        "total_files": file_count,
        "total_bytes": total_bytes,
        "size_mb": size_mb,
        "items": copied_items,
        "pruned": pruned,
        "duration_seconds": duration,
    }


def list_backups(backup_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns list of all available daily backups sorted by date descending.
    Each entry contains date, path, total_files, size_bytes, size_mb, and created_time.
    """
    b_root = get_backup_root(backup_root)
    if not b_root.exists():
        return []

    backups: List[Dict[str, Any]] = []
    for item in b_root.iterdir():
        if item.is_dir() and DATE_PATTERN.match(item.name):
            file_count, total_bytes = _get_dir_stats(item)
            manifest_file = item / "backup_manifest.json"
            created_str = item.name
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        m = json.load(f)
                        created_str = m.get("created_local") or m.get("timestamp_utc", item.name)
                except Exception:
                    pass

            backups.append({
                "date": item.name,
                "path": str(item),
                "total_files": file_count,
                "size_bytes": total_bytes,
                "size_mb": round(total_bytes / (1024 * 1024), 2),
                "size_kb": round(total_bytes / 1024, 1),
                "created": created_str,
            })

    backups.sort(key=lambda x: x["date"], reverse=True)
    return backups


def restore_backup(
    backup_date: str,
    backup_root: Optional[str] = None,
    target_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Restores critical data from <backup_root>/<backup_date>/ into target_root.
    """
    clean_date = str(backup_date).strip()
    b_root = get_backup_root(backup_root)
    src_dir = b_root / clean_date

    if not src_dir.exists() or not src_dir.is_dir():
        return {
            "status": "NOT_FOUND",
            "date": clean_date,
            "message": f"Backup directory '{clean_date}' not found at {b_root}.",
        }

    p_root = Path(target_root).resolve() if target_root else get_project_root()
    restored_items: List[str] = []
    t0 = time.time()

    # 1. Restore knowledge/
    src_k = src_dir / "knowledge"
    if src_k.exists():
        dst_k = p_root / "knowledge"
        shutil.copytree(src_k, dst_k, dirs_exist_ok=True)
        restored_items.append("knowledge")

    # 2. Restore config/
    src_c = src_dir / "config"
    if src_c.exists():
        dst_c = p_root / "config"
        shutil.copytree(src_c, dst_c, dirs_exist_ok=True)
        restored_items.append("config")

    # 3. Restore proactive/triggers.json
    src_t = src_dir / "proactive" / "triggers.json"
    if not src_t.exists():
        src_t = src_dir / "triggers.json"
    if src_t.exists():
        dst_p = p_root / "proactive"
        dst_p.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_t, dst_p / "triggers.json")
        restored_items.append("proactive/triggers.json")

    # 4. Restore logs/errors.db
    src_e = src_dir / "logs" / "errors.db"
    if src_e.exists():
        dst_l = p_root / "logs"
        dst_l.mkdir(parents=True, exist_ok=True)
        try:
            import sqlite3
            with sqlite3.connect(str(src_e)) as s_conn:
                with sqlite3.connect(str(dst_l / "errors.db")) as d_conn:
                    s_conn.backup(d_conn)
        except Exception:
            shutil.copy2(src_e, dst_l / "errors.db")
        restored_items.append("logs/errors.db")

    duration = round(time.time() - t0, 3)
    _log_backup_event("RESTORE", {"date": clean_date, "status": "SUCCESS", "items": restored_items, "duration": f"{duration}s"}, p_root)

    return {
        "status": "SUCCESS",
        "date": clean_date,
        "restored_items": restored_items,
        "target_directory": str(p_root),
        "duration_seconds": duration,
    }


def main():
    parser = argparse.ArgumentParser(description="Orvix Sphere Automatic Backup System")
    parser.add_argument("--now", action="store_true", help="Run backup immediately")
    parser.add_argument("--force", action="store_true", help="Overwrite existing backup for today")
    parser.add_argument("--list", action="store_true", help="List all existing backups")
    parser.add_argument("--restore", type=str, default=None, help="Restore from specific backup date (YYYYMMDD)")
    parser.add_argument("--backup-dir", type=str, default=None, help="Custom backup directory path")
    args = parser.parse_args()

    if args.list:
        backups = list_backups(args.backup_dir)
        print(f"\n📦 Orvix Sphere Backups ({len(backups)} available):")
        if not backups:
            print("  No backups found.")
        else:
            print(f"  {'Date':<10} {'Size':<10} {'Files':<8} {'Created / Timestamp':<22} {'Path'}")
            print(f"  {'-'*10} {'-'*10} {'-'*8} {'-'*22} {'-'*30}")
            for b in backups:
                print(f"  {b['date']:<10} {b['size_mb']:<7} MB {b['total_files']:<8} {str(b['created'])[:22]:<22} {b['path']}")
        print()
        return

    if args.restore:
        print(f"\n🔄 Restoring Orvix Sphere from backup: {args.restore}...")
        res = restore_backup(args.restore, backup_root=args.backup_dir)
        if res["status"] == "SUCCESS":
            print(f"✅ Successfully restored {len(res['restored_items'])} components from {res['date']} in {res['duration_seconds']}s.")
            for item in res["restored_items"]:
                print(f"  • Restored: {item}")
        else:
            print(f"⚠️ Restore failed: {res.get('message', 'Unknown error')}")
        print()
        return

    # Default: create backup
    print("\n🚀 Running Orvix Sphere Critical Data Backup...")
    res = create_backup(backup_root=args.backup_dir, force=args.force)
    if res["status"] == "SUCCESS":
        print(f"✅ Backup created successfully at: {res['path']}")
        print(f"  • Date:        {res['date']}")
        print(f"  • Total Files: {res['total_files']}")
        print(f"  • Total Size:  {res['size_mb']} MB ({res['total_bytes']:,} bytes)")
        print(f"  • Components:  {', '.join(res['items'])}")
        print(f"  • Pruned:      {res['pruned']} older backup(s)")
        print(f"  • Duration:    {res['duration_seconds']}s\n")
    elif res["status"] == "SKIPPED":
        print(f"ℹ️ {res['message']}")
        print(f"  • Existing:    {res['path']} ({res['size_mb']} MB, {res['total_files']} files)")
        print("  • Tip: Use '--force' or '/backup now --force' to overwrite.\n")
    else:
        print(f"⚠️ Backup failed: {res.get('message')}\n")


if __name__ == "__main__":
    main()
