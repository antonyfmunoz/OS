"""Operational Scaling Contracts v1.

Contracts for operational substrate scaling coordination:
  ResourceBudget, ExecutionPressureState, QueuePressureState,
  OperationalHealthState, ScalingCoordinationReceipt,
  ConcurrencyWindow, ExecutionThrottleState,
  OperationalPriorityState, AdaptiveRegulationState,
  DegradedModeState, ScalingReplayState,
  CapacityAllocationDecision

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_hash(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Enums ──────────────────────────────────────────────


class ScalingLifecycleState(enum.Enum):
    STABLE = "stable"
    ELEVATED = "elevated"
    PRESSURED = "pressured"
    THROTTLED = "throttled"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    STABILIZED = "stabilized"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ScalingEventType(enum.Enum):
    PRESSURE_INCREASE = "pressure_increase"
    PRESSURE_RELIEF = "pressure_relief"
    QUEUE_THROTTLE = "queue_throttle"
    EXECUTION_DELAYED = "execution_delayed"
    DEGRADED_MODE_ENTERED = "degraded_mode_entered"
    DEGRADED_MODE_RECOVERED = "degraded_mode_recovered"
    CONCURRENCY_LIMITED = "concurrency_limited"
    RESOURCE_BUDGET_EXCEEDED = "resource_budget_exceeded"
    PRIORITY_ARBITRATED = "priority_arbitrated"
    SCALING_BOUNDARY_DENIED = "scaling_boundary_denied"


class PriorityClass(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"
    DEFERRED = "deferred"
    SUSPENDED = "suspended"


class DegradedReason(enum.Enum):
    ENVIRONMENT_FAILURE = "environment_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONCURRENCY_OVERLOAD = "concurrency_overload"
    QUEUE_SATURATION = "queue_saturation"
    OPERATOR_INITIATED = "operator_initiated"


# ── Contracts ──────────────────────────────────────────


@dataclass
class ResourceBudget:
    budget_id: str = field(default_factory=lambda: _new_id("rbud"))
    max_traversals_per_hour: int = 100
    max_concurrent: int = 5
    max_queue_depth: int = 50
    max_deferred: int = 20
    max_continuation_depth: int = 5
    allocated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "max_traversals_per_hour": self.max_traversals_per_hour,
            "max_concurrent": self.max_concurrent,
            "max_queue_depth": self.max_queue_depth,
            "max_deferred": self.max_deferred,
            "max_continuation_depth": self.max_continuation_depth,
            "allocated_at": self.allocated_at,
        }


@dataclass
class ExecutionPressureState:
    active_traversals: int = 0
    queue_depth: int = 0
    avg_latency_ms: float = 0.0
    concurrency_load: float = 0.0
    continuation_pressure: int = 0
    environment_saturation: float = 0.0
    deferred_accumulation: int = 0
    pressure_score: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_traversals": self.active_traversals,
            "queue_depth": self.queue_depth,
            "avg_latency_ms": self.avg_latency_ms,
            "concurrency_load": self.concurrency_load,
            "continuation_pressure": self.continuation_pressure,
            "environment_saturation": self.environment_saturation,
            "deferred_accumulation": self.deferred_accumulation,
            "pressure_score": self.pressure_score,
            "timestamp": self.timestamp,
        }


@dataclass
class QueuePressureState:
    queue_id: str = field(default_factory=lambda: _new_id("qp"))
    depth: int = 0
    max_depth: int = 50
    oldest_age_seconds: float = 0.0
    throttled: bool = False
    delay_ms: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "oldest_age_seconds": self.oldest_age_seconds,
            "throttled": self.throttled,
            "delay_ms": self.delay_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalHealthState:
    health_id: str = field(default_factory=lambda: _new_id("ohealth"))
    overall_healthy: bool = True
    pressure_score: float = 0.0
    degraded_environments: int = 0
    active_throttles: int = 0
    lifecycle_state: str = ScalingLifecycleState.STABLE.value
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_id": self.health_id,
            "overall_healthy": self.overall_healthy,
            "pressure_score": self.pressure_score,
            "degraded_environments": self.degraded_environments,
            "active_throttles": self.active_throttles,
            "lifecycle_state": self.lifecycle_state,
            "timestamp": self.timestamp,
        }


@dataclass
class ScalingCoordinationReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("srcpt"))
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    pressure_score: float = 0.0
    decision: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "pressure_score": self.pressure_score,
            "decision": self.decision,
            "timestamp": self.timestamp,
        }


@dataclass
class ConcurrencyWindow:
    window_id: str = field(default_factory=lambda: _new_id("cwin"))
    max_concurrent: int = 5
    current_active: int = 0
    environment_limits: dict[str, int] = field(default_factory=dict)
    workflow_limits: dict[str, int] = field(default_factory=dict)
    session_limits: dict[str, int] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "max_concurrent": self.max_concurrent,
            "current_active": self.current_active,
            "environment_limits": self.environment_limits,
            "workflow_limits": self.workflow_limits,
            "session_limits": self.session_limits,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionThrottleState:
    throttle_id: str = field(default_factory=lambda: _new_id("ethrt"))
    active: bool = False
    delay_ms: int = 0
    reason: str = ""
    affected_priorities: list[str] = field(default_factory=list)
    started_at: str = ""
    released_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "throttle_id": self.throttle_id,
            "active": self.active,
            "delay_ms": self.delay_ms,
            "reason": self.reason,
            "affected_priorities": self.affected_priorities,
            "started_at": self.started_at,
            "released_at": self.released_at,
        }


@dataclass
class OperationalPriorityState:
    priority_id: str = field(default_factory=lambda: _new_id("opri"))
    item_id: str = ""
    priority_class: str = PriorityClass.STANDARD.value
    set_by: str = "operator"
    override_allowed: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_id": self.priority_id,
            "item_id": self.item_id,
            "priority_class": self.priority_class,
            "set_by": self.set_by,
            "override_allowed": self.override_allowed,
            "timestamp": self.timestamp,
        }


@dataclass
class AdaptiveRegulationState:
    regulation_id: str = field(default_factory=lambda: _new_id("areg"))
    throttle_active: bool = False
    concurrency_reduced: bool = False
    queue_delayed: bool = False
    degraded_environments: list[str] = field(default_factory=list)
    pressure_score: float = 0.0
    regulation_reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "regulation_id": self.regulation_id,
            "throttle_active": self.throttle_active,
            "concurrency_reduced": self.concurrency_reduced,
            "queue_delayed": self.queue_delayed,
            "degraded_environments": self.degraded_environments,
            "pressure_score": self.pressure_score,
            "regulation_reason": self.regulation_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class DegradedModeState:
    mode_id: str = field(default_factory=lambda: _new_id("dmode"))
    active: bool = False
    reason: str = DegradedReason.ENVIRONMENT_FAILURE.value
    affected_environments: list[str] = field(default_factory=list)
    reduced_concurrency: int = 0
    entered_at: str = ""
    recovered_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "active": self.active,
            "reason": self.reason,
            "affected_environments": self.affected_environments,
            "reduced_concurrency": self.reduced_concurrency,
            "entered_at": self.entered_at,
            "recovered_at": self.recovered_at,
        }


@dataclass
class ScalingReplayState:
    replay_id: str = field(default_factory=lambda: _new_id("srply"))
    pressure_hash: str = ""
    throttle_hash: str = ""
    concurrency_hash: str = ""
    degraded_hash: str = ""
    priority_hash: str = ""
    all_deterministic: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "pressure_hash": self.pressure_hash,
            "throttle_hash": self.throttle_hash,
            "concurrency_hash": self.concurrency_hash,
            "degraded_hash": self.degraded_hash,
            "priority_hash": self.priority_hash,
            "all_deterministic": self.all_deterministic,
            "timestamp": self.timestamp,
        }


@dataclass
class CapacityAllocationDecision:
    decision_id: str = field(default_factory=lambda: _new_id("cadec"))
    item_id: str = ""
    allocated: bool = False
    reason: str = ""
    concurrency_at_decision: int = 0
    queue_depth_at_decision: int = 0
    pressure_at_decision: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "item_id": self.item_id,
            "allocated": self.allocated,
            "reason": self.reason,
            "concurrency_at_decision": self.concurrency_at_decision,
            "queue_depth_at_decision": self.queue_depth_at_decision,
            "pressure_at_decision": self.pressure_at_decision,
            "timestamp": self.timestamp,
        }
