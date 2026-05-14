"""Live Operational Deployment Contracts v1.

15 contracts, 5 enums for live operational deployment orchestration.

Orchestration is supervised routing and coordination —
never autonomous infrastructure authority.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"{prefix}{h}"


class OrchestrationLifecyclePhase(str, Enum):
    PLANNED = "planned"
    VALIDATED = "validated"
    STAGED = "staged"
    APPROVED = "approved"
    COORDINATED = "coordinated"
    OBSERVED = "observed"
    CHECKPOINTED = "checkpointed"
    RESTORED = "restored"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


class OrchestrationEventType(str, Enum):
    DEPLOYMENT_OPERATION_STARTED = "deployment_operation_started"
    DEPLOYMENT_OPERATION_COMPLETED = "deployment_operation_completed"
    DEPLOYMENT_CHECKPOINT_CREATED = "deployment_checkpoint_created"
    DEPLOYMENT_RESTORE_STARTED = "deployment_restore_started"
    DEPLOYMENT_RESTORE_COMPLETED = "deployment_restore_completed"
    DEPLOYMENT_RECOVERY_RECOMMENDED = "deployment_recovery_recommended"
    DEPLOYMENT_BOUNDARY_DENIED = "deployment_boundary_denied"
    DEPLOYMENT_REPLAY_VALIDATED = "deployment_replay_validated"


class OrchestrationTrustTier(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    SANDBOX = "sandbox"


class RecoveryAction(str, Enum):
    RECOMMEND_ROLLBACK = "recommend_rollback"
    RECOMMEND_RESTORE = "recommend_restore"
    RECOMMEND_ISOLATION = "recommend_isolation"
    RECOMMEND_DEGRADED = "recommend_degraded"
    RECOMMEND_ESCALATION = "recommend_escalation"


class SynchronizationTarget(str, Enum):
    APPLICATION_RUNTIME = "application_runtime"
    ENVIRONMENT_RUNTIME = "environment_runtime"
    DEPLOYMENT_CONTINUITY = "deployment_continuity"
    WORKFLOW_RUNTIME = "workflow_runtime"
    OBSERVABILITY_RUNTIME = "observability_runtime"


@dataclass
class LiveDeploymentOperation:
    application_id: str
    environment_id: str
    deployment_id: str = ""
    trust_tier: str = "development"
    approved_by: str = "operator"
    operation_id: str = field(default="")
    status: str = "planned"
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.operation_id:
            self.operation_id = _deterministic_id(
                "ldop-", self.application_id, self.environment_id,
                self.deployment_id, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "application_id": self.application_id,
            "environment_id": self.environment_id,
            "deployment_id": self.deployment_id,
            "trust_tier": self.trust_tier,
            "approved_by": self.approved_by,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeDeploymentState:
    operation_id: str
    phase: str = "planned"
    healthy: bool = True
    last_updated: str = field(default_factory=_now_iso)
    state_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _deterministic_id(
                "rdst-", self.operation_id, self.phase, self.last_updated,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "operation_id": self.operation_id,
            "phase": self.phase,
            "healthy": self.healthy,
            "last_updated": self.last_updated,
        }


@dataclass
class DeploymentExecutionGraph:
    graph_id: str = field(default="")
    nodes: list[str] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.graph_id:
            self.graph_id = _deterministic_id(
                "dgraph-", ",".join(sorted(self.nodes)), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": list(self.nodes),
            "edges": [list(e) for e in self.edges],
            "created_at": self.created_at,
        }


@dataclass
class OperationalDeploymentReceipt:
    operation_id: str
    outcome: str = "completed"
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "drcpt-", self.operation_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "operation_id": self.operation_id,
            "outcome": self.outcome,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentCheckpointState:
    operation_id: str
    content_hash: str = ""
    checkpoint_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = _deterministic_id(
                "dckpt-", self.operation_id, self.content_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "operation_id": self.operation_id,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentRoutingState:
    operation_id: str
    source_environment: str = ""
    target_environment: str = ""
    route_hash: str = ""
    routing_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.routing_id:
            self.routing_id = _deterministic_id(
                "droute-", self.operation_id, self.source_environment,
                self.target_environment, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_id": self.routing_id,
            "operation_id": self.operation_id,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "route_hash": self.route_hash,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "dreplay-", self.check_name, self.input_hash,
                self.output_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "check_name": self.check_name,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentGovernanceState:
    operation_id: str
    approved: bool = False
    approved_by: str = ""
    governance_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.governance_id:
            self.governance_id = _deterministic_id(
                "dgov-", self.operation_id, str(self.approved), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "operation_id": self.operation_id,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentObservabilityState:
    operation_id: str
    event_type: str = ""
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "dobs-", self.operation_id, self.event_type, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "operation_id": self.operation_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentRecoveryState:
    operation_id: str
    action: str = "recommend_escalation"
    reason: str = ""
    approved_by: str = ""
    recovery_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.recovery_id:
            self.recovery_id = _deterministic_id(
                "drecov-", self.operation_id, self.action, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "operation_id": self.operation_id,
            "action": self.action,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentBoundaryState:
    limit_name: str
    current_value: int = 0
    max_value: int = 0
    exceeded: bool = False
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "dbnd-", self.limit_name, str(self.current_value),
                str(self.max_value), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "limit_name": self.limit_name,
            "current_value": self.current_value,
            "max_value": self.max_value,
            "exceeded": self.exceeded,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentContinuationState:
    operation_id: str
    continuation_type: str = "checkpoint"
    content_hash: str = ""
    continuation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.continuation_id:
            self.continuation_id = _deterministic_id(
                "dcont-", self.operation_id, self.continuation_type,
                self.content_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuation_id": self.continuation_id,
            "operation_id": self.operation_id,
            "continuation_type": self.continuation_type,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentSynchronizationState:
    target: str
    epoch: int = 0
    synchronized: bool = False
    sync_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.sync_id:
            self.sync_id = _deterministic_id(
                "dsync-", self.target, str(self.epoch), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "target": self.target,
            "epoch": self.epoch,
            "synchronized": self.synchronized,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentTrustState:
    operation_id: str
    trust_tier: str = "development"
    validated: bool = False
    trust_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.trust_id:
            self.trust_id = _deterministic_id(
                "dtrust-", self.operation_id, self.trust_tier, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_id": self.trust_id,
            "operation_id": self.operation_id,
            "trust_tier": self.trust_tier,
            "validated": self.validated,
            "created_at": self.created_at,
        }


@dataclass
class DeploymentOperatorIntentState:
    intent: str
    set_by: str = "operator"
    operation_id: str = ""
    intent_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.intent_id:
            self.intent_id = _deterministic_id(
                "dintent-", self.intent, self.set_by,
                self.operation_id, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent": self.intent,
            "set_by": self.set_by,
            "operation_id": self.operation_id,
            "created_at": self.created_at,
        }
