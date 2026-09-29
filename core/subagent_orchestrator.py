"""
Subagent Orchestrator Engine for P.H.A.S.S Sphere & Llama Assistant.
Provides project manager capability to spawn specialized subagents,
execute them concurrently, and aggregate outputs into comprehensive reports.
"""

from __future__ import annotations
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.multi_agent_orchestrator import (
    MultiAgentOrchestrator,
    SubagentSpec,
    SubagentResult,
    multi_agent_orchestrator as base_orchestrator,
)

logger = logging.getLogger("phass.core.subagent_orchestrator")


PREBUILT_ROLES = {
    "researcher": {
        "name": "Web Research & Intelligence Subagent",
        "description": "Performs online search, web scraping, content summarization, and fact-checking.",
        "system_prompt": (
            "You are the P.H.A.S.S Lead Researcher. Your job is to search the web, scrape articles, "
            "verify facts, and provide accurate, synthesized research briefs."
        ),
        "tools": ["web_scraper", "web_search", "browser_controller", "rss_reader", "download_file"],
    },
    "coder": {
        "name": "Software Engineering & Architecture Subagent",
        "description": "Writes, reviews, refactors, debugs, and optimizes code across Python, JS, C++, shell, and SQL.",
        "system_prompt": (
            "You are the P.H.A.S.S Senior Software Architect. Produce clean, robust, type-annotated, "
            "production-grade code and debug technical issues with precision."
        ),
        "tools": ["code_generator", "code_analyzer", "git_manager", "compiler_runner", "instant_code_solver"],
    },
    "data_analyst": {
        "name": "Data Analytics & Statistics Subagent",
        "description": "Processes Excel/CSV datasets, computes statistics, creates data visualizations, and analyzes trends.",
        "system_prompt": (
            "You are the P.H.A.S.S Data Scientist. Parse tabular data, compute descriptive and inferential "
            "metrics, identify anomalies, and present actionable statistical insights."
        ),
        "tools": ["advanced_calculator", "csv_excel_master", "database_connector", "sentiment_analyzer", "text_summarizer"],
    },
    "file_manager": {
        "name": "File Organization & Storage Subagent",
        "description": "Organizes directories, detects duplicate files, creates backups, manages archives, and performs safe cleanups.",
        "system_prompt": (
            "You are the P.H.A.S.S File Management Engineer. Safely organize file trees, calculate disk usage, "
            "find redundant files, and ensure zero accidental data loss."
        ),
        "tools": ["file_deleter", "analyze_disk_space", "find_duplicate_files", "smart_file_organizer", "file_ops"],
    },
    "system_monitor": {
        "name": "System Health & Performance Subagent",
        "description": "Monitors CPU, RAM, disk usage, active processes, system logs, and triggers proactive alerts.",
        "system_prompt": (
            "You are the P.H.A.S.S System Administrator. Continuously inspect OS telemetry, track resource limits, "
            "and diagnose system anomalies."
        ),
        "tools": ["system_diagnostics", "performance_monitor", "process_hunter", "network_analyzer", "error_log_analyzer"],
    },
    "writer": {
        "name": "Creative Writing & Documentation Subagent",
        "description": "Drafts emails, business reports, articles, creative stories, technical documentation, and presentations.",
        "system_prompt": (
            "You are the P.H.A.S.S Master Communicator and Writer. Craft eloquent, engaging, clear, and structured "
            "written material tailored to the requested audience."
        ),
        "tools": ["text_summarizer", "docx_creator", "pdf_processor", "story_generator"],
    },
    "translator": {
        "name": "Multi-Lingual Translation & Localization Subagent",
        "description": "Translates documents and dialogue across languages while preserving idioms, tone, and cultural nuance.",
        "system_prompt": (
            "You are the P.H.A.S.S Polyglot Translation Specialist. Translate between multiple languages with "
            "high fidelity to cultural nuance, technical terms, and intended tone."
        ),
        "tools": ["text_summarizer", "language_translator"],
    },
    "security_auditor": {
        "name": "Cybersecurity & Permissions Auditor Subagent",
        "description": "Scans file permissions, audits access logs, detects suspicious activity, and verifies cryptographic integrity.",
        "system_prompt": (
            "You are the P.H.A.S.S Cybersecurity Auditor. Identify vulnerabilities, inspect sensitive files, "
            "audit network ports, and enforce zero-trust security postures."
        ),
        "tools": ["security_audit", "threat_detection", "audit_logger", "firewall_manager"],
    },
}


