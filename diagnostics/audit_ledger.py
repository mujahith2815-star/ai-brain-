"""
Cryptographic Merkle Tree Audit Ledger for P.H.A.S.S Sphere.
Computes SHA-256 chained hashes and Merkle Root signatures for every cognitive decision,
sensory snapshot, and tool execution to guarantee tamper-proof audit trails.
"""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AuditBlock:
    index: int
    event_type: str
    payload: Dict[str, Any]
    prev_hash: str
    block_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "event_type": self.event_type,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "block_hash": self.block_hash,
            "timestamp": self.timestamp,
        }


class CryptographicAuditLedger:
    def __init__(self):
        self.blocks: List[AuditBlock] = []
        self._init_genesis_block()

    def _hash_data(self, data_str: str) -> str:
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def _init_genesis_block(self) -> None:
        payload = {"message": "P.H.A.S.S SPHERE GENESIS AUDIT BLOCK"}
        h = self._hash_data("GENESIS" + json.dumps(payload))
        gen = AuditBlock(0, "GENESIS", payload, "0"*64, h)
        self.blocks.append(gen)

    def record_decision(self, event_type: str, payload: Dict[str, Any]) -> AuditBlock:
        prev = self.blocks[-1]
        raw_str = f"{prev.block_hash}:{event_type}:{json.dumps(payload, sort_keys=True)}"
        curr_hash = self._hash_data(raw_str)

        block = AuditBlock(
            index=len(self.blocks),
            event_type=event_type,
            payload=payload,
            prev_hash=prev.block_hash,
            block_hash=curr_hash,
        )
        self.blocks.append(block)
        return block

    def compute_merkle_root(self) -> str:
        """
        Computes pairwise binary Merkle Root hash across all blocks.
        """
        if not self.blocks:
            return "0" * 64

        curr_hashes = [b.block_hash for b in self.blocks]

        while len(curr_hashes) > 1:
            if len(curr_hashes) % 2 == 1:
                curr_hashes.append(curr_hashes[-1]) # Duplicate last if odd

            next_level = []
            for i in range(0, len(curr_hashes), 2):
                combined = self._hash_data(curr_hashes[i] + curr_hashes[i+1])
                next_level.append(combined)
            curr_hashes = next_level

        return curr_hashes[0]

    def verify_ledger_integrity(self) -> bool:
        for i in range(1, len(self.blocks)):
            curr = self.blocks[i]
            prev = self.blocks[i-1]
            if curr.prev_hash != prev.block_hash:
                return False
            expected_hash = self._hash_data(f"{prev.block_hash}:{curr.event_type}:{json.dumps(curr.payload, sort_keys=True)}")
            if curr.block_hash != expected_hash:
                return False
        return True

    def get_ledger_summary(self) -> Dict[str, Any]:
        return {
            "total_blocks": len(self.blocks),
            "merkle_root": self.compute_merkle_root(),
            "is_valid": self.verify_ledger_integrity(),
            "latest_block_hash": self.blocks[-1].block_hash,
        }


audit_ledger = CryptographicAuditLedger()
