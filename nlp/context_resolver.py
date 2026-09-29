"""
Context Resolver for P.H.A.S.S.
Provides pronoun resolution and 3-tier memory context unification.
"""

from __future__ import annotations
import re
import json
import logging
from typing import Any, Dict, List, Optional
from core.lifelong_context import lifelong_context

logger = logging.getLogger("phass.nlp.context_resolver")


def resolve_context(query: str) -> str:
    """Resolves implicit pronouns and context references."""
    return lifelong_context.resolve_reference(query)


resolve_pronouns = resolve_context
