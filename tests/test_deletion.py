"""
Comprehensive Unit & Integration Test Suite for Safe File Deletion,
Disk Space Analysis, Duplicate File Detection, Smart File Organization,
and User Preferences Memory in P.H.A.S.S Sphere.
"""

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from tools.file_deleter import delete_unwanted_files
from tools.file_organizer import analyze_disk_space, find_duplicate_files, smart_file_organizer
from core.user_preferences import UserPreferencesManager
from core.llama_tool_agent import llama_tool_agent
from config.llama_config import llama_config


@pytest.fixture
def test_sandbox():
    """Creates an isolated temporary sandbox directory with mock files."""
    temp_dir = tempfile.mkdtemp(prefix="phass_test_sandbox_")
    sandbox = Path(temp_dir)

    # Create dummy files
    (sandbox / "doc1.txt").write_text("Document 1 content", encoding="utf-8")
    (sandbox / "doc2.pdf").write_text("PDF mock content", encoding="utf-8")
    (sandbox / "temp_1.tmp").write_text("Temporary file 1", encoding="utf-8")
    (sandbox / "temp_2.tmp").write_text("Temporary file 2", encoding="utf-8")
    (sandbox / "app.log").write_text("Log file content", encoding="utf-8")
    (sandbox / "script.py").write_text("print('hello')", encoding="utf-8")

    # Create subfolder with files
    sub = sandbox / "nested"
    sub.mkdir()
    (sub / "nested_temp.tmp").write_text("Nested temporary", encoding="utf-8")
    (sub / "nested_doc.txt").write_text("Nested doc", encoding="utf-8")

    yield sandbox

    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSafeFileDeleter:
    def test_dry_run_does_not_delete_files(self, test_sandbox):
        """dry_run=True must preview files without removing them."""
        res = delete_unwanted_files(str(test_sandbox), pattern="*.tmp", dry_run=True)
        assert res["status"] == "SUCCESS"
        assert res["deleted_count"] == 3  # temp_1.tmp, temp_2.tmp, nested_temp.tmp
        assert "DRY RUN" in res["message"]
        
        # Verify files still exist on disk
        assert (test_sandbox / "temp_1.tmp").exists()
        assert (test_sandbox / "temp_2.tmp").exists()
        assert (test_sandbox / "nested" / "nested_temp.tmp").exists()

    def test_extension_filter(self, test_sandbox):
        """Targeting specific extensions should only match those extensions."""
        res = delete_unwanted_files(str(test_sandbox), extensions=[".log"], dry_run=True)
        assert res["deleted_count"] == 1
        file_paths = [f["path"] for f in res["file_list"]]
        assert any(p.endswith("app.log") for p in file_paths)
        assert not any(p.endswith(".tmp") for p in file_paths)

    def test_actual_deletion_with_dry_run_false(self, test_sandbox):
        """dry_run=False should permanently delete matching files."""
        res = delete_unwanted_files(str(test_sandbox), extensions=[".tmp"], dry_run=False)
        assert res["status"] == "SUCCESS"
        assert res["deleted_count"] == 3
        assert not (test_sandbox / "temp_1.tmp").exists()
        assert not (test_sandbox / "temp_2.tmp").exists()
        assert not (test_sandbox / "nested" / "nested_temp.tmp").exists()
        # Non-tmp files must be preserved
        assert (test_sandbox / "doc1.txt").exists()
        assert (test_sandbox / "script.py").exists()

    def test_older_than_days_filter(self, test_sandbox):
        """Files newer than older_than_days should be skipped."""
        old_file = test_sandbox / "ancient.tmp"
        old_file.write_text("Ancient temporary file", encoding="utf-8")
        
        # Set file modification time to 10 days ago
        ten_days_ago = time.time() - (10 * 86400)
        os.utime(str(old_file), (ten_days_ago, ten_days_ago))

        res = delete_unwanted_files(str(test_sandbox), extensions=[".tmp"], older_than_days=5, dry_run=True)
        assert res["deleted_count"] == 1
        assert res["file_list"][0]["path"] == str(old_file)

    def test_safety_protection_system_and_git_folders(self, test_sandbox):
        """Files inside .git or __pycache__ must be protected from deletion."""
        git_dir = test_sandbox / ".git"
        git_dir.mkdir()
        (git_dir / "temp_in_git.tmp").write_text("Critical git temp", encoding="utf-8")

        pycache_dir = test_sandbox / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "temp_in_cache.tmp").write_text("Cache temp", encoding="utf-8")

        res = delete_unwanted_files(str(test_sandbox), pattern="*.tmp", dry_run=False)
        # Git and cache files should be skipped
        assert (git_dir / "temp_in_git.tmp").exists()
        assert (pycache_dir / "temp_in_cache.tmp").exists()

    def test_nonexistent_directory_fails_gracefully(self):
        """Targeting a nonexistent directory should report FAILED without crashing."""
        res = delete_unwanted_files("C:/non_existent_folder_xyz_123", dry_run=True)
        assert res["status"] == "FAILED"
        assert len(res["errors"]) > 0


