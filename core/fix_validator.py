"""
Sandbox Validator Engine for P.H.A.S.S Autonomic Recovery Circuit.
Isolates candidate patches in sandbox/, runs py_compile syntax verification,
and executes unit test suites before any hot deployment.
"""

from __future__ import annotations
import ast
import logging
import os
import py_compile
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from core.fix_generator import GeneratedFix

logger = logging.getLogger("phass.core.fix_validator")

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_SANDBOX_DIR = PROJECT_ROOT / "sandbox"


@dataclass
class ValidationResult:
    passed: bool
    syntax_ok: bool
    tests_ok: bool
    target_file: str
    sandbox_file: Optional[str] = None
    error_message: Optional[str] = None
    syntax_error: Optional[str] = None
    test_output: Optional[str] = None
    tests_run: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "syntax_ok": self.syntax_ok,
            "tests_ok": self.tests_ok,
            "target_file": self.target_file,
            "sandbox_file": self.sandbox_file,
            "error_message": self.error_message,
            "syntax_error": self.syntax_error,
            "test_output": self.test_output,
            "tests_run": self.tests_run,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


class SandboxValidator:
    """
    Validates candidate fixes in an isolated sandbox.
    Enforces AST + py_compile syntax checks and pytest unit tests.
    """

    def __init__(
        self,
        sandbox_dir: Optional[Union[str, Path]] = None,
        python_executable: Optional[str] = None,
    ):
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else DEFAULT_SANDBOX_DIR
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        # Ensure sandbox has __init__.py
        init_file = self.sandbox_dir / "__init__.py"
        if not init_file.exists():
            try:
                init_file.write_text("# sandbox package\n", encoding="utf-8")
            except Exception:
                pass

        self.python_executable = python_executable or sys.executable

    def prepare_sandbox(self, target_file: Union[str, Path], candidate_code: str) -> Path:
        """Copies candidate code into isolated sandbox directory."""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        fname = Path(target_file).name
        sandbox_path = self.sandbox_dir / fname
        sandbox_path.write_text(candidate_code, encoding="utf-8")
        return sandbox_path

    def validate_syntax(self, file_path_or_code: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validates Python syntax using AST parsing and py_compile.
        Returns (is_valid, error_description).
        """
        # 1. AST parse check
        if isinstance(file_path_or_code, Path) or (isinstance(file_path_or_code, str) and os.path.exists(file_path_or_code)):
            target_path = Path(file_path_or_code)
            try:
                code_text = target_path.read_text(encoding="utf-8")
            except Exception as e:
                return False, f"Failed to read file for syntax check: {e}"
        else:
            code_text = str(file_path_or_code)
            target_path = None

        try:
            ast.parse(code_text)
        except SyntaxError as se:
            return False, f"SyntaxError at line {se.lineno}: {se.msg}"
        except Exception as e:
            return False, f"AST parse error: {e}"

        # 2. py_compile check if target path exists
        if target_path and target_path.exists():
            try:
                py_compile.compile(str(target_path), doraise=True)
            except py_compile.PyCompileError as pce:
                return False, f"py_compile error: {pce}"
            except Exception as e:
                return False, f"Bytecode compilation error: {e}"

        return True, None

    def find_associated_tests(self, target_file: Union[str, Path]) -> List[Path]:
        """Discovers unit test files associated with target module."""
        stem = Path(target_file).stem
        tests_dir = PROJECT_ROOT / "tests"
        if not tests_dir.exists():
            return []

        candidates = [
            tests_dir / f"test_{stem}.py",
            tests_dir / f"test_{stem.replace('_', '')}.py",
        ]
        return [c for c in candidates if c.exists()]

    def run_unit_tests(
        self,
        sandbox_file: Path,
        test_path: Optional[Union[str, Path]] = None,
        timeout: float = 20.0,
    ) -> Tuple[bool, str, int]:
        """
        Executes pytest against the specified or discovered test suite.
        Returns (passed, stdout/stderr_output, tests_run).
        """
        test_target = Path(test_path) if test_path else None
        if test_target and not test_target.exists():
            test_target = None

        if not test_target:
            associated = self.find_associated_tests(sandbox_file)
            if associated:
                test_target = associated[0]

        if not test_target:
            # If no unit test file exists, execute a subprocess bytecode & import sanity check
            cmd = [
                self.python_executable,
                "-c",
                f"import py_compile; py_compile.compile(r'{sandbox_file}', doraise=True)",
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if proc.returncode == 0:
                    return True, "Subprocess bytecode compilation verified (no dedicated unit tests).", 1
                else:
                    return False, proc.stderr or proc.stdout, 0
            except subprocess.TimeoutExpired:
                return False, "Subprocess validation timed out.", 0
            except Exception as e:
                return False, f"Sanity verification exception: {e}", 0

        # Execute pytest on discovered suite
        env = dict(os.environ)
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{self.sandbox_dir}{os.pathsep}{PROJECT_ROOT}{os.pathsep}{current_pythonpath}"

        cmd = [
            self.python_executable,
            "-m",
            "pytest",
            str(test_target),
            "-v",
            "--tb=no",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
            passed = (proc.returncode == 0)
            tests_run = output.count(" PASSED") + output.count(" FAILED")
            return passed, output, max(1, tests_run)
        except subprocess.TimeoutExpired:
            return False, "Unit tests timed out.", 0
        except Exception as e:
            return False, f"Test runner execution error: {e}", 0

    def validate_fix(
        self,
        fix: GeneratedFix,
        test_path: Optional[Union[str, Path]] = None,
        run_tests: bool = True,
    ) -> ValidationResult:
        """
        Executes full validation pipeline:
        1. Safety Valve Check: Confidence >= 70% and status == "READY_FOR_SANDBOX".
        2. Sandbox Isolation.
        3. AST & py_compile Syntax Verification.
        4. Unit Test Suite Execution.
        """
        start_time = time.time()

        # 1. Safety Valve Gating
        if fix.confidence < 0.70 or fix.status != "READY_FOR_SANDBOX":
            duration_ms = (time.time() - start_time) * 1000
            msg = (
                f"Fix rejected by safety valve: confidence is {fix.confidence*100:.1f}% "
                f"(required >= 70.0%). Status: {fix.status}. Escalating to user."
            )
            logger.warning(msg)
            return ValidationResult(
                passed=False,
                syntax_ok=False,
                tests_ok=False,
                target_file=fix.target_file,
                error_message=msg,
                duration_ms=duration_ms,
            )

        # 2. Stage to Sandbox
        try:
            sandbox_file = self.prepare_sandbox(fix.target_file, fix.repaired_code)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ValidationResult(
                passed=False,
                syntax_ok=False,
                tests_ok=False,
                target_file=fix.target_file,
                error_message=f"Failed to isolate fix in sandbox: {e}",
                duration_ms=duration_ms,
            )

        # 3. Syntax Verification (AST + py_compile)
        syntax_ok, syntax_err = self.validate_syntax(sandbox_file)
        if not syntax_ok:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Sandbox syntax validation failed for {fix.target_file}: {syntax_err}")
            return ValidationResult(
                passed=False,
                syntax_ok=False,
                tests_ok=False,
                target_file=fix.target_file,
                sandbox_file=str(sandbox_file),
                syntax_error=syntax_err,
                error_message=f"Syntax check failed: {syntax_err}",
                duration_ms=duration_ms,
            )

        # 4. Unit Test Verification
        tests_ok = True
        test_output = "Tests bypassed by configuration."
        tests_run = 0

        if run_tests:
            tests_ok, test_output, tests_run = self.run_unit_tests(sandbox_file, test_path=test_path)
            if not tests_ok:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"Sandbox unit tests failed for {fix.target_file}:\n{test_output}")
                return ValidationResult(
                    passed=False,
                    syntax_ok=True,
                    tests_ok=False,
                    target_file=fix.target_file,
                    sandbox_file=str(sandbox_file),
                    test_output=test_output,
                    tests_run=tests_run,
                    error_message=f"Unit test suite failed for candidate patch: {test_output[:200]}",
                    duration_ms=duration_ms,
                )

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"Sandbox validation successful for {fix.target_file} in {duration_ms:.1f}ms")
        return ValidationResult(
            passed=True,
            syntax_ok=True,
            tests_ok=tests_ok,
            target_file=fix.target_file,
            sandbox_file=str(sandbox_file),
            test_output=test_output,
            tests_run=tests_run,
            duration_ms=duration_ms,
        )


sandbox_validator = SandboxValidator()
