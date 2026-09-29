"""
Comprehensive Automated Test Suite for P.H.A.S.S Universal Data Hub Architecture.
Validates:
1. DataHub singleton resolution and directory auto-creation
2. MindPalace SQLite/ChromaDB persistence on physical Data Hub
3. User Preferences persistence on Data Hub
4. Lifelong Profile Manager persistence on Data Hub
5. Component Engine hardware DB resolution on Data Hub
6. Vibe Project Bootstrap scaffolding into Data Hub projects
7. Migration script idempotency and safety
8. Graceful fallback when configured drive is unmounted/invalid
"""

import os
import json
import pytest
import shutil
from pathlib import Path

from core.data_hub import data_hub, DataHub
from core.mind_palace import mind_palace
from core.user_preferences import UserPreferencesManager
from core.lifelong_profile_manager import LifelongProfileManager
from hardware.component_engine import ComponentEngine
from hardware.vibe_project_bootstrap import VibeProjectBootstrap
from migrate_to_data_hub import migrate_if_needed


def test_data_hub_initialization():
    """Verify DataHub initializes cleanly and provides root path."""
    data_hub.initialize()
    root = data_hub.root
    assert root is not None
    assert root.exists()
    assert data_hub.is_migrated is True


def test_data_hub_resolve_and_directory_creation():
    """Verify data_hub.resolve() builds valid paths and creates parent directories."""
    resolved_file = data_hub.resolve("test_suite", "nested_folder", "sample_test.json")
    assert resolved_file.parent.exists()
    assert str(resolved_file).startswith(str(data_hub.root))

    # Write test data
    test_payload = {"status": "ok", "hub_verified": True}
    with open(resolved_file, "w", encoding="utf-8") as f:
        json.dump(test_payload, f)

    assert resolved_file.exists()
    with open(resolved_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["hub_verified"] is True

    # Cleanup
    if resolved_file.exists():
        resolved_file.unlink()
    if resolved_file.parent.exists():
        shutil.rmtree(resolved_file.parent)


def test_mind_palace_data_hub_persistence():
    """Verify mind_palace interacts with checkpoints on Data Hub."""
    assert str(mind_palace.memory_path).startswith(str(data_hub.root))
    assert str(mind_palace.db_path).startswith(str(data_hub.root))

    row_id = mind_palace.store_conversation(
        session_id="test_hub_sess",
        user_msg="Testing physical Data Hub storage",
        assistant_msg="Mind Palace verified on physical disk",
    )
    assert row_id > 0

    mind_palace.store_user_preference("hardware", "favorite_chip", "ESP32-S3")
    prefs = mind_palace.get_user_preferences("hardware")
    assert prefs.get("favorite_chip") == "ESP32-S3"


def test_user_preferences_on_data_hub():
    """Verify user preferences are persisted to <data_root>/user/preferences.json."""
    pref_path = data_hub.resolve("user", "preferences.json")
    mgr = UserPreferencesManager()
    assert mgr.file_path == pref_path
    assert pref_path.parent.exists()

    test_dir = "W:/Test/DataHub/Directory"
    mgr.add_favorite_directory(test_dir)
    assert os.path.normpath(test_dir) in mgr.preferences.get("favorite_directories", [])

    # Verify directly from disk
    assert pref_path.exists()
    disk_data = json.loads(pref_path.read_text(encoding="utf-8"))
    assert os.path.normpath(test_dir) in disk_data.get("favorite_directories", [])


def test_lifelong_profile_on_data_hub():
    """Verify lifelong profile manager stores and reads from <data_root>/user/lifelong_profile.json."""
    profile_path = data_hub.resolve("user", "lifelong_profile.json")
    prof_mgr = LifelongProfileManager()
    assert prof_mgr.profile_path == profile_path
    assert profile_path.parent.exists()

    name = prof_mgr.real_name
    assert name == "M.Mohammed Mujahith"
    assert prof_mgr.save_profile() is True
    assert profile_path.exists()


def test_component_engine_on_data_hub():
    """Verify component engine resolves datasheet database from Data Hub."""
    engine = ComponentEngine()
    expected_hw_path = data_hub.resolve("hardware_db", "component_db.json")
    assert engine.db_json_path == expected_hw_path

    res = engine.fetch_datasheet("bc547")
    assert res["status"] == "SUCCESS"
    assert "BC547" in res["data"]["name"]


def test_vibe_project_bootstrap_on_data_hub():
    """Verify project bootstrapper scaffolding targets <data_root>/projects/ by default."""
    bootstrapper = VibeProjectBootstrap()
    assert bootstrapper.base_dir == data_hub.resolve("projects")

    test_proj_name = "test_hub_sensor_node"
    result = bootstrapper.bootstrap_project(test_proj_name)
    assert result["status"] == "SUCCESS"

    proj_dir = bootstrapper.base_dir / test_proj_name
    assert proj_dir.exists()
    assert (proj_dir / "firmware").exists()
    assert (proj_dir / "hardware").exists()
    assert (proj_dir / "README.md").exists()

    # Cleanup test scaffolded project
    shutil.rmtree(proj_dir)


def test_migrate_to_data_hub_idempotent():
    """Verify migrate_if_needed() is completely safe to call repeatedly."""
    res1 = migrate_if_needed()
    assert res1 is True

    res2 = migrate_if_needed()
    assert res2 is True


def test_data_hub_invalid_drive_fallback(tmp_path):
    """Verify that specifying an unmounted/non-existent drive falls back gracefully."""
    config_file = tmp_path / "test_hub_config.json"
    config_file.write_text(json.dumps({
        "data_root": "Z:/PHASS_NONEXISTENT_DRIVE_XYZ",
        "migrated": False,
        "version": "1.0"
    }), encoding="utf-8")

    hub = DataHub()
    root = hub.initialize(config_path=str(config_file))
    # It must fallback to an existing drive (e.g. W: or C:) without crashing
    assert root is not None
    assert root.exists()
