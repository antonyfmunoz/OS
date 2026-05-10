"""
Execution contract types for the event-native execution fabric.

Platform-agnostic, frozen, JSON-serializable data contracts that define
the boundary between the control plane (decides what runs) and the
execution plane (runs it).

These types are the foundation every other fabric module depends on:
routing, scheduling, checkpoint, and replay all speak this vocabulary.

Usage:
    from eos_ai.transport.execution_contract import (
        ExecutionRequest, ExecutionResult, ExecutionClass,
        ExecutionStatus, ExecutionConstraints, RoutingDecision,
    )
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExecutionClass(str, Enum):
    """Classifies what kind of effect an execution has."""

    PURE = "pure"
    SIDE_EFFECT = "side_effect"
    TRANSPORT = "transport"


class ExecutionStatus(str, Enum):
    """Terminal status of a completed execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"


class RoutingReasonCode(str, Enum):
    """Why the router chose a particular target node."""

    CAPABILITY_MATCH = "capability_match"
    EXECUTION_CLASS_POLICY = "execution_class_policy"
    HEALTH_PREFERENCE = "health_preference"
    EXPLICIT_OVERRIDE = "explicit_override"
    FALLBACK_PRIMARY_UNAVAILABLE = "fallback_primary_unavailable"
    ONLY_CAPABLE_NODE = "only_capable_node"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionConstraints:
    """Limits placed on a single execution attempt."""

    timeout_s: int = 30
    max_retries: int = 0
    sandbox: bool = False


@dataclass(frozen=True)
class NodeCapability:
    """A single named capability that a node advertises."""

    slug: str
    description: str = ""
    execution_classes: frozenset[ExecutionClass] = frozenset({ExecutionClass.PURE})


@dataclass(frozen=True)
class NodeHealthSnapshot:
    """Point-in-time health reading from a node."""

    node_id: str
    status: str
    capabilities: tuple[str, ...] = ()
    last_heartbeat_age_s: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionTarget:
    """Where an execution should run, plus optional fallback."""

    node_id: str
    transport: str
    fallback_node_id: Optional[str] = None
    fallback_transport: Optional[str] = None


@dataclass(frozen=True)
class RoutingContext:
    """Input parameters the router uses to make a decision."""

    execution_class: ExecutionClass
    required_capabilities: frozenset[str] = frozenset()
    priority: int = 5
    latency_sensitivity: str = "normal"
    cost_sensitivity: str = "normal"
    force_node_id: Optional[str] = None
    allow_fallback: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    """The router's output: a target plus rationale."""

    target: ExecutionTarget
    reason_code: RoutingReasonCode
    reason_detail: str = ""
    routing_context: Optional[RoutingContext] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_execution_id() -> str:
    """Generate a unique execution identifier."""
    return f"exec_{uuid.uuid4().hex[:16]}"


def _compute_idempotency_key(primitive_name: str, inputs: dict) -> str:
    """Deterministic key from primitive name + inputs (first 16 hex of SHA-256)."""
    payload = json.dumps(
        {"primitive": primitive_name, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _compute_execution_hash(execution_id: str, status: str, outputs: dict) -> str:
    """Deterministic hash of execution outcome (first 16 hex of SHA-256)."""
    payload = json.dumps(
        {"execution_id": execution_id, "status": status, "outputs": outputs},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Execution envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionRequest:
    """Immutable envelope that fully describes a unit of work to execute."""

    execution_id: str
    correlation_id: str
    causal_event_id: str
    session_name: str
    run_id: str
    primitive_name: str
    inputs: dict
    execution_class: ExecutionClass
    constraints: ExecutionConstraints
    target: ExecutionTarget
    issued_at: str
    issued_by: str
    idempotency_key: str
    retry_count: int = 0

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON transport."""
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "causal_event_id": self.causal_event_id,
            "session_name": self.session_name,
            "run_id": self.run_id,
            "primitive_name": self.primitive_name,
            "inputs": self.inputs,
            "execution_class": self.execution_class.value,
            "constraints": {
                "timeout_s": self.constraints.timeout_s,
                "max_retries": self.constraints.max_retries,
                "sandbox": self.constraints.sandbox,
            },
            "target": {
                "node_id": self.target.node_id,
                "transport": self.target.transport,
                "fallback_node_id": self.target.fallback_node_id,
                "fallback_transport": self.target.fallback_transport,
            },
            "issued_at": self.issued_at,
            "issued_by": self.issued_by,
            "idempotency_key": self.idempotency_key,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionRequest:
        """Reconstruct from a plain dict."""
        constraints_raw = data["constraints"]
        target_raw = data["target"]
        return cls(
            execution_id=data["execution_id"],
            correlation_id=data["correlation_id"],
            causal_event_id=data["causal_event_id"],
            session_name=data["session_name"],
            run_id=data["run_id"],
            primitive_name=data["primitive_name"],
            inputs=data["inputs"],
            execution_class=ExecutionClass(data["execution_class"]),
            constraints=ExecutionConstraints(
                timeout_s=constraints_raw["timeout_s"],
                max_retries=constraints_raw["max_retries"],
                sandbox=constraints_raw["sandbox"],
            ),
            target=ExecutionTarget(
                node_id=target_raw["node_id"],
                transport=target_raw["transport"],
                fallback_node_id=target_raw.get("fallback_node_id"),
                fallback_transport=target_raw.get("fallback_transport"),
            ),
            issued_at=data["issued_at"],
            issued_by=data["issued_by"],
            idempotency_key=data["idempotency_key"],
            retry_count=data.get("retry_count", 0),
        )


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable envelope describing the outcome of an execution."""

    execution_id: str
    correlation_id: str
    causal_event_id: str
    primitive_name: str
    status: ExecutionStatus
    outputs: dict
    side_effects: tuple[str, ...] = ()
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    node_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    execution_hash: Optional[str] = None
    retry_count: int = 0

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON transport."""
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "causal_event_id": self.causal_event_id,
            "primitive_name": self.primitive_name,
            "status": self.status.value,
            "outputs": self.outputs,
            "side_effects": list(self.side_effects),
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "node_id": self.node_id,
            "idempotency_key": self.idempotency_key,
            "execution_hash": self.execution_hash,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionResult:
        """Reconstruct from a plain dict."""
        return cls(
            execution_id=data["execution_id"],
            correlation_id=data["correlation_id"],
            causal_event_id=data["causal_event_id"],
            primitive_name=data["primitive_name"],
            status=ExecutionStatus(data["status"]),
            outputs=data["outputs"],
            side_effects=tuple(data.get("side_effects", ())),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            node_id=data.get("node_id"),
            idempotency_key=data.get("idempotency_key"),
            execution_hash=data.get("execution_hash"),
            retry_count=data.get("retry_count", 0),
        )
