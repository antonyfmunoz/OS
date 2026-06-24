"""Device Awareness Runtime — deterministic device detection and capability routing.

Detects which device the operator is on and routes work to the best
available device based on capability requirements. All detection is
deterministic: env vars, hostname matching, registry lookup. No LLM.

Device names come from infra/device_registry.json — never hardcoded.

Campaign 5.3. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import weakref
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_INSTANCES: set[weakref.ref] = set()

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"

# Capability keywords mapped to device properties that satisfy them.
# Used by best_device_for() for deterministic routing.
_CAPABILITY_MATCHERS: dict[str, list[str]] = {
    "gpu": ["gpu"],
    "gpu_available": ["gpu"],
    "heavy_compute": ["gpu", "compute"],
    "orchestration": ["role:orchestrator"],
    "execution": ["role:executor", "compute"],
    "always_on": ["always_online"],
    "local_models": ["gpu"],
}


@dataclass
class DeviceRecord:
    """Parsed device from device_registry.json."""

    device_id: str
    display_name: str
    tailscale_name: str = ""
    device_type: str = ""
    os_name: str = ""
    role: str = ""
    tailscale_ip: str = ""
    always_online: bool = False
    compute: bool = False
    gpu: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.device_id,
            "display_name": self.display_name,
            "tailscale_name": self.tailscale_name,
            "device_type": self.device_type,
            "os": self.os_name,
            "role": self.role,
            "compute": self.compute,
            "gpu": self.gpu,
            "always_online": self.always_online,
        }


class DeviceAwarenessRuntime:
    """Deterministic device detection and capability-based routing."""

    def __init__(
        self,
        reality_graph: Any | None = None,
        device_registry_path: str | None = None,
    ) -> None:
        self._graph = reality_graph
        self._devices: dict[str, DeviceRecord] = {}
        self._registry_path = device_registry_path
        self._load_registry(device_registry_path)
        _INSTANCES.add(weakref.ref(self, _INSTANCES.discard))

    def reload(self) -> None:
        """Re-read the device registry from disk. Called by cache invalidation."""
        self._devices.clear()
        self._load_registry(self._registry_path)

    def _load_registry(self, path: str | None) -> None:
        registry_path = path or os.path.join(_ROOT, "infra", "device_registry.json")
        try:
            with open(registry_path, "r") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug("Could not load device registry %s: %s", registry_path, exc)
            return

        for entry in raw:
            dev_id = entry.get("id", "")
            if not dev_id:
                continue
            record = DeviceRecord(
                device_id=dev_id,
                display_name=entry.get("display_name", dev_id),
                tailscale_name=entry.get("tailscale_name", ""),
                device_type=entry.get("device_type", ""),
                os_name=entry.get("os", ""),
                role=entry.get("role", ""),
                tailscale_ip=entry.get("tailscale_ip", ""),
                always_online=bool(entry.get("always_online", False)),
                compute=bool(entry.get("compute", False)),
                gpu=entry.get("gpu", ""),
                properties={
                    k: v for k, v in entry.items()
                    if k not in (
                        "id", "display_name", "tailscale_name", "device_type",
                        "os", "role", "tailscale_ip", "always_online", "compute", "gpu",
                    )
                },
            )
            self._devices[dev_id] = record

    # ── Detection ─────────────────────────────────────────────────────

    def detect_active_device(self) -> str:
        env_device = os.environ.get("UMH_DEVICE_ID", "")
        if env_device and env_device in self._devices:
            return env_device

        hostname = os.environ.get("HOSTNAME", "") or socket.gethostname()
        if hostname:
            for dev in self._devices.values():
                if dev.tailscale_name and dev.tailscale_name == hostname:
                    return dev.device_id
            hostname_lower = hostname.lower()
            for dev in self._devices.values():
                if dev.tailscale_name and dev.tailscale_name.lower() in hostname_lower:
                    return dev.device_id

        return "unknown"

    # ── Capability Queries ────────────────────────────────────────────

    def device_capabilities(self, device_id: str) -> dict[str, Any]:
        record = self._devices.get(device_id)
        if record is None:
            return {}

        caps: dict[str, Any] = record.to_dict()

        if self._graph is not None:
            from substrate.organism.reality_graph import RealityEntityType
            entity = self._graph.get(f"dev-{device_id}")
            if entity is not None:
                caps["graph_properties"] = entity.properties
                caps["graph_status"] = entity.status.value if hasattr(entity.status, "value") else str(entity.status)

        return caps

    def best_device_for(self, capability: str) -> str:
        matchers = _CAPABILITY_MATCHERS.get(capability.lower(), [capability.lower()])
        scored: list[tuple[int, str]] = []

        for dev in self._devices.values():
            score = 0
            for matcher in matchers:
                if matcher.startswith("role:"):
                    required_role = matcher.split(":", 1)[1]
                    if dev.role == required_role:
                        score += 2
                elif matcher == "gpu" and dev.gpu:
                    score += 2
                elif matcher == "compute" and dev.compute:
                    score += 1
                elif matcher == "always_online" and dev.always_online:
                    score += 1
            if score > 0:
                scored.append((score, dev.device_id))

        if not scored:
            return "unknown"

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def available_devices(self) -> list[dict[str, str]]:
        return [
            {"id": dev.device_id, "name": dev.display_name, "role": dev.role}
            for dev in self._devices.values()
        ]

    # ── Context Population ────────────────────────────────────────────

    def populate_context(self, ctx: Any) -> None:
        active = self.detect_active_device()
        ctx.active_device = active

        ctx.active_compute_nodes = [
            dev.to_dict() for dev in self._devices.values()
            if dev.compute
        ]

        ctx.preferred_execution_device = self.best_device_for("heavy_compute")

        ctx.available_execution_devices = [
            dev.device_id for dev in self._devices.values()
            if dev.compute
        ]

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        active = self.detect_active_device()
        return {
            "active_device": active,
            "active_device_capabilities": self.device_capabilities(active) if active != "unknown" else {},
            "preferred_execution_device": self.best_device_for("heavy_compute"),
            "available_devices": self.available_devices(),
            "device_count": len(self._devices),
        }
