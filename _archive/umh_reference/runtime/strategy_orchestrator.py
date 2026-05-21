"""Regime-aware strategy orchestration — unified decision pipeline, multi-signal regime aggregation, adaptive dimension weighting, weighted decision influence, cross-dimension interactions, pattern influence.

Combines base scores, regime weights, optional feedback selection,
optional weighted decision influence, optional cross-dimension
interaction factors, and optional pattern influence into a single
deterministic selection.
Strict computation order:
base_score → regime_factor → feedback_factor (opt-in) → weight_factor (opt-in) → interaction_factor (opt-in) → pattern_factor (opt-in).

Default behavior is base + regime only (feedback, weights, interactions,
pattern influence disabled).
Optional AggregatedRegimeState attaches per-dimension context
to explainability without affecting scoring.
Optional DimensionWeightVector attaches adaptive dimension weights;
when WeightedDecisionPolicy.enabled, weights influence scoring.
Optional InteractionConfig enables cross-dimension interaction factors.
Optional PatternInfluenceConfig enables pattern-based scoring nudges (Phase 68).

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.runtime.feedback_selection import (
    FeedbackSelectionPolicy,
    FeedbackSelectionResult,
    select_with_feedback,
)

if TYPE_CHECKING:
    from umh.runtime.dimension_interactions import InteractionConfig, InteractionResult
    from umh.runtime.dimension_weighting import DimensionWeightVector
    from umh.runtime.pattern_aggregation import PatternAggregationResult
    from umh.runtime.pattern_influence import PatternInfluenceConfig, PatternInfluenceResult
    from umh.runtime.pattern_matching import PatternResult
    from umh.runtime.regime_aggregation import AggregatedRegimeState, DimensionRegime
    from umh.runtime.weighted_decision import (
        WeightedDecisionBatchResult,
        WeightedDecisionPolicy,
    )

_REGIME_FACTOR_MIN: float = 0.85
_REGIME_FACTOR_MAX: float = 1.15


@dataclass(frozen=True)
class StrategyOrchestrationPolicy:
    """Policy controlling the orchestration pipeline."""

    use_regime_weighting: bool = True
    use_feedback_selection: bool = False
    feedback_policy: FeedbackSelectionPolicy | None = None
    require_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "use_regime_weighting": self.use_regime_weighting,
            "use_feedback_selection": self.use_feedback_selection,
            "feedback_policy": self.feedback_policy.to_dict() if self.feedback_policy else None,
            "require_valid": self.require_valid,
        }


_INTERACTION_FACTOR_MIN: float = 0.9
_INTERACTION_FACTOR_MAX: float = 1.1
_PATTERN_FACTOR_MIN: float = 0.9
_PATTERN_FACTOR_MAX: float = 1.1


@dataclass(frozen=True)
class StrategyCandidate:
    """A strategy candidate with scoring layers."""

    strategy_id: str = ""
    base_score: float = 0.0
    regime_factor: float = 1.0
    feedback_factor: float = 1.0
    weight_factor: float = 1.0
    interaction_factor: float = 1.0
    pattern_factor: float = 1.0
    confidence: float = 0.0
    valid: bool = True
    safe: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_score", max(0.0, min(2.0, self.base_score)))
        object.__setattr__(
            self,
            "regime_factor",
            max(_REGIME_FACTOR_MIN, min(_REGIME_FACTOR_MAX, self.regime_factor)),
        )
        object.__setattr__(self, "feedback_factor", max(0.0, min(2.0, self.feedback_factor)))
        object.__setattr__(self, "weight_factor", max(0.5, min(1.5, self.weight_factor)))
        object.__setattr__(
            self,
            "interaction_factor",
            max(_INTERACTION_FACTOR_MIN, min(_INTERACTION_FACTOR_MAX, self.interaction_factor)),
        )
        object.__setattr__(
            self,
            "pattern_factor",
            max(_PATTERN_FACTOR_MIN, min(_PATTERN_FACTOR_MAX, self.pattern_factor)),
        )
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    @property
    def regime_adjusted_score(self) -> float:
        return self.base_score * self.regime_factor

    @property
    def final_score(self) -> float:
        return (
            self.base_score
            * self.regime_factor
            * self.feedback_factor
            * self.weight_factor
            * self.interaction_factor
            * self.pattern_factor
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "base_score": round(self.base_score, 4),
            "regime_factor": round(self.regime_factor, 4),
            "feedback_factor": round(self.feedback_factor, 4),
            "weight_factor": round(self.weight_factor, 4),
            "interaction_factor": round(self.interaction_factor, 4),
            "pattern_factor": round(self.pattern_factor, 4),
            "confidence": round(self.confidence, 4),
            "regime_adjusted_score": round(self.regime_adjusted_score, 4),
            "final_score": round(self.final_score, 4),
            "valid": self.valid,
            "safe": self.safe,
        }


@dataclass(frozen=True)
class StrategySelectionResult:
    """Result of strategy orchestration."""

    selected_strategy: str = ""
    candidates: tuple[StrategyCandidate, ...] = ()
    explanation: str = ""
    used_regime: bool = False
    used_feedback: bool = False
    used_weights: bool = False
    used_interactions: bool = False
    used_pattern: bool = False
    base_winner: str = ""
    regime_winner: str = ""
    feedback_winner: str = ""
    weight_winner: str = ""
    interaction_winner: str = ""
    pattern_winner: str = ""
    changed_from_base: bool = False
    changed_from_regime: bool = False
    changed_from_feedback: bool = False
    changed_from_weights: bool = False
    changed_from_interactions: bool = False
    aggregated_regime: AggregatedRegimeState | None = None
    dimension_weights: DimensionWeightVector | None = None
    weighted_decision: WeightedDecisionBatchResult | None = None
    interaction_result: InteractionResult | None = None
    pattern_influence_result: PatternInfluenceResult | None = None
    pattern_aggregation_result: PatternAggregationResult | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "selected_strategy": self.selected_strategy,
            "candidates": [c.to_dict() for c in self.candidates],
            "explanation": self.explanation,
            "used_regime": self.used_regime,
            "used_feedback": self.used_feedback,
            "used_weights": self.used_weights,
            "used_interactions": self.used_interactions,
            "used_pattern": self.used_pattern,
            "base_winner": self.base_winner,
            "regime_winner": self.regime_winner,
            "feedback_winner": self.feedback_winner,
            "weight_winner": self.weight_winner,
            "interaction_winner": self.interaction_winner,
            "pattern_winner": self.pattern_winner,
            "changed_from_base": self.changed_from_base,
            "changed_from_regime": self.changed_from_regime,
            "changed_from_feedback": self.changed_from_feedback,
            "changed_from_weights": self.changed_from_weights,
            "changed_from_interactions": self.changed_from_interactions,
        }
        if self.aggregated_regime is not None:
            d["aggregated_regime"] = self.aggregated_regime.to_dict()
        if self.dimension_weights is not None:
            d["dimension_weights"] = self.dimension_weights.to_dict()
        if self.weighted_decision is not None:
            d["weighted_decision"] = self.weighted_decision.to_dict()
        if self.interaction_result is not None:
            d["interaction_result"] = self.interaction_result.to_dict()
        if self.pattern_influence_result is not None:
            d["pattern_influence_result"] = self.pattern_influence_result.to_dict()
        if self.pattern_aggregation_result is not None:
            d["pattern_aggregation_result"] = self.pattern_aggregation_result.to_dict()
        return d


def _clamp_regime_factor(factor: float) -> float:
    return max(_REGIME_FACTOR_MIN, min(_REGIME_FACTOR_MAX, factor))


def _find_best_valid(
    ids: list[str],
    scores: list[float],
    valid_mask: list[bool],
) -> int:
    best_idx = -1
    best_score = -1.0
    for i, sid in enumerate(ids):
        if not valid_mask[i]:
            continue
        if scores[i] > best_score or (
            scores[i] == best_score and (best_idx == -1 or sid < ids[best_idx])
        ):
            best_score = scores[i]
            best_idx = i
    return best_idx


def orchestrate_selection(
    strategy_ids: list[str],
    base_scores: list[float],
    regime_factors: list[float] | None = None,
    feedback_factors: list[float] | None = None,
    confidences: list[float] | None = None,
    valid_flags: list[bool] | None = None,
    safe_flags: list[bool] | None = None,
    policy: StrategyOrchestrationPolicy | None = None,
    aggregated_regime: AggregatedRegimeState | None = None,
    dimension_weights: DimensionWeightVector | None = None,
    weighted_decision_policy: WeightedDecisionPolicy | None = None,
    interaction_config: InteractionConfig | None = None,
    dimension_regimes: dict[str, DimensionRegime] | None = None,
    pattern_result: PatternResult | None = None,
    pattern_influence_config: PatternInfluenceConfig | None = None,
) -> StrategySelectionResult:
    """Orchestrate strategy selection through the full pipeline.

    Computation order: base → regime → feedback (opt-in) → weights (opt-in) → interactions (opt-in) → pattern (opt-in).
    Optional aggregated_regime provides per-dimension context.
    Optional dimension_weights provides adaptive weights.
    Optional weighted_decision_policy enables weight influence on scoring.
    Optional interaction_config enables cross-dimension interaction factors.
    Optional pattern_result + pattern_influence_config enables pattern-based scoring (Phase 68).
    """
    p = policy or StrategyOrchestrationPolicy()

    if not strategy_ids:
        return StrategySelectionResult(
            explanation="no strategies provided",
        )

    n = len(strategy_ids)

    if len(base_scores) < n:
        base_scores = list(base_scores) + [0.0] * (n - len(base_scores))
    elif len(base_scores) > n:
        base_scores = base_scores[:n]

    if regime_factors is None:
        regime_factors = [1.0] * n
    elif len(regime_factors) < n:
        regime_factors = list(regime_factors) + [1.0] * (n - len(regime_factors))
    elif len(regime_factors) > n:
        regime_factors = regime_factors[:n]

    if feedback_factors is None:
        feedback_factors = [1.0] * n
    elif len(feedback_factors) < n:
        feedback_factors = list(feedback_factors) + [1.0] * (n - len(feedback_factors))
    elif len(feedback_factors) > n:
        feedback_factors = feedback_factors[:n]

    if confidences is None:
        confidences = [0.0] * n
    elif len(confidences) < n:
        confidences = list(confidences) + [0.0] * (n - len(confidences))
    elif len(confidences) > n:
        confidences = confidences[:n]

    if valid_flags is None:
        valid_flags = [True] * n
    elif len(valid_flags) < n:
        valid_flags = list(valid_flags) + [True] * (n - len(valid_flags))
    elif len(valid_flags) > n:
        valid_flags = valid_flags[:n]

    if safe_flags is None:
        safe_flags = [True] * n
    elif len(safe_flags) < n:
        safe_flags = list(safe_flags) + [True] * (n - len(safe_flags))
    elif len(safe_flags) > n:
        safe_flags = safe_flags[:n]

    effective_valid = [(valid_flags[i] and safe_flags[i]) for i in range(n)]

    if p.require_valid and not any(effective_valid):
        return StrategySelectionResult(
            explanation="all strategies invalid or unsafe",
        )

    # --- STEP 1: base winner ---
    base_best_idx = _find_best_valid(strategy_ids, base_scores, effective_valid)
    if base_best_idx == -1:
        return StrategySelectionResult(
            explanation="no valid strategies found",
        )
    base_winner = strategy_ids[base_best_idx]

    # --- STEP 2: regime weighting ---
    if p.use_regime_weighting:
        regime_scores = [base_scores[i] * _clamp_regime_factor(regime_factors[i]) for i in range(n)]
        used_regime = True
    else:
        regime_scores = list(base_scores)
        used_regime = False

    regime_best_idx = _find_best_valid(strategy_ids, regime_scores, effective_valid)
    regime_winner = strategy_ids[regime_best_idx] if regime_best_idx != -1 else base_winner

    # --- STEP 3: feedback selection (opt-in) ---
    if p.use_feedback_selection:
        fb_policy = p.feedback_policy or FeedbackSelectionPolicy(enabled=True)
        fb_result = select_with_feedback(
            candidates=strategy_ids,
            base_scores=regime_scores,
            feedback_factors=feedback_factors,
            confidences=confidences,
            policy=fb_policy,
            valid_flags=valid_flags,
            safe_flags=safe_flags,
        )
        used_feedback = True
        feedback_winner = fb_result.selected_candidate or regime_winner
    else:
        fb_result = None
        used_feedback = False
        feedback_winner = regime_winner

    # --- Pre-weight selection (feedback or regime winner) ---
    if used_feedback and fb_result is not None and fb_result.selected_candidate:
        pre_weight_selected = fb_result.selected_candidate
    else:
        pre_weight_selected = regime_winner

    # --- STEP 4: weighted decision influence (opt-in) ---
    wd_policy = weighted_decision_policy
    wd_result = None
    used_weights = False
    weight_winner = pre_weight_selected
    wf = 1.0

    if wd_policy is not None and wd_policy.enabled:
        from umh.runtime.weighted_decision import apply_weighted_influence

        pre_weight_scores = []
        for i in range(n):
            rf = _clamp_regime_factor(regime_factors[i]) if p.use_regime_weighting else 1.0
            ff = 1.0
            if used_feedback and fb_result is not None:
                for ac in fb_result.adjusted_candidates:
                    if ac.candidate_id == strategy_ids[i]:
                        ff = ac.feedback_factor
                        break
            pre_weight_scores.append(base_scores[i] * rf * ff)

        wd_result = apply_weighted_influence(
            strategy_ids=strategy_ids,
            input_scores=pre_weight_scores,
            weights=dimension_weights,
            regime=aggregated_regime,
            policy=wd_policy,
        )

        if wd_result.results:
            used_weights = wd_result.results[0].used_weights
            wf = wd_result.results[0].weight_factor if used_weights else 1.0

        if used_weights:
            weight_scores = [r.final_score for r in wd_result.results]
            weight_best_idx = _find_best_valid(strategy_ids, weight_scores, effective_valid)
            weight_winner = (
                strategy_ids[weight_best_idx] if weight_best_idx != -1 else pre_weight_selected
            )
        else:
            weight_winner = pre_weight_selected

    # --- STEP 5: cross-dimension interactions (opt-in) ---
    int_result = None
    used_interactions = False
    interaction_winner = weight_winner
    inf = 1.0

    if interaction_config is not None and interaction_config.enabled:
        from umh.runtime.dimension_interactions import compute_interaction_factor
        from umh.runtime.regime_aggregation import DimensionName

        dim_regimes = None
        if dimension_regimes:
            dim_regimes = {
                DimensionName(k) if isinstance(k, str) else k: v
                for k, v in dimension_regimes.items()
            }

        int_result = compute_interaction_factor(
            dimension_regimes=dim_regimes,
            config=interaction_config,
        )
        inf = int_result.interaction_factor
        used_interactions = inf != 1.0

        if used_interactions:
            pre_int_scores = []
            for i in range(n):
                rf = _clamp_regime_factor(regime_factors[i]) if p.use_regime_weighting else 1.0
                ff = 1.0
                if used_feedback and fb_result is not None:
                    for ac in fb_result.adjusted_candidates:
                        if ac.candidate_id == strategy_ids[i]:
                            ff = ac.feedback_factor
                            break
                pre_int_scores.append(base_scores[i] * rf * ff * wf * inf)

            int_best_idx = _find_best_valid(strategy_ids, pre_int_scores, effective_valid)
            interaction_winner = strategy_ids[int_best_idx] if int_best_idx != -1 else weight_winner

    # --- STEP 6: pattern influence (opt-in, Phase 68/69) ---
    pat_result = None
    pat_agg_result = None
    used_pattern = False
    pattern_winner = interaction_winner
    pf = 1.0

    if pattern_influence_config is not None and pattern_influence_config.enabled:
        pre_pat_scores = []
        for i in range(n):
            rf = _clamp_regime_factor(regime_factors[i]) if p.use_regime_weighting else 1.0
            ff = 1.0
            if used_feedback and fb_result is not None:
                for ac in fb_result.adjusted_candidates:
                    if ac.candidate_id == strategy_ids[i]:
                        ff = ac.feedback_factor
                        break
            pre_pat_scores.append(base_scores[i] * rf * ff * wf * inf)

        use_aggregation = (
            pattern_result is not None
            and pattern_result.matched
            and len(pattern_result.all_matches) > 1
        )

        if use_aggregation:
            from umh.runtime.pattern_aggregation import compute_pattern_aggregation

            pat_agg_results_per_candidate = []
            for i in range(n):
                ar = compute_pattern_aggregation(
                    pattern_result=pattern_result,
                    baseline_score=pre_pat_scores[i],
                    config=pattern_influence_config,
                )
                pat_agg_results_per_candidate.append(ar)

            pat_agg_result = (
                pat_agg_results_per_candidate[0] if pat_agg_results_per_candidate else None
            )
            if pat_agg_result is not None and pat_agg_result.applied:
                pf = pat_agg_result.final_factor
                used_pattern = True
        else:
            from umh.runtime.pattern_influence import compute_pattern_influence

            pat_results_per_candidate = []
            for i in range(n):
                pr = compute_pattern_influence(
                    pattern_result=pattern_result,
                    candidate_score=pre_pat_scores[i],
                    config=pattern_influence_config,
                )
                pat_results_per_candidate.append(pr)

            pat_result = pat_results_per_candidate[0] if pat_results_per_candidate else None
            if pat_result is not None and pat_result.applied:
                pf = pat_result.factor
                used_pattern = True

        if used_pattern:
            final_pat_scores = [pre_pat_scores[i] * pf for i in range(n)]
            pat_best_idx = _find_best_valid(strategy_ids, final_pat_scores, effective_valid)
            pattern_winner = (
                strategy_ids[pat_best_idx] if pat_best_idx != -1 else interaction_winner
            )
        else:
            pattern_winner = interaction_winner

    # --- Final selection ---
    selected = pattern_winner

    # --- Build candidates ---
    built_candidates: list[StrategyCandidate] = []
    for i in range(n):
        rf = _clamp_regime_factor(regime_factors[i]) if p.use_regime_weighting else 1.0
        ff = 1.0
        conf = confidences[i]

        if used_feedback and fb_result is not None:
            for ac in fb_result.adjusted_candidates:
                if ac.candidate_id == strategy_ids[i]:
                    ff = ac.feedback_factor
                    break

        built_candidates.append(
            StrategyCandidate(
                strategy_id=strategy_ids[i],
                base_score=base_scores[i],
                regime_factor=rf,
                feedback_factor=ff,
                weight_factor=wf,
                interaction_factor=inf,
                pattern_factor=pf,
                confidence=conf,
                valid=valid_flags[i],
                safe=safe_flags[i],
            )
        )

    changed_from_base = selected != base_winner
    changed_from_regime = selected != regime_winner
    changed_from_feedback = selected != pre_weight_selected
    changed_from_weights = selected != weight_winner
    changed_from_interactions = selected != interaction_winner

    explanation = _build_explanation(
        selected=selected,
        base_winner=base_winner,
        regime_winner=regime_winner,
        feedback_winner=feedback_winner,
        weight_winner=weight_winner,
        interaction_winner=interaction_winner,
        pattern_winner=pattern_winner,
        used_regime=used_regime,
        used_feedback=used_feedback,
        used_weights=used_weights,
        used_interactions=used_interactions,
        used_pattern=used_pattern,
        changed_from_base=changed_from_base,
        changed_from_regime=changed_from_regime,
        changed_from_feedback=changed_from_feedback,
        changed_from_weights=changed_from_weights,
        changed_from_interactions=changed_from_interactions,
        base_scores=base_scores,
        regime_scores=regime_scores,
        base_best_idx=base_best_idx,
        regime_best_idx=regime_best_idx,
        fb_result=fb_result,
        wd_result=wd_result,
        int_result=int_result,
        pat_result=pat_result,
        aggregated_regime=aggregated_regime,
        dimension_weights=dimension_weights,
    )

    return StrategySelectionResult(
        selected_strategy=selected,
        candidates=tuple(built_candidates),
        explanation=explanation,
        used_regime=used_regime,
        used_feedback=used_feedback,
        used_weights=used_weights,
        used_interactions=used_interactions,
        used_pattern=used_pattern,
        base_winner=base_winner,
        regime_winner=regime_winner,
        feedback_winner=feedback_winner,
        weight_winner=weight_winner,
        interaction_winner=interaction_winner,
        pattern_winner=pattern_winner,
        changed_from_base=changed_from_base,
        changed_from_regime=changed_from_regime,
        changed_from_feedback=changed_from_feedback,
        changed_from_weights=changed_from_weights,
        changed_from_interactions=changed_from_interactions,
        aggregated_regime=aggregated_regime,
        dimension_weights=dimension_weights,
        weighted_decision=wd_result,
        interaction_result=int_result,
        pattern_influence_result=pat_result,
        pattern_aggregation_result=pat_agg_result,
    )


def _build_explanation(
    *,
    selected: str,
    base_winner: str,
    regime_winner: str,
    feedback_winner: str,
    weight_winner: str,
    interaction_winner: str = "",
    pattern_winner: str = "",
    used_regime: bool,
    used_feedback: bool,
    used_weights: bool,
    used_interactions: bool = False,
    used_pattern: bool = False,
    changed_from_base: bool,
    changed_from_regime: bool,
    changed_from_feedback: bool,
    changed_from_weights: bool = False,
    changed_from_interactions: bool = False,
    base_scores: list[float],
    regime_scores: list[float],
    base_best_idx: int,
    regime_best_idx: int,
    fb_result: FeedbackSelectionResult | None,
    wd_result: WeightedDecisionBatchResult | None = None,
    int_result: InteractionResult | None = None,
    pat_result: PatternInfluenceResult | None = None,
    aggregated_regime: AggregatedRegimeState | None = None,
    dimension_weights: DimensionWeightVector | None = None,
) -> str:
    parts: list[str] = []

    parts.append(f"base_winner='{base_winner}' (score={base_scores[base_best_idx]:.4f})")

    if used_regime:
        parts.append(
            f"regime_winner='{regime_winner}' (regime_score={regime_scores[regime_best_idx]:.4f})"
        )
        if regime_winner != base_winner:
            parts.append("regime changed leader")
    else:
        parts.append("regime weighting disabled")

    if used_feedback:
        parts.append(f"feedback_winner='{feedback_winner}'")
        if fb_result is not None and fb_result.changed_selection:
            parts.append("feedback changed leader")
        else:
            parts.append("feedback did not change leader")
    else:
        parts.append("feedback selection disabled")

    if used_weights:
        parts.append(f"weight_winner='{weight_winner}'")
        if wd_result is not None:
            parts.append(f"weight_influence=[{wd_result.explanation}]")
        if changed_from_feedback:
            parts.append("weights changed leader")
    else:
        parts.append("weighted influence disabled")

    if used_interactions:
        parts.append(f"interaction_winner='{interaction_winner}'")
        if int_result is not None:
            parts.append(f"interaction_factor={int_result.interaction_factor:.4f}")
            parts.append(f"interactions=[{int_result.explanation}]")
        if changed_from_weights:
            parts.append("interactions changed leader")
    else:
        parts.append("interactions disabled")

    if used_pattern:
        parts.append(f"pattern_winner='{pattern_winner}'")
        if pat_result is not None:
            parts.append(f"pattern_factor={pat_result.factor:.4f}")
            parts.append(f"pattern_key={pat_result.contributing_pattern_key}")
        if changed_from_interactions:
            parts.append("pattern changed leader")
    else:
        parts.append("pattern influence disabled")

    parts.append(f"selected='{selected}'")

    if changed_from_base:
        parts.append(f"selection changed from base '{base_winner}'")
    if changed_from_regime and used_feedback:
        parts.append(f"feedback overrode regime winner '{regime_winner}'")
    if changed_from_feedback and used_weights:
        parts.append(f"weights overrode feedback winner '{feedback_winner}'")
    if changed_from_weights and used_interactions:
        parts.append(f"interactions overrode weight winner '{weight_winner}'")
    if changed_from_interactions and used_pattern:
        parts.append(f"pattern overrode interaction winner '{interaction_winner}'")

    if aggregated_regime is not None:
        parts.append(f"aggregated_regime=[{aggregated_regime.explanation}]")

    if dimension_weights is not None:
        parts.append(f"dimension_weights=[{dimension_weights.explanation}]")

    return "; ".join(parts)
