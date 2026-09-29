"""
Advanced Memory & Retrieval-Augmented Generation (RAG) Module for P.H.A.S.S Sphere.
Provides document chunking, semantic vector search, knowledge graph triplets,
and isolated memory partitions (project, user, global).
"""

from __future__ import annotations
import os
import math
import json
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import logging

logger = logging.getLogger("phass.tools.memory_rag")

_VAULT_DIR = Path("memory_vault")
_VAULT_DIR.mkdir(parents=True, exist_ok=True)
_RAG_STORAGE = _VAULT_DIR / "rag_collections.json"
_KG_STORAGE = _VAULT_DIR / "knowledge_graph.json"

_ACTIVE_STORE_SCOPE = "project"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


def _cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    return float(numerator) / denominator if denominator else 0.0


def _load_collections() -> Dict[str, List[Dict[str, Any]]]:
    if _RAG_STORAGE.exists():
        try:
            with open(_RAG_STORAGE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_collections(data: Dict[str, List[Dict[str, Any]]]):
    try:
        with open(_RAG_STORAGE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save RAG collections: {e}")


def _load_kg() -> List[Dict[str, Any]]:
    if _KG_STORAGE.exists():
        try:
            with open(_KG_STORAGE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_kg(triplets: List[Dict[str, Any]]):
    try:
        with open(_KG_STORAGE, "w", encoding="utf-8") as f:
            json.dump(triplets, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save Knowledge Graph: {e}")


def rag_ingest_documents(
    paths_or_texts: List[str],
    collection_name: str = "default",
    chunk_size: int = 500,
) -> Dict[str, Any]:
    """Chunks and ingests documents or text snippets into a searchable vector index."""
    collections = _load_collections()
    col = collections.setdefault(collection_name, [])
    new_chunks = 0

    for item in paths_or_texts:
        p = Path(item)
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                source = str(p)
            except Exception:
                continue
        else:
            content = str(item)
            source = "direct_text"

        # Chunk content
        words = content.split()
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            if chunk_text.strip():
                col.append({
                    "chunk_id": str(uuid.uuid4())[:8],
                    "text": chunk_text,
                    "source": source,
                    "scope": _ACTIVE_STORE_SCOPE,
                })
                new_chunks += 1

    _save_collections(collections)
    return {
        "status": "SUCCESS",
        "collection": collection_name,
        "scope": _ACTIVE_STORE_SCOPE,
        "new_chunks_ingested": new_chunks,
        "total_chunks_in_collection": len(col),
    }


def rag_query(
    query: str,
    collection_name: str = "default",
    top_k: int = 5,
) -> Dict[str, Any]:
    """Performs semantic similarity retrieval on indexed documents."""
    collections = _load_collections()
    col = collections.get(collection_name, [])
    if not col:
        return {
            "status": "SUCCESS",
            "query": query,
            "matches_count": 0,
            "results": [],
            "message": f"Collection '{collection_name}' is empty or does not exist.",
        }

    q_vec = Counter(_tokenize(query))
    scored = []

    for item in col:
        # Check scope isolation
        if item.get("scope") and item.get("scope") != _ACTIVE_STORE_SCOPE and _ACTIVE_STORE_SCOPE != "global":
            continue
        c_vec = Counter(_tokenize(item["text"]))
        score = _cosine_similarity(q_vec, c_vec)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_matches = [
        {
            "score": round(s, 4),
            "chunk_id": item["chunk_id"],
            "source": item["source"],
            "text": item["text"][:300],
        }
        for s, item in scored[:top_k] if s > 0.01
    ]

    return {
        "status": "SUCCESS",
        "query": query,
        "collection": collection_name,
        "scope": _ACTIVE_STORE_SCOPE,
        "matches_count": len(top_matches),
        "results": top_matches,
    }


def knowledge_graph_extract(
    text: str,
    entity_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Extracts subject-predicate-object triplets from text and stores in Knowledge Graph."""
    triplets = _load_kg()
    new_extracted = []

    # Simple heuristic triplet extraction: [Subject] is/has/uses [Object]
    sentences = re.split(r"[.\n;]", text)
    patterns = [
        (r"(\b[A-Z][a-zA-Z0-9_-]+\b)\s+(is a|is an|is)\s+([^,.]*)", "IS_A"),
        (r"(\b[A-Z][a-zA-Z0-9_-]+\b)\s+(uses|implements|contains)\s+([^,.]*)", "USES"),
        (r"(\b[A-Z][a-zA-Z0-9_-]+\b)\s+(runs on|supports)\s+([^,.]*)", "RUNS_ON"),
    ]

    for sent in sentences:
        s = sent.strip()
        for pat, rel in patterns:
            m = re.search(pat, s, re.IGNORECASE)
            if m:
                subj = m.group(1).strip()
                obj = m.group(3).strip()
                t = {"subject": subj, "predicate": rel, "object": obj, "scope": _ACTIVE_STORE_SCOPE}
                triplets.append(t)
                new_extracted.append(t)

    # If no pattern matched, generate a semantic link
    if not new_extracted and len(sentences) > 0:
        first = sentences[0].strip()
        if first:
            t = {"subject": "P.H.A.S.S", "predicate": "KNOWS", "object": first[:80], "scope": _ACTIVE_STORE_SCOPE}
            triplets.append(t)
            new_extracted.append(t)

    _save_kg(triplets)
    return {
        "status": "SUCCESS",
        "extracted_triplets_count": len(new_extracted),
        "triplets": new_extracted,
        "total_knowledge_graph_size": len(triplets),
    }


def knowledge_graph_query(
    entity: str,
    relation: Optional[str] = None,
) -> Dict[str, Any]:
    """Queries connected graph triplets for an entity."""
    triplets = _load_kg()
    ent = entity.lower().strip()
    rel = relation.lower().strip() if relation else None

    matches = []
    for t in triplets:
        subj_match = ent in t.get("subject", "").lower()
        obj_match = ent in t.get("object", "").lower()
        rel_match = not rel or rel in t.get("predicate", "").lower()

        if (subj_match or obj_match) and rel_match:
            matches.append(t)

    return {
        "status": "SUCCESS",
        "entity": entity,
        "relation_filter": relation,
        "matches_count": len(matches),
        "triplets": matches[:20],
    }


def isolate_memory_store(
    store_scope: str = "project",
    action: str = "switch",
) -> Dict[str, Any]:
    """Switches or inspects isolated memory store scopes ('project', 'user', 'global')."""
    global _ACTIVE_STORE_SCOPE
    valid = ["project", "user", "global"]
    sc = store_scope.lower().strip()
    if sc not in valid:
        return {"status": "FAILED", "error": f"Invalid scope '{store_scope}'. Valid: {valid}"}

    if action == "switch":
        _ACTIVE_STORE_SCOPE = sc
        return {
            "status": "SUCCESS",
            "action": "switch",
            "active_scope": _ACTIVE_STORE_SCOPE,
            "message": f"Active memory partition switched to '{_ACTIVE_STORE_SCOPE}'.",
        }

    return {
        "status": "SUCCESS",
        "action": "status",
        "active_scope": _ACTIVE_STORE_SCOPE,
    }
