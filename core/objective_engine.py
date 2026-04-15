"""Multi-Objective Engine — evaluate runs against multiple weighted objectives.

Extends the single-objective system in core/objective.py to support:
- Multiple simultaneous objectives with weights
- Hard constraints that override weighted scoring
- Short/mid/long time horizons
- Tradeoff explanation between competing objectives

Usage:
    from core.objective_engine import ObjectiveFunction, ObjectiveSet

    obj_set = ObjectiveSet(objectives=[
        ObjectiveFunction("reply_rate", "reply_rate", "maximize", 0.05, weight=0.4),
        ObjectiveFunction("cost_per_run", "cost", "minimize", 10.0, weight=0.3),
        ObjectiveFunction("quality", "quality_score", "maximize", 0.7, weight=0.3, hard_constraint=True),
    ])

    result = obj_set.evaluate(real_data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Single objective function
# ---------------------------------------------------------------------------


@dataclass
class ObjectiveFunction:
    """One objective in a multi-objective set.

    Args:
        name:            Human-readable identifier.
        metric_name:     Key to look up in real_data dict.
        direction:       "maximize" or "minimize".
        threshold:       Success/failure boundary.
        weight:          Relative importance (0.0-1.0). Weights don't need to sum to 1.
        time_horizon:    "short" (days), "mid" (weeks), "long" (months+).
        hard_constraint: If True, failing this objective fails the entire run.
    """

    name: str
    metric_name: str
    direction: str  # "maximize" | "minimize"
    threshold: float
    weight: float = 1.0
    time_horizon: str = "short"  # "short" | "mid" | "long"
    hard_constraint: bool = False

    def score(self, value: float) -> float:
        """Score a single metric value against this objective.

        Returns 0.0-1.0 where 1.0 = fully achieved.
        """
        if self.direction == "maximize":
            if self.threshold == 0:
                return 1.0 if value > 0 else 0.0
            return min(value / self.threshold, 1.0)
        else:  # minimize
            if value <= 0:
                return 1.0
            if self.threshold <= 0:
                return 0.0
            # Lower is better: score = threshold / value, capped at 1.0
            return min(self.threshold / value, 1.0)

    def achieved(self, value: float) -> bool:
        """Check if the threshold is met."""
        if self.direction == "maximize":
            return value >= self.threshold
        return value <= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "metric_name": self.metric_name,
            "direction": self.direction,
            "threshold": self.threshold,
            "weight": self.weight,
            "time_horizon": self.time_horizon,
            "hard_constraint": self.hard_constraint,
        }


# ---------------------------------------------------------------------------
# Objective evaluation result
# ---------------------------------------------------------------------------


@dataclass
class ObjectiveResult:
    """Result of evaluating one objective."""

    objective: ObjectiveFunction
    value: float  # raw metric value
    score: float  # 0.0-1.0 normalized score
    achieved: bool
    gap: float  # distance from threshold (positive = below)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.objective.name,
            "metric": self.objective.metric_name,
            "value": round(self.value, 4),
            "score": round(self.score, 4),
            "achieved": self.achieved,
            "gap": round(self.gap, 4),
            "hard_constraint": self.objective.hard_constraint,
            "weight": self.objective.weight,
        }


# ---------------------------------------------------------------------------
# Objective set — multiple objectives evaluated together
# ---------------------------------------------------------------------------


@dataclass
class ObjectiveSet:
    """A set of objectives evaluated together with weighted aggregation.

    Hard constraints override the weighted score: if any hard constraint
    fails, the entire run is marked failed regardless of weighted score.
    """

    objectives: list[ObjectiveFunction]
    _results: list[ObjectiveResult] = field(default_factory=list, init=False)

    def evaluate(self, real_data: dict[str, Any]) -> list[ObjectiveResult]:
        """Evaluate all objectives against real data.

        Args:
            real_data: Dict of metric_name → value.

        Returns:
            List of ObjectiveResult for each objective.
        """
        self._results = []
        for obj in self.objectives:
            value = float(real_data.get(obj.metric_name, 0))
            score = obj.score(value)
            achieved = obj.achieved(value)

            if obj.direction == "maximize":
                gap = max(obj.threshold - value, 0)
            else:
                gap = max(value - obj.threshold, 0)

            self._results.append(
                ObjectiveResult(
                    objective=obj,
                    value=value,
                    score=score,
                    achieved=achieved,
                    gap=gap,
                )
            )
        return self._results

    def aggregate_score(self) -> float:
        """Weighted aggregate score across all objectives.

        Returns 0.0 if any hard constraint is violated.
        """
        if not self._results:
            return 0.0

        # Hard constraint check first
        for r in self._results:
            if r.objective.hard_constraint and not r.achieved:
                return 0.0

        total_weight = sum(r.objective.weight for r in self._results)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(r.score * r.objective.weight for r in self._results)
        return weighted_sum / total_weight

    def constraint_violations(self) -> list[ObjectiveResult]:
        """Return all hard constraints that were violated."""
        return [
            r for r in self._results if r.objective.hard_constraint and not r.achieved
        ]

    def explain_tradeoffs(self) -> list[dict[str, Any]]:
        """Explain tradeoffs between objectives.

        Identifies:
        - Objectives pulling in opposite directions
        - Which objectives are being sacrificed
        - Time horizon conflicts
        """
        if not self._results:
            return []

        tradeoffs: list[dict[str, Any]] = []

        # Find achieved vs failed
        achieved = [r for r in self._results if r.achieved]
        failed = [r for r in self._results if not r.achieved]

        # Opposing direction pairs
        for i, r1 in enumerate(self._results):
            for r2 in self._results[i + 1 :]:
                if r1.objective.direction != r2.objective.direction:
                    tradeoffs.append(
                        {
                            "type": "opposing_direction",
                            "objectives": [r1.objective.name, r2.objective.name],
                            "explanation": (
                                f"{r1.objective.name} ({r1.objective.direction} {r1.objective.metric_name}) "
                                f"vs {r2.objective.name} ({r2.objective.direction} {r2.objective.metric_name})"
                            ),
                            "scores": {
                                r1.objective.name: round(r1.score, 4),
                                r2.objective.name: round(r2.score, 4),
                            },
                        }
                    )

        # Time horizon conflicts
        horizons: dict[str, list[ObjectiveResult]] = {}
        for r in self._results:
            horizons.setdefault(r.objective.time_horizon, []).append(r)

        if "short" in horizons and "long" in horizons:
            short_avg = sum(r.score for r in horizons["short"]) / len(horizons["short"])
            long_avg = sum(r.score for r in horizons["long"]) / len(horizons["long"])
            if abs(short_avg - long_avg) > 0.3:
                tradeoffs.append(
                    {
                        "type": "time_horizon_conflict",
                        "explanation": (
                            f"Short-term objectives avg {short_avg:.2f} vs "
                            f"long-term avg {long_avg:.2f} — "
                            f"{'short-term sacrifice' if short_avg < long_avg else 'long-term sacrifice'}"
                        ),
                        "short_term_score": round(short_avg, 4),
                        "long_term_score": round(long_avg, 4),
                    }
                )

        # Sacrificed objectives (high weight, low score)
        for r in failed:
            if r.objective.weight >= 0.3:
                tradeoffs.append(
                    {
                        "type": "sacrifice",
                        "objective": r.objective.name,
                        "explanation": (
                            f"{r.objective.name} (weight={r.objective.weight}) "
                            f"scored {r.score:.2f} — high-weight objective not met"
                        ),
                        "weight": r.objective.weight,
                        "score": round(r.score, 4),
                    }
                )

        return tradeoffs

    @property
    def ok(self) -> bool:
        """True if aggregate score > 0 (no hard constraint violations)
        and at least half the objectives are achieved."""
        if not self._results:
            return False
        agg = self.aggregate_score()
        if agg == 0.0:
            return False
        achieved_count = sum(1 for r in self._results if r.achieved)
        return achieved_count > len(self._results) / 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregate_score": round(self.aggregate_score(), 4),
            "ok": self.ok,
            "results": [r.to_dict() for r in self._results],
            "constraint_violations": [
                r.to_dict() for r in self.constraint_violations()
            ],
            "tradeoffs": self.explain_tradeoffs(),
        }


# ---------------------------------------------------------------------------
# Pre-built objective sets for common scenarios
# ---------------------------------------------------------------------------


def outreach_objectives() -> ObjectiveSet:
    """Standard objective set for outreach campaigns."""
    return ObjectiveSet(
        objectives=[
            ObjectiveFunction(
                "reply_rate",
                "reply_rate",
                "maximize",
                0.05,
                weight=0.4,
                time_horizon="short",
            ),
            ObjectiveFunction(
                "meetings_booked",
                "meetings_booked",
                "maximize",
                1.0,
                weight=0.35,
                time_horizon="short",
            ),
            ObjectiveFunction(
                "cost_per_reply",
                "cost_per_reply",
                "minimize",
                5.0,
                weight=0.15,
                time_horizon="short",
            ),
            ObjectiveFunction(
                "sent_volume",
                "sent",
                "maximize",
                50.0,
                weight=0.1,
                time_horizon="short",
                hard_constraint=True,
            ),
        ]
    )


def content_objectives() -> ObjectiveSet:
    """Standard objective set for content creation."""
    return ObjectiveSet(
        objectives=[
            ObjectiveFunction(
                "engagement_rate",
                "engagement_rate",
                "maximize",
                0.03,
                weight=0.3,
                time_horizon="short",
            ),
            ObjectiveFunction(
                "impressions",
                "impressions",
                "maximize",
                1000.0,
                weight=0.25,
                time_horizon="short",
            ),
            ObjectiveFunction(
                "saves_shares",
                "saves",
                "maximize",
                10.0,
                weight=0.25,
                time_horizon="mid",
            ),
            ObjectiveFunction(
                "follower_growth",
                "follower_delta",
                "maximize",
                5.0,
                weight=0.2,
                time_horizon="long",
            ),
        ]
    )


def habit_objectives() -> ObjectiveSet:
    """Standard objective set for habit tracking."""
    return ObjectiveSet(
        objectives=[
            ObjectiveFunction(
                "completion_rate",
                "completion_rate",
                "maximize",
                0.8,
                weight=0.4,
                time_horizon="short",
                hard_constraint=True,
            ),
            ObjectiveFunction(
                "focus_score",
                "focus_score",
                "maximize",
                7.0,
                weight=0.3,
                time_horizon="mid",
            ),
            ObjectiveFunction(
                "energy_score",
                "energy_score",
                "maximize",
                6.0,
                weight=0.3,
                time_horizon="long",
            ),
        ]
    )


__all__ = [
    "ObjectiveFunction",
    "ObjectiveResult",
    "ObjectiveSet",
    "outreach_objectives",
    "content_objectives",
    "habit_objectives",
]
