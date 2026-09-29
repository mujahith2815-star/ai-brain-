"""
Fix Generator Engine for P.H.A.S.S Autonomic Recovery Circuit.
Extracts error context, constructs AI remediation prompts for Llama/Phi-4,
synthesizes deterministic and cognitive patches, and enforces the 70% confidence safety valve.
"""

from __future__ import annotations
import ast
import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from core.error_analyzer import AnalyzedError

logger = logging.getLogger("phass.core.fix_generator")


@dataclass
class GeneratedFix:
    target_file: str
    target_line: Optional[int]
    error_type: str
    error_msg: str
    fix_type: str
    repaired_code: str
    original_code: str
    confidence: float
    escalate_to_user: bool
    status: str  # "READY_FOR_SANDBOX", "NEEDS_USER_REVIEW", "FAILED"
    explanation: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "target_line": self.target_line,
            "error_type": self.error_type,
            "error_msg": self.error_msg,
            "fix_type": self.fix_type,
            "confidence": round(self.confidence, 2),
            "escalate_to_user": self.escalate_to_user,
            "status": self.status,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


class FixGenerator:
    """
    Generates targeted code repairs using cached solutions, heuristic patterns,
    or cognitive LLM reasoning with strict confidence gating.
    """

    CONFIDENCE_THRESHOLD = 0.70  # Safety Valve: < 70% escalates to user

    def __init__(self, ollama_endpoint: str = "http://127.0.0.1:11434"):
        self.ollama_endpoint = ollama_endpoint

    def construct_llm_prompt(self, analyzed_error: AnalyzedError, file_content: str) -> str:
        """Constructs prompt for local LLM (Llama) or secondary brain (Phi-4)."""
        fname = Path(analyzed_error.file_path).name if analyzed_error.file_path else "module.py"
        line_no = analyzed_error.line_number or "unknown"
        return (
            f"You are an autonomic Python code repair agent. "
            f"Fix the following error in [{fname}] at line [{line_no}]: [{analyzed_error.error_msg}]. "
            f"Provide only the complete, corrected Python file content without any markdown or conversational filler."
        )

    def _query_local_llm(self, prompt: str, timeout: float = 2.0) -> Optional[str]:
        """Queries local Ollama endpoint if available."""
        try:
            from config.llama_config import llama_config
            payload = {
                "model": llama_config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            }
            req = urllib.request.Request(
                f"{self.ollama_endpoint}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    ans = data.get("response", "").strip()
                    # Clean markdown wrappers if returned
                    ans = re.sub(r"^```python\s*", "", ans, flags=re.IGNORECASE)
                    ans = re.sub(r"```$", "", ans.strip())
                    return ans
        except Exception:
            pass
        return None

    @staticmethod
    def _insert_import_cleanly(lines: List[str], import_stmt: str) -> List[str]:
        """Inserts an import statement cleanly after docstrings and __future__ imports."""
        insert_idx = 0
        in_multiline_docstring = False
        future_passed = False

        for i, l in enumerate(lines):
            s = l.strip()
            # Handle multiline docstrings
            if not in_multiline_docstring and (s.startswith('"""') or s.startswith("'''")):
                if (s.startswith('"""') and s.endswith('"""') and len(s) >= 6) or \
                   (s.startswith("'''") and s.endswith("'''") and len(s) >= 6):
                    insert_idx = i + 1
                    continue
                in_multiline_docstring = True
                continue
            if in_multiline_docstring:
                if '"""' in s or "'''" in s:
                    in_multiline_docstring = False
                    insert_idx = i + 1
                continue

            # Skip __future__ imports
            if s.startswith("from __future__"):
                insert_idx = i + 1
                future_passed = True
                continue

            # If we hit an existing import, insert before it (after docstring/future)
            if s.startswith("import ") or s.startswith("from "):
                insert_idx = i
                break

            # If we hit code statements
            if s and not s.startswith("#"):
                if not future_passed and insert_idx == 0:
                    insert_idx = i
                break

        new_lines = list(lines)
        new_lines.insert(insert_idx, import_stmt.strip())
        return new_lines

    def _generate_deterministic_fix(
        self,
        analyzed_error: AnalyzedError,
        source_code: str,
    ) -> Optional[Tuple[str, str, float, str]]:
        """
        Synthesizes high-confidence deterministic fixes for well-understood patterns.
        Returns: (repaired_source, fix_type, confidence, explanation)
        """
        err_type = analyzed_error.error_type
        err_msg = analyzed_error.error_msg
        lines = source_code.splitlines()

        # 1. NameError for missing module import (e.g. name 're' is not defined)
        m_name = re.search(r"name '([a-zA-Z0-9_]+)' is not defined", err_msg)
        if err_type == "NameError" and m_name:
            missing_mod = m_name.group(1)
            standard_modules = {
                "re": "import re",
                "json": "import json",
                "os": "import os",
                "sys": "import sys",
                "time": "import time",
                "math": "import math",
                "ast": "import ast",
                "shutil": "import shutil",
                "Path": "from pathlib import Path",
                "Dict": "from typing import Dict, Any, List, Optional",
                "List": "from typing import List, Dict, Any, Optional",
                "Optional": "from typing import Optional, Dict, Any, List",
                "Any": "from typing import Any, Dict, List, Optional",
            }
            import_stmt = standard_modules.get(missing_mod)
            if import_stmt:
                new_lines = self._insert_import_cleanly(lines, import_stmt)
                repaired = "\n".join(new_lines) + ("\n" if source_code.endswith("\n") else "")
                return (
                    repaired,
                    f"add_import_{missing_mod}",
                    0.96,
                    f"Injected missing '{import_stmt}' cleanly after docstring/__future__.",
                )

        # 2. ImportError / ModuleNotFoundError
        m_imp = re.search(r"cannot import name '([a-zA-Z0-9_]+)' from '([a-zA-Z0-9_\.]+)'", err_msg)
        if m_imp:
            sym = m_imp.group(1)
            pkg = m_imp.group(2)
            # Fallback wrapper
            return (
                source_code,
                "import_symbol_mismatch",
                0.50,  # Below safety valve -> triggers user review
                f"Cannot import symbol '{sym}' from '{pkg}'. Requires manual signature resolution.",
            )

        # 3. SyntaxError: expected ':'
        if "expected ':'" in err_msg and analyzed_error.line_number:
            idx = analyzed_error.line_number - 1
            if 0 <= idx < len(lines):
                new_lines = list(lines)
                new_lines[idx] = new_lines[idx].rstrip() + ":"
                repaired = "\n".join(new_lines)
                return (
                    repaired,
                    "append_colon",
                    0.95,
                    f"Appended missing colon to line {analyzed_error.line_number}.",
                )

        # 4. Unterminated string literal
        if "unterminated string literal" in err_msg.lower() and analyzed_error.line_number:
            idx = analyzed_error.line_number - 1
            if 0 <= idx < len(lines):
                new_lines = list(lines)
                l = new_lines[idx]
                if l.count('"') % 2 != 0:
                    new_lines[idx] = l + '"'
                elif l.count("'") % 2 != 0:
                    new_lines[idx] = l + "'"
                repaired = "\n".join(new_lines)
                return (
                    repaired,
                    "close_string_literal",
                    0.93,
                    f"Closed unterminated string literal at line {analyzed_error.line_number}.",
                )

        return None

    def generate_fix(
        self,
        analyzed_error: AnalyzedError,
        target_file: Optional[Union[str, Path]] = None,
    ) -> GeneratedFix:
        """
        Central entry point to synthesize a code fix:
        1. Checks cached known fixes from ErrorAnalyzer.
        2. Tries deterministic heuristic rules.
        3. Queries local LLM (Llama / Phi-4).
        4. Applies the 70% confidence safety valve.
        """
        filepath = Path(target_file or analyzed_error.file_path or "").resolve()
        if not filepath.exists():
            return GeneratedFix(
                target_file=str(filepath),
                target_line=analyzed_error.line_number,
                error_type=analyzed_error.error_type,
                error_msg=analyzed_error.error_msg,
                fix_type="file_not_found",
                repaired_code="",
                original_code="",
                confidence=0.0,
                escalate_to_user=True,
                status="FAILED",
                explanation=f"Target file {filepath} not found on disk.",
            )

        original_code = filepath.read_text(encoding="utf-8", errors="replace")

        # --- PATH 1: Cached Known Fix ---
        if analyzed_error.cached_fix:
            c_fix = analyzed_error.cached_fix
            fix_code = c_fix.get("fix_code", "")
            action = c_fix.get("fix_action", "")
            if action == "insert_import" and fix_code:
                # Prepend or insert import cleanly
                lines = original_code.splitlines()
                new_lines = self._insert_import_cleanly(lines, fix_code.strip())
                repaired = "\n".join(new_lines) + "\n"
                return GeneratedFix(
                    target_file=str(filepath),
                    target_line=analyzed_error.line_number,
                    error_type=analyzed_error.error_type,
                    error_msg=analyzed_error.error_msg,
                    fix_type="cached_import_insertion",
                    repaired_code=repaired,
                    original_code=original_code,
                    confidence=c_fix.get("confidence", 0.95),
                    escalate_to_user=False,
                    status="READY_FOR_SANDBOX",
                    explanation=f"Applied cached known fix: {c_fix.get('description')}",
                )

        # --- PATH 2: Deterministic Heuristic Synthesis ---
        det_result = self._generate_deterministic_fix(analyzed_error, original_code)
        if det_result:
            repaired_code, fix_type, confidence, explanation = det_result
            escalate = confidence < self.CONFIDENCE_THRESHOLD
            status = "NEEDS_USER_REVIEW" if escalate else "READY_FOR_SANDBOX"
            return GeneratedFix(
                target_file=str(filepath),
                target_line=analyzed_error.line_number,
                error_type=analyzed_error.error_type,
                error_msg=analyzed_error.error_msg,
                fix_type=fix_type,
                repaired_code=repaired_code,
                original_code=original_code,
                confidence=confidence,
                escalate_to_user=escalate,
                status=status,
                explanation=explanation,
            )

        # --- PATH 3: Local LLM / Secondary Brain Generation ---
        prompt = self.construct_llm_prompt(analyzed_error, original_code)
        llm_response = self._query_local_llm(prompt)
        if llm_response:
            # Check if AST compiles
            try:
                ast.parse(llm_response)
                conf = 0.85
                return GeneratedFix(
                    target_file=str(filepath),
                    target_line=analyzed_error.line_number,
                    error_type=analyzed_error.error_type,
                    error_msg=analyzed_error.error_msg,
                    fix_type="llm_cognitive_patch",
                    repaired_code=llm_response,
                    original_code=original_code,
                    confidence=conf,
                    escalate_to_user=False,
                    status="READY_FOR_SANDBOX",
                    explanation="Synthesized cognitive repair via local LLM.",
                )
            except Exception as e:
                logger.warning(f"LLM patch had syntax error: {e}")

        # --- PATH 4: Safety Valve Escalation ---
        # Unknown error without confident resolution
        return GeneratedFix(
            target_file=str(filepath),
            target_line=analyzed_error.line_number,
            error_type=analyzed_error.error_type,
            error_msg=analyzed_error.error_msg,
            fix_type="unresolved_anomaly",
            repaired_code=original_code,
            original_code=original_code,
            confidence=0.45,
            escalate_to_user=True,
            status="NEEDS_USER_REVIEW",
            explanation=f"Error '{analyzed_error.error_msg}' has <70% confidence. Escalating to user.",
        )


# Global singleton instance
fix_generator = FixGenerator()
