"""
Tests for Shadow Mode & Tripwire Security.
"""

import os
import pytest
from pathlib import Path
from security.shadow_mode import ShadowGuard


@pytest.fixture
def temp_shadow_guard(tmp_path):
    guard = ShadowGuard(security_dir=str(tmp_path / "shadow_security"))
    return guard


def test_high_risk_pattern_detection(temp_shadow_guard):
    # Critical risk
    risk1, reason1 = temp_shadow_guard.evaluate_risk("rm -rf /")
    assert risk1 == "CRITICAL"
    assert "rm -rf" in reason1

    risk2, reason2 = temp_shadow_guard.evaluate_risk("format C: /fs:NTFS")
    assert risk2 == "CRITICAL"

    risk3, reason3 = temp_shadow_guard.evaluate_risk("DROP TABLE users;")
    assert risk3 == "CRITICAL"

    # High risk
    risk4, reason4 = temp_shadow_guard.evaluate_risk("taskkill /F /IM explorer.exe")
    assert risk4 == "HIGH"

    # Safe
    risk5, reason5 = temp_shadow_guard.evaluate_risk("git status")
    assert risk5 == "SAFE"


def test_audit_logging_and_tamper_evident_chain(temp_shadow_guard):
    rec1 = temp_shadow_guard.audit_command("git pull origin main", auto_confirm=True)
    assert rec1["status"] == "APPROVED"
    assert "block_hash" in rec1

    rec2 = temp_shadow_guard.audit_command("rm -rf /tmp/scratch", auto_confirm=False)
    assert rec2["status"] == "BLOCKED"
    assert rec2["block_hash"] != rec1["block_hash"]

    history = temp_shadow_guard.get_audit_history()
    assert len(history) == 2
    assert history[0]["command"] == "git pull origin main"
    assert history[1]["status"] == "BLOCKED"


def test_snapshot_and_restore(temp_shadow_guard, tmp_path):
    # Setup test workspace
    work_dir = tmp_path / "important_data"
    work_dir.mkdir()
    (work_dir / "file1.txt").write_text("Original content 1", encoding="utf-8")
    (work_dir / "file2.txt").write_text("Original content 2", encoding="utf-8")

    # Create safety snapshot
    snap_res = temp_shadow_guard.create_snapshot(str(work_dir), snapshot_id="test_backup_01")
    assert snap_res["status"] == "SUCCESS"
    assert snap_res["snapshot_id"] == "test_backup_01"
    assert Path(snap_res["path"]).exists()

    # Simulate catastrophic corruption/deletion
    (work_dir / "file1.txt").write_text("CORRUPTED", encoding="utf-8")
    (work_dir / "file2.txt").unlink()

    # Restore snapshot
    restore_res = temp_shadow_guard.restore_snapshot("test_backup_01", str(work_dir))
    assert restore_res["status"] == "SUCCESS"

    # Verify content restored
    assert (work_dir / "file1.txt").read_text(encoding="utf-8") == "Original content 1"
    assert (work_dir / "file2.txt").exists()
    assert (work_dir / "file2.txt").read_text(encoding="utf-8") == "Original content 2"
