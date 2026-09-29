"""
Unit & Integration Tests for P.H.A.S.S Autonomic Error Recovery Circuit.
Tests:
1. test_error_capture: Log watcher, error classification, and Levenshtein similarity matching.
2. test_fix_generation: Cognitive/heuristic fix synthesis, NameError resolution, and safety valve gating.
3. test_sandbox_validation: Sandbox isolation, AST/py_compile verification, failure rejection.
4. test_rollback_recovery: Pre-fix .bak snapshots, hot deployment, 60s rollback recovery, and immunity metrics.
5. test_e2e_self_healing_acid_test: Complete closed-loop repair of missing import re.
6. test_proactive_alert_and_autopilot_audit: Proactive monitor interruption and weekly backup/error compaction.
"""

import os
import shutil
import time
from pathlib import Path
import pytest

from core.error_analyzer import ErrorAnalyzer, AnalyzedError, levenshtein_distance, similarity_ratio
from core.fix_generator import FixGenerator, GeneratedFix
from core.fix_validator import SandboxValidator, ValidationResult
from core.rollback_manager import RollbackManager, DeploymentResult
from core.autonomic_circuit import AutonomicCircuit, HealResult
from core.proactive_monitor import ProactiveMonitor
from core.autopilot_mode import AutopilotMode


@pytest.fixture
def temp_workspace(tmp_path):
    """Creates an isolated temporary test workspace with necessary directory structure."""
    ws = tmp_path / "orvix_test_ws"
    ws.mkdir()
    checkpoints = ws / "checkpoints"
    checkpoints.mkdir()
    backups = checkpoints / "backups"
    backups.mkdir()
    sandbox = ws / "sandbox"
    sandbox.mkdir()

    # Seed known errors
    known_errors_file = checkpoints / "known_errors.json"
    known_errors_content = """{
      "version": "1.0",
      "known_errors": [
        {
          "pattern": "name 're' is not defined",
          "error_type": "NameError",
          "category": "VARIABLE_OR_ATTRIBUTE_FAULT",
          "fix_strategy": "ADD_IMPORT",
          "fix_code": "import re\\n",
          "confidence": 0.98,
          "description": "Add missing re module import at top of file"
        },
        {
          "pattern": "No module named 'serial'",
          "error_type": "ModuleNotFoundError",
          "category": "IMPORT_MODULE_FAULT",
          "fix_strategy": "INSTALL_PACKAGE",
          "fix_code": "pip install pyserial",
          "confidence": 0.95,
          "description": "Install missing serial package"
        }
      ]
    }"""
    known_errors_file.write_text(known_errors_content, encoding="utf-8")

    yield ws


def test_error_capture(temp_workspace):
    """Verifies ErrorAnalyzer parses, categorizes, and matches errors using fuzzy Levenshtein distance."""
    analyzer = ErrorAnalyzer(
        known_errors_file=temp_workspace / "checkpoints" / "known_errors.json",
        execution_log_file=temp_workspace / "checkpoints" / "execution_log.json",
    )

    # 1. Test Levenshtein and similarity ratio
    assert levenshtein_distance("kitten", "sitting") == 3
    assert similarity_ratio("NameError: name 're' is not defined", "NameError: name 're' is not defined") == 1.0
    assert similarity_ratio("NameError: name 're' is not defined", "name 're' is not defined") > 0.6

    # 2. Test Error Classification
    analyzed = analyzer.analyze_error(
        error_type="NameError",
        error_msg="name 're' is not defined",
        file_path="tools/web_search.py",
        line_number=14,
        code_context="return re.sub(r'\\s+', ' ', query)",
    )

    assert analyzed.error_type == "NameError"
    assert analyzed.category == "VARIABLE_OR_ATTRIBUTE_FAULT"
    assert analyzed.file_path == "tools/web_search.py"
    assert analyzed.line_number == 14
    assert analyzed.cached_fix is not None
    assert analyzed.similarity_score >= 0.85
    assert analyzed.cached_fix["fix_strategy"] == "ADD_IMPORT"

    # 3. Test Log String parsing
    log_text = "ERROR: Traceback (most recent call last):\n  File \"core/voice.py\", line 42, in speak\nModuleNotFoundError: No module named 'serial'"
    analyzed_log = analyzer.analyze_log_entry(log_text)
    assert analyzed_log.error_type == "ModuleNotFoundError"
    assert analyzed_log.category == "IMPORT_MODULE_FAULT"
    assert analyzed_log.cached_fix is not None
    assert analyzed_log.similarity_score >= 0.85


