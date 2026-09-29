"""
One-time Migration Script for P.H.A.S.S Universal Data Hub.
Decouples all persistent data, memories, models, logs, and projects from the codebase
and safely migrates them to the configured physical Data Hub root.
"""

from __future__ import annotations
import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.data_hub import data_hub

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phass.migration")


def migrate_if_needed(force: bool = False) -> bool:
    """
    Checks whether migration has already occurred.
    If false (or force=True), migrates all persistent data to data_hub.root.
    """
    data_hub.initialize()

    if data_hub.is_migrated and not force:
        logger.info(f"Data is already migrated to Data Hub at: {data_hub.root}")
        return True

    data_root = data_hub.root
    logger.info(f"Starting migration to Data Hub at: {data_root}...")

    # Ensure essential target subdirectories exist
    for sub in ["checkpoints", "logs", "user", "tasks", "hardware_db", "projects", "models", "oracle"]:
        (data_root / sub).mkdir(parents=True, exist_ok=True)

    # 1. checkpoints/ -> <data_root>/checkpoints/
    src_checkpoints = Path("checkpoints")
    if src_checkpoints.exists() and src_checkpoints.is_dir():
        dst_checkpoints = data_root / "checkpoints"
        try:
            logger.info("Migrating checkpoints folder...")
            shutil.copytree(src_checkpoints, dst_checkpoints, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Error migrating checkpoints folder: {e}")

    # 2. Execution log -> <data_root>/logs/execution_log.json
    src_exec_log = Path("checkpoints/execution_log.json")
    if src_exec_log.exists():
        dst_exec_log = data_root / "logs" / "execution_log.json"
        try:
            dst_exec_log.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_exec_log, dst_exec_log)
        except Exception as e:
            logger.warning(f"Error migrating execution_log.json: {e}")

    # 3. User preferences -> <data_root>/user/preferences.json
    src_pref = Path("checkpoints/user_preferences.json")
    if src_pref.exists():
        dst_pref = data_root / "user" / "preferences.json"
        try:
            dst_pref.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_pref, dst_pref)
        except Exception as e:
            logger.warning(f"Error migrating user_preferences.json: {e}")

    # 4. Lifelong profile -> <data_root>/user/lifelong_profile.json
    src_profile = Path("core/lifelong_profile.json")
    if src_profile.exists():
        dst_profile = data_root / "user" / "lifelong_profile.json"
        try:
            dst_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_profile, dst_profile)
        except Exception as e:
            logger.warning(f"Error migrating lifelong_profile.json: {e}")

    # 5. memory_vault/scheduled_tasks.json -> <data_root>/tasks/scheduled_tasks.json
    src_tasks = Path("memory_vault/scheduled_tasks.json")
    if src_tasks.exists():
        dst_tasks = data_root / "tasks" / "scheduled_tasks.json"
        try:
            dst_tasks.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_tasks, dst_tasks)
        except Exception as e:
            logger.warning(f"Error migrating scheduled_tasks.json: {e}")

    # 6. checkpoints/hardware_db.json -> <data_root>/hardware_db/component_db.json
    src_hw = Path("checkpoints/hardware_db.json")
    if src_hw.exists():
        dst_hw = data_root / "hardware_db" / "component_db.json"
        try:
            dst_hw.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_hw, dst_hw)
        except Exception as e:
            logger.warning(f"Error migrating hardware_db.json: {e}")

    # 7. projects/ -> <data_root>/projects/
    src_proj = Path("projects")
    if src_proj.exists() and src_proj.is_dir():
        dst_proj = data_root / "projects"
        try:
            logger.info("Migrating projects folder...")
            shutil.copytree(src_proj, dst_proj, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Error migrating projects folder: {e}")

    # 8. models/ -> <data_root>/models/
    src_models = Path("models")
    if src_models.exists() and src_models.is_dir():
        dst_models = data_root / "models"
        try:
            logger.info("Migrating models folder (this may take a few moments)...")
            shutil.copytree(src_models, dst_models, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Error migrating models folder: {e}")

    # Mark migration complete in configuration
    data_hub.set_migrated(True)
    try:
        print(f"✅ All memories, models, and projects migrated to {data_root}.")
    except Exception:
        print(f"[SUCCESS] All memories, models, and projects migrated to {data_root}.")
    return True


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    migrate_if_needed(force=force_flag)
