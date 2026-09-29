"""
Error Analyzer Engine for P.H.A.S.S Autonomic Recovery Circuit.
Continuous log watcher, error classifier, and fuzzy similarity matcher.
"""

from __future__ import annotations
import json
import logging
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("phass.core.error_analyzer")

DEFAULT_KNOWN_ERRORS_FILE = Path(__file__).parent.parent / "checkpoints" / "known_errors.json"
DEFAULT_EXECUTION_LOG = Path(__file__).parent.parent / "checkpoints" / "execution_log.json"


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes pure-Python Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Returns normalized similarity ratio [0.0 to 1.0] using Levenshtein distance."""
    s1_clean = s1.lower().strip()
    s2_clean = s2.lower().strip()
    if s1_clean == s2_clean:
        return 1.0
    max_len = max(len(s1_clean), len(s2_clean))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1_clean, s2_clean)
    return max(0.0, 1.0 - (dist / max_len))


@dataclass
class AnalyzedError:
    error_type: str
    category: str
    error_msg: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_context: Optional[str] = None
    traceback_str: Optional[str] = None
    similarity_match: Optional[Dict[str, Any]] = None
    similarity_score: float = 0.0
    cached_fix: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "category": self.category,
            "error_msg": self.error_msg,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_context": self.code_context,
            "traceback_str": self.traceback_str,
            "similarity_score": round(self.similarity_score, 3),
            "cached_fix": self.cached_fix,
            "timestamp": self.timestamp,
        }


class ErrorAnalyzer:
    """
    Monitors execution logs and stderr, classifies errors into systemic domains,
    and performs fuzzy matching against known fixes.
    """

    ERROR_CATEGORIES = {
        "ImportError": "IMPORT_MODULE_FAULT",
        "ModuleNotFoundError": "IMPORT_MODULE_FAULT",
        "SyntaxError": "SYNTAX_PARSER_FAULT",
        "IndentationError": "SYNTAX_PARSER_FAULT",
        "AttributeError": "VARIABLE_OR_ATTRIBUTE_FAULT",
        "NameError": "VARIABLE_OR_ATTRIBUTE_FAULT",
        "UnboundLocalError": "VARIABLE_OR_ATTRIBUTE_FAULT",
        "TimeoutError": "NETWORK_OR_TIMEOUT_FAULT",
        "ConnectionError": "NETWORK_OR_TIMEOUT_FAULT",
        "ConnectionRefusedError": "NETWORK_OR_TIMEOUT_FAULT",
        "FileNotFoundError": "FILESYSTEM_PERMISSION_FAULT",
        "PermissionError": "FILESYSTEM_PERMISSION_FAULT",
        "IsADirectoryError": "FILESYSTEM_PERMISSION_FAULT",
    }

    def __init__(
        self,
        known_errors_path: Optional[Union[str, Path]] = None,
        log_file: Optional[Union[str, Path]] = None,
        known_errors_file: Optional[Union[str, Path]] = None,
        execution_log_file: Optional[Union[str, Path]] = None,
    ):
        target_known = known_errors_file or known_errors_path or DEFAULT_KNOWN_ERRORS_FILE
        target_log = execution_log_file or log_file or DEFAULT_EXECUTION_LOG
        self.known_errors_path = Path(target_known).resolve()
        self.log_file = Path(target_log).resolve()
        self.known_errors: List[Dict[str, Any]] = []
        self.load_known_errors()

    def load_known_errors(self) -> List[Dict[str, Any]]:
        """Loads cached errors and known fixes from disk, supporting both list and dict formats."""
        if self.known_errors_path.exists():
            try:
                raw = json.loads(self.known_errors_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    self.known_errors = raw
                elif isinstance(raw, dict):
                    self.known_errors = raw.get("known_errors", [])
                else:
                    self.known_errors = []
            except Exception as e:
                logger.warning(f"Could not load known errors: {e}")
                self.known_errors = []
        return self.known_errors

    def save_known_error(self, error_record: Dict[str, Any]) -> None:
        """Saves a newly verified fix to the known errors database."""
        self.known_errors_path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid duplicate pattern records
        for i, existing in enumerate(self.known_errors):
            if existing.get("pattern") == error_record.get("pattern"):
                self.known_errors[i] = error_record
                self._persist_known_errors()
                return
        self.known_errors.append(error_record)
        self._persist_known_errors()

    def _persist_known_errors(self) -> None:
        try:
            self.known_errors_path.write_text(json.dumps(self.known_errors, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist known errors: {e}")

    def optimize_known_errors(self) -> int:
        """Prunes duplicate or obsolete error patterns."""
        seen = set()
        optimized = []
        for item in self.known_errors:
            pat = item.get("pattern", "")
            if pat and pat not in seen:
                seen.add(pat)
                optimized.append(item)
        self.known_errors = optimized
        self._persist_known_errors()
        return len(optimized)

    def classify_error(self, err_type_or_exc: Union[str, Exception]) -> str:
        """Categorizes an error into its canonical recovery group."""
        if isinstance(err_type_or_exc, Exception):
            err_name = type(err_type_or_exc).__name__
        else:
            err_name = str(err_type_or_exc).strip()
        return self.ERROR_CATEGORIES.get(err_name, "RUNTIME_EXECUTION_FAULT")

    def find_similar_known_error(self, error_msg: str, error_type: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Performs fuzzy matching (Levenshtein ratio) across known error patterns.
        Returns the best matching record and similarity score.
        """
        best_match = None
        best_score = 0.0

        for candidate in self.known_errors:
            pat = candidate.get("pattern", "")
            cand_type = candidate.get("error_type", "")

            # Exact regex match
            try:
                if re.search(pat, error_msg, re.IGNORECASE):
                    return candidate, 1.0
            except Exception:
                pass

            # Substring match
            if pat.lower() in error_msg.lower() or error_msg.lower() in pat.lower():
                score = 0.95
            else:
                score = similarity_ratio(pat, error_msg)

            # Bonus for matching error type
            if cand_type and cand_type == error_type:
                score = min(1.0, score + 0.05)

            if score > best_score:
                best_score = score
                best_match = candidate

        return best_match, best_score

    def analyze_exception(
        self,
        exc: Exception,
        file_path: Optional[Union[str, Path]] = None,
        line_number: Optional[int] = None,
        tb_str: Optional[str] = None,
    ) -> AnalyzedError:
        """
        Analyzes a live Exception instance: extracts traceback, identifies file/line,
        classifies category, and checks similarity against known errors.
        """
        err_type = type(exc).__name__
        err_msg = str(exc)
        category = self.classify_error(exc)

        # Traceback analysis
        if not tb_str:
            tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        parsed_file = str(file_path) if file_path else None
        parsed_line = line_number

        if not parsed_file or not parsed_line:
            # Extract last frame from traceback
            tb_matches = re.findall(r'File "([^"]+)", line (\d+)', tb_str)
            if tb_matches:
                # Pick the most relevant project file (ignoring standard library)
                for f_cand, l_cand in reversed(tb_matches):
                    if "lib" not in f_cand.lower() and "site-packages" not in f_cand.lower():
                        parsed_file = f_cand
                        parsed_line = int(l_cand)
                        break
                if not parsed_file:
                    parsed_file, l_str = tb_matches[-1]
                    parsed_line = int(l_str)

        code_context = None
        if parsed_file and os.path.exists(parsed_file) and parsed_line:
            try:
                lines = Path(parsed_file).read_text(encoding="utf-8", errors="replace").splitlines()
                if 1 <= parsed_line <= len(lines):
                    code_context = lines[parsed_line - 1].strip()
            except Exception:
                pass

        # Check similarity match
        match, score = self.find_similar_known_error(err_msg, err_type)

        return AnalyzedError(
            error_type=err_type,
            category=category,
            error_msg=err_msg,
            file_path=parsed_file,
            line_number=parsed_line,
            code_context=code_context,
            traceback_str=tb_str,
            similarity_match=match if score >= 0.70 else None,
            similarity_score=score,
            cached_fix=match if score >= 0.70 else None,
        )

    def analyze_error(
        self,
        error_type: str,
        error_msg: str,
        file_path: Optional[Union[str, Path]] = None,
        line_number: Optional[int] = None,
        code_context: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ) -> AnalyzedError:
        """Analyzes an error with direct parameters, classifying and checking similarity match."""
        category = self.classify_error(error_type)
        match, score = self.find_similar_known_error(error_msg, error_type)
        return AnalyzedError(
            error_type=error_type,
            category=category,
            error_msg=error_msg,
            file_path=str(file_path) if file_path else None,
            line_number=line_number,
            code_context=code_context,
            traceback_str=traceback_str,
            similarity_match=match if score >= 0.70 else None,
            similarity_score=score,
            cached_fix=match if score >= 0.70 else None,
        )

    def analyze_log_entry(
        self,
        entry: Optional[Union[Dict[str, Any], str]] = None,
        error_text: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        code_context: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ) -> AnalyzedError:
        """Analyzes an error entry from execution log or raw stderr text."""
        raw_input = error_text if error_text is not None else entry
        if isinstance(raw_input, dict):
            err_raw = str(raw_input.get("error") or raw_input.get("verification_reason", ""))
        else:
            err_raw = str(raw_input or "")

        parsed_file = file_path
        parsed_line = line_number

        tb_matches = re.findall(r'File "([^"]+)", line (\d+)', err_raw)
        if tb_matches:
            for f_cand, l_cand in reversed(tb_matches):
                if "lib" not in f_cand.lower() and "site-packages" not in f_cand.lower():
                    parsed_file = f_cand
                    parsed_line = int(l_cand)
                    break
            if not parsed_file:
                parsed_file, l_str = tb_matches[-1]
                parsed_line = int(l_str)

        m = re.search(r"([A-Z][a-zA-Z0-9]+Error):\s*(.+)", err_raw)
        if m:
            e_type = m.group(1)
            e_msg = m.group(2).strip()
        else:
            e_type = "RuntimeError"
            e_msg = err_raw

        return self.analyze_error(
            error_type=e_type,
            error_msg=e_msg,
            file_path=parsed_file,
            line_number=parsed_line,
            code_context=code_context,
            traceback_str=traceback_str or err_raw,
        )


# Global singleton instance
error_analyzer = ErrorAnalyzer()