def test_fix_generation(temp_workspace):
    """Verifies FixGenerator synthesizes repairs and strictly enforces the 70% confidence safety valve."""
    analyzer = ErrorAnalyzer(known_errors_file=temp_workspace / "checkpoints" / "known_errors.json")
    generator = FixGenerator()

    # Create dummy target file
    test_file = temp_workspace / "target_tool.py"
    test_file.write_text('"""Module docstring."""\n\ndef run():\n    return re.sub(r"\\s+", " ", "hello")\n', encoding="utf-8")

    analyzed = analyzer.analyze_error(
        error_type="NameError",
        error_msg="name 're' is not defined",
        file_path=str(test_file),
        line_number=4,
    )

    fix = generator.generate_fix(analyzed)

    assert isinstance(fix, GeneratedFix)
    assert fix.confidence >= 0.70
    assert fix.confidence >= 0.90
    assert fix.status == "READY_FOR_SANDBOX"
    assert not fix.escalate_to_user
    assert "import re" in fix.repaired_code
    assert '"""Module docstring."""' in fix.repaired_code

    # Test Safety Valve: Unknown error with low confidence
    unknown_error = AnalyzedError(
        error_type="ComplexQuantumError",
        category="SYSTEMIC_RUNTIME_FAULT",
        error_msg="Unknown matrix singularity in kernel",
        file_path=str(test_file),
    )
    low_conf_fix = generator.generate_fix(unknown_error)
    assert low_conf_fix.confidence < 0.70
    assert low_conf_fix.escalate_to_user is True
    assert low_conf_fix.status == "NEEDS_USER_REVIEW"


def test_sandbox_validation(temp_workspace):
    """Verifies SandboxValidator tests fixes in isolation and rejects corrupt syntax."""
    sandbox_dir = temp_workspace / "sandbox"
    validator = SandboxValidator(sandbox_dir=sandbox_dir)

    target_file = temp_workspace / "calculator.py"
    target_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    # 1. Valid Fix Passes Validation
    valid_fix = GeneratedFix(
        target_file=str(target_file),
        target_line=2,
        error_type="NameError",
        error_msg="missing import",
        fix_type="REPLACE",
        repaired_code="import math\n\ndef add(a, b):\n    return a + b\n",
        original_code=target_file.read_text(encoding="utf-8"),
        confidence=0.95,
        escalate_to_user=False,
        status="READY_FOR_SANDBOX",
        explanation="Added math import",
    )

    res_valid = validator.validate_fix(valid_fix, run_tests=False)
    assert res_valid.passed is True
    assert res_valid.syntax_ok is True
    assert res_valid.sandbox_file is not None
    assert Path(res_valid.sandbox_file).exists()
    # Ensure live file wasn't touched by sandbox validation
    assert "import math" not in target_file.read_text(encoding="utf-8")

    # 2. Corrupt / Broken Syntax Fails Validation and live file stays untouched
    broken_fix = GeneratedFix(
        target_file=str(target_file),
        target_line=2,
        error_type="SyntaxError",
        error_msg="invalid syntax",
        fix_type="REPLACE",
        repaired_code="def broken_syntax(:\n    return\n",
        original_code=target_file.read_text(encoding="utf-8"),
        confidence=0.85,
        escalate_to_user=False,
        status="READY_FOR_SANDBOX",
        explanation="Attempted broken fix",
    )

    res_broken = validator.validate_fix(broken_fix, run_tests=False)
    assert res_broken.passed is False
    assert res_broken.syntax_ok is False
    assert "Syntax check failed" in res_broken.error_message
    # Live file is still pristine
    assert "def add(a, b):" in target_file.read_text(encoding="utf-8")


