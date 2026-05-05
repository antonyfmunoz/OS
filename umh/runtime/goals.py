"""Long-horizon goals — goal typing, reinforcement scoring, and bias computation.

Provides LongTermGoal for goal classification, ReinforcementScorer for
computing reinforcement signals from goal memory, and GoalBiasScorer
for producing multiplicative bias factors in the meta-planner scoring chain.

Reinforcement formula:
    reinforcement = success_rate * identity_alignment * duration_factor
    clamped to [0.5, 1.5]

Duration factor:
    min(1.0, duration_ticks / max_duration)

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from umh.runtime.goal_memory import GoalMemory, GoalTypeStats


_DEFAULT_MAX_DURATION = 100
_MIN_REINFORCEMENT = 0.5
_MAX_REINFORCEMENT = 1.5
_MIN_GOAL_BIAS = 0.85
_MAX_GOAL_BIAS = 1.15
_DEFAULT_PERSISTENCE_WEIGHT = 0.3
_DEFAULT_ALIGNMENT_WEIGHT = 0.4
_DEFAULT_SUCCESS_WEIGHT = 0.3


@dataclass(frozen=True)
class LongTermGoal:
    """A classified long-horizon goal with type and scoring weights."""

    goal_id: str
    goal_type: str
    description: str
    weight: float = 1.0
    persistence_weight: float = _DEFAULT_PERSISTENCE_WEIGHT
    alignment_weight: float = _DEFAULT_ALIGNMENT_WEIGHT
    success_weight: float = _DEFAULT_SUCCESS_WEIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "description": self.description,
            "weight": round(self.weight, 4),
            "persistence_weight": round(self.persistence_weight, 4),
            "alignment_weight": round(self.alignment_weight, 4),
            "success_weight": round(self.success_weight, 4),
        }


@dataclass(frozen=True)
class ReinforcementSignal:
    """Result of computing a reinforcement signal for a goal type."""

    goal_type: str
    reinforcement: float
    success_component: float
    alignment_component: float
    duration_component: float
    record_count: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "reinforcement": round(self.reinforcement, 4),
            "success_component": round(self.success_component, 4),
            "alignment_component": round(self.alignment_component, 4),
            "duration_component": round(self.duration_component, 4),
            "record_count": self.record_count,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GoalBiasInfluence:
    """Result of computing goal bias on a scoring decision."""

    factor: float
    reinforcement_signal: ReinforcementSignal | None
    goal_type: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "factor": round(self.factor, 4),
            "goal_type": self.goal_type,
            "reason": self.reason,
        }
        if self.reinforcement_signal is not None:
            result["reinforcement"] = self.reinforcement_signal.to_dict()
        return result


class ReinforcementScorer:
    """Computes reinforcement signals from goal memory.

    reinforcement = success_rate * identity_alignment * duration_factor
    clamped to [MIN_REINFORCEMENT, MAX_REINFORCEMENT]

    duration_factor = min(1.0, avg_duration / max_duration)
    """

    def __init__(
        self,
        *,
        max_duration: int = _DEFAULT_MAX_DURATION,
    ) -> None:
        self._max_duration = max(1, max_duration)

    @property
    def max_duration(self) -> int:
        return self._max_duration

    def compute(
        self,
        stats: GoalTypeStats,
    ) -> ReinforcementSignal:
        """Compute reinforcement signal from goal type statistics."""
        duration_factor = min(1.0, stats.avg_duration / self._max_duration)
        success_component = stats.avg_success_rate
        alignment_component = stats.avg_identity_alignment
        duration_component = duration_factor

        raw = success_component * alignment_component * duration_component
        reinforcement = max(
            _MIN_REINFORCEMENT,
            min(_MAX_REINFORCEMENT, raw),
        )

        reason = self._build_reason(
            stats,
            reinforcement,
            success_component,
            alignment_component,
            duration_component,
        )

        return ReinforcementSignal(
            goal_type=stats.goal_type,
            reinforcement=reinforcement,
            success_component=success_component,
            alignment_component=alignment_component,
            duration_component=duration_component,
            record_count=stats.count,
            reason=reason,
        )

    def _build_reason(
        self,
        stats: GoalTypeStats,
        reinforcement: float,
        success: float,
        alignment: float,
        duration: float,
    ) -> str:
        parts: list[str] = []

        if success >= 0.7:
            parts.append("strong success history")
        elif success >= 0.4:
            parts.append("moderate success")
        else:
            parts.append("weak success history")

        if alignment >= 0.7:
            parts.append("high identity alignment")
        elif alignment >= 0.4:
            parts.append("moderate alignment")
        else:
            parts.append("low alignment")

        if stats.count >= 5:
            parts.append(f"well-established ({stats.count} records)")
        elif stats.count >= 2:
            parts.append(f"emerging ({stats.count} records)")
        else:
            parts.append("limited data (1 record)")

        parts.append(f"reinforcement={reinforcement:.4f}")
        return "; ".join(parts)


class GoalBiasScorer:
    """Computes goal bias factors for the meta-planner scoring chain.

    Produces a multiplicative factor in [0.85, 1.15] that biases
    sequence scores based on historical goal performance and identity
    alignment. The factor never overrides — only nudges.

    When goal memory has records for the relevant goal type,
    the bias is derived from the reinforcement signal. Otherwise
    the bias is neutral (1.0).
    """

    def __init__(
        self,
        *,
        goal_memory: GoalMemory | None = None,
        reinforcement_scorer: ReinforcementScorer | None = None,
        enabled: bool = False,
    ) -> None:
        self._goal_memory = goal_memory
        self._reinforcement_scorer = reinforcement_scorer or ReinforcementScorer()
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def goal_memory(self) -> GoalMemory | None:
        return self._goal_memory

    @property
    def reinforcement_scorer(self) -> ReinforcementScorer:
        return self._reinforcement_scorer

    def compute_factor(
        self,
        *,
        goal_type: str = "",
        goal_weight: float = 1.0,
    ) -> GoalBiasInfluence:
        """Compute goal bias factor. Pure, no side effects."""
        if not self._enabled or self._goal_memory is None:
            return GoalBiasInfluence(
                factor=1.0,
                reinforcement_signal=None,
                goal_type=goal_type,
                reason="goal bias scoring disabled",
            )

        if not goal_type:
            return GoalBiasInfluence(
                factor=1.0,
                reinforcement_signal=None,
                goal_type="",
                reason="no goal type specified",
            )

        stats = self._goal_memory.compute_stats(goal_type)
        if stats is None:
            return GoalBiasInfluence(
                factor=1.0,
                reinforcement_signal=None,
                goal_type=goal_type,
                reason=f"no history for goal type '{goal_type}'",
            )

        signal = self._reinforcement_scorer.compute(stats)

        raw_bias = (signal.reinforcement - 0.5) * goal_weight
        bias = max(-0.5, min(0.5, raw_bias))

        factor = max(
            _MIN_GOAL_BIAS,
            min(_MAX_GOAL_BIAS, 1.0 + bias),
        )

        reason = f"goal type '{goal_type}': {signal.reason}; bias factor={factor:.4f}"

        return GoalBiasInfluence(
            factor=factor,
            reinforcement_signal=signal,
            goal_type=goal_type,
            reason=reason,
        )
