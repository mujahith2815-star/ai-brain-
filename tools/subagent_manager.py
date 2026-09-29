"""
Subagent Manager Tool Module for P.H.A.S.S Sphere & Llama Assistant.
Provides operational tool wrappers for spawning subagents, coordinating
parallel fleet tasks, tracking status, and aggregating reports.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from core.multi_agent_orchestrator import multi_agent_orchestrator, SubagentSpec

logger = logging.getLogger("phass.tools.subagent_manager")


def spawn_subagent(
    role: str,
    task: str,
    custom_tools: Optional[List[str]] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Spawns a specialized subagent to execute a focused directive.
    Available roles: 'file_manager', 'web_research', 'code_synthesis', 'data_analyst', 'system_monitor'.
    """
    result = multi_agent_orchestrator.dispatch_task(
        role=role,
        task=task,
        context=context,
        custom_tools=custom_tools,
    )
    return {
        "status": result.status,
        "subagent_id": result.subagent_id,
        "role": result.role,
        "task": result.task,
        "response": result.response,
        "duration_seconds": result.duration_seconds,
        "tool_calls_count": result.tool_calls_count,
    }


def list_subagents() -> Dict[str, Any]:
    """Lists all available subagent roles and their specialized capabilities."""
    agents = multi_agent_orchestrator.list_subagents()
    return {
        "status": "SUCCESS",
        "subagent_count": len(agents),
        "available_subagents": agents,
    }


def get_subagent_status(subagent_id: str) -> Dict[str, Any]:
    """Queries the execution record and result of a specific subagent."""
    res = multi_agent_orchestrator.active_tasks.get(subagent_id)
    if not res:
        return {"status": "FAILED", "error": f"Subagent task ID '{subagent_id}' not found."}
    return {"status": "SUCCESS", "subagent": res.to_dict()}


def send_subagent_task(subagent_id: str, task: str) -> Dict[str, Any]:
    """Sends a follow-up directive to a previously spawned subagent role."""
    res = multi_agent_orchestrator.active_tasks.get(subagent_id)
    if not res:
        return {"status": "FAILED", "error": f"Subagent '{subagent_id}' not found."}

    return spawn_subagent(role=res.role, task=task)


def orchestrate_parallel_subagents(
    plan: List[Dict[str, Any]],
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    Executes a multi-task orchestration plan concurrently using parallel subagents.
    plan is a list of dicts: [{'role': 'web_research', 'task': '...'}, {'role': 'data_analyst', 'task': '...'}]
    """
    if not plan or not isinstance(plan, list):
        return {"status": "FAILED", "error": "Plan must be a non-empty list of subagent tasks."}

    results = multi_agent_orchestrator.dispatch_parallel(plan, max_workers=max_workers)
    aggregated_report = multi_agent_orchestrator.aggregate_results(results)

    return {
        "status": "SUCCESS",
        "tasks_executed": len(results),
        "subagent_results": [r.to_dict() for r in results],
        "aggregated_summary": aggregated_report,
    }


def aggregate_agent_reports(subagent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Collects and synthesizes outputs from recent subagent runs into a single executive briefing."""
    if subagent_ids:
        selected = [multi_agent_orchestrator.active_tasks[sid] for sid in subagent_ids if sid in multi_agent_orchestrator.active_tasks]
    else:
        selected = list(multi_agent_orchestrator.active_tasks.values())[-10:]

    report = multi_agent_orchestrator.aggregate_results(selected)
    return {
        "status": "SUCCESS",
        "reports_aggregated": len(selected),
        "summary": report,
    }
