"""Goal hierarchy — meta-goal abstraction, grouped reinforcement, and bias propagation.

Provides MetaGoal for hierarchical goal grouping, GoalHierarchy for
registration and querying, and HierarchyScorer for computing meta-goal
factors in the planner scoring chain.

Aggregation:
    meta_score = Σ(child_reinforcement_i × child_weight_i) / Σ(child_weight_i)
    clamped to [0.5, 1.5]

Meta-goal factor:
    factor = clamp(1.0 + (meta_score - 0.5) × meta_weight, 0.9, 1.1)

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from umh.runtime.goal_memory import GoalMemory
    from umh.runtime.goals import ReinforcementScorer


_MIN_META_FACTOR = 0.90
_MAX_META_FACTOR = 1.10
_MIN_META_SCORE = 0.5
_MAX_META_SCORE = 1.5
_DEFAULT_META_WEIGHT = 0.5


@dataclass(frozen=True)
class MetaGoal:
    """An abstract grouping of child goal types."""

    name: str
    child_goal_types: tuple[str, ...]
    weight: float = _DEFAULT_META_WEIGHT
    aggregation_method: str = "weighted_average"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "child_goal_types": list(self.child_goal_types),
            "weight": round(self.weight, 4),
            "aggregation_method": self.aggregation_method,
            "description": self.description,
        }


@dataclass(frozen=True)
class MetaGoalScore:
    """Aggregated score for a meta-goal."""

    meta_goal_name: str
    score: float
    child_scores: dict[str, float]
    child_counts: dict[str, int]
    total_records: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_goal_name": self.meta_goal_name,
            "score": round(self.score, 4),
            "child_scores": {k: round(v, 4) for k, v in sorted(self.child_scores.items())},
            "child_counts": dict(sorted(self.child_counts.items())),
            "total_records": self.total_records,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class HierarchyInfluence:
    """Result of computing hierarchy influence on scoring."""

    factor: float
    meta_goal_scores: dict[str, float]
    contributing_types: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": round(self.factor, 4),
            "meta_goal_scores": {k: round(v, 4) for k, v in sorted(self.meta_goal_scores.items())},
            "contributing_types": self.contributing_types,
            "reason": self.reason,
        }


class CycleError(ValueError):
    """Raised when registering a meta-goal would create a cycle."""


class GoalHierarchy:
    """Registry of meta-goals with cycle-free child mappings.

    Meta-goals group child goal types for aggregated reinforcement.
    The hierarchy is validated at registration time to prevent cycles.
    Read-only during execution — all mutations happen at setup time.
    """

    def __init__(self) -> None:
        self._meta_goals: dict[str, MetaGoal] = {}
        self._type_to_meta: dict[str, list[str]] = {}

    @property
    def meta_goal_count(self) -> int:
        return len(self._meta_goals)

    def register_meta_goal(self, meta_goal: MetaGoal) -> None:
        """Register a meta-goal. Raises CycleError on circular dependency."""
        if not meta_goal.name:
            raise ValueError("Meta-goal name cannot be empty")
        if not meta_goal.child_goal_types:
            raise ValueError("Meta-goal must have at least one child goal type")

        if self._would_create_cycle(meta_goal):
            raise CycleError(f"Registering '{meta_goal.name}' would create a circular dependency")

        self._meta_goals[meta_goal.name] = meta_goal

        for child_type in meta_goal.child_goal_types:
            if child_type not in self._type_to_meta:
                self._type_to_meta[child_type] = []
            if meta_goal.name not in self._type_to_meta[child_type]:
                self._type_to_meta[child_type].append(meta_goal.name)

    def _would_create_cycle(self, new_meta: MetaGoal) -> bool:
        """Check if adding this meta-goal creates a cycle.

        A cycle exists if any child type is the name of a meta-goal
        that (transitively) depends on the new meta-goal's name.
        """
        for child_type in new_meta.child_goal_types:
            if child_type == new_meta.name:
                return True
            if self._has_path(child_type, new_meta.name):
                return True
        return False

    def _has_path(self, from_type: str, to_name: str) -> bool:
        """Check if there's a path from from_type to to_name through the hierarchy."""
        if from_type not in self._meta_goals:
            return False

        visited: set[str] = set()
        stack = [from_type]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current not in self._meta_goals:
                continue

            meta = self._meta_goals[current]
            for child in meta.child_goal_types:
                if child == to_name:
                    return True
                if child not in visited:
                    stack.append(child)

        return False

    def get_meta_goal(self, name: str) -> MetaGoal | None:
        """Get a registered meta-goal by name."""
        return self._meta_goals.get(name)

    def get_children(self, meta_goal_name: str) -> tuple[str, ...]:
        """Get child goal types for a meta-goal."""
        meta = self._meta_goals.get(meta_goal_name)
        if meta is None:
            return ()
        return meta.child_goal_types

    def get_meta_goals_for_type(self, goal_type: str) -> list[str]:
        """Get all meta-goal names that contain this goal type."""
        return list(self._type_to_meta.get(goal_type, []))

    def list_meta_goals(self) -> list[MetaGoal]:
        """Return all registered meta-goals, sorted by name."""
        return [self._meta_goals[k] for k in sorted(self._meta_goals)]

    def compute_meta_score(
        self,
        meta_goal_name: str,
        child_reinforcements: dict[str, float],
    ) -> MetaGoalScore | None:
        """Compute aggregated score for a meta-goal from child reinforcements.

        Uses weighted average: Σ(reinforcement_i × 1.0) / count
        Clamped to [_MIN_META_SCORE, _MAX_META_SCORE].
        """
        meta = self._meta_goals.get(meta_goal_name)
        if meta is None:
            return None

        child_scores: dict[str, float] = {}
        child_counts: dict[str, int] = {}
        total_weight = 0.0
        weighted_sum = 0.0
        total_records = 0

        for child_type in meta.child_goal_types:
            if child_type in child_reinforcements:
                reinforcement = child_reinforcements[child_type]
                child_scores[child_type] = reinforcement
                child_counts[child_type] = 1
                weighted_sum += reinforcement
                total_weight += 1.0
                total_records += 1

        if total_weight == 0:
            return MetaGoalScore(
                meta_goal_name=meta_goal_name,
                score=1.0,
                child_scores={},
                child_counts={},
                total_records=0,
                reason="no child data available",
            )

        raw_score = weighted_sum / total_weight
        score = max(_MIN_META_SCORE, min(_MAX_META_SCORE, raw_score))

        reason = self._build_score_reason(meta, child_scores, score, total_records)

        return MetaGoalScore(
            meta_goal_name=meta_goal_name,
            score=score,
            child_scores=child_scores,
            child_counts=child_counts,
            total_records=total_records,
            reason=reason,
        )

    def _build_score_reason(
        self,
        meta: MetaGoal,
        child_scores: dict[str, float],
        score: float,
        total_records: int,
    ) -> str:
        parts: list[str] = []

        contributing = len(child_scores)
        total_children = len(meta.child_goal_types)
        parts.append(f"{contributing}/{total_children} child types contributing")

        if score >= 0.8:
            parts.append("strong aggregate performance")
        elif score >= 0.6:
            parts.append("moderate aggregate performance")
        else:
            parts.append("weak aggregate performance")

        parts.append(f"meta_score={score:.4f}")
        return "; ".join(parts)

    def clear(self) -> None:
        """Clear all registrations."""
        self._meta_goals.clear()
        self._type_to_meta.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_goal_count": self.meta_goal_count,
            "meta_goals": {k: v.to_dict() for k, v in sorted(self._meta_goals.items())},
            "type_to_meta": {k: list(v) for k, v in sorted(self._type_to_meta.items())},
        }


