"""Phase 77 workstation environment registry — availability and preference layer.

This is workstation-level environment awareness, NOT a replacement for
Phase 76 environment definitions or the backend registry.

Phase 76 definitions describe what capabilities an environment supports.
Backend registry controls which backend handles execution.
This registry describes availability, preference, and context from the
operator's perspective.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class EnvironmentStatus(str, Enum):
    ACTIVE = "active"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class WorkstationEnvironmentRecord:
    environment_id: str
    name: str
    environment_type: str = "general"
    device_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    safe_roots: list[str] = field(default_factory=list)
    network_policy: str = "deny"
    preferred_for: list[str] = field(default_factory=list)
    status: EnvironmentStatus = EnvironmentStatus.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "name": self.name,
            "environment_type": self.environment_type,
            "device_id": self.device_id,
            "capabilities": self.capabilities,
            "constraints": self.constraints,
            "safe_roots": self.safe_roots,
            "network_policy": self.network_policy,
            "preferred_for": self.preferred_for,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationEnvironmentRecord:
        return cls(
            environment_id=data["environment_id"],
            name=data.get("name", ""),
            environment_type=data.get("environment_type", "general"),
            device_id=data.get("device_id", ""),
            capabilities=data.get("capabilities", []),
            constraints=data.get("constraints", {}),
            safe_roots=data.get("safe_roots", []),
            network_policy=data.get("network_policy", "deny"),
            preferred_for=data.get("preferred_for", []),
            status=EnvironmentStatus(data.get("status", "unknown")),
            metadata=data.get("metadata", {}),
        )


class WorkstationEnvironmentRegistry:
    """Operator-level environment awareness. Thread-safe."""

    def __init__(self) -> None:
        self._environments: dict[str, WorkstationEnvironmentRecord] = {}
        self._lock = threading.Lock()

    def register_environment(self, env: WorkstationEnvironmentRecord) -> None:
        with self._lock:
            self._environments[env.environment_id] = env

    def get_environment(self, environment_id: str) -> WorkstationEnvironmentRecord | None:
        return self._environments.get(environment_id)

    def list_environments(self) -> list[WorkstationEnvironmentRecord]:
        return list(self._environments.values())

    def find_by_capability(self, capability: str) -> list[WorkstationEnvironmentRecord]:
        return [e for e in self._environments.values() if capability in e.capabilities]

    def find_preferred(
        self,
        capability: str | None = None,
        mode: str | None = None,
    ) -> WorkstationEnvironmentRecord | None:
        candidates = list(self._environments.values())
        if capability:
            candidates = [e for e in candidates if capability in e.capabilities]
        if mode:
            candidates = [e for e in candidates if mode in e.preferred_for]
        active = [e for e in candidates if e.status == EnvironmentStatus.ACTIVE]
        if active:
            return active[0]
        available = [e for e in candidates if e.status == EnvironmentStatus.AVAILABLE]
        if available:
            return available[0]
        return candidates[0] if candidates else None

    def set_status(self, environment_id: str, status: EnvironmentStatus) -> bool:
        with self._lock:
            env = self._environments.get(environment_id)
            if env is None:
                return False
            env.status = status
            return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "environments": [e.to_dict() for e in self._environments.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkstationEnvironmentRegistry:
        registry = cls()
        for e in data.get("environments", []):
            registry.register_environment(WorkstationEnvironmentRecord.from_dict(e))
        return registry


def export_storage_descriptors(
    registry: WorkstationEnvironmentRegistry | None = None,
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
    for e in registry.list_environments():
        descriptors.append(
            StorageRecordDescriptor(
                record_id=e.environment_id,
                record_type=StorageRecordType.ENVIRONMENT_REGISTRY,
                scope=StorageScope.SYSTEM,
                mutability=StorageMutability.MUTABLE,
                source=StorageSource.WORKSTATION,
                backend_type=StorageBackendType.MEMORY,
                owner_id="",
            )
        )

    return descriptors


def create_default_environments() -> list[WorkstationEnvironmentRecord]:
    from umh.environments.definitions import MVP_ENVIRONMENTS

    records = []
    for env_id, env_def in MVP_ENVIRONMENTS.items():
        records.append(
            WorkstationEnvironmentRecord(
                environment_id=env_id,
                name=env_def.description,
                environment_type=env_id,
                capabilities=sorted(env_def.capabilities),
                safe_roots=list(env_def.safe_roots),
                network_policy=env_def.network_policy,
                status=EnvironmentStatus.AVAILABLE
                if env_def.available
                else EnvironmentStatus.UNAVAILABLE,
            )
        )
    return records
