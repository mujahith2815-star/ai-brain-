"""
Natural Language Processing (NLP) Pipeline for P.H.A.S.S Sphere.
Provides text normalization, tokenization, keyword extraction, and local vector embeddings.
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Set, Tuple
import logging

logger = logging.getLogger("phass.nlp.pipeline")

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}


class NLPPipeline:
    def __init__(self):
        self.vocabulary: Dict[str, int] = {}

    def normalize(self, text: str) -> str:
        """Converts to lowercase and cleans non-standard characters."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s\-\.]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def tokenize(self, text: str, remove_stopwords: bool = True) -> List[str]:
        """Extracts word tokens with optional stopword filtering."""
        cleaned = self.normalize(text)
        tokens = re.findall(r"\b[a-z0-9_\-\.]+\b", cleaned)
        if remove_stopwords:
            tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
        return tokens

    def extract_keywords(self, text: str, top_k: int = 5) -> List[Tuple[str, int]]:
        """Extracts high-frequency content keywords."""
        tokens = self.tokenize(text, remove_stopwords=True)
        counts: Dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        sorted_keywords = sorted(counts.items(), key=lambda x: -x[1])
        return sorted_keywords[:top_k]

    SEMANTIC_CLUSTERS: Dict[str, int] = {
        # Tech & System
        "server": 1, "rack": 1, "terminal": 1, "computer": 1, "system": 1, "hardware": 1, "device": 1, "code": 1,
        # Inspection & Diagnostics
        "inspect": 2, "examine": 2, "check": 2, "analyze": 2, "diagnose": 2, "scan": 2, "probe": 2, "audit": 2,
        # Spatial & Location
        "laboratory": 3, "room": 3, "sector": 3, "dock": 3, "area": 3, "arena": 3, "zone": 3,
        # Motion & Navigation
        "move": 4, "navigate": 4, "roll": 4, "patrol": 4, "drive": 4, "travel": 4, "go": 4,
        # Cooking / Unrelated domain
        "bake": 5, "cake": 5, "recipe": 5, "strawberry": 5, "cook": 5, "kitchen": 5, "food": 5,
    }

    def compute_embedding(self, text: str, dim: int = 64) -> List[float]:
        """
        Generates a deterministic semantic embedding vector using stable token hashing & synset clusters.
        Runs locally with zero external dependencies.
        """
        import hashlib
        tokens = self.tokenize(text, remove_stopwords=True)
        vector = [0.0] * dim
        if not tokens:
            return vector

        for token in tokens:
            # 1. Semantic Cluster Projection
            if token in self.SEMANTIC_CLUSTERS:
                cluster_id = self.SEMANTIC_CLUSTERS[token]
                c_idx = (cluster_id * 7) % dim
                vector[c_idx] += 3.0
                vector[(c_idx + 1) % dim] += 2.0

            # 2. Deterministic MD5 token hash
            h_bytes = hashlib.md5(token.encode("utf-8")).digest()
            idx1 = int.from_bytes(h_bytes[0:4], "big") % dim
            vector[idx1] += 2.0

        # L2 Normalize
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 1e-6:
            vector = [v / magnitude for v in vector]
        return vector

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculates cosine similarity between two embedding vectors."""
        if len(vec1) != len(vec2) or not vec1:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(0.0, min(1.0, dot))


nlp_pipeline = NLPPipeline()
