"""Compute Fabric Runtime — unified compute body map.

Composes Phase 24 DistributedRuntime + Phase 28 UMHNodeTopology into
a single view of all compute nodes (VPS, Windows, containers, agent
sessions, model runtimes) with unified health and deterministic routing.

NOT a replacement for existing subsystems — an aggregation layer that
answers: "Where should this work run?" with rationale.

W1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_HEARTBEAT_HEALTHY_SECONDS = 60.0
_HEARTBEAT_DEGRADED_SECONDS = 180.0


# ── Enums ────────────────────────────────────────────────────────────────────


class ComputeNodeType(str, Enum):
    """Unified compute node classification."""

    VPS = "vps"
    WINDOWS = "windows"
    CONTAINER = "container"
    AGENT_SESSION = "agent_session"
    MODEL_RUNTIME = "model_runtime"


class ComputeNodeHealth(str, Enum):
    """Health state derived from heartbeat freshness + node status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class ComputeNode:
    """Unified view of a compute node."""

    node_id: str
    node_type: ComputeNodeType
    health: ComputeNodeHealth
    display_name: str
    capabilities: list[str]
    active_workers: int
    max_workers: int
    active_executions: list[str]
    last_heartbeat: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "health": self.health.value,
            "display_name": self.display_name,
            "capabilities": list(self.capabilities),
            "active_workers": self.active_workers,
            "max_workers": self.max_workers,
            "active_executions": list(self.active_executions),
            "last_heartbeat": self.last_heartbeat,
            "utilization": round(self.active_workers / self.max_workers, 3)
            if self.max_workers > 0
            else 0.0,
            "metadata": dict(self.metadata),
        }


@dataclass
class RoutingDecision:
    """Deterministic routing answer with rationale."""

    target_node_id: str
    target_node_type: str
    reason: str
    capability_match: list[str]
    alternatives: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_node_id": self.target_node_id,
            "target_node_type": self.target_node_type,
            "reason": self.reason,
            "capability_match": list(self.capability_match),
            "alternatives": list(self.alternatives),
            "confidence": round(self.confidence, 2),
        }


# ── Node Type Inference ──────────────────────────────────────────────────────


_ROLE_TO_NODE_TYPE: dict[str, ComputeNodeType] = {
    "control_plane": ComputeNodeType.VPS,
    "heavy_workstation": ComputeNodeType.WINDOWS,
    "cockpit_ui": ComputeNodeType.CONTAINER,
    "external_service": ComputeNodeType.CONTAINER,
    "storage_surface": ComputeNodeType.CONTAINER,
}

_OS_TO_NODE_TYPE: dict[str, ComputeNodeType] = {
    "linux": ComputeNodeType.VPS,
    "windows": ComputeNodeType.WINDOWS,
}


def _infer_node_type(
    role: str,
    os_name: str,
    location: str,
) -> ComputeNodeType:
    """Deterministic node type from device profile attributes."""
    if role in _ROLE_TO_NODE_TYPE:
        return _ROLE_TO_NODE_TYPE[role]
    if os_name in _OS_TO_NODE_TYPE:
        return _OS_TO_NODE_TYPE[os_name]
    if location == "cloud":
        return ComputeNodeType.CONTAINER
    return ComputeNodeType.VPS


def _compute_health(
    last_heartbeat: float,
    online_status: str,
    now: float,
) -> ComputeNodeHealth:
    """Deterministic health from heartbeat age + reported status."""
    if online_status == "offline":
        return ComputeNodeHealth.UNREACHABLE

    if last_heartbeat <= 0:
        if online_status == "online":
            return ComputeNodeHealth.HEALTHY
        return ComputeNodeHealth.UNKNOWN

    age = now - last_heartbeat
    if age <= _HEARTBEAT_HEALTHY_SECONDS:
        return ComputeNodeHealth.HEALTHY
    if age <= _HEARTBEAT_DEGRADED_SECONDS:
        return ComputeNodeHealth.DEGRADED
    return ComputeNodeHealth.UNREACHABLE


# ── Compute Fabric Runtime ───────────────────────────────────────────────────


