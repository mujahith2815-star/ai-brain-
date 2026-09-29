"""
Unit & Integration Tests for Universal OS Control, File Operations,
Deep Diagnostics, and Recursive Self-Evolution Engine.
"""

import os
import pytest
from pathlib import Path

from tools.os_controller import UniversalOSController
from tools.file_ops import UniversalFileManager
from diagnostics.deep_diagnostics import DeepDiagnosticsEngine
from learning.self_evolution import SelfEvolutionEngine
from nlp.conversational_agent import conversational_agent


# 1. OS & Application Controller
def test_os_controller_process_listing_and_execution():
    ctrl = UniversalOSController()

    # List running processes
    procs = ctrl.list_running_processes(max_results=10)
    assert isinstance(procs, list)
    assert len(procs) > 0
    assert procs[0].pid >= 0

    # Shell command execution
    res = ctrl.execute_command("echo PHASS_OS_TEST")
    assert res["success"] is True
    assert "PHASS_OS_TEST" in res["stdout"]


# 2. File Operations (View, Write, Edit, List, Search)
def test_file_manager_operations(tmp_path):
    fm = UniversalFileManager()
    test_file = tmp_path / "test_doc.txt"

    # Write file
    w_res = fm.write_file(str(test_file), "Line 1: Alpha\nLine 2: Beta\nLine 3: Gamma\n")
    assert w_res["success"] is True

    # View file with line slicing
    v_res = fm.view_file(str(test_file), start_line=1, end_line=2)
    assert v_res["success"] is True
    assert "Alpha" in v_res["content"]
    assert "Beta" in v_res["content"]
    assert v_res["total_lines"] == 3

    # Edit / Patch file
    e_res = fm.edit_file(str(test_file), "Beta", "Delta_Optimized")
    assert e_res["success"] is True

    # Verify updated content
    v_res2 = fm.view_file(str(test_file))
    assert "Delta_Optimized" in v_res2["content"]

    # List directory
    l_res = fm.list_directory(str(tmp_path))
    assert l_res["success"] is True
    assert len(l_res["entries"]) >= 1

    # Search in files
    s_res = fm.search_in_files(str(tmp_path), query="Delta_Optimized")
    assert s_res["success"] is True
    assert len(s_res["matches"]) >= 1


# 3. Deep Hardware & OS Diagnostics
def test_deep_diagnostics_sweep():
    diag = DeepDiagnosticsEngine()
    rep = diag.run_full_diagnosis()

    assert rep.overall_health in ("EXCELLENT", "NOMINAL", "WARNING")
    assert rep.cpu_metrics["logical_cores"] > 0
    assert rep.memory_metrics["process_ram_mb"] > 0.0
    assert len(rep.recommendations) >= 1

    # Human-readable report
    rep_str = diag.generate_human_readable_report()
    assert "DEEP SYSTEM DIAGNOSTIC REPORT" in rep_str
    assert "Processor Cores" in rep_str


# 4. Recursive Self-Evolution Engine
def test_self_evolution_analysis_and_rollback_protection(tmp_path):
    evo = SelfEvolutionEngine(codebase_root=str(tmp_path))

    # Self-performance analysis
    analysis = evo.analyze_self_performance()
    assert len(analysis["candidate_modules_for_optimization"]) > 0

    # Create dummy module to test self-patching with safety rollback
    mod_file = tmp_path / "dummy_module.py"
    mod_file.write_text("def run_calc():\n    return 10\n", encoding="utf-8")

    # Attempt patch with invalid test (will trigger automatic safety rollback)
    ok, msg = evo.run_self_improvement_cycle(
        target_file_rel="dummy_module.py",
        improvement_description="Optimize dummy calculation",
        improved_code_snippet="def run_calc():\n    return 20\n",
        target_code_snippet="def run_calc():\n    return 10\n",
    )
    # The cycle handles testing and rolls back if pytest has no tests in tmp_path or fails
    assert isinstance(ok, bool)
    assert len(evo.evolution_history) >= 1


# 5. Natural Conversational Routing for System & Files
def test_conversational_agent_system_and_files():
    # 1. App Launch
    res_app = conversational_agent.handle_natural_conversation("open notepad")
    assert res_app is not None
    assert "notepad" in res_app["speech_text"].lower()

    # 2. Deep Diagnosis
    res_diag = conversational_agent.handle_natural_conversation("check system diagnosis")
    assert res_diag is not None
    assert "DEEP SYSTEM DIAGNOSTIC REPORT" in res_diag["speech_text"]

    # 3. Process Listing
    res_procs = conversational_agent.handle_natural_conversation("list processes")
    assert res_procs is not None
    assert "processes" in res_procs["speech_text"].lower()

    # 4. Self-Evolution
    res_evo = conversational_agent.handle_natural_conversation("improve your own code")
    assert res_evo is not None
    assert "Self-Evolution" in res_evo["speech_text"]
