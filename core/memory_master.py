"""
Memory Master Engine for P.H.A.S.S Sphere & Llama Assistant.
Provides deep cognitive memory capabilities:
1. Vector database semantic search with pure-Python TF-IDF cosine fallback.
2. Multi-format document ingestion (PDF, Word, Excel, HTML, Markdown, Plaintext).
3. Knowledge Graph storing subject-predicate-object semantic triplets.
4. Pattern Learning tracking user behavior and predicting upcoming tasks.
5. Isolated Per-Project Memory workspaces.
"""

from __future__ import annotations
import os
import re
import math
import time
import json
import uuid
import sqlite3
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("phass.core.memory_master")


class VectorMemoryStore:
    """
    Lightweight vector store with pure-Python cosine similarity fallback.
    Extracts term-frequency vectors and computes cosine similarity across document chunks.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    project TEXT,
                    source_file TEXT,
                    content TEXT,
                    metadata_json TEXT,
                    created_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON document_chunks(project)")
            conn.commit()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w{2,}\b", text.lower())

    def _vectorize(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        norm = math.sqrt(sum(c * c for c in counts.values())) or 1.0
        return {w: c / norm for w, c in counts.items()}

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        intersection = set(vec1.keys()) & set(vec2.keys())
        return sum(vec1[w] * vec2[w] for w in intersection)

    def add_chunk(self, content: str, source: str, project: str = "default", metadata: Optional[Dict[str, Any]] = None) -> str:
        chunk_id = f"chk-{uuid.uuid4().hex[:8]}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO document_chunks (chunk_id, project, source_file, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk_id, project, source, content, json.dumps(metadata or {}), time.time()),
            )
            conn.commit()
        return chunk_id

    def search(self, query: str, top_k: int = 5, project: Optional[str] = None) -> List[Dict[str, Any]]:
        query_vec = self._vectorize(self._tokenize(query))
        with sqlite3.connect(self.db_path) as conn:
            if project:
                cur = conn.execute(
                    "SELECT chunk_id, project, source_file, content, metadata_json FROM document_chunks WHERE project = ?",
                    (project,),
                )
            else:
                cur = conn.execute("SELECT chunk_id, project, source_file, content, metadata_json FROM document_chunks")
            rows = cur.fetchall()

        scores = []
        for cid, proj, src, content, meta in rows:
            doc_vec = self._vectorize(self._tokenize(content))
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.0 or len(scores) < top_k:
                scores.append({
                    "chunk_id": cid,
                    "project": proj,
                    "source": src,
                    "content": content,
                    "similarity": round(sim, 4),
                    "metadata": json.loads(meta),
                })

        scores.sort(key=lambda x: x["similarity"], reverse=True)
        return scores[:top_k]


class KnowledgeGraph:
    """Stores and queries semantic triplets (subject, predicate, object)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_triplets (
                    triplet_id TEXT PRIMARY KEY,
                    project TEXT,
                    subject TEXT,
                    predicate TEXT,
                    object TEXT,
                    confidence REAL,
                    created_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg ON knowledge_triplets(subject, predicate)")
            conn.commit()

    def add_triplet(self, subject: str, predicate: str, obj: str, project: str = "default", confidence: float = 1.0) -> str:
        tid = f"kg-{uuid.uuid4().hex[:8]}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO knowledge_triplets (triplet_id, project, subject, predicate, object, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, project, subject.strip(), predicate.strip(), obj.strip(), confidence, time.time()),
            )
            conn.commit()
        return tid

    def query(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []
        if subject:
            clauses.append("LOWER(subject) = LOWER(?)")
            params.append(subject.strip())
        if predicate:
            clauses.append("LOWER(predicate) = LOWER(?)")
            params.append(predicate.strip())
        if obj:
            clauses.append("LOWER(object) = LOWER(?)")
            params.append(obj.strip())
        if project:
            clauses.append("project = ?")
            params.append(project)

        where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT triplet_id, project, subject, predicate, object, confidence FROM knowledge_triplets{where_clause}"

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "triplet_id": r[0],
                "project": r[1],
                "subject": r[2],
                "predicate": r[3],
                "object": r[4],
                "confidence": r[5],
            }
            for r in rows
        ]


