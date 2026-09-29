"""
RAG Pipeline for P.H.A.S.S Sphere Knowledge Layer.
Gathers semantic document snippets from VectorStore and structured facts
from KnowledgeStore to augment user prompts prior to agent reasoning.
"""

from __future__ import annotations
from typing import Optional
from knowledge.vector_store import VectorStore
from knowledge.sqlite_store import KnowledgeStore


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline combining semantic search
    and structured factual memory.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        sql_store: Optional[KnowledgeStore] = None
    ):
        self.vector_store = vector_store if vector_store is not None else VectorStore()
        self.sql_store = sql_store if sql_store is not None else KnowledgeStore()

    def retrieve_context(self, query: str, top_k: int = 3) -> Optional[str]:
        """
        Gathers relevant context from both document embeddings and structured facts.
        Returns a formatted markdown/text snippet, or None if no context is found.
        """
        if not query or not query.strip():
            return None

        # Early return if vector store has 0 documents (avoids unnecessary search/model calls)
        if hasattr(self.vector_store, "num_documents") and self.vector_store.num_documents() == 0:
            return None

        context_parts = []

        # 1. Semantic search from documents
        doc_results = self.vector_store.search(query, top_k=top_k)
        for r in doc_results:
            if r.get("text") and r.get("score", 0.0) >= 0.2:
                context_parts.append(f"[From {r['source']}]: {r['text']}")

        # 2. Structured facts from SQLite
        seen_keys = set()
        matched_facts = []

        # Try key terms from query
        tokens = query.split()
        first_token = tokens[0] if tokens else ""
        candidates = [first_token] if first_token else []

        for w in tokens:
            clean_w = w.strip("?,.!:;\"\'")
            if len(clean_w) > 2 and clean_w not in candidates:
                candidates.append(clean_w)

        for kw in candidates:
            if not kw:
                continue
            for f in self.sql_store.search_facts(kw):
                if f["key"] not in seen_keys:
                    seen_keys.add(f["key"])
                    matched_facts.append(f)
                    if len(matched_facts) >= 3:
                        break
            if len(matched_facts) >= 3:
                break

        for f in matched_facts[:3]:
            context_parts.append(f"[Fact - {f['key']}]: {f['value']}")

        if not context_parts:
            return None

        return "\n\n".join(context_parts)

    def build_augmented_prompt(self, user_query: str) -> str:
        """
        Builds a prompt string with injected knowledge context.
        If no relevant context is found, returns the user_query unchanged.
        """
        context = self.retrieve_context(user_query)

        if context:
            return (
                f"You have access to the following knowledge:\n\n"
                f"{context}\n\n"
                f"Based on the above, answer the user's question: {user_query}\n\n"
                f"If the knowledge above doesn't contain the answer, say so and use your tools to find it."
            )
        return user_query
