"""Device Continuity — per-device presence state tracking.

Maps each device (VPS, Windows, iPad, iPhone) to its last known
workspace, session, and node. Observation only — no synchronization,
no control.

Phase 32. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from substrate.operator.operator_presence import PresenceDeviceType


@dataclass
class DevicePresenceState:
    """Last known presence state for a single device."""

    device_type: PresenceDeviceType
    device_id: str = ""
    last_workspace_id: str = ""
    last_workspace_name: str = ""
    last_session_id: str = ""
    last_session_type: str = ""
    last_node_id: str = ""
    last_seen_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "last_workspace_id": self.last_workspace_id,
            "last_workspace_name": self.last_workspace_name,
            "last_session_id": self.last_session_id,
            "last_session_type": self.last_session_type,
            "last_node_id": self.last_node_id,
            "last_seen_at": self.last_seen_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DevicePresenceState:
        return cls(
            device_type=PresenceDeviceType(data.get("device_type", "unknown")),
            device_id=data.get("device_id", ""),
            last_workspace_id=data.get("last_workspace_id", ""),
            last_workspace_name=data.get("last_workspace_name", ""),
            last_session_id=data.get("last_session_id", ""),
            last_session_type=data.get("last_session_type", ""),
            last_node_id=data.get("last_node_id", ""),
            last_seen_at=data.get("last_seen_at", time.time()),
        )


class DeviceContinuityTracker:
    """Tracks per-device presence state for continuity."""

    def __init__(self) -> None:
        self._devices: dict[str, DevicePresenceState] = {}

    def update(
        self,
        device_type: PresenceDeviceType,
        device_id: str = "",
        workspace_id: str = "",
        workspace_name: str = "",
        session_id: str = "",
        session_type: str = "",
        node_id: str = "",
    ) -> DevicePresenceState:
        """Update presence state for a device."""
        key = device_id or device_type.value

        existing = self._devices.get(key)
        if existing is None:
            existing = DevicePresenceState(
                device_type=device_type,
                device_id=device_id,
            )

        if workspace_id:
            existing.last_workspace_id = workspace_id
        if workspace_name:
            existing.last_workspace_name = workspace_name
        if session_id:
            existing.last_session_id = session_id
        if session_type:
            existing.last_session_type = session_type
        if node_id:
            existing.last_node_id = node_id
        existing.last_seen_at = time.time()

        self._devices[key] = existing
        return existing

    def get(self, device_id: str) -> DevicePresenceState | None:
        """Get presence state for a device."""
        return self._devices.get(device_id)

    def get_by_type(self, device_type: PresenceDeviceType) -> DevicePresenceState | None:
        """Get presence state by device type."""
        for state in self._devices.values():
            if state.device_type == device_type:
                return state
        return None

    def all_devices(self) -> list[DevicePresenceState]:
        """All tracked device presence states."""
        return list(self._devices.values())

    def last_active_device(self) -> DevicePresenceState | None:
        """Device with most recent activity."""
        if not self._devices:
            return None
        return max(self._devices.values(), key=lambda d: d.last_seen_at)

    def device_count(self) -> int:
        """Number of tracked devices."""
        return len(self._devices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "devices": {k: v.to_dict() for k, v in self._devices.items()},
            "count": len(self._devices),
        }
