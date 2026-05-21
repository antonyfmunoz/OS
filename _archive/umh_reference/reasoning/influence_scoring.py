"""
InfluenceScoring — deterministic signal composition into a single influence score.

Aggregates all existing decision signals from the EOS runtime into a
comparable, normalized space and composes them additively into a final
score.  This is a composition layer only — it does NOT introduce new
intelligence, alter upstream logic, or replace existing selection.

Seven input signals, each pre-normalized to [0, 1]:
    goal_score        — active goal evaluation score
    plan_score        — active plan confidence
    strategy_score    — selected strategy effective score
    state_bias        — combined world-state bias magnitude
    credit_signal     — causal credit total signal strength
    exploration_signal — exploration rate (inverted: low rate = high exploitation)
    commitment_signal — goal commitment / persistence strength

Composition formula (strictly additive, no nonlinear transforms):
    final_score = sum(W_i * signal_i)

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


W_GOAL = 0.30
W_PLAN = 0.20
W_STRATEGY = 0.15
W_STATE = 0.10
W_CREDIT = 0.10
W_EXPLORATION = 0.10
W_COMMITMENT = 0.05

_WEIGHT_SUM = (
    W_GOAL + W_PLAN + W_STRATEGY + W_STATE + W_CREDIT + W_EXPLORATION + W_COMMITMENT
)
assert abs(_WEIGHT_SUM - 1.0) < 1e-9, f"Weights must sum to 1.0, got {_WEIGHT_SUM}"

INFLUENCE_WEIGHT = 0.15
PLAN_INFLUENCE_WEIGHT = 0.10


def _clamp(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


@dataclass(frozen=True)
class InfluenceComponent:
    """A single signal's contribution to the final influence score."""

    name: str
    value: float
    weight: float
    contribution: float

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass(frozen=True)
class InfluenceSnapshot:
    """Raw signal values before weighting."""

    goal_score: float = 0.0
    plan_score: float = 0.0
    strategy_score: float = 0.0
    state_bias: float = 0.0
    credit_signal: float = 0.0
    exploration_signal: float = 0.0
    commitment_signal: float = 0.0

    def to_dict(self) -> dict:
        return {
            "goal_score": round(self.goal_score, 4),
            "plan_score": round(self.plan_score, 4),
            "strategy_score": round(self.strategy_score, 4),
            "state_bias": round(self.state_bias, 4),
            "credit_signal": round(self.credit_signal, 4),
            "exploration_signal": round(self.exploration_signal, 4),
            "commitment_signal": round(self.commitment_signal, 4),
        }


@dataclass(frozen=True)
class InfluenceResult:
    """Final computed influence with full breakdown."""

    final_score: float
    snapshot: InfluenceSnapshot
    components: tuple[InfluenceComponent, ...]
    weights: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "final_score": round(self.final_score, 4),
            "components": [c.to_dict() for c in self.components],
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
        }


NO_INFLUENCE_RESULT = InfluenceResult(
    final_score=0.0,
    snapshot=InfluenceSnapshot(),
    components=(),
    weights={},
)


def compute_influence_score(
    snapshot: InfluenceSnapshot,
    adapted_weights: dict[str, float] | None = None,
) -> InfluenceResult:
    """Compute weighted additive influence score from signal snapshot.

    All inputs are clamped to [0, 1] before weighting.
    Final score is clamped to [0, 1].

    When ``adapted_weights`` is provided, those weights override the base
    constants.  Adapted weights must be pre-normalized (sum to 1.0).
    """
    w_goal = adapted_weights.get("goal", W_GOAL) if adapted_weights else W_GOAL
    w_plan = adapted_weights.get("plan", W_PLAN) if adapted_weights else W_PLAN
    w_strategy = (
        adapted_weights.get("strategy", W_STRATEGY) if adapted_weights else W_STRATEGY
    )
    w_state = adapted_weights.get("state_bias", W_STATE) if adapted_weights else W_STATE
    w_credit = adapted_weights.get("credit", W_CREDIT) if adapted_weights else W_CREDIT
    w_exploration = (
        adapted_weights.get("exploration", W_EXPLORATION)
        if adapted_weights
        else W_EXPLORATION
    )
    w_commitment = (
        adapted_weights.get("commitment", W_COMMITMENT)
        if adapted_weights
        else W_COMMITMENT
    )

    pairs = (
        ("goal", _clamp(snapshot.goal_score), w_goal),
        ("plan", _clamp(snapshot.plan_score), w_plan),
        ("strategy", _clamp(snapshot.strategy_score), w_strategy),
        ("state_bias", _clamp(snapshot.state_bias), w_state),
        ("credit", _clamp(snapshot.credit_signal), w_credit),
        ("exploration", _clamp(snapshot.exploration_signal), w_exploration),
        ("commitment", _clamp(snapshot.commitment_signal), w_commitment),
    )

    components: list[InfluenceComponent] = []
    total = 0.0

    for name, value, weight in pairs:
        contribution = value * weight
        total += contribution
        components.append(
            InfluenceComponent(
                name=name,
                value=value,
                weight=weight,
                contribution=contribution,
            )
        )

    final_score = _clamp(total)

    weights = {
        "goal": W_GOAL,
        "plan": W_PLAN,
        "strategy": W_STRATEGY,
        "state_bias": W_STATE,
        "credit": W_CREDIT,
        "exploration": W_EXPLORATION,
        "commitment": W_COMMITMENT,
    }

    return InfluenceResult(
        final_score=final_score,
        snapshot=snapshot,
        components=tuple(components),
        weights=weights,
    )


