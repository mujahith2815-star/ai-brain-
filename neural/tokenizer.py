"""
Subword Tokenizer & Token Economics Manager for P.H.A.S.S Sphere.
Handles byte-level subword tokenization, context budgeting, and token throughput telemetry.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TokenBudgetTelemetry:
    total_tokens_processed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    context_window_limit: int = 8192
    current_context_usage: int = 0
    tokens_per_second: float = 0.0
    last_reset: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        pct = (self.current_context_usage / max(1, self.context_window_limit)) * 100.0
        return {
            "total_tokens_processed": self.total_tokens_processed,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "context_window_limit": self.context_window_limit,
            "current_context_usage": self.current_context_usage,
            "context_usage_pct": round(pct, 1),
            "tokens_per_second": round(self.tokens_per_second, 1),
        }


class SubwordTokenizer:
    """
    Fast, deterministic subword tokenizer for context budgeting and neural tokenization.
    """

    def __init__(self, vocab_size: int = 4096):
        self.vocab_size = vocab_size
        self._vocab: Dict[str, int] = {}
        self._reverse_vocab: Dict[int, str] = {}
        self._init_base_vocab()
        self.telemetry = TokenBudgetTelemetry()

    def _init_base_vocab(self) -> None:
        # Base ASCII characters
        for i in range(256):
            ch = chr(i)
            self._vocab[ch] = i
            self._reverse_vocab[i] = ch

        # Seed standard robotic subwords
        common_subwords = [
            "phass", "sphere", "robot", "auton", "omni", "lidar", "sensor", "telemetry",
            "battery", "diagnos", "fail", "reason", "plan", "execut", "observ", "learn",
            "evaluat", "memor", "knowledg", "system", "action", "directiv", "goal", "task"
        ]
        curr_id = 256
        for sw in common_subwords:
            if curr_id < self.vocab_size:
                self._vocab[sw] = curr_id
                self._reverse_vocab[curr_id] = sw
                curr_id += 1

    def encode(self, text: str) -> List[int]:
        """Encodes string into integer token IDs."""
        if not text:
            return []
        tokens: List[int] = []
        words = re.findall(r"\w+|[^\w\s]", text.lower())

        for word in words:
            if word in self._vocab:
                tokens.append(self._vocab[word])
            else:
                # Subword character fallback
                for ch in word:
                    tokens.append(self._vocab.get(ch, ord(ch) % 256))

        return tokens

    def decode(self, tokens: List[int]) -> str:
        """Decodes token IDs back to string."""
        chars = []
        for t in tokens:
            chars.append(self._reverse_vocab.get(t, ""))
        return "".join(chars)

    def tokenize(self, text: str) -> List[str]:
        """Tokenizes string into word/subword tokens."""
        if not text:
            return []
        return re.findall(r"\w+|[^\w\s]", text.lower())

    def count_tokens(self, text: str) -> int:
        return len(self.encode(text))

    def record_usage(self, prompt_text: str, completion_text: str) -> TokenBudgetTelemetry:
        p_count = self.count_tokens(prompt_text)
        c_count = self.count_tokens(completion_text)

        self.telemetry.prompt_tokens += p_count
        self.telemetry.completion_tokens += c_count
        self.telemetry.total_tokens_processed += (p_count + c_count)
        self.telemetry.current_context_usage = p_count + c_count

        return self.telemetry

    def compact_context_if_needed(self, messages: List[Dict[str, str]], max_tokens: int = 4000) -> List[Dict[str, str]]:
        """Prunes older messages when approaching context budget."""
        total = sum(self.count_tokens(m.get("content", "")) for m in messages)
        if total <= max_tokens:
            return messages

        # Preserve system prompt and recent turns
        if len(messages) > 3:
            return [messages[0]] + messages[-3:]
        return messages


tokenizer = SubwordTokenizer()
