"""
Personal Document, Codebase & PDF Vector Memory Ingestor for P.H.A.S.S Sphere v5.0.
Parses, chunks, and indexes source code, markdown docs, PDFs, CSVs, and text files
into the dense 64-dimensional Vector Memory Vault for instant semantic search and Q&A.
"""

from __future__ import annotations
import csv
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from memory.vector_vault import vector_vault, VectorQueryResult

logger = logging.getLogger("phass.memory.document_ingestor")


@dataclass
class IngestedDocumentSummary:
    file_path: str
    file_name: str
    file_type: str
    file_size_bytes: int
    total_chunks_created: int
    vector_doc_ids: List[str]
    ingest_duration_sec: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "total_chunks_created": self.total_chunks_created,
            "vector_doc_ids": self.vector_doc_ids,
            "ingest_duration_sec": round(self.ingest_duration_sec, 3),
            "timestamp": self.timestamp,
        }


class DocumentVectorIngestor:
    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".cpp", ".c", ".h", ".java", ".go", ".rs",
        ".html", ".css", ".sql", ".sh", ".bat", ".ps1", ".md", ".txt", ".json", ".yaml",
        ".yml", ".csv", ".tsv", ".log", ".ini", ".env", ".pdf", ".docx"
    }

    def __init__(self, chunk_size_words: int = 150, chunk_overlap_words: int = 30):
        self.chunk_size = chunk_size_words
        self.chunk_overlap = chunk_overlap_words
        self.ingestion_history: List[IngestedDocumentSummary] = []

    def _extract_raw_text(self, path: Path) -> str:
        """Extracts text content from various file formats."""
        ext = path.suffix.lower()

        if ext == ".pdf":
            try:
                # Basic PDF text stream extraction
                with open(path, "rb") as f:
                    content = f.read().decode("latin1", errors="ignore")
                # Extract text within parentheses in stream objects
                text_chunks = re.findall(r"\(([^\(\)]+)\)\s*Tj", content)
                if text_chunks:
                    return " ".join(text_chunks)
                # Fallback: strip stream binary
                text_clean = re.sub(r"[^\x20-\x7E\n]", " ", content)
                return text_clean[:50000]
            except Exception as e:
                logger.warning(f"PDF extraction fallback for '{path}': {e}")
                return path.read_text(encoding="utf-8", errors="ignore")

        elif ext in (".csv", ".tsv"):
            try:
                delimiter = "\t" if ext == ".tsv" else ","
                rows = []
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    for i, row in enumerate(reader):
                        if i > 500:
                            break
                        rows.append(" | ".join(row))
                return "\n".join(rows)
            except Exception:
                return path.read_text(encoding="utf-8", errors="ignore")

        else:
            return path.read_text(encoding="utf-8", errors="ignore")

    def _chunk_text(self, text: str) -> List[str]:
        """Splits text into overlapping word chunks to preserve semantic context."""
        words = text.split()
        if not words:
            return []
        if len(words) <= self.chunk_size:
            return [" ".join(words)]

        chunks = []
        step = self.chunk_size - self.chunk_overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def ingest_file(self, file_path_str: str) -> IngestedDocumentSummary:
        """
        Ingests and indexes a single document or source code file into vector memory.
        """
        start_t = time.time()
        p = Path(file_path_str).resolve()
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        text = self._extract_raw_text(p)
        chunks = self._chunk_text(text)
        vector_ids = []

        for idx, chunk in enumerate(chunks):
            meta = {
                "source_file": str(p),
                "file_name": p.name,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "file_extension": p.suffix.lower(),
            }
            doc_id = vector_vault.store_memory(
                content=f"[{p.name} - Chunk {idx+1}/{len(chunks)}]\n{chunk}",
                metadata=meta,
            )
            vector_ids.append(doc_id)

        dur = time.time() - start_t
        summary = IngestedDocumentSummary(
            file_path=str(p),
            file_name=p.name,
            file_type=p.suffix.lower() or "plain_text",
            file_size_bytes=p.stat().st_size,
            total_chunks_created=len(chunks),
            vector_doc_ids=vector_ids,
            ingest_duration_sec=dur,
        )
        self.ingestion_history.append(summary)
        logger.info(f"Ingested [{p.name}] into {len(chunks)} vector chunks in {dur:.3f}s")
        return summary

    def ingest_directory(self, dir_path_str: str, max_files: int = 50) -> List[IngestedDocumentSummary]:
        """
        Recursively ingests and indexes all supported code and document files within a directory.
        """
        d = Path(dir_path_str).resolve()
        if not d.exists() or not d.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path_str}")

        summaries = []
        count = 0
        for root, _, files in os.walk(d):
            # Skip hidden / node_modules / .git
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", "venv", "dist") for part in Path(root).parts):
                continue
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    fp = os.path.join(root, file)
                    try:
                        sum_doc = self.ingest_file(fp)
                        summaries.append(sum_doc)
                        count += 1
                        if count >= max_files:
                            break
                    except Exception as e:
                        logger.warning(f"Skipped file during batch ingestion '{fp}': {e}")
            if count >= max_files:
                break

        return summaries

    def search_ingested_documents(self, query: str, top_k: int = 3) -> List[VectorQueryResult]:
        """Performs semantic search specifically over ingested files."""
        return vector_vault.search_semantic_memory(query, top_k=top_k)

    def format_ingest_report_text(self, summary: IngestedDocumentSummary) -> str:
        return (
            f"=== DOCUMENT VECTOR INGESTION REPORT ===\n"
            f"Source File:         {summary.file_name} ({summary.file_path})\n"
            f"File Format:         {summary.file_type.upper()} ({summary.file_size_bytes} Bytes)\n"
            f"Vector Chunks:       {summary.total_chunks_created} Semantic Embeddings Created\n"
            f"Ingestion Duration:  {summary.ingest_duration_sec:.3f} seconds\n"
            f"Indexing Status:     100% STORED IN VECTOR VAULT\n\n"
            f"Sample Vector IDs:   {', '.join(summary.vector_doc_ids[:5])}"
        )


document_ingestor = DocumentVectorIngestor()
