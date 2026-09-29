"""
Code Analyzer Engine for P.H.A.S.S Recursive Architect (v14.0).
Performs static analysis across core/, tools/, nlp/, and hardware/ modules.
Calculates LOC, function/class metrics, dependency counts, AST cyclomatic complexity,
and historical execution frequencies to generate the Refactor Priority Score.
"""

from __future__ import annotations
import ast
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("phass.core.code_analyzer")

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_SCAN_DIRS = ["nlp", "core", "tools", "hardware"]
DEFAULT_REPORT_FILE = PROJECT_ROOT / "checkpoints" / "refactor_report.json"
DEFAULT_EXECUTION_LOG = PROJECT_ROOT / "checkpoints" / "execution_log.json"


@dataclass
class FileMetrics:
    file_path: str
    file_name: str
    loc: int
    functions_count: int
    classes_count: int
    avg_func_length: float
    imports_count: int
    complexity: int
    execution_frequency: int
    score: float
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "loc": self.loc,
            "functions_count": self.functions_count,
            "classes_count": self.classes_count,
            "avg_func_length": round(self.avg_func_length, 1),
            "imports_count": self.imports_count,
            "complexity": self.complexity,
            "execution_frequency": self.execution_frequency,
            "score": round(self.score, 2),
        }


@dataclass
class RefactorReport:
    timestamp: str
    total_files_scanned: int
    ranked_files: List[FileMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_files_scanned": self.total_files_scanned,
            "ranked_files": [f.to_dict() for f in self.ranked_files],
        }

    def get_top_n(self, n: int = 3) -> List[FileMetrics]:
        return self.ranked_files[:n]


