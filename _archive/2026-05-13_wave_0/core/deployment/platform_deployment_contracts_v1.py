"""Platform Deployment Contracts v1.

15 contracts, 5 enums for governed platform deployment readiness.

Deployment is operational infrastructure coordination —
not execution authority transfer.

UMH substrate subsystem. Phase 96.8CE.
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


def _uuid_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Enums ──────────────────────────────────────────────


class DeploymentLifecyclePhase(enum.Enum):
    DEFINED = "defined"
    VALIDATED = "validated"
    STAGED = "staged"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    OBSERVED = "observed"
    RESTORED = "restored"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


class DeploymentEventType(enum.Enum):
    DEPLOYMENT_CREATED = "deployment_created"
    DEPLOYMENT_VALIDATED = "deployment_validated"
    DEPLOYMENT_DENIED = "deployment_denied"
    ROLLOUT_STARTED = "rollout_started"
    ROLLOUT_COMPLETED = "rollout_completed"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    TOPOLOGY_VALIDATED = "topology_validated"
    DEPLOYMENT_REPLAY_VALIDATED = "deployment_replay_validated"


class DeploymentTrustTier(enum.Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    SANDBOX = "sandbox"


class DeploymentEnvironmentType(enum.Enum):
    LOCAL_WORKSTATION = "local_workstation"
    VPS = "vps"
    SANDBOX = "sandbox"
    BROWSER_PROJECTION = "browser_projection"
    TMUX_RUNTIME = "tmux_runtime"
    CLOUD = "cloud"


class RolloutStrategy(enum.Enum):
    SEQUENTIAL = "sequential"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    ALL_AT_ONCE = "all_at_once"


# ── Contracts ──────────────────────────────────────────


@dataclass
class DeploymentProjection:
    deployment_id: str = ""
    application_id: str = ""
    manifest_id: str = ""
    environment_id: str = ""
    trust_tier: str = "development"
    created_at: str = ""
    deployment_hash: str = ""

    def __post_init__(self) -> None:
        if not self.deployment_id:
            self.deployment_id = _uuid_id("dply")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.deployment_hash:
            content = f"{self.application_id}:{self.manifest_id}:{self.environment_id}"
            self.deployment_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "application_id": self.application_id,
            "manifest_id": self.manifest_id,
            "environment_id": self.environment_id,
            "trust_tier": self.trust_tier,
            "created_at": self.created_at,
            "deployment_hash": self.deployment_hash,
        }


@dataclass
class DeploymentEnvironment:
    environment_id: str = ""
    environment_type: str = "local_workstation"
    trust_tier: str = "development"
    capabilities: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.environment_id:
            self.environment_id = _uuid_id("denv")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "environment_type": self.environment_type,
            "trust_tier": self.trust_tier,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentTopology:
    topology_id: str = ""
    environments: list[str] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)
    topology_hash: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.topology_id:
            self.topology_id = _uuid_id("dtopo")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.topology_hash:
            content = f"{','.join(sorted(self.environments))}"
            self.topology_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "environments": self.environments,
            "edges": self.edges,
            "topology_hash": self.topology_hash,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentManifest:
    manifest_id: str = ""
    application_id: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    environment_bindings: list[str] = field(default_factory=list)
    topology_bindings: list[str] = field(default_factory=list)
    manifest_hash: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.manifest_id:
            self.manifest_id = _uuid_id("dman")
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.manifest_hash:
            content = (
                f"{self.application_id}:"
                f"{','.join(sorted(self.required_capabilities))}:"
                f"{','.join(sorted(self.environment_bindings))}"
            )
            self.manifest_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "application_id": self.application_id,
            "required_capabilities": self.required_capabilities,
            "environment_bindings": self.environment_bindings,
            "topology_bindings": self.topology_bindings,
            "manifest_hash": self.manifest_hash,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentReceipt:
    receipt_id: str = ""
    deployment_id: str = ""
    action: str = ""
    status: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _uuid_id("drcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "deployment_id": self.deployment_id,
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp,
        }


@dataclass
class DeploymentLifecycleState:
    deployment_id: str = ""
    current_phase: str = "defined"
    transitions: list[dict[str, str]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "current_phase": self.current_phase,
            "transitions": self.transitions,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentReplayState:
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
class DeploymentGovernanceState:
    governance_id: str = ""
    deployment_id: str = ""
    action: str = ""
    permitted: bool = False
    reason: str = ""
    approved_by: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.governance_id:
            self.governance_id = _uuid_id("dgov")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "deployment_id": self.deployment_id,
            "action": self.action,
            "permitted": self.permitted,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


@dataclass
class DeploymentObservabilityState:
    observability_id: str = ""
    deployment_id: str = ""
    total_events: int = 0
    last_event_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _uuid_id("dobs")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "deployment_id": self.deployment_id,
            "total_events": self.total_events,
            "last_event_at": self.last_event_at,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentBoundaryState:
    boundary_id: str = ""
    deployment_id: str = ""
    allowed_actions: list[str] = field(default_factory=list)
    denied_actions: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _uuid_id("dbnd")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "deployment_id": self.deployment_id,
            "allowed_actions": self.allowed_actions,
            "denied_actions": self.denied_actions,
            "created_at": self.created_at,
        }


@dataclass
class RolloutState:
    rollout_id: str = ""
    deployment_id: str = ""
    strategy: str = "sequential"
    stages_total: int = 0
    stages_completed: int = 0
    status: str = "pending"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.rollout_id:
            self.rollout_id = _uuid_id("rout")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollout_id": self.rollout_id,
            "deployment_id": self.deployment_id,
            "strategy": self.strategy,
            "stages_total": self.stages_total,
            "stages_completed": self.stages_completed,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class RollbackState:
    rollback_id: str = ""
    deployment_id: str = ""
    target_deployment_id: str = ""
    reason: str = ""
    status: str = "pending"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.rollback_id:
            self.rollback_id = _uuid_id("rback")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "deployment_id": self.deployment_id,
            "target_deployment_id": self.target_deployment_id,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ProvisioningState:
    provisioning_id: str = ""
    environment_id: str = ""
    dependencies_met: bool = False
    capabilities_validated: bool = False
    topology_validated: bool = False
    ready: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.provisioning_id:
            self.provisioning_id = _uuid_id("dprov")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provisioning_id": self.provisioning_id,
            "environment_id": self.environment_id,
            "dependencies_met": self.dependencies_met,
            "capabilities_validated": self.capabilities_validated,
            "topology_validated": self.topology_validated,
            "ready": self.ready,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentTrustState:
    trust_id: str = ""
    deployment_id: str = ""
    trust_tier: str = "development"
    governance_approved: bool = False
    replay_validated: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.trust_id:
            self.trust_id = _uuid_id("dtrust")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_id": self.trust_id,
            "deployment_id": self.deployment_id,
            "trust_tier": self.trust_tier,
            "governance_approved": self.governance_approved,
            "replay_validated": self.replay_validated,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentContinuityState:
    continuity_id: str = ""
    deployment_id: str = ""
    checkpoint_hash: str = ""
    session_chain: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.continuity_id:
            self.continuity_id = _uuid_id("dcont")
        if not self.created_at:
            self.created_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_id": self.continuity_id,
            "deployment_id": self.deployment_id,
            "checkpoint_hash": self.checkpoint_hash,
            "session_chain": self.session_chain,
            "created_at": self.created_at,
        }
