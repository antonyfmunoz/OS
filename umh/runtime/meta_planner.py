"""Meta-planner — multi-objective sequencing and long-horizon planning.

Generates sequences of objectives, evaluates cumulative discounted
value across steps, and selects the best sequence. Only the first
objective in the selected sequence is committed — "plan the horizon,
act on step one." Mirrors trajectory planning but at the goal level.

Supports dependency-aware generation and memory-informed scoring
when DependencyGraph and SequenceMemory are provided (opt-in).

Pure computation — no I/O, no subprocess, no state mutation.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import TYPE_CHECKING, Any

from umh.runtime.arbitration import (
    ArbitrationWeights,
    Objective,
    ObjectiveEvaluator,
    ObjectiveScore,
)

if TYPE_CHECKING:
    from umh.runtime.dependency import DependencyGraph
    from umh.runtime.goal_hierarchy import HierarchyScorer
    from umh.runtime.goals import GoalBiasScorer
    from umh.runtime.identity import IdentityScorer
    from umh.runtime.sequence_memory import SequenceMemory
    from umh.runtime.strategy_orchestrator import StrategyOrchestrationPolicy
    from umh.runtime.tradeoff import TradeoffScorer


_DEFAULT_DEPTH = 3
_MIN_DEPTH = 2
_MAX_DEPTH = 4
_DEFAULT_TOP_K = 3
_MIN_TOP_K = 2
_MAX_TOP_K = 6
_DEFAULT_DISCOUNT = 0.85
_MAX_SEQUENCES = 30


@dataclass(frozen=True)
class SequenceStep:
    """One step in an objective sequence with its score and discount."""

    step_index: int
    objective: Objective
    score: ObjectiveScore
    discount: float
    discounted_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "objective_id": self.objective.objective_id,
            "score": self.score.to_dict(),
            "discount": round(self.discount, 4),
            "discounted_score": round(self.discounted_score, 4),
        }


@dataclass(frozen=True)
class ObjectiveSequence:
    """A planned sequence of objectives with cumulative metrics."""

    steps: tuple[SequenceStep, ...]
    label: str
    total_score: float
    cumulative_effort: float

    @property
    def depth(self) -> int:
        return len(self.steps)

    @property
    def first_objective(self) -> Objective:
        return self.steps[0].objective

    @property
    def objectives(self) -> list[Objective]:
        return [s.objective for s in self.steps]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "depth": self.depth,
            "total_score": round(self.total_score, 4),
            "cumulative_effort": round(self.cumulative_effort, 4),
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass(frozen=True)
class MetaPlanResult:
    """Complete meta-planning decision with all evaluated sequences."""

    sequences: tuple[ObjectiveSequence, ...]
    selected: ObjectiveSequence
    next_objective: Objective
    reason: str
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequences_evaluated": len(self.sequences),
            "selected": self.selected.to_dict(),
            "next_objective": self.next_objective.to_dict(),
            "reason": self.reason,
            "depth": self.depth,
            "all_sequences": [s.to_dict() for s in self.sequences],
        }

    @property
    def explanation(self) -> list[str]:
        lines: list[str] = [
            f"Selected sequence '{self.selected.label}' "
            f"(score {self.selected.total_score:.4f}, depth {self.depth})",
            f"Next objective: {self.next_objective.objective_id} "
            f"— '{self.next_objective.description}'",
            self.reason,
        ]
        for seq in self.sequences:
            marker = ">>>" if seq.label == self.selected.label else "   "
            obj_ids = " → ".join(s.objective.objective_id for s in seq.steps)
            lines.append(
                f"{marker} {seq.label}: score={seq.total_score:.4f} "
                f"effort={seq.cumulative_effort:.2f} [{obj_ids}]"
            )
        return lines


@dataclass(frozen=True)
class MetaPlanWeights:
    """Weights for meta-plan sequence scoring."""

    score_weight: float = 0.70
    effort_weight: float = 0.30

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_weight": round(self.score_weight, 4),
            "effort_weight": round(self.effort_weight, 4),
        }


class SequenceGenerator:
    """Generates bounded permutations of objectives as candidate sequences.

    Takes the top K objectives (by single-step score), generates all
    permutations up to the specified depth, and caps total sequences.
    When a DependencyGraph is provided, sequences are sorted by
    dependency alignment (best-aligned first).
    """

    def __init__(
        self,
        *,
        evaluator: ObjectiveEvaluator | None = None,
        top_k: int = _DEFAULT_TOP_K,
        max_sequences: int = _MAX_SEQUENCES,
        dependency_graph: DependencyGraph | None = None,
    ) -> None:
        self._evaluator = evaluator or ObjectiveEvaluator()
        self._top_k = max(_MIN_TOP_K, min(_MAX_TOP_K, top_k))
        self._max_sequences = max(5, min(100, max_sequences))
        self._dep_graph = dependency_graph

    @property
    def evaluator(self) -> ObjectiveEvaluator:
        return self._evaluator

    @property
    def top_k(self) -> int:
        return self._top_k

    @property
    def max_sequences(self) -> int:
        return self._max_sequences

    @property
    def dependency_graph(self) -> DependencyGraph | None:
        return self._dep_graph

    def generate(
        self,
        objectives: list[Objective],
        depth: int = _DEFAULT_DEPTH,
    ) -> list[list[Objective]]:
        """Generate objective sequences of length `depth`.

        Selects top K objectives by score, generates permutations of
        length min(depth, len(top_k)), and caps at max_sequences.
        If a dependency graph is provided, sequences are sorted by
        dependency alignment score (best-aligned first).
        """
        depth = max(_MIN_DEPTH, min(_MAX_DEPTH, depth))

        if not objectives:
            return []

        scores = [(self._evaluator.score(o), o) for o in objectives]
        scores.sort(key=lambda x: (-x[0].total_score, x[1].objective_id))
        top = [obj for _, obj in scores[: self._top_k]]

        actual_depth = min(depth, len(top))

        sequences: list[list[Objective]] = []
        for perm in permutations(top, actual_depth):
            sequences.append(list(perm))

        if self._dep_graph is not None and self._dep_graph.edge_count > 0:
            sequences.sort(
                key=lambda s: (
                    -self._dep_graph.sequence_dependency_score([o.objective_id for o in s]),
                    s[0].objective_id if s else "",
                )
            )

        return sequences[: self._max_sequences]

    def label_sequence(
        self,
        index: int,
        sequence: list[Objective],
    ) -> str:
        """Generate a human-readable label for a sequence."""
        if not sequence:
            return f"sequence-{index}"

        first = sequence[0]
        parts: list[str] = []

        if first.priority >= 8:
            parts.append("high-priority-lead")
        elif first.priority >= 5:
            parts.append("moderate-lead")
        else:
            parts.append("low-priority-lead")

        if len(sequence) > 1:
            avg_priority = sum(o.priority for o in sequence[1:]) / len(sequence[1:])
            if avg_priority >= 7:
                parts.append("strong-follow")
            elif avg_priority >= 4:
                parts.append("balanced-follow")
            else:
                parts.append("easy-follow")

        return f"{'-'.join(parts)}-{index}"


_DEFAULT_DEP_WEIGHT = 0.15
_MIN_ADJUSTMENT = 0.5
_MAX_ADJUSTMENT = 1.5


class SequenceEvaluator:
    """Scores objective sequences using discounted objective scores.

    Score = Σ (objective_score * discount^step)

    When a dependency graph is provided, adds a dependency alignment
    bonus. When sequence memory is provided and learning is enabled,
    multiplies by a historical adjustment factor.

    Higher discount factor (closer to 1.0) values future objectives
    more; lower discount (closer to 0.5) focuses on near-term goals.
    """

    def __init__(
        self,
        *,
        evaluator: ObjectiveEvaluator | None = None,
        discount: float = _DEFAULT_DISCOUNT,
        weights: MetaPlanWeights | None = None,
        dependency_graph: DependencyGraph | None = None,
        sequence_memory: SequenceMemory | None = None,
        enable_learning: bool = False,
        dep_weight: float = _DEFAULT_DEP_WEIGHT,
        identity_scorer: IdentityScorer | None = None,
        goal_bias_scorer: GoalBiasScorer | None = None,
        hierarchy_scorer: HierarchyScorer | None = None,
        tradeoff_scorer: TradeoffScorer | None = None,
    ) -> None:
        self._evaluator = evaluator or ObjectiveEvaluator()
        self._discount = max(0.5, min(1.0, discount))
        w = weights or MetaPlanWeights()
        total = w.score_weight + w.effort_weight
        if total <= 0:
            total = 1.0
        self._w_score = w.score_weight / total
        self._w_effort = w.effort_weight / total
        self._dep_graph = dependency_graph
        self._seq_memory = sequence_memory
        self._enable_learning = enable_learning
        self._dep_weight = max(0.0, min(0.5, dep_weight))
        self._identity_scorer = identity_scorer
        self._goal_bias_scorer = goal_bias_scorer
        self._hierarchy_scorer = hierarchy_scorer
        self._tradeoff_scorer = tradeoff_scorer

    @property
    def evaluator(self) -> ObjectiveEvaluator:
        return self._evaluator

    @property
    def discount(self) -> float:
        return self._discount

    @property
    def weights(self) -> MetaPlanWeights:
        return MetaPlanWeights(
            score_weight=self._w_score,
            effort_weight=self._w_effort,
        )

    @property
    def dependency_graph(self) -> DependencyGraph | None:
        return self._dep_graph

    @property
    def sequence_memory(self) -> SequenceMemory | None:
        return self._seq_memory

    @property
    def identity_scorer(self) -> IdentityScorer | None:
        return self._identity_scorer

    @property
    def goal_bias_scorer(self) -> GoalBiasScorer | None:
        return self._goal_bias_scorer

    @property
    def hierarchy_scorer(self) -> HierarchyScorer | None:
        return self._hierarchy_scorer

    @property
    def tradeoff_scorer(self) -> TradeoffScorer | None:
        return self._tradeoff_scorer

    @property
    def learning_enabled(self) -> bool:
        return self._enable_learning

    def score_sequence(
        self,
        sequence: list[Objective],
        label: str = "",
    ) -> ObjectiveSequence:
        """Score a sequence of objectives with temporal discounting. Pure."""
        steps: list[SequenceStep] = []
        total_discounted = 0.0
        cum_effort = 0.0

        for i, obj in enumerate(sequence):
            obj_score = self._evaluator.score(obj)
            disc = self._discount**i
            discounted = obj_score.total_score * disc
            total_discounted += discounted
            cum_effort += obj.effort_estimate

            steps.append(
                SequenceStep(
                    step_index=i,
                    objective=obj,
                    score=obj_score,
                    discount=disc,
                    discounted_score=discounted,
                )
            )

        effort_score = 1.0 / (1.0 + cum_effort)
        combined = self._w_score * total_discounted + self._w_effort * effort_score

        if self._dep_graph is not None and len(sequence) >= 2:
            ids = [o.objective_id for o in sequence]
            dep_score = self._dep_graph.sequence_dependency_score(ids)
            combined += self._dep_weight * dep_score

        if self._enable_learning and self._seq_memory is not None:
            ids = [o.objective_id for o in sequence]
            adjustment = self._seq_memory.compute_adjustment_factor(ids)
            combined *= max(_MIN_ADJUSTMENT, min(_MAX_ADJUSTMENT, adjustment))

        if self._identity_scorer is not None:
            avg_effort = cum_effort / len(sequence) if sequence else 1.0
            avg_priority = sum(o.priority for o in sequence) / len(sequence) if sequence else 5.0
            influence = self._identity_scorer.compute_factor(
                sequence_length=len(sequence),
                avg_effort=avg_effort,
                avg_priority=avg_priority,
            )
            combined *= influence.factor

        if self._goal_bias_scorer is not None and sequence:
            goal_type = sequence[0].metadata.get("goal_type", "")
            goal_weight = sequence[0].metadata.get("goal_weight", 1.0)
            bias_influence = self._goal_bias_scorer.compute_factor(
                goal_type=goal_type,
                goal_weight=goal_weight if isinstance(goal_weight, (int, float)) else 1.0,
            )
            combined *= bias_influence.factor

        if self._hierarchy_scorer is not None and sequence:
            goal_type = sequence[0].metadata.get("goal_type", "")
            hierarchy_influence = self._hierarchy_scorer.compute_factor(
                goal_type=goal_type,
            )
            combined *= hierarchy_influence.factor

        if self._tradeoff_scorer is not None and sequence:
            goal_type = sequence[0].metadata.get("goal_type", "")
            meta_scores: dict[str, float] = {}
            if self._hierarchy_scorer is not None and goal_type:
                meta_scores = self._hierarchy_scorer.collect_meta_scores(
                    goal_type=goal_type,
                )
            if meta_scores:
                cid = sequence[0].objective_id if sequence else ""
                tradeoff_influence = self._tradeoff_scorer.compute_factor(
                    meta_goal_scores=meta_scores,
                    candidate_id=cid,
                )
                combined *= tradeoff_influence.factor

        return ObjectiveSequence(
            steps=tuple(steps),
            label=label,
            total_score=combined,
            cumulative_effort=cum_effort,
        )

    def rank(self, sequences: list[ObjectiveSequence]) -> list[ObjectiveSequence]:
        """Rank sequences by total_score (highest first). Deterministic."""
        ranked = sorted(sequences, key=lambda s: (-s.total_score, s.label))
        return ranked


class MetaPlanner:
    """End-to-end meta-planning: generate → evaluate → rank → select.

    Combines SequenceGenerator and SequenceEvaluator. Returns the
    best sequence; the caller should extract .next_objective for
    immediate commitment. "Plan the horizon, act on step one."

    When dependency graph and sequence memory are provided, uses
    dependency-aware generation and history-informed scoring.
    """

    def __init__(
        self,
        *,
        generator: SequenceGenerator | None = None,
        sequence_evaluator: SequenceEvaluator | None = None,
        dependency_graph: DependencyGraph | None = None,
        sequence_memory: SequenceMemory | None = None,
        identity_scorer: IdentityScorer | None = None,
        goal_bias_scorer: GoalBiasScorer | None = None,
        hierarchy_scorer: HierarchyScorer | None = None,
        tradeoff_scorer: TradeoffScorer | None = None,
        orchestration_policy: StrategyOrchestrationPolicy | None = None,
    ) -> None:
        self._generator = generator or SequenceGenerator()
        self._evaluator = sequence_evaluator or SequenceEvaluator()
        self._dep_graph = dependency_graph
        self._seq_memory = sequence_memory
        self._identity_scorer = identity_scorer
        self._goal_bias_scorer = goal_bias_scorer
        self._hierarchy_scorer = hierarchy_scorer
        self._tradeoff_scorer = tradeoff_scorer
        self._orchestration_policy = orchestration_policy

    @property
    def generator(self) -> SequenceGenerator:
        return self._generator

    @property
    def sequence_evaluator(self) -> SequenceEvaluator:
        return self._evaluator

    @property
    def dependency_graph(self) -> DependencyGraph | None:
        return self._dep_graph

    @property
    def sequence_memory(self) -> SequenceMemory | None:
        return self._seq_memory

    @property
    def identity_scorer(self) -> IdentityScorer | None:
        return self._identity_scorer

    @property
    def goal_bias_scorer(self) -> GoalBiasScorer | None:
        return self._goal_bias_scorer

    @property
    def hierarchy_scorer(self) -> HierarchyScorer | None:
        return self._hierarchy_scorer

    @property
    def tradeoff_scorer(self) -> TradeoffScorer | None:
        return self._tradeoff_scorer

    @property
    def orchestration_policy(self) -> StrategyOrchestrationPolicy | None:
        return self._orchestration_policy

    def plan(
        self,
        objectives: list[Objective],
        *,
        depth: int = _DEFAULT_DEPTH,
        regime_factors: dict[str, float] | None = None,
        feedback_factors: dict[str, float] | None = None,
        confidences: dict[str, float] | None = None,
    ) -> MetaPlanResult | None:
        """Generate, evaluate, and select the best objective sequence.

        When orchestration_policy is set and regime/feedback data is
        provided, uses orchestrate_selection for final sequence ranking.
        Otherwise preserves original scoring-only logic exactly.
        """
        if not objectives:
            return None

        raw_sequences = self._generator.generate(objectives, depth)
        if not raw_sequences:
            return None

        scored: list[ObjectiveSequence] = []
        for i, seq in enumerate(raw_sequences):
            label = self._generator.label_sequence(i, seq)
            evaluated = self._evaluator.score_sequence(seq, label=label)
            scored.append(evaluated)

        ranked = self._evaluator.rank(scored)

        if self._orchestration_policy is not None and ranked:
            selected = self._orchestrated_select(
                ranked, regime_factors, feedback_factors, confidences
            )
        else:
            selected = ranked[0]

        next_obj = selected.first_objective

        reason = self._build_reason(selected, ranked)

        return MetaPlanResult(
            sequences=tuple(ranked),
            selected=selected,
            next_objective=next_obj,
            reason=reason,
            depth=selected.depth,
        )

    def _orchestrated_select(
        self,
        ranked: list[ObjectiveSequence],
        regime_factors: dict[str, float] | None,
        feedback_factors: dict[str, float] | None,
        confidences: dict[str, float] | None,
    ) -> ObjectiveSequence:
        from umh.runtime.strategy_orchestrator import orchestrate_selection

        policy = self._orchestration_policy
        ids = [s.label for s in ranked]
        base_scores = [s.total_score for s in ranked]
        rf = [regime_factors.get(s.label, 1.0) for s in ranked] if regime_factors else None
        ff = [feedback_factors.get(s.label, 1.0) for s in ranked] if feedback_factors else None
        cf = [confidences.get(s.label, 0.0) for s in ranked] if confidences else None

        result = orchestrate_selection(
            strategy_ids=ids,
            base_scores=base_scores,
            regime_factors=rf,
            feedback_factors=ff,
            confidences=cf,
            policy=policy,
        )

        if result.selected_strategy:
            for seq in ranked:
                if seq.label == result.selected_strategy:
                    return seq

        return ranked[0]

    def _build_reason(
        self,
        selected: ObjectiveSequence,
        ranked: list[ObjectiveSequence],
    ) -> str:
        parts: list[str] = []

        first_step = selected.steps[0]
        if first_step.score.total_score >= 0.6:
            parts.append("strong first objective")
        elif first_step.score.total_score >= 0.4:
            parts.append("solid first objective")

        if selected.cumulative_effort < 3.0:
            parts.append("manageable total effort")
        elif selected.cumulative_effort < 6.0:
            parts.append("moderate total effort")
        else:
            parts.append("high total effort")

        if self._dep_graph is not None and selected.depth >= 2:
            ids = [s.objective.objective_id for s in selected.steps]
            dep_score = self._dep_graph.sequence_dependency_score(ids)
            if dep_score > 0.3:
                parts.append(f"strong dependency alignment ({dep_score:.2f})")
            elif dep_score > 0.0:
                parts.append(f"partial dependency alignment ({dep_score:.2f})")

        if self._seq_memory is not None:
            ids = [s.objective.objective_id for s in selected.steps]
            rate = self._seq_memory.get_success_rate(ids)
            if rate is not None:
                parts.append(f"historical success rate {rate:.0%}")

        if len(ranked) > 1:
            runner = ranked[1]
            margin = selected.total_score - runner.total_score
            if margin < 0.02:
                parts.append(f"narrow margin over '{runner.label}' ({margin:.4f})")

        if self._identity_scorer is not None and self._identity_scorer.enabled:
            store = self._identity_scorer.identity_store
            if store is not None and store.update_count > 0:
                profile = store.get_profile()
                dominant = max(profile.traits.items(), key=lambda x: abs(x[1] - 0.5), default=None)
                if dominant is not None:
                    trait_name, trait_val = dominant
                    direction = "high" if trait_val > 0.5 else "low"
                    parts.append(f"identity: {direction} {trait_name} ({trait_val:.2f})")

        if self._goal_bias_scorer is not None and self._goal_bias_scorer.enabled:
            first_obj = selected.steps[0].objective
            goal_type = first_obj.metadata.get("goal_type", "")
            if goal_type:
                bias = self._goal_bias_scorer.compute_factor(goal_type=goal_type)
                if abs(bias.factor - 1.0) > 0.001:
                    direction = "boosted" if bias.factor > 1.0 else "penalized"
                    parts.append(f"goal bias: {direction} '{goal_type}' ({bias.factor:.4f})")

        if self._hierarchy_scorer is not None and self._hierarchy_scorer.enabled:
            first_obj = selected.steps[0].objective
            goal_type = first_obj.metadata.get("goal_type", "")
            if goal_type:
                h_influence = self._hierarchy_scorer.compute_factor(goal_type=goal_type)
                if abs(h_influence.factor - 1.0) > 0.001:
                    direction = "boosted" if h_influence.factor > 1.0 else "penalized"
                    meta_names = list(h_influence.meta_goal_scores.keys())
                    meta_str = ", ".join(meta_names[:3]) if meta_names else "none"
                    parts.append(
                        f"hierarchy: {direction} via [{meta_str}] ({h_influence.factor:.4f})"
                    )

        if self._tradeoff_scorer is not None and self._tradeoff_scorer.enabled:
            first_obj = selected.steps[0].objective
            goal_type = first_obj.metadata.get("goal_type", "")
            if goal_type and self._hierarchy_scorer is not None:
                meta_scores = self._hierarchy_scorer.collect_meta_scores(
                    goal_type=goal_type,
                )
                if meta_scores:
                    cid = first_obj.objective_id
                    t_influence = self._tradeoff_scorer.compute_factor(
                        meta_goal_scores=meta_scores,
                        candidate_id=cid,
                    )
                    if abs(t_influence.factor - 1.0) > 0.001:
                        direction = "boosted" if t_influence.factor > 1.0 else "penalized"
                        parts.append(f"tradeoff: {direction} ({t_influence.factor:.4f})")

        if selected.depth >= 3:
            parts.append(f"plans {selected.depth} steps ahead")

        return "; ".join(parts) if parts else "best overall sequence score"
