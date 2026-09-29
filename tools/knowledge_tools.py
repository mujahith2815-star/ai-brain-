"""
Knowledge Tools for P.H.A.S.S Sphere Agent.
Exposes standalone callable functions for facts, custom lists,
document indexing, and semantic search to the tool registry.
"""

from __future__ import annotations
import os
from typing import Any, Dict
from knowledge.sqlite_store import KnowledgeStore
from knowledge.vector_store import VectorStore
from core.rag_pipeline import RAGPipeline

_knowledge = KnowledgeStore()
_vector = VectorStore()
_rag = RAGPipeline(vector_store=_vector, sql_store=_knowledge)


def remember_fact(key: str, value: str, category: str = "general") -> Dict[str, Any]:
    """Store a fact for later retrieval."""
    return _knowledge.store_fact(key, value, category)


def recall_fact(key: str) -> Dict[str, Any]:
    """Retrieve a stored fact by its key."""
    result = _knowledge.get_fact(key)
    if result is not None:
        val = result.value if hasattr(result, "value") else result
        return {"status": "SUCCESS", "key": key, "value": val}
    return {"status": "NOT_FOUND", "key": key}


def add_to_list(list_name: str, item: str, quantity: int = 1, notes: str = "") -> Dict[str, Any]:
    """Add an item to a named list (shopping, tasks, etc.)."""
    return _knowledge.add_to_list(list_name, item, quantity, notes)


def get_list(list_name: str) -> Dict[str, Any]:
    """Retrieve all items from a named list."""
    items = _knowledge.get_list(list_name)
    item_list = list(items.items) if hasattr(items, "items") else list(items)
    return {"status": "SUCCESS", "list": list_name, "items": item_list, "count": len(item_list)}


def search_documents(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Search your indexed documents for relevant passages."""
    results = _vector.search(query, top_k=top_k)
    if not results:
        return {"status": "NO_RESULTS", "message": "No documents indexed yet."}
    return {"status": "SUCCESS", "results": results}


def ingest_document(filepath: str) -> Dict[str, Any]:
    """Add a document to the knowledge base."""
    if not os.path.exists(filepath):
        return {"status": "FAILED", "error": f"File not found: {filepath}"}
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return _vector.add_document(content, source=filepath)
    except Exception as e:
        return {"status": "FAILED", "error": str(e), "filepath": filepath}


def ask_with_knowledge(question: str) -> Dict[str, Any]:
    """Answer a question using RAG (retrieves context then reasons)."""
    augmented = _rag.build_augmented_prompt(question)
    return {"status": "SUCCESS", "augmented_prompt": augmented}
