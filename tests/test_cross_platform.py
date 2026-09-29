"""
Comprehensive Cross-Platform & Advanced Architectural Capabilities Test Suite.
Verifies PlatformAbstraction across Windows and Linux, Multi-Agent Orchestration,
Lifecycle Hook Engine, Task Scheduler, Desktop GUI Automation, Document Generation,
Advanced RAG, Security Audit Ledger, MCP Client, Language Support, and Proactive AI.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Core imports
from core.platform_abstraction import PlatformAbstraction, get_platform
from core.multi_agent_orchestrator import multi_agent_orchestrator, SubagentSpec
from core.hook_engine import hook_engine
from core.scheduler_engine import scheduler_engine
from core.security_audit import security_audit
from core.llama_tool_agent import llama_tool_agent
from tools.registry import tool_registry

# Tool imports
from tools.subagent_manager import spawn_subagent, list_subagents, orchestrate_parallel_subagents, aggregate_agent_reports
from tools.hooks_interceptors import register_interceptor, list_interceptors, toggle_interceptor, audit_interceptor_logs
from tools.scheduler import schedule_task, list_scheduled_tasks, cancel_scheduled_task, trigger_task_now, get_schedule_history
from tools.gui_automation import gui_click, gui_type_text, gui_set_of_mark_grounding, gui_safety_abort
from tools.document_automation import office_word_generator, office_excel_master, office_presentation_maker, pdf_form_filler_and_extractor
from tools.browser_automation import browser_navigate, browser_click_element, browser_fill_form, browser_extract_content
from tools.memory_rag import rag_ingest_documents, rag_query, knowledge_graph_extract, knowledge_graph_query, isolate_memory_store
from tools.security_manager import enterprise_key_manager, secure_credential_vault, file_shredder, query_security_audit_log, request_action_confirmation
from tools.mcp_client import mcp_connect_server, mcp_discover_tools, mcp_invoke_tool, mcp_list_active_connections
from tools.language_support import detect_language, translate_text, get_localized_response, map_multilingual_command
from tools.proactive_agent import proactive_context_prediction, proactive_system_recommendations, proactive_anomaly_detection


# =============================================================================
# 1. PLATFORM ABSTRACTION TESTS
# =============================================================================

def test_platform_detection_and_directories():
    plat = get_platform()
    assert plat.os_type in ("windows", "linux", "darwin")
    assert isinstance(plat.is_windows, bool)
    assert isinstance(plat.is_linux, bool)
    
    # Path methods
    home = plat.get_home_dir()
    assert home.exists()
    assert plat.get_temp_dir().exists()
    
    # Normalization
    norm = plat.normalize_path("~")
    assert norm.exists()


def test_platform_protected_paths():
    plat = get_platform()
    assert plat.is_system_protected_path("C:\\Windows\\System32") is True
    assert plat.is_system_protected_path("/etc/shadow") is True
    assert plat.is_system_protected_path(".git") is True
    assert plat.is_system_protected_path("my_safe_project/data.txt") is False


def test_platform_command_execution():
    plat = get_platform()
    res = plat.execute_command("python -c \"print('cross_platform_ok')\"")
    assert res["status"] == "SUCCESS"
    assert res["exit_code"] == 0
    assert "cross_platform_ok" in res["stdout"]


def test_platform_process_listing_and_system_info():
    plat = get_platform()
    procs = plat.list_processes(limit=10)
    assert len(procs) > 0
    assert "pid" in procs[0]
    assert "name" in procs[0]
    
    info = plat.get_system_info()
    assert "os_name" in info
    assert "cpu_count" in info
    assert info["cpu_count"] >= 1
    assert "disk_free_gb" in info


# =============================================================================
# 2. MULTI-AGENT ORCHESTRATION TESTS
# =============================================================================

def test_subagent_registry_and_catalog():
    agents = list_subagents()
    assert agents["status"] == "SUCCESS"
    assert agents["subagent_count"] >= 5
    roles = [a["role"] for a in agents["available_subagents"]]
    assert "file_manager" in roles
    assert "web_research" in roles
    assert "code_synthesis" in roles
    assert "data_analyst" in roles
    assert "system_monitor" in roles


def test_subagent_dispatch_single():
    res = spawn_subagent(
        role="system_monitor",
        task="Check CPU and memory telemetry",
    )
    assert res["status"] in ("SUCCESS", "PARTIAL")
    assert "subagent_id" in res
    assert res["role"] == "system_monitor"
    assert len(res["response"]) > 0


def test_subagent_parallel_orchestration_and_aggregation():
    plan = [
        {"role": "system_monitor", "task": "Check RAM usage"},
        {"role": "data_analyst", "task": "Evaluate stability metric"},
    ]
    res = orchestrate_parallel_subagents(plan=plan, max_workers=2)
    assert res["status"] == "SUCCESS"
    assert res["tasks_executed"] == 2
    assert "MULTI-AGENT SYNTHESIS REPORT" in res["aggregated_summary"]

    # Aggregated reports tool
    agg = aggregate_agent_reports()
    assert agg["status"] == "SUCCESS"
    assert "MULTI-AGENT SYNTHESIS REPORT" in agg["summary"]


# =============================================================================
# 3. HOOKS & INTERCEPTORS TESTS
# =============================================================================

def test_hooks_registration_and_listing():
    reg = register_interceptor(
        hook_point="before_tool_call",
        hook_name="test_rule_interceptor",
        rule="dangerous_payload",
        action="block",
    )
    assert reg["status"] == "SUCCESS"
    assert reg["hook_name"] == "test_rule_interceptor"

    hooks = list_interceptors()
    assert hooks["status"] == "SUCCESS"
    names = [h["name"] for h in hooks["hooks"]]
    assert "test_rule_interceptor" in names

    # Toggle hook
    tog = toggle_interceptor("test_rule_interceptor", enabled=False)
    assert tog["status"] == "SUCCESS"
    assert tog["enabled"] is False


def test_safety_hook_prevents_system_deletion():
    # Attempt safety check on protected system folder
    allow, mod_params, reason = hook_engine.run_before_tool_call(
        tool_name="file_deleter",
        parameters={"directory": "C:\\Windows\\System32"},
    )
    assert allow is False
    assert "strictly prohibited" in str(reason)

    # Clean up test hook
    hook_engine.unregister_hook("test_rule_interceptor")


# =============================================================================
# 4. TASK SCHEDULER TESTS
# =============================================================================

def test_scheduler_lifecycle():
    task_res = schedule_task(
        task_name="unit_test_diagnostic",
        cron_or_delay="every_1h",
        tool_or_command="system_diagnostics",
    )
    assert task_res["status"] == "SUCCESS"
    task_id = task_res["task_id"]

    tasks_list = list_scheduled_tasks()
    assert tasks_list["status"] == "SUCCESS"
    assert any(t["task_id"] == task_id for t in tasks_list["scheduled_tasks"])

    # Immediate trigger
    trig = trigger_task_now(task_id)
    assert trig["status"] == "SUCCESS"

    # History verification
    hist = get_schedule_history(limit=5)
    assert hist["status"] == "SUCCESS"
    assert len(hist["history"]) > 0

    # Cancel task
    canc = cancel_scheduled_task(task_id)
    assert canc["status"] == "SUCCESS"


# =============================================================================
# 5. ENTERPRISE SECURITY & AUDIT TESTS
# =============================================================================

def test_security_audit_ledger_integrity():
    security_audit.log_event("test_event_1", details={"key": "val1"})
    security_audit.log_event("test_event_2", details={"key": "val2"})

    valid, count, err = security_audit.verify_ledger_integrity()
    assert valid is True
    assert count >= 2
    assert err is None

    audit_query = query_security_audit_log(limit=5)
    assert audit_query["status"] == "SUCCESS"
    assert audit_query["ledger_integrity_verified"] is True


def test_threat_detection_scanner():
    detected, threats = security_audit.scan_threat("SELECT * FROM users WHERE '1'='1' UNION SELECT")
    assert detected is True
    assert any("SQL Injection" in t for t in threats)

    detected_pt, threats_pt = security_audit.scan_threat("../../etc/shadow")
    assert detected_pt is True
    assert any("Path Traversal" in t for t in threats_pt)

    detected_safe, _ = security_audit.scan_threat("Please summarize today's notes.")
    assert detected_safe is False


def test_confirmation_gate_tokens():
    req = request_action_confirmation("reboot_system_server", risk_level="CRITICAL")
    assert req["status"] == "PENDING_CONFIRMATION"
    token = req["confirmation_token"]
    assert token.startswith("CONFIRM-")

    # Validate token
    valid, ctx = security_audit.validate_confirmation_token(token)
    assert valid is True
    assert ctx["description"] == "reboot_system_server"

    # Second validation should fail (consumed token)
    valid2, _ = security_audit.validate_confirmation_token(token)
    assert valid2 is False


def test_file_shredder_safety():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"sensitive operational data")
        temp_path = tf.name

    try:
        # Unconfirmed should return PREVIEW
        preview = file_shredder(temp_path, passes=2, confirmed=False)
        assert preview["status"] == "PREVIEW"
        assert preview["confirmation_required"] is True
        assert os.path.exists(temp_path)

        # Confirmed execution should shred and delete file
        shred = file_shredder(temp_path, passes=2, confirmed=True)
        assert shred["status"] == "SUCCESS"
        assert not os.path.exists(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =============================================================================
# 6. MCP (MODEL CONTEXT PROTOCOL) CLIENT TESTS
# =============================================================================

def test_mcp_client_operations():
    conn = mcp_connect_server("stdio://sample_server", transport="stdio")
    assert conn["status"] == "SUCCESS"
    server_id = conn["server_id"]

    tools = mcp_discover_tools(server_id)
    assert tools["status"] == "SUCCESS"
    assert tools["tool_count"] >= 1

    tool_name = tools["tools"][0]["name"]
    inv = mcp_invoke_tool(server_id, tool_name=tool_name, arguments={"test": True})
    assert inv["status"] == "SUCCESS"
    assert inv["tool_name"] == tool_name

    conns = mcp_list_active_connections()
    assert conns["status"] == "SUCCESS"
    assert conns["active_connections_count"] >= 1


# =============================================================================
# 7. ADVANCED MEMORY & RAG TESTS
# =============================================================================

def test_memory_rag_ingest_and_query():
    # Ingest text chunks
    ing = rag_ingest_documents(
        paths_or_texts=["Quantum mechanics describes physical properties of nature at subatomic scales."],
        collection_name="test_physics",
    )
    assert ing["status"] == "SUCCESS"
    assert ing["new_chunks_ingested"] >= 1

    # Query
    q_res = rag_query("subatomic quantum particles", collection_name="test_physics")
    assert q_res["status"] == "SUCCESS"
    assert q_res["matches_count"] >= 1

    # Knowledge graph
    kg_ext = knowledge_graph_extract("Llama uses GPU memory for high-speed inference.")
    assert kg_ext["status"] == "SUCCESS"
    assert kg_ext["extracted_triplets_count"] >= 1

    kg_q = knowledge_graph_query("Llama")
    assert kg_q["status"] == "SUCCESS"
    assert kg_q["matches_count"] >= 1

    # Memory isolation
    iso = isolate_memory_store("user", action="switch")
    assert iso["status"] == "SUCCESS"
    assert iso["active_scope"] == "user"
    isolate_memory_store("project", action="switch")


# =============================================================================
# 8. DESKTOP GUI & DOCUMENT AUTOMATION TESTS
# =============================================================================

def test_gui_automation_fallbacks():
    clk = gui_click(x=100, y=100)
    assert clk["status"] == "SUCCESS"
    assert clk["coordinates"]["x"] == 100

    typ = gui_type_text("test_input")
    assert typ["status"] == "SUCCESS"

    som = gui_set_of_mark_grounding()
    assert som["status"] == "SUCCESS"
    assert som["marks_detected"] >= 1


def test_office_document_generation():
    with tempfile.TemporaryDirectory() as td:
        word_path = Path(td) / "test.docx"
        excel_path = Path(td) / "test.xlsx"
        ppt_path = Path(td) / "test.pptx"

        w_res = office_word_generator(file_path=str(word_path), title="Test Doc")
        assert w_res["status"] == "SUCCESS"
        assert word_path.exists() or Path(w_res.get("fallback_markdown", "")).exists()

        e_res = office_excel_master(file_path=str(excel_path), data=[{"Col": 1}])
        assert e_res["status"] == "SUCCESS"

        p_res = office_presentation_maker(file_path=str(ppt_path), slides=[{"title": "Intro"}])
        assert p_res["status"] == "SUCCESS"


# =============================================================================
# 9. MULTI-LANGUAGE & PROACTIVE INTELLIGENCE TESTS
# =============================================================================

def test_language_support():
    det = detect_language("Hola como estas por favor limpiar disco")
    assert det["status"] == "SUCCESS"
    assert det["language"] == "es"

    trans = translate_text("hello", target_lang="es")
    assert trans["status"] == "SUCCESS"
    assert trans["translated_text"].lower() == "hola"

    loc = get_localized_response("welcome", lang="es")
    assert loc["status"] == "SUCCESS"
    assert "bienvenido" in loc["localized_text"].lower()

    cmd = map_multilingual_command("limpiar disco")
    assert cmd["matched"] is True
    assert cmd["mapped_command"] == "clean disk"


def test_proactive_agent():
    pred = proactive_context_prediction(recent_queries=["how to clean disk space"])
    assert pred["status"] == "SUCCESS"
    assert pred["predictions_count"] >= 1

    recs = proactive_system_recommendations()
    assert recs["status"] == "SUCCESS"
    assert recs["recommendations_count"] >= 1

    anom = proactive_anomaly_detection()
    assert anom["status"] == "SUCCESS"


# =============================================================================
# 10. LLAMA TOOL AGENT COGNITIVE INTEGRATION TESTS
# =============================================================================

def test_llama_agent_threat_screen_blocks_injection():
    res = llama_tool_agent.run_turn("; rm -rf /")
    assert res.success is False
    assert "Security Alert" in res.final_response
    assert "security_audit_shield" in res.model_used


def test_llama_agent_routes_subagent_directive():
    res = llama_tool_agent.run_turn("spawn subagent file_manager to organize files")
    assert res.success is True
    tool_steps = [s for s in res.steps_executed if s.tool_name == "spawn_subagent"]
    assert len(tool_steps) > 0
    assert tool_steps[0].parameters.get("role") == "file_manager"


def test_registered_tools_catalog_expanded_count():
    tools = tool_registry.list_tools()
    # 130 + 44 new tools = 174+ tools
    assert len(tools) >= 170
    tool_names = [t["name"] for t in tools]
    assert "spawn_subagent" in tool_names
    assert "register_interceptor" in tool_names
    assert "schedule_task" in tool_names
    assert "gui_click" in tool_names
    assert "office_word_generator" in tool_names
    assert "browser_navigate" in tool_names
    assert "rag_query" in tool_names
    assert "enterprise_key_manager" in tool_names
    assert "mcp_connect_server" in tool_names
    assert "detect_language" in tool_names
    assert "proactive_system_recommendations" in tool_names
