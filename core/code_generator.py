"""
Code Generator & Diff Engine for P.H.A.S.S Recursive Architect (v14.0).
Extracts, merges, and replaces target functions/classes, generates unified diff patches,
and writes isolated candidate code to sandbox/.
"""

from __future__ import annotations
import ast
import difflib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from core.architect_planner import ArchitecturePlan

logger = logging.getLogger("phass.core.code_generator")

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_PATCH_DIR = PROJECT_ROOT / "checkpoints" / "patches"
DEFAULT_SANDBOX_DIR = PROJECT_ROOT / "sandbox"


@dataclass
class GeneratedPatch:
    target_file: str
    target_function: str
    patch_path: str
    sandbox_file: str
    original_code: str
    new_code: str
    diff_content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file": self.target_file,
            "target_function": self.target_function,
            "patch_path": self.patch_path,
            "sandbox_file": self.sandbox_file,
            "diff_content": self.diff_content,
            "timestamp": self.timestamp,
        }


class CodeGenerator:
    """
    Integrates proposed code changes into original files,
    generates unified diff patches, and stages files to sandbox/.
    """

    def __init__(
        self,
        patch_dir: Optional[Union[str, Path]] = None,
        sandbox_dir: Optional[Union[str, Path]] = None,
    ):
        self.patch_dir = Path(patch_dir) if patch_dir else DEFAULT_PATCH_DIR
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else DEFAULT_SANDBOX_DIR
        self.patch_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def replace_function_in_source(self, source_code: str, target_fn_name: str, new_fn_code: str) -> str:
        """
        Replaces target function definition in source code with new_fn_code,
        preserving all surrounding functions, classes, comments, and docstrings.
        """
        try:
            tree = ast.parse(source_code)
            lines = source_code.splitlines()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_fn_name:
                    start_line = node.lineno - 1
                    end_line = getattr(node, "end_lineno", len(lines))

                    # Include any preceding decorators
                    if node.decorator_list:
                        first_dec = node.decorator_list[0]
                        start_line = min(start_line, first_dec.lineno - 1)

                    before = lines[:start_line]
                    after = lines[end_line:]

                    replacement = new_fn_code.strip().splitlines()
                    merged_lines = before + replacement + after
                    return "\n".join(merged_lines) + ("\n" if source_code.endswith("\n") else "")

        except Exception as e:
            logger.warning(f"AST replacement fallback for {target_fn_name}: {e}")

        # Fallback regex substitution
        pattern = rf"(def\s+{re.escape(target_fn_name)}\s*\([^)]*\)[^:]*:.*?(?=\n(?:def\s+|\nclass\s+|\Z)))"
        subbed, count = re.subn(pattern, new_fn_code.strip(), source_code, count=1, flags=re.DOTALL)
        if count > 0:
            return subbed

        return source_code

    def generate_patch(
        self,
        plan: ArchitecturePlan,
        source_override: Optional[str] = None,
    ) -> GeneratedPatch:
        """
        Applies ArchitecturePlan to the target module:
        1. Reads original source file.
        2. Replaces target function with new_code.
        3. Creates unified diff and saves checkpoints/patches/[file]_[timestamp].patch.
        4. Writes sandboxed file to sandbox/[file].
        """
        target_path = Path(plan.target_file)
        full_target_path = PROJECT_ROOT / target_path if not target_path.is_absolute() else target_path

        if source_override is not None:
            original_code = source_override
        else:
            original_code = full_target_path.read_text(encoding="utf-8", errors="replace")

        # Determine new complete file content
        if plan.new_code.startswith("def ") or plan.new_code.startswith("async def "):
            repaired_code = self.replace_function_in_source(original_code, plan.target_function, plan.new_code)
        elif plan.new_code:
            # If new_code is a full module replacement or already contains the file
            repaired_code = plan.new_code
        else:
            repaired_code = original_code

        # Generate Unified Diff
        orig_lines = original_code.splitlines(keepends=True)
        new_lines = repaired_code.splitlines(keepends=True)
        filename = full_target_path.name
        diff_lines = list(
            difflib.unified_diff(
                orig_lines,
                new_lines,
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
                n=3,
            )
        )
        diff_content = "".join(diff_lines)

        # Write Patch File
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_name = f"{full_target_path.stem}_{timestamp_str}.patch"
        patch_file = self.patch_dir / patch_name
        patch_file.write_text(diff_content, encoding="utf-8")
        logger.info(f"Generated unified diff patch: {patch_file}")

        # Write Sandboxed File (mirroring relative path if applicable)
        rel_path = (
            full_target_path.relative_to(PROJECT_ROOT)
            if PROJECT_ROOT in full_target_path.parents
            else Path(full_target_path.name)
        )
        sandbox_target = self.sandbox_dir / rel_path
        sandbox_target.parent.mkdir(parents=True, exist_ok=True)
        sandbox_target.write_text(repaired_code, encoding="utf-8")
        logger.info(f"Staged candidate file in sandbox: {sandbox_target}")

        return GeneratedPatch(
            target_file=str(full_target_path),
            target_function=plan.target_function,
            patch_path=str(patch_file),
            sandbox_file=str(sandbox_target),
            original_code=original_code,
            new_code=repaired_code,
            diff_content=diff_content,
        )


code_generator = CodeGenerator()
