"""Distributed Runtime — facade composing all distributed runtime subsystems.

Single entry point for cockpit and API. Read-only queries + worker
registration. No execution authority. No transport imports.

Phase 24. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any

from substrate.organism.device_capacity import DeviceCapacityModel
from substrate.organism.device_role_registry import (
    DeviceCapability,
    DeviceNodeProfile,
    DeviceRole,
    load_registry,
    seed_known_nodes,
)
from substrate.organism.packet_router import PacketPlacement, PacketRouter
from substrate.organism.worker_lifecycle import WorkerLifecycleEmitter
from substrate.organism.worker_registry import (
    WorkerInstance,
    WorkerRegistry,
    WorkerStatus,
)

logger = logging.getLogger(__name__)

_MESH_NODES_PATH = Path("data/runtime/mesh_nodes.json")


class DistributedRuntime:
    """Facade composing all distributed runtime subsystems.

    Read-only queries + worker registration. No execution authority.
    """

    def __init__(
        self,
        event_spine: Any = None,
        device_profiles: list[DeviceNodeProfile] | None = None,
    ) -> None:
        self._event_spine = event_spine
        profiles = device_profiles or load_registry() or seed_known_nodes()
        self._profiles: dict[str, DeviceNodeProfile] = {p.node_id: p for p in profiles}

        self._worker_registry = WorkerRegistry(event_spine=event_spine)
        self._capacity_model = DeviceCapacityModel(
            self._worker_registry,
            profiles,
        )
        self._packet_router = PacketRouter(
            self._worker_registry,
            self._capacity_model,
            event_spine=event_spine,
        )
        self._lifecycle = WorkerLifecycleEmitter(event_spine) if event_spine else None
        self._placements: deque[PacketPlacement] = deque(maxlen=1000)

    def overview(self) -> dict[str, Any]:
        """Full distributed runtime state for cockpit."""
        return {
            "devices": self.device_summary(),
            "workers": self._worker_registry.to_dict(),
            "capacity": self._capacity_model.to_dict(),
            "topology": self.topology(),
        }

    def device_summary(self) -> list[dict[str, Any]]:
        """Per-device summary: profile + capacity + workers + online status."""
        online = self._load_online_devices()
        summaries: list[dict[str, Any]] = []

        for did, profile in self._profiles.items():
            cap = self._capacity_model.capacity_for(did)
            workers = self._worker_registry.workers_on_device(did)
            summaries.append(
                {
                    "device_id": did,
                    "device_name": profile.device_name,
                    "role": profile.role.value,
                    "os": profile.os,
                    "online": did in online,
                    "capabilities": [c.value for c in profile.capabilities],
                    "capacity": cap.to_dict(),
                    "worker_count": len(workers),
                    "workers": [w.to_dict() for w in workers],
                }
            )

        return summaries

    def workers(self, device_id: str | None = None) -> list[dict[str, Any]]:
        if device_id:
            ws = self._worker_registry.workers_on_device(device_id)
        else:
            ws = self._worker_registry.active_workers()
        return [w.to_dict() for w in ws]

    def capacity(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._capacity_model.all_capacities()]

    def assignments(self, limit: int = 50) -> list[dict[str, Any]]:
        items = list(self._placements)
        recent = items[-limit:] if limit else items
        return [p.to_dict() for p in reversed(recent)]

    def capabilities_matrix(self) -> dict[str, Any]:
        """Device x Capability matrix for cockpit visualization."""
        all_caps = sorted(set(c.value for c in DeviceCapability))
        matrix: dict[str, dict[str, bool]] = {}

        for did, profile in self._profiles.items():
            device_caps = {c.value for c in profile.capabilities}
            matrix[did] = {cap: cap in device_caps for cap in all_caps}

        return {
            "capabilities": all_caps,
            "devices": list(self._profiles.keys()),
            "matrix": matrix,
        }

    def topology(self) -> dict[str, Any]:
        """Capability-first organism body map.

        For each capability, which workers can satisfy it, on which
        devices, with which workspaces.
        """
        cap_map: dict[str, list[dict[str, Any]]] = {}

        for worker in self._worker_registry.active_workers():
            for cap in worker.capabilities:
                entry = {
                    "worker_id": worker.worker_id,
                    "device_id": worker.device_id,
                    "status": worker.status.value
                    if isinstance(worker.status, WorkerStatus)
                    else worker.status,
                    "device_name": self._profiles.get(
                        worker.device_id,
                        DeviceNodeProfile(
                            node_id="",
                            device_name="unknown",
                            role=DeviceRole.UNKNOWN,
                            os="",
                            location="",
                            trust_level="",
                            online_status="unknown",
                        ),
                    ).device_name,
                }
                cap_map.setdefault(cap, []).append(entry)

        for did, profile in self._profiles.items():
            for dc in profile.capabilities:
                cap_name = dc.value
                if cap_name not in cap_map:
                    cap_map[cap_name] = []

        return {
            "capabilities": cap_map,
            "total_capabilities": len(cap_map),
            "total_workers": len(self._worker_registry.active_workers()),
        }

    def register_worker(
        self,
        worker_id: str,
        device_id: str,
        runtime_id: str,
        capabilities: list[str] | None = None,
        spec: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerInstance:
        worker = self._worker_registry.register(
            worker_id=worker_id,
            device_id=device_id,
            runtime_id=runtime_id,
            capabilities=capabilities,
            spec=spec,
            metadata=metadata,
        )
        if self._lifecycle:
            self._lifecycle.on_spawn(worker)
        return worker

    def unregister_worker(self, worker_id: str) -> bool:
        worker = self._worker_registry.unregister(worker_id)
        if worker is not None and self._lifecycle:
            self._lifecycle.on_terminated(worker, "unregistered")
        return worker is not None

    def worker_heartbeat(self, worker_id: str) -> bool:
        return self._worker_registry.heartbeat(worker_id)

    def route_packet(self, packet: Any) -> PacketPlacement:
        placement = self._packet_router.route(packet)
        self._placements.append(placement)
        return placement

    def route_batch(self, packets: list[Any]) -> list[PacketPlacement]:
        results = self._packet_router.route_batch(packets)
        self._placements.extend(results)
        return results

    def _load_online_devices(self) -> set[str]:
        """Read mesh_nodes.json for online status. No transport import."""
        try:
            if _MESH_NODES_PATH.exists():
                data = json.loads(_MESH_NODES_PATH.read_text())
                nodes = data if isinstance(data, list) else data.get("nodes", [])
                return {
                    n.get("node_id", n.get("id", ""))
                    for n in nodes
                    if n.get("online", False) or n.get("status") == "online"
                }
        except Exception as exc:
            logger.debug("Failed to load mesh nodes: %s", exc)
        return set()
