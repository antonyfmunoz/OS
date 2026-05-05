"""Phase 87A distributed runtime contracts — typed enums and dataclasses.

All enums have UNKNOWN fallback. All normalizers degrade gracefully.
All dataclasses support to_dict()/from_dict() round-trips.

No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


def _dist_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def clamp_score(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalize(enum_cls: type[Enum], value: str | Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        upper = value.upper().replace(" ", "_").replace("-", "_")
        for member in enum_cls:
            if member.value == value or member.name == upper:
                return member
    return enum_cls.UNKNOWN  # type: ignore[attr-defined]


# ─── Enums ─────────────────────────────────────────────────────────────


@unique
class RuntimeNodeType(str, Enum):
    VPS = "vps"
    LOCAL_PC = "local_pc"
    MOBILE = "mobile"
    TABLET = "tablet"
    CLOUD_GPU = "cloud_gpu"
    CLOUD_CPU = "cloud_cpu"
    EDGE_DEVICE = "edge_device"
    ROBOTICS = "robotics"
    UNKNOWN = "unknown"


@unique
class NodeRole(str, Enum):
    PRIMARY_COMPUTE = "primary_compute"
    DEVELOPMENT = "development"
    LOCAL_EMBODIMENT = "local_embodiment"
    GPU_BURST = "gpu_burst"
    STORAGE_ARCHIVE = "storage_archive"
    INGESTION = "ingestion"
    MONITORING = "monitoring"
    EDGE_SENSOR = "edge_sensor"
    UNKNOWN = "unknown"


@unique
class NodeAvailability(str, Enum):
    ALWAYS_ON = "always_on"
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    INTERMITTENT = "intermittent"
    FUTURE = "future"
    UNKNOWN = "unknown"


@unique
class CapabilityDomain(str, Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    DOCKER = "docker"
    SSH = "ssh"
    DISPLAY = "display"
    AUDIO = "audio"
    CAMERA = "camera"
    LOCATION = "location"
    BLUETOOTH = "bluetooth"
    USB = "usb"
    LOCAL_ACCOUNTS = "local_accounts"
    UNKNOWN = "unknown"


@unique
class SourceAffinity(str, Enum):
    LOCAL_ONLY = "local_only"
    VPS_ONLY = "vps_only"
    ANY_NODE = "any_node"
    GPU_REQUIRED = "gpu_required"
    BROWSER_REQUIRED = "browser_required"
    LOCAL_PREFERRED = "local_preferred"
    VPS_PREFERRED = "vps_preferred"
    UNKNOWN = "unknown"


@unique
class RoutingPriority(str, Enum):
    LATENCY = "latency"
    COST = "cost"
    RELIABILITY = "reliability"
    PRIVACY = "privacy"
    CAPABILITY = "capability"
    LOAD_BALANCE = "load_balance"
    UNKNOWN = "unknown"


@unique
class ArtifactSyncDirection(str, Enum):
    LOCAL_TO_VPS = "local_to_vps"
    VPS_TO_LOCAL = "vps_to_local"
    BIDIRECTIONAL = "bidirectional"
    NO_SYNC = "no_sync"
    UNKNOWN = "unknown"


@unique
class ArtifactType(str, Enum):
    CODE = "code"
    DATA = "data"
    CONFIG = "config"
    MODEL = "model"
    MEDIA = "media"
    LOG = "log"
    CREDENTIAL = "credential"
    CACHE = "cache"
    UNKNOWN = "unknown"


# ─── Normalizers ───────────────────────────────────────────────────────


def normalize_node_type(v: str | RuntimeNodeType) -> RuntimeNodeType:
    return _normalize(RuntimeNodeType, v)  # type: ignore[return-value]


def normalize_node_role(v: str | NodeRole) -> NodeRole:
    return _normalize(NodeRole, v)  # type: ignore[return-value]


def normalize_availability(v: str | NodeAvailability) -> NodeAvailability:
    return _normalize(NodeAvailability, v)  # type: ignore[return-value]


def normalize_capability_domain(v: str | CapabilityDomain) -> CapabilityDomain:
    return _normalize(CapabilityDomain, v)  # type: ignore[return-value]


def normalize_source_affinity(v: str | SourceAffinity) -> SourceAffinity:
    return _normalize(SourceAffinity, v)  # type: ignore[return-value]


def normalize_routing_priority(v: str | RoutingPriority) -> RoutingPriority:
    return _normalize(RoutingPriority, v)  # type: ignore[return-value]


def normalize_sync_direction(v: str | ArtifactSyncDirection) -> ArtifactSyncDirection:
    return _normalize(ArtifactSyncDirection, v)  # type: ignore[return-value]


def normalize_artifact_type(v: str | ArtifactType) -> ArtifactType:
    return _normalize(ArtifactType, v)  # type: ignore[return-value]


# ─── Dataclasses ───────────────────────────────────────────────────────


@dataclass
class RuntimeNodeProfile:
    node_id: str
    name: str
    node_type: RuntimeNodeType = RuntimeNodeType.UNKNOWN
    roles: list[NodeRole] = field(default_factory=list)
    availability: NodeAvailability = NodeAvailability.UNKNOWN
    capabilities: list[CapabilityDomain] = field(default_factory=list)
    description: str = ""
    hostname: str = ""
    os_family: str = ""
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    gpu: bool = False
    storage_gb: float = 0.0
    network_policy: str = ""
    safe_roots: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "roles": [r.value for r in self.roles],
            "availability": self.availability.value,
            "capabilities": [c.value for c in self.capabilities],
            "description": self.description,
            "hostname": self.hostname,
            "os_family": self.os_family,
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "gpu": self.gpu,
            "storage_gb": self.storage_gb,
            "network_policy": self.network_policy,
            "safe_roots": self.safe_roots,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RuntimeNodeProfile:
        return cls(
            node_id=d["node_id"],
            name=d.get("name", ""),
            node_type=normalize_node_type(d.get("node_type", "unknown")),
            roles=[normalize_node_role(r) for r in d.get("roles", [])],
            availability=normalize_availability(d.get("availability", "unknown")),
            capabilities=[normalize_capability_domain(c) for c in d.get("capabilities", [])],
            description=d.get("description", ""),
            hostname=d.get("hostname", ""),
            os_family=d.get("os_family", ""),
            cpu_cores=d.get("cpu_cores", 0.0),
            memory_gb=d.get("memory_gb", 0.0),
            gpu=d.get("gpu", False),
            storage_gb=d.get("storage_gb", 0.0),
            network_policy=d.get("network_policy", ""),
            safe_roots=d.get("safe_roots", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class NodeCapability:
    capability_id: str
    domain: CapabilityDomain = CapabilityDomain.UNKNOWN
    name: str = ""
    description: str = ""
    required_node_types: list[RuntimeNodeType] = field(default_factory=list)
    source_affinity: SourceAffinity = SourceAffinity.ANY_NODE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "domain": self.domain.value,
            "name": self.name,
            "description": self.description,
            "required_node_types": [t.value for t in self.required_node_types],
            "source_affinity": self.source_affinity.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NodeCapability:
        return cls(
            capability_id=d["capability_id"],
            domain=normalize_capability_domain(d.get("domain", "unknown")),
            name=d.get("name", ""),
            description=d.get("description", ""),
            required_node_types=[normalize_node_type(t) for t in d.get("required_node_types", [])],
            source_affinity=normalize_source_affinity(d.get("source_affinity", "any_node")),
            metadata=d.get("metadata", {}),
        )


@dataclass
class RoutingPolicy:
    policy_id: str
    name: str = ""
    description: str = ""
    priority: RoutingPriority = RoutingPriority.RELIABILITY
    source_affinity: SourceAffinity = SourceAffinity.ANY_NODE
    required_capabilities: list[CapabilityDomain] = field(default_factory=list)
    preferred_node_types: list[RuntimeNodeType] = field(default_factory=list)
    fallback_node_types: list[RuntimeNodeType] = field(default_factory=list)
    max_latency_ms: int = 0
    requires_gpu: bool = False
    requires_local_accounts: bool = False
    requires_browser: bool = False
    requires_display: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "source_affinity": self.source_affinity.value,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "preferred_node_types": [t.value for t in self.preferred_node_types],
            "fallback_node_types": [t.value for t in self.fallback_node_types],
            "max_latency_ms": self.max_latency_ms,
            "requires_gpu": self.requires_gpu,
            "requires_local_accounts": self.requires_local_accounts,
            "requires_browser": self.requires_browser,
            "requires_display": self.requires_display,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RoutingPolicy:
        return cls(
            policy_id=d["policy_id"],
            name=d.get("name", ""),
            description=d.get("description", ""),
            priority=normalize_routing_priority(d.get("priority", "reliability")),
            source_affinity=normalize_source_affinity(d.get("source_affinity", "any_node")),
            required_capabilities=[
                normalize_capability_domain(c) for c in d.get("required_capabilities", [])
            ],
            preferred_node_types=[
                normalize_node_type(t) for t in d.get("preferred_node_types", [])
            ],
            fallback_node_types=[normalize_node_type(t) for t in d.get("fallback_node_types", [])],
            max_latency_ms=d.get("max_latency_ms", 0),
            requires_gpu=d.get("requires_gpu", False),
            requires_local_accounts=d.get("requires_local_accounts", False),
            requires_browser=d.get("requires_browser", False),
            requires_display=d.get("requires_display", False),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ArtifactSyncPolicy:
    policy_id: str
    name: str = ""
    artifact_type: ArtifactType = ArtifactType.UNKNOWN
    direction: ArtifactSyncDirection = ArtifactSyncDirection.NO_SYNC
    source_node_type: RuntimeNodeType = RuntimeNodeType.UNKNOWN
    target_node_type: RuntimeNodeType = RuntimeNodeType.UNKNOWN
    sync_on_change: bool = False
    sync_on_schedule: bool = False
    exclude_patterns: list[str] = field(default_factory=list)
    max_size_mb: int = 0
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "artifact_type": self.artifact_type.value,
            "direction": self.direction.value,
            "source_node_type": self.source_node_type.value,
            "target_node_type": self.target_node_type.value,
            "sync_on_change": self.sync_on_change,
            "sync_on_schedule": self.sync_on_schedule,
            "exclude_patterns": self.exclude_patterns,
            "max_size_mb": self.max_size_mb,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ArtifactSyncPolicy:
        return cls(
            policy_id=d["policy_id"],
            name=d.get("name", ""),
            artifact_type=normalize_artifact_type(d.get("artifact_type", "unknown")),
            direction=normalize_sync_direction(d.get("direction", "no_sync")),
            source_node_type=normalize_node_type(d.get("source_node_type", "unknown")),
            target_node_type=normalize_node_type(d.get("target_node_type", "unknown")),
            sync_on_change=d.get("sync_on_change", False),
            sync_on_schedule=d.get("sync_on_schedule", False),
            exclude_patterns=d.get("exclude_patterns", []),
            max_size_mb=d.get("max_size_mb", 0),
            description=d.get("description", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class RoutingDecision:
    decision_id: str
    task_description: str = ""
    selected_node_id: str = ""
    selected_node_type: RuntimeNodeType = RuntimeNodeType.UNKNOWN
    policy_id: str = ""
    reason: str = ""
    alternatives: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "task_description": self.task_description,
            "selected_node_id": self.selected_node_id,
            "selected_node_type": self.selected_node_type.value,
            "policy_id": self.policy_id,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "warnings": self.warnings,
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }
