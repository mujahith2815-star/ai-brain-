"""
Database Management for P.H.A.S.S Sphere.
Initializes SQLite schemas for memory, experiences, and audit logs.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger("phass.database")


class DatabaseManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_db = self.data_dir / "phass_memory.db"
        self.experience_db = self.data_dir / "phass_experiences.db"
        self._init_schemas()

    def _init_schemas(self) -> None:
        try:
            with sqlite3.connect(self.memory_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_records (
                        id TEXT PRIMARY KEY,
                        tier TEXT,
                        content TEXT,
                        tags TEXT,
                        importance REAL,
                        access_count INTEGER,
                        created_at TEXT,
                        last_accessed TEXT
                    )
                """)
                conn.commit()
            logger.info("Initialized Memory Database Schema.")
        except Exception as e:
            logger.warning(f"Failed to init SQLite memory schema: {e}")


db_manager = DatabaseManager()
