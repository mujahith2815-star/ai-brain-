"""
File Watcher for P.H.A.S.S Sphere Knowledge Layer.
Monitors the knowledge/inbox directory for new text and code documents,
automatically ingesting them into the semantic VectorStore.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from knowledge.vector_store import VectorStore, PROJECT_ROOT


class FileWatcher:
    """
    Watches an inbox directory and indexes new files into VectorStore.
    """

    SUPPORTED_EXTENSIONS = ('.txt', '.md', '.py', '.json', '.csv')

    def __init__(self, watch_dir: Optional[str | Path] = None, vector_store: Optional[VectorStore] = None):
        if watch_dir is None:
            self.watch_dir = str(PROJECT_ROOT / "knowledge" / "inbox")
        else:
            p = Path(watch_dir)
            self.watch_dir = str(p if p.is_absolute() else (PROJECT_ROOT / p))

        self.vector_store = vector_store if vector_store is not None else VectorStore()
        self.processed: Set[str] = set()
        os.makedirs(self.watch_dir, exist_ok=True)

    def scan_and_ingest(self) -> List[Dict[str, Any]]:
        """
        Scans the inbox directory and ingests any unprocessed supported files.
        """
        results: List[Dict[str, Any]] = []
        if not os.path.exists(self.watch_dir):
            os.makedirs(self.watch_dir, exist_ok=True)
            return results

        for filename in sorted(os.listdir(self.watch_dir)):
            filepath = os.path.join(self.watch_dir, filename)
            if not os.path.isfile(filepath):
                continue

            norm_path = os.path.abspath(filepath)
            if norm_path in self.processed or filepath in self.processed:
                continue

            if filename.lower().endswith(self.SUPPORTED_EXTENSIONS):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    res = self.vector_store.add_document(content, source=filename)
                    self.vector_store._save()
                    doc_count = self.vector_store.num_documents()
                    print(f"[FileWatcher] Ingested '{filename}': {res.get('chunks_added', 0)} chunks added. Total documents in store: {doc_count}")
                    self.processed.add(norm_path)
                    self.processed.add(filepath)
                    results.append(res)
                except Exception as e:
                    results.append({"status": "FAILED", "source": filename, "error": str(e)})

        return results
