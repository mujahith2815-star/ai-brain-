"""
Vector Store for P.H.A.S.S Sphere Knowledge Layer.
Provides semantic document indexing, persistent embedding storage,
and cosine similarity retrieval via sentence-transformers.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = PROJECT_ROOT / "knowledge" / "vector_store.json"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_LOG_FILE = LOGS_DIR / "vector_store.log"

logger = logging.getLogger("orvix.knowledge.vector_store")
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(VECTOR_LOG_FILE.resolve()) for h in logger.handlers):
    fh = logging.FileHandler(VECTOR_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

# Cached model instance for fast instantiations across the session
_MODEL_CACHE: Dict[str, SentenceTransformer] = {}


def _get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Retrieves or initializes a cached SentenceTransformer model."""
    if model_name not in _MODEL_CACHE:
        try:
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


class VectorStore:
    """
    Persistent vector store using sentence-transformers and cosine similarity.
    Persists document chunks and 384-dimensional embeddings to JSON with atomic writes.
    """

    def __init__(self, store_path: Optional[str | Path] = None, model_name: str = "all-MiniLM-L6-v2"):
        if store_path is None:
            self.store_path = STORE_PATH
        else:
            p = Path(store_path)
            self.store_path = p if p.is_absolute() else (PROJECT_ROOT / p)
        self.model_name = model_name
        self.model = _get_embedding_model(self.model_name)
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Loads vectors and metadata from persistent storage if available."""
        with self._lock:
            if not self.store_path.exists():
                self.vectors = []
                self.metadata = []
                return

            try:
                content = self.store_path.read_text(encoding="utf-8").strip()
                if not content:
                    self.vectors = []
                    self.metadata = []
                    return

                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("Vector store JSON root must be an object")

                loaded_vectors = []
                for v in data.get("vectors", []):
                    loaded_vectors.append(np.array(v, dtype=np.float32))
                self.vectors = loaded_vectors
                self.metadata = data.get("metadata", [])
            except Exception as e:
                logger.warning(f"Corrupted or invalid vector store at {self.store_path}: {e}. Backing up to .corrupt.")
                backup_path = self.store_path.with_suffix(".corrupt")
                try:
                    shutil.copy2(self.store_path, backup_path)
                except Exception as copy_err:
                    logger.error(f"Failed to create .corrupt backup: {copy_err}")
                self.vectors = []
                self.metadata = []

    def _save(self) -> None:
        """Saves vectors and metadata to disk using an atomic temp file write."""
        with self._lock:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.store_path.with_suffix(".tmp")
            data = {
                "vectors": [v.tolist() for v in self.vectors],
                "metadata": self.metadata,
            }
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            try:
                temp_path.replace(self.store_path)
            except Exception:
                if self.store_path.exists():
                    self.store_path.unlink(missing_ok=True)
                temp_path.rename(self.store_path)

    def num_documents(self) -> int:
        """Returns the total number of document chunk vectors currently stored."""
        return len(self.vectors)

    def __len__(self) -> int:
        return len(self.vectors)

    def __bool__(self) -> bool:
        return True

    def check_persistence(self) -> bool:
        """Verifies round-trip persistence by writing a health check probe and reloading."""
        test_text = "persistence_check_probe"
        try:
            self.add_document(test_text, source="__health__")
            reload_vs = VectorStore(store_path=self.store_path, model_name=self.model_name)
            results = reload_vs.search(test_text, top_k=1)
            success = len(results) > 0 and any(r.get("source") == "__health__" for r in results)
            return success
        except Exception as e:
            logger.error(f"check_persistence failed: {e}")
            return False
        finally:
            self.remove_source("__health__")
            if "reload_vs" in locals():
                reload_vs.remove_source("__health__")

    def remove_source(self, source: str) -> int:
        """Removes all document chunks matching the given source and saves."""
        with self._lock:
            new_vectors = []
            new_metadata = []
            removed = 0
            for v, m in zip(self.vectors, self.metadata):
                if m.get("source") == source:
                    removed += 1
                else:
                    new_vectors.append(v)
                    new_metadata.append(m)
            if removed > 0:
                self.vectors = new_vectors
                self.metadata = new_metadata
                self._save()
            return removed

    def reset(self) -> None:
        """Clears all vectors and metadata in memory and on disk."""
        with self._lock:
            self.vectors = []
            self.metadata = []
            self._save()

    def add_document(self, text: str, source: str = "unknown", chunk_size: int = 500) -> Dict[str, Any]:
        """
        Chunks text, computes embeddings for each chunk, appends to the store,
        and auto-saves to disk.
        """
        words = text.split()
        if not words:
            return {"status": "SUCCESS", "chunks_added": 0, "total_documents": len(self.vectors), "source": source}

        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        for chunk in chunks:
            embedding = self.model.encode(chunk)
            embedding_arr = np.array(embedding, dtype=np.float32)
            with self._lock:
                self.vectors.append(embedding_arr)
                self.metadata.append({
                    "text": chunk,
                    "source": source,
                    "chunk_index": len(self.metadata),
                })

        self._save()

        file_size = self.store_path.stat().st_size if self.store_path.exists() else 0
        total_docs = len(self.vectors)
        logger.info(
            f"[add_document] source='{source}' chunks_added={len(chunks)} "
            f"total_documents={total_docs} file_size_bytes={file_size}"
        )

        return {
            "status": "SUCCESS",
            "chunks_added": len(chunks),
            "total_documents": total_docs,
            "source": source,
        }

    def add_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 500) -> Dict[str, Any]:
        """
        Batch add multiple documents efficiently using batched embedding generation.
        Each doc should have 'text' and optional 'source'.
        """
        if not documents:
            return {"status": "SUCCESS", "documents_added": 0, "total_documents": len(self.vectors)}

        all_chunks: List[str] = []
        all_sources: List[str] = []

        for doc in documents:
            text = doc.get("text", "")
            src = doc.get("source", "unknown")
            words = text.split()
            if not words:
                continue
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                all_chunks.append(chunk)
                all_sources.append(src)

        if not all_chunks:
            return {"status": "SUCCESS", "documents_added": 0, "total_documents": len(self.vectors)}

        # Batched encode for fast parallel execution
        embeddings = self.model.encode(all_chunks, batch_size=64, show_progress_bar=False)

        with self._lock:
            start_idx = len(self.metadata)
            for idx, (chunk, src, emb) in enumerate(zip(all_chunks, all_sources, embeddings)):
                emb_arr = np.array(emb, dtype=np.float32)
                self.vectors.append(emb_arr)
                self.metadata.append({
                    "text": chunk,
                    "source": src,
                    "chunk_index": start_idx + idx,
                })
            self._save()

        file_size = self.store_path.stat().st_size if self.store_path.exists() else 0
        total_docs = len(self.vectors)
        logger.info(
            f"[add_documents] docs_processed={len(documents)} chunks_added={len(all_chunks)} "
            f"total_documents={total_docs} file_size_bytes={file_size}"
        )

        return {
            "status": "SUCCESS",
            "documents_added": len(documents),
            "chunks_added": len(all_chunks),
            "total_documents": total_docs,
        }

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Computes cosine similarity between query and stored chunk embeddings,
        returning the top_k most relevant snippets.
        """
        if not self.vectors or not query or not query.strip():
            return []

        query_embedding = self.model.encode(query)
        query_vec = np.array(query_embedding, dtype=np.float32)

        scores = []
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []

        for i, vec in enumerate(self.vectors):
            v_norm = np.linalg.norm(vec)
            if v_norm == 0:
                similarity = 0.0
            else:
                similarity = float(np.dot(query_vec, vec) / (q_norm * v_norm))
            scores.append((similarity, self.metadata[i]))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, meta in scores[:top_k]:
            results.append({
                "text": meta["text"],
                "source": meta["source"],
                "score": score,
                "chunk_index": meta.get("chunk_index", 0),
            })
        return results
