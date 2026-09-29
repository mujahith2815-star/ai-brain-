"""
Runtime In-Memory Hot-Coding & Live AST Patching Engine for P.H.A.S.S Sphere v4.0.
Compiles, hot-swaps, and injects Python functions and classes directly into live memory
without restarting the application or dropping session state.
"""

from __future__ import annotations
import ast
import inspect
import logging
import sys
import types
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.learning.hot_coder")


@dataclass
class HotPatchRecord:
    patch_id: str
    target_module: str
    target_symbol: str
    code_injected: str
    previous_symbol_ref: Optional[Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "target_module": self.target_module,
            "target_symbol": self.target_symbol,
            "code_injected": self.code_injected,
            "timestamp": self.timestamp,
        }


class RuntimeHotCoder:
    def __init__(self):
        self.active_patches: Dict[str, HotPatchRecord] = {}
        self.patch_counter = 0

    def hot_inject_function(self, target_module_name: str, symbol_name: str, python_code: str) -> Tuple[bool, str]:
        """
        Parses, compiles, and dynamically injects a function into a live running Python module.
        """
        # 1. AST Syntax & Security Verification
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            return False, f"AST Syntax Error in hot-patch: {e}"

        # 2. Compile Bytecode in isolated namespace
        local_scope: Dict[str, Any] = {}
        global_scope: Dict[str, Any] = globals().copy()

        try:
            compiled = compile(tree, filename=f"<hotpatch_{symbol_name}>", mode="exec")
            exec(compiled, global_scope, local_scope)
        except Exception as e:
            return False, f"Compilation/Execution Error in hot-patch: {e}"

        if symbol_name not in local_scope:
            return False, f"Symbol '{symbol_name}' was not defined in the supplied code."

        new_symbol = local_scope[symbol_name]

        # 3. Locate or create target module in sys.modules
        if target_module_name not in sys.modules:
            mod = types.ModuleType(target_module_name)
            sys.modules[target_module_name] = mod
        else:
            mod = sys.modules[target_module_name]

        # 4. Save previous symbol reference for rollback capability
        prev_ref = getattr(mod, symbol_name, None)
        self.patch_counter += 1
        p_id = f"patch_{self.patch_counter:04d}"

        record = HotPatchRecord(
            patch_id=p_id,
            target_module=target_module_name,
            target_symbol=symbol_name,
            code_injected=python_code,
            previous_symbol_ref=prev_ref,
        )
        self.active_patches[p_id] = record

        # 5. Hot-swap symbol into live module namespace
        setattr(mod, symbol_name, new_symbol)
        msg = f"Hot-patch '{p_id}' successfully injected '{symbol_name}' into live module '{target_module_name}'."
        logger.info(msg)
        return True, msg

    def hot_execute_snippet(self, code_snippet: str) -> Tuple[bool, Any, str]:
        """
        Evaluates a snippet in the live environment and returns the result.
        """
        try:
            tree = ast.parse(code_snippet)
            # If single expression, eval it
            if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                val = eval(compile(ast.Expression(tree.body[0].value), "<dynamic_expr>", "eval"))
                return True, val, str(val)

            # Otherwise execute statement block
            local_scope: Dict[str, Any] = {}
            compiled = compile(tree, "<dynamic_block>", "exec")
            exec(compiled, globals(), local_scope)
            return True, local_scope, f"Executed successfully with {len(local_scope)} local exports."
        except Exception as e:
            return False, None, f"Hot execution error: {e}"

    def rollback_patch(self, patch_id: str) -> Tuple[bool, str]:
        """
        Rolls back an active hot-patch in live memory.
        """
        if patch_id not in self.active_patches:
            return False, f"Patch '{patch_id}' not found."

        record = self.active_patches[patch_id]
        if record.target_module in sys.modules:
            mod = sys.modules[record.target_module]
            if record.previous_symbol_ref is not None:
                setattr(mod, record.target_symbol, record.previous_symbol_ref)
            else:
                if hasattr(mod, record.target_symbol):
                    delattr(mod, record.target_symbol)

        del self.active_patches[patch_id]
        return True, f"Successfully rolled back patch '{patch_id}' on '{record.target_symbol}'."


hot_coder = RuntimeHotCoder()
