"""Phase 77 device registry — tracks known devices in the workstation.

Devices are explicitly registered, not probed.  No OS probing,
no network probing.  Missing devices degrade to UNKNOWN.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class DeviceType(str, Enum):
    VPS = "vps"
    LOCAL_DESKTOP = "local_desktop"
    LAPTOP = "laptop"
    MOBILE = "mobile"
    TABLET = "tablet"
    CLOUD_NODE = "cloud_node"
    SANDBOX = "sandbox"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class DeviceRecord:
    device_id: str
    name: str
    device_type: DeviceType = DeviceType.UNKNOWN
    environment_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_seen: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "environment_id": self.environment_id,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceRecord:
        return cls(
            device_id=data["device_id"],
            name=data.get("name", ""),
            device_type=DeviceType(data.get("device_type", "unknown")),
            environment_id=data.get("environment_id", ""),
            capabilities=data.get("capabilities", []),
            status=DeviceStatus(data.get("status", "unknown")),
            last_seen=data.get("last_seen", ""),
            metadata=data.get("metadata", {}),
        )


class DeviceRegistry:
    """In-memory registry of known devices. Thread-safe."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceRecord] = {}
        self._lock = threading.Lock()

    def register_device(self, device: DeviceRecord) -> None:
        with self._lock:
            self._devices[device.device_id] = device

    def get_device(self, device_id: str) -> DeviceRecord | None:
        return self._devices.get(device_id)

    def list_devices(self) -> list[DeviceRecord]:
        return list(self._devices.values())

    def mark_seen(self, device_id: str) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.last_seen = _iso_now()
            if device.status == DeviceStatus.UNKNOWN:
                device.status = DeviceStatus.AVAILABLE
            return True

    def set_status(self, device_id: str, status: DeviceStatus) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            device.status = status
            return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "devices": [d.to_dict() for d in self._devices.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceRegistry:
        registry = cls()
        for d in data.get("devices", []):
            registry.register_device(DeviceRecord.from_dict(d))
        return registry


def export_storage_descriptors(
    registry: DeviceRegistry | None = None,
) -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    if registry is None:
        return []

    descriptors: list[StorageRecordDescriptor] = []
    for d in registry.list_devices():
        descriptors.append(
            StorageRecordDescriptor(
                record_id=d.device_id,
                record_type=StorageRecordType.DEVICE_REGISTRY,
                scope=StorageScope.SYSTEM,
                mutability=StorageMutability.MUTABLE,
                source=StorageSource.WORKSTATION,
                backend_type=StorageBackendType.MEMORY,
                owner_id="",
                created_at=d.last_seen or "",
            )
        )

    return descriptors


def create_default_devices() -> list[DeviceRecord]:
    return [
        DeviceRecord(
            device_id="default_vps",
            name="Primary VPS",
            device_type=DeviceType.VPS,
            environment_id="local",
            capabilities=[
                "cli.command",
                "filesystem.read",
                "filesystem.write",
                "filesystem.list",
                "http.get",
                "http.post",
            ],
            status=DeviceStatus.ACTIVE,
            last_seen=_iso_now(),
        ),
    ]
