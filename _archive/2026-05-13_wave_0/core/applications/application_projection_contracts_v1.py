"""Application Projection Contracts v1.

15 contracts, 5 enums for governed application projection.

Applications are NOT intelligence systems.
Applications are interfaces + domain surfaces + orchestration views
over substrate capabilities.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_id(prefix: str, content: str) -> str:
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"{prefix}-{h}"


def _uuid_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Enums ──────────────────────────────────────────────


class ApplicationLifecycleState(enum.Enum):
    REGISTERED = "registered"
    PROJECTED = "projected"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RESTORED = "restored"
    ARCHIVED = "archived"


class ApplicationEventType(enum.Enum):
    APPLICATION_REGISTERED = "application_registered"
    CAPABILITY_BOUND = "capability_bound"
    PROJECTION_CREATED = "projection_created"
    PROJECTION_DENIED = "projection_denied"
    APPLICATION_CONTEXT_STARTED = "application_context_started"
    APPLICATION_CONTEXT_RESTORED = "application_context_restored"
    APPLICATION_BOUNDARY_DENIED = "application_boundary_denied"
    APPLICATION_REPLAY_VALIDATED = "application_replay_validated"


class DomainContextType(enum.Enum):
    BUSINESS = "business"
    PERSONAL = "personal"
    CREATOR_MEDIA = "creator_media"
    INFRASTRUCTURE = "infrastructure"
    RESEARCH = "research"
    OPERATIONS = "operations"


class ApplicationTrustTier(enum.Enum):
    CORE = "core"
    GOVERNED = "governed"
    RESTRICTED = "restricted"
    SANDBOXED = "sandboxed"


class CapabilityCategory(enum.Enum):
    COGNITION = "cognition"
    WORKFLOWS = "workflows"
    KNOWLEDGE = "knowledge"
    LEARNING = "learning"
    RESILIENCE = "resilience"
    SCALING = "scaling"
    ENVIRONMENTS = "environments"
    SESSIONS = "sessions"
    OBSERVABILITY = "observability"


# ── Contracts ──────────────────────────────────────────


@dataclass
class ApplicationProjection:
    projection_id: str = ""
    application_id: str = ""
    domain_context: str = ""
    capabilities_bound: list[str] = field(default_factory=list)
    trust_tier: str = "restricted"
    created_at: str = ""
    projection_hash: str = ""

    def __post_init__(self) -> None:
        if not self.projection_id:
            self.projection_id = _uuid_id("aproj")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.projection_hash:
            content = f"{self.application_id}:{self.domain_context}:{','.join(sorted(self.capabilities_bound))}"
            self.projection_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "application_id": self.application_id,
            "domain_context": self.domain_context,
            "capabilities_bound": self.capabilities_bound,
            "trust_tier": self.trust_tier,
            "created_at": self.created_at,
            "projection_hash": self.projection_hash,
        }


@dataclass
class ApplicationCapabilitySurface:
    surface_id: str = ""
    application_id: str = ""
    capability_category: str = ""
    exposed_operations: list[str] = field(default_factory=list)
    trust_tier: str = "restricted"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.surface_id:
            self.surface_id = _uuid_id("acaps")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "application_id": self.application_id,
            "capability_category": self.capability_category,
            "exposed_operations": self.exposed_operations,
            "trust_tier": self.trust_tier,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationRuntimeContext:
    context_id: str = ""
    application_id: str = ""
    domain_context: str = ""
    session_id: str = ""
    started_at: str = ""
    context_hash: str = ""

    def __post_init__(self) -> None:
        if not self.context_id:
            self.context_id = _uuid_id("actx")
        if not self.started_at:
            self.started_at = _now_iso()
        if not self.context_hash:
            content = f"{self.application_id}:{self.domain_context}:{self.session_id}"
            self.context_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "application_id": self.application_id,
            "domain_context": self.domain_context,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "context_hash": self.context_hash,
        }


@dataclass
class ApplicationBoundaryState:
    boundary_id: str = ""
    application_id: str = ""
    allowed_capabilities: list[str] = field(default_factory=list)
    denied_capabilities: list[str] = field(default_factory=list)
    trust_tier: str = "restricted"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _uuid_id("abnd")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "application_id": self.application_id,
            "allowed_capabilities": self.allowed_capabilities,
            "denied_capabilities": self.denied_capabilities,
            "trust_tier": self.trust_tier,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationExecutionSurface:
    surface_id: str = ""
    application_id: str = ""
    spine_binding: str = ""
    governed: bool = True
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.surface_id:
            self.surface_id = _uuid_id("aexec")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "application_id": self.application_id,
            "spine_binding": self.spine_binding,
            "governed": self.governed,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationWorkflowSurface:
    surface_id: str = ""
    application_id: str = ""
    workflow_bindings: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.surface_id:
            self.surface_id = _uuid_id("awfs")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "application_id": self.application_id,
            "workflow_bindings": self.workflow_bindings,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationContinuityState:
    continuity_id: str = ""
    application_id: str = ""
    session_chain: list[str] = field(default_factory=list)
    last_checkpoint: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.continuity_id:
            self.continuity_id = _uuid_id("acont")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_id": self.continuity_id,
            "application_id": self.application_id,
            "session_chain": self.session_chain,
            "last_checkpoint": self.last_checkpoint,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationProjectionReceipt:
    receipt_id: str = ""
    application_id: str = ""
    projection_id: str = ""
    action: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _uuid_id("arcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "application_id": self.application_id,
            "projection_id": self.projection_id,
            "action": self.action,
            "timestamp": self.timestamp,
        }


@dataclass
class ApplicationCapabilityBinding:
    binding_id: str = ""
    application_id: str = ""
    capability_category: str = ""
    bound_at: str = ""
    binding_hash: str = ""

    def __post_init__(self) -> None:
        if not self.binding_id:
            self.binding_id = _uuid_id("abind")
        if not self.bound_at:
            self.bound_at = _now_iso()
        if not self.binding_hash:
            content = f"{self.application_id}:{self.capability_category}"
            self.binding_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "application_id": self.application_id,
            "capability_category": self.capability_category,
            "bound_at": self.bound_at,
            "binding_hash": self.binding_hash,
        }


@dataclass
class DomainProjectionState:
    domain_id: str = ""
    domain_context: str = ""
    active_applications: list[str] = field(default_factory=list)
    isolation_verified: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.domain_id:
            self.domain_id = _uuid_id("dproj")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "domain_context": self.domain_context,
            "active_applications": self.active_applications,
            "isolation_verified": self.isolation_verified,
            "created_at": self.created_at,
        }


@dataclass
class ProjectionReplayState:
    check_name: str = ""
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    checked_at: str = ""

    def __post_init__(self) -> None:
        if not self.checked_at:
            self.checked_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "checked_at": self.checked_at,
        }


@dataclass
class ProjectionGovernanceState:
    governance_id: str = ""
    application_id: str = ""
    action: str = ""
    permitted: bool = False
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.governance_id:
            self.governance_id = _uuid_id("agov")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "application_id": self.application_id,
            "action": self.action,
            "permitted": self.permitted,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class ApplicationLifecycleStateContract:
    application_id: str = ""
    current_state: str = "registered"
    transitions: list[dict[str, str]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "current_state": self.current_state,
            "transitions": self.transitions,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationTopologyState:
    topology_id: str = ""
    applications: list[str] = field(default_factory=list)
    shared_bindings: list[str] = field(default_factory=list)
    isolation_boundaries: list[str] = field(default_factory=list)
    topology_hash: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.topology_id:
            self.topology_id = _uuid_id("atopo")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.topology_hash:
            content = f"{','.join(sorted(self.applications))}:{','.join(sorted(self.shared_bindings))}"
            self.topology_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "applications": self.applications,
            "shared_bindings": self.shared_bindings,
            "isolation_boundaries": self.isolation_boundaries,
            "topology_hash": self.topology_hash,
            "created_at": self.created_at,
        }


@dataclass
class ApplicationObservabilityState:
    observability_id: str = ""
    application_id: str = ""
    total_events: int = 0
    last_event_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _uuid_id("aobs")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "application_id": self.application_id,
            "total_events": self.total_events,
            "last_event_at": self.last_event_at,
            "created_at": self.created_at,
        }
