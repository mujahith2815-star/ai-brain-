"""
Tests for Project Cleaner, Reorganizer, and Manifest Generator.
"""

import pytest
from pathlib import Path
from tools.project_cleaner import (
    find_duplicates,
    clean_cache_and_orphans,
    create_backup,
    reorganize_project,
    generate_manifest,
    generate_summary,
)


def test_find_duplicates(tmp_path):
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f3 = tmp_path / "unique.txt"

    content = "Hello duplicate world content 12345"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")
    f3.write_text("Completely different file content", encoding="utf-8")

    dups = find_duplicates(str(tmp_path))
    assert len(dups) == 1
    paths = list(dups.values())[0]
    assert len(paths) == 2


def test_clean_cache_and_orphans(tmp_path):
    pyc_file = tmp_path / "compiled.pyc"
    pyc_file.write_bytes(b"\x00\x01\x02")

    # Dry run
    dry_res = clean_cache_and_orphans(str(tmp_path), dry_run=True)
    assert dry_res["removed_files_count"] >= 1
    assert pyc_file.exists()

    # Live clean
    clean_res = clean_cache_and_orphans(str(tmp_path), dry_run=False)
    assert clean_res["removed_files_count"] >= 1
    assert not pyc_file.exists()


def test_create_backup(tmp_path):
    src = tmp_path / "project_src"
    src.mkdir()
    (src / "test.py").write_text("print('hello')", encoding="utf-8")

    backup_dest = tmp_path / "backups"
    backup_file = create_backup(str(src), backup_dest=str(backup_dest))
    assert Path(backup_file).exists()
    assert backup_file.endswith(".zip")


def test_reorganize_project(tmp_path):
    res = reorganize_project(str(tmp_path), dry_run=False)
    assert res["status"] == "SUCCESS"
    for d in ["core", "tools", "tests", "docs", "scripts"]:
        assert (tmp_path / d).exists()


def test_generate_manifest_and_summary(tmp_path):
    (tmp_path / "fileA.txt").write_text("Sample file A", encoding="utf-8")
    (tmp_path / "fileB.txt").write_text("Sample file B", encoding="utf-8")

    manifest = generate_manifest(str(tmp_path))
    assert manifest["total_files"] >= 2
    assert (tmp_path / "CLEAN_MANIFEST.json").exists()

    summary_file = tmp_path / "CLEAN_SUMMARY.md"
    summary_text = generate_summary(manifest, output_path=str(summary_file))
    assert summary_file.exists()
    assert "Codebase Audit & Hygiene Report" in summary_text