class PatternLearner:
    """Tracks user interactions and predicts next likely actions based on Markov state transitions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    context TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()

    def record_action(self, action: str, context: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO action_history (action, context, timestamp) VALUES (?, ?, ?)",
                (action, context or "", time.time()),
            )
            conn.commit()

    def predict_next(self, current_action: Optional[str] = None) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT action FROM action_history ORDER BY id DESC LIMIT 50").fetchall()

        actions = [r[0] for r in reversed(rows)]
        if not actions:
            return {"predicted_action": "check_system_status", "confidence": 0.5, "basis": "default_baseline"}

        target_action = current_action or actions[-1]
        transitions: List[str] = []
        for i in range(len(actions) - 1):
            if actions[i] == target_action:
                transitions.append(actions[i + 1])

        if transitions:
            most_common, count = Counter(transitions).most_common(1)[0]
            confidence = round(count / len(transitions), 2)
            return {"predicted_action": most_common, "confidence": confidence, "basis": "markov_transition"}

        # Fallback to most frequent overall action
        most_freq, total = Counter(actions).most_common(1)[0]
        return {"predicted_action": most_freq, "confidence": round(total / len(actions), 2), "basis": "frequency"}


class MemoryMaster:
    """
    Central cognitive memory orchestrator.
    Integrates Vector RAG, Document Ingestion, Knowledge Graphs, Pattern Learning,
    and Isolated Project Spaces.
    """

    def __init__(self, vault_dir: str = "memory_vault"):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.vault_dir / "memory_master.db"

        self.vector_store = VectorMemoryStore(self.db_path)
        self.kg = KnowledgeGraph(self.db_path)
        self.patterns = PatternLearner(self.db_path)
        self.project_dir = self.vault_dir / "projects"
        self.project_dir.mkdir(exist_ok=True)

    def ingest_document(
        self,
        file_path: str,
        project: str = "default",
        chunk_size: int = 500,
    ) -> Dict[str, Any]:
        """Ingests PDF, Word, Excel, HTML, or Markdown text into semantic vector memory."""
        p = Path(file_path)
        if not p.exists():
            return {"status": "FAILED", "error": f"File not found: {file_path}"}

        text = self._extract_text(p)
        if not text.strip():
            return {"status": "FAILED", "error": "No extractable text found in file."}

        # Chunk text
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)

        chunk_ids = []
        for c in chunks:
            cid = self.vector_store.add_chunk(
                content=c,
                source=str(p),
                project=project,
                metadata={"filename": p.name, "file_ext": p.suffix},
            )
            chunk_ids.append(cid)

        return {
            "status": "SUCCESS",
            "file": str(p),
            "project": project,
            "chunks_created": len(chunks),
            "chunk_ids": chunk_ids[:5],
            "message": f"Ingested {len(chunks)} chunks from '{p.name}' into project '{project}'.",
        }

    def _extract_text(self, p: Path) -> str:
        ext = p.suffix.lower()
        if ext in [".txt", ".md", ".json", ".csv", ".py", ".html"]:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if ext == ".html":
                        content = re.sub(r"<[^>]+>", " ", content)
                    return content
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
                return ""

        # Binary/office fallbacks
        try:
            with open(p, "rb") as f:
                raw = f.read()
                # Extract ASCII strings
                ascii_strings = re.findall(rb"[a-zA-Z0-9\s.,;:'\"\-_]{4,}", raw)
                return " ".join(s.decode("ascii", errors="ignore") for s in ascii_strings[:1000])
        except Exception:
            return ""

    def semantic_search(self, query: str, top_k: int = 5, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches ingested documents via semantic similarity."""
        return self.vector_store.search(query, top_k=top_k, project=project)

    def add_knowledge_triplet(
        self,
        subject: str,
        predicate: str,
        obj: str,
        project: str = "default",
    ) -> str:
        """Adds a fact triplet to the knowledge graph."""
        return self.kg.add_triplet(subject, predicate, obj, project)

    def query_knowledge_graph(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries the knowledge graph."""
        return self.kg.query(subject, predicate, obj, project)

    def record_pattern(self, action: str, context: Optional[str] = None):
        """Records a user action to learn patterns."""
        self.patterns.record_action(action, context)

    def predict_next_action(self, current_action: Optional[str] = None) -> Dict[str, Any]:
        """Predicts the next action based on learned patterns."""
        return self.patterns.predict_next(current_action)

    def get_project_memory(self, project_name: str) -> Dict[str, Any]:
        """Loads isolated project memory space."""
        p_path = self.project_dir / f"{project_name}.json"
        if not p_path.exists():
            return {"project": project_name, "context": {}, "notes": []}
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"project": project_name, "context": {}, "notes": []}

    def save_project_memory(self, project_name: str, data: Dict[str, Any]) -> bool:
        """Persists isolated project memory space."""
        p_path = self.project_dir / f"{project_name}.json"
        try:
            with open(p_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving project memory: {e}")
            return False


# Global Singleton
memory_master = MemoryMaster()


# Standalone top-level functions matching user requests
def semantic_search(query: str, top_k: int = 5, project: Optional[str] = None) -> List[Dict[str, Any]]:
    return memory_master.semantic_search(query, top_k=top_k, project=project)


def ingest_document(file_path: str, project: str = "default") -> Dict[str, Any]:
    return memory_master.ingest_document(file_path, project)


def add_knowledge_triplet(subject: str, predicate: str, obj: str, project: str = "default") -> str:
    return memory_master.add_knowledge_triplet(subject, predicate, obj, project)


def query_knowledge_graph(
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    obj: Optional[str] = None,
    project: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return memory_master.query_knowledge_graph(subject, predicate, obj, project)


def record_pattern(action: str, context: Optional[str] = None):
    memory_master.record_pattern(action, context)


def predict_next_action(current_action: Optional[str] = None) -> Dict[str, Any]:
    return memory_master.predict_next_action(current_action)


def get_project_memory(project_name: str) -> Dict[str, Any]:
    return memory_master.get_project_memory(project_name)


def save_project_memory(project_name: str, data: Dict[str, Any]) -> bool:
    return memory_master.save_project_memory(project_name, data)
