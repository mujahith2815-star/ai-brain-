"""
Unit Tests for Automatic Smart File Search on Read Failures in Orvix Sphere.
Verifies:
1. test_file_reader_finds_file_in_desktop
2. test_file_reader_finds_file_in_documents
3. test_file_reader_multiple_matches
4. test_file_reader_no_matches_returns_helpful_error
5. test_file_reader_respects_explicit_path
"""

import os
from pathlib import Path
import pytest

from tools.builtin_tools import file_reader
from tools.terminal_tools import find_file_smart
from tools.executor import ToolExecutor


@pytest.mark.asyncio
async def test_file_reader_finds_file_in_desktop(tmp_path):
    """Verifies that file_reader automatically finds a file placed in ~/Desktop."""
    fake_desktop = tmp_path / "Desktop"
    fake_desktop.mkdir(parents=True, exist_ok=True)
    test_file = fake_desktop / "test_notes_desktop.txt"
    test_content = "Meeting at 3pm. Cost 150. Attendees 5. Budget 2000."
    test_file.write_text(test_content, encoding="utf-8")

    res = await file_reader("test_notes_desktop.txt", search_paths=[str(fake_desktop)])

    assert res["status"] == "SUCCESS"
    assert os.path.normpath(res["path"]).lower() == os.path.normpath(str(test_file)).lower()
    assert test_content in res["content"]
    assert "Found at" in res.get("note", "")
    assert "searched from test_notes_desktop.txt" in res.get("note", "")


@pytest.mark.asyncio
async def test_file_reader_finds_file_in_documents(tmp_path):
    """Verifies that file_reader automatically finds a file placed in ~/Documents."""
    fake_docs = tmp_path / "Documents"
    fake_docs.mkdir(parents=True, exist_ok=True)
    test_file = fake_docs / "test_notes_docs.txt"
    test_content = "Quarterly financial report data: Q1 revenue 45000."
    test_file.write_text(test_content, encoding="utf-8")

    res = await file_reader("test_notes_docs.txt", search_paths=[str(fake_docs)])

    assert res["status"] == "SUCCESS"
    assert os.path.normpath(res["path"]).lower() == os.path.normpath(str(test_file)).lower()
    assert test_content in res["content"]
    assert "Found at" in res.get("note", "")


@pytest.mark.asyncio
async def test_file_reader_multiple_matches(tmp_path):
    """Verifies that file_reader detects multiple matches and returns MULTIPLE_MATCHES."""
    folder_a = tmp_path / "folder_a"
    folder_b = tmp_path / "folder_b"
    folder_a.mkdir(parents=True, exist_ok=True)
    folder_b.mkdir(parents=True, exist_ok=True)

    file_a = folder_a / "duplicate_report.txt"
    file_b = folder_b / "duplicate_report.txt"
    file_a.write_text("Report version A", encoding="utf-8")
    file_b.write_text("Report version B", encoding="utf-8")

    res = await file_reader("duplicate_report.txt", search_paths=[str(folder_a), str(folder_b)])

    assert res["status"] == "MULTIPLE_MATCHES"
    assert len(res["matches"]) >= 2
    match_paths = [os.path.normpath(p).lower() for p in res["matches"]]
    assert os.path.normpath(str(file_a)).lower() in match_paths
    assert os.path.normpath(str(file_b)).lower() in match_paths
    assert "Found multiple files" in res["note"]


@pytest.mark.asyncio
async def test_file_reader_no_matches_returns_helpful_error():
    """Verifies that file_reader returns NOT_FOUND with searched paths when file does not exist."""
    missing_filename = "definitely_nonexistent_notes_999xyz.txt"
    res = await file_reader(missing_filename)

    assert res["status"] == "NOT_FOUND"
    assert "searched_paths" in res
    assert len(res["searched_paths"]) >= 5
    assert missing_filename in res["note"]
    assert "Please provide the full path" in res["note"]
    assert "does not exist" in str(res.get("error"))


@pytest.mark.asyncio
async def test_file_reader_respects_explicit_path(tmp_path):
    """Verifies that an explicit, existing path is read directly without triggering a search note."""
    explicit_file = tmp_path / "explicit_direct_read.txt"
    explicit_content = "Explicit direct content - no search required."
    explicit_file.write_text(explicit_content, encoding="utf-8")

    res = await file_reader(str(explicit_file))

    assert res["status"] == "SUCCESS"
    assert os.path.normpath(res["path"]).lower() == os.path.normpath(str(explicit_file)).lower()
    assert explicit_content in res["content"]
    assert "searched from" not in res.get("note", "")


def test_find_file_smart_constraints(tmp_path):
    """Verifies constraints: max depth 3, skipping system dirs, and logging."""
    root = tmp_path / "test_root"
    root.mkdir()
    l1 = root / "level1"
    l1.mkdir()
    l2 = l1 / "level2"
    l2.mkdir()
    l3 = l2 / "level3"
    l3.mkdir()
    l4 = l3 / "level4"
    l4.mkdir()

    valid_file = l2 / "target_valid.txt"
    valid_file.write_text("Found me!", encoding="utf-8")

    deep_file = l4 / "target_deep.txt"
    deep_file.write_text("Too deep!", encoding="utf-8")

    sys_dir = root / "node_modules"
    sys_dir.mkdir()
    skipped_file = sys_dir / "target_skip.txt"
    skipped_file.write_text("In system dir!", encoding="utf-8")

    # 1. Valid file within depth 3
    matches_valid = find_file_smart("target_valid.txt", extra_paths=[str(root)])
    assert any(os.path.normpath(str(valid_file)).lower() == os.path.normpath(m).lower() for m in matches_valid)

    # 2. Deep file beyond depth 3 is skipped
    matches_deep = find_file_smart("target_deep.txt", extra_paths=[str(root)])
    assert not any(os.path.normpath(str(deep_file)).lower() == os.path.normpath(m).lower() for m in matches_deep)

    # 3. System dir file is skipped
    matches_sys = find_file_smart("target_skip.txt", extra_paths=[str(root)])
    assert not any(os.path.normpath(str(skipped_file)).lower() == os.path.normpath(m).lower() for m in matches_sys)

    # 4. Check log file written
    log_file = Path(__file__).resolve().parent.parent / "logs" / "file_search.log"
    assert log_file.exists()
