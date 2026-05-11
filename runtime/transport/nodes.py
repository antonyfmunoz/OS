"""
Node abstraction — execution targets beyond "the VPS".

Today EOS implicitly assumes all work happens on the VPS. This module
introduces a typed `Node` model and an in-memory `NodeRegistry` so future
routing code can reason about *where* work runs (VPS, local station, future
remote GPU box, future mobile companion) without hardcoding machine names.

This is SCAFFOLDING. It does not replace current routing. The model_router
continues to make its own decisions. Eventually capability-aware routing
(see runtime.transport.capabilities) will consult the node registry to pick
a target, but that integration is intentionally deferred.

Usage:
    from runtime.substrate import NodeRegistry, Node, NodeType, NodeStatus

    reg = NodeRegistry.default()
    reg.upsert(Node(
        node_id="vps-primary",
        node_type=NodeType.VPS,
        capabilities=["reasoning", "long_running_session"],
        status=NodeStatus.ONLINE,
    ))
    vps = reg.get("vps-primary")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class NodeType(str, Enum):
    """Known execution target classes. Extend cautiously."""

    VPS = "vps"
    LOCAL_STATION = "local_station"
    FUTURE_REMOTE = "future_remote"
    FUTURE_MOBILE = "future_mobile"


class NodeRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    WORKSTATION = "workstation"
    OBSERVER = "observer"


class NodeStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class Node:
    """
    A single execution target the substrate can reason about.

    `capabilities` is a list of capability slugs — kept as plain strings so
    this module has no import-cycle with runtime.transport.capabilities.
    Callers can validate against `Capability` from that module when needed.
    """

    node_id: str
    node_type: NodeType
    role: NodeRole = NodeRole.WORKSTATION
    capabilities: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.UNKNOWN
    availability: str = "unknown"  # e.g. "always", "when_awake", "on_demand"
    metadata: dict = field(default_factory=dict)
    last_seen: Optional[str] = None  # ISO timestamp string

    def touch(self) -> None:
        self.last_seen = datetime.now(timezone.utc).isoformat()

    def has_capability(self, slug: str) -> bool:
        return slug in self.capabilities


class NodeRegistry:
    """
    Persistent node registry.

    State is held in memory for fast access and flushed through
    runtime.transport.storage on every upsert/remove, so nodes survive across
    processes. Storage falls back to a JSON file if Neon is unavailable.
    """

    _STORAGE_KEY = "nodes"
    _default: Optional["NodeRegistry"] = None

    def __init__(self, *, persist: bool = True) -> None:
        self._nodes: dict[str, Node] = {}
        self._persist = persist
        if persist:
            self._load()

    # ─── Persistence ──────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            from runtime.transport.storage import get_storage

            raw = get_storage().get(self._STORAGE_KEY, default={}) or {}
            for node_id, data in raw.items():
                self._nodes[node_id] = Node(
                    node_id=data["node_id"],
                    node_type=NodeType(data.get("node_type", NodeType.VPS.value)),
                    capabilities=list(data.get("capabilities", [])),
                    status=NodeStatus(data.get("status", NodeStatus.UNKNOWN.value)),
                    availability=data.get("availability", "unknown"),
                    metadata=data.get("metadata", {}) or {},
                    last_seen=data.get("last_seen"),
                )
        except Exception as e:
            import sys

            print(f"[substrate.nodes] load failed ({e}); starting empty", file=sys.stderr)

    def _flush(self) -> None:
        if not self._persist:
            return
        try:
            from runtime.transport.storage import get_storage

            payload = {
                nid: {
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "capabilities": list(n.capabilities),
                    "status": n.status.value,
                    "availability": n.availability,
                    "metadata": n.metadata,
                    "last_seen": n.last_seen,
                }
                for nid, n in self._nodes.items()
            }
            get_storage().put(self._STORAGE_KEY, payload)
        except Exception as e:
            import sys

            print(f"[substrate.nodes] flush failed ({e}); in-memory only", file=sys.stderr)

    # ─── CRUD ─────────────────────────────────────────────────────────────
    def upsert(self, node: Node) -> Node:
        node.touch()
        self._nodes[node.node_id] = node
        self._flush()
        return node

    def get(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        if self._nodes.pop(node_id, None) is not None:
            self._flush()

    def all(self) -> list[Node]:
        return list(self._nodes.values())

    # ─── Queries ──────────────────────────────────────────────────────────
    def by_type(self, node_type: NodeType) -> list[Node]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def with_capability(self, slug: str) -> list[Node]:
        return [n for n in self._nodes.values() if n.has_capability(slug)]

    def online(self) -> list[Node]:
        return [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]

    def purge_stale(self, *, max_age_hours: float = 24.0) -> list[str]:
        """Remove nodes whose last_seen is older than max_age_hours.

        Protects well-known nodes (vps-primary, antony-workstation) from
        purge.  Returns list of removed node_ids.
        """
        from datetime import datetime, timezone

        protected = {"vps-primary", "antony-workstation"}
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed: list[str] = []

        for node_id, node in list(self._nodes.items()):
            if node_id in protected:
                continue
            if node.last_seen is None:
                # No last_seen — stale by definition
                removed.append(node_id)
                continue
            try:
                seen_ts = datetime.fromisoformat(node.last_seen).timestamp()
                if seen_ts < cutoff:
                    removed.append(node_id)
            except (ValueError, TypeError):
                removed.append(node_id)

        for nid in removed:
            self._nodes.pop(nid, None)
        if removed:
            self._flush()
            import sys

            print(
                f"[substrate.nodes] purged {len(removed)} stale node(s)",
                file=sys.stderr,
            )
        return removed

    # ─── Defaults ─────────────────────────────────────────────────────────
    @classmethod
    def default(cls) -> "NodeRegistry":
        """
        Process-wide default registry, seeded with the current VPS as the
        sole known node. Safe to call multiple times.
        """
        if cls._default is None:
            reg = cls()
            # Seed vps-primary only if it's not already persisted.
            if reg.get("vps-primary") is None:
                reg.upsert(
                    Node(
                        node_id="vps-primary",
                        node_type=NodeType.VPS,
                        capabilities=[
                            "reasoning",
                            "long_running_session",
                            "high_compute",
                        ],
                        status=NodeStatus.ONLINE,
                        availability="always",
                        metadata={"role": "control_plane"},
                    )
                )
            cls._default = reg
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        cls._default = None
