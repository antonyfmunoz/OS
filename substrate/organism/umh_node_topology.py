"""UMH Node Topology — canonical node role and version models.

Models UMH as one distributed organism running the same substrate
across multiple nodes. Each node has a role, purpose, active services,
capabilities, and version info. Version drift is detected; capability
drift is expected.

Read-only topology — no execution, no deployment, no remote control.

Phase 28. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class UMHNodeRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CONTROL_PLANE = "control_plane"
    WORKSTATION = "workstation"
    BUILDER = "builder"
    OBSERVER = "observer"
    CONTROLLER = "controller"
    FALLBACK = "fallback"


class UMHNodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class UMHServiceRole(str, Enum):
    COCKPIT_API = "cockpit_api"
    COCKPIT_FRONTEND = "cockpit_frontend"
    GOVERNANCE = "governance"
    MEMORY = "memory"
    EVENT_SPINE = "event_spine"
    DISTRIBUTED_RUNTIME = "distributed_runtime"
    ACTION_BRIDGE = "action_bridge"
    META_IDE = "meta_ide"
    WORKSPACE_OBSERVATION = "workspace_observation"
    WORKSTATION_CONTROL = "workstation_control"
    VISION_RUNTIME = "vision_runtime"
    VOICE_RUNTIME = "voice_runtime"
    LOCAL_BUILDER = "local_builder"


class UMHVersionStatus(str, Enum):
    COHERENT = "coherent"
    DRIFTED = "drifted"
    UNKNOWN = "unknown"


@dataclass
class UMHVersionInfo:
    umh_version: str = ""
    git_commit: str = ""
    branch: str = "main"
    schema_version: str = ""
    migration_version: str = ""
    build_timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "umh_version": self.umh_version,
            "git_commit": self.git_commit,
            "branch": self.branch,
            "schema_version": self.schema_version,
            "migration_version": self.migration_version,
            "build_timestamp": self.build_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UMHVersionInfo:
        return cls(
            umh_version=data.get("umh_version", ""),
            git_commit=data.get("git_commit", ""),
            branch=data.get("branch", "main"),
            schema_version=data.get("schema_version", ""),
            migration_version=data.get("migration_version", ""),
            build_timestamp=data.get("build_timestamp", 0.0),
        )

    def matches(self, other: UMHVersionInfo) -> bool:
        if not self.git_commit or not other.git_commit:
            return False
        return (
            self.git_commit == other.git_commit
            and self.schema_version == other.schema_version
            and self.migration_version == other.migration_version
        )


@dataclass
class UMHServiceActivation:
    service_id: str
    node_id: str = ""
    service_role: str = ""
    active: bool = True
    status: str = "unknown"
    endpoint: str = ""
    health: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "node_id": self.node_id,
            "service_role": self.service_role,
            "active": self.active,
            "status": self.status,
            "endpoint": self.endpoint,
            "health": self.health,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UMHServiceActivation:
        return cls(
            service_id=data.get("service_id", ""),
            node_id=data.get("node_id", ""),
            service_role=data.get("service_role", ""),
            active=data.get("active", True),
            status=data.get("status", "unknown"),
            endpoint=data.get("endpoint", ""),
            health=data.get("health", "unknown"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UMHNodeRecord:
    node_id: str
    device_id: str = ""
    hostname: str = ""
    purpose: str = ""
    roles: list[str] = field(default_factory=list)
    status: str = "unknown"
    version: UMHVersionInfo = field(default_factory=UMHVersionInfo)
    active_services: list[UMHServiceActivation] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)
    workspace_ids: list[str] = field(default_factory=list)
    owned_state_domains: list[str] = field(default_factory=list)
    primary: bool = False
    last_seen: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "device_id": self.device_id,
            "hostname": self.hostname,
            "purpose": self.purpose,
            "roles": self.roles,
            "status": self.status,
            "version": self.version.to_dict(),
            "active_services": [s.to_dict() for s in self.active_services],
            "capability_ids": self.capability_ids,
            "workspace_ids": self.workspace_ids,
            "owned_state_domains": self.owned_state_domains,
            "primary": self.primary,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UMHNodeRecord:
        version_data = data.get("version", {})
        version = UMHVersionInfo.from_dict(version_data) if version_data else UMHVersionInfo()
        services_data = data.get("active_services", [])
        services = (
            [UMHServiceActivation.from_dict(s) for s in services_data]
            if isinstance(services_data, list)
            and services_data
            and isinstance(services_data[0], dict)
            else []
        )
        return cls(
            node_id=data.get("node_id", ""),
            device_id=data.get("device_id", ""),
            hostname=data.get("hostname", ""),
            purpose=data.get("purpose", ""),
            roles=data.get("roles", []),
            status=data.get("status", "unknown"),
            version=version,
            active_services=services,
            capability_ids=data.get("capability_ids", []),
            workspace_ids=data.get("workspace_ids", []),
            owned_state_domains=data.get("owned_state_domains", []),
            primary=data.get("primary", False),
            last_seen=data.get("last_seen", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UMHNodeTopology:
    topology_id: str = field(default_factory=lambda: f"unt-{uuid4().hex[:12]}")
    organism_id: str = "umh"
    nodes: list[UMHNodeRecord] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    version_status: str = "unknown"
    canonical_version: UMHVersionInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "organism_id": self.organism_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "node_count": len(self.nodes),
            "generated_at": self.generated_at,
            "version_status": self.version_status,
            "canonical_version": self.canonical_version.to_dict()
            if self.canonical_version
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UMHNodeTopology:
        cv = data.get("canonical_version")
        return cls(
            topology_id=data.get("topology_id", ""),
            organism_id=data.get("organism_id", "umh"),
            nodes=[UMHNodeRecord.from_dict(n) for n in data.get("nodes", [])],
            generated_at=data.get("generated_at", 0.0),
            version_status=data.get("version_status", "unknown"),
            canonical_version=UMHVersionInfo.from_dict(cv) if cv else None,
        )