class SubagentOrchestrator:
    """
    Project Manager subagent orchestration system.
    Maintains registered roles, dispatches single or parallel subagent jobs,
    and aggregates individual findings into a structured master report.
    """

    def __init__(self, base: Optional[MultiAgentOrchestrator] = None):
        self.base = base or base_orchestrator
        self.roles = dict(PREBUILT_ROLES)
        self.active_results: List[SubagentResult] = []
        self._register_prebuilt_roles()

    def _register_prebuilt_roles(self):
        for role_key, meta in self.roles.items():
            spec = SubagentSpec(
                role=role_key,
                name=meta["name"],
                description=meta["description"],
                system_prompt=meta["system_prompt"],
                tools=meta["tools"],
            )
            self.base.register_subagent(spec)

    def get_available_roles(self) -> List[str]:
        """Returns list of all available subagent roles."""
        return list(self.roles.keys())

    def spawn_subagent(
        self,
        role: str,
        task: str,
        context: Optional[str] = None,
        custom_tools: Optional[List[str]] = None,
    ) -> SubagentResult:
        """
        Creates and executes a specialized subagent for the specified role and task.
        """
        norm_role = role.lower().strip()
        alias_map = {
            "web_research": "researcher",
            "research": "researcher",
            "code_synthesis": "coder",
            "code": "coder",
            "programming": "coder",
            "analytics": "data_analyst",
            "analysis": "data_analyst",
            "file": "file_manager",
            "monitor": "system_monitor",
            "admin": "system_monitor",
            "copywriter": "writer",
            "translate": "translator",
            "security": "security_auditor",
            "audit": "security_auditor",
        }
        resolved_role = alias_map.get(norm_role, norm_role)

        result = self.base.dispatch_task(
            role=resolved_role,
            task=task,
            context=context,
            custom_tools=custom_tools,
        )
        self.active_results.append(result)
        return result

    def parallel_execute(
        self,
        tasks: List[Dict[str, Any]],
        max_workers: int = 4,
    ) -> List[SubagentResult]:
        """
        Executes multiple subagents simultaneously across thread workers.
        `tasks` is a list of dicts: [{'role': 'coder', 'task': '...'}, ...]
        """
        results: List[SubagentResult] = []
        with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks) or 1)) as executor:
            future_to_task = {
                executor.submit(
                    self.spawn_subagent,
                    t.get("role", "system_monitor"),
                    t.get("task", ""),
                    t.get("context"),
                    t.get("custom_tools"),
                ): t
                for t in tasks
            }
            for future in as_completed(future_to_task):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    task_meta = future_to_task[future]
                    results.append(
                        SubagentResult(
                            subagent_id=f"subagent-err-{uuid.uuid4().hex[:4]}",
                            role=task_meta.get("role", "unknown"),
                            task=task_meta.get("task", ""),
                            status="FAILED",
                            response=f"Subagent execution failed with error: {e}",
                        )
                    )
        return results

    def aggregate_results(self, results: Optional[List[SubagentResult]] = None) -> str:
        """
        Combines outputs from multiple subagents into a unified, consolidated report.
        """
        target_results = results if results is not None else self.active_results
        if not target_results:
            return "No subagent operations have been executed yet."

        total_tasks = len(target_results)
        successful = sum(1 for r in target_results if r.status == "SUCCESS")
        total_time = sum(r.duration_seconds for r in target_results)

        lines = [
            "============================================================",
            "        P.H.A.S.S FLEET: CONSOLIDATED SUBAGENT REPORT           ",
            "============================================================",
            f"• Subagents Deployed:  {total_tasks}",
            f"• Success Rate:        {successful}/{total_tasks} ({int((successful/max(1, total_tasks))*100)}%)",
            f"• Cumulative Duration: {total_time:.2f}s\n",
        ]

        for i, res in enumerate(target_results, 1):
            status_icon = "🟢" if res.status == "SUCCESS" else "🔴"
            role_title = res.role.upper().replace("_", " ")
            lines.append(f"{status_icon} [{i}] ROLE: {role_title} ({res.subagent_id})")
            lines.append(f"    Directive: {res.task}")
            lines.append(f"    Findings / Output:")
            for sub_line in res.response.strip().splitlines():
                lines.append(f"      {sub_line}")
            lines.append("")

        lines.append("============================================================")
        return "\n".join(lines)


# Global singleton instance
subagent_orchestrator = SubagentOrchestrator()


def spawn_subagent(
    role: str,
    task: str,
    context: Optional[str] = None,
    custom_tools: Optional[List[str]] = None,
) -> SubagentResult:
    return subagent_orchestrator.spawn_subagent(role, task, context, custom_tools)


def parallel_execute(
    tasks: List[Dict[str, Any]],
    max_workers: int = 4,
) -> List[SubagentResult]:
    return subagent_orchestrator.parallel_execute(tasks, max_workers)


def aggregate_results(results: Optional[List[SubagentResult]] = None) -> str:
    return subagent_orchestrator.aggregate_results(results)