class HierarchyScorer:
    """Computes meta-goal factors for the planner scoring chain.

    Produces a multiplicative factor in [0.9, 1.1] based on
    meta-goal aggregation of child reinforcements.

    Requires GoalMemory and ReinforcementScorer to compute child
    reinforcement signals from historical records.
    """

    def __init__(
        self,
        *,
        hierarchy: GoalHierarchy | None = None,
        goal_memory: GoalMemory | None = None,
        reinforcement_scorer: ReinforcementScorer | None = None,
        enabled: bool = False,
    ) -> None:
        self._hierarchy = hierarchy
        self._goal_memory = goal_memory
        self._reinforcement_scorer = reinforcement_scorer
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def hierarchy(self) -> GoalHierarchy | None:
        return self._hierarchy

    @property
    def goal_memory(self) -> GoalMemory | None:
        return self._goal_memory

    @property
    def reinforcement_scorer(self) -> ReinforcementScorer | None:
        return self._reinforcement_scorer

    def compute_factor(
        self,
        *,
        goal_type: str = "",
    ) -> HierarchyInfluence:
        """Compute hierarchy-based scoring factor. Pure, no side effects."""
        if not self._enabled or self._hierarchy is None:
            return HierarchyInfluence(
                factor=1.0,
                meta_goal_scores={},
                contributing_types=[],
                reason="hierarchy scoring disabled",
            )

        if not goal_type:
            return HierarchyInfluence(
                factor=1.0,
                meta_goal_scores={},
                contributing_types=[],
                reason="no goal type specified",
            )

        meta_names = self._hierarchy.get_meta_goals_for_type(goal_type)
        if not meta_names:
            return HierarchyInfluence(
                factor=1.0,
                meta_goal_scores={},
                contributing_types=[],
                reason=f"goal type '{goal_type}' not in any meta-goal",
            )

        child_reinforcements = self._compute_child_reinforcements()

        meta_scores: dict[str, float] = {}
        contributing_types: list[str] = []
        total_bias = 0.0
        count = 0

        for meta_name in meta_names:
            meta = self._hierarchy.get_meta_goal(meta_name)
            if meta is None:
                continue

            result = self._hierarchy.compute_meta_score(meta_name, child_reinforcements)
            if result is None or result.total_records == 0:
                continue

            meta_scores[meta_name] = result.score
            contributing_types.extend(
                ct for ct in result.child_scores if ct not in contributing_types
            )

            bias = (result.score - 1.0) * meta.weight
            total_bias += bias
            count += 1

        if count == 0:
            return HierarchyInfluence(
                factor=1.0,
                meta_goal_scores=meta_scores,
                contributing_types=contributing_types,
                reason="no meta-goal data available",
            )

        avg_bias = total_bias / count
        factor = max(
            _MIN_META_FACTOR,
            min(_MAX_META_FACTOR, 1.0 + avg_bias),
        )

        reason = self._build_reason(meta_scores, contributing_types, factor)

        return HierarchyInfluence(
            factor=factor,
            meta_goal_scores=meta_scores,
            contributing_types=contributing_types,
            reason=reason,
        )

    def collect_meta_scores(
        self,
        *,
        goal_type: str = "",
    ) -> dict[str, float]:
        """Collect all meta-goal scores relevant to a goal type.

        Returns a dict of meta_goal_name → aggregated score.
        Used as input dimensions for tradeoff resolution.
        """
        if not self._enabled or self._hierarchy is None or not goal_type:
            return {}

        meta_names = self._hierarchy.get_meta_goals_for_type(goal_type)
        if not meta_names:
            return {}

        child_reinforcements = self._compute_child_reinforcements()
        scores: dict[str, float] = {}

        for meta_name in meta_names:
            result = self._hierarchy.compute_meta_score(meta_name, child_reinforcements)
            if result is not None and result.total_records > 0:
                scores[meta_name] = result.score

        return scores

    def _compute_child_reinforcements(self) -> dict[str, float]:
        """Compute reinforcement signals for all known goal types."""
        if self._goal_memory is None or self._reinforcement_scorer is None:
            return {}

        result: dict[str, float] = {}
        for goal_type in self._goal_memory.get_types():
            stats = self._goal_memory.compute_stats(goal_type)
            if stats is not None:
                signal = self._reinforcement_scorer.compute(stats)
                result[goal_type] = signal.reinforcement

        return result

    def _build_reason(
        self,
        meta_scores: dict[str, float],
        contributing_types: list[str],
        factor: float,
    ) -> str:
        parts: list[str] = []

        for name, score in sorted(meta_scores.items()):
            direction = "positive" if score > 1.0 else "negative" if score < 1.0 else "neutral"
            parts.append(f"'{name}': {direction} ({score:.4f})")

        if contributing_types:
            parts.append(f"types: {', '.join(sorted(contributing_types))}")

        direction = "boost" if factor > 1.0 else "penalty" if factor < 1.0 else "neutral"
        parts.append(f"net {direction}: {factor:.4f}")

        return "; ".join(parts) if parts else "no hierarchy influence"
