"""
Multi-Agent Orchestrator for P.H.A.S.S Sphere & Llama Assistant.
Enables the primary AI brain to spawn, coordinate, and aggregate results from
specialized subagents (File Manager, Web Research, Code Synthesis, Data Analyst,
System Monitor) with parallel thread execution.
"""

from __future__ import annotations
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("phass.core.orchestrator")


@dataclass
class SubagentSpec:
    role: str
    name: str
    description: str
    system_prompt: str
    tools: List[str]
    max_steps: int = 4


@dataclass
class SubagentResult:
    subagent_id: str
    role: str
    task: str
    status: str  # "SUCCESS", "FAILED", "PARTIAL"
    response: str
    tool_calls_count: int = 0
    duration_seconds: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subagent_id": self.subagent_id,
            "role": self.role,
            "task": self.task,
            "status": self.status,
            "response": self.response,
            "tool_calls_count": self.tool_calls_count,
            "duration_seconds": self.duration_seconds,
            "data": self.data,
        }


class MultiAgentOrchestrator:
    """
    Coordinates specialized subagents, executing sub-tasks either sequentially
    or concurrently across threads, and synthesizing consolidated executive reports.
    """

    def __init__(self):
        self.subagents: Dict[str, SubagentSpec] = {}
        self.active_tasks: Dict[str, SubagentResult] = {}
        self._init_default_subagents()

    def _init_default_subagents(self):
        self.register_subagent(
            SubagentSpec(
                role="file_manager",
                name="File Manager Subagent",
                description="Specialized in file organization, duplicate finding, directory cleanups, and safe deletion.",
                system_prompt="You are the P.H.A.S.S File Management Specialist. Focus on organizing, indexing, and validating file operations safely.",
                tools=["file_deleter", "analyze_disk_space", "find_duplicate_files", "smart_file_organizer", "file_ops"],
            )
        )
        self.register_subagent(
            SubagentSpec(
                role="web_research",
                name="Web Research Subagent",
                description="Specialized in web scraping, page content extraction, news aggregation, and online queries.",
                system_prompt="You are the P.H.A.S.S Web Researcher. Extract precise factual data, parse web content, and summarize findings.",
                tools=["web_scraper", "web_search", "browser_controller", "rss_reader", "download_file"],
            )
        )
        self.register_subagent(
            SubagentSpec(
                role="code_synthesis",
                name="Code Synthesis Subagent",
                description="Specialized in code generation, AST analysis, refactoring, unit tests, and debugging.",
                system_prompt="You are the P.H.A.S.S Senior Software Engineer. Produce production-grade, bug-free, verified Python/shell code.",
                tools=["code_generator", "code_analyzer", "git_manager", "compiler_runner", "instant_code_solver"],
            )
        )
        self.register_subagent(
            SubagentSpec(
                role="data_analyst",
                name="Data Analyst Subagent",
                description="Specialized in numerical computing, statistical summaries, spreadsheet data, and text sentiment.",
                system_prompt="You are the P.H.A.S.S Data Analyst. Compute high-precision metrics, generate structured datasets, and extract insights.",
                tools=["advanced_calculator", "csv_excel_master", "database_connector", "sentiment_analyzer", "text_summarizer"],
            )
        )
        self.register_subagent(
            SubagentSpec(
                role="system_monitor",
                name="System Monitor Subagent",
                description="Specialized in OS performance monitoring, process inspection, network telemetry, and system diagnostics.",
                system_prompt="You are the P.H.A.S.S Systems Administrator. Inspect system resources, detect bottlenecks, and report health status.",
                tools=["system_diagnostics", "performance_monitor", "process_hunter", "network_analyzer", "error_log_analyzer"],
            )
        )

    def register_subagent(self, spec: SubagentSpec):
        """Registers or updates a subagent role specification."""
        self.subagents[spec.role.lower()] = spec
        logger.info(f"Registered subagent role: '{spec.role}' ({spec.name})")

    def list_subagents(self) -> List[Dict[str, Any]]:
        """Returns catalog of registered subagents."""
        return [
            {
                "role": s.role,
                "name": s.name,
                "description": s.description,
                "tools": s.tools,
                "max_steps": s.max_steps,
            }
            for s in self.subagents.values()
        ]

    def dispatch_task(
        self,
        role: str,
        task: str,
        context: Optional[str] = None,
        custom_tools: Optional[List[str]] = None,
    ) -> SubagentResult:
        """
        Dispatches a single directive to a specific subagent role.
        Executes using the primary cognitive brain with role-specialized scoping.
        """
        start_t = time.time()
        subagent_id = f"subagent-{role[:4]}-{uuid.uuid4().hex[:6]}"
        spec = self.subagents.get(role.lower())

        if not spec:
            # Fallback subagent definition
            spec = SubagentSpec(
                role=role,
                name=f"Custom {role.title()} Agent",
                description="Dynamically spawned subagent.",
                system_prompt=f"You are a specialized agent focusing on {role}.",
                tools=custom_tools or [],
            )

        logger.info(f"Dispatching task to '{spec.name}' [{subagent_id}]: {task}")

        try:
            # Execute through LlamaToolAgent with role context
            from core.llama_tool_agent import llama_tool_agent
            if spec.role in ("researcher", "web_research"):
                scoped_prompt = f"web research {task}"
            elif spec.role in ("coder", "software_engineer"):
                scoped_prompt = f"code {task}"
            else:
                scoped_prompt = (
                    f"[SUBAGENT ROLE: {spec.name}]\n"
                    f"Assigned Task: {task}\n"
                    f"Context: {context or 'None'}\n"
                    f"Available Specialized Tools: {', '.join(spec.tools)}\n"
                    f"Directive: Resolve the task completely and provide a concise factual summary."
                )
            agent_result = llama_tool_agent.run_turn(scoped_prompt)
            duration = round(time.time() - start_t, 3)

            tool_count = sum(1 for s in agent_result.steps_executed if s.action_type == "call_tool")
            res = SubagentResult(
                subagent_id=subagent_id,
                role=spec.role,
                task=task,
                status="SUCCESS" if agent_result.success else "PARTIAL",
                response=agent_result.final_response,
                tool_calls_count=tool_count,
                duration_seconds=duration,
                data={"steps_count": len(agent_result.steps_executed)},
            )
        except Exception as e:
            logger.error(f"Error in subagent {spec.role} execution: {e}")
            duration = round(time.time() - start_t, 3)
            res = SubagentResult(
                subagent_id=subagent_id,
                role=spec.role,
                task=task,
                status="FAILED",
                response=f"Subagent execution failed: {str(e)}",
                duration_seconds=duration,
                data={"error": str(e)},
            )

        self.active_tasks[subagent_id] = res
        return res

    def dispatch_parallel(
        self,
        tasks: List[Dict[str, Any]],
        max_workers: int = 4,
    ) -> List[SubagentResult]:
        """
        Executes a list of subagent tasks concurrently using a thread pool.
        Each task dict contains: {'role': str, 'task': str, 'context': Optional[str]}
        """
        results: List[SubagentResult] = []
        with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks) or 1)) as executor:
            future_to_task = {
                executor.submit(
                    self.dispatch_task,
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
                    task_info = future_to_task[future]
                    results.append(
                        SubagentResult(
                            subagent_id=f"subagent-err-{uuid.uuid4().hex[:4]}",
                            role=task_info.get("role", "unknown"),
                            task=task_info.get("task", ""),
                            status="FAILED",
                            response=f"Subagent thread failed: {e}",
                        )
                    )

        return results

    def aggregate_results(self, results: List[SubagentResult]) -> str:
        """Synthesizes multiple subagent results into a single cohesive executive report."""
        if not results:
            return "No subagent tasks were executed."

        total_tools = sum(r.tool_calls_count for r in results)
        total_time = sum(r.duration_seconds for r in results)
        successful = sum(1 for r in results if r.status == "SUCCESS")

        lines = [
            f"=== MULTI-AGENT SYNTHESIS REPORT ===",
            f"• Tasks Completed: {successful}/{len(results)}",
            f"• Cumulative Execution Time: {total_time:.2f}s",
            f"• Tools Invoked across Fleet: {total_tools}\n",
        ]

        for idx, r in enumerate(results, 1):
            status_symbol = "✓" if r.status == "SUCCESS" else "✗"
            lines.append(f"[{status_symbol}] Subagent {idx} ({r.role.upper()} — {r.subagent_id}):")
            lines.append(f"    Directive: {r.task}")
            lines.append(f"    Report: {r.response.strip()}\n")

        return "\n".join(lines)


# Global Singleton
multi_agent_orchestrator = MultiAgentOrchestrator()
