"""Device Capacity Model — per-device worker slots and backpressure.

Computes capacity from device profiles + live worker registry state.
Deterministic. No LLM calls.

Phase 24. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.device_role_registry import (
    DeviceNodeProfile,
    DeviceRole,
    load_registry,
    seed_known_nodes,
)
from substrate.organism.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)

_ROLE_LIMITS: dict[DeviceRole, int] = {
    DeviceRole.CONTROL_PLANE: 4,
    DeviceRole.HEAVY_WORKSTATION: 8,
    DeviceRole.COCKPIT_UI: 0,
    DeviceRole.MOBILE_OPERATOR: 0,
    DeviceRole.EXTERNAL_SERVICE: 2,
    DeviceRole.STORAGE_SURFACE: 0,
    DeviceRole.UNKNOWN: 1,
}


@dataclass
class DeviceCapacity:
    device_id: str = ""
    max_workers: int = 0
    active_workers: int = 0
    queued_packets: int = 0
    utilization: float = 0.0
    accepting_work: bool = False
    headroom: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "max_workers": self.max_workers,
            "active_workers": self.active_workers,
            "queued_packets": self.queued_packets,
            "utilization": round(self.utilization, 3),
            "accepting_work": self.accepting_work,
            "headroom": self.headroom,
        }


class DeviceCapacityModel:
    """Computes capacity from device profiles + worker registry state."""

    def __init__(
        self,
        worker_registry: WorkerRegistry,
        device_profiles: list[DeviceNodeProfile] | None = None,
    ) -> None:
        self._registry = worker_registry
        profiles = device_profiles or load_registry() or seed_known_nodes()
        self._profiles: dict[str, DeviceNodeProfile] = {p.node_id: p for p in profiles}

    def capacity_for(self, device_id: str) -> DeviceCapacity:
        profile = self._profiles.get(device_id)
        max_w = _ROLE_LIMITS.get(
            profile.role if profile else DeviceRole.UNKNOWN,
            1,
        )
        active = len(self._registry.workers_on_device(device_id))
        headroom = max(0, max_w - active)
        utilization = active / max_w if max_w > 0 else 1.0

        return DeviceCapacity(
            device_id=device_id,
            max_workers=max_w,
            active_workers=active,
            utilization=utilization,
            accepting_work=headroom > 0,
            headroom=headroom,
        )

    def all_capacities(self) -> list[DeviceCapacity]:
        return [self.capacity_for(did) for did in self._profiles]

    def best_device_for_work(self, eligible_devices: list[str]) -> str | None:
        best_id: str | None = None
        best_headroom = -1
        for did in eligible_devices:
            cap = self.capacity_for(did)
            if cap.accepting_work and cap.headroom > best_headroom:
                best_headroom = cap.headroom
                best_id = did
        return best_id

    def is_saturated(self, device_id: str) -> bool:
        return not self.capacity_for(device_id).accepting_work

    def to_dict(self) -> dict[str, Any]:
        caps = self.all_capacities()
        return {
            "devices": [c.to_dict() for c in caps],
            "total_headroom": sum(c.headroom for c in caps),
            "saturated_count": sum(1 for c in caps if not c.accepting_work),
        }
