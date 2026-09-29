"""
Tool Adapter converting MCP tool schemas into Orvix Sphere tool_registry format.
Namespaces external tools as mcp__{server}__{tool} and integrates with PermissionLevel.
"""

import logging
from typing import Optional, Dict, Any

from tools.registry import tool_registry, PermissionLevel
from mcp.mcp_manager import MCPManager

logger = logging.getLogger("orvix.mcp.adapter")


class MCPToolAdapter:
    """
    Translates discovered MCP tool schemas into callable internal tool functions
    and registers them with tool_registry.
    """

    def __init__(self, manager: Optional[MCPManager] = None):
        self.manager = manager or MCPManager()

    def register_all(self, registry=None) -> int:
        """
        Registers all tools from every connected MCP server into tool_registry.
        Returns the count of registered MCP tools.
        """
        target_registry = registry or tool_registry
        all_tools = self.manager.get_all_tools()
        count = 0

        for server_name, tools in all_tools.items():
            for tool in tools:
                tool_name = tool.get("name", "")
                if not tool_name:
                    continue

                namespaced_name = f"mcp__{server_name}__{tool_name}"
                description = f"[MCP:{server_name}] {tool.get('description', 'External MCP tool')}"
                input_schema = tool.get("inputSchema", {})

                # Derive permission level
                low_name = tool_name.lower()
                if any(verb in low_name for verb in ("read", "get", "list", "query", "select", "fetch")):
                    perm = PermissionLevel.READ
                    risk = "LOW"
                elif any(verb in low_name for verb in ("write", "create", "insert")):
                    perm = PermissionLevel.CREATE
                    risk = "MEDIUM"
                elif any(verb in low_name for verb in ("update", "delete", "drop", "edit", "move")):
                    perm = PermissionLevel.MODIFY
                    risk = "MEDIUM"
                else:
                    perm = PermissionLevel.EXECUTE
                    risk = "MEDIUM"

                def _make_handler(s_name: str, t_name: str):
                    async def _handler(**kwargs) -> Dict[str, Any]:
                        return self.manager.call_tool(s_name, t_name, kwargs)
                    return _handler

                handler_func = _make_handler(server_name, tool_name)
                handler_func.__name__ = namespaced_name
                handler_func.__doc__ = description

                try:
                    reg_dec = target_registry.register(
                        name=namespaced_name,
                        description=description,
                        input_schema=input_schema,
                        permission_level=perm,
                        risk_level=risk
                    )
                    reg_dec(handler_func)
                    count += 1
                except Exception as e:
                    logger.debug(f"Tool registration for '{namespaced_name}' notice: {e}")

        logger.info(f"[MCPToolAdapter] Successfully registered {count} external MCP tool(s).")
        return count
