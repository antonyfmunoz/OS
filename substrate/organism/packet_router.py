"""Packet Router — capability-first work routing.

Routes WorkPackets through the chain:
  Packet → Capability → Worker → Device → Workspace → Runtime

Capability is the primary routing target. Device is an implementation
detail derived from which nodes can satisfy the capability.

Deterministic. No LLM calls. No execution authority.

Phase 24. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from substrate.organism.device_capacity import DeviceCapacityModel
from substrate.organism.device_role_registry import (
    DeviceCapability,
    DeviceNodeProfile,
    load_registry,
    seed_known_nodes,
)
from substrate.organism.worker_registry import WorkerInstance, WorkerRegistry, WorkerStatus

logger = logging.getLogger(__name__)

_CAPABILITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("react_build", re.compile(r"(?i)\b(react|vite|next\.?js|frontend|tsx|jsx)\b")),
    ("electron_build", re.compile(r"(?i)\b(electron|desktop.app)\b")),
    ("code_execution", re.compile(r"(?i)\b(run|execute|script|python|node)\b")),
    ("code_review", re.compile(r"(?i)\b(review|audit|check|verify)\b")),
    ("code_write", re.compile(r"(?i)\b(implement|build|create|add|write|fix|refactor)\b")),
    ("browser_automation", re.compile(r"(?i)\b(browser|scrape|crawl|selenium|playwright)\b")),
    ("gpu_compute", re.compile(r"(?i)\b(gpu|cuda|model.train|inference|ml|ai)\b")),
    ("media_generation", re.compile(r"(?i)\b(video|image|render|media|ffmpeg)\b")),
    ("deployment", re.compile(r"(?i)\b(deploy|release|ship|publish)\b")),
    ("documentation", re.compile(r"(?i)\b(doc|readme|wiki|knowledge)\b")),
]

_CAPABILITY_DEVICE_CAPS: dict[str, list[DeviceCapability]] = {
    "react_build": [DeviceCapability.CODE_EXECUTION],
    "electron_build": [DeviceCapability.DESKTOP_AUTOMATION, DeviceCapability.CODE_EXECUTION],
    "gpu_compute": [DeviceCapability.GPU_AVAILABLE],
    "browser_automation": [DeviceCapability.BROWSER_AUTOMATION],
    "media_generation": [DeviceCapability.MEDIA_GENERATION],
}


@dataclass
class PacketPlacement:
    packet_id: str = ""
    required_capability: str = ""
    matched_worker_id: str = ""
    device_id: str = ""
    workspace_path: str = ""
    runtime_id: str = ""
    execution_environment: str = ""
    capacity_at_placement: dict[str, Any] = field(default_factory=dict)
    requires_remote_dispatch: bool = False
    routing_chain: list[str] = field(default_factory=list)
    reason: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "required_capability": self.required_capability,
            "matched_worker_id": self.matched_worker_id,
            "device_id": self.device_id,
            "workspace_path": self.workspace_path,
            "runtime_id": self.runtime_id,
            "execution_environment": self.execution_environment,
            "capacity_at_placement": self.capacity_at_placement,
            "requires_remote_dispatch": self.requires_remote_dispatch,
            "routing_chain": self.routing_chain,
            "reason": self.reason,
            "created_at": self.created_at,
        }


class PacketRouter:
    """Routes WorkPackets via capability-first chain."""

    def __init__(
        self,
        worker_registry: WorkerRegistry,
        capacity_model: DeviceCapacityModel,
        runtime_graph: Any = None,
        event_spine: Any = None,
    ) -> None:
        self._workers = worker_registry
        self._capacity = capacity_model
        self._runtime_graph = runtime_graph
        self._event_spine = event_spine
        profiles = load_registry() or seed_known_nodes()
        self._profiles: dict[str, DeviceNodeProfile] = {p.node_id: p for p in profiles}

    def route(self, packet: Any) -> PacketPlacement:
        """Capability-first routing chain."""
        chain: list[str] = []
        packet_id = getattr(packet, "packet_id", "") or getattr(packet, "id", "") or ""
        description = getattr(packet, "description", "") or getattr(packet, "action_type", "") or ""
        target_repo = getattr(packet, "target_repo", "") or ""

        capability = self._infer_capability(description)
        chain.append(f"capability:{capability}")

        worker = self._find_best_worker(capability, target_repo)
        worker_id = worker.worker_id if worker else ""
        chain.append(f"worker:{worker_id or 'none'}")

        if worker:
            device_id = worker.device_id
        else:
            device_id = self._find_device_for_capability(capability)
        chain.append(f"device:{device_id or 'none'}")

        workspace = self._resolve_workspace(device_id, target_repo) if device_id else ""
        chain.append(f"workspace:{workspace or 'none'}")

        runtime_id = ""
        if self._runtime_graph is not None and device_id:
            try:
                candidates = self._runtime_graph.select(
                    required=None,
                    device_preference=[device_id],
                )
                if candidates:
                    runtime_id = candidates[0].runtime_id
            except Exception:
                pass
        chain.append(f"runtime:{runtime_id or 'none'}")

        cap_snapshot = self._capacity.capacity_for(device_id).to_dict() if device_id else {}
        requires_remote = device_id != "" and not self._is_local_device(device_id)

        reason_parts = [f"capability={capability}"]
        if worker:
            reason_parts.append(f"matched worker {worker_id} on {device_id}")
        elif device_id:
            reason_parts.append(f"no idle worker, selected device {device_id} by capability")
        else:
            reason_parts.append("no eligible device found")

        placement = PacketPlacement(
            packet_id=packet_id,
            required_capability=capability,
            matched_worker_id=worker_id,
            device_id=device_id,
            workspace_path=workspace,
            runtime_id=runtime_id,
            capacity_at_placement=cap_snapshot,
            requires_remote_dispatch=requires_remote,
            routing_chain=chain,
            reason="; ".join(reason_parts),
        )

        self._emit(
            "packet_routed",
            {
                "packet_id": packet_id,
                "device_id": device_id,
                "capability": capability,
                "worker_id": worker_id,
            },
        )

        return placement

    def route_batch(self, packets: list[Any]) -> list[PacketPlacement]:
        return [self.route(p) for p in packets]

    def _infer_capability(self, description: str) -> str:
        for cap_name, pattern in _CAPABILITY_PATTERNS:
            if pattern.search(description):
                return cap_name
        return "code_write"

    def _find_best_worker(self, capability: str, target_repo: str) -> WorkerInstance | None:
        candidates = self._workers.workers_with_capability(capability)
        idle = [w for w in candidates if w.status == WorkerStatus.IDLE]
        if not idle:
            return None
        if target_repo:
            for w in idle:
                if not self._capacity.is_saturated(w.device_id):
                    return w
        for w in idle:
            if not self._capacity.is_saturated(w.device_id):
                return w
        return idle[0] if idle else None

    def _find_device_for_capability(self, capability: str) -> str:
        required_caps = _CAPABILITY_DEVICE_CAPS.get(capability, [])
        eligible: list[str] = []
        for did, profile in self._profiles.items():
            if required_caps and not all(c in profile.capabilities for c in required_caps):
                continue
            if capability in profile.blocked_workloads:
                continue
            eligible.append(did)

        if not eligible:
            eligible = list(self._profiles.keys())

        best = self._capacity.best_device_for_work(eligible)
        return best or (eligible[0] if eligible else "")

    def _resolve_workspace(self, device_id: str, target_repo: str) -> str:
        if not target_repo:
            return ""
        profile = self._profiles.get(device_id)
        if profile is None:
            return ""
        if profile.os == "windows":
            return f"C:\\Projects\\{target_repo}"
        return f"/opt/{target_repo}"

    def _is_local_device(self, device_id: str) -> bool:
        profile = self._profiles.get(device_id)
        if profile is None:
            return False
        return profile.location == "vps"

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_spine is None:
            return
        try:
            from substrate.organism.event_spine import EventDomain

            self._event_spine.emit(
                domain=EventDomain.WORKER,
                event_type=event_type,
                source="packet_router",
                data=data,
            )
        except Exception as exc:
            logger.debug("PacketRouter event emission failed: %s", exc)
