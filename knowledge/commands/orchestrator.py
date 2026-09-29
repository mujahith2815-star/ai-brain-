"""
Command Brain Bootstrap and Ingestion Orchestrator.
Coordinates the 3-Layer Command Intelligence lifecycle:
- Layer 1 (Core Catalog): Ingests ~520 high-value commands into VectorStore once
- Layer 2 (Live Discovery): Populates SQLite cache (~2,000+ commands) without bloating VectorStore
- Layer 3 (Learned Patterns): Starts background PatternLearner worker
- Idempotency: Uses .brain_bootstrapped marker to keep subsequent startups under 1 second.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from knowledge.commands.core.load_core import load_core_commands
from tools.command_discovery import CommandDiscovery
from tools.command_cache import count_cached
from knowledge.commands.pattern_learner import start_pattern_learner

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP_MARKER = os.path.join(MODULE_DIR, ".brain_bootstrapped")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
BOOTSTRAP_LOG_FILE = os.path.join(LOGS_DIR, "command_brain_bootstrap.log")

logger = logging.getLogger("orvix.knowledge.commands.orchestrator")
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(os.path.abspath(BOOTSTRAP_LOG_FILE)) for h in logger.handlers):
    fh = logging.FileHandler(BOOTSTRAP_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


def format_core_command_for_vector(cmd: Dict[str, Any]) -> str:
    """Formats a core command definition into a rich text snippet for semantic embedding."""
    name = cmd.get("name", "unknown")
    shell = cmd.get("shell", "cross-platform")
    category = cmd.get("category", "general")
    desc = cmd.get("description", "")
    syntax = cmd.get("syntax", "")
    tags = ", ".join(cmd.get("tags", []))

    lines = [
        f"Command: {name} (Shell: {shell}, Category: {category})",
        f"Description: {desc}",
        f"Syntax: {syntax}",
    ]
    if tags:
        lines.append(f"Tags: {tags}")

    examples = cmd.get("examples", [])
    if isinstance(examples, list) and examples:
        ex_strs = []
        for ex in examples:
            if isinstance(ex, dict):
                ex_strs.append(f"{ex.get('cmd', '')} ({ex.get('desc', '')})")
            elif isinstance(ex, str):
                ex_strs.append(ex)
        if ex_strs:
            lines.append(f"Examples: {' | '.join(ex_strs)}")

    return "\n".join(lines)


def bootstrap_command_brain(vector_store: Any = None, force_reindex: bool = False) -> Dict[str, Any]:
    """
    Bootstraps the 3-Layer Command Intelligence system.
    Runs initial vector indexing of Layer 1 and OS discovery of Layer 2 on first startup.
    Subsequent runs load immediately via the bootstrap marker.
    """
    start_t = time.perf_counter()

    # Always ensure background pattern learner is active for Layer 3
    try:
        start_pattern_learner(interval_seconds=300, vector_store=vector_store)
    except Exception as ple:
        logger.warning(f"Pattern learner startup notice: {ple}")

    is_bootstrapped = os.path.exists(BOOTSTRAP_MARKER) and not force_reindex

    if is_bootstrapped:
        elapsed = time.perf_counter() - start_t
        stats = count_cached()
        logger.info(f"Command Brain already bootstrapped. Fast startup completed in {elapsed:.3f}s.")
        return {
            "status": "CACHED",
            "startup_sec": round(elapsed, 3),
            "layer1_core": len(load_core_commands()),
            "layer2_discovered": stats.get("total", 0),
            "bootstrapped": True
        }

    logger.info("Initializing first-time bootstrap of Command Intelligence Brain...")

    # 1. Load Layer 1 Core Commands
    core_commands = load_core_commands(force_reload=True)
    logger.info(f"Loaded {len(core_commands)} core commands for Layer 1.")

    # 2. Index Layer 1 into VectorStore (batched)
    indexed_vector_count = 0
    if vector_store is not None:
        try:
            docs_to_index = []
            for cmd in core_commands:
                text_content = format_core_command_for_vector(cmd)
                metadata = {
                    "source": "layer1_core",
                    "command_name": cmd.get("name"),
                    "shell": cmd.get("shell"),
                    "category": cmd.get("category"),
                    "tags": cmd.get("tags", []),
                }
                docs_to_index.append({"text": text_content, "metadata": metadata})

            if hasattr(vector_store, "add_documents"):
                vector_store.add_documents(docs_to_index)
            else:
                for doc in docs_to_index:
                    vector_store.add_document(doc["text"], doc["metadata"])

            indexed_vector_count = len(docs_to_index)
            logger.info(f"Indexed {indexed_vector_count} Layer 1 commands into VectorStore.")
        except Exception as ve:
            logger.error(f"Error vector-indexing Layer 1 commands: {ve}")

    # 3. Run Layer 2 Live Discovery ONCE to populate SQLite cache (NOT vector store)
    disc = CommandDiscovery()
    discovery_res = disc.discover_all(save_snapshot=True)
    logger.info(f"Discovered and cached {discovery_res.get('total')} commands in Layer 2 SQLite cache.")

    # 4. Write bootstrap marker
    marker_data = {
        "bootstrapped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "layer1_core_count": len(core_commands),
        "layer1_vector_indexed": indexed_vector_count,
        "layer2_discovered_count": discovery_res.get("total", 0),
        "version": "1.2.0"
    }
    with open(BOOTSTRAP_MARKER, "w", encoding="utf-8") as f:
        json.dump(marker_data, f, indent=2)

    total_sec = time.perf_counter() - start_t
    logger.info(f"Command Brain bootstrap completed in {total_sec:.2f}s.")

    return {
        "status": "BOOTSTRAPPED",
        "startup_sec": round(total_sec, 3),
        "layer1_core": len(core_commands),
        "layer1_vector_indexed": indexed_vector_count,
        "layer2_discovered": discovery_res.get("total", 0),
        "bootstrapped": True
    }
