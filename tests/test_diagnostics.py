"""
Unit Tests for Orvix Sphere SystemDoctor Diagnostic Health Suite.
"""

import pytest
import sys
from diagnostics.doctor import SystemDoctor


def test_doctor_instantiation():
    doc = SystemDoctor()
    assert doc.workspace.exists()


def test_check_python_version():
    doc = SystemDoctor()
    ok, msg = doc.check_python_version()
    assert ok is True
    assert "Python 3." in msg


def test_check_dependencies():
    doc = SystemDoctor()
    ok, msg = doc.check_required_packages()
    assert ok is True
    assert "dependencies installed" in msg


def test_check_sqlite():
    doc = SystemDoctor()
    ok, msg = doc.check_sqlite_db()
    assert ok is True
    assert "Database accessible" in msg


def test_check_disk_space():
    doc = SystemDoctor()
    ok, msg = doc.check_disk_space()
    assert ok is True
    assert "GB disk space free" in msg


def test_check_write_permissions():
    doc = SystemDoctor()
    ok, msg = doc.check_write_permissions()
    assert ok is True
    assert "writable" in msg


def test_check_vector_storage():
    doc = SystemDoctor()
    ok, msg = doc.check_vector_store()
    assert ok is True


def test_check_mcp_servers():
    doc = SystemDoctor()
    ok, msg = doc.check_mcp_servers()
    assert ok is True


def test_check_proactive_scheduler():
    doc = SystemDoctor()
    ok, msg = doc.check_proactive_scheduler()
    assert ok is True


def test_check_model_configuration():
    doc = SystemDoctor()
    ok, msg = doc.check_models()
    assert ok is True


def test_run_full_check():
    doc = SystemDoctor()
    report = doc.run_full_check()
    assert report["healthy"] is True
    assert report["total_checks"] == 9
    assert report["passed_checks"] == 9
    assert len(report["checks"]) == 9
    for item in report["checks"]:
        assert "check" in item
        assert item["passed"] is True


def test_format_report_string():
    doc = SystemDoctor()
    text = doc.format_report()
    assert "ORVIX SPHERE SYSTEM HEALTH DIAGNOSTIC REPORT" in text
    assert "ALL SYSTEMS OPERATIONAL" in text
    assert "Python Runtime" in text
