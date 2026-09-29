"""
Silent Debug Logger for P.H.A.S.S Sphere.
Directs internal execution logs, stack traces, JSON debug payloads,
and verification attempts into checkpoints/silent_logs/ with timestamps,
completely isolating internal machinery from the user chat interface.
"""

from __future__ import annotations
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("phass.core.silent_logger")


class SilentLogger:
    """Thread-safe silent logger for background execution data and traces."""

    def __init__(self, log_dir: str = "checkpoints/silent_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_log_file(self) -> Path:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return self.log_dir / f"silent_execution_{today_str}.jsonl"

    def log(
        self,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        raw_trace: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Silently appends execution details to the daily silent log."""
        merged_details = dict(details or {})
        merged_details.update(kwargs)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "message": message,
            "details": merged_details,
            "raw_trace": raw_trace,
            "error": error,
        }
        try:
            log_file = self._get_log_file()
            line = json.dumps(record, ensure_ascii=False)
            with self._lock:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            logger.debug(f"Silent logger fallback failed: {e}")
        return record

    def log_suppressed_internal(self, raw_text: str, user_query: Optional[str] = None) -> None:
        """Specifically records internal planner/executor text stripped before reaching the user."""
        self.log(
            category="suppressed_internal_log",
            message="Internal execution log suppressed from UI",
            details={"user_query": user_query, "raw_content": raw_text},
        )


silent_logger = SilentLogger()
