"""
Auto-ingestion module for Orvix Universal Control command knowledge base.
Ensures commands from JSON datasets are idempotently indexed into VectorStore.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .load_commands import load_all_commands, get_command_summary

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXED_MARKER = os.path.join(MODULE_DIR, ".indexed")
PROJECT_ROOT = os.path.abspath(os.path.join(MODULE_DIR, "..", ".."))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
INDEX_LOG_FILE = os.path.join(LOGS_DIR, "command_indexing.log")

logger = logging.getLogger("orvix.knowledge.commands.auto_ingest")
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(os.path.abspath(INDEX_LOG_FILE)) for h in logger.handlers):
    fh = logging.FileHandler(INDEX_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


def format_command_for_embedding(cmd: Dict[str, Any]) -> str:
    """Formats a structured command definition into a rich text snippet for semantic embedding."""
    name = cmd.get("name", "unknown")
    shell = cmd.get("shell", "cross-platform")
    category = cmd.get("category", "general")
    desc = cmd.get("description", "")
    syntax = cmd.get("syntax", "")
    equiv = cmd.get("windows_equivalent") or cmd.get("linux_equivalent") or "None"
    tags = ", ".join(cmd.get("tags", []))
    
    examples_str = ""
    examples = cmd.get("examples", [])
    if isinstance(examples, list):
        ex_lines = []
        for ex in examples:
            if isinstance(ex, dict):
                c = ex.get("cmd", "")
                d = ex.get("desc", "")
                ex_lines.append(f"{c} ({d})")
            elif isinstance(ex, str):
                ex_lines.append(ex)
        if ex_lines:
            examples_str = " | ".join(ex_lines)

    lines = [
        f"Command: {name} (Shell: {shell}, Category: {category})",
        f"Description: {desc}",
        f"Syntax: {syntax}",
    ]
    if examples_str:
        lines.append(f"Examples: {examples_str}")
    if equiv != "None":
        lines.append(f"Cross-Platform Equivalent: {equiv}")
    if tags:
        lines.append(f"Tags: {tags}")

    return "\n".join(lines)


def is_indexed() -> bool:
    """Returns True if the indexing marker exists and is valid."""
    return os.path.exists(INDEXED_MARKER)


def ensure_commands_indexed(vector_store: Optional[Any] = None, force: bool = False) -> Dict[str, Any]:
    """
    Idempotently indexes all pre-loaded command definitions into VectorStore.
    If already indexed and not force, returns immediately.
    """
    if is_indexed() and not force:
        try:
            with open(INDEXED_MARKER, "r", encoding="utf-8") as f:
                marker_data = json.load(f)
            return {
                "status": "already_indexed",
                "indexed_at": marker_data.get("indexed_at"),
                "total_commands": marker_data.get("total_commands", 0),
                "message": "Commands already indexed in VectorStore. Skipping."
            }
        except Exception:
            pass

    t0 = time.time()
    commands = load_all_commands(force_reload=True)
    if not commands:
        return {"status": "error", "message": "No commands found to index"}

    # Prepare document list
    documents: List[Dict[str, Any]] = []
    for c in commands:
        text = format_command_for_embedding(c)
        source = c.get("source_file", "commands_knowledge")
        documents.append({
            "text": text,
            "source": f"commands/{c.get('name', 'cmd')}",
            "command_name": c.get("name"),
            "category": c.get("category"),
            "shell": c.get("shell"),
        })

    # Lazy load vector store if not passed in
    if vector_store is None:
        from ..vector_store import VectorStore
        vector_store = VectorStore()

    logger.info(f"Starting command indexing: {len(documents)} items to process...")
    
    # Use batch indexing
    if hasattr(vector_store, "add_documents"):
        ingest_res = vector_store.add_documents(documents)
    else:
        for doc in documents:
            vector_store.add_document(doc["text"], source=doc["source"])
        ingest_res = {"documents_added": len(documents)}

    elapsed = round(time.time() - t0, 2)
    summary = get_command_summary()

    marker_info = {
        "indexed_at": datetime.now().isoformat(),
        "total_commands": len(commands),
        "summary": summary,
        "elapsed_seconds": elapsed,
    }

    try:
        with open(INDEXED_MARKER, "w", encoding="utf-8") as f:
            json.dump(marker_info, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write .indexed marker: {e}")

    logger.info(f"Command indexing complete in {elapsed}s: {len(commands)} commands indexed.")

    return {
        "status": "indexed",
        "total_commands": len(commands),
        "elapsed_seconds": elapsed,
        "summary": summary,
        "ingest_result": ingest_res,
    }
