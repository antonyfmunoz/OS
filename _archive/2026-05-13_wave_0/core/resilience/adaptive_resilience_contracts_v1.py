"""Adaptive Resilience Contracts v1.

Data contracts for resilience coordination:
  fault containment, instability detection, cascading failure
  interruption, checkpoint integrity, degraded survivability,
  recovery recommendation, isolation decisions.

All recovery actions are RECOMMENDATIONS — the coordinator
CANNOT execute repairs, rollbacks, or mutations autonomously.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ResilienceLifecycleState(enum.Enum):
    STABLE = "stable"
    MONITORED = "monitored"
    UNSTABLE = "unstable"
    DEGRADED = "degraded"
    ISOLATED = "isolated"
    RECOVERING = "recovering"
    VALIDATED = "validated"
    STABILIZED = "stabilized"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ResilienceEventType(enum.Enum):
    INSTABILITY_DETECTED = "instability_detected"
    FAULT_CONTAINED = "fault_contained"
    CASCADE_INTERRUPTED = "cascade_interrupted"
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_VALIDATED = "checkpoint_validated"
    ISOLATION_APPLIED = "isolation_applied"
    RECOVERY_RECOMMENDED = "recovery_recommended"
    RECOVERY_VALIDATED = "recovery_validated"
    SURVIVABILITY_ASSESSED = "survivability_assessed"
    RESILIENCE_RESTORED = "resilience_restored"


class InstabilityClass(enum.Enum):
    TRANSIENT = "transient"
    INTERMITTENT = "intermittent"
    PERSISTENT = "persistent"
    CASCADING = "cascading"
    SYSTEMIC = "systemic"


class IsolationScope(enum.Enum):
    SUBSYSTEM = "subsystem"
    ENVIRONMENT = "environment"
    WORKFLOW = "workflow"
    SESSION = "session"
    CAMPAIGN = "campaign"


class RecoveryAction(enum.Enum):
    RESTART_SUBSYSTEM = "restart_subsystem"
    RESTORE_CHECKPOINT = "restore_checkpoint"
    REDUCE_CONCURRENCY = "reduce_concurrency"
    ISOLATE_ENVIRONMENT = "isolate_environment"
    ESCALATE_TO_OPERATOR = "escalate_to_operator"


@dataclass
class ResilienceState:
    state_id: str = field(default_factory=lambda: _new_id("rstate"))
    lifecycle: str = "stable"
    instability_score: float = 0.0
    fault_count: int = 0
    isolation_count: int = 0
    recovery_count: int = 0
    last_assessment: str = field(default_factory=_now_iso)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "lifecycle": self.lifecycle,
            "instability_score": self.instability_score,
            "fault_count": self.fault_count,
            "isolation_count": self.isolation_count,
            "recovery_count": self.recovery_count,
            "last_assessment": self.last_assessment,
            "timestamp": self.timestamp,
        }


@dataclass
class FaultContainmentState:
    containment_id: str = field(default_factory=lambda: _new_id("fcon"))
    fault_source: str = ""
    affected_subsystems: list[str] = field(default_factory=list)
    contained: bool = False
    containment_boundary: str = ""
    propagation_blocked: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "containment_id": self.containment_id,
            "fault_source": self.fault_source,
            "affected_subsystems": self.affected_subsystems,
            "contained": self.contained,
            "containment_boundary": self.containment_boundary,
            "propagation_blocked": self.propagation_blocked,
            "timestamp": self.timestamp,
        }


@dataclass
class InstabilitySignal:
    signal_id: str = field(default_factory=lambda: _new_id("isig"))
    source: str = ""
    instability_class: str = "transient"
    severity: float = 0.0
    consecutive_failures: int = 0
    pattern: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "instability_class": self.instability_class,
            "severity": self.severity,
            "consecutive_failures": self.consecutive_failures,
            "pattern": self.pattern,
            "timestamp": self.timestamp,
        }


@dataclass
class CascadingFailureState:
    cascade_id: str = field(default_factory=lambda: _new_id("casc"))
    origin_subsystem: str = ""
    affected_subsystems: list[str] = field(default_factory=list)
    propagation_depth: int = 0
    interrupted: bool = False
    interruption_point: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cascade_id": self.cascade_id,
            "origin_subsystem": self.origin_subsystem,
            "affected_subsystems": self.affected_subsystems,
            "propagation_depth": self.propagation_depth,
            "interrupted": self.interrupted,
            "interruption_point": self.interruption_point,
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryCoordinationReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("rrcpt"))
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    instability_score: float = 0.0
    recommendation: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "instability_score": self.instability_score,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class SubsystemHealthState:
    health_id: str = field(default_factory=lambda: _new_id("sheal"))
    subsystem_id: str = ""
    healthy: bool = True
    consecutive_failures: int = 0
    last_success: str = field(default_factory=_now_iso)
    last_failure: str = ""
    degraded: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_id": self.health_id,
            "subsystem_id": self.subsystem_id,
            "healthy": self.healthy,
            "consecutive_failures": self.consecutive_failures,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "degraded": self.degraded,
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryBoundaryState:
    boundary_id: str = field(default_factory=lambda: _new_id("rbnd"))
    max_recovery_attempts: int = 3
    current_attempts: int = 0
    max_isolation_depth: int = 3
    current_isolation_depth: int = 0
    within_bounds: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "max_recovery_attempts": self.max_recovery_attempts,
            "current_attempts": self.current_attempts,
            "max_isolation_depth": self.max_isolation_depth,
            "current_isolation_depth": self.current_isolation_depth,
            "within_bounds": self.within_bounds,
            "timestamp": self.timestamp,
        }


@dataclass
class ContinuityPreservationState:
    preservation_id: str = field(default_factory=lambda: _new_id("cpres"))
    preserved_subsystems: list[str] = field(default_factory=list)
    checkpoint_count: int = 0
    last_checkpoint: str = ""
    continuity_intact: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preservation_id": self.preservation_id,
            "preserved_subsystems": self.preserved_subsystems,
            "checkpoint_count": self.checkpoint_count,
            "last_checkpoint": self.last_checkpoint,
            "continuity_intact": self.continuity_intact,
            "timestamp": self.timestamp,
        }


@dataclass
class CheckpointIntegrityState:
    integrity_id: str = field(default_factory=lambda: _new_id("cint"))
    checkpoint_id: str = ""
    subsystem_id: str = ""
    state_hash: str = ""
    valid: bool = True
    validated_at: str = field(default_factory=_now_iso)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity_id": self.integrity_id,
            "checkpoint_id": self.checkpoint_id,
            "subsystem_id": self.subsystem_id,
            "state_hash": self.state_hash,
            "valid": self.valid,
            "validated_at": self.validated_at,
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryReplayState:
    replay_id: str = field(default_factory=lambda: _new_id("rrply"))
    check_name: str = ""
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "check_name": self.check_name,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "timestamp": self.timestamp,
        }


@dataclass
class SurvivabilityScore:
    score_id: str = field(default_factory=lambda: _new_id("sscore"))
    overall_score: float = 1.0
    subsystem_scores: dict[str, float] = field(default_factory=dict)
    fault_tolerance: float = 1.0
    recovery_capacity: float = 1.0
    isolation_effectiveness: float = 1.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "overall_score": self.overall_score,
            "subsystem_scores": self.subsystem_scores,
            "fault_tolerance": self.fault_tolerance,
            "recovery_capacity": self.recovery_capacity,
            "isolation_effectiveness": self.isolation_effectiveness,
            "timestamp": self.timestamp,
        }


@dataclass
class IsolationDecision:
    decision_id: str = field(default_factory=lambda: _new_id("isodec"))
    target: str = ""
    scope: str = "subsystem"
    reason: str = ""
    isolated: bool = False
    isolation_boundary: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "target": self.target,
            "scope": self.scope,
            "reason": self.reason,
            "isolated": self.isolated,
            "isolation_boundary": self.isolation_boundary,
            "timestamp": self.timestamp,
        }


@dataclass
class RecoveryRecommendation:
    recommendation_id: str = field(default_factory=lambda: _new_id("rrec"))
    target_subsystem: str = ""
    action: str = "escalate_to_operator"
    priority: str = "standard"
    rationale: str = ""
    approved: bool = False
    approved_by: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "target_subsystem": self.target_subsystem,
            "action": self.action,
            "priority": self.priority,
            "rationale": self.rationale,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


@dataclass
class DegradedSurvivabilityState:
    survivability_id: str = field(default_factory=lambda: _new_id("dsurv"))
    degraded_subsystems: list[str] = field(default_factory=list)
    functional_subsystems: list[str] = field(default_factory=list)
    survivability_score: float = 1.0
    can_continue: bool = True
    minimum_viable: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "survivability_id": self.survivability_id,
            "degraded_subsystems": self.degraded_subsystems,
            "functional_subsystems": self.functional_subsystems,
            "survivability_score": self.survivability_score,
            "can_continue": self.can_continue,
            "minimum_viable": self.minimum_viable,
            "timestamp": self.timestamp,
        }
