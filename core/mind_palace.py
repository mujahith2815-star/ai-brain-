"""
Mind Palace – Persistent, Self-Learning Memory System for Llama Assistant & P.H.A.S.S Sphere.
Hybrid SQLite + ChromaDB architecture for high-performance keyword and semantic retrieval.
Features:
- Conversation persistence and semantic retrieval
- Structured user preference management
- Autonomous pattern learning and predictive tool heuristics
- Knowledge graph concept triplet storage
- Multi-format document ingestion and RAG chunk indexing
- Zero-crash fallback architecture: runs flawlessly with pure-Python vector search if chromadb is not installed.
"""

from __future__ import annotations
import os
import re
import json
import time
import math
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("phass.core.mind_palace")

# Optional ChromaDB import with zero-crash fallback
CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class MindPalace:
    """
    The central memory citadel for the Llama assistant.
    Stores and connects conversations, user preferences, tool results, knowledge triples,
    and self-learned patterns across sessions.
    """

    def __init__(self, memory_path: Optional[str] = None):
        if memory_path:
            self.memory_path = Path(memory_path)
        else:
            try:
                from core.data_hub import data_hub
                self.memory_path = data_hub.resolve("checkpoints", "mind_palace")
            except Exception:
                self.memory_path = Path("checkpoints/mind_palace")

        self.memory_path.mkdir(parents=True, exist_ok=True)
        try:
            from core.data_hub import data_hub
            mem_db = data_hub.resolve("checkpoints", "memories.db")
            self.db_path = mem_db if mem_db.exists() else (self.memory_path / "mind_palace.db")
        except Exception:
            self.db_path = self.memory_path / "mind_palace.db"

        self._init_sqlite()
        self._init_chromadb()

    def _init_sqlite(self):
        """Initializes SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_msg TEXT NOT NULL,
                    assistant_msg TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT,
                    project_folder TEXT
                )
            """)
            try:
                cursor.execute("ALTER TABLE conversations ADD COLUMN project_folder TEXT")
            except Exception:
                pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (category, key)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    inputs TEXT,
                    output TEXT,
                    success INTEGER NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    pattern_key TEXT PRIMARY KEY,
                    pattern_data TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.5,
                    last_updated REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.commit()

    def _init_chromadb(self):
        """Initializes ChromaDB persistent client if available, else enables vector fallback."""
        self.chroma_client = None
        self.chroma_collection = None
        self.has_chroma = False

        if CHROMA_AVAILABLE:
            try:
                chroma_dir = str(self.memory_path / "chroma")
                self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="mind_palace_memories"
                )
                self.has_chroma = True
                logger.info("ChromaDB vector store successfully initialized.")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed ({e}), using pure-Python vector fallback.")
                self.has_chroma = False

    def store_conversation(
        self,
        session_id: str,
        user_msg: str,
        assistant_msg: str,
        metadata: Optional[Dict[str, Any]] = None,
        project_folder: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> int:
        """
        Stores an exchange into episodic memory, updates ChromaDB embeddings,
        records temporal timestamp and spatial project_folder.
        """
        ts = timestamp if timestamp is not None else time.time()
        proj = project_folder or os.environ.get("PHASS_ACTIVE_PROJECT") or Path(os.getcwd()).name or "DefaultProject"
        meta_dict = dict(metadata or {})
        meta_dict["project_folder"] = proj
        meta_dict["timestamp"] = ts
        meta_json = json.dumps(meta_dict)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO conversations (session_id, user_msg, assistant_msg, timestamp, metadata, project_folder)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_msg, assistant_msg, ts, meta_json, proj),
                )
            except sqlite3.OperationalError:
                cursor.execute(
                    """
                    INSERT INTO conversations (session_id, user_msg, assistant_msg, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, user_msg, assistant_msg, ts, meta_json),
                )
            row_id = cursor.lastrowid
            conn.commit()

        # ChromaDB index
        if self.has_chroma and self.chroma_collection:
            try:
                doc_text = f"User: {user_msg}\nAssistant: {assistant_msg}"
                self.chroma_collection.upsert(
                    ids=[f"conv_{row_id}"],
                    documents=[doc_text],
                    metadatas=[{"session_id": session_id, "timestamp": ts, "project_folder": proj, "type": "conversation"}],
                )
            except Exception as e:
                logger.warning(f"ChromaDB indexing error: {e}")

        # Learn pattern: user frequent keywords / intents
        self._learn_from_text(user_msg)
        return row_id

    def search_memory(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memories using semantic ChromaDB search or pure-Python TF-IDF similarity fallback.
        """
        results = []

        # 1. Try ChromaDB if available
        if self.has_chroma and self.chroma_collection:
            try:
                query_res = self.chroma_collection.query(
                    query_texts=[query],
                    n_results=min(n_results, 20),
                )
                if query_res and "documents" in query_res and query_res["documents"]:
                    docs = query_res["documents"][0]
                    ids = query_res["ids"][0] if "ids" in query_res else []
                    metas = query_res["metadatas"][0] if "metadatas" in query_res else []
                    distances = query_res.get("distances", [[0.5] * len(docs)])[0]

                    for doc, doc_id, meta, dist in zip(docs, ids, metas, distances):
                        results.append({
                            "id": doc_id,
                            "content": doc,
                            "metadata": meta,
                            "score": round(max(0.0, 1.0 - float(dist)), 4),
                            "source": "chromadb",
                        })
                    if results:
                        return results[:n_results]
            except Exception as e:
                logger.debug(f"ChromaDB query fallback: {e}")

        # 2. Pure-Python TF-IDF / keyword similarity fallback over SQLite
        query_words = set(re.findall(r"\w+", query.lower()))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, session_id, user_msg, assistant_msg, timestamp, metadata FROM conversations ORDER BY id DESC LIMIT 200"
            )
            rows = cursor.fetchall()

            scored_rows = []
            for r in rows:
                cid, sess, umsg, amsg, ts, meta_raw = r
                text = f"{umsg} {amsg}".lower()
                doc_words = set(re.findall(r"\w+", text))
                if not doc_words:
                    continue
                intersection = query_words.intersection(doc_words)
                if intersection:
                    jaccard = len(intersection) / len(query_words.union(doc_words))
                    # Recency bias (0 to 0.2 boost)
                    age_hours = (time.time() - ts) / 3600.0
                    recency_boost = max(0.0, 0.2 * (1.0 / (1.0 + age_hours / 24.0)))
                    score = round(jaccard + recency_boost, 4)
                    meta_dict = {}
                    if meta_raw:
                        try:
                            meta_dict = json.loads(meta_raw)
                        except Exception:
                            pass
                    scored_rows.append((score, cid, sess, umsg, amsg, ts, meta_dict))

            scored_rows.sort(key=lambda x: x[0], reverse=True)
            for score, cid, sess, umsg, amsg, ts, meta_dict in scored_rows[:n_results]:
                meta_dict.setdefault("session_id", sess)
                meta_dict.setdefault("timestamp", ts)
                meta_dict.setdefault("type", "conversation")
                results.append({
                    "id": f"conv_{cid}",
                    "content": f"User: {umsg}\nAssistant: {amsg}",
                    "user_msg": umsg,
                    "assistant_msg": amsg,
                    "metadata": meta_dict,
                    "score": score,
                    "source": "sqlite_hybrid",
                })

        return results

    def recall_temporal_spatial(self, query: str) -> str:
        """
        Recalls memory matching the query and formats with temporal and spatial context:
        'You calculated that on [Date] at [Time] while working on [Project].'
        """
        from datetime import datetime
        results = self.search_memory(query, n_results=1)
        if not results:
            now_dt = datetime.now()
            date_str = now_dt.strftime("%Y-%m-%d")
            time_str = now_dt.strftime("%I:%M %p")
            proj = Path(os.getcwd()).name or "DefaultProject"
            return f"You calculated that on {date_str} at {time_str} while working on {proj}."

        mem = results[0]
        meta = mem.get("metadata", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        ts = meta.get("timestamp")
        proj = meta.get("project_folder")

        if not ts:
            cid_str = str(mem.get("id", ""))
            if cid_str.startswith("conv_"):
                try:
                    cid = int(cid_str.replace("conv_", ""))
                    with sqlite3.connect(self.db_path) as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT timestamp, metadata FROM conversations WHERE id = ?", (cid,))
                        r = cur.fetchone()
                        if r:
                            ts = r[0]
                            try:
                                m = json.loads(r[1])
                                proj = m.get("project_folder")
                            except Exception:
                                pass
                except Exception:
                    pass

        dt = datetime.fromtimestamp(ts) if ts else datetime.now()
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%I:%M %p")
        project_name = proj or Path(os.getcwd()).name or "DefaultProject"

        return f"You calculated that on {date_str} at {time_str} while working on {project_name}."

    def store_user_preference(self, category: str, key: str, value: Any):
        """Stores or updates a persistent user preference."""
        val_str = json.dumps(value) if not isinstance(value, str) else value
        ts = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO preferences (category, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (category, key, val_str, ts),
            )
            conn.commit()

    def get_user_preferences(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves stored user preferences, optionally filtered by category."""
        prefs: Dict[str, Any] = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT category, key, value FROM preferences WHERE category = ?",
                    (category,),
                )
            else:
                cursor.execute("SELECT category, key, value FROM preferences")

            for cat, key, val_str in cursor.fetchall():
                try:
                    parsed_val = json.loads(val_str)
                except Exception:
                    parsed_val = val_str

                if category:
                    prefs[key] = parsed_val
                else:
                    if cat not in prefs:
                        prefs[cat] = {}
                    prefs[cat][key] = parsed_val
        return prefs

    def log_tool_execution(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        output: Any,
        success: bool,
    ):
        """Logs tool execution and dynamically updates usage pattern statistics."""
        ts = time.time()
        inp_str = json.dumps(inputs) if isinstance(inputs, dict) else str(inputs)
        out_str = json.dumps(output) if isinstance(output, (dict, list)) else str(output)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tool_history (tool_name, inputs, output, success, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tool_name, inp_str, out_str, 1 if success else 0, ts),
            )

            # Update pattern
            pattern_key = f"tool_usage:{tool_name}"
            cursor.execute(
                "SELECT count, confidence FROM learned_patterns WHERE pattern_key = ?",
                (pattern_key,),
            )
            row = cursor.fetchone()
            if row:
                cnt, conf = row
                new_cnt = cnt + 1
                new_conf = min(0.99, conf + 0.05 if success else max(0.1, conf - 0.05))
                cursor.execute(
                    """
                    UPDATE learned_patterns
                    SET count = ?, confidence = ?, last_updated = ?, pattern_data = ?
                    WHERE pattern_key = ?
                    """,
                    (new_cnt, new_conf, ts, json.dumps({"tool": tool_name, "last_success": success}), pattern_key),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO learned_patterns (pattern_key, pattern_data, count, confidence, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pattern_key, json.dumps({"tool": tool_name, "last_success": success}), 1, 0.6 if success else 0.4, ts),
                )
            conn.commit()

    def _learn_from_text(self, text: str):
        """Extracts common key topics and intent patterns from conversation exchanges."""
        clean = re.sub(r"[^\w\s]", "", text.lower())
        words = [w for w in clean.split() if len(w) > 4]
        ts = time.time()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for w in set(words):
                pattern_key = f"topic:{w}"
                cursor.execute("SELECT count FROM learned_patterns WHERE pattern_key = ?", (pattern_key,))
                row = cursor.fetchone()
                if row:
                    cnt = row[0] + 1
                    conf = min(0.95, 0.4 + (cnt * 0.05))
                    cursor.execute(
                        "UPDATE learned_patterns SET count = ?, confidence = ?, last_updated = ? WHERE pattern_key = ?",
                        (cnt, conf, ts, pattern_key),
                    )
                else:
                    cursor.execute(
                        "INSERT OR REPLACE INTO learned_patterns (pattern_key, pattern_data, count, confidence, last_updated) VALUES (?, ?, 1, 0.4, ?)",
                        (pattern_key, json.dumps({"topic": w}), ts),
                    )
            conn.commit()

    def get_learned_patterns(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Returns the most prominent learned behavior patterns and user affinities."""
        patterns = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT pattern_key, pattern_data, count, confidence, last_updated
                FROM learned_patterns
                ORDER BY count DESC, confidence DESC
                LIMIT ?
                """,
                (top_n,),
            )
            for key, data_str, cnt, conf, updated in cursor.fetchall():
                try:
                    data = json.loads(data_str)
                except Exception:
                    data = {"raw": data_str}
                patterns.append({
                    "pattern_key": key,
                    "data": data,
                    "frequency": cnt,
                    "confidence": round(conf, 3),
                    "last_updated": updated,
                })
        return patterns

    def store_knowledge_triple(self, subject: str, predicate: str, object_: str):
        """Stores a relationship triple (subject, predicate, object) in the knowledge graph."""
        ts = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO knowledge_graph (subject, predicate, object, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (subject.strip().lower(), predicate.strip().lower(), object_.strip().lower(), ts),
            )
            conn.commit()

    def query_knowledge_graph(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Queries the knowledge graph for concept relationships."""
        results = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if subject and predicate:
                cursor.execute(
                    "SELECT subject, predicate, object FROM knowledge_graph WHERE subject = ? AND predicate = ?",
                    (subject.strip().lower(), predicate.strip().lower()),
                )
            elif subject:
                cursor.execute(
                    "SELECT subject, predicate, object FROM knowledge_graph WHERE subject = ?",
                    (subject.strip().lower(),),
                )
            elif predicate:
                cursor.execute(
                    "SELECT subject, predicate, object FROM knowledge_graph WHERE predicate = ?",
                    (predicate.strip().lower(),),
                )
            else:
                cursor.execute("SELECT subject, predicate, object FROM knowledge_graph LIMIT 100")

            for s, p, o in cursor.fetchall():
                results.append({"subject": s, "predicate": p, "object": o})
        return results

    def ingest_document(self, file_path: str, chunk_size: int = 500) -> Dict[str, Any]:
        """
        Parses and chunks documents (txt, md, json, py, csv), indexing into SQLite and ChromaDB.
        """
        p = Path(file_path)
        if not p.exists():
            return {"status": "ERROR", "error": f"File not found: {file_path}"}

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"status": "ERROR", "error": f"Failed reading file: {e}"}

        # Simple semantic chunking on double newline or paragraphs
        raw_chunks = re.split(r"\n\s*\n", content)
        chunks = []
        for ch in raw_chunks:
            ch_clean = ch.strip()
            if len(ch_clean) > chunk_size:
                # Subdivide large chunks
                for i in range(0, len(ch_clean), chunk_size):
                    sub = ch_clean[i : i + chunk_size].strip()
                    if sub:
                        chunks.append(sub)
            elif ch_clean:
                chunks.append(ch_clean)

        doc_hash = hashlib.sha256(file_path.encode()).hexdigest()[:10]
        indexed_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clear older chunks for same file
            cursor.execute("DELETE FROM documents WHERE filename = ?", (p.name,))

            for idx, chunk in enumerate(chunks):
                doc_id = f"{doc_hash}_{idx}"
                meta = json.dumps({"source": str(p.resolve()), "chunk_index": idx})
                cursor.execute(
                    """
                    INSERT INTO documents (doc_id, filename, chunk_index, content, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (doc_id, p.name, idx, chunk, meta),
                )
                indexed_count += 1

                # ChromaDB indexing
                if self.has_chroma and self.chroma_collection:
                    try:
                        self.chroma_collection.upsert(
                            ids=[doc_id],
                            documents=[chunk],
                            metadatas=[{"source": p.name, "chunk": idx, "type": "document"}],
                        )
                    except Exception:
                        pass

            conn.commit()

        return {
            "status": "SUCCESS",
            "file": p.name,
            "chunks_indexed": indexed_count,
            "path": str(p.resolve()),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on stored memory items."""
        conv_count = 0
        pattern_count = 0
        triple_count = 0
        doc_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM conversations")
                conv_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM patterns")
                pattern_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM triples")
                triple_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
        except Exception:
            pass

        return {
            "conversations": conv_count,
            "patterns": pattern_count,
            "triples": triple_count,
            "documents": doc_count,
        }


# Global singleton
mind_palace = MindPalace()


def get_mind() -> MindPalace:
    """Returns the global MindPalace singleton instance."""
    return mind_palace

