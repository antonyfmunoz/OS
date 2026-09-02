"""Pure data types for the node mesh — no transport dependencies."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


@dataclass
class NodeCapability:
    name: str
    category: str
    risk_class: str
    max_risk_class: str


class PeripheralType(str, Enum):
    MONITOR = "monitor"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    CAMERA = "camera"
    INPUT_DEVICE = "input_device"
    STORAGE = "storage"
    NETWORK = "network"
    BLUETOOTH = "bluetooth"
    DISPLAY_ADAPTER = "display_adapter"


@dataclass
class Peripheral:
    """A peripheral device connected to a mesh node.

    Type-specific data goes in `properties` — keeps the wire format flat.
    """

    peripheral_id: str
    peripheral_type: str
    name: str
    manufacturer: str = ""
    model: str = ""
    device_id: str = ""
    active: bool = True
    is_default: bool = False
    health: str = "ok"
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "peripheral_id": self.peripheral_id,
            "type": self.peripheral_type,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "device_id": self.device_id,
            "active": self.active,
            "is_default": self.is_default,
            "health": self.health,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Peripheral:
        return cls(
            peripheral_id=data.get("peripheral_id", ""),
            peripheral_type=data.get("type", ""),
            name=data.get("name", ""),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
            device_id=data.get("device_id", ""),
            active=data.get("active", True),
            is_default=data.get("is_default", False),
            health=data.get("health", "ok"),
            properties=data.get("properties", {}),
        )


@dataclass
class ConnectedNode:
    node_id: str
    hostname: str
    os: str
    os_version: str
    capabilities: list[NodeCapability]
    daemon_version: str
    tailscale_ip: str
    ws: Any
    connection_id: str = ""
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: float = field(default_factory=time.monotonic)
    status: str = "connected"
    latest_metrics: dict[str, Any] = field(default_factory=dict)
    peripherals: list[Peripheral] = field(default_factory=list)

    @property
    def connected_at_iso(self) -> str:
        return self.connected_at.isoformat()

    @property
    def last_heartbeat_iso(self) -> str:
        dt = datetime.now(timezone.utc)
        return dt.isoformat()

    def update_heartbeat(self, metrics: dict[str, Any] | None = None) -> None:
        self.last_heartbeat = time.monotonic()
        self.status = "connected"
        if metrics:
            self.latest_metrics = metrics

    def heartbeat_age_s(self) -> float:
        return time.monotonic() - self.last_heartbeat

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.hostname,
            "os": self.os,
            "os_version": self.os_version,
            "status": self.status,
            "capabilities": [c.name for c in self.capabilities],
            "peripherals": [p.to_dict() for p in self.peripherals],
            "metrics": self.latest_metrics,
            "last_heartbeat": self.last_heartbeat_iso,
            "tailscale_ip": self.tailscale_ip,
            "connected_at": self.connected_at_iso,
            "daemon_version": self.daemon_version,
        }
