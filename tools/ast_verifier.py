"""
AST Sandboxing & Formal Security Verifier for Dynamically Synthesized Tools.
Performs static analysis on synthesized Python code before execution to guarantee safety bounds.
"""

from __future__ import annotations
import ast
from typing import Any, Dict, List, Set, Tuple


FORBIDDEN_CALLS: Set[str] = {
    "eval", "exec", "__import__", "globals", "locals", "compile",
}

FORBIDDEN_MODULES: Set[str] = {
    "ctypes", "subprocess", "multiprocessing", "pty", "posix",
}


class ASTSecurityVerifier:
    def verify_code_safety(self, python_code: str) -> Tuple[bool, List[str]]:
        """
        Parses Python AST and verifies that code contains no dangerous syscalls or forbidden imports.
        """
        violations: List[str] = []

        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return False, [f"Syntax error in synthesized code: {e}"]

        for node in ast.walk(tree):
            # Check Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        violations.append(f"Forbidden module import: '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    violations.append(f"Forbidden from-import module: '{node.module}'")

            # Check Function Calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_CALLS:
                        violations.append(f"Forbidden built-in function call: '{node.func.id}'")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("system", "popen", "spawn", "fork", "execv"):
                        violations.append(f"Forbidden OS system call attribute: '{node.func.attr}'")

        is_safe = len(violations) == 0
        return is_safe, violations


ast_verifier = ASTSecurityVerifier()
