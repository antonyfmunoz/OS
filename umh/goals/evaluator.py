"""
GoalEvaluator — deterministic per-turn goal progress measurement.

Computes a goal_score (0.0–1.0) that measures how well the current
turn's output aligns with the session goal. Tracks delta vs previous
turn to detect progress, regression, or stagnation.

Feeds into:
    - DecisionTrace (observability)
    - ConvergenceEngine (trajectory stability)
    - StrategyMemory (reinforcement weighting)
    - UnifiedInfluence (progress signal)

No LLM calls. No randomness. Pure function of trace + goal_state.

Usage::

    from umh.goals.evaluator import GoalEvaluator, GoalEvaluation

    evaluator = GoalEvaluator()
    evaluation = evaluator.evaluate(trace, goal_state, prev_evaluation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.decision.trace import DecisionTrace
    from umh.goals.state import GoalState

NEUTRAL_SCORE = 0.5
NEUTRAL_CONFIDENCE = 0.0


@dataclass(frozen=True)
class GoalEvaluation:
    """Immutable record of goal progress for a single turn."""

    goal_score: float
    delta: float
    confidence: float
    signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "goal_score": round(self.goal_score, 4),
            "delta": round(self.delta, 4),
            "confidence": round(self.confidence, 4),
            "signals": self.signals,
        }


NO_GOAL_EVAL = GoalEvaluation(
    goal_score=NEUTRAL_SCORE,
    delta=0.0,
    confidence=NEUTRAL_CONFIDENCE,
    signals={},
)


class GoalEvaluator:
    """Deterministic goal progress evaluator.

    Computes goal_score from trace signals and goal criteria.
    Tracks delta from previous evaluation to detect trajectory.
    """

    def evaluate(
        self,
        trace: DecisionTrace,
        goal_state: GoalState,
        prev: GoalEvaluation | None = None,
    ) -> GoalEvaluation:
        """Evaluate goal progress for the current turn.

        Components of goal_score (all deterministic):
            1. criteria_match — how well trace context matches goal criteria
            2. quality_alignment — quality score weighted by goal priority
            3. strategy_affinity — whether the selected strategy aligns

        Returns NO_GOAL_EVAL when goal is inactive.
        """
        if not goal_state.active:
            return NO_GOAL_EVAL

        signals: dict = {}

        criteria_match = self._score_criteria_match(trace, goal_state)
        signals["criteria_match"] = round(criteria_match, 4)

        quality_alignment = self._score_quality_alignment(trace, goal_state)
        signals["quality_alignment"] = round(quality_alignment, 4)

        strategy_affinity = self._score_strategy_affinity(trace, goal_state)
        signals["strategy_affinity"] = round(strategy_affinity, 4)

        w_criteria = 0.4
        w_quality = 0.35
        w_strategy = 0.25

        goal_score = (
            criteria_match * w_criteria
            + quality_alignment * w_quality
            + strategy_affinity * w_strategy
        )
        goal_score = max(0.0, min(1.0, goal_score))

        prev_score = prev.goal_score if prev is not None else NEUTRAL_SCORE
        delta = goal_score - prev_score

        confidence = self._compute_confidence(trace, goal_state, signals)

        return GoalEvaluation(
            goal_score=goal_score,
            delta=delta,
            confidence=confidence,
            signals=signals,
        )

    def _score_criteria_match(
        self,
        trace: DecisionTrace,
        goal_state: GoalState,
    ) -> float:
        """Score how well the trace's evaluation context matches goal criteria."""
        from umh.goals.state import compute_goal_relevance

        context: dict = {}
        eval_signals = trace.signals or {}
        context.update(eval_signals.get("context", {}))

        flags = eval_signals.get("flags", {})
        if flags.get("hallucination_risk"):
            context["hallucination"] = True

        return compute_goal_relevance(goal_state, context)

    def _score_quality_alignment(
        self,
        trace: DecisionTrace,
        goal_state: GoalState,
    ) -> float:
        """Quality score weighted by goal priority.

        High priority goals demand higher quality. The score is the
        trace quality normalized against priority-scaled expectations.
        """
        q = trace.quality_score
        p = goal_state.priority

        expected = 0.3 + (p * 0.4)
        if expected <= 0:
            return q

        return min(q / expected, 1.0)

    def _score_strategy_affinity(
        self,
        trace: DecisionTrace,
        goal_state: GoalState,
    ) -> float:
        """Score how well the selected strategy aligns with the goal."""
        from umh.goals.state import strategy_goal_score

        strategy = trace.selected_strategy
        if not strategy:
            return 0.5

        return strategy_goal_score(strategy, goal_state)

    def _compute_confidence(
        self,
        trace: DecisionTrace,
        goal_state: GoalState,
        signals: dict,
    ) -> float:
        """Confidence in the goal_score based on data availability.

        Higher when: more criteria matched, trace has high confidence,
        strategy is known.
        """
        components: list[float] = []

        components.append(min(trace.confidence, 1.0))

        criteria_count = len(goal_state.success_criteria)
        if criteria_count > 0:
            matched = sum(
                1
                for k in goal_state.success_criteria
                if k in (trace.signals or {}).get("context", {})
            )
            components.append(matched / criteria_count)
        else:
            components.append(0.3)

        if trace.selected_strategy:
            components.append(0.8)
        else:
            components.append(0.3)

        if not components:
            return 0.0

        return sum(components) / len(components)
