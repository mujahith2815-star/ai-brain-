"""
Tool Registry for P.H.A.S.S Sphere.
Defines tool schemas, execution interfaces, and self-documenting capabilities.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional
import inspect
from .permissions import PermissionLevel


@dataclass
class ToolDefinition:
    name: str
    description: str
    permission_level: PermissionLevel
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, Dict[str, Any]]]
    verifier: Optional[Callable[[Dict[str, Any]], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "risk_level": self.risk_level,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: Any = "",
        permission_level: Any = PermissionLevel.READ,
        risk_level: str = "LOW",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        verifier: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        if callable(description):
            func = description
            desc = func.__doc__ or name
            schema = permission_level if isinstance(permission_level, dict) else (input_schema or {})
            if "properties" not in schema:
                schema = {"type": "object", "properties": schema}
            tool_def = ToolDefinition(
                name=name,
                description=desc,
                permission_level=PermissionLevel.READ if not isinstance(permission_level, PermissionLevel) else permission_level,
                risk_level=risk_level,
                input_schema=schema,
                output_schema=output_schema or {"type": "object", "properties": {}},
                handler=func,
                verifier=verifier,
            )
            self._tools[name] = tool_def
            return func

        def decorator(func: Callable[..., Any]):
            tool_def = ToolDefinition(
                name=name,
                description=description,
                permission_level=permission_level if isinstance(permission_level, PermissionLevel) else PermissionLevel.READ,
                risk_level=risk_level,
                input_schema=input_schema or {"type": "object", "properties": {}},
                output_schema=output_schema or {"type": "object", "properties": {}},
                handler=func,
                verifier=verifier,
            )
            self._tools[name] = tool_def
            return func
        return decorator

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self.get_tool(name)

    def get_description(self, name: str) -> Optional[str]:
        tool = self.get_tool(name)
        return tool.description if tool else None

    def execute(self, name: str, *args, **kwargs) -> Any:
        if args and isinstance(args[0], dict):
            kwargs = {**args[0], **kwargs}
        tool_def = self.get_tool(name)
        if not tool_def:
            return {"status": "ERROR", "error": f"Tool {name} not found."}
        if inspect.iscoroutinefunction(tool_def.handler):
            import asyncio
            try:
                return asyncio.run(tool_def.handler(**kwargs))
            except RuntimeError:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, tool_def.handler(**kwargs)).result()
        return tool_def.handler(**kwargs)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    def list_names(self) -> List[str]:
        return list(self._tools.keys())


tool_registry = ToolRegistry()

