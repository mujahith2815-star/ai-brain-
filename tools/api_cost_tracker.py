"""
API Usage and Cost Tracker for Google Gemini & Cloud Engines.
Tracks token consumption, request counts, rate limiting, and estimated expenditure.
Persists aggregate metrics in knowledge/agent_memory.db under the `api_usage` table.
"""

from __future__ import annotations
import os
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config.api_config import api_config

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "knowledge", "agent_memory.db")
)
_LOCK = threading.RLock()


class ApiCostTracker:
    """Tracks token consumption, daily request quotas, and per-minute rate limits."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._request_timestamps: deque[float] = deque()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates api_usage table if it does not already exist."""
        with _LOCK:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        requests INTEGER DEFAULT 0,
                        tokens_in INTEGER DEFAULT 0,
                        tokens_out INTEGER DEFAULT 0,
                        model TEXT NOT NULL,
                        cost REAL DEFAULT 0.0,
                        last_updated TEXT,
                        UNIQUE(date, model)
                    )
                """)
                conn.commit()

    def _get_today_str(self) -> str:
        """Returns current UTC date string (YYYY-MM-DD)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def check_rate_limit(self, max_rpm: Optional[int] = None) -> Tuple[bool, float]:
        """
        Evaluates whether a new request can proceed within the rate limit window (60s).
        Returns:
            (allowed: bool, wait_seconds: float)
        """
        rpm_limit = max_rpm or api_config.rate_limit_rpm
        now = time.time()
        window_start = now - 60.0

        with _LOCK:
            # Purge timestamps older than 60 seconds
            while self._request_timestamps and self._request_timestamps[0] < window_start:
                self._request_timestamps.popleft()

            current_count = len(self._request_timestamps)
            if current_count >= rpm_limit:
                oldest = self._request_timestamps[0]
                wait_time = max(0.1, round(60.0 - (now - oldest), 2))
                return False, wait_time

            return True, 0.0

    def record_request_start(self) -> None:
        """Records timestamp of an in-flight API request for rate limiting."""
        with _LOCK:
            now = time.time()
            self._request_timestamps.append(now)

    def log_request(
        self,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> None:
        """
        Records completed API call metrics into SQLite api_usage table.
        For Gemini Flash Free Tier, cost is normally $0.00.
        """
        today = self._get_today_str()
        now_iso = datetime.now(timezone.utc).isoformat()

        with _LOCK:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO api_usage (date, requests, tokens_in, tokens_out, model, cost, last_updated)
                    VALUES (?, 1, ?, ?, ?, ?, ?)
                    ON CONFLICT(date, model) DO UPDATE SET
                        requests = requests + 1,
                        tokens_in = tokens_in + excluded.tokens_in,
                        tokens_out = tokens_out + excluded.tokens_out,
                        cost = cost + excluded.cost,
                        last_updated = excluded.last_updated
                """, (today, tokens_in, tokens_out, model, cost, now_iso))
                conn.commit()

    def get_usage_today(self) -> Dict[str, Any]:
        """
        Summarizes API usage for the current calendar day (UTC).
        Returns requests, tokens, cost, and rate-limit headroom.
        """
        today = self._get_today_str()
        now = time.time()
        window_start = now - 60.0

        with _LOCK:
            # Clean rolling window
            while self._request_timestamps and self._request_timestamps[0] < window_start:
                self._request_timestamps.popleft()
            rpm_active = len(self._request_timestamps)

            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        COALESCE(SUM(requests), 0) AS total_requests,
                        COALESCE(SUM(tokens_in), 0) AS total_tokens_in,
                        COALESCE(SUM(tokens_out), 0) AS total_tokens_out,
                        COALESCE(SUM(cost), 0.0) AS total_cost
                    FROM api_usage
                    WHERE date = ?
                """, (today,))
                row = cursor.fetchone()

                # Model breakdown
                cursor_models = conn.execute("""
                    SELECT model, requests, tokens_in, tokens_out, cost
                    FROM api_usage
                    WHERE date = ?
                """, (today,))
                model_breakdown = [dict(r) for r in cursor_models.fetchall()]

        total_reqs = row["total_requests"] if row else 0
        tokens_in = row["total_tokens_in"] if row else 0
        tokens_out = row["total_tokens_out"] if row else 0
        total_tokens = tokens_in + tokens_out
        total_cost = row["total_cost"] if row else 0.0

        rpm_limit = api_config.rate_limit_rpm
        rpm_remaining = max(0, rpm_limit - rpm_active)

        # Warning evaluation (80% of rate limit or daily limit)
        warning = None
        rpm_threshold = max(1, int(rpm_limit * 0.8))
        if rpm_active >= rpm_threshold:
            warning = f"⚠️ Rate limit warning (>=80%): {rpm_active}/{rpm_limit} requests in current minute window."
        elif total_reqs >= 1200:
            warning = f"⚠️ Daily quota warning (>=80%): {total_reqs}/1500 requests used today."

        return {
            "date": today,
            "requests_today": total_reqs,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost, 4),
            "current_rpm": rpm_active,
            "rpm_limit": rpm_limit,
            "rpm_remaining": rpm_remaining,
            "warning": warning,
            "models": model_breakdown,
        }

    def reset_daily(self) -> None:
        """Clears rolling timestamps and resets daily stats if date transitioned."""
        with _LOCK:
            self._request_timestamps.clear()

    def reset_usage_for_test(self) -> None:
        """Utility method for unit testing to clear recorded usage."""
        with _LOCK:
            self._request_timestamps.clear()
            with self._get_connection() as conn:
                conn.execute("DELETE FROM api_usage")
                conn.commit()


# Singleton instance
api_cost_tracker = ApiCostTracker()
