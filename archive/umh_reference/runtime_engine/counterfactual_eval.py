"""
CounterfactualEvaluator — pre-activation utility projection for goals.

Previous behavior: GoalAlignmentEvaluator scores goals based on observed
historical signals. No mechanism to estimate expected utility *before*
a goal is activated and consumes resources.

This module projects expected utility from existing data:

    A. Similar goal trajectories — Jaccard-matched historical goals
    B. Parent performance trend — EMA + delta forward projection
    C. Strategy affinity — strategy success on similar criteria
    D. Resource projection — estimated cost vs expected return

CounterfactualResult carries:
    - expected_utility (0.0–1.0)
    - expected_delta (projected change, can be negative)
    - confidence (0.0–1.0, how trustworthy the projection is)
    - reasoning (deterministic explanation string)

Sits between GoalValidator and GoalAlignmentEvaluator in the pipeline.
Does NOT block goals — only modifies confidence and provides a multiplier
for downstream alignment scoring.

No LLM calls. No randomness. No simulation branching.
Pure projection from existing signals.

Usage::

    from umh.runtime_engine.counterfactual_eval import CounterfactualEvaluator

    cf = CounterfactualEvaluator()
    result = cf.evaluate_counterfactual(meta_goal, registry, traces)
    # result.expected_utility modifies alignment weighting
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.decision_trace import DecisionTrace
    from umh.goals.state import GoalRegistry
    from umh.runtime_engine.meta_goal import MetaGoal

_log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

SIMILARITY_MATCH_THRESHOLD = 0.50
TREND_PROJECTION_WINDOW = 10
STRATEGY_AFFINITY_WINDOW = 10
RESOURCE_PROJECTION_WINDOW = 10

LOW_UTILITY_THRESHOLD = 0.30
HIGH_UTILITY_THRESHOLD = 0.70

UNCERTAINTY_WEIGHT = 0.3
HORIZON_WEIGHT = 0.25
COMMITMENT_WEIGHT = 0.05
COMMITMENT_CAP = 0.3

CONFIDENCE_FLOOR = 0.1
CONFIDENCE_NO_DATA = 0.2

HORIZON_TRACE_WINDOW = 10
HORIZON_ENABLEMENT_MIN_USES = 2
HORIZON_DELAYED_PAYOFF_WINDOW = 5
HIGH_QUALITY_THRESHOLD = 0.65

# Signal weights (sum to 1.0)
W_SIMILAR = 0.30
W_TREND = 0.30
W_STRATEGY = 0.20
W_RESOURCE = 0.20


# ─── Data model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CounterfactualResult:
    """Projected utility of a goal before activation."""

    expected_utility: float
    expected_delta: float
    confidence: float
    reasoning: str
    horizon_value: float = 0.0
    horizon_reason: str = ""
    commitment_bonus: float = 0.0

    @property
    def uncertainty(self) -> float:
        """Epistemic uncertainty: 1.0 - confidence."""
        return 1.0 - self.confidence

    @property
    def exploration_boost(self) -> float:
        """Exploration pressure from uncertainty: uncertainty * UNCERTAINTY_WEIGHT."""
        return self.uncertainty * UNCERTAINTY_WEIGHT

    @property
    def effective_utility(self) -> float:
        """Utility adjusted for exploration + horizon + commitment: clamped to [0.0, 1.0]."""
        raw = (
            self.expected_utility
            + self.exploration_boost
            + HORIZON_WEIGHT * self.horizon_value
            + self.commitment_bonus
        )
        return max(0.0, min(1.0, raw))

    def to_dict(self) -> dict:
        d = {
            "expected_utility": round(self.expected_utility, 4),
            "expected_delta": round(self.expected_delta, 4),
            "confidence": round(self.confidence, 4),
            "uncertainty": round(self.uncertainty, 4),
            "exploration_boost": round(self.exploration_boost, 4),
            "horizon_value": round(self.horizon_value, 4),
            "commitment_bonus": round(self.commitment_bonus, 4),
            "effective_utility": round(self.effective_utility, 4),
            "reasoning": self.reasoning,
        }
        if self.horizon_reason:
            d["horizon_reason"] = self.horizon_reason
        return d


# ─── Evaluator ───────────────────────────────────────────────────────────────


class CounterfactualEvaluator:
    """Deterministic pre-activation utility projector.

    Estimates expected utility from 4 signal channels using only
    existing runtime data. No LLM calls, no randomness.
    """

    def evaluate_counterfactual(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list | None = None,
    ) -> CounterfactualResult:
        """Project expected utility for a goal before activation.

        Returns CounterfactualResult. Does not block — only informs
        downstream alignment scoring.
        """
        traces = traces or []
        reasons: list[str] = []
        confidences: list[float] = []

        # ── Signal A: Similar goal trajectories ────────────────────
        sim_utility, sim_conf = self._project_similar_goals(meta_goal, registry)
        confidences.append(sim_conf)
        if sim_conf > CONFIDENCE_NO_DATA:
            reasons.append(f"similar_goals:{sim_utility:.2f}")

        # ── Signal B: Parent performance trend ─────────────────────
        trend_utility, trend_delta, trend_conf = self._project_parent_trend(
            meta_goal, registry
        )
        confidences.append(trend_conf)
        if trend_conf > CONFIDENCE_NO_DATA:
            reasons.append(f"parent_trend:{trend_utility:.2f}")

        # ── Signal C: Strategy affinity ────────────────────────────
        strat_utility, strat_conf = self._project_strategy_affinity(meta_goal, traces)
        confidences.append(strat_conf)
        if strat_conf > CONFIDENCE_NO_DATA:
            reasons.append(f"strategy_affinity:{strat_utility:.2f}")

        # ── Signal D: Resource projection ──────────────────────────
        resource_utility, resource_conf = self._project_resource_efficiency(
            meta_goal, registry, traces
        )
        confidences.append(resource_conf)
        if resource_conf > CONFIDENCE_NO_DATA:
            reasons.append(f"resource_projection:{resource_utility:.2f}")

        # ── Weighted expected utility ──────────────────────────────
        expected_utility = (
            W_SIMILAR * sim_utility
            + W_TREND * trend_utility
            + W_STRATEGY * strat_utility
            + W_RESOURCE * resource_utility
        )
        expected_utility = max(0.0, min(1.0, expected_utility))

        # ── Aggregate confidence ───────────────────────────────────
        confidence = (
            sum(confidences) / len(confidences) if confidences else CONFIDENCE_FLOOR
        )
        confidence = max(CONFIDENCE_FLOOR, min(1.0, confidence))

        # ── Expected delta from trend ──────────────────────────────
        expected_delta = trend_delta

        # ── Signal E: Horizon value (downstream payoff) ────────────
        horizon_value, horizon_reasons = self._compute_horizon_value(
            meta_goal, registry, traces
        )
        if horizon_reasons:
            reasons.append(f"horizon:{horizon_value:.2f}")

        # ── Signal F: Commitment bonus (persistence pressure) ─────
        _commitment = 0.0
        _tracker = registry.get_tracker(meta_goal.goal_id)
        if _tracker is not None and _tracker.persistence_streak > 0:
            _commitment = min(
                _tracker.persistence_streak * COMMITMENT_WEIGHT, COMMITMENT_CAP
            )
            reasons.append(f"commitment:{_commitment:.2f}")

        # ── Deterministic reasoning ────────────────────────────────
        if not reasons:
            reasoning = "no_data:neutral_projection"
        else:
            reasoning = "|".join(reasons)

        return CounterfactualResult(
            expected_utility=expected_utility,
            expected_delta=expected_delta,
            confidence=confidence,
            reasoning=reasoning,
            horizon_value=horizon_value,
            horizon_reason="|".join(horizon_reasons) if horizon_reasons else "",
            commitment_bonus=_commitment,
        )

    # ── Signal A: Similar goal trajectories ───────────────────────────────

    def _project_similar_goals(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> tuple[float, float]:
        """Find historical goals with similar criteria and project utility.

        Returns (projected_utility, confidence).
        Uses Jaccard similarity on success_criteria.
        """
        from umh.runtime_engine.goal_validator import _criteria_similarity

        existing = registry.get_all_goals()
        if not existing:
            return 0.5, CONFIDENCE_NO_DATA

        matches: list[tuple[float, float]] = []

        for eg in existing:
            if eg.goal_id == meta_goal.goal_id:
                continue
            sim = _criteria_similarity(meta_goal.success_criteria, eg.success_criteria)
            if sim >= SIMILARITY_MATCH_THRESHOLD:
                tracker = registry.get_tracker(eg.goal_id)
                if tracker is not None and tracker.uses > 0:
                    matches.append((sim, tracker.success_score))

        if not matches:
            return 0.5, CONFIDENCE_NO_DATA

        total_weight = sum(sim for sim, _ in matches)
        projected = sum(sim * score for sim, score in matches) / total_weight

        match_confidence = min(1.0, len(matches) * 0.25 + 0.3)

        return projected, match_confidence

    # ── Signal B: Parent performance trend ────────────────────────────────

    def _project_parent_trend(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> tuple[float, float, float]:
        """Project utility from parent goal's EMA trend.

        Returns (projected_utility, projected_delta, confidence).
        Projects forward by extending the recent delta trend.
        """
        if not meta_goal.parent_goals:
            return 0.5, 0.0, CONFIDENCE_NO_DATA

        best_utility = 0.0
        best_delta = 0.0
        best_confidence = 0.0
        found = False

        for pid in meta_goal.parent_goals:
            tracker = registry.get_tracker(pid)
            if tracker is None or tracker.uses == 0:
                continue
            found = True

            history = tracker.delta_history[-TREND_PROJECTION_WINDOW:]
            current_score = tracker.success_score

            if history:
                recent_deltas = history[-5:] if len(history) >= 5 else history
                mean_delta = sum(recent_deltas) / len(recent_deltas)
                projected = current_score + mean_delta
                projected = max(0.0, min(1.0, projected))

                data_confidence = min(1.0, tracker.uses * 0.1 + 0.2)
                if projected > best_utility:
                    best_utility = projected
                    best_delta = mean_delta
                    best_confidence = data_confidence
            else:
                if current_score > best_utility:
                    best_utility = current_score
                    best_delta = 0.0
                    best_confidence = 0.3

        if not found:
            return 0.5, 0.0, CONFIDENCE_NO_DATA

        return best_utility, best_delta, best_confidence

    # ── Signal C: Strategy affinity ───────────────────────────────────────

    def _project_strategy_affinity(
        self,
        meta_goal: MetaGoal,
        traces: list,
    ) -> tuple[float, float]:
        """Estimate utility from strategy performance on similar criteria.

        Looks at recent traces where strategies operated on goals with
        similar criteria. Returns (projected_utility, confidence).
        """
        from umh.runtime_engine.goal_validator import _criteria_similarity

        recent = traces[-STRATEGY_AFFINITY_WINDOW:] if traces else []
        if not recent:
            return 0.5, CONFIDENCE_NO_DATA

        affinity_scores: list[float] = []

        for trace in recent:
            active_id = getattr(trace, "active_goal_id", None)
            pool = getattr(trace, "goal_pool_snapshot", None)
            quality = getattr(trace, "quality_score", None)

            if not active_id or quality is None:
                continue

            goal_criteria = None
            if pool and "goals" in pool:
                goal_info = pool["goals"].get(active_id)
                if goal_info:
                    goal_criteria = goal_info.get("success_criteria")

            if goal_criteria is None:
                continue

            sim = _criteria_similarity(meta_goal.success_criteria, goal_criteria)
            if sim >= SIMILARITY_MATCH_THRESHOLD:
                affinity_scores.append(quality)

        if not affinity_scores:
            return 0.5, CONFIDENCE_NO_DATA

        avg_quality = sum(affinity_scores) / len(affinity_scores)
        confidence = min(1.0, len(affinity_scores) * 0.2 + 0.3)

        return avg_quality, confidence

    # ── Signal D: Resource projection ─────────────────────────────────────

    def _project_resource_efficiency(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list,
    ) -> tuple[float, float]:
        """Estimate cost-efficiency for the new goal.

        Uses parent goals' budget consumption and success as a proxy
        for expected resource efficiency.

        Returns (projected_efficiency, confidence).
        """
        if not meta_goal.parent_goals:
            return 0.5, CONFIDENCE_NO_DATA

        from umh.runtime_engine.goal_alignment import _compute_budget_usage

        efficiencies: list[float] = []

        for pid in meta_goal.parent_goals:
            tracker = registry.get_tracker(pid)
            if tracker is None or tracker.uses < 2:
                continue

            budget_usage = _compute_budget_usage(pid, traces)

            if budget_usage > 0.0:
                efficiency = tracker.success_score / max(budget_usage, 0.01)
                efficiency = min(efficiency, 1.0)
            else:
                efficiency = tracker.success_score

            efficiencies.append(efficiency)

        if not efficiencies:
            return 0.5, CONFIDENCE_NO_DATA

        avg_eff = sum(efficiencies) / len(efficiencies)
        confidence = min(1.0, len(efficiencies) * 0.3 + 0.2)

        return avg_eff, confidence

    # ── Signal E: Temporal horizon value ─────────────────────────────────

    def _compute_horizon_value(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
        traces: list,
    ) -> tuple[float, list[str]]:
        """Compute downstream payoff projection from 4 sub-signals.

        Returns (horizon_value in [0.0, 1.0], list of contributing reasons).
        Each sub-signal returns a value in [0.0, 1.0]; we average those
        that produce signal (skip those with no data).
        """
        values: list[float] = []
        reasons: list[str] = []

        # A. Enablement: does this goal's parent historically spawn high-performing children?
        en = self._horizon_enablement(meta_goal, registry)
        if en is not None:
            values.append(en)
            reasons.append(f"enablement:{en:.2f}")

        # B. Transition probability: goal A → high-utility goal B in trace sequences
        tp = self._horizon_transition(meta_goal, traces)
        if tp is not None:
            values.append(tp)
            reasons.append(f"transition:{tp:.2f}")

        # C. Delayed payoff: low immediate but improving delta trend
        dp = self._horizon_delayed_payoff(meta_goal, registry)
        if dp is not None:
            values.append(dp)
            reasons.append(f"delayed_payoff:{dp:.2f}")

        # D. Goal graph expansion: does this goal introduce novel criteria?
        ge = self._horizon_graph_expansion(meta_goal, registry)
        if ge is not None:
            values.append(ge)
            reasons.append(f"expansion:{ge:.2f}")

        if not values:
            return 0.0, []

        horizon_value = sum(values) / len(values)
        horizon_value = max(0.0, min(1.0, horizon_value))
        return horizon_value, reasons

    def _horizon_enablement(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> float | None:
        """Signal A: Do goals parented by this goal's parents tend to perform well?

        If the parent(s) historically produce high-performing children,
        this new child is likely to benefit from the same enablement path.
        """
        if not meta_goal.parent_goals:
            return None

        child_scores: list[float] = []
        for goal in registry.get_all_goals():
            if goal.goal_id == meta_goal.goal_id:
                continue
            tracker = registry.get_tracker(goal.goal_id)
            if tracker is None or tracker.uses < HORIZON_ENABLEMENT_MIN_USES:
                continue
            goal_criteria = goal.success_criteria or {}
            if goal_criteria.get("_meta_origin") in ("specialization", "merged"):
                child_scores.append(tracker.success_score)

        if not child_scores:
            return None

        avg = sum(child_scores) / len(child_scores)
        return max(0.0, min(1.0, avg))

    def _horizon_transition(
        self,
        meta_goal: MetaGoal,
        traces: list,
    ) -> float | None:
        """Signal B: When goals with similar criteria are active, does the next turn perform well?

        Looks at sequential trace pairs where the active goal has similar
        criteria to the candidate. If the next trace shows high quality,
        it suggests this goal type enables strong follow-on performance.
        """
        from umh.runtime_engine.goal_validator import _criteria_similarity

        recent = traces[-HORIZON_TRACE_WINDOW:] if traces else []
        if len(recent) < 2:
            return None

        transition_scores: list[float] = []
        for i in range(len(recent) - 1):
            t_curr = recent[i]
            t_next = recent[i + 1]

            pool = getattr(t_curr, "goal_pool_snapshot", None)
            active_id = getattr(t_curr, "active_goal_id", None)
            next_quality = getattr(t_next, "quality_score", None)

            if not active_id or next_quality is None or not pool:
                continue

            goal_criteria = None
            if isinstance(pool, dict) and "goals" in pool:
                goal_info = pool["goals"]
                if isinstance(goal_info, dict):
                    gi = goal_info.get(active_id)
                    if gi and isinstance(gi, dict):
                        goal_criteria = gi.get("success_criteria")
                elif isinstance(goal_info, list):
                    for entry in goal_info:
                        if (
                            isinstance(entry, dict)
                            and entry.get("goal_id") == active_id
                        ):
                            goal_criteria = entry.get("success_criteria")
                            break

            if goal_criteria is None:
                continue

            sim = _criteria_similarity(meta_goal.success_criteria, goal_criteria)
            if (
                sim >= SIMILARITY_MATCH_THRESHOLD
                and next_quality >= HIGH_QUALITY_THRESHOLD
            ):
                transition_scores.append(next_quality)

        if not transition_scores:
            return None

        return sum(transition_scores) / len(transition_scores)

    def _horizon_delayed_payoff(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> float | None:
        """Signal C: Parent goals with low immediate utility but improving delta trend.

        If the parent started poorly but its recent deltas are trending
        positive, the child may benefit from a late-blooming trajectory.
        """
        if not meta_goal.parent_goals:
            return None

        payoff_scores: list[float] = []
        for pid in meta_goal.parent_goals:
            tracker = registry.get_tracker(pid)
            if tracker is None or tracker.uses < HORIZON_ENABLEMENT_MIN_USES:
                continue

            history = tracker.delta_history[-HORIZON_DELAYED_PAYOFF_WINDOW:]
            if len(history) < 2:
                continue

            first_half = history[: len(history) // 2]
            second_half = history[len(history) // 2 :]

            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)

            if avg_second > avg_first and avg_second > 0:
                improvement = min(1.0, (avg_second - avg_first) * 5.0)
                payoff_scores.append(improvement)

        if not payoff_scores:
            return None

        return sum(payoff_scores) / len(payoff_scores)

    def _horizon_graph_expansion(
        self,
        meta_goal: MetaGoal,
        registry: GoalRegistry,
    ) -> float | None:
        """Signal D: Does this goal introduce criteria not present in existing goals?

        Novel criteria keys/values expand the goal space, creating future
        diversity. Higher novelty → higher horizon value.
        """
        candidate_keys = (
            set(meta_goal.success_criteria.keys())
            if meta_goal.success_criteria
            else set()
        )
        if not candidate_keys:
            return None

        existing_keys: set[str] = set()
        for goal in registry.get_all_goals():
            if goal.goal_id == meta_goal.goal_id:
                continue
            if goal.success_criteria:
                existing_keys.update(goal.success_criteria.keys())

        if not existing_keys:
            return None

        novel_keys = candidate_keys - existing_keys
        if not novel_keys:
            return None

        novelty_ratio = len(novel_keys) / len(candidate_keys)
        return max(0.0, min(1.0, novelty_ratio))
