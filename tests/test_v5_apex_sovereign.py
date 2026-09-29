"""
Unit & Integration Tests for P.H.A.S.S Apex Sovereign v5.0 Platform:
Agent Colony, Vector Vault Memory, Web Browser Agent, Self-Healing Debugger, Hybrid Fusion Router, and Full-Duplex Voice Stream.
"""

import pytest
from core.version import VERSION, VERSION_CODENAME
from agents.agent_colony import agent_colony, AgentRole
from memory.vector_vault import vector_vault
from tools.web_browser_agent import web_browser_agent
from learning.self_healer import self_healer
from neural.hybrid_fusion import hybrid_fusion_router
from voice.full_duplex_stream import full_duplex_streamer
from nlp.conversational_agent import conversational_agent


# 1. Version 5.0 Platform Metadata
def test_v5_version_metadata():
    assert VERSION in ("5.0.0", "6.0.0", "7.0.0", "8.0.0")
    assert any(k in VERSION_CODENAME for k in ("Apex Sovereign", "Supreme Sovereign", "Zenith Omnipresence", "Apex Nexus Singularity"))


# 2. Multi-Agent Swarm Colony
def test_agent_colony_orchestrator():
    mission = agent_colony.spawn_colony_mission("Build High-Frequency Trading Microservice")

    assert mission.mission_id.startswith("colony_mission_")
    assert mission.agents_deployed_count == 5
    assert len(mission.sub_results) == 5
    assert "Converged" in mission.consolidated_synthesis or "converged" in mission.consolidated_synthesis.lower()

    # Formatted report
    txt = agent_colony.format_mission_report_text(mission)
    assert "SWARM COLONY MISSION REPORT" in txt
    assert "SOFTWARE_ARCHITECT" in txt
    assert "CYBER_SECURITY_AUDITOR" in txt


# 3. Infinite Vector Memory & Semantic Vault
def test_vector_vault_memory():
    doc1 = vector_vault.store_memory("P.H.A.S.S is a physical 6-DOF spherical robot with LiDAR and continuous kinematics.")
    doc2 = vector_vault.store_memory("Quantum entanglement creates Bell states for teleportation.")
    doc3 = vector_vault.store_memory("Python asyncio enables non-blocking event loops and coroutines.")

    assert len(vector_vault.documents) >= 3

    # Semantic search
    results = vector_vault.search_semantic_memory("robot kinematics and physics", top_k=2)
    assert len(results) >= 1
    assert results[0].similarity_score > 0.0


# 4. Autonomous Headless Web Browser Agent
def test_web_browser_agent():
    page = web_browser_agent.browse_url("https://python.org")

    assert page.status_code == 200
    assert page.links_extracted_count >= 1
    assert len(page.text_content_preview) > 10

    txt = web_browser_agent.format_browse_report_text(page)
    assert "WEB BROWSER EXTRACTION" in txt


# 5. Metacognitive Self-Healing & Automatic Code Debugger
def test_metacognitive_self_healer():
    buggy_code = "divisor = 0\nresult = 500 / divisor"
    rep = self_healer.diagnose_and_heal_code(buggy_code)

    assert rep.bug_id.startswith("heal_event_")
    assert rep.error_type == "ZeroDivisionError"
    assert rep.patch_verified_clean is True
    assert "= 1.0" in rep.patched_code or "/ 1.0" in rep.patched_code

    txt = self_healer.format_healing_report_text(rep)
    assert "SELF-HEALING & DEBUGGING REPORT" in txt


# 6. Hybrid Local-Cloud Multi-LLM Fusion Router
def test_hybrid_llm_router():
    # Simple local query
    dec_local = hybrid_fusion_router.evaluate_and_route("open notepad and set volume to 50")
    assert dec_local.selected_engine == "LOCAL_LORA_NEURAL"
    assert dec_local.latency_est_ms < 20.0

    # Complex quantum query
    dec_cloud = hybrid_fusion_router.evaluate_and_route("Design a theoretical physics quantum algorithm with advanced multi-step macroeconomics")
    assert dec_cloud.selected_engine == "HYBRID_FRONTIER_CLOUD"
    assert dec_cloud.complexity_score >= 0.70


# 7. Full-Duplex Real-Time Voice Streaming
def test_full_duplex_voice_streaming():
    # Normal streaming
    ev_norm = full_duplex_streamer.stream_speech_full_duplex("P.H.A.S.S systems nominal.")
    assert ev_norm.interruption_triggered is False

    # Barge-in interruption
    ev_int = full_duplex_streamer.stream_speech_full_duplex("Long speech stream...", interruption_probe="Wait P.H.A.S.S stop")
    assert ev_int.interruption_triggered is True
    assert ev_int.event_type == "BARGE_IN_INTERRUPTION"


# 8. Conversational Directives for Version 5.0
def test_conversational_v5_directives():
    # A. Colony Swarm Mission
    res_swarm = conversational_agent.handle_natural_conversation("spawn agent colony for autonomous drone swarm navigation")
    assert res_swarm is not None
    assert res_swarm["type"] == "SWARM_COLONY_MISSION"

    # B. Vector Vault Memory Search
    res_vec = conversational_agent.handle_natural_conversation("search vector memory for robotics kinematics")
    assert res_vec is not None
    assert res_vec["type"] == "VECTOR_MEMORY_SEARCH"

    # C. Browser Agent
    res_brow = conversational_agent.handle_natural_conversation("browse web for https://docs.python.org")
    assert res_brow is not None
    assert res_brow["type"] == "WEB_BROWSER_EXTRACTION"

    # D. Metacognitive Self-Healing
    res_heal = conversational_agent.handle_natural_conversation("self heal code x = 100 / 0")
    assert res_heal is not None
    assert res_heal["type"] == "METACOGNITIVE_SELF_HEALING"
