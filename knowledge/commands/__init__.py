"""
Orvix Command Knowledge Base and Terminal Mastery Package.
Houses 350+ pre-indexed terminal commands, auto-ingestion pipeline,
command history analytics, and autonomous feedback learner.
"""

from .load_commands import (
    load_all_commands,
    get_command_by_name,
    search_commands,
    get_by_category,
    get_by_shell,
    get_by_tag,
    get_all_categories,
    get_command_summary,
)
from .auto_ingest import ensure_commands_indexed, is_indexed
from .command_history import (
    log_command,
    get_history,
    get_most_used_commands,
    get_failed_commands,
    get_success_rate,
    record_feedback,
)
from .auto_learner import (
    learn_from_history,
    load_learned_commands,
    start_background_learner,
    stop_background_learner,
)

from .core.load_core import (
    load_core_commands,
    get_core_command,
    search_core_commands,
    get_core_categories,
    get_core_by_category,
)
from .command_patterns import (
    log_sequence,
    promote_to_pattern,
    get_all_patterns,
    get_pattern_by_name,
    get_similar_patterns,
    suggest_chain,
    record_pattern_usage,
)
from .pattern_learner import (
    PatternLearner,
    start_pattern_learner,
    stop_pattern_learner,
)
from .orchestrator import (
    bootstrap_command_brain,
)

__all__ = [
    "load_all_commands",
    "get_command_by_name",
    "search_commands",
    "get_by_category",
    "get_by_shell",
    "get_by_tag",
    "get_all_categories",
    "get_command_summary",
    "ensure_commands_indexed",
    "is_indexed",
    "log_command",
    "get_history",
    "get_most_used_commands",
    "get_failed_commands",
    "get_success_rate",
    "record_feedback",
    "learn_from_history",
    "load_learned_commands",
    "start_background_learner",
    "stop_background_learner",
    "load_core_commands",
    "get_core_command",
    "search_core_commands",
    "get_core_categories",
    "get_core_by_category",
    "log_sequence",
    "promote_to_pattern",
    "get_all_patterns",
    "get_pattern_by_name",
    "get_similar_patterns",
    "suggest_chain",
    "record_pattern_usage",
    "PatternLearner",
    "start_pattern_learner",
    "stop_pattern_learner",
    "bootstrap_command_brain",
]