class TestFileOrganizerAndAnalysis:
    def test_analyze_disk_space(self, test_sandbox):
        """analyze_disk_space should calculate file counts and categorized sizes."""
        res = analyze_disk_space(str(test_sandbox))
        assert res["status"] == "SUCCESS"
        assert res["total_files"] >= 7
        assert "Documents" in res["category_breakdown_mb"]
        assert "Code" in res["category_breakdown_mb"]

    def test_find_duplicate_files(self, test_sandbox):
        """find_duplicate_files should use SHA-256 to locate identical files."""
        # Create identical content duplicates
        (test_sandbox / "dup_a.txt").write_text("Identical duplicate content 12345", encoding="utf-8")
        (test_sandbox / "dup_b.txt").write_text("Identical duplicate content 12345", encoding="utf-8")

        res = find_duplicate_files(str(test_sandbox))
        assert res["status"] == "SUCCESS"
        assert res["duplicate_groups_count"] >= 1
        dup_paths = [res["duplicates"][0]["original"]] + res["duplicates"][0]["duplicates"]
        assert any("dup_a.txt" in p for p in dup_paths)
        assert any("dup_b.txt" in p for p in dup_paths)

    def test_smart_file_organizer_dry_run_and_execution(self, test_sandbox):
        """smart_file_organizer dry run vs execution."""
        # Dry run preview
        dry_res = smart_file_organizer(str(test_sandbox), dry_run=True)
        assert dry_res["status"] == "SUCCESS"
        assert dry_res["mode"] == "DRY_RUN"
        assert dry_res["files_to_organize"] > 0
        assert (test_sandbox / "doc1.txt").exists()

        # Actual execution
        exec_res = smart_file_organizer(str(test_sandbox), dry_run=False)
        assert exec_res["status"] == "SUCCESS"
        assert exec_res["organized_count"] > 0
        # doc1.txt should now be in Documents subfolder
        assert (test_sandbox / "Documents" / "doc1.txt").exists()


class TestUserPreferencesMemory:
    def test_preferences_save_and_load(self, tmp_path):
        """UserPreferencesManager should persist favorite directories and commands."""
        pref_file = tmp_path / "test_prefs.json"
        mgr = UserPreferencesManager(str(pref_file))

        # Add favorite directories
        mgr.add_favorite_directory("C:/my_projects/web_app")
        mgr.add_favorite_directory("D:/data/models")
        assert len(mgr.get_favorite_directories()) == 2

        # Add common commands
        mgr.add_common_command("git status")
        mgr.add_common_command("pytest tests/")
        assert len(mgr.get_common_commands()) == 2

        # Verify persistence on disk
        assert pref_file.exists()
        with open(pref_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["favorite_directories"]) == 2
            assert "git status" in data["common_commands"]

        # Reload in a new manager instance
        reloaded = UserPreferencesManager(str(pref_file))
        assert len(reloaded.get_favorite_directories()) == 2
        assert len(reloaded.get_common_commands()) == 2


class TestLlamaToolAgentSafeAutomation:
    def test_agent_routes_deletion_with_dry_run_default(self, test_sandbox):
        """Agent should dispatch delete_unwanted_files with dry_run=True by default."""
        query = f"Delete unwanted .tmp files in {str(test_sandbox)}"
        res = llama_tool_agent.run_turn(query)
        assert res.success is True
        assert len(res.steps_executed) >= 1
        first_step = res.steps_executed[0]
        assert first_step.tool_name == "delete_unwanted_files"
        assert first_step.parameters.get("dry_run") is True
        # Verify files were not deleted
        assert (test_sandbox / "temp_1.tmp").exists()
        assert "Dry-Run" in res.final_response or "dry_run" in res.final_response.lower()

    def test_agent_routes_disk_space_analysis(self, test_sandbox):
        """Agent should dispatch analyze_disk_space."""
        query = f"Analyze disk space in {str(test_sandbox)}"
        res = llama_tool_agent.run_turn(query)
        assert res.success is True
        assert any(s.tool_name == "analyze_disk_space" for s in res.steps_executed)
        assert "Disk Space" in res.final_response

    def test_agent_routes_duplicate_finder(self, test_sandbox):
        """Agent should dispatch find_duplicate_files."""
        query = f"Find duplicate files in {str(test_sandbox)}"
        res = llama_tool_agent.run_turn(query)
        assert res.success is True
        assert any(s.tool_name == "find_duplicate_files" for s in res.steps_executed)

    def test_agent_saves_and_retrieves_favorite_directory(self):
        """Agent should remember and report favorite directories."""
        save_res = llama_tool_agent.run_turn("Remember my favorite directory is C:/work/phass")
        assert "saved" in save_res.final_response.lower()
        assert "C:\\work\\phass" in llama_tool_agent.preferences.get_favorite_directories() or "C:/work/phass" in llama_tool_agent.preferences.get_favorite_directories()

        query_res = llama_tool_agent.run_turn("What is my favorite directory")
        assert "C:" in query_res.final_response

    def test_agent_error_explanation_and_recovery_suggestions(self):
        """Agent must truthfully explain errors with actionable suggestions on failure."""
        res = llama_tool_agent.run_turn("Read document C:/totally_non_existent_folder_99/missing.txt")
        assert "failed" in res.final_response.lower() or "error" in res.final_response.lower()
        assert "Suggested steps" in res.final_response or "Verify" in res.final_response
