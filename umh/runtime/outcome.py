"""Outcome model — execution result records for the learning loop.

Captures what happened when a strategy was executed under a given state:
    - outcome status (SUCCESS / FAILURE / PARTIAL / UNKNOWN)
    - numeric performance metrics (success_score, latency, effort, error_count)
    - linkage to decision and state context

Frozen dataclasses — immutable after creation.
No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class OutcomeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class StrategyOutcome:
    """Immutable record of a strategy execution result."""

    outcome_id: str
    decision_id: str
    action_name: str
    strategy_name: str
    state_signature: str
    status: OutcomeStatus = OutcomeStatus.UNKNOWN
    success_score: float = 0.0
    latency: float = 0.0
    effort: float = 0.0
    error_count: int = 0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "success_score", _clamp(self.success_score, 0.0, 1.0))
        object.__setattr__(self, "latency", max(0.0, self.latency))
        object.__setattr__(self, "effort", _clamp(self.effort, 0.0, 1.0))
        object.__setattr__(self, "error_count", max(0, self.error_count))
        if not self.timestamp:
            object.__setattr__(self, "timestamp", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "decision_id": self.decision_id,
            "action_name": self.action_name,
            "strategy_name": self.strategy_name,
            "state_signature": self.state_signature,
            "status": self.status.value,
            "success_score": round(self.success_score, 4),
            "latency": round(self.latency, 4),
            "effort": round(self.effort, 4),
            "error_count": self.error_count,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DecisionOutcomeLink:
    """Links a state + decision to its outcome."""

    state_signature: str
    decision_id: str
    strategy_name: str
    objective_id: str
    outcome_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_signature": self.state_signature,
            "decision_id": self.decision_id,
            "strategy_name": self.strategy_name,
            "objective_id": self.objective_id,
            "outcome_id": self.outcome_id,
        }


@dataclass(frozen=True)
class StrategyStats:
    """Aggregate performance statistics for a strategy."""

    strategy_name: str
    total_count: int
    success_count: int
    failure_count: int
    partial_count: int
    unknown_count: int
    average_success_score: float
    average_latency: float
    average_effort: float

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "partial_count": self.partial_count,
            "unknown_count": self.unknown_count,
            "average_success_score": round(self.average_success_score, 4),
            "average_latency": round(self.average_latency, 4),
            "average_effort": round(self.average_effort, 4),
            "success_rate": round(self.success_rate, 4),
        }


@dataclass(frozen=True)
class StrategyPerformanceSignal:
    """Performance signal for a strategy with confidence."""

    strategy_name: str
    sample_size: int
    success_rate: float
    average_score: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "sample_size": self.sample_size,
            "success_rate": round(self.success_rate, 4),
            "average_score": round(self.average_score, 4),
            "confidence": round(self.confidence, 4),
        }