def test_rollback_recovery(temp_workspace):
    """Verifies RollbackManager creates pre-fix .bak snapshots, deploys, and performs 60s rollbacks."""
    backups_dir = temp_workspace / "checkpoints" / "backups"
    metrics_file = temp_workspace / "checkpoints" / "immunity_metrics.json"
    manager = RollbackManager(backup_dir=backups_dir, metrics_file=metrics_file)

    target_file = temp_workspace / "service_worker.py"
    original_content = "# Version 1.0 Live Code\ndef work():\n    return 'original'\n"
    target_file.write_text(original_content, encoding="utf-8")

    # 1. Pre-fix backup
    bak_path = manager.backup_file(target_file)
    assert bak_path.exists()
    assert bak_path.read_text(encoding="utf-8") == original_content

    # 2. Hot Deployment
    hotfix = GeneratedFix(
        target_file=str(target_file),
        target_line=2,
        error_type="NameError",
        error_msg="fixed worker",
        fix_type="HOTFIX",
        repaired_code="# Version 1.1 Hotfixed Code\ndef work():\n    return 'hotfixed'\n",
        original_code=original_content,
        confidence=0.92,
        escalate_to_user=False,
        status="READY_FOR_SANDBOX",
        explanation="Patched worker function",
    )

    dep_res = manager.deploy_fix(hotfix, restart_service_if_needed=False)
    assert dep_res.success is True
    assert target_file.read_text(encoding="utf-8") == hotfix.repaired_code

    # Metrics updated
    metrics = manager.get_metrics()
    assert metrics["errors_fixed_today"] >= 1

    # 3. Simulate Crash Within 60s -> Immediate Rollback
    rollback_ok = manager.trigger_rollback(target_file, reason="Crash in work() function")
    assert rollback_ok is True
    assert target_file.read_text(encoding="utf-8") == original_content

    # Metrics updated for rollback
    metrics_after = manager.get_metrics()
    assert metrics_after["rollbacks"] >= 1


def test_e2e_self_healing_acid_test(temp_workspace):
    """
    End-to-End Acid Test:
    Simulates removing 'import re', catching NameError, and autonomously repairing the module.
    """
    backups_dir = temp_workspace / "checkpoints" / "backups"
    metrics_file = temp_workspace / "checkpoints" / "immunity_metrics.json"
    known_errors_file = temp_workspace / "checkpoints" / "known_errors.json"
    sandbox_dir = temp_workspace / "sandbox"

    circuit = AutonomicCircuit.get_instance()
    # Configure custom components for isolated test workspace
    circuit.error_analyzer = ErrorAnalyzer(known_errors_file=known_errors_file)
    circuit.sandbox_validator = SandboxValidator(sandbox_dir=sandbox_dir)
    circuit.rollback_manager = RollbackManager(backup_dir=backups_dir, metrics_file=metrics_file)

    # Broken module missing import re
    search_file = temp_workspace / "web_search.py"
    broken_code = '"""Search Tool."""\n\ndef sanitize(q):\n    return re.sub(r"\\s+", " ", q)\n'
    search_file.write_text(broken_code, encoding="utf-8")

    # Heal the missing import
    heal_result = circuit.heal_runtime_error(
        error_or_text="NameError: name 're' is not defined",
        file_path=str(search_file),
        line_number=4,
        run_tests=False,
    )

    assert heal_result.success is True
    assert heal_result.deployment_result.success is True
    repaired_file_content = search_file.read_text(encoding="utf-8")
    assert "import re" in repaired_file_content
    assert "def sanitize(q):" in repaired_file_content


def test_proactive_alert_and_autopilot_audit(temp_workspace):
    """Verifies proactive interrupt emission and weekly backup retention & compaction."""
    # 1. Proactive Alert
    monitor = ProactiveMonitor.get_instance()
    alert_msg = monitor.alert_autonomic_fix("web_search.py")
    assert "Sir, I detected an error in my own web_search.py module" in alert_msg
    assert "testing it in the sandbox" in alert_msg

    # 2. Autopilot Weekly Audit
    backups_dir = temp_workspace / "checkpoints" / "backups"
    metrics_file = temp_workspace / "checkpoints" / "immunity_metrics.json"
    rollback_mgr = RollbackManager(backup_dir=backups_dir, metrics_file=metrics_file)

    # Create dummy old backup (8 days old)
    old_bak = backups_dir / "old_module.py_20260101_000000.bak"
    old_bak.write_text("# old backup", encoding="utf-8")
    old_time = time.time() - (8 * 86400)
    os.utime(str(old_bak), (old_time, old_time))

    purged = rollback_mgr.cleanup_old_backups(max_age_days=7)
    assert purged == 1
    assert not old_bak.exists()

    # 3. Autopilot maintenance event
    autopilot = AutopilotMode.get_instance()
    audit_summary = autopilot.run_weekly_error_audit()
    assert "purged_backups" in audit_summary
    assert "compacted_errors" in audit_summary
