"""
Autonomous Tool Synthesis & Dynamic Self-Coding Engine for P.H.A.S.S Sphere.
Enables the AI to write, verify, and register its own Python tools on the fly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .ast_verifier import ast_verifier
from .permissions import PermissionLevel
from .registry import tool_registry

logger = logging.getLogger("phass.tools.synthesis")


@dataclass
class SynthesizedToolRecord:
    tool_name: str
    description: str
    code_body: str
    permission_level: str
    verified_safe: bool
    creation_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "code_body": self.code_body,
            "permission_level": self.permission_level,
            "verified_safe": self.verified_safe,
            "creation_timestamp": self.creation_timestamp,
        }


class AutonomousToolSynthesizer:
    def __init__(self):
        self.synthesized_tools: Dict[str, SynthesizedToolRecord] = {}

    def synthesize_tool(
        self,
        tool_name: str,
        description: str,
        python_code: str,
        permission: PermissionLevel = PermissionLevel.ANALYZE,
    ) -> Tuple[bool, str]:
        """
        Synthesizes, verifies, and dynamically registers a new tool.
        """
        clean_name = tool_name.strip().replace(" ", "_").lower()

        # 1. AST Security Verification
        is_safe, violations = ast_verifier.verify_code_safety(python_code)
        if not is_safe:
            err = f"Security verification rejected tool synthesis: {', '.join(violations)}"
            logger.error(err)
            return False, err

        # 2. Dynamic Compilation in Isolated Namespace
        local_scope: Dict[str, Any] = {}
        try:
            compiled_code = compile(python_code, f"<synthesized_tool_{clean_name}>", "exec")
            exec(compiled_code, {"math": __import__("math"), "json": __import__("json")}, local_scope)
        except Exception as e:
            err = f"Compilation error in synthesized tool: {e}"
            logger.error(err)
            return False, err

        # Find the callable function
        func: Optional[Callable] = None
        for k, v in local_scope.items():
            if callable(v) and not k.startswith("_"):
                func = v
                break

        if not func:
            return False, "No valid callable function discovered in synthesized code."

        # Wrap in async coroutine handler
        async def async_wrapper(*args, **kwargs):
            import inspect
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        # 3. Register in Tool Registry
        tool_registry.register(
            name=clean_name,
            description=description,
            permission_level=permission,
            risk_level="LOW",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "options": {"type": "object"}}},
        )(async_wrapper)

        record = SynthesizedToolRecord(
            tool_name=clean_name,
            description=description,
            code_body=python_code,
            permission_level=permission.name,
            verified_safe=True,
        )
        self.synthesized_tools[clean_name] = record
        logger.info(f"Synthesized tool '{clean_name}' successfully verified and dynamically registered.")
        return True, f"Tool '{clean_name}' successfully compiled and registered."

    def list_synthesized_tools(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.synthesized_tools.values()]


tool_synthesizer = AutonomousToolSynthesizer()
