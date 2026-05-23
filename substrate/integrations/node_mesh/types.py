"""Pure data types for the node mesh — no transport dependencies."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NodeCapability:
    name: str
    category: str
    risk_class: str
    max_risk_class: str


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
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: float = field(default_factory=time.monotonic)
    status: str = "connected"
    latest_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def connected_at_iso(self) -> str:
        return self.connected_at.isoformat()

    @property
    def last_heartbeat_iso(self) -> str:
        age = time.monotonic() - self.last_heartbeat
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
            "metrics": self.latest_metrics,
            "last_heartbeat": self.last_heartbeat_iso,
            "tailscale_ip": self.tailscale_ip,
            "connected_at": self.connected_at_iso,
            "daemon_version": self.daemon_version,
        }
