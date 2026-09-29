"""
Unit tests for the Automatic Backup System of Orvix Sphere (v1.4.3).
Verifies:
1. Critical files copying (knowledge, config, triggers, errors.db)
2. Models exclusion (models/ is never backed up)
3. Same-day skip logic and force overwrite
4. 7-day rolling retention pruning
5. Listing backups with metadata
6. Restoring backups cleanly
7. Audit logging to logs/backup.log
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pytest

from scripts.backup_orvix import (
    create_backup,
    list_backups,
    restore_backup,
    prune_backups,
    _get_dir_stats,
)


@pytest.fixture
def test_env(tmp_path):
    """Sets up an isolated project root and backup root for testing."""
    proj = tmp_path / "project"
    backup = tmp_path / "backups"
    proj.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)

    # 1. Setup knowledge/
    k_dir = proj / "knowledge"
    k_dir.mkdir(parents=True, exist_ok=True)
    (k_dir / "notes.txt").write_text("Important knowledge notes", encoding="utf-8")
    (k_dir / "commands.json").write_text('{"cmd": "test"}', encoding="utf-8")

    # 2. Setup config/
    c_dir = proj / "config"
    c_dir.mkdir(parents=True, exist_ok=True)
    (c_dir / "settings.yaml").write_text("mode: test\nretries: 3", encoding="utf-8")

    # 3. Setup proactive/triggers.json
    p_dir = proj / "proactive"
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "triggers.json").write_text('[{"name": "test_trigger", "type": "CRON"}]', encoding="utf-8")

    # 4. Setup logs/errors.db
    l_dir = proj / "logs"
    l_dir.mkdir(parents=True, exist_ok=True)
    (l_dir / "errors.db").write_text("SQLite format 3 dummy db data", encoding="utf-8")

    # 5. Setup models/ (oversized data that should NEVER be backed up)
    m_dir = proj / "models"
    m_dir.mkdir(parents=True, exist_ok=True)
    (m_dir / "huge_model.bin").write_text("A" * 1024 * 100, encoding="utf-8")

    return {
        "project_root": proj,
        "backup_root": backup,
    }


def test_create_backup_copies_critical_files(test_env):
    """Verifies that create_backup copies knowledge, config, triggers.json, errors.db and generates manifest."""
    res = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    assert res["status"] == "SUCCESS"
    target_dir = Path(res["path"])
    assert target_dir.exists()

    # Check components exist in backup
    assert (target_dir / "knowledge" / "notes.txt").exists()
    assert (target_dir / "knowledge" / "commands.json").exists()
    assert (target_dir / "config" / "settings.yaml").exists()
    assert (target_dir / "proactive" / "triggers.json").exists()
    assert (target_dir / "triggers.json").exists()
    assert (target_dir / "logs" / "errors.db").exists()

    # Check manifest
    manifest_path = target_dir / "backup_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["backup_date"] == res["date"]
    assert "knowledge" in manifest["items_backed_up"]
    assert manifest["total_files"] >= 4


def test_models_not_backed_up(test_env):
    """Verifies that the models/ directory is strictly excluded from backups."""
    res = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    assert res["status"] == "SUCCESS"
    target_dir = Path(res["path"])

    assert not (target_dir / "models").exists()
    assert not (target_dir / "huge_model.bin").exists()


def test_create_backup_skips_if_already_exists(test_env):
    """Verifies that create_backup skips same-day backup when force is False."""
    res1 = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    assert res1["status"] == "SUCCESS"

    res2 = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=False,
    )
    assert res2["status"] == "SKIPPED"
    assert "already exists" in res2["message"]


def test_create_backup_force_overwrites(test_env):
    """Verifies that create_backup overwrites today's backup when force is True."""
    res1 = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    assert res1["status"] == "SUCCESS"

    # Add extra file to project knowledge
    extra = test_env["project_root"] / "knowledge" / "new_doc.txt"
    extra.write_text("brand new document", encoding="utf-8")

    res2 = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    assert res2["status"] == "SUCCESS"
    target_dir = Path(res2["path"])
    assert (target_dir / "knowledge" / "new_doc.txt").exists()


def test_prune_backups_keeps_7_days(test_env):
    """Verifies rolling retention keeps only the 7 most recent backups and prunes older ones."""
    b_root = test_env["backup_root"]

    # Create 10 mock date folders: 20260901 through 20260910
    dates = [f"2026090{i}" if i < 10 else f"202609{i}" for i in range(1, 11)]
    for d in dates:
        d_dir = b_root / d
        d_dir.mkdir(parents=True, exist_ok=True)
        (d_dir / "test.txt").write_text("data", encoding="utf-8")

    assert len(list_backups(str(b_root))) == 10

    # Prune keeping 7 days
    pruned = prune_backups(b_root, keep_days=7)
    assert pruned == 3

    remaining = list_backups(str(b_root))
    assert len(remaining) == 7
    remaining_dates = [b["date"] for b in remaining]
    # The remaining 7 should be the newest: 20260904 through 20260910
    assert "20260910" in remaining_dates
    assert "20260904" in remaining_dates
    assert "20260901" not in remaining_dates
    assert "20260902" not in remaining_dates
    assert "20260903" not in remaining_dates


def test_list_backups_returns_metadata(test_env):
    """Verifies list_backups accurately reports file counts, sizes, and paths."""
    res = create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    backups = list_backups(str(test_env["backup_root"]))
    assert len(backups) == 1
    b = backups[0]
    assert b["date"] == res["date"]
    assert b["total_files"] >= 4
    assert b["size_bytes"] > 0
    assert "path" in b


def test_restore_backup_restores_files(test_env):
    """Verifies restore_backup restores overwritten/deleted files from backup."""
    # 1. Create backup
    create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    today_str = datetime.now().strftime("%Y%m%d")

    # 2. Corrupt or delete files in project root
    notes_file = test_env["project_root"] / "knowledge" / "notes.txt"
    notes_file.write_text("Corrupted content!!", encoding="utf-8")

    triggers_file = test_env["project_root"] / "proactive" / "triggers.json"
    triggers_file.unlink()

    # 3. Restore
    restore_res = restore_backup(
        backup_date=today_str,
        backup_root=str(test_env["backup_root"]),
        target_root=str(test_env["project_root"]),
    )
    assert restore_res["status"] == "SUCCESS"
    assert "knowledge" in restore_res["restored_items"]
    assert "proactive/triggers.json" in restore_res["restored_items"]

    # 4. Verify original content restored
    assert notes_file.read_text(encoding="utf-8") == "Important knowledge notes"
    assert triggers_file.exists()


def test_backup_log_recorded(test_env):
    """Verifies audit events are logged to logs/backup.log."""
    create_backup(
        backup_root=str(test_env["backup_root"]),
        project_root=str(test_env["project_root"]),
        force=True,
    )
    log_file = test_env["project_root"] / "logs" / "backup.log"
    assert log_file.exists()
    log_content = log_file.read_text(encoding="utf-8")
    assert "CREATE" in log_content
    assert "SUCCESS" in log_content
