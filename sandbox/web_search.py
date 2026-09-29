"""
Web Search Tool for P.H.A.S.S.
Provides web information retrieval, Wikipedia fallback, and encyclopedic search.
"""

from __future__ import annotations
import re
import json
import logging
from typing import Any, Dict, List, Optional
from tools.builtin_tools import web_search as _builtin_web_search

logger = logging.getLogger("phass.tools.web_search")


def sanitize_query(query: str) -> str:
    """Sanitizes search query using regex."""
    return re.sub(r"\s+", " ", query.strip())


async def web_search(query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
    """Autonomous search tool that executes sanitization via re."""
    clean_q = sanitize_query(query)
    return await _builtin_web_search(clean_q, max_results=max_results, **kwargs)


__all__ = ["web_search", "sanitize_query"]
