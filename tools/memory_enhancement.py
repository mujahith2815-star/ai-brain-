"""
Enhanced Memory & Learning Module for P.H.A.S.S Sphere & Llama Assistant.
Provides cognitive long-term retention:
Vector memory (semantic storage & TF-IDF/cosine similarity retrieval),
Cross-session conversation context,
Pattern learning (habit prediction based on prior tool calls),
Searchable task execution history,
and Knowledge Graph triple store (subject-predicate-object relationships).
"""

from __future__ import annotations
import os
import re
import json
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("phass.tools.memory_enhancement")

_MEM_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints", "memory_system")
os.makedirs(_MEM_STORE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Vector Memory (Semantic Storage & Retrieval)
# ---------------------------------------------------------------------------
_VECTOR_MEM_FILE = os.path.join(_MEM_STORE_DIR, "vector_memories.json")

def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_]{2,}\b', text)]

def vector_memory(
    action: str = "retrieve",
    text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Stores and retrieves semantic memories using local term-frequency / vector cosine metric.
    """
    act = action.strip().lower()

    memories: List[Dict[str, Any]] = []
    if os.path.exists(_VECTOR_MEM_FILE):
        try:
            with open(_VECTOR_MEM_FILE, "r", encoding="utf-8") as f:
                memories = json.load(f)
        except Exception:
            memories = []

    if act in ("store", "add"):
        if not text:
            return {"status": "FAILED", "error": "text is required to store memory."}
        entry = {
            "id": len(memories) + 1,
            "text": text,
            "tokens": _tokenize(text),
            "metadata": metadata or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        memories.append(entry)
        with open(_VECTOR_MEM_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
        return {"status": "SUCCESS", "action": "store", "memory_id": entry["id"]}

    elif act in ("retrieve", "query", "search"):
        q_tokens = _tokenize(query or text or "")
        if not q_tokens:
            return {"status": "SUCCESS", "results": memories[-top_k:]}

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for m in memories:
            m_tokens = set(m.get("tokens", []))
            common = set(q_tokens).intersection(m_tokens)
            if common:
                score = len(common) / (math.sqrt(len(q_tokens)) * math.sqrt(len(m_tokens) or 1))
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {"score": round(s, 3), "text": item["text"], "metadata": item.get("metadata", {})}
            for s, item in scored[:top_k]
        ]
        return {"status": "SUCCESS", "query": query, "matched_count": len(results), "memories": results}

    return {"status": "FAILED", "error": f"Unknown vector memory action '{action}'. Valid: store, retrieve."}


# ---------------------------------------------------------------------------
# 2. Conversation Context (Cross-Session History)
# ---------------------------------------------------------------------------
_CONTEXT_FILE = os.path.join(_MEM_STORE_DIR, "session_context.json")

def conversation_context(
    action: str = "get",
    session_id: str = "default_session",
    message: Optional[str] = None,
    role: str = "user",
) -> Dict[str, Any]:
    """
    Persists and queries conversation history across chat sessions.
    """
    act = action.strip().lower()

    sessions: Dict[str, List[Dict[str, str]]] = {}
    if os.path.exists(_CONTEXT_FILE):
        try:
            with open(_CONTEXT_FILE, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        except Exception:
            sessions = {}

    if act in ("add", "record", "append"):
        if not message:
            return {"status": "FAILED", "error": "message is required."}
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append({
            "role": role,
            "content": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        with open(_CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
        return {"status": "SUCCESS", "action": "record", "session_id": session_id, "turns": len(sessions[session_id])}

    elif act in ("get", "history", "load"):
        hist = sessions.get(session_id, [])
        return {"status": "SUCCESS", "session_id": session_id, "turns": len(hist), "history": hist[-10:]}

    return {"status": "FAILED", "error": f"Unknown context action '{action}'. Valid: add, get."}


# ---------------------------------------------------------------------------
# 3. Pattern Learning (Workflow Habit Prediction)
# ---------------------------------------------------------------------------
_PATTERNS_FILE = os.path.join(_MEM_STORE_DIR, "workflow_patterns.json")

def pattern_learning(
    action: str = "predict",
    user_input: Optional[str] = None,
    tool_used: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Learns common user request patterns and predicts appropriate tools.
    """
    act = action.strip().lower()

    patterns: Dict[str, Dict[str, int]] = {}
    if os.path.exists(_PATTERNS_FILE):
        try:
            with open(_PATTERNS_FILE, "r", encoding="utf-8") as f:
                patterns = json.load(f)
        except Exception:
            patterns = {}

    if act in ("learn", "record"):
        if not user_input or not tool_used:
            return {"status": "FAILED", "error": "user_input and tool_used required to learn pattern."}
        tokens = _tokenize(user_input)
        for t in tokens:
            if t not in patterns:
                patterns[t] = {}
            patterns[t][tool_used] = patterns[t].get(tool_used, 0) + 1

        with open(_PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2)
        return {"status": "SUCCESS", "action": "learn", "tool_associated": tool_used}

    elif act == "predict":
        if not user_input:
            return {"status": "FAILED", "error": "user_input required for prediction."}
        tokens = _tokenize(user_input)
        tool_votes: Dict[str, int] = {}
        for t in tokens:
            if t in patterns:
                for tool, count in patterns[t].items():
                    tool_votes[tool] = tool_votes.get(tool, 0) + count

        top_tools = sorted(tool_votes.items(), key=lambda x: x[1], reverse=True)
        return {
            "status": "SUCCESS",
            "user_input": user_input,
            "predicted_tools": [t[0] for t in top_tools[:3]],
            "confidence": min(0.95, round(top_tools[0][1] / (sum(tool_votes.values()) or 1), 2)) if top_tools else 0.5,
        }

    return {"status": "FAILED", "error": f"Unknown pattern action '{action}'. Valid: learn, predict."}


# ---------------------------------------------------------------------------
# 4. Task History (Searchable Audit Log of Tasks)
# ---------------------------------------------------------------------------
_TASK_HIST_FILE = os.path.join(_MEM_STORE_DIR, "task_execution_history.json")

def task_history(
    action: str = "query",
    task_name: Optional[str] = None,
    task_type: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Logs and queries all completed assistant tasks by name, type, and keyword.
    """
    act = action.strip().lower()

    tasks: List[Dict[str, Any]] = []
    if os.path.exists(_TASK_HIST_FILE):
        try:
            with open(_TASK_HIST_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception:
            tasks = []

    if act in ("record", "log"):
        if not task_name:
            return {"status": "FAILED", "error": "task_name is required."}
        entry = {
            "id": len(tasks) + 1,
            "task_name": task_name,
            "task_type": task_type or "general",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        tasks.append(entry)
        with open(_TASK_HIST_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        return {"status": "SUCCESS", "action": "record", "task_id": entry["id"]}

    elif act in ("query", "search", "list"):
        matched = tasks
        if task_type:
            matched = [t for t in matched if t.get("task_type") == task_type]
        if query:
            q_low = query.lower()
            matched = [t for t in matched if q_low in t.get("task_name", "").lower()]

        return {"status": "SUCCESS", "total_tasks": len(tasks), "matched_count": len(matched), "tasks": matched[-10:]}

    return {"status": "FAILED", "error": f"Unknown action '{action}'. Valid: record, query."}


# ---------------------------------------------------------------------------
# 5. Knowledge Graph (Triple Store)
# ---------------------------------------------------------------------------
_KG_FILE = os.path.join(_MEM_STORE_DIR, "knowledge_graph.json")

def knowledge_graph(
    action: str = "query",
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    object_: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Semantic knowledge graph store for (subject, predicate, object) triples.
    """
    act = action.strip().lower()

    triples: List[Dict[str, str]] = []
    if os.path.exists(_KG_FILE):
        try:
            with open(_KG_FILE, "r", encoding="utf-8") as f:
                triples = json.load(f)
        except Exception:
            triples = []

    if act in ("add", "insert"):
        if not subject or not predicate or not object_:
            return {"status": "FAILED", "error": "subject, predicate, and object_ are required."}
        new_triple = {"subject": subject.strip(), "predicate": predicate.strip(), "object": object_.strip()}
        if new_triple not in triples:
            triples.append(new_triple)
            with open(_KG_FILE, "w", encoding="utf-8") as f:
                json.dump(triples, f, indent=2)
        return {"status": "SUCCESS", "action": "add", "triple": new_triple}

    elif act in ("query", "find"):
        res = triples
        if subject:
            res = [t for t in res if subject.lower() in t["subject"].lower()]
        if predicate:
            res = [t for t in res if predicate.lower() in t["predicate"].lower()]
        if object_:
            res = [t for t in res if object_.lower() in t["object"].lower()]

        return {"status": "SUCCESS", "total_triples": len(triples), "matched_count": len(res), "results": res}

    return {"status": "FAILED", "error": f"Unknown KG action '{action}'. Valid: add, query."}