def build_influence_snapshot(
    goal_score: float | None = None,
    plan_confidence: float | None = None,
    strategy_score: float | None = None,
    conditioning_bias: dict | None = None,
    learned_state_bias: dict | None = None,
    credit_total_signal: float | None = None,
    exploration_rate: float | None = None,
    commitment_bonuses: dict | None = None,
    persistence_streaks: dict | None = None,
) -> InfluenceSnapshot:
    """Build an InfluenceSnapshot from raw runtime signals.

    Handles normalization from raw signal formats to [0, 1] range.
    """
    _goal = goal_score if goal_score is not None else 0.0
    _plan = plan_confidence if plan_confidence is not None else 0.0
    _strategy = strategy_score if strategy_score is not None else 0.0

    # State bias: average magnitude of combined conditioning + learned bias
    _state = 0.0
    bias_values: list[float] = []
    if conditioning_bias and isinstance(conditioning_bias, dict):
        strat_bias = conditioning_bias.get("strategy_bias", {})
        if strat_bias and isinstance(strat_bias, dict):
            bias_values.extend(abs(v) for v in strat_bias.values())
    if learned_state_bias and isinstance(learned_state_bias, dict):
        bias_values.extend(abs(v) for v in learned_state_bias.values())
    if bias_values:
        _state = sum(bias_values) / len(bias_values)
        _state = min(_state * 5.0, 1.0)

    # Credit signal: total_signal from causal credit (normalize to [0, 1])
    _credit = 0.0
    if credit_total_signal is not None and credit_total_signal > 0:
        _credit = min(credit_total_signal, 1.0)

    # Exploration: invert rate so high exploitation = high signal
    _exploration = 0.0
    if exploration_rate is not None:
        _exploration = 1.0 - min(exploration_rate, 1.0)

    # Commitment: average persistence streak + bonus across goals
    _commitment = 0.0
    commit_signals: list[float] = []
    if commitment_bonuses and isinstance(commitment_bonuses, dict):
        commit_signals.extend(min(abs(v), 1.0) for v in commitment_bonuses.values())
    if persistence_streaks and isinstance(persistence_streaks, dict):
        for v in persistence_streaks.values():
            commit_signals.append(min(v / 5.0, 1.0))
    if commit_signals:
        _commitment = sum(commit_signals) / len(commit_signals)

    return InfluenceSnapshot(
        goal_score=_goal,
        plan_score=_plan,
        strategy_score=_strategy,
        state_bias=_state,
        credit_signal=_credit,
        exploration_signal=_exploration,
        commitment_signal=_commitment,
    )


def compute_influence_adjustment(final_influence_score: float) -> float:
    """Compute the additive adjustment for strategy ranking.

    Returns final_influence_score * INFLUENCE_WEIGHT, bounded.
    """
    return _clamp(final_influence_score) * INFLUENCE_WEIGHT


def compute_plan_influence(final_influence_score: float) -> float:
    """Compute the additive influence term for plan utility.

    Returns final_influence_score * PLAN_INFLUENCE_WEIGHT, bounded.
    """
    return _clamp(final_influence_score) * PLAN_INFLUENCE_WEIGHT


BASE_WEIGHTS: dict[str, float] = {
    "goal": W_GOAL,
    "plan": W_PLAN,
    "strategy": W_STRATEGY,
    "state_bias": W_STATE,
    "credit": W_CREDIT,
    "exploration": W_EXPLORATION,
    "commitment": W_COMMITMENT,
}
