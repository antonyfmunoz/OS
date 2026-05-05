"""
UMH Execution Contract — platform-agnostic execution types.

Defines the boundary between the control plane (decides what runs) and the
execution plane (runs it).  These types carry no platform dependency — they
work identically whether execution is dispatched by EOS substrate, a CLI
tool, or a future SaaS runtime.

Integration with UMH intelligence layers is achieved through typed fields
on ExecutionContext:
  - decision_trace_id  → links to umh.decision.trace.DecisionTrace
  - active_goal_id     → links to umh.goals.state.GoalState
  - strategy_name      → links to umh.strategy.memory.StrategyStats
  - memory_snapshot     → opaque dict from umh.memory.storage

No runtime imports of those modules.  The execution contract is pure data;
intelligence integration happens at the caller layer.
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
    LLM_CALL = "llm_call"


class ExecutionStatus(str, Enum):
    """Terminal status of a completed execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"


class ExecutionPriority(str, Enum):
    """Execution urgency classification."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionConstraints:
    """Limits placed on a single execution attempt."""

    timeout_s: int = 30
    max_retries: int = 0
    sandbox: bool = False
    max_tokens: int = 0
    cost_limit_usd: float = 0.0


@dataclass(frozen=True)
class ExecutionTarget:
    """Where an execution should run."""

    node_id: str
    transport: str
    fallback_node_id: Optional[str] = None
    fallback_transport: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_execution_id() -> str:
    return f"exec_{uuid.uuid4().hex[:16]}"


def _compute_idempotency_key(operation: str, inputs: dict) -> str:
    payload = json.dumps(
        {"operation": operation, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _compute_execution_hash(execution_id: str, status: str, outputs: dict) -> str:
    payload = json.dumps(
        {"execution_id": execution_id, "status": status, "outputs": outputs},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# ExecutionContext — intelligence integration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable intelligence snapshot for an execution.

    Carries references to the decision, goal, and strategy state that
    motivated this execution.  No runtime imports of UMH intelligence
    modules — just IDs and snapshots.
    """

    session_id: str = ""
    correlation_id: str = ""
    decision_trace_id: Optional[int] = None
    active_goal_id: Optional[str] = None
    goal_weight: float = 0.0
    strategy_name: Optional[str] = None
    strategy_confidence: float = 0.0
    memory_snapshot: dict[str, Any] = field(default_factory=dict)
    authority_class: str = "analyze"
    agent_type: str = ""
    venture_id: str = ""
    channel: str = ""
    user_id: str = ""
    org_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "decision_trace_id": self.decision_trace_id,
            "active_goal_id": self.active_goal_id,
            "goal_weight": self.goal_weight,
            "strategy_name": self.strategy_name,
            "strategy_confidence": self.strategy_confidence,
            "memory_snapshot": self.memory_snapshot,
            "authority_class": self.authority_class,
            "agent_type": self.agent_type,
            "venture_id": self.venture_id,
            "channel": self.channel,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionContext:
        return cls(
            session_id=data.get("session_id", ""),
            correlation_id=data.get("correlation_id", ""),
            decision_trace_id=data.get("decision_trace_id"),
            active_goal_id=data.get("active_goal_id"),
            goal_weight=data.get("goal_weight", 0.0),
            strategy_name=data.get("strategy_name"),
            strategy_confidence=data.get("strategy_confidence", 0.0),
            memory_snapshot=data.get("memory_snapshot", {}),
            authority_class=data.get("authority_class", "analyze"),
            agent_type=data.get("agent_type", ""),
            venture_id=data.get("venture_id", ""),
            channel=data.get("channel", ""),
            user_id=data.get("user_id", ""),
            org_id=data.get("org_id", ""),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# ExecutionRequest — what to execute
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionRequest:
    """Immutable envelope fully describing a unit of work.

    Platform-agnostic.  The ``operation`` field replaces the substrate's
    ``primitive_name`` — it names what to do without coupling to the EOS
    primitive ontology.
    """

    execution_id: str
    correlation_id: str
    causal_event_id: str
    session_id: str
    operation: str
    inputs: dict[str, Any]
    execution_class: ExecutionClass
    constraints: ExecutionConstraints
    target: ExecutionTarget
    context: ExecutionContext
    issued_at: str
    issued_by: str
    idempotency_key: str
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "causal_event_id": self.causal_event_id,
            "session_id": self.session_id,
            "operation": self.operation,
            "inputs": self.inputs,
            "execution_class": self.execution_class.value,
            "constraints": {
                "timeout_s": self.constraints.timeout_s,
                "max_retries": self.constraints.max_retries,
                "sandbox": self.constraints.sandbox,
                "max_tokens": self.constraints.max_tokens,
                "cost_limit_usd": self.constraints.cost_limit_usd,
            },
            "target": {
                "node_id": self.target.node_id,
                "transport": self.target.transport,
                "fallback_node_id": self.target.fallback_node_id,
                "fallback_transport": self.target.fallback_transport,
            },
            "context": self.context.to_dict(),
            "issued_at": self.issued_at,
            "issued_by": self.issued_by,
            "idempotency_key": self.idempotency_key,
            "priority": self.priority.value,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionRequest:
        constraints_raw = data["constraints"]
        target_raw = data["target"]
        return cls(
            execution_id=data["execution_id"],
            correlation_id=data["correlation_id"],
            causal_event_id=data["causal_event_id"],
            session_id=data["session_id"],
            operation=data["operation"],
            inputs=data["inputs"],
            execution_class=ExecutionClass(data["execution_class"]),
            constraints=ExecutionConstraints(
                timeout_s=constraints_raw["timeout_s"],
                max_retries=constraints_raw["max_retries"],
                sandbox=constraints_raw["sandbox"],
                max_tokens=constraints_raw.get("max_tokens", 0),
                cost_limit_usd=constraints_raw.get("cost_limit_usd", 0.0),
            ),
            target=ExecutionTarget(
                node_id=target_raw["node_id"],
                transport=target_raw["transport"],
                fallback_node_id=target_raw.get("fallback_node_id"),
                fallback_transport=target_raw.get("fallback_transport"),
            ),
            context=ExecutionContext.from_dict(data.get("context", {})),
            issued_at=data["issued_at"],
            issued_by=data["issued_by"],
            idempotency_key=data["idempotency_key"],
            priority=ExecutionPriority(data.get("priority", "normal")),
            retry_count=data.get("retry_count", 0),
        )


# ---------------------------------------------------------------------------
# ExecutionResult — what happened
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable envelope describing the outcome of an execution."""

    execution_id: str
    correlation_id: str
    causal_event_id: str
    operation: str
    status: ExecutionStatus
    outputs: dict[str, Any]
    side_effects: tuple[str, ...] = ()
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    node_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    execution_hash: Optional[str] = None
    retry_count: int = 0
    model_used: Optional[str] = None
    tokens_used: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "causal_event_id": self.causal_event_id,
            "operation": self.operation,
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
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionResult:
        return cls(
            execution_id=data["execution_id"],
            correlation_id=data["correlation_id"],
            causal_event_id=data["causal_event_id"],
            operation=data["operation"],
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
            model_used=data.get("model_used"),
            tokens_used=data.get("tokens_used", {}),
            cost_usd=data.get("cost_usd", 0.0),
            latency_ms=data.get("latency_ms", 0),
        )
