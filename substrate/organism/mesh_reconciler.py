"""Mesh node reconciliation — syncs RuntimeGraph with live mesh relay.

Polls the mesh HTTP relay (/nodes endpoint) each tick and reconciles
the RuntimeGraph: registers new mesh nodes, marks disconnected ones
unavailable, and feeds heartbeats into the supervisor.

This runs inside the organism daemon (Docker container) while the mesh
WebSocket server runs on the host as a separate process. Polling the
HTTP relay bridges the process boundary without violating architecture
layer constraints (substrate never imports from transports).

Designed to run as an AutonomousTick stage.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)

if TYPE_CHECKING:
    from substrate.organism.runtime_supervisor import RuntimeSupervisor

logger = logging.getLogger(__name__)

def _detect_relay_host() -> str:
    """Return the correct host for reaching the mesh relay.

    Inside Docker, localhost refers to the container — use host.docker.internal
    to reach the host-side relay process.
    """
    if os.path.exists("/.dockerenv"):
        return "host.docker.internal"
    return "localhost"


_DEVICE_REGISTRY_CACHE: list[dict[str, Any]] | None = None


def _load_device_registry() -> list[dict[str, Any]]:
    global _DEVICE_REGISTRY_CACHE
    if _DEVICE_REGISTRY_CACHE is not None:
        return _DEVICE_REGISTRY_CACHE
    registry_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"), "infra", "device_registry.json"
    )
    try:
        with open(registry_path) as f:
            _DEVICE_REGISTRY_CACHE = json.load(f)
    except Exception:
        _DEVICE_REGISTRY_CACHE = []
    return _DEVICE_REGISTRY_CACHE


def _resolve_device_id(node_id: str) -> str:
    for dev in _load_device_registry():
        if dev.get("mesh_node_id") == node_id or dev.get("id") == node_id:
            return dev["id"]
    return node_id


_NODE_CAP_MAP: dict[str, set[RuntimeCapability]] = {
    "shell": {RuntimeCapability.SHELL, RuntimeCapability.CODE_EXECUTE},
    "filesystem": {RuntimeCapability.FILE_OPS},
    "desktop": {RuntimeCapability.BROWSER},
    "clipboard": {RuntimeCapability.FILE_OPS},
    "gpu": {RuntimeCapability.GPU_COMPUTE},
}


@dataclass
class MeshReconcileReport:
    """Result of a single mesh reconciliation cycle."""

    timestamp: float = 0.0
    registered: list[str] = field(default_factory=list)
    marked_unavailable: list[str] = field(default_factory=list)
    heartbeats_sent: int = 0
    relay_reachable: bool = True
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "registered": self.registered,
            "marked_unavailable": self.marked_unavailable,
            "heartbeats_sent": self.heartbeats_sent,
            "relay_reachable": self.relay_reachable,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


class MeshReconciler:
    """Reconciles RuntimeGraph against the mesh HTTP relay.

    Each reconcile_tick() call:
      1. Polls GET /nodes from the mesh relay
      2. Registers any new mesh nodes in the RuntimeGraph
      3. Marks previously-registered mesh nodes that are gone as UNAVAILABLE
      4. Sends supervisor heartbeats for all connected nodes
    """

    def __init__(
        self,
        graph: RuntimeGraph,
        supervisor: "RuntimeSupervisor | None" = None,
        relay_host: str | None = None,
        relay_port: int | None = None,
    ) -> None:
        self._graph = graph
        self._supervisor = supervisor
        port = relay_port or int(os.environ.get("UMH_MESH_RELAY_PORT", "8095"))
        host = relay_host or os.environ.get("UMH_MESH_RELAY_HOST") or _detect_relay_host()
        self._relay_url = f"http://{host}:{port}"
        self._known_mesh_rids: set[str] = set()
        self._last_report = MeshReconcileReport()

    def _fetch_mesh_nodes(self) -> list[dict[str, Any]] | None:
        try:
            req = urllib.request.Request(f"{self._relay_url}/nodes", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def reconcile_tick(self) -> None:
        start = time.monotonic()
        report = MeshReconcileReport(timestamp=time.time())

        nodes = self._fetch_mesh_nodes()
        if nodes is None:
            report.relay_reachable = False
            report.elapsed_ms = (time.monotonic() - start) * 1000
            self._last_report = report
            return

        connected_rids: set[str] = set()

        for node in nodes:
            node_id = node.get("id", "")
            if not node_id:
                continue
            rid = f"mesh:{node_id}"
            connected_rids.add(rid)
            cap_names = node.get("capabilities", [])

            existing = self._graph.get(rid)
            if existing is None:
                from substrate.organism.runtime_adapters import MeshNodeRuntimeAdapter

                adapter = MeshNodeRuntimeAdapter(node_id, cap_names)
                device_id = _resolve_device_id(node_id)
                self._graph.register(
                    rid,
                    RuntimeClass.REMOTE_NODE,
                    adapter.capabilities,
                    cost=CostProfile(is_subscription=False, cost_per_1k_input=0.0),
                    adapter=adapter,
                    metadata={"device_id": device_id},
                )
                self._graph.update_status(rid, AvailabilityStatus.AVAILABLE)
                self._known_mesh_rids.add(rid)
                report.registered.append(rid)
                logger.info("mesh reconciler: registered %s (device=%s)", rid, device_id)
            else:
                if existing.status != AvailabilityStatus.AVAILABLE:
                    self._graph.update_status(rid, AvailabilityStatus.AVAILABLE)
                existing.last_heartbeat = time.time()

            if self._supervisor is not None:
                self._supervisor.supervise(rid)
                self._supervisor.heartbeat(rid)
                report.heartbeats_sent += 1

        stale = self._known_mesh_rids - connected_rids
        for rid in stale:
            self._graph.update_status(rid, AvailabilityStatus.UNAVAILABLE)
            report.marked_unavailable.append(rid)
            logger.info("mesh reconciler: marked %s unavailable", rid)
        self._known_mesh_rids = connected_rids

        report.elapsed_ms = (time.monotonic() - start) * 1000
        self._last_report = report

        if report.registered or report.marked_unavailable:
            logger.info(
                "mesh reconciliation: +%d registered, -%d unavailable, %d heartbeats (%.1fms)",
                len(report.registered),
                len(report.marked_unavailable),
                report.heartbeats_sent,
                report.elapsed_ms,
            )

    @property
    def last_report(self) -> MeshReconcileReport:
        return self._last_report

    def to_dict(self) -> dict[str, Any]:
        return {
            "relay_url": self._relay_url,
            "known_mesh_nodes": sorted(self._known_mesh_rids),
            "last_report": self._last_report.to_dict(),
        }
