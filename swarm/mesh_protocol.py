"""
Multi-Agent Swarm Intelligence & Mesh Coordination for P.H.A.S.S Sphere.
Implements P2P Mesh Networking, CRDT Distributed Knowledge Graph Sync,
and Contract Net Protocol (Auction-Based Task Allocation) between peer spheres.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import random
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("phass.swarm.mesh")


@dataclass
class SwarmPeerNode:
    peer_id: str
    position: Tuple[float, float, float]
    battery_pct: float
    current_load_tasks: int
    status: str
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "position": {"x": self.position[0], "y": self.position[1], "z": self.position[2]},
            "battery_pct": round(self.battery_pct, 1),
            "current_load_tasks": self.current_load_tasks,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class TaskAuctionBid:
    task_id: str
    bidder_id: str
    bid_cost: float  # Lower cost = better bid (function of distance and battery)
    estimated_duration_sec: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SwarmMeshCoordinator:
    def __init__(self, local_id: str = "P.H.A.S.S-PRIME"):
        self.local_id = local_id
        self.peers: Dict[str, SwarmPeerNode] = {}
        self.shared_crdt_triples: List[Dict[str, Any]] = []
        self._seed_default_swarm()

    def _seed_default_swarm(self) -> None:
        self.register_peer_heartbeat("P.H.A.S.S-BETA", (4.5, 2.0, 0.25), 88.0, 1, "PATROL")
        self.register_peer_heartbeat("P.H.A.S.S-GAMMA", (-3.0, 5.0, 0.25), 94.0, 0, "STANDBY")

    def register_peer_heartbeat(
        self,
        peer_id: str,
        position: Tuple[float, float, float],
        battery_pct: float,
        current_load: int,
        status: str,
    ) -> None:
        self.peers[peer_id] = SwarmPeerNode(
            peer_id=peer_id,
            position=position,
            battery_pct=battery_pct,
            current_load_tasks=current_load,
            status=status,
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
        )

    def run_contract_net_auction(
        self,
        task_id: str,
        task_name: str,
        target_pos: Tuple[float, float, float],
    ) -> Tuple[str, float]:
        """
        Executes Contract Net Protocol auction: all peer spheres calculate cost bid.
        Winner is peer with lowest bid cost: Cost = (Distance * 1.5) + (100 - Battery) * 0.5 + (Tasks * 5.0).
        """
        bids: List[TaskAuctionBid] = []

        # Local Bid
        local_dist = math.hypot(target_pos[0] - 0.0, target_pos[1] - 0.0)
        local_cost = (local_dist * 1.5) + (100.0 - 95.0) * 0.5 + (0 * 5.0)
        bids.append(TaskAuctionBid(task_id, self.local_id, local_cost, 4.5))

        # Peer Bids
        for pid, p in self.peers.items():
            dist = math.hypot(target_pos[0] - p.position[0], target_pos[1] - p.position[1])
            cost = (dist * 1.5) + (100.0 - p.battery_pct) * 0.5 + (p.current_load_tasks * 5.0)
            bids.append(TaskAuctionBid(task_id, pid, cost, 4.0 + dist * 0.5))

        bids.sort(key=lambda b: b.bid_cost)
        winning_bid = bids[0]
        logger.info(f"Swarm Auction for '{task_name}' awarded to {winning_bid.bidder_id} (Cost: {winning_bid.bid_cost:.2f})")
        return winning_bid.bidder_id, round(winning_bid.bid_cost, 2)

    def sync_crdt_knowledge_triples(self, incoming_triples: List[Dict[str, Any]]) -> int:
        """
        Merges incoming distributed knowledge triples into local CRDT set.
        """
        added_count = 0
        existing_keys = {(t["subject"], t["relation"], t["object"]) for t in self.shared_crdt_triples}

        for inc in incoming_triples:
            key = (inc["subject"], inc["relation"], inc["object"])
            if key not in existing_keys:
                self.shared_crdt_triples.append(inc)
                existing_keys.add(key)
                added_count += 1

        return added_count

    def get_swarm_snapshot(self) -> Dict[str, Any]:
        return {
            "local_node_id": self.local_id,
            "active_peers_count": len(self.peers),
            "peers": [p.to_dict() for p in self.peers.values()],
            "shared_crdt_triples_count": len(self.shared_crdt_triples),
        }


swarm_coordinator = SwarmMeshCoordinator()
