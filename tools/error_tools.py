"""
Error Inspection & Logging Tools for Orvix Sphere.
Provides registered tools for agents to manually log errors, inspect recent error logs,
and retrieve error statistics.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
try:
    from logging.error_logger import error_logger
except (ImportError, ModuleNotFoundError):
    import logging
    from pathlib import Path
    _proj_log = str(Path(__file__).resolve().parent.parent / "logging")
    if hasattr(logging, "__path__") and _proj_log not in logging.__path__:
        logging.__path__.append(_proj_log)
    from logging.error_logger import error_logger
from tools.registry import tool_registry
from tools.permissions import PermissionLevel


@tool_registry.register(
    name="log_error",
    description="Manually logs an error or operational fault with category and context for human-in-the-loop Antigravity repair.",
    permission_level=PermissionLevel.CREATE,
    risk_level="LOW",
    input_schema={
        "type": "object",
        "properties": {
            "error_message": {"type": "string", "description": "The description or text of the error."},
            "category": {"type": "string", "description": "Category of error (e.g. TOOL_FAILURE, SYSTEM, NETWORK).", "default": "MANUAL"},
            "context": {"type": "object", "description": "Optional dictionary containing operational context."},
        },
        "required": ["error_message"],
    },
)
async def log_error(
    error_message: str,
    category: str = "MANUAL",
    context: Optional[Dict[str, Any]] = None,
    error_type: Optional[str] = None,
    source_file: Optional[str] = None,
    traceback: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Manually logs an error into errors.db."""
    payload = {
        "category": category,
        "error_type": error_type or "ManualReportedError",
        "error_message": error_message,
        "source_file": source_file or kwargs.get("source", ""),
        "traceback": traceback or "",
        "context": context or {},
    }
    err_id = error_logger.log(payload)
    return {
        "status": "SUCCESS",
        "error_id": err_id,
        "message": f"Error successfully logged under ID {err_id}. Use '/errors {err_id}' to inspect.",
    }


@tool_registry.register(
    name="get_errors",
    description="Retrieves a list of recent error records logged in the system for self-inspection.",
    permission_level=PermissionLevel.READ,
    risk_level="LOW",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximum number of recent errors to retrieve (default 10).", "default": 10},
        },
    },
)
async def get_errors(limit: int = 10, **kwargs) -> Dict[str, Any]:
    """Retrieves recent errors from errors.db."""
    records = error_logger.get_recent(limit=limit)
    return {
        "status": "SUCCESS",
        "count": len(records),
        "errors": records,
    }


@tool_registry.register(
    name="get_error_stats",
    description="Returns aggregate error statistics and counts grouped by category.",
    permission_level=PermissionLevel.READ,
    risk_level="LOW",
    input_schema={"type": "object", "properties": {}},
)
async def get_error_stats(**kwargs) -> Dict[str, Any]:
    """Computes error statistics from errors.db."""
    all_recent = error_logger.get_recent(limit=100)
    top_errors = error_logger.get_top_errors(days=30, limit=10)

    category_counts: Dict[str, int] = {}
    total_occurrences = 0
    for e in all_recent:
        cat = e.get("category", "GENERAL")
        cnt = e.get("count", 1)
        category_counts[cat] = category_counts.get(cat, 0) + cnt
        total_occurrences += cnt

    return {
        "status": "SUCCESS",
        "total_unique_errors": len(all_recent),
        "total_error_occurrences": total_occurrences,
        "by_category": category_counts,
        "top_frequent": [
            {"id": t["id"], "type": t["error_type"], "count": t["count"], "msg": t["error_message"][:60]}
            for t in top_errors[:5]
        ],
    }