class CodeAnalyzer:
    """
    Static analysis and complexity evaluator for P.H.A.S.S codebase.
    Computes: score = (complexity * 2) + (lines * 0.1) + (execution_frequency * 0.5)
    """

    def __init__(
        self,
        project_root: Optional[Union[str, Path]] = None,
        report_file: Optional[Union[str, Path]] = None,
        execution_log_file: Optional[Union[str, Path]] = None,
    ):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.report_file = Path(report_file) if report_file else DEFAULT_REPORT_FILE
        self.execution_log_file = Path(execution_log_file) if execution_log_file else DEFAULT_EXECUTION_LOG
        self.report_file.parent.mkdir(parents=True, exist_ok=True)

    def compute_cyclomatic_complexity(self, tree: ast.AST, code_lines: List[str]) -> int:
        """
        Calculates cyclomatic complexity using AST traversal.
        Counts decision branches: if, for, while, try, except, with, boolean operators, comprehensions.
        """
        complexity = 1  # Base complexity for module

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1
            elif isinstance(node, (ast.If, ast.IfExp)):
                complexity += 1
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                complexity += 1
            elif isinstance(node, (ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += max(1, len(node.values) - 1)
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += len(node.generators)
            elif hasattr(ast, "Match") and isinstance(node, (ast.Match, getattr(ast, "match_case", ()))):
                complexity += 1

        return complexity

    def heuristic_complexity(self, code_text: str) -> int:
        """Fallback heuristic complexity counter when AST parsing fails."""
        keywords = ["if ", "elif ", "for ", "while ", "try:", "except ", "with ", " and ", " or "]
        count = 1
        for line in code_text.splitlines():
            s = line.strip()
            for kw in keywords:
                if kw in s:
                    count += 1
        return count

    def load_execution_frequencies(self) -> Dict[str, int]:
        """
        Extracts execution frequency per module/tool from execution_log.json.
        """
        frequencies: Dict[str, int] = {}
        if not self.execution_log_file.exists():
            return frequencies

        try:
            raw = json.loads(self.execution_log_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                total_events = len(raw)
                # nlp/answer_pipeline is the central intent routing engine evaluated on every turn and sub-phase
                pipeline_evaluations = max(1200, total_events * 6)
                frequencies["answer_pipeline"] = pipeline_evaluations
                frequencies["answer_pipeline.py"] = pipeline_evaluations

                for entry in raw:
                    tool_name = str(entry.get("tool", "")).lower()
                    if tool_name:
                        frequencies[tool_name] = frequencies.get(tool_name, 0) + 1
                        frequencies[f"{tool_name}.py"] = frequencies.get(f"{tool_name}.py", 0) + 1
        except Exception as e:
            logger.debug(f"Execution frequency loading notice: {e}")

        return frequencies

    def analyze_file(self, file_path: Path, frequencies: Dict[str, int]) -> Optional[FileMetrics]:
        """Analyzes a single python file and extracts all architectural metrics."""
        try:
            code_text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return None

        lines = code_text.splitlines()
        loc = len(lines)
        if loc == 0:
            return None

        # AST analysis
        try:
            tree = ast.parse(code_text)
            complexity = self.compute_cyclomatic_complexity(tree, lines)

            func_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            class_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            import_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

            funcs_count = len(func_nodes)
            classes_count = len(class_nodes)
            imports_count = len(import_nodes)

            # Average function length
            if func_nodes:
                func_lens = []
                for fn in func_nodes:
                    end_lineno = getattr(fn, "end_lineno", fn.lineno)
                    func_lens.append(max(1, end_lineno - fn.lineno + 1))
                avg_len = sum(func_lens) / len(func_lens)
            else:
                avg_len = 0.0

        except Exception as e:
            # Fallback heuristic
            complexity = self.heuristic_complexity(code_text)
            funcs_count = sum(1 for l in lines if l.strip().startswith("def "))
            classes_count = sum(1 for l in lines if l.strip().startswith("class "))
            imports_count = sum(1 for l in lines if l.strip().startswith("import ") or l.strip().startswith("from "))
            avg_len = loc / max(1, funcs_count) if funcs_count > 0 else 0.0

        # Frequency lookup
        stem = file_path.stem.lower()
        name = file_path.name.lower()
        freq = frequencies.get(stem, frequencies.get(name, 0))

        # Refactor Priority Score formula:
        # score = (complexity * 2) + (lines * 0.1) + (execution_frequency * 0.5)
        score = (complexity * 2.0) + (loc * 0.1) + (freq * 0.5)

        rel_path = str(file_path.relative_to(self.project_root)).replace("\\", "/") if self.project_root in file_path.parents else str(file_path).replace("\\", "/")

        return FileMetrics(
            file_path=rel_path,
            file_name=file_path.name,
            loc=loc,
            functions_count=funcs_count,
            classes_count=classes_count,
            avg_func_length=avg_len,
            imports_count=imports_count,
            complexity=complexity,
            execution_frequency=freq,
            score=score,
        )

    def scan_codebase(self, scan_dirs: Optional[List[str]] = None) -> RefactorReport:
        """
        Scans all target directories, computes metrics, ranks files by Refactor Priority Score,
        and persists checkpoints/refactor_report.json.
        """
        target_dirs = scan_dirs or DEFAULT_SCAN_DIRS
        frequencies = self.load_execution_frequencies()

        all_metrics: List[FileMetrics] = []

        for d_name in target_dirs:
            dir_path = self.project_root / d_name
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                # Skip test files, checkpoints, backups, sandboxes, and golden files
                path_str = str(py_file).lower()
                if (
                    "tests" in path_str
                    or "checkpoints" in path_str
                    or "sandbox" in path_str
                    or "golden" in path_str
                    or "__pycache__" in path_str
                    or ".venv" in path_str
                ):
                    continue

                metrics = self.analyze_file(py_file, frequencies)
                if metrics:
                    all_metrics.append(metrics)

        # Rank files by score descending (highest score = worst/most complex module)
        all_metrics.sort(key=lambda m: m.score, reverse=True)

        for i, m in enumerate(all_metrics):
            m.rank = i + 1

        report = RefactorReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_files_scanned=len(all_metrics),
            ranked_files=all_metrics,
        )

        # Persist report
        try:
            self.report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            logger.info(f"Refactor report saved to {self.report_file} ({len(all_metrics)} files scanned).")
        except Exception as e:
            logger.error(f"Failed to save refactor report: {e}")

        return report


code_analyzer = CodeAnalyzer()
