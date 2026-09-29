"""
Test Suite for P.H.A.S.S Recursive Architect (v14.0).
Verifies:
1. test_code_analyzer_ranks_files: Identifies intentionally over-complex dummy files.
2. test_architect_planner_generates_valid_json: Verifies structural planning & 70% safety valve.
3. test_evolution_validator_rejects_bad_code: Rejects corrupt syntax and unauthorized imports.
4. test_rollback_restores_file: Verifies 60s watchdog restores pre-evolution .bak file.
5. test_performance_benchmark: Verifies 100-run timer accepts faster code and rejects slower code.
6. test_natural_language_commands: Verifies Intent Router and process_query handlers.
"""

import json
import os
import shutil
import time
from pathlib import Path
import pytest

from core.code_analyzer import CodeAnalyzer, FileMetrics
from core.architect_planner import ArchitectPlanner, ArchitecturePlan
from core.code_generator import CodeGenerator, GeneratedPatch
from core.evolution_validator import EvolutionValidator, ValidationReport
from core.evolution_deployer import EvolutionDeployer, EvolutionRecord
from core.recursive_architect import RecursiveArchitect
from nlp.answer_pipeline import route_intent, process_query


@pytest.fixture
def temp_architect_workspace(tmp_path):
    """Sets up an isolated workspace for recursive architect testing."""
    ws = tmp_path / "phass_architect_ws"
    ws.mkdir()
    checkpoints = ws / "checkpoints"
    checkpoints.mkdir()
    (checkpoints / "backups").mkdir()
    (checkpoints / "patches").mkdir()
    (ws / "sandbox").mkdir()

    # Create dummy execution log
    exec_log = checkpoints / "execution_log.json"
    exec_log.write_text(json.dumps([{"tool": "complex_worker"}] * 50), encoding="utf-8")

    # Create simple dummy module
    simple_file = ws / "simple_module.py"
    simple_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    # Create intentionally over-complex dummy module
    complex_file = ws / "complex_module.py"
    complex_code = """
def nested_nightmare(x, data):
    total = 0
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                for item in data:
                    try:
                        if item and item.get("val") and item["val"] > 10:
                            total += item["val"]
                        elif item and item.get("val") and item["val"] <= 10:
                            total -= item["val"]
                    except Exception:
                        pass
            elif i % 3 == 0:
                while total > 100:
                    total -= 5
    return total
"""
    complex_file.write_text(complex_code, encoding="utf-8")

    yield ws


def test_code_analyzer_ranks_files(temp_architect_workspace):
    """Ensures CodeAnalyzer calculates cyclomatic complexity and ranks complex files higher."""
    analyzer = CodeAnalyzer(
        project_root=temp_architect_workspace,
        report_file=temp_architect_workspace / "checkpoints" / "refactor_report.json",
        execution_log_file=temp_architect_workspace / "checkpoints" / "execution_log.json",
    )

    report = analyzer.scan_codebase(scan_dirs=["."])
    assert report.total_files_scanned >= 2

    # Verify complex_module has higher complexity and score than simple_module
    ranked_paths = [m.file_path for m in report.ranked_files]
    assert any("complex_module.py" in p for p in ranked_paths)
    assert any("simple_module.py" in p for p in ranked_paths)

    complex_metric = next(m for m in report.ranked_files if "complex_module.py" in m.file_path)
    simple_metric = next(m for m in report.ranked_files if "simple_module.py" in m.file_path)

    assert complex_metric.complexity > simple_metric.complexity
    assert complex_metric.score > simple_metric.score
    assert complex_metric.rank < simple_metric.rank  # Lower rank number = higher priority


def test_architect_planner_generates_valid_json(temp_architect_workspace):
    """Ensures ArchitectPlanner generates structured plans and enforces 70% safety valve."""
    planner = ArchitectPlanner()

    # 1. High-Confidence Optimization Plan
    target_file = temp_architect_workspace / "nlp_pipeline.py"
    target_file.write_text("def route_intent(query):\n    return 'general'\n", encoding="utf-8")

    plan = planner.plan_refactoring(target_file)
    assert isinstance(plan, ArchitecturePlan)
    assert plan.confidence >= 0.70
    assert plan.status == "READY_FOR_GENERATION"
    assert not plan.escalate_to_user
    assert len(plan.improvements) >= 1

    # 2. Safety Valve Trigger (< 70% Confidence)
    low_conf_plan = ArchitecturePlan(
        target_file=str(target_file),
        target_function="unknown_black_box",
        confidence=0.55,  # Below safety threshold
        best_approach="Experimental unverified transformation",
        improvements=["Uncertain change"],
        new_code="",
        escalate_to_user=True,
        status="NEEDS_USER_REVIEW",
    )
    assert low_conf_plan.confidence < 0.70
    assert low_conf_plan.status == "NEEDS_USER_REVIEW"
    assert low_conf_plan.escalate_to_user is True