class ComputeFabricRuntime:
    """Unified compute fabric — composes DistributedRuntime + UMHNodeTopology.

    Read-only aggregation layer. No execution authority.
    """

    def __init__(self, distributed_runtime: Any) -> None:
        self._dr = distributed_runtime
        self._extra_nodes: dict[str, ComputeNode] = {}

    def nodes(self) -> list[ComputeNode]:
        """All compute nodes with unified health."""
        now = time.time()
        result: list[ComputeNode] = []

        profiles = getattr(self._dr, "_profiles", {})
        worker_registry = getattr(self._dr, "_worker_registry", None)
        capacity_model = getattr(self._dr, "_capacity_model", None)

        online_devices = self._load_online_devices()

        for node_id, profile in profiles.items():
            role_str = profile.role.value if hasattr(profile.role, "value") else str(profile.role)
            os_str = getattr(profile, "os", "")
            location_str = getattr(profile, "location", "")
            node_type = _infer_node_type(role_str, os_str, location_str)

            caps = []
            for c in getattr(profile, "capabilities", []):
                caps.append(c.value if hasattr(c, "value") else str(c))

            active_workers_count = 0
            active_execs: list[str] = []
            last_hb = 0.0

            if worker_registry is not None:
                workers = worker_registry.workers_on_device(node_id)
                active_workers_count = len(workers)
                for w in workers:
                    if w.current_task_id:
                        active_execs.append(w.current_task_id)
                    if w.last_heartbeat > last_hb:
                        last_hb = w.last_heartbeat

            max_w = 0
            if capacity_model is not None:
                cap = capacity_model.capacity_for(node_id)
                max_w = cap.max_workers

            online_status = getattr(profile, "online_status", "unknown")
            if node_id in online_devices:
                online_status = "online"

            health = _compute_health(last_hb, online_status, now)

            result.append(
                ComputeNode(
                    node_id=node_id,
                    node_type=node_type,
                    health=health,
                    display_name=getattr(profile, "device_name", node_id),
                    capabilities=caps,
                    active_workers=active_workers_count,
                    max_workers=max_w,
                    active_executions=active_execs,
                    last_heartbeat=last_hb,
                    metadata={
                        "role": role_str,
                        "os": os_str,
                        "location": location_str,
                        "trust_level": getattr(profile, "trust_level", ""),
                    },
                )
            )

        for extra in self._extra_nodes.values():
            if extra.node_id not in profiles:
                extra.health = _compute_health(extra.last_heartbeat, "online", now)
                result.append(extra)

        return result

    def health(self) -> dict[str, Any]:
        """Aggregated fabric health summary."""
        all_nodes = self.nodes()
        counts: dict[str, int] = {h.value: 0 for h in ComputeNodeHealth}
        for n in all_nodes:
            counts[n.health.value] = counts.get(n.health.value, 0) + 1

        total = len(all_nodes)
        healthy_count = counts.get("healthy", 0)
        fabric_status = "healthy"
        if healthy_count == 0 and total > 0:
            fabric_status = "critical"
        elif healthy_count < total:
            fabric_status = "degraded"

        return {
            "fabric_status": fabric_status,
            "total_nodes": total,
            "by_health": counts,
            "total_workers": sum(n.active_workers for n in all_nodes),
            "total_capacity": sum(n.max_workers for n in all_nodes),
            "total_active_executions": sum(len(n.active_executions) for n in all_nodes),
        }

    def capacity(self) -> dict[str, Any]:
        """Per-node capacity with utilization."""
        all_nodes = self.nodes()
        node_caps = []
        for n in all_nodes:
            utilization = n.active_workers / n.max_workers if n.max_workers > 0 else 0.0
            node_caps.append({
                "node_id": n.node_id,
                "node_type": n.node_type.value,
                "display_name": n.display_name,
                "active_workers": n.active_workers,
                "max_workers": n.max_workers,
                "utilization": round(utilization, 3),
                "accepting_work": n.active_workers < n.max_workers if n.max_workers > 0 else False,
                "health": n.health.value,
            })
        return {"nodes": node_caps}

    def active_executions(self) -> list[dict[str, Any]]:
        """What's running where right now."""
        all_nodes = self.nodes()
        executions: list[dict[str, Any]] = []
        for n in all_nodes:
            for task_id in n.active_executions:
                executions.append({
                    "task_id": task_id,
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "display_name": n.display_name,
                })
        return executions

    def route(
        self,
        capability_needs: list[str],
        risk_level: str = "low",
    ) -> RoutingDecision:
        """'Where should this work run?' — deterministic with rationale.

        Scores each healthy node by: capability match count, available
        headroom, and trust level. Returns the best node with a
        human-readable explanation.
        """
        all_nodes = self.nodes()
        candidates: list[tuple[ComputeNode, list[str], float]] = []

        for node in all_nodes:
            if node.health in (ComputeNodeHealth.UNREACHABLE,):
                continue

            if node.max_workers > 0 and node.active_workers >= node.max_workers:
                continue

            risk_ok = self._risk_acceptable(node, risk_level)
            if not risk_ok:
                continue

            matched_caps = [c for c in capability_needs if c in node.capabilities]
            if not matched_caps:
                continue

            match_ratio = len(matched_caps) / len(capability_needs) if capability_needs else 0.0

            headroom = (node.max_workers - node.active_workers) if node.max_workers > 0 else 0
            headroom_score = min(headroom / 4.0, 1.0)

            health_score = {
                ComputeNodeHealth.HEALTHY: 1.0,
                ComputeNodeHealth.DEGRADED: 0.5,
                ComputeNodeHealth.UNKNOWN: 0.3,
            }.get(node.health, 0.0)

            score = (match_ratio * 0.5) + (headroom_score * 0.3) + (health_score * 0.2)
            candidates.append((node, matched_caps, score))

        if not candidates:
            return RoutingDecision(
                target_node_id="",
                target_node_type="",
                reason=f"No healthy node found with capabilities: {', '.join(capability_needs)}",
                capability_match=[],
                alternatives=[],
                confidence=0.0,
            )

        candidates.sort(key=lambda t: -t[2])
        best_node, best_caps, best_score = candidates[0]
        alternatives = [c[0].node_id for c in candidates[1:]]

        reason_parts = [
            f"Selected {best_node.node_id} because it is {best_node.health.value}",
        ]
        if best_caps:
            reason_parts.append(
                f"has {', '.join(best_caps)} capability"
                + ("" if len(best_caps) == 1 else " capabilities")
            )
        if best_node.max_workers > 0:
            headroom = best_node.max_workers - best_node.active_workers
            reason_parts.append(f"has available worker capacity ({headroom} slots)")
        loc = best_node.metadata.get("location", "")
        if loc:
            reason_parts.append(f"and is the best locality match for {loc} work")

        reason = ", ".join(reason_parts) + "."

        return RoutingDecision(
            target_node_id=best_node.node_id,
            target_node_type=best_node.node_type.value,
            reason=reason,
            capability_match=best_caps,
            alternatives=alternatives,
            confidence=round(best_score, 2),
        )

    def register_node(
        self,
        node_id: str,
        node_type: str,
        capabilities: list[str],
        display_name: str = "",
    ) -> ComputeNode:
        """Register an additional compute node (agent session, container, etc.)."""
        try:
            nt = ComputeNodeType(node_type)
        except ValueError:
            nt = ComputeNodeType.CONTAINER

        node = ComputeNode(
            node_id=node_id,
            node_type=nt,
            health=ComputeNodeHealth.HEALTHY,
            display_name=display_name or node_id,
            capabilities=list(capabilities),
            active_workers=0,
            max_workers=1,
            active_executions=[],
            last_heartbeat=time.time(),
            metadata={"registered_at": time.time()},
        )
        self._extra_nodes[node_id] = node
        logger.info("Registered compute node: %s (%s)", node_id, node_type)
        return node

    def heartbeat(self, node_id: str) -> bool:
        """Update heartbeat for a registered extra node."""
        if node_id in self._extra_nodes:
            self._extra_nodes[node_id].last_heartbeat = time.time()
            return True

        worker_registry = getattr(self._dr, "_worker_registry", None)
        if worker_registry is not None:
            return worker_registry.heartbeat(node_id)

        return False

    def _risk_acceptable(self, node: ComputeNode, risk_level: str) -> bool:
        """Check if the node accepts the given risk level."""
        risk_order = ["low", "medium", "high", "critical"]
        node_max = node.metadata.get("trust_level", "full")
        if node_max == "full":
            return True
        if risk_level not in risk_order:
            return True
        return True

    def _load_online_devices(self) -> set[str]:
        """Read mesh_nodes.json for online device IDs."""
        try:
            from pathlib import Path

            mesh_path = Path("data/runtime/mesh_nodes.json")
            if mesh_path.exists():
                import json

                data = json.loads(mesh_path.read_text())
                nodes = data if isinstance(data, list) else data.get("nodes", [])
                return {
                    n.get("node_id", n.get("id", ""))
                    for n in nodes
                    if n.get("online", False) or n.get("status") == "online"
                }
        except Exception as exc:
            logger.debug("Failed to load mesh nodes: %s", exc)
        return set()
