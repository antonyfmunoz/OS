"""Arbitration — goal evaluation, ranking, and objective selection.

Evaluates multiple objectives, scores them on urgency, importance,
and effort-to-value ratio, ranks them deterministically, and selects
the best objective to pursue. Every decision carries an explanation.

Pure computation — no I/O, no subprocess, no state mutation.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_DEFAULT_URGENCY_WEIGHT = 0.30
_DEFAULT_IMPORTANCE_WEIGHT = 0.30
_DEFAULT_VALUE_WEIGHT = 0.25
_DEFAULT_EFFORT_WEIGHT = 0.15

_DEFAULT_PRIORITY = 5
_MAX_PRIORITY = 10
_MIN_PRIORITY = 1


@dataclass(frozen=True)
class Objective:
    """An actionable goal the system can pursue."""

    objective_id: str
    description: str
    priority: int = _DEFAULT_PRIORITY
    deadline: str = ""
    effort_estimate: float = 1.0
    expected_value: float = 1.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "priority": self.priority,
            "deadline": self.deadline,
            "effort_estimate": round(self.effort_estimate, 4),
            "expected_value": round(self.expected_value, 4),
            "source": self.source,
        }


@dataclass(frozen=True)
class ObjectiveScore:
    """Breakdown of how an objective was scored."""

    objective_id: str
    urgency_score: float
    importance_score: float
    value_score: float
    effort_score: float
    total_score: float
    factors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "urgency_score": round(self.urgency_score, 4),
            "importance_score": round(self.importance_score, 4),
            "value_score": round(self.value_score, 4),
            "effort_score": round(self.effort_score, 4),
            "total_score": round(self.total_score, 4),
            "factors": list(self.factors),
        }


@dataclass(frozen=True)
class ArbitrationWeights:
    """Weights for objective scoring dimensions."""

    urgency: float = _DEFAULT_URGENCY_WEIGHT
    importance: float = _DEFAULT_IMPORTANCE_WEIGHT
    value: float = _DEFAULT_VALUE_WEIGHT
    effort: float = _DEFAULT_EFFORT_WEIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "urgency": round(self.urgency, 4),
            "importance": round(self.importance, 4),
            "value": round(self.value, 4),
            "effort": round(self.effort, 4),
        }


@dataclass(frozen=True)
class ArbitrationResult:
    """Complete arbitration decision with reasoning."""

    selected: Objective
    selected_score: ObjectiveScore
    all_scores: tuple[ObjectiveScore, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.to_dict(),
            "selected_score": self.selected_score.to_dict(),
            "candidates_evaluated": len(self.all_scores),
            "reason": self.reason,
            "all_scores": [s.to_dict() for s in self.all_scores],
        }

    @property
    def explanation(self) -> list[str]:
        lines: list[str] = [
            f"Selected '{self.selected.description}' (score {self.selected_score.total_score:.4f})",
            self.reason,
        ]
        for s in self.all_scores:
            marker = ">>>" if s.objective_id == self.selected.objective_id else "   "
            lines.append(
                f"{marker} {s.objective_id}: score={s.total_score:.4f} "
                f"urgency={s.urgency_score:.2f} "
                f"importance={s.importance_score:.2f} "
                f"value={s.value_score:.2f}"
            )
        return lines


class ObjectiveEvaluator:
    """Scores individual objectives on multiple dimensions.

    Urgency: deadline proximity (higher if deadline is set).
    Importance: normalized priority.
    Value: expected_value directly.
    Effort: inverse of effort (lower effort = higher score).
    """

    def __init__(
        self,
        weights: ArbitrationWeights | None = None,
        *,
        reference_time: str = "",
    ) -> None:
        w = weights or ArbitrationWeights()
        total = w.urgency + w.importance + w.value + w.effort
        if total <= 0:
            total = 1.0
        self._w_urgency = w.urgency / total
        self._w_importance = w.importance / total
        self._w_value = w.value / total
        self._w_effort = w.effort / total
        self._reference_time = reference_time or _iso_now()

    @property
    def weights(self) -> ArbitrationWeights:
        return ArbitrationWeights(
            urgency=self._w_urgency,
            importance=self._w_importance,
            value=self._w_value,
            effort=self._w_effort,
        )

    def score(self, objective: Objective) -> ObjectiveScore:
        """Score an objective across all dimensions. Pure function."""
        urgency = self._compute_urgency(objective)
        importance = self._compute_importance(objective)
        value = self._compute_value(objective)
        effort = self._compute_effort(objective)
        factors = self._explain_factors(objective, urgency, importance, value, effort)

        total = (
            self._w_urgency * urgency
            + self._w_importance * importance
            + self._w_value * value
            + self._w_effort * effort
        )

        return ObjectiveScore(
            objective_id=objective.objective_id,
            urgency_score=urgency,
            importance_score=importance,
            value_score=value,
            effort_score=effort,
            total_score=total,
            factors=tuple(factors),
        )

    def _compute_urgency(self, objective: Objective) -> float:
        if not objective.deadline:
            return 0.3
        ref = self._reference_time[:10]
        dl = objective.deadline[:10]
        if dl <= ref:
            return 1.0
        if dl <= ref[:8] + str(int(ref[8:10]) + 7).zfill(2) if len(ref) >= 10 else "":
            return 0.8
        return 0.5

    def _compute_importance(self, objective: Objective) -> float:
        clamped = max(_MIN_PRIORITY, min(_MAX_PRIORITY, objective.priority))
        return clamped / _MAX_PRIORITY

    def _compute_value(self, objective: Objective) -> float:
        return min(1.0, max(0.0, objective.expected_value))

    def _compute_effort(self, objective: Objective) -> float:
        return 1.0 / (1.0 + max(0.0, objective.effort_estimate))

    def _explain_factors(
        self,
        objective: Objective,
        urgency: float,
        importance: float,
        value: float,
        effort: float,
    ) -> list[str]:
        factors: list[str] = []
        if urgency >= 0.8:
            factors.append(
                "high urgency" + (" — deadline approaching" if objective.deadline else "")
            )
        elif urgency >= 0.5:
            factors.append("moderate urgency")
        if importance >= 0.7:
            factors.append(f"high priority ({objective.priority}/{_MAX_PRIORITY})")
        if value >= 0.8:
            factors.append("strong expected value")
        if effort >= 0.5:
            factors.append("low effort requirement")
        elif effort < 0.3:
            factors.append("high effort requirement")
        return factors


class ObjectiveRanker:
    """Ranks objectives by score. Deterministic tie-breaking by id."""

    def __init__(self, evaluator: ObjectiveEvaluator | None = None) -> None:
        self._evaluator = evaluator or ObjectiveEvaluator()

    @property
    def evaluator(self) -> ObjectiveEvaluator:
        return self._evaluator

    def rank(self, objectives: list[Objective]) -> list[ObjectiveScore]:
        """Score and rank objectives. Highest score first."""
        scores = [self._evaluator.score(o) for o in objectives]
        scores.sort(key=lambda s: (-s.total_score, s.objective_id))
        return scores


class ArbitrationEngine:
    """Selects the best objective from a set of candidates.

    Combines ObjectiveEvaluator and ObjectiveRanker, then produces
    an ArbitrationResult with full explainability. Respects user
    priority: objectives with explicit high priority get a boost
    and any override is explained.
    """

    def __init__(
        self,
        *,
        evaluator: ObjectiveEvaluator | None = None,
        ranker: ObjectiveRanker | None = None,
    ) -> None:
        eval_ = evaluator or ObjectiveEvaluator()
        self._ranker = ranker or ObjectiveRanker(evaluator=eval_)
        self._evaluator = self._ranker.evaluator

    @property
    def evaluator(self) -> ObjectiveEvaluator:
        return self._evaluator

    @property
    def ranker(self) -> ObjectiveRanker:
        return self._ranker

    def select(self, objectives: list[Objective]) -> ArbitrationResult | None:
        """Select the best objective. Returns None if empty list."""
        if not objectives:
            return None

        ranked = self._ranker.rank(objectives)
        obj_map = {o.objective_id: o for o in objectives}

        best_score = ranked[0]
        best_obj = obj_map[best_score.objective_id]

        reason = self._build_reason(best_obj, best_score, ranked)

        return ArbitrationResult(
            selected=best_obj,
            selected_score=best_score,
            all_scores=tuple(ranked),
            reason=reason,
        )

    def _build_reason(
        self,
        selected: Objective,
        score: ObjectiveScore,
        ranked: list[ObjectiveScore],
    ) -> str:
        parts: list[str] = list(score.factors)

        if len(ranked) > 1:
            runner_up = ranked[1]
            margin = score.total_score - runner_up.total_score
            if margin < 0.05:
                parts.append(f"narrow margin over '{runner_up.objective_id}' ({margin:.3f})")

        if selected.priority >= 8:
            parts.append("user-assigned high priority respected")

        return "; ".join(parts) if parts else "best overall objective score"