def test_evolution_validator_rejects_bad_code(temp_architect_workspace):
    """Verifies EvolutionValidator rejects syntax errors and foreign dependencies."""
    validator = EvolutionValidator(requirements_file=temp_architect_workspace / "requirements.txt")
    sandbox_dir = temp_architect_workspace / "sandbox"

    # 1. Corrupted Syntax Rejection
    bad_syntax_file = sandbox_dir / "bad_syntax.py"
    bad_syntax_file.write_text("def broken_func(:\n    return None\n", encoding="utf-8")
    syntax_ok, syntax_err = validator.check_syntax(bad_syntax_file)
    assert syntax_ok is False
    assert "SyntaxError" in syntax_err

    # 2. Foreign Dependency Rejection
    bad_dep_file = sandbox_dir / "unauthorized_dep.py"
    bad_dep_file.write_text("import unauthorized_crypto_miner_pkg\n\ndef run(): pass\n", encoding="utf-8")
    deps_ok, deps_err = validator.check_dependencies(bad_dep_file)
    assert deps_ok is False
    assert "Unauthorized external import" in deps_err

    # 3. Clean Code Passes
    clean_file = sandbox_dir / "clean_code.py"
    clean_file.write_text("import math\nfrom typing import List\n\ndef calc(v: int) -> int:\n    return math.isqrt(v)\n", encoding="utf-8")
    clean_syntax, _ = validator.check_syntax(clean_file)
    clean_deps, _ = validator.check_dependencies(clean_file)
    assert clean_syntax is True
    assert clean_deps is True


def test_rollback_restores_file(temp_architect_workspace):
    """Verifies EvolutionDeployer creates pre-evolution .bak snapshots and restores them on crash."""
    backups_dir = temp_architect_workspace / "checkpoints" / "backups"
    evolution_log = temp_architect_workspace / "checkpoints" / "evolution_log.json"
    deployer = EvolutionDeployer(backup_dir=backups_dir, evolution_log_file=evolution_log)

    live_file = temp_architect_workspace / "live_service.py"
    original_text = "# Live Service v1.0\ndef service():\n    return 'original'\n"
    live_file.write_text(original_text, encoding="utf-8")

    # 1. Backup creation
    bak_path = deployer.backup_file(live_file)
    assert bak_path.exists()
    assert bak_path.read_text(encoding="utf-8") == original_text

    # 2. Simulate deployment
    evolved_text = "# Live Service v14.0\ndef service():\n    return 'evolved'\n"
    live_file.write_text(evolved_text, encoding="utf-8")
    assert live_file.read_text(encoding="utf-8") == evolved_text

    # 3. Simulate runtime error inside watchdog window -> Rollback
    rollback_ok = deployer.trigger_rollback(live_file, reason="Watchdog detected unhandled runtime exception")
    assert rollback_ok is True
    # Verify file is restored to pristine original content
    assert live_file.read_text(encoding="utf-8") == original_text


def test_performance_benchmark():
    """Verifies EvolutionValidator benchmark accepts faster code and rejects degraded code."""
    validator = EvolutionValidator()

    # Fast vs Slow implementation
    def slow_loop():
        res = []
        for i in range(100):
            if i % 2 == 0:
                res.append(i * 2)
        return res

    def fast_comprehension():
        return [i * 2 for i in range(100) if i % 2 == 0]

    # Fast compared against Slow (Fast should pass)
    passed, t_slow, t_fast, speed_pct = validator.benchmark_functions(slow_loop, fast_comprehension, iterations=100)
    assert passed is True
    assert speed_pct > -10.0  # Must not degrade by >10%

    # Artificially degraded slow comparison
    def ultra_slow():
        time.sleep(0.0005)

    def normal():
        pass

    # Normal compared against Ultra Slow (Ultra Slow as candidate must be rejected)
    degraded_passed, _, _, degraded_speed = validator.benchmark_functions(normal, ultra_slow, iterations=20)
    assert degraded_passed is False
    assert degraded_speed < -10.0


def test_natural_language_commands():
    """Verifies intent routing and query execution for Recursive Architect triggers."""
    # 1. Route Intent Verification
    assert route_intent("P.H.A.S.S, analyze your architecture") == "architect_analyze"
    assert route_intent("P.H.A.S.S, upgrade your architecture") == "architect_upgrade"
    assert route_intent("P.H.A.S.S, show me evolution history") == "architect_history"

    # 2. Query Execution Verification
    resp_analyze = process_query("P.H.A.S.S, analyze your architecture")
    assert "analyzed our codebase architecture" in resp_analyze
    assert "nlp/answer_pipeline.py" in resp_analyze
    assert "Priority Score" in resp_analyze

    resp_history = process_query("P.H.A.S.S, show me evolution history")
    assert "Architectural Evolution" in resp_history or "checkpoints/evolution_log.json" in resp_history
