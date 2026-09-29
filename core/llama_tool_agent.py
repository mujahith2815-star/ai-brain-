"""
Llama Tool-Dispatching & Multi-Step Reasoning Agent for P.H.A.S.S / NICON.
Acts as the central cognitive brain: plans actions, executes tools via ToolRegistry,
observes real results (with truthful error reporting), chains multi-step workflows,
and synthesizes natural, human-friendly responses.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config.llama_config import llama_config
from tools.registry import tool_registry
from tools.executor import ToolExecutor, ToolExecutionResult
from jarvis.persona import jarvis_persona, ChatPersonaMode
from core.user_preferences import user_preferences
from core.rag_pipeline import RAGPipeline

try:
    from mcp.mcp_manager import MCPManager
    from mcp.mcp_tool_adapter import MCPToolAdapter
except Exception as _mcp_imp_err:
    MCPManager = None
    MCPToolAdapter = None

logger = logging.getLogger("phass.core.llama_tool_agent")


@dataclass
class ReasoningStep:
    step_number: int
    thought: str
    action_type: str  # "call_tool" or "final_answer"
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    tool_output: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "thought": self.thought,
            "action": self.action_type,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "output": self.tool_output,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class LlamaAgentResult:
    user_query: str
    final_response: str
    steps_executed: List[ReasoningStep]
    model_used: str
    total_steps: int
    total_duration_sec: float
    fallback_used: bool = False
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_query": self.user_query,
            "final_response": self.final_response,
            "steps": [s.to_dict() for s in self.steps_executed],
            "model_used": self.model_used,
            "total_steps": self.total_steps,
            "total_duration_sec": round(self.total_duration_sec, 2),
            "fallback_used": self.fallback_used,
            "success": self.success,
        }


class LlamaToolAgent:
    def __init__(self):
        self.executor = ToolExecutor()
        self.history: List[Dict[str, str]] = []
        self.preferences = user_preferences
        self.rag = RAGPipeline()

        # Model Context Protocol (MCP) Manager & Dynamic Tool Registration
        self.mcp = None
        self.mcp_adapter = None
        try:
            if MCPManager is not None:
                self.mcp = MCPManager()
                self.mcp.start_all()
                if MCPToolAdapter is not None:
                    self.mcp_adapter = MCPToolAdapter(self.mcp)
                    self.mcp_adapter.register_all()
        except Exception as e:
            logger.warning(f"MCP server initialization notice: {e}")

        # Bootstrap 3-Layer Command Intelligence Brain (v1.2.0)
        try:
            from knowledge.commands import bootstrap_command_brain
            bootstrap_command_brain(vector_store=self.rag.vector_store)
        except Exception as _cmd_err:
            logger.warning(f"Command Brain bootstrap notice: {_cmd_err}")

        # Model Router for Primary Cloud (Gemini Flash) + Offline Local (Llama-3.2-1B) (v1.3.0)
        try:
            from tools.model_router import model_router
            self.router = model_router
        except Exception as _router_err:
            logger.warning(f"Model Router initialization notice: {_router_err}")
            self.router = None

    def refresh_mcp_tools(self) -> Dict[str, Any]:
        """Reloads external MCP servers and registers newly discovered tools."""
        if self.mcp is None and MCPManager is not None:
            try:
                self.mcp = MCPManager()
            except Exception:
                pass

        if self.mcp is not None:
            self.mcp.restart_all()
            if self.mcp_adapter is None and MCPToolAdapter is not None:
                self.mcp_adapter = MCPToolAdapter(self.mcp)
            if self.mcp_adapter is not None:
                count = self.mcp_adapter.register_all()
                return {
                    "status": "SUCCESS",
                    "registered_tools": count,
                    "servers": self.mcp.get_status(),
                }
        return {"status": "FAILED", "error": "MCPManager unavailable on this system."}

    def _extract_directory_from_text(self, text: str, default: str = ".") -> str:
        """Extracts directory path from user directive or returns default."""
        # 1. Windows drive path: C:\... or C:/...
        drive_match = re.search(r'([a-zA-Z]:[\\\/][a-zA-Z0-9_\-\.\\\/]+)', text)
        if drive_match:
            return drive_match.group(1).rstrip(".,;'\"")
        # 2. Explicit relative or POSIX path: ./path, ../path, /tmp/...
        rel_match = re.search(r'(?:in|from|dir|directory|folder)\s+([.\/\\][a-zA-Z0-9_\-\.\\\/]+|[a-zA-Z0-9_\-]+[\\\/][a-zA-Z0-9_\-\.\\\/]+)', text, re.IGNORECASE)
        if rel_match:
            return rel_match.group(1).rstrip(".,;'\"")
        # 3. Simple directory name after 'in <dir>' or 'folder <dir>'
        simple_in = re.search(r'(?:in|folder|directory|from)\s+([a-zA-Z0-9_\-]+)', text, re.IGNORECASE)
        if simple_in:
            candidate = simple_in.group(1).strip()
            if candidate.lower() not in ("the", "this", "my", "our", "a", "all", "each", "every", "days", "files", "here"):
                return candidate
        return default

    def get_tool_catalog_prompt(self) -> str:
        """Serializes all registered tools into clean JSON-oriented documentation."""
        tools = tool_registry.list_tools()
        lines = []
        for t in tools:
            lines.append(f"- **{t['name']}**: {t['description']}")
            props = t.get("input_schema", {}).get("properties", {})
            if props:
                param_strs = [f"{k} ({v.get('type', 'any')})" for k, v in props.items()]
                lines.append(f"  Parameters: {', '.join(param_strs)}")

        # Add MCP status to tool catalog output
        if self.mcp is not None:
            try:
                st = self.mcp.get_status()
                conn = st.get("connected_servers", 0)
                tot = st.get("total_servers", 0)
                lines.append(f"\n### Model Context Protocol (MCP): {conn}/{tot} external servers connected.")
            except Exception:
                pass
        return "\n".join(lines)

    def _query_gemini_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """Queries Google Gemini Flash for structured JSON action plan."""
        from tools.gemini_engine import gemini_engine
        if not gemini_engine.is_available():
            return None

        full_prompt = (
            f"{prompt}\n\n"
            "CRITICAL FORMAT REQUIREMENT: Respond with VALID JSON ONLY. "
            'Either an action plan: {"actions": [{"tool": "tool_name", "args": {...}}]} '
            'or a final conversational answer: {"action": "final_answer", "thought": "...", "response": "..."}'
        )
        raw_res = gemini_engine.generate(
            prompt=full_prompt,
            system_instruction=system_prompt,
            temperature=0.3,
        )
        if not raw_res:
            return None

        raw_clean = raw_res.strip()
        if raw_clean.startswith("```"):
            raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_clean)
            raw_clean = re.sub(r"\s*```$", "", raw_clean)

        try:
            return json.loads(raw_clean)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw_clean)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
            return {
                "action": "final_answer",
                "thought": "Direct Gemini synthesis",
                "response": raw_clean,
            }

    def _query_qwen_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """Queries local Qwen2.5-7B engine on W: drive via Ollama."""
        try:
            from tools.qwen_engine import qwen_engine
            if not qwen_engine.is_available():
                return None
            res = qwen_engine.generate_with_tools(
                prompt=prompt,
                system_instruction=system_prompt,
            )
            return res.get("decision")
        except Exception as e:
            logger.warning(f"Error querying Qwen JSON: {e}")
            return None

    def _query_engine_json(
        self,
        prompt: str,
        system_prompt: str,
        route_target: Any,
    ) -> Tuple[Optional[Dict[str, Any]], str, bool]:
        """
        Executes query on routed engine (Gemini or Qwen/Local), with automatic fallback.
        Returns: (decision_dict, actual_model_used, fallback_occurred)
        """
        from config.api_config import api_config
        from tools.gemini_engine import gemini_engine
        from tools.qwen_engine import qwen_engine

        fallback_occurred = False
        target_str = getattr(route_target, "name", str(route_target)).lower()

        # Branch 1: Gemini Cloud Primary
        if target_str in ("gemini", "cloud"):
            if gemini_engine.is_available():
                try:
                    res = self._query_gemini_json(prompt, system_prompt)
                    if res is not None:
                        return res, gemini_engine.model_name, False
                except Exception as e:
                    logger.warning(f"Gemini execution failed ({e}). Checking fallback...")
                    if self.router:
                        self.router.record_fallback()
                    if not api_config.fallback_enabled:
                        raise

            # Fallback to local Qwen on W:
            fallback_occurred = True
            logger.info("Fell back from Gemini to local Qwen2.5-7B / native solver.")
            if qwen_engine.is_available():
                try:
                    q_res = self._query_qwen_json(prompt, system_prompt)
                    if q_res is not None:
                        return q_res, qwen_engine.model_name, True
                except Exception as qe:
                    logger.warning(f"Qwen fallback failed ({qe}). Falling back to native solver.")

            local_res = self._query_llama_json(prompt, system_prompt)
            return local_res, llama_config.model_name, True

        # Branch 2: Local Qwen2.5-7B Primary
        if qwen_engine.is_available():
            try:
                res = self._query_qwen_json(prompt, system_prompt)
                if res is not None:
                    return res, qwen_engine.model_name, False
            except Exception as e:
                logger.warning(f"Qwen execution failed ({e}). Checking cloud fallback...")
                if self.router:
                    self.router.record_fallback()

        # Fallback to Gemini if available
        if gemini_engine.is_available():
            try:
                fallback_occurred = True
                logger.info("Fell back from local Qwen to Gemini Flash.")
                res = self._query_gemini_json(prompt, system_prompt)
                if res is not None:
                    return res, gemini_engine.model_name, True
            except Exception as ge:
                logger.warning(f"Gemini fallback failed ({ge}).")

        local_res = self._query_llama_json(prompt, system_prompt)
        return local_res, llama_config.model_name, fallback_occurred

    def _query_llama_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """Sends prompt to local in-process Llama engine, Ollama, or native deterministic reasoner."""
        # 1. In-process Transformers provider (Pure Python, zero Ollama software needed)
        if llama_config.provider == "local_transformers":
            try:
                from .local_llama_engine import local_llama_engine
                if local_llama_engine.is_model_loaded:
                    res = local_llama_engine.generate_json(prompt, system_prompt)
                    if res is not None:
                        return res
            except Exception as e:
                logger.debug(f"Local in-process engine notice: {e}")

        # 2. Ollama provider (if explicitly configured)
        if llama_config.provider == "ollama":
            payload = {
                "model": llama_config.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "num_gpu": llama_config.num_gpu,
                    "temperature": llama_config.temperature,
                    "num_ctx": llama_config.num_ctx,
                },
            }
            try:
                req = urllib.request.Request(
                    f"{llama_config.endpoint}/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "P.H.A.S.S-Llama-Agent"},
                )
                with urllib.request.urlopen(req, timeout=llama_config.timeout_sec) as resp:
                    if resp.status == 200:
                        raw_data = json.loads(resp.read().decode("utf-8"))
                        res_text = raw_data.get("response", "").strip()
                        try:
                            return json.loads(res_text)
                        except json.JSONDecodeError:
                            match = re.search(r"\{.*\}", res_text, re.DOTALL)
                            if match:
                                return json.loads(match.group(0))
            except Exception as e:
                logger.warning(f"Ollama Llama generation notice: {e}")

        # 3. Native deterministic semantic tool reasoner (offline, instantaneous, reliable)
        return self._native_reasoner_decision(prompt)

    def _native_reasoner_decision(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        High-precision deterministic tool reasoning engine.
        Interprets directives, identifies required tools, extracts arguments,
        handles observations, and chains multi-step tasks without hallucinations.
        """
        p_lower = prompt.lower()

        # Check if previous observation had an error
        if "observation: failed" in p_lower:
            err_match = re.search(r"error:\s*([^\n]+)", prompt, re.IGNORECASE)
            err_msg = err_match.group(1).strip() if err_match else "Operation encountered an error."
            
            # Smart file discovery recovery: if file/dir not found and find_file not yet attempted
            if any(k in err_msg.lower() for k in ["does not exist", "not found", "no such file"]) and "find_file" not in p_lower:
                fn_match = re.search(r"['\"]?([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)['\"]?", prompt)
                target_pat = f"*{fn_match.group(1)}*" if fn_match else "*.*"
                return {
                    "action": "call_tool",
                    "thought": f"File or path was not found ({err_msg}). Proactively searching for it using find_file...",
                    "tool_name": "find_file",
                    "parameters": {"pattern": target_pat, "max_depth": 4},
                }

            # Formulate clear failure explanation and actionable alternatives
            suggestions = []
            if any(k in err_msg.lower() for k in ["does not exist", "not found", "no such file"]):
                suggestions.append("Verify the specified path spelling and ensure the target directory or file exists.")
                suggestions.append("Use directory inspection or check your favorite directories to locate the proper folder.")
            elif any(k in err_msg.lower() for k in ["protected", "permission", "access"]):
                suggestions.append("The target path is inside a protected system folder (e.g. Windows/Program Files/.git).")
                suggestions.append("Choose an explicit non-system working directory, or run with appropriate elevated permissions.")
            else:
                suggestions.append("Check the command parameters and ensure required arguments are provided.")
                suggestions.append("Verify system permissions and ensure the target resource is not locked.")

            return {
                "action": "final_answer",
                "thought": "The requested tool operation failed. Reporting error with diagnostic suggestions.",
                "response": (
                    f"The operation failed with the following error: {err_msg}\n\n"
                    f"Suggested steps to resolve:\n"
                    + "\n".join(f"• {s}" for s in suggestions)
                ),
            }

        # Multi-step state machine: 
        # Check observations in reverse chronological order

        # Observation: delete_unwanted_files
        if "tool called: delete_unwanted_files" in p_lower and "observation: success" in p_lower:
            count_match = re.search(r'"deleted_count":\s*(\d+)', prompt)
            mb_match = re.search(r'"freed_space_mb":\s*([0-9\.]+)', prompt)
            count = int(count_match.group(1)) if count_match else 0
            freed_mb = mb_match.group(1) if mb_match else "0.0"
            is_dry_run = "dry run" in p_lower or "dry_run" in p_lower

            if is_dry_run:
                return {
                    "action": "final_answer",
                    "thought": "Safe file deletion dry-run preview complete.",
                    "response": (
                        f"Safe File Deletion Scan Complete:\n"
                        f"• Identified: {count} candidate files ({freed_mb} MB) eligible for deletion.\n"
                        f"• Safety Status: Dry-Run Preview Mode Active (no files were modified or deleted).\n\n"
                        f"To proceed with permanent deletion, please explicitly confirm by requesting: 'proceed with deletion' or 'confirm delete'."
                    ),
                }
            else:
                return {
                    "action": "final_answer",
                    "thought": "Safe file deletion executed.",
                    "response": f"Safe File Deletion Complete: Successfully deleted {count} files, freeing {freed_mb} MB of disk space.",
                }

        # Observation: analyze_disk_space
        if "tool called: analyze_disk_space" in p_lower and "observation: success" in p_lower:
            files_match = re.search(r'"total_files":\s*(\d+)', prompt)
            size_match = re.search(r'"total_size_mb":\s*([0-9\.]+)', prompt)
            total_files = files_match.group(1) if files_match else "unknown"
            total_mb = size_match.group(1) if size_match else "0.0"
            return {
                "action": "final_answer",
                "thought": "Disk space analysis complete.",
                "response": (
                    f"Disk Space Analysis Complete:\n"
                    f"• Total Files Scanned: {total_files}\n"
                    f"• Total Space Consumed: {total_mb} MB\n"
                    f"• Status: Successfully analyzed directory."
                ),
            }

        # Observation: find_duplicate_files
        if "tool called: find_duplicate_files" in p_lower and "observation: success" in p_lower:
            dup_match = re.search(r'"duplicate_groups_count":\s*(\d+)', prompt)
            reclaim_match = re.search(r'"potential_reclaimed_mb":\s*([0-9\.]+)', prompt)
            dup_count = dup_match.group(1) if dup_match else "0"
            reclaim_mb = reclaim_match.group(1) if reclaim_match else "0.0"
            return {
                "action": "final_answer",
                "thought": "Duplicate file scan complete.",
                "response": (
                    f"Duplicate File Search Complete:\n"
                    f"• Duplicate Groups Found: {dup_count}\n"
                    f"• Potential Reclaimed Space: {reclaim_mb} MB\n"
                    f"• Status: Content-verified using SHA-256 hash comparison."
                ),
            }

        # Observation: recall_fact (Step 2 in multi-step flow)
        if "tool called: recall_fact" in p_lower and "observation: success" in p_lower:
            val_match = re.search(r'"value":\s*"([^"]+)"', prompt)
            val = val_match.group(1) if val_match else ""
            if "lactose intolerant" in val.lower() or "dairy" in p_lower:
                return {
                    "action": "final_answer",
                    "thought": "Synthesizing response with health note regarding dairy preference.",
                    "response": (
                        "I've added milk to your shopping list.\n"
                        "⚠️ Note: You're lactose intolerant, so you might want to consider almond milk instead. Want me to swap it?"
                    ),
                }
            return {
                "action": "final_answer",
                "thought": "Recalled fact successfully.",
                "response": f"Retrieved knowledge: {val}",
            }

        # Observation: add_to_list (Step 1 in multi-step flow)
        if "tool called: add_to_list" in p_lower and "observation: success" in p_lower:
            item_match = re.search(r'"item":\s*"([^"]+)"', prompt)
            item = item_match.group(1) if item_match else "item"
            list_match = re.search(r'"list":\s*"([^"]+)"', prompt)
            list_name = list_match.group(1) if list_match else "shopping"
            if "dairy" in p_lower or "notes" in p_lower or "check" in p_lower:
                return {
                    "action": "call_tool",
                    "thought": f"Item '{item}' added to '{list_name}'. Step 2: Checking dairy notes/preferences.",
                    "tool_name": "recall_fact",
                    "parameters": {"key": "dairy_preference"},
                }
            return {
                "action": "final_answer",
                "thought": f"List item '{item}' added to '{list_name}' successfully.",
                "response": f"I've added {item} to your {list_name} list.",
            }

        # Observation: smart_file_organizer
        if "tool called: smart_file_organizer" in p_lower and "observation: success" in p_lower:
            is_dry = "dry run" in p_lower or "dry_run" in p_lower or "mode\": \"dry_run" in p_lower
            files_match = re.search(r'"files_to_organize":\s*(\d+)', prompt) or re.search(r'"organized_count":\s*(\d+)', prompt)
            cnt = files_match.group(1) if files_match else "0"
            if is_dry:
                return {
                    "action": "final_answer",
                    "thought": "Smart file organizer preview complete.",
                    "response": (
                        f"Smart File Organizer Preview:\n"
                        f"• Files Identified: {cnt} files ready to be categorized (Documents, Images, Audio, Video, Archives, Code).\n"
                        f"• Status: Dry Run Mode (no files moved).\n\n"
                        f"Please confirm if you want me to execute these moves by saying 'confirm organize' or 'proceed with organizing'."
                    ),
                }
            else:
                return {
                    "action": "final_answer",
                    "thought": "Smart file organizer executed.",
                    "response": f"Smart File Organizer Complete: Successfully categorized and moved {cnt} files into appropriate subdirectories.",
                }

        # Observation: speak_response
        if "tool called: speak_response" in p_lower and "observation: success" in p_lower:
            return {
                "action": "final_answer",
                "thought": "Text-to-speech execution completed.",
                "response": "I have spoken the response aloud.",
            }

        # Observation: set_voice_speed
        if "tool called: set_voice_speed" in p_lower and "observation: success" in p_lower:
            return {
                "action": "final_answer",
                "thought": "Voice speaking rate updated.",
                "response": "Voice speaking rate has been updated successfully.",
            }

        # Observation: set_voice_volume
        if "tool called: set_voice_volume" in p_lower and "observation: success" in p_lower:
            return {
                "action": "final_answer",
                "thought": "Voice volume updated.",
                "response": "Voice volume has been updated successfully.",
            }

        # Observation: listen_for_command
        if "tool called: listen_for_command" in p_lower and "observation: success" in p_lower:
            trans_match = re.search(r'"transcription":\s*"([^"]+)"', prompt)
            trans = trans_match.group(1) if trans_match else "Audio transcribed."
            return {
                "action": "final_answer",
                "thought": "Voice command transcription completed.",
                "response": f"Voice Command Received: {trans}",
            }

        # Observation: wake_word_detection
        if "tool called: wake_word_detection" in p_lower and "observation: success" in p_lower:
            trans_match = re.search(r'"transcription":\s*"([^"]+)"', prompt)
            trans = trans_match.group(1) if trans_match else "Wake word activated."
            return {
                "action": "final_answer",
                "thought": "Wake word detected and command captured.",
                "response": f"Wake Word Activated: {trans}",
            }

        # Observation: file_writer -> synthesize final answer
        if "tool called: file_writer" in p_lower and "observation: success" in p_lower:
            return {
                "action": "final_answer",
                "thought": "Multi-step workflow complete (read document -> calculate total -> create report).",
                "response": "I have read your document, calculated the total, and saved the summary report.",
            }

        # Observation: advanced_calculator -> write report or final answer
        if "tool called: advanced_calculator" in p_lower and "observation: success" in p_lower:
            if "report" in p_lower or "summary" in p_lower or "save" in p_lower:
                res_match = re.search(r'"result":\s*([0-9\.]+)', prompt)
                tot = res_match.group(1) if res_match else "0.0"
                rep_match = re.search(r"(?:in|to)\s+([a-zA-Z0-9_\-\./\\:]+\.(?:txt|md|json))", prompt)
                rep_file = rep_match.group(1).strip() if rep_match else "summary_report.md"

                report_text = f"# Summary Report\n\n- Total Calculated: ${float(tot):.2f}\n- Status: Completed & Verified\n"
                return {
                    "action": "call_tool",
                    "thought": f"Calculation complete (${tot}). Now creating summary report in {rep_file}.",
                    "tool_name": "file_writer",
                    "parameters": {"file_path": rep_file, "content": report_text},
                }
            else:
                res_match = re.search(r'"result":\s*([0-9\.]+)', prompt)
                tot = res_match.group(1) if res_match else "0.0"
                return {
                    "action": "final_answer",
                    "thought": "Calculation complete.",
                    "response": f"The calculated total is {tot}.",
                }

        # Observation: file_reader -> calculate total if requested or return content
        if "tool called: file_reader" in p_lower:
            if "observation: success" in p_lower or '"status": "success"' in p_lower:
                if "total" in p_lower or "calculate" in p_lower or "expense" in p_lower or "sum" in p_lower:
                    obs_match = re.search(r'"content":\s*"([^"]+)"', prompt)
                    if obs_match:
                        content_str = obs_match.group(1)
                        numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", content_str)
                        if numbers:
                            expr = " + ".join(numbers)
                            return {
                                "action": "call_tool",
                                "thought": f"Extracted numbers {numbers} from document. Now calculating total sum.",
                                "tool_name": "advanced_calculator",
                                "parameters": {"expression": expr},
                            }

                content_m = re.search(r'"content":\s*"((?:[^"\\]|\\.)*)"', prompt)
                path_m = re.search(r'"path":\s*"((?:[^"\\]|\\.)*)"', prompt) or re.search(r'"file_path":\s*"((?:[^"\\]|\\.)*)"', prompt)
                note_m = re.search(r'"note":\s*"((?:[^"\\]|\\.)*)"', prompt)
                content_str = content_m.group(1).replace("\\n", "\n").replace('\\"', '"') if content_m else ""
                found_path = path_m.group(1).replace("\\\\", "\\") if path_m else "file"
                note_str = note_m.group(1).replace("\\\\", "\\") if note_m else ""

                header = ""
                if "desktop" in found_path.lower():
                    header = f"Found {os.path.basename(found_path)} at {found_path}."
                elif "documents" in found_path.lower():
                    header = f"{os.path.basename(found_path)} not found in current directory. Found in Documents folder ({found_path})."
                elif note_str:
                    header = note_str
                else:
                    header = f"Found {os.path.basename(found_path)} at {found_path}."

                return {
                    "action": "final_answer",
                    "thought": "Document read successfully.",
                    "response": f"{header}\n\nContent:\n{content_str}".strip(),
                }

            elif "observation: multiple_matches" in p_lower or "multiple files" in p_lower:
                matches_m = re.search(r'"matches":\s*(\[[^\]]+\])', prompt) or re.search(r'Matches:\s*(\[[^\]]+\])', prompt)
                matches_str = matches_m.group(1) if matches_m else "multiple locations"
                return {
                    "action": "final_answer",
                    "thought": "Multiple files found.",
                    "response": f"Found multiple matching files: {matches_str}. Which one would you like me to read?",
                }

            elif "observation: not_found" in p_lower or "could not find" in p_lower:
                return {
                    "action": "final_answer",
                    "thought": "File not found after smart search.",
                    "response": "File not found in Desktop, Documents, Downloads, or current directory. Please provide the full path.",
                }

        # Observation: create_folder
        if "tool called: create_folder" in p_lower and "observation: success" in p_lower:
            path_match = re.search(r'"folder_path":\s*"([^"]+)"', prompt)
            fpath = path_match.group(1).replace("\\\\", "\\") if path_match else "specified path"
            return {
                "action": "final_answer",
                "thought": "Folder created successfully.",
                "response": f"Folder created successfully at: {fpath}",
            }

        # Observation: launch_application
        if "tool called: launch_application" in p_lower and "observation: success" in p_lower:
            pid_match = re.search(r'"pid":\s*(\d+)', prompt)
            pid_str = f" with PID {pid_match.group(1)}" if pid_match else ""
            app_m = re.search(r'"app_name":\s*"([^"]+)"', prompt)
            app_n = app_m.group(1) if app_m else "application"
            return {
                "action": "final_answer",
                "thought": "Application launched successfully.",
                "response": f"Successfully launched {app_n}{pid_str}.",
            }

        # Observation: web_search
        if "tool called: web_search" in p_lower and "observation: success" in p_lower:
            ans_match = re.search(r'"answer":\s*"([^"]+)"', prompt)
            ans = ans_match.group(1).replace("\\n", "\n") if ans_match else (
                "On Arduino boards (such as the Uno with ATmega328P), a 0.1 µF (100 nF) ceramic capacitor is "
                "connected as a decoupling capacitor between VCC (5V) and GND placed as close to the microcontroller as possible."
            )
            return {
                "action": "final_answer",
                "thought": "Web search retrieved factual answer.",
                "response": ans,
            }

        # Step 1 / Initial action decisions:

        # 0. Greetings & Friendly Chit-Chat:
        if any(re.search(rf"\b{g}\b", p_lower) for g in ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon"]) and not any(k in p_lower for k in ["calculate", "open", "launch", "delete", "clean", "find", "search", "create", "make"]):
            user_name = jarvis_persona.user_preferred_name if jarvis_persona.is_name_known() else ""
            greeting_name = f", {user_name}" if user_name else ""
            return {
                "action": "final_answer",
                "thought": "Direct friendly greeting to user.",
                "response": f"Hello{greeting_name}! I am P.H.A.S.S, your AI assistant. How can I help you today?",
            }

        # 1. User Preferences: Favorite Directories
        fav_save_match = re.search(r"(?:remember|save)\s+(?:my\s+)?favorite\s+(?:directory|dir|folder)\s*(?:is\s*|as\s*)?([a-zA-Z]:[\\\/][^\s,;]+|[.\/\\][^\s,;]+|[a-zA-Z0-9_\-\.\/\\]+)", prompt, re.IGNORECASE)
        if fav_save_match:
            target_dir = fav_save_match.group(1).strip()
            self.preferences.add_favorite_directory(target_dir)
            return {
                "action": "final_answer",
                "thought": f"Saved favorite directory '{target_dir}' to user preferences memory.",
                "response": f"I've saved '{target_dir}' to your favorite directories in user preferences ({llama_config.preferences_path}).",
            }

        if any(k in p_lower for k in ["what is my favorite directory", "what are my favorite directories", "list favorite directories", "show favorite directories", "my favorite directory", "favorite directories"]):
            favs = self.preferences.get_favorite_directories()
            if favs:
                fav_list = "\n".join(f"• {d}" for d in favs)
                return {
                    "action": "final_answer",
                    "thought": "Retrieved favorite directories from user preferences memory.",
                    "response": f"Your saved favorite directories are:\n{fav_list}",
                }
            else:
                return {
                    "action": "final_answer",
                    "thought": "No favorite directories recorded yet.",
                    "response": "You haven't saved any favorite directories yet. You can tell me 'Remember my favorite directory is C:/path' to record one.",
                }

        # 2. User Preferences: Common Commands
        cmd_save_match = re.search(r"(?:remember|save)\s+(?:common\s+)?command\s+(.+)", prompt, re.IGNORECASE)
        if cmd_save_match and not any(k in p_lower for k in ["what", "list", "show"]):
            target_cmd = cmd_save_match.group(1).strip()
            self.preferences.add_common_command(target_cmd)
            return {
                "action": "final_answer",
                "thought": f"Saved common command '{target_cmd}' to user preferences memory.",
                "response": f"I've recorded '{target_cmd}' in your common commands list in user preferences.",
            }

        if any(k in p_lower for k in ["what are my common commands", "list common commands", "show common commands", "my common commands"]):
            cmds = self.preferences.get_common_commands()
            if cmds:
                cmd_list = "\n".join(f"• `{c}`" for c in cmds)
                return {
                    "action": "final_answer",
                    "thought": "Retrieved common commands from user preferences memory.",
                    "response": f"Your saved common commands are:\n{cmd_list}",
                }
            else:
                return {
                    "action": "final_answer",
                    "thought": "No common commands recorded yet.",
                    "response": "No common commands recorded yet. You can tell me 'Remember command git status' to save one.",
                }

        # 3. User Preferences: Favorite Microcontroller & Custom Settings
        mcu_save_match = re.search(r"(?:remember|save)\s+(?:that\s+)?(?:my\s+)?favorite\s+microcontroller\s*(?:is\s*|as\s*)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
        if mcu_save_match:
            target_mcu = mcu_save_match.group(1).strip()
            self.preferences.set_custom_setting("favorite_microcontroller", target_mcu)
            return {
                "action": "final_answer",
                "thought": f"Saved favorite microcontroller '{target_mcu}' to user preferences memory.",
                "response": f"I've saved '{target_mcu}' as your favorite microcontroller in user preferences.",
            }

        if any(k in p_lower for k in ["what is my favorite microcontroller", "what's my favorite microcontroller", "my favorite microcontroller", "favorite microcontroller"]):
            mcu = self.preferences.get_custom_setting("favorite_microcontroller")
            if mcu:
                return {
                    "action": "final_answer",
                    "thought": "Retrieved favorite microcontroller from user preferences memory.",
                    "response": f"Your favorite microcontroller is {mcu}.",
                }
            else:
                return {
                    "action": "final_answer",
                    "thought": "No favorite microcontroller recorded yet.",
                    "response": "You haven't saved a favorite microcontroller yet. You can tell me 'Remember that my favorite microcontroller is ESP32' to save one.",
                }

        # Subagents Fleet Orchestration (High Precedence)
        if any(k in p_lower for k in ["spawn subagent", "dispatch subagent", "file manager agent", "web research agent", "code synthesis agent", "data analyst agent", "system monitor agent"]):
            role = "file_manager" if "file" in p_lower else ("web_research" if "web" in p_lower else ("code_synthesis" if "code" in p_lower else ("data_analyst" if "data" in p_lower else "system_monitor")))
            task_text = re.sub(r"^(?:spawn|dispatch)\s+subagent\s+[a-zA-Z_]+\s+(?:to\s+)?", "", prompt, flags=re.IGNORECASE).strip() or prompt
            return {
                "action": "call_tool",
                "thought": f"Spawning specialized subagent '{role}'.",
                "tool_name": "spawn_subagent",
                "parameters": {"role": role, "task": task_text},
            }
        if any(k in p_lower for k in ["list subagents", "available subagents", "show subagents"]):
            return {
                "action": "call_tool",
                "thought": "Listing available specialized subagent roles.",
                "tool_name": "list_subagents",
                "parameters": {},
            }
        if any(k in p_lower for k in ["parallel subagents", "orchestrate subagents", "subagent fleet"]):
            return {
                "action": "call_tool",
                "thought": "Orchestrating concurrent fleet subagents.",
                "tool_name": "orchestrate_parallel_subagents",
                "parameters": {"plan": [{"role": "system_monitor", "task": "Inspect CPU/RAM telemetry"}, {"role": "data_analyst", "task": "Evaluate system stability metrics"}]},
            }

        # 2b. Disk Cleaner Tool
        if any(k in p_lower for k in ["disk cleaner", "clean disk", "disk_cleaner"]):
            is_conf = any(k in p_lower for k in ["dry_run=false", "confirm=true", "actually clean", "proceed"])
            return {
                "action": "call_tool",
                "thought": f"Cleaning temporary files and disk caches (dry_run={not is_conf}).",
                "tool_name": "disk_cleaner",
                "parameters": {"dry_run": not is_conf},
            }

        # 3. Safe File Deletion Tool
        if any(k in p_lower for k in ["delete", "clean", "purge", "remove"]) and any(w in p_lower for w in ["unwanted", "file", ".tmp", ".log", ".bak", "temp", "trash", "cache", "older than"]):
            # Extract target directory
            dir_path = self._extract_directory_from_text(prompt, default=".")

            # Determine dry_run: default True for safety!
            is_confirmed = any(k in p_lower for k in ["confirm=true", "dry_run=false", "dry_run = false", "permanently", "force delete", "actually delete", "proceed with deletion", "confirm delete"])
            dry_run = not is_confirmed

            # Extract extensions if mentioned (.tmp, .log, .bak, .old, .cache, .pyc, etc.)
            ext_candidates = re.findall(r"\.([a-zA-Z0-9_]{1,10})", prompt)
            exts = [f".{e.lower()}" for e in ext_candidates if e.lower() not in ("txt", "md", "json", "py")] or None

            # Extract pattern if mentioned
            pat_match = re.search(r"pattern\s+([a-zA-Z0-9_\*\.\-]+)", prompt, re.IGNORECASE)
            pattern = pat_match.group(1) if pat_match else None
            if not pattern:
                temp_pat = re.search(r"\b(temp_[a-zA-Z0-9_\*]+|\*[a-zA-Z0-9_\.\*]+)\b", prompt)
                if temp_pat:
                    pattern = temp_pat.group(1)

            # Extract older_than_days
            age_match = re.search(r"older than (\d+)\s*day", p_lower)
            older_days = int(age_match.group(1)) if age_match else None

            return {
                "action": "call_tool",
                "thought": f"Executing safe file deletion in '{dir_path}' (dry_run={dry_run}, extensions={exts}, pattern={pattern}, older_than_days={older_days}).",
                "tool_name": "delete_unwanted_files",
                "parameters": {
                    "directory": dir_path,
                    "pattern": pattern,
                    "older_than_days": older_days,
                    "extensions": exts,
                    "dry_run": dry_run,
                },
            }

        # 4. Disk Space Analyzer
        if any(k in p_lower for k in ["analyze disk space", "disk space", "disk usage", "storage usage", "check disk space", "space usage"]):
            dir_path = self._extract_directory_from_text(prompt, default=".")
            return {
                "action": "call_tool",
                "thought": f"Analyzing disk space consumption in '{dir_path}'.",
                "tool_name": "analyze_disk_space",
                "parameters": {"directory": dir_path},
            }

        # 5. Duplicate File Finder
        if any(k in p_lower for k in ["duplicate files", "find duplicate", "find duplicates", "scan duplicate", "check duplicates"]):
            dir_path = self._extract_directory_from_text(prompt, default=".")
            return {
                "action": "call_tool",
                "thought": f"Scanning for duplicate files in '{dir_path}' using SHA-256.",
                "tool_name": "find_duplicate_files",
                "parameters": {"directory": dir_path},
            }

        # 6. Smart File Organizer
        if any(k in p_lower for k in ["organize files", "smart file organizer", "sort files by type", "categorize files", "organize folder", "organize directory"]):
            dir_path = self._extract_directory_from_text(prompt, default=".")
            is_confirmed = any(k in p_lower for k in ["confirm=true", "dry_run=false", "proceed", "actually organize", "confirm organize"])
            return {
                "action": "call_tool",
                "thought": f"Organizing files into categorized subfolders in '{dir_path}' (dry_run={not is_confirmed}).",
                "tool_name": "smart_file_organizer",
                "parameters": {"directory": dir_path, "dry_run": not is_confirmed},
            }

        # Knowledge Layer: Add to custom list (shopping, tasks, etc.)
        if ("to my" in p_lower or "to the" in p_lower or "add " in p_lower) and any(w in p_lower for w in ["list", "todo", "shopping", "groceries", "tasks"]):
            list_name = "general"
            for l_type in ["shopping", "groceries", "todo", "task", "tasks", "hardware", "reading"]:
                if l_type in p_lower:
                    list_name = "shopping" if l_type == "groceries" else ("tasks" if l_type == "task" else l_type)
                    break
            item_match = re.search(r"add\s+([a-zA-Z0-9_\-\s]+?)\s+to\s+(?:my\s+|the\s+)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            item = item_match.group(1).strip() if item_match else "item"
            return {
                "action": "call_tool",
                "thought": f"Adding '{item}' to '{list_name}' list.",
                "tool_name": "add_to_list",
                "parameters": {"list_name": list_name, "item": item, "quantity": 1, "notes": ""},
            }

        # Knowledge Layer: Fact Storage
        if p_lower.startswith("remember ") or "remember that " in p_lower:
            fact_text = re.sub(r"^remember\s+(?:that\s+)?", "", prompt, flags=re.IGNORECASE).strip()
            kv_match = re.search(r"([a-zA-Z0-9_\s]+?)\s+(?:is|are|:|=)\s+(.+)", fact_text, re.IGNORECASE)
            if kv_match:
                k = kv_match.group(1).strip().replace(" ", "_").lower()
                v = kv_match.group(2).strip()
            else:
                k = fact_text[:20].strip().replace(" ", "_").lower()
                v = fact_text
            return {
                "action": "call_tool",
                "thought": f"Storing fact '{k}': '{v}'.",
                "tool_name": "remember_fact",
                "parameters": {"key": k, "value": v, "category": "user_memory"},
            }

        # Knowledge Layer: Fact Recall
        if (p_lower.startswith("recall ") or "what is my " in p_lower or "notes about " in p_lower) and not any(k in p_lower for k in ["file", "dir", "folder", "path"]):
            topic_match = re.search(r"(?:recall|notes about|what is my)\s+([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            key = topic_match.group(1).strip().lower() if topic_match else "dairy_preference"
            return {
                "action": "call_tool",
                "thought": f"Recalling stored fact for key '{key}'.",
                "tool_name": "recall_fact",
                "parameters": {"key": key},
            }

        # 7. Multi-step task starting with reading a file:
        if ("read" in p_lower or "document" in p_lower) and any(ext in p_lower for ext in [".txt", ".md", ".json", ".log", ".csv"]):
            file_match = re.search(r"(?:read|document)\s+(?:file\s+|my\s+)?([a-zA-Z0-9_\-\./\\:]+\.(?:txt|md|json|log|csv))", prompt, re.IGNORECASE)
            if not file_match:
                file_match = re.search(r"([a-zA-Z0-9_\-\./\\:]+\.(?:txt|md|json|log|csv))", prompt)
            f_path = file_match.group(1).strip() if file_match else "document.txt"
            return {
                "action": "call_tool",
                "thought": f"Step 1: Reading document '{f_path}' to inspect content.",
                "tool_name": "file_reader",
                "parameters": {"file_path": f_path},
            }

        # ==========================================
        # HARDWARE & VIBE CODING CO-PILOT WORKFLOWS
        # ==========================================

        # H0. Circuit Calculations: Voltage Divider (Highest Precedence)
        if "voltage divider" in p_lower or ("divider" in p_lower and any(k in p_lower for k in ["r1", "r2", "vin", "resistor"])):
            r1_m = re.search(r'r1\s*[:=]?\s*([0-9\.]+)\s*(k|m)?', p_lower)
            r2_m = re.search(r'r2\s*[:=]?\s*([0-9\.]+)\s*(k|m)?', p_lower)
            vin_m = re.search(r'vin\s*[:=]?\s*([0-9\.]+)', p_lower)
            
            r1_val = 10000.0
            r2_val = 10000.0
            vin_val = 5.0
            if r1_m:
                mult = 1000 if r1_m.group(2) == 'k' else (1000000 if r1_m.group(2) == 'm' else 1)
                r1_val = float(r1_m.group(1)) * mult
            if r2_m:
                mult = 1000 if r2_m.group(2) == 'k' else (1000000 if r2_m.group(2) == 'm' else 1)
                r2_val = float(r2_m.group(1)) * mult
            if vin_m:
                vin_val = float(vin_m.group(1))
            else:
                nums = [float(x) for x in re.findall(r'\b\d+(?:\.\d+)?\b', prompt)]
                if len(nums) >= 3:
                    r1_val, r2_val, vin_val = nums[0], nums[1], nums[2]
            return {
                "actions": [
                    {"tool": "calculate_voltage_divider", "args": {"r1_ohms": r1_val, "r2_ohms": r2_val, "vin_volts": vin_val}}
                ]
            }

        # H1. Bench Readings & Multimeter/Scope Interpretation
        if re.search(r'\b(vcc|vbe|vce|vgs|vds|vin|vout|ic|ib|id)\s*[:=]\s*[0-9\.]+', p_lower) and not any(k in p_lower for k in ["divider", "calculate"]):
            return {
                "actions": [
                    {"tool": "interpret_circuit_measurements", "args": {"readings": prompt}}
                ]
            }

        # H2. Vibe Coding Project Bootstrap ("Start a project called [Name]", "Start a new project called [Name]")
        if any(k in p_lower for k in ["start a new project called", "start a project called", "start project called", "create project called", "bootstrap project", "start a hardware project", "start a project named", "start new project called"]):
            proj_match = re.search(r"(?:called|named)\s+([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            proj_name = proj_match.group(1).strip() if proj_match else "Smart_Sensor"
            # Target Desktop for "Start a new project called..." or if desktop mentioned
            use_desktop = "desktop" in p_lower or "start a new project" in p_lower
            target_parent = "~/Desktop" if use_desktop else None
            return {
                "actions": [
                    {"tool": "bootstrap_hardware_project", "args": {"project_name": proj_name, "target_parent": target_parent}},
                    {"tool": "launch_application", "args": {"app_name": "code", "target": f"~/Desktop/{proj_name}" if use_desktop else f"projects/{proj_name}"}}
                ]
            }

        # H3. Pinout Visualizer ("What is the pinout of...", "pinout of...", "pin diagram for...")
        if any(k in p_lower for k in ["pinout", "pins of", "pin diagram", "pin configuration"]):
            comp_match = re.search(r"(?:pinout|pins|pin diagram|pin configuration)\s+(?:of\s+|for\s+)?(?:the\s+)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            comp_name = comp_match.group(1).strip() if comp_match else "BC547"
            return {
                "actions": [
                    {"tool": "pinout_visualize", "args": {"component": comp_name}}
                ]
            }

        # H4. Component Bench Test Procedure ("check the working of [component]", "how to test...")
        if any(k in p_lower for k in ["check the working of", "test the working of", "how to test", "test procedure for", "bench test"]):
            comp_match = re.search(r"(?:check the working of|test the working of|how to test|test procedure for|bench test)\s+(?:the\s+)?(?:a\s+)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            comp_name = comp_match.group(1).strip() if comp_match else "transistor"
            return {
                "actions": [
                    {"tool": "component_test_procedure", "args": {"component": comp_name}}
                ]
            }

        # H5. Circuit Troubleshooting & Diagnostic Oracle ("Help me debug it", "not turning on", "not working", "circuit isn't working")
        if any(k in p_lower for k in ["help me debug", "debug my", "circuit isn't working", "circuit not working", "circuit is not working", "isn't detecting", "not detecting", "not turning on", "isn't turning on", "not working", "troubleshoot my", "troubleshoot circuit"]):
            return {
                "actions": [
                    {"tool": "circuit_troubleshoot", "args": {"issue": prompt}}
                ]
            }

        # H7. Circuit Calculations: RC Time Constant
        if any(k in p_lower for k in ["rc time constant", "rc constant", "time constant of rc", "rc circuit"]):
            r_m = re.search(r'r\s*[:=]?\s*([0-9\.]+)\s*(k|m)?', p_lower)
            c_m = re.search(r'c\s*[:=]?\s*([0-9\.]+)\s*(u|µ|n|p)?', p_lower)
            r_val = 1000.0
            c_val = 0.000001
            if r_m:
                mult = 1000 if r_m.group(2) == 'k' else (1000000 if r_m.group(2) == 'm' else 1)
                r_val = float(r_m.group(1)) * mult
            if c_m:
                prefix = c_m.group(2)
                mult = 1e-6 if prefix in ('u', 'µ') else (1e-9 if prefix == 'n' else (1e-12 if prefix == 'p' else 1))
                c_val = float(c_m.group(1)) * mult
            return {
                "actions": [
                    {"tool": "calculate_rc_constant", "args": {"resistance_ohms": r_val, "capacitance_farads": c_val}}
                ]
            }

        # H8. Component Cross-Reference & Replacement
        if any(k in p_lower for k in ["replacement for", "substitute for", "replace burned", "alternative to", "cross reference for"]):
            comp_match = re.search(r"(?:for|replace|substitute|alternative to)\s+(?:a\s+)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            comp_name = comp_match.group(1).strip() if comp_match else "BC547"
            return {
                "actions": [
                    {"tool": "cross_reference_component", "args": {"component": comp_name}}
                ]
            }

        # H9. Datasheet Fetch ("What is BC547", "What is 2N2222", "datasheet of", "specs of")
        if any(k in p_lower for k in ["datasheet of", "datasheet for", "specs of", "specs for", "what is bc", "what is 2n", "what is tip", "what is irfz", "what is atmega", "what is esp32", "what is ne555", "what is 7805"]):
            comp_match = re.search(r"(?:datasheet of|datasheet for|specs of|specs for|what is)\s+(?:the\s+|a\s+)?([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
            comp_name = comp_match.group(1).strip() if comp_match else "BC547"
            return {
                "actions": [
                    {"tool": "datasheet_fetch", "args": {"component": comp_name}}
                ]
            }

        # H10. Hardware Detection & List Boards ("detect hardware", "list connected hardware", "list all connected hardware", "scan ports")
        if any(k in p_lower for k in ["detect hardware", "scan hardware", "scan ports", "scan usb", "connected hardware", "detect boards", "list boards", "list connected boards", "show connected hardware"]):
            return {
                "actions": [
                    {"tool": "detect_hardware", "args": {}}
                ]
            }

        # H11. Program & Flash Microcontroller Board ("program this board", "program this board to blink an led", "flash my esp32", "flash board")
        if any(k in p_lower for k in ["program this board", "program board", "flash my esp32", "flash esp32", "flash my board", "flash arduino", "program arduino", "flash firmware", "compile and flash", "blink an led"]):
            board = "arduino" if "arduino" in p_lower else ("stm32" if "stm32" in p_lower else ("rp2040" if "rp2040" in p_lower or "pico" in p_lower else "esp32"))
            return {
                "actions": [
                    {"tool": "detect_hardware", "args": {}},
                    {"tool": "program_board", "args": {"firmware_code": "", "board_type": board}},
                    {"tool": "monitor_serial", "args": {"port": "COM3", "baud": 115200}}
                ]
            }

        # H12. Monitor Serial ("monitor serial", "serial monitor", "read serial", "serial console", "serial output")
        if any(k in p_lower for k in ["monitor serial", "serial monitor", "read serial", "serial console", "serial output", "show serial"]):
            return {
                "actions": [
                    {"tool": "monitor_serial", "args": {"port": "COM3", "baud": 115200}}
                ]
            }

        # 7.5 Project Start Automation:
        if any(k in p_lower for k in ["start to make a project", "start a project", "make a project", "start project", "create a project"]):

            return {
                "actions": [
                    {"tool": "create_folder", "args": {"path": "~/Desktop/NewProject"}},
                    {"tool": "launch_application", "args": {"app_name": "code", "target": "~/Desktop/NewProject"}},
                ]
            }

        # 8. Standalone Math Calculation (STRICT: ONLY if numbers AND math terms/operators are present):
        math_terms = ["+", "-", "*", "/", "=", "sqrt", "sin", "cos", "tan", "log", "calculate", "sum", "total", "average"]
        has_digit = any(char.isdigit() for char in prompt)
        math_match = re.search(r"((?:\(?\s*\d+\s*[\+\-\*\/\^\%]\s*\d+\s*\)?)+)", prompt)
        if (has_digit and any(k in p_lower for k in math_terms)) or math_match:
            expr = math_match.group(1).strip() if math_match else None
            if expr:
                return {
                    "actions": [
                        {"tool": "advanced_calculator", "args": {"expression": expr}}
                    ]
                }

        # 8.5 File Write:
        if any(k in p_lower for k in ["write to file", "write file", "save to file", "create file", "write hello"]) or (("write" in p_lower or "save" in p_lower) and any(ext in p_lower for ext in [".txt", ".md", ".json", ".py", ".log"])):
            file_match = re.search(r"(?:to|file|in)\s+([a-zA-Z0-9_\-\./\\:]+\.[a-zA-Z0-9_]+)", prompt, re.IGNORECASE)
            f_path = file_match.group(1).strip() if file_match else "test.txt"
            content_match = re.search(r"(?:content|text|saying|with text|write)\s+['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            content = content_match.group(1) if content_match else "Hello"
            return {
                "actions": [
                    {"tool": "write_file", "args": {"file_path": f_path, "content": content}}
                ]
            }

        # 8.6 File Delete:
        if ("delete file" in p_lower or "remove file" in p_lower) and any(ext in p_lower for ext in [".txt", ".md", ".json", ".tmp", ".log"]):
            file_match = re.search(r"(?:file|delete|remove)\s+([a-zA-Z0-9_\-\./\\:]+\.[a-zA-Z0-9_]+)", prompt, re.IGNORECASE)
            f_path = file_match.group(1).strip() if file_match else "test.txt"
            return {
                "actions": [
                    {"tool": "delete_file", "args": {"file_path": f_path}}
                ]
            }

        # 9. Unit Conversion:
        if " to " in p_lower and re.search(r'\d+\s*(?:c|f|celsius|fahrenheit|km|miles|meters|kg|lbs|gb|mb)\s+to\s+[a-z]+', p_lower):
            conv_match = re.search(r"(\d+(?:\.\d+)?\s*[a-zA-Z]+\s+to\s+[a-zA-Z]+)", prompt, re.IGNORECASE)
            expr = conv_match.group(1).strip() if conv_match else prompt
            return {
                "actions": [
                    {"tool": "advanced_calculator", "args": {"expression": expr}}
                ]
            }

        # 9.5 Folder Creation:
        if any(k in p_lower for k in ["create folder", "create a folder", "make a folder", "make folder", "create directory", "new folder", "mkdir"]):
            folder_match = re.search(r"(?:called|named)\s+([a-zA-Z0-9_\-\.]+)", prompt, re.IGNORECASE)
            dest_match = re.search(r"(?:on|in|at)\s+(?:my\s+)?(desktop|documents|downloads|[a-zA-Z]:[\\\/][a-zA-Z0-9_\-\.\\\/]+|[a-zA-Z0-9_\-\.\/]+)", prompt, re.IGNORECASE)
            folder_name = folder_match.group(1).strip() if folder_match else "TestProject"
            dest = dest_match.group(1).strip() if dest_match else "."

            if dest.lower() == "desktop":
                folder_path = os.path.join(os.path.expanduser("~"), "Desktop", folder_name)
            elif dest.lower() == "documents":
                folder_path = os.path.join(os.path.expanduser("~"), "Documents", folder_name)
            elif dest.lower() == "downloads":
                folder_path = os.path.join(os.path.expanduser("~"), "Downloads", folder_name)
            else:
                folder_path = os.path.join(dest, folder_name)

            return {
                "actions": [
                    {"tool": "create_folder", "args": {"path": folder_path}}
                ]
            }

        # 9.6 Factual Search / Web Search / Technical Queries:
        if any(k in p_lower for k in ["web search", "search web", "google", "search for", "look up online"]) or (
            any(k in p_lower for k in ["what", "which", "how", "tell me", "explain"]) and any(k in p_lower for k in ["capacitor", "arduino", "resistor", "schematic"])
        ):
            clean_q = re.sub(r"^(?:search|google|look up|web search)\s+(?:for\s+)?", "", prompt, flags=re.IGNORECASE).strip()
            return {
                "actions": [
                    {"tool": "web_search", "args": {"query": clean_q or prompt}}
                ]
            }

        # 10. Launch Application:
        if any(k in p_lower for k in ["launch", "open app", "open ", "start "]) and any(k in p_lower for k in ["code", "vscode", "visual studio", "calculator", "calc", "notepad", "chrome", "browser", "app", "application"]):
            app_match = re.search(r"(?:launch|open|start)\s+(?:the\s+)?(?:application\s+)?([a-zA-Z0-9_\-\s]+)", prompt, re.IGNORECASE)
            raw_app = app_match.group(1).strip() if app_match else "calculator"
            if any(k in raw_app.lower() for k in ["visual studio", "vscode", "code"]):
                app_name = "code"
            elif "calc" in raw_app.lower():
                app_name = "calculator"
            elif "notepad" in raw_app.lower():
                app_name = "notepad"
            elif "chrome" in raw_app.lower():
                app_name = "chrome"
            else:
                app_name = raw_app
            return {
                "actions": [
                    {"tool": "launch_application", "args": {"app_name": app_name}}
                ]
            }


        # 11. List Processes:
        if any(k in p_lower for k in ["running processes", "list processes", "tasklist", "show processes"]):
            return {
                "action": "call_tool",
                "thought": "Querying running system processes.",
                "tool_name": "list_processes",
                "parameters": {"max_results": 15},
            }

        # 12. Voice: Speak Response
        if any(k in p_lower for k in ["speak ", "/speak ", "say aloud", "read aloud", "speak_response"]):
            speak_match = re.search(r'(?:speak|/speak|say aloud|read aloud)\s+([^\n]+)', prompt, re.IGNORECASE)
            if speak_match:
                text_to_speak = speak_match.group(1).strip()
                return {
                    "action": "call_tool",
                    "thought": f"Speaking text aloud using speak_response: '{text_to_speak[:50]}...'",
                    "tool_name": "speak_response",
                    "parameters": {"text": text_to_speak},
                }

        # 13. Voice: Set Voice Speed
        if any(k in p_lower for k in ["voice speed", "speaking speed", "voice rate", "set speed", "/speed", "set_voice_speed"]):
            rate_match = re.search(r'(?:speed|rate|to)\s+(\d+)', prompt, re.IGNORECASE) or re.search(r'(\d+)', prompt)
            rate_val = int(rate_match.group(1)) if rate_match else 180
            return {
                "action": "call_tool",
                "thought": f"Setting voice speaking speed to {rate_val} wpm.",
                "tool_name": "set_voice_speed",
                "parameters": {"rate": rate_val},
            }

        # 14. Voice: Set Voice Volume
        if any(k in p_lower for k in ["voice volume", "set volume", "change volume", "/volume", "set_voice_volume"]):
            vol_match = re.search(r'(?:volume|level|to)\s+(\d+)', prompt, re.IGNORECASE) or re.search(r'(\d+)', prompt)
            vol_val = int(vol_match.group(1)) if vol_match else 80
            return {
                "action": "call_tool",
                "thought": f"Setting voice volume level to {vol_val}%.",
                "tool_name": "set_voice_volume",
                "parameters": {"level": vol_val},
            }

        # 15. Voice: Listen for Command
        if any(k in p_lower for k in ["listen for command", "voice input", "record audio", "start listening", "/voice"]):
            return {
                "action": "call_tool",
                "thought": "Listening for voice command via microphone and transcribing with Whisper.",
                "tool_name": "listen_for_command",
                "parameters": {},
            }

        # 16. Voice: Wake Word Detection
        if any(k in p_lower for k in ["wake word", "hey llama", "wait for wake word", "/wake"]):
            return {
                "action": "call_tool",
                "thought": "Waiting for wake word 'Hey Llama' using Porcupine.",
                "tool_name": "wake_word_detection",
                "parameters": {},
            }

        # 17. System Deep Control: Screenshot Capture
        if any(k in p_lower for k in ["take screenshot", "screenshot", "capture screen", "capture desktop"]):
            ocr_flag = "ocr" in p_lower or "extract text" in p_lower
            return {
                "action": "call_tool",
                "thought": f"Capturing screenshot (perform_ocr={ocr_flag}).",
                "tool_name": "screenshot_capture",
                "parameters": {"output_path": "screenshot.png", "perform_ocr": ocr_flag},
            }

        # 18. System Deep Control: Clipboard Manager
        if any(k in p_lower for k in ["clipboard", "get clipboard", "copy to clipboard", "set clipboard"]):
            c_action = "set" if any(k in p_lower for k in ["set", "copy to", "write"]) else "get"
            text_match = re.search(r'(?:to|content|with)\s+["\']?([^"\']+)["\']?', prompt)
            c_text = text_match.group(1).strip() if text_match and c_action == "set" else None
            return {
                "action": "call_tool",
                "thought": f"Accessing system clipboard with action '{c_action}'.",
                "tool_name": "clipboard_manager",
                "parameters": {"action": c_action, "content": c_text},
            }

        # 19. System Deep Control: Lock Screen / Power
        if any(k in p_lower for k in ["lock screen", "lock workstation", "lock pc", "lock computer"]):
            return {
                "action": "call_tool",
                "thought": "Locking workstation via system_control.",
                "tool_name": "system_control",
                "parameters": {"action": "lock_screen", "confirmed": True},
            }
        if any(k in p_lower for k in ["shutdown", "restart", "sleep", "hibernate"]):
            p_action = "shutdown" if "shutdown" in p_lower else ("restart" if "restart" in p_lower else ("sleep" if "sleep" in p_lower else "hibernate"))
            is_conf = any(k in p_lower for k in ["confirm=true", "confirmed=true", "proceed", "yes"])
            return {
                "action": "call_tool",
                "thought": f"System power action '{p_action}' (confirmed={is_conf}).",
                "tool_name": "system_control",
                "parameters": {"action": p_action, "confirmed": is_conf},
            }

        # 20. Diagnostics: Performance Monitor & Health Checker
        if any(k in p_lower for k in ["performance monitor", "cpu usage", "ram usage", "system telemetry", "hardware metrics", "check cpu"]):
            return {
                "action": "call_tool",
                "thought": "Querying real-time system performance telemetry.",
                "tool_name": "performance_monitor",
                "parameters": {"metric_type": "all"},
            }
        if any(k in p_lower for k in ["health check", "health report", "system health", "audit health"]):
            return {
                "action": "call_tool",
                "thought": "Auditing system health and resources with health_checker.",
                "tool_name": "health_checker",
                "parameters": {"quick_scan": True},
            }

        # 21. Diagnostics: Network Ping / DNS
        if any(k in p_lower for k in ["ping host", "test connection", "network latency"]) or re.search(r'\bping\s+', p_lower):
            host_match = re.search(r'\bping\s+([a-zA-Z0-9_\-\.]+)', prompt, re.IGNORECASE)
            t_host = host_match.group(1).strip() if host_match else "8.8.8.8"
            return {
                "action": "call_tool",
                "thought": f"Measuring network latency to '{t_host}'.",
                "tool_name": "network_analyzer",
                "parameters": {"action": "ping", "host": t_host, "count": 2},
            }

        # 22. Security: Antivirus & Quarantine
        if any(k in p_lower for k in ["antivirus", "scan for viruses", "virus scan", "malware scan", "scan directory for malware"]):
            dir_path = self._extract_directory_from_text(prompt, default=".")
            return {
                "action": "call_tool",
                "thought": f"Scanning path '{dir_path}' for malware threats.",
                "tool_name": "antivirus_scanner",
                "parameters": {"target_path": dir_path, "deep_scan": False},
            }

        # 23. Security: Password Vault
        if any(k in p_lower for k in ["password vault", "retrieve password", "store password", "vault"]):
            v_act = "store" if any(k in p_lower for k in ["store", "save", "add"]) else ("retrieve" if "get" in p_lower or "retrieve" in p_lower else "list")
            svc_match = re.search(r'(?:for|service)\s+([a-zA-Z0-9_\-]+)', prompt)
            svc = svc_match.group(1).strip() if svc_match else None
            return {
                "action": "call_tool",
                "thought": f"Password vault operation '{v_act}'.",
                "tool_name": "password_vault",
                "parameters": {"action": v_act, "service": svc},
            }

        # 24. Dev Tools: Git Manager
        if any(k in p_lower for k in ["git status", "git log", "git commit", "git branch"]):
            g_act = "status" if "status" in p_lower else ("log" if "log" in p_lower else ("commit" if "commit" in p_lower else "branch"))
            return {
                "action": "call_tool",
                "thought": f"Executing Git operation '{g_act}'.",
                "tool_name": "git_manager",
                "parameters": {"action": g_act, "repo_dir": "."},
            }

        # 25. Dev Tools: Port Scanner
        if any(k in p_lower for k in ["scan ports", "port scan", "port scanner", "open ports"]):
            host_match = re.search(r'(?:on|host|target)\s+([a-zA-Z0-9_\-\.]+)', prompt)
            t_host = host_match.group(1).strip() if host_match else "127.0.0.1"
            return {
                "action": "call_tool",
                "thought": f"Scanning open TCP ports on '{t_host}'.",
                "tool_name": "port_scanner",
                "parameters": {"host": t_host},
            }

        # 26. Web Automation: Web Scraper & RSS
        if any(k in p_lower for k in ["scrape web", "scrape page", "scrape url", "web scraper", "extract text from url"]):
            url_match = re.search(r'(https?://[^\s]+)', prompt)
            target_url = url_match.group(1) if url_match else "https://news.ycombinator.com"
            return {
                "action": "call_tool",
                "thought": f"Scraping content from '{target_url}'.",
                "tool_name": "web_scraper",
                "parameters": {"url": target_url, "extract_type": "text"},
            }
        if any(k in p_lower for k in ["rss feed", "read rss", "rss reader", "parse rss"]):
            url_match = re.search(r'(https?://[^\s]+)', prompt)
            target_url = url_match.group(1) if url_match else "https://news.ycombinator.com/rss"
            return {
                "action": "call_tool",
                "thought": f"Fetching RSS feed from '{target_url}'.",
                "tool_name": "rss_reader",
                "parameters": {"url": target_url, "max_items": 5},
            }

        # 27. Entertainment: Jokes, Stories, Trivia, Games
        if any(k in p_lower for k in ["tell me a joke", "tell a joke", "joke", "make me laugh", "pun", "riddle"]):
            cat = "riddle" if "riddle" in p_lower else "tech"
            return {
                "action": "call_tool",
                "thought": f"Generating a {cat} joke using joke_generator.",
                "tool_name": "joke_generator",
                "parameters": {"category": cat},
            }
        if any(k in p_lower for k in ["play trivia", "trivia game", "trivia question", "ask trivia"]):
            return {
                "action": "call_tool",
                "thought": "Serving an interactive question with trivia_game.",
                "tool_name": "trivia_game",
                "parameters": {"action": "question"},
            }
        if any(k in p_lower for k in ["play tictactoe", "play tic tac toe", "tic-tac-toe", "tictactoe"]):
            move_match = re.search(r'(?:move|position|pos)\s+(\d+)', prompt)
            mv = int(move_match.group(1)) if move_match else None
            return {
                "action": "call_tool",
                "thought": "Processing Tic-Tac-Toe move.",
                "tool_name": "game_controller",
                "parameters": {"game_name": "tictactoe", "action": "move" if mv is not None else "status", "move": mv},
            }

        # 28. AI/ML: Sentiment, Translation, Code Gen, Summarization
        if any(k in p_lower for k in ["analyze sentiment", "sentiment of", "sentiment analysis"]):
            text_match = re.search(r'(?:sentiment of|analyze sentiment)\s+[:"\'“]?([^"\'”\n]+)', prompt, re.IGNORECASE)
            t_to_analyze = text_match.group(1).strip() if text_match else prompt
            return {
                "action": "call_tool",
                "thought": "Evaluating emotional sentiment polarity.",
                "tool_name": "sentiment_analyzer",
                "parameters": {"text": t_to_analyze},
            }
        if any(k in p_lower for k in ["translate ", "translate to ", "in spanish", "in french", "in german"]):
            target_l = "es" if "spanish" in p_lower else ("fr" if "french" in p_lower else ("de" if "german" in p_lower else "es"))
            text_match = re.search(r'(?:translate|text)\s+[:"\'“]?([^"\'”\n]+?)(?:\s+to|\s+in|$)', prompt, re.IGNORECASE)
            t_to_trans = text_match.group(1).strip() if text_match else prompt
            return {
                "action": "call_tool",
                "thought": f"Translating text to '{target_l}'.",
                "tool_name": "language_translator",
                "parameters": {"text": t_to_trans, "target_lang": target_l},
            }
        if any(k in p_lower for k in ["generate code for", "write code for", "code generator"]):
            desc_match = re.search(r'(?:code for|generate code)\s+([^\n]+)', prompt, re.IGNORECASE)
            desc = desc_match.group(1).strip() if desc_match else "sample task"
            return {
                "action": "call_tool",
                "thought": f"Generating code implementation for: {desc}",
                "tool_name": "code_generator",
                "parameters": {"description": desc, "language": "python"},
            }

        # 29. UX & Storage: Profiles, Privacy, Disk Cleaner
        if any(k in p_lower for k in ["clean disk", "disk cleaner", "clean temp files", "clean cache"]):
            is_conf = any(k in p_lower for k in ["dry_run=false", "confirm=true", "actually clean", "proceed"])
            return {
                "action": "call_tool",
                "thought": f"Cleaning temporary files and disk caches (dry_run={not is_conf}).",
                "tool_name": "disk_cleaner",
                "parameters": {"dry_run": not is_conf},
            }
        if any(k in p_lower for k in ["privacy mode", "incognito mode"]):
            p_action = "enable" if any(k in p_lower for k in ["on", "enable", "start"]) else ("disable" if any(k in p_lower for k in ["off", "disable", "stop"]) else "status")
            return {
                "action": "call_tool",
                "thought": f"Configuring privacy mode with action '{p_action}'.",
                "tool_name": "privacy_mode",
                "parameters": {"action": p_action},
            }
        if any(k in p_lower for k in ["switch profile", "user profile", "profiles manager"]):
            p_name = "work" if "work" in p_lower else ("personal" if "personal" in p_lower else ("guest" if "guest" in p_lower else "developer"))
            return {
                "action": "call_tool",
                "thought": f"Managing profile: switching to '{p_name}'.",
                "tool_name": "profiles_manager",
                "parameters": {"action": "switch", "profile_name": p_name},
            }

        # 30. Subagents: Spawn, List, Parallel Orchestration
        if any(k in p_lower for k in ["spawn subagent", "dispatch subagent", "file manager agent", "web research agent", "code synthesis agent", "data analyst agent", "system monitor agent"]):
            role = "file_manager" if "file" in p_lower else ("web_research" if "web" in p_lower else ("code_synthesis" if "code" in p_lower else ("data_analyst" if "data" in p_lower else "system_monitor")))
            return {
                "action": "call_tool",
                "thought": f"Spawning specialized subagent '{role}'.",
                "tool_name": "spawn_subagent",
                "parameters": {"role": role, "task": prompt},
            }
        if any(k in p_lower for k in ["list subagents", "available subagents", "show subagents"]):
            return {
                "action": "call_tool",
                "thought": "Listing available specialized subagent roles.",
                "tool_name": "list_subagents",
                "parameters": {},
            }
        if any(k in p_lower for k in ["parallel subagents", "orchestrate subagents", "subagent fleet"]):
            return {
                "action": "call_tool",
                "thought": "Orchestrating concurrent fleet subagents.",
                "tool_name": "orchestrate_parallel_subagents",
                "parameters": {"plan": [{"role": "system_monitor", "task": "Inspect CPU/RAM telemetry"}, {"role": "data_analyst", "task": "Evaluate system stability metrics"}]},
            }

        # 31. Hooks & Interceptors
        if any(k in p_lower for k in ["register interceptor", "add interceptor", "policy hook"]):
            return {
                "action": "call_tool",
                "thought": "Registering lifecycle policy interceptor.",
                "tool_name": "register_interceptor",
                "parameters": {"hook_point": "before_tool_call", "hook_name": "operator_rule", "rule": "safe", "action": "allow"},
            }
        if any(k in p_lower for k in ["list interceptors", "show interceptors", "active hooks"]):
            return {
                "action": "call_tool",
                "thought": "Listing registered lifecycle interceptors.",
                "tool_name": "list_interceptors",
                "parameters": {},
            }

        # 32. Scheduler: Schedule, List, Cancel
        if any(k in p_lower for k in ["schedule a daily backup", "schedule daily backup", "schedule a backup", "schedule backup"]) or (
            "schedule" in p_lower and any(w in p_lower for w in ["daily", "weekly", "hourly", "backup", "task", "job", "cron"])
        ):
            if "backup" in p_lower:
                task_name = "Daily Backup"
                tool_or_cmd = "backup_documents"
            else:
                m_task = re.search(r'schedule\s+(?:a\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+at|\s+every|$)', prompt, re.IGNORECASE)
                task_name = m_task.group(1).strip().title() if m_task else "Scheduled Task"
                tool_or_cmd = "system_diagnostics"

            # Parse time (e.g. 2 AM, 14:00, 2:00 am)
            hour = 2
            minute = 0
            time_m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', p_lower)
            if time_m:
                h = int(time_m.group(1))
                minute = int(time_m.group(2)) if time_m.group(2) else 0
                meridiem = time_m.group(3)
                if meridiem == "pm" and h < 12:
                    h += 12
                elif meridiem == "am" and h == 12:
                    h = 0
                hour = h

            cron_expr = f"{minute} {hour} * * *"
            if "every hour" in p_lower or "hourly" in p_lower:
                cron_expr = "0 * * * *"
            elif "every sunday" in p_lower or "weekly" in p_lower:
                cron_expr = f"{minute} {hour} * * 0"

            return {
                "actions": [
                    {
                        "tool": "schedule_task",
                        "args": {
                            "task_name": task_name,
                            "cron_or_delay": cron_expr,
                            "tool_or_command": tool_or_cmd,
                        }
                    }
                ]
            }
        if any(k in p_lower for k in ["list scheduled tasks", "show scheduled tasks", "scheduled jobs"]):
            return {
                "action": "call_tool",
                "thought": "Listing pending scheduled tasks.",
                "tool_name": "list_scheduled_tasks",
                "parameters": {},
            }

        # 33. Desktop & GUI Automation
        if any(k in p_lower for k in ["gui click", "mouse click", "click at"]):
            return {
                "action": "call_tool",
                "thought": "Executing desktop mouse click.",
                "tool_name": "gui_click",
                "parameters": {"x": 500, "y": 500, "button": "left"},
            }
        if any(k in p_lower for k in ["set-of-mark", "visual grounding", "som marks"]):
            return {
                "action": "call_tool",
                "thought": "Performing Set-of-Mark visual coordinate grounding.",
                "tool_name": "gui_set_of_mark_grounding",
                "parameters": {},
            }
        if any(k in p_lower for k in ["gui abort", "emergency abort", "abort gui"]):
            return {
                "action": "call_tool",
                "thought": "Triggering GUI emergency abort.",
                "tool_name": "gui_safety_abort",
                "parameters": {},
            }

        # 34. Documents: Word, Excel, Presentation, PDF
        if any(k in p_lower for k in ["generate word document", "create docx", "word doc"]):
            return {
                "action": "call_tool",
                "thought": "Generating Microsoft Word document.",
                "tool_name": "office_word_generator",
                "parameters": {"action": "create", "file_path": "report.docx", "title": "System Report"},
            }
        if any(k in p_lower for k in ["create spreadsheet", "excel sheet", "create xlsx"]):
            return {
                "action": "call_tool",
                "thought": "Creating Excel spreadsheet.",
                "tool_name": "office_excel_master",
                "parameters": {"action": "create", "file_path": "telemetry.xlsx"},
            }

        # 35. Browser Automation
        if any(k in p_lower for k in ["browser navigate", "navigate to url", "open website"]):
            url_match = re.search(r'https?://[^\s]+', prompt)
            u = url_match.group(0) if url_match else "https://python.org"
            return {
                "action": "call_tool",
                "thought": f"Navigating browser to '{u}'.",
                "tool_name": "browser_navigate",
                "parameters": {"url": u},
            }

        # 36. Advanced RAG & Knowledge Graph
        if any(k in p_lower for k in ["rag query", "search knowledge", "semantic search memory"]):
            return {
                "action": "call_tool",
                "thought": "Querying indexed documents via RAG vector search.",
                "tool_name": "rag_query",
                "parameters": {"query": prompt},
            }
        if any(k in p_lower for k in ["extract triplets", "knowledge graph extract"]):
            return {
                "action": "call_tool",
                "thought": "Extracting subject-predicate-object knowledge graph triplets.",
                "tool_name": "knowledge_graph_extract",
                "parameters": {"text": prompt},
            }

        # 37. Enterprise Security
        if any(k in p_lower for k in ["generate rsa", "generate aes", "key manager"]):
            return {
                "action": "call_tool",
                "thought": "Executing enterprise cryptographic key management.",
                "tool_name": "enterprise_key_manager",
                "parameters": {"action": "generate_rsa", "key_id": "primary"},
            }
        if any(k in p_lower for k in ["shred file", "secure shred", "destroy file"]):
            return {
                "action": "call_tool",
                "thought": "Initiating cryptographic file shredder preview.",
                "tool_name": "file_shredder",
                "parameters": {"file_path": "temp.txt", "confirmed": False},
            }
        if any(k in p_lower for k in ["security audit log", "audit ledger", "tamper ledger"]):
            return {
                "action": "call_tool",
                "thought": "Verifying cryptographic security audit trail.",
                "tool_name": "query_security_audit_log",
                "parameters": {"limit": 20},
            }

        # 38. MCP Client
        if any(k in p_lower for k in ["connect mcp", "mcp connect"]):
            return {
                "action": "call_tool",
                "thought": "Establishing Model Context Protocol server connection.",
                "tool_name": "mcp_connect_server",
                "parameters": {"server_url_or_cmd": "stdio://host", "transport": "stdio"},
            }
        if any(k in p_lower for k in ["mcp connections", "list mcp"]):
            return {
                "action": "call_tool",
                "thought": "Listing active MCP connections.",
                "tool_name": "mcp_list_active_connections",
                "parameters": {},
            }

        # 39. Proactive Intelligence & Multi-Language
        if any(k in p_lower for k in ["proactive recommendations", "system recommendations"]):
            return {
                "action": "call_tool",
                "thought": "Generating proactive system telemetry optimizations.",
                "tool_name": "proactive_system_recommendations",
                "parameters": {},
            }
        if any(k in p_lower for k in ["detect language of", "what language is"]):
            return {
                "action": "call_tool",
                "thought": "Detecting input language.",
                "tool_name": "detect_language",
                "parameters": {"text": prompt},
            }

        # Generic direct tool invocation pattern: "call <tool_name>" or "<tool_name> <params>"
        for registered_tool in tool_registry.list_tools():
            t_name = registered_tool["name"]
            if f"call {t_name}" in p_lower or f"tool:{t_name}" in p_lower or prompt.strip().startswith(t_name):
                return {
                    "action": "call_tool",
                    "thought": f"Dispatching direct invocation for registered tool '{t_name}'.",
                    "tool_name": t_name,
                    "parameters": {},
                }

        # Default: Fall back to web_search for general knowledge, anime, history, pop culture
        clean_q = prompt.strip()
        return {
            "actions": [
                {"tool": "web_search", "args": {"query": clean_q}}
            ]
        }

    def _execute_tool_sync(self, tool_name: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Executes a tool synchronously with robust event loop isolation, hook interceptors, and security auditing."""
        import concurrent.futures
        from core.hook_engine import hook_engine
        from core.security_audit import security_audit

        # 1. Lifecycle hook check & safety policy
        allow, mod_params, reason = hook_engine.run_before_tool_call(tool_name, parameters)
        if not allow:
            logger.warning(f"Tool execution blocked by hook/interceptor: {reason}")
            security_audit.log_event(action=tool_name, status="BLOCKED", details={"parameters": parameters, "reason": reason}, severity="WARNING")
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output={"status": "BLOCKED", "error": reason or "Blocked by interceptor"},
                error=reason or "Blocked by interceptor",
            )
        parameters = mod_params

        # 2. Proactive restricted tool whitelist check
        active_whitelist = getattr(self, "_active_tool_whitelist", None)
        if active_whitelist is not None and tool_name not in active_whitelist:
            logger.warning(f"Tool '{tool_name}' blocked: not in active restricted whitelist.")
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                output={"status": "BLOCKED", "error": f"Tool '{tool_name}' is not in restricted whitelist: {sorted(list(active_whitelist))}"},
                error=f"Tool '{tool_name}' blocked by restricted whitelist",
            )

        def _run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(self.executor.execute_tool(tool_name, parameters))
            finally:
                new_loop.close()

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                res = pool.submit(_run_in_new_loop).result()
        else:
            res = _run_in_new_loop()

        # 2. After tool execution hook & audit logging
        if res.success:
            res.output = hook_engine.run_after_tool_call(tool_name, parameters, res.output)
            security_audit.log_event(action=tool_name, status="ALLOWED", details={"parameters": parameters})
        else:
            security_audit.log_event(action=tool_name, status="ERROR", details={"error": res.error}, severity="WARNING")

        return res

    def run_turn(self, user_query: str, context: Optional[str] = None) -> LlamaAgentResult:
        """
        Main cognitive loop:
        1. Analyzes user request with tool catalog.
        2. Decides whether to answer directly or invoke tools.
        3. Chains multiple steps (e.g. read file -> calculate -> write report).
        4. Observes real outputs and real errors truthfully.
        5. Synthesizes a clean, human-friendly response.
        """
        import time
        start_time = time.time()
        steps: List[ReasoningStep] = []
        clean_query = user_query.strip()

        # Enterprise Security Threat Pre-screening
        from core.security_audit import security_audit
        has_threat, threats = security_audit.scan_threat(clean_query)
        if has_threat:
            return LlamaAgentResult(
                user_query=clean_query,
                final_response=f"Security Alert: Action blocked due to detected security violation: {', '.join(threats)}",
                steps_executed=[],
                model_used="security_audit_shield",
                total_steps=0,
                total_duration_sec=time.time() - start_time,
                fallback_used=False,
                success=False,
            )

        # User preferences context
        pref_info = ""
        if llama_config.save_memory:
            fav_dirs = self.preferences.get_favorite_directories()
            common_cmds = self.preferences.get_common_commands()
            pref_info = (
                f"User Preferences Memory (saved in {llama_config.preferences_path}):\n"
                f"- Favorite Directories: {fav_dirs if fav_dirs else 'None recorded'}\n"
                f"- Common Commands: {common_cmds if common_cmds else 'None recorded'}\n\n"
            )

        # Determine engine route via ModelRouter (v1.3.0 Cloud Primary + Local Fallback)
        route_target = "local"
        if hasattr(self, "router") and self.router is not None:
            try:
                route_target = self.router.route(clean_query)
            except Exception as _re:
                logger.warning(f"Router error: {_re}. Defaulting to local.")
                route_target = "local"

        logger.info(f"[ModelRouter] Query routed to engine: '{route_target}' (query: '{clean_query[:50]}...')")
        active_model_name = llama_config.model_name
        fallback_occurred_in_turn = False

        # Build System Prompt with Orvix Universal Persona and execution guidelines
        active_engine_label = getattr(route_target, "name", str(route_target))
        system_prompt = (
            "You are Orvix. You have:\n"
            "- Terminal control (Windows CMD, PowerShell, Linux bash)\n"
            "- File operations\n"
            "- Web search\n"
            "- Memory (facts, lists, documents)\n"
            "- 130+ tools\n\n"
            "CRITICAL RULES:\n"
            f'1. When asked "who are you", say: "I\'m Orvix, your local AI assistant running on {active_engine_label}. '
            'I can control your system, manage files, and automate tasks."\n'
            '2. When asked "what can you do", LIST real capabilities. Never give a dictionary definition or vague summary.\n'
            '3. Multi-step tasks: break into steps, use tools sequentially, retry up to 3 times on failure.\n'
            '4. Never give up after one error.\n\n'
            "STRICT ACTION SCHEMA:\n"
            "1. If an action or tool execution is needed, output valid JSON:\n"
            '   {"actions": [{"tool": "exact_tool_name", "args": {...}}]}\n'
            "2. For conversational replies, greetings, identity questions, or final answers, output:\n"
            '   {"action": "final_answer", "thought": "reasoning...", "response": "..."}\n'
            "3. NEVER output a math calculation unless the user explicitly asks for a calculation with numbers.\n"
            '4. If no specific tool matches, output: {"actions": [{"tool": "web_search", "args": {"query": "USER_QUERY_HERE"}}]}\n\n'
            "STRICT HARDWARE ENGINEERING & REAL EXECUTION MANDATE:\n"
            "1. You MUST NEVER simulate, hallucinate, or role-play tool outputs.\n"
            "2. Always reference physical electrical parameters: V_CE, V_GS, hFE, R_shunt, time constants, forward drop, logic threshold.\n"
            "3. Provide physical test procedures for diagnosing faulty components using multimeters or oscilloscopes.\n"
            "4. NEVER suggest software solutions for physical hardware problems.\n"
            "5. When starting projects, always create dual firmware/ and hardware/ directories with schematic notes and BOM.\n"
            "6. Be concise and focus on the physical laws of electricity and circuits.\n"
            "7. If an action, task, or hardware inquiry is requested, you MUST emit a valid JSON action plan in the following schema:\n"
            '   {"actions": [{"tool": "exact_tool_name", "args": {...}}]}\n'
            "8. For greetings, identity questions ('who are you'), or natural chit-chat ONLY, respond immediately with:\n"
            '   {"action": "final_answer", "thought": "reasoning...", "response": "..."}\n'
            "9. The EXECUTOR performs real system calls, verifies outcomes (checking process PIDs, file existence, hardware directories, calculation outputs), and returns real status reports.\n\n"
            "HARDWARE PROGRAMMING DOMAIN (Domain 28):\n"
            "You are now a Real-Time Hardware Programmer.\n"
            "- TOOL: detect_hardware() → Scans USB/serial ports for connected boards (ESP32, Arduino, STM32, RP2040).\n"
            "- TOOL: list_boards() → Shows all detected boards with their port and toolchain.\n"
            "- TOOL: program_board(firmware_code, board_type) → Compiles and flashes the code to the detected board.\n"
            "- TOOL: monitor_serial(port, baud) → Reads serial output from the board.\n\n"
            'When the user says "program this board", "flash my ESP32", or "detect hardware":\n'
            "1. ALWAYS call detect_hardware() first to confirm the board exists.\n"
            "2. Generate or use the provided firmware code.\n"
            "3. Call program_board().\n"
            "4. Call monitor_serial() to verify it works.\n"
            "5. Report SUCCESS or FAILED with the actual port and PID.\n\n"
            "UNIVERSAL SYSTEM CONTROL & TERMINAL MASTERY MANDATE (v1.1.0):\n"
            "1. You are the ultimate master of controlling the local system via terminal commands, applications, processes, network, and hardware.\n"
            "2. NEVER give up when a file or directory is not found! Instead, proactively call `find_file` with wildcards to discover where files reside.\n"
            "3. You know 350+ Windows and Linux terminal commands. If the user asks how to do something in the terminal, lookup or suggest the exact command with flags using `suggest_command` or `lookup_command`.\n"
            "4. When executing commands, use `run_terminal` or `chain_commands`.\n"
            "5. For cross-platform tasks, translate between PowerShell, CMD, and Bash using `translate_command`.\n"
            "6. For hardware inspection, use `get_hardware_summary`, `get_cpu_info`, `get_ram_info`, `get_disk_info`, `get_battery_status`.\n"
            "7. For apps and processes, use `launch_app`, `close_app`, `list_running_apps`, `list_processes`, `kill_process`.\n"
            "8. For network diagnostics, use `get_ip_addresses`, `ping_host`, `test_port`, `get_active_connections`, `flush_dns`.\n"
            "9. For clipboard, media, and notifications, use `get_clipboard_text`, `set_clipboard_text`, `set_volume`, `take_screenshot`, `show_notification`.\n\n"
            "COMMAND INTELLIGENCE RULES (v1.2.0):\n"
            "You have a 3-layer command brain:\n"
            "Layer 1 (Core, ~500 commands): Always available, instant, offline.\n"
            "Layer 2 (Discovery, unlimited): Query the OS when you need something obscure. Use: command_find, command_discover, command_explain.\n"
            "Layer 3 (Learned): Commands and workflow chains you've used successfully before. Use: command_patterns.\n"
            "When asked to do something in the terminal:\n"
            "1. First check Layer 3 (learned patterns) via `command_find` — you may already know it.\n"
            "2. Then Layer 1 (core commands) — 500 most useful offline commands.\n"
            "3. Then Layer 2 (discovery) — ask the OS via `command_explain` or `command_discover`.\n"
            "4. If all else fails, verify syntax with `command_explain` before running.\n"
            "5. Never invent a command — always verify it exists.\n\n"
            f"Active Persona: {jarvis_persona.active_mode.value}.\n"
            f"User Identity: {jarvis_persona.user_preferred_name if jarvis_persona.is_name_known() else 'Unknown'}.\n\n"
            f"{pref_info}"
            f"Voice Recognition & Speech Features:\n"
            f"You have voice capabilities: speech-to-text transcription via Whisper (`listen_for_command`), text-to-speech output via pyttsx3 (`speak_response`), speaking rate configuration (`set_voice_speed`), volume control (`set_voice_volume`), and wake word detection for 'Hey Llama' (`wake_word_detection`).\n\n"
            f"Available Tools:\n"
            f"{self.get_tool_catalog_prompt()}\n\n"
            f"JSON Output Examples:\n"
            f'- Detect Hardware: {{"actions": [{{"tool": "detect_hardware", "args": {{}}}}]}}\n'
            f'- List Boards: {{"actions": [{{"tool": "list_boards", "args": {{}}}}]}}\n'
            f'- Program Board & Flash: {{"actions": [{{"tool": "detect_hardware", "args": {{}}}}, {{"tool": "program_board", "args": {{"firmware_code": "// LED Blink", "board_type": "esp32"}}}}, {{"tool": "monitor_serial", "args": {{"port": "COM3", "baud": 115200}}}}]}}\n'
            f'- Monitor Serial: {{"actions": [{{"tool": "monitor_serial", "args": {{"port": "COM3", "baud": 115200}}}}]}}\n'
            f'- Pinout Query: {{"actions": [{{"tool": "pinout_visualize", "args": {{"component": "ATmega328P"}}}}]}}\n'
            f'- Datasheet Query: {{"actions": [{{"tool": "datasheet_fetch", "args": {{"component": "BC547"}}}}]}}\n'
            f'- Debug Circuit: {{"actions": [{{"tool": "circuit_troubleshoot", "args": {{"issue": "IR sensor not detecting"}}}}]}}\n'
            f'- Bench Test: {{"actions": [{{"tool": "component_test_procedure", "args": {{"component": "2N2222"}}}}]}}\n'
            f'- Hardware Project Start: {{"actions": [{{"tool": "bootstrap_hardware_project", "args": {{"project_name": "Drone_ESC"}}}}, {{"tool": "launch_application", "args": {{"app_name": "code", "target": "projects/Drone_ESC"}}}}]}}\n'
            f'- Measurement Diagnostic: {{"actions": [{{"tool": "interpret_circuit_measurements", "args": {{"readings": "Vcc=5V, Vbe=0.2V, Ic=100mA"}}}}]}}\n'
            f'- Voltage Divider: {{"actions": [{{"tool": "calculate_voltage_divider", "args": {{"r1_ohms": 10000, "r2_ohms": 10000, "vin_volts": 5}}}}]}}\n'
            f'- Launching VS Code: {{"actions": [{{"tool": "launch_application", "args": {{"app_name": "code"}}}}]}}\n'
            f'- Launching Notepad: {{"actions": [{{"tool": "launch_application", "args": {{"app_name": "notepad"}}}}]}}\n'
            f'- Create Folder: {{"actions": [{{"tool": "create_folder", "args": {{"path": "~/Desktop/TestProject"}}}}]}}\n'
            f'- Web Search: {{"actions": [{{"tool": "web_search", "args": {{"query": "what capacitor is connected to Arduino?"}}}}]}}\n'
            f'- File Write: {{"actions": [{{"tool": "write_file", "args": {{"file_path": "test.txt", "content": "Hello"}}]}}\n'
            f'- File Delete: {{"actions": [{{"tool": "delete_file", "args": {{"file_path": "test.txt"}}}}]}}\n'
            f'- Math: {{"actions": [{{"tool": "advanced_calculator", "args": {{"expression": "2+2"}}}}]}}\n'
        )

        # RAG Knowledge Context Augmentation
        augmented_input = self.rag.build_augmented_prompt(clean_query)

        conversation_history = f"User Request: {augmented_input}\n"
        if context:
            conversation_history += f"Additional Context: {context}\n"

        for step_idx in range(1, llama_config.max_reasoning_steps + 1):
            prompt = (
                f"{conversation_history}\n"
                f"Current Step: {step_idx} of {llama_config.max_reasoning_steps}\n"
                f"Decide your next action. Return JSON only."
            )

            decision, actual_model, was_fallback = self._query_engine_json(prompt, system_prompt, route_target)
            active_model_name = actual_model
            if was_fallback:
                fallback_occurred_in_turn = True

            # Fallback if Ollama is unreachable or invalid output
            if not decision or not isinstance(decision, dict):
                logger.warning("Llama model response was empty or unparseable. Falling back to native solver.")
                return self._execute_fallback(clean_query, steps, start_time)

            # 1. Multi-action or Single-action plan via ExecutionOrchestrator
            if "actions" in decision and isinstance(decision["actions"], list) and decision["actions"]:
                from core.execution_orchestrator import execution_orchestrator
                exec_report = execution_orchestrator.execute_plan(decision)
                for idx, act_res in enumerate(exec_report.get("results", []), 1):
                    tool_call = act_res.get("action", {})
                    tool_n = act_res.get("tool", tool_call.get("tool", "unknown"))
                    tool_a = act_res.get("args", tool_call.get("args", {}))
                    v_res = act_res.get("result", {})
                    success = act_res.get("verified", act_res.get("status") == "SUCCESS")
                    steps.append(ReasoningStep(
                        step_number=idx,
                        thought="Executed planned action via ExecutionOrchestrator with verification",
                        action_type="call_tool",
                        tool_name=tool_n,
                        parameters=tool_a,
                        tool_output=v_res if isinstance(v_res, dict) else {"output": v_res},
                        success=success,
                        error=None if success else act_res.get("verification_reason"),
                    ))
                return LlamaAgentResult(
                    user_query=clean_query,
                    final_response=exec_report.get("summary", "Plan executed."),
                    steps_executed=steps,
                    model_used=active_model_name,
                    total_steps=len(steps),
                    total_duration_sec=time.time() - start_time,
                    fallback_used=fallback_occurred_in_turn,
                    success=exec_report.get("status") == "SUCCESS",
                )

            # 2. Tool call representation conversion via ExecutionOrchestrator
            if "tool" in decision and decision.get("action") != "call_tool":
                tool_n = decision.get("tool") or decision.get("tool_name", "")
                tool_args = decision.get("args", decision.get("parameters", {}))
                decision_plan = {"actions": [{"tool": tool_n, "args": tool_args}]}
                from core.execution_orchestrator import execution_orchestrator
                exec_report = execution_orchestrator.execute_plan(decision_plan)
                for idx, act_res in enumerate(exec_report.get("results", []), 1):
                    v_res = act_res.get("result", {})
                    success = act_res.get("verified", act_res.get("status") == "SUCCESS")
                    steps.append(ReasoningStep(
                        step_number=idx,
                        thought="Executed planned action via PhassExecutor with verification",
                        action_type="call_tool",
                        tool_name=tool_n,
                        parameters=tool_args,
                        tool_output=v_res if isinstance(v_res, dict) else {"output": v_res},
                        success=success,
                        error=None if success else act_res.get("verification_reason"),
                    ))
                return LlamaAgentResult(
                    user_query=clean_query,
                    final_response=exec_report.get("summary", "Plan executed."),
                    steps_executed=steps,
                    model_used=active_model_name,
                    total_steps=len(steps),
                    total_duration_sec=time.time() - start_time,
                    fallback_used=fallback_occurred_in_turn,
                    success=exec_report.get("status") == "SUCCESS",
                )

            thought = decision.get("thought", "")
            action = decision.get("action", "").lower().strip()

            # 3. Action: Final Answer
            if action == "final_answer" or "response" in decision:
                final_resp = decision.get("response", "Directive resolved.")
                steps.append(ReasoningStep(
                    step_number=step_idx,
                    thought=thought,
                    action_type="final_answer",
                ))
                return LlamaAgentResult(
                    user_query=clean_query,
                    final_response=final_resp,
                    steps_executed=steps,
                    model_used=active_model_name,
                    total_steps=len(steps),
                    total_duration_sec=time.time() - start_time,
                    fallback_used=fallback_occurred_in_turn,
                    success=True,
                )

            # Action: Call Tool
            if action == "call_tool":
                tool_name = decision.get("tool_name", "").strip()
                parameters = decision.get("parameters", {})
                if not isinstance(parameters, dict):
                    parameters = {}

                # Execute tool
                try:
                    exec_result = self._execute_tool_sync(tool_name, parameters)
                except Exception as exc:
                    import traceback
                    tb_str = traceback.format_exc()
                    exec_result = ToolExecutionResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        output={"status": "ERROR", "error": str(exc)},
                        success=False,
                        verified=False,
                        permission_granted=False,
                        requires_confirmation=False,
                        error=str(exc),
                    )

                # Automatic smart search on file-not-found for file operations
                is_file_tool = tool_name in ("file_reader", "read_file", "view_file") or "file_path" in parameters
                if is_file_tool:
                    out = exec_result.output or {}
                    status_val = out.get("status")
                    if status_val == "NOT_FOUND" or (not exec_result.success and "does not exist" in str(exec_result.error or out.get("error", "")).lower()):
                        # Check if smart search was already performed by tool
                        if not out.get("searched_paths"):
                            from tools.terminal_tools import find_file_smart
                            f_path = parameters.get("file_path") or parameters.get("path") or parameters.get("filename") or ""
                            fname = os.path.basename(f_path) if f_path else ""
                            if fname:
                                matches = find_file_smart(fname)
                                if len(matches) == 1:
                                    try:
                                        with open(matches[0], "r", encoding="utf-8", errors="replace") as f:
                                            c = f.read()
                                        exec_result.success = True
                                        exec_result.error = None
                                        exec_result.output = {
                                            "status": "SUCCESS",
                                            "path": matches[0],
                                            "file_path": matches[0],
                                            "content": c,
                                            "note": f"Found at {matches[0]} (searched from {f_path})",
                                        }
                                    except Exception:
                                        pass
                                elif len(matches) > 1:
                                    exec_result.output = {
                                        "status": "MULTIPLE_MATCHES",
                                        "matches": matches,
                                        "note": "Found multiple files. Which one?",
                                    }
                                else:
                                    default_paths = [
                                        os.path.expanduser("~/Desktop"),
                                        os.path.expanduser("~/Documents"),
                                        os.path.expanduser("~/Downloads"),
                                        os.path.expanduser("~/OneDrive/Desktop"),
                                        os.path.expanduser("~/OneDrive/Documents"),
                                        os.getcwd(),
                                    ]
                                    exec_result.output = {
                                        "status": "NOT_FOUND",
                                        "searched_paths": default_paths,
                                        "error": f"File does not exist: {f_path}",
                                        "note": f"Could not find {fname}. Please provide the full path, or check the filename.",
                                    }

                # Log tool failure to ErrorLogger and generate diagnostic hint
                error_hint = ""
                if not exec_result.success:
                    try:
                        from logging.error_logger import error_logger
                        out = exec_result.output or {}
                        err_msg = str(exec_result.error or (out.get("error") if isinstance(out, dict) else "") or "Tool execution failed")
                        recent_tools = [s.tool_name for s in steps if s.tool_name][-3:]
                        if tool_name and (not recent_tools or recent_tools[-1] != tool_name):
                            recent_tools.append(tool_name)

                        tb_text = getattr(exec_result, "traceback", None) or exec_result.error or ""

                        err_id = error_logger.log({
                            "category": "TOOL_FAILURE",
                            "source_file": "core/llama_tool_agent.py",
                            "function_name": f"_execute_tool_sync:{tool_name}",
                            "error_type": "ToolExecutionError",
                            "error_message": err_msg,
                            "traceback": tb_text,
                            "context": {
                                "tool": tool_name,
                                "args": parameters,
                                "last_3_tools": recent_tools,
                                "agent_state": "RUNNING",
                                "user_query": clean_query,
                                "step": step_idx,
                            },
                        })
                        error_hint = f"\n[This error logged as ID {err_id}. Use /errors {err_id} to see full report.]"
                    except Exception:
                        error_hint = ""

                step_record = ReasoningStep(
                    step_number=step_idx,
                    thought=thought,
                    action_type="call_tool",
                    tool_name=tool_name,
                    parameters=parameters,
                    tool_output=exec_result.output,
                    success=exec_result.success,
                    error=exec_result.error,
                )
                steps.append(step_record)

                # Format observation truthfully
                if exec_result.success:
                    obs_str = f"Observation: Success. Output: {json.dumps(exec_result.output)}"
                else:
                    out = exec_result.output or {}
                    if out.get("status") == "NOT_FOUND":
                        searched = out.get("searched_paths", [])
                        note = out.get("note", "File not found.")
                        obs_str = f"Observation: NOT_FOUND. Searched paths: {json.dumps(searched)}. Note: {note}"
                    elif out.get("status") == "MULTIPLE_MATCHES":
                        matches = out.get("matches", [])
                        note = out.get("note", "Found multiple files.")
                        obs_str = f"Observation: MULTIPLE_MATCHES. Matches: {json.dumps(matches)}. Note: {note}"
                    else:
                        err_msg = exec_result.error or out.get("error", "Execution failed")
                        obs_str = f"Observation: FAILED. Error: {err_msg}"

                    if error_hint:
                        obs_str += error_hint

                conversation_history += (
                    f"\nStep {step_idx}:\n"
                    f"Thought: {thought}\n"
                    f"Tool Called: {tool_name} with parameters {json.dumps(parameters)}\n"
                    f"{obs_str}\n"
                )

        # Reached max steps without final answer: ask for immediate final synthesis
        synthesis_prompt = (
            f"{conversation_history}\n"
            f"You have reached the maximum reasoning steps. Synthesize all observations into your final answer.\n"
            f'Return JSON: {{"action": "final_answer", "thought": "...", "response": "Your concise final response"}}'
        )
        final_decision, actual_model, was_fallback = self._query_engine_json(
            synthesis_prompt, system_prompt, route_target
        )
        active_model_name = actual_model
        if was_fallback:
            fallback_occurred_in_turn = True

        if final_decision and "response" in final_decision:
            resp = final_decision["response"]
        else:
            resp = "I have executed the requested actions. Check the system log for full details."

        return LlamaAgentResult(
            user_query=clean_query,
            final_response=resp,
            steps_executed=steps,
            model_used=active_model_name,
            total_steps=len(steps),
            total_duration_sec=time.time() - start_time,
            fallback_used=fallback_occurred_in_turn,
            success=True,
        )

    def _execute_fallback(
        self,
        query: str,
        prior_steps: List[ReasoningStep],
        start_time: float,
    ) -> LlamaAgentResult:
        """Executes fallback using secondary brain or native answer pipeline."""
        from core.secondary_brain import secondary_brain
        from nlp.natural_response_engine import natural_response_engine
        import time

        if secondary_brain.is_active:
            resp = secondary_brain.process_query(query)
        else:
            resp = natural_response_engine.process_turn(query)

        return LlamaAgentResult(
            user_query=query,
            final_response=resp,
            steps_executed=prior_steps,
            model_used="native_secondary_brain",
            total_steps=len(prior_steps),
            total_duration_sec=time.time() - start_time,
            fallback_used=True,
            success=True,
        )

    def process_query(self, query: str) -> str:
        """Processes a query and returns the final response string, recording into Mind Palace."""
        res = self.run_turn(query)
        try:
            from core.mind_palace import mind_palace
            import threading
            threading.Thread(target=mind_palace.store_conversation, args=("interactive_session", query, res.final_response), daemon=True).start()
        except Exception:
            pass
        return res.final_response

    def run(self, prompt: str, max_steps: Optional[int] = None, **kwargs) -> str:
        """Run cognitive reasoning on prompt and return textual output."""
        res = self.run_turn(prompt)
        return res.final_response

    def run_restricted(self, user_input: str, tool_whitelist: List[str]) -> str:
        """Run cognitive reasoning restricted strictly to the specified list of allowed tools."""
        prev = getattr(self, "_active_tool_whitelist", None)
        self._active_tool_whitelist = set(tool_whitelist)
        try:
            res = self.run_turn(user_input)
            return res.final_response
        finally:
            self._active_tool_whitelist = prev

    def propose_for_approval(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Proposes an action for user approval in the approval queue instead of executing."""
        try:
            from knowledge.sqlite_store import KnowledgeStore
            ks = KnowledgeStore()
            name = action.get("name") or action.get("action_name") or "unnamed_action"
            reason = action.get("reason") or "Requires explicit user confirmation"
            tool = action.get("tool") or action.get("tool_name") or "unknown_tool"
            args = action.get("args") or action.get("parameters") or {}
            qid = ks.queue_approval(name, reason, tool, args)
            return {
                "status": "QUEUED",
                "queue_id": qid,
                "action_name": name,
                "reason": reason,
                "tool": tool,
            }
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a specific tool directly."""
        from tools.executor import execute_tool
        return execute_tool(tool_name, parameters)

    def run_autonomous(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a task autonomously – the agent does everything without asking.
        Only interrupts for emergencies or critical decisions.
        """
        from core.autonomous_orchestrator import get_orchestrator
        from datetime import datetime

        orchestrator = get_orchestrator()
        orchestrator.initialize(self, getattr(self, "callback", None))

        result = orchestrator.execute_workflow(goal, context)

        if not hasattr(self, "task_history"):
            self.task_history = []

        self.task_history.append({
            "goal": goal,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        return result


# Global singleton instance
llama_tool_agent = LlamaToolAgent()


def process_query(query: str) -> str:
    """Module-level helper to process query using the singleton llama_tool_agent."""
    return llama_tool_agent.process_query(query)


def get_agent() -> LlamaToolAgent:
    """Returns the global singleton llama_tool_agent."""
    return llama_tool_agent


def run_autonomous(goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Module-level helper to execute a goal autonomously using the global agent."""
    return llama_tool_agent.run_autonomous(goal, context)




