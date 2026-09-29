"""
Unit & Integration Tests for Universal Cross-Platform Environment Auto-Installer & Dependency Manager.
"""

import os
import pytest
from core.auto_environment_installer import (
    auto_environment_installer,
    SystemEnvironmentInfo,
    InstallationReport,
)
from nlp.conversational_agent import conversational_agent


# 1. System Environment Inspection
def test_system_environment_inspection():
    info = auto_environment_installer.inspect_system_environment()
    assert isinstance(info, SystemEnvironmentInfo)
    assert info.os_name in ("Windows", "Linux", "Darwin")
    assert info.python_version.startswith("3.")
    assert info.cpu_logical_cores >= 1
    assert info.total_ram_gb > 0.0
    assert os.path.exists(info.workspace_root)


# 2. Runtime Directory Scaffolding
def test_runtime_directory_scaffolding():
    created = auto_environment_installer.scaffold_runtime_directories()
    assert isinstance(created, list)
    for d_name in auto_environment_installer.RUNTIME_DIRECTORIES:
        assert os.path.exists(os.path.join(os.getcwd(), d_name))


# 3. Environment Auto-Provisioning
def test_auto_provision_environment():
    report = auto_environment_installer.auto_provision_environment(run_pip_install=False)
    assert isinstance(report, InstallationReport)
    assert "READY" in report.status
    assert report.installation_duration_sec >= 0.0
    assert len(report.verified_packages) >= 1

    rep_text = auto_environment_installer.format_readiness_report_text(report)
    assert "P.H.A.S.S UNIVERSAL ENVIRONMENT READINESS" in rep_text
    assert report.system_info.os_name in rep_text


# 4. Dynamic Package Resolution
def test_dynamic_package_resolution():
    # Test on an already installed module
    ok = auto_environment_installer.dynamically_resolve_package("pytest")
    assert ok is True


# 5. Conversational Environment Directives
def test_conversational_environment_directives():
    res = conversational_agent.handle_natural_conversation("check environment readiness")
    assert res is not None
    assert res["type"] == "ENVIRONMENT_PROVISIONING_REPORT"
    assert "P.H.A.S.S UNIVERSAL ENVIRONMENT READINESS REPORT" in res["speech_text"]
