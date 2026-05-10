"""
Regime break detection engine — detects and corrects strategy lock-in.

Addresses the failure mode where the system is stuck in a locally reinforced
but globally suboptimal strategy. The exploration engine nudges scores, but
can't overcome large accumulated advantages. The regime engine detects the
lock-in pattern and applies corrective pressure.

Detection signals:
1. Reward plateau: recent rewards flat but below historical peak (≥ 0.5 avg).
2. Strategy dominance: one strategy's score >> all others.
3. Confidence mismatch: system reports confidence but rewards degraded.

When a regime break is detected:
- All non-protected scores are compressed toward the mean.
- Exploration confidence is reduced (amplifies exploration engine).
- Untried strategies (score == 0.0) get forced trial via select_regime_override.

Design constraints:
- Deterministic: same history → same signal, always.
- Stateless: no carry-over between turns (prevents oscillation).
- Bounded: all outputs clamped to safe ranges.
- No permanent overrides: compression is temporary per-turn.
- Safety: RECOVER strategies cannot be regime-broken.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ─── Constants ────────────────────────────────────────────────────

MIN_HISTORY = 15
PLATEAU_WINDOW = 8
PEAK_LOOKBACK = 50

PLATEAU_THRESHOLD = 0.02
REWARD_DROP_THRESHOLD = 0.15
DOMINANCE_THRESHOLD = 0.5
CONFIDENCE_MISMATCH_THRESHOLD = 0.2

MIN_DAMPENING = 0.3
EPSILON = 1e-9

PROTECTED_STRATEGIES = frozenset({"RECOVER", "recover"})


# ─── Data structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class RegimeSignal:
    """Result of regime break detection. Immutable snapshot."""

    active: bool
    strength: float
    reason: str
    dampened_strategy: str | None
    dampening_factor: float
    exploration_boost: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "strength": round(self.strength, 6),
            "reason": self.reason,
            "dampened_strategy": self.dampened_strategy,
            "dampening_factor": round(self.dampening_factor, 6),
            "exploration_boost": round(self.exploration_boost, 6),
        }


NO_REGIME_BREAK = RegimeSignal(
    active=False,
    strength=0.0,
    reason="",
    dampened_strategy=None,
    dampening_factor=1.0,
    exploration_boost=0.0,
)


# ─── Detection signals ───────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _compute_plateau_signal(reward_history: list[float]) -> float:
    """Detect reward plateau: recent rewards flat but below historical peak.

    Only fires when the plateau average is ≥ 0.5 (system is "succeeding"
    but suboptimal). If rewards are below 0.5, the exploration engine's
    failure-streak logic handles it.

    Returns signal strength [0, 1]. Higher = stronger plateau detection.
    """
    if len(reward_history) < MIN_HISTORY:
        return 0.0

    recent = reward_history[-PLATEAU_WINDOW:]
    recent_avg = sum(recent) / len(recent)

    if recent_avg < 0.5:
        return 0.0

    recent_variance = sum((r - recent_avg) ** 2 for r in recent) / len(recent)
    is_flat = recent_variance < PLATEAU_THRESHOLD**2

    if not is_flat:
        return 0.0

    lookback = reward_history[-PEAK_LOOKBACK:]
    peak = max(lookback)

    drop = peak - recent_avg
    if drop < REWARD_DROP_THRESHOLD:
        return 0.0

    return _clamp(drop / 0.5, 0.0, 1.0)


def _compute_dominance_signal(
    strategy_scores: dict[str, float],
) -> tuple[float, str | None]:
    """Detect when one strategy dominates all others.

    Returns (signal_strength, dominant_strategy_name).
    """
    if len(strategy_scores) < 2:
        return 0.0, None

    total = sum(abs(v) for v in strategy_scores.values())
    if total <= 0:
        return 0.0, None

    sorted_strats = sorted(strategy_scores.items(), key=lambda x: -x[1])
    top_name, top_score = sorted_strats[0]

    if top_name in PROTECTED_STRATEGIES:
        return 0.0, None

    share = abs(top_score) / total
    if share < DOMINANCE_THRESHOLD:
        return 0.0, None

    dominance = _clamp(
        (share - DOMINANCE_THRESHOLD) / (1.0 - DOMINANCE_THRESHOLD), 0.0, 1.0
    )
    return dominance, top_name


def _compute_confidence_mismatch(
    plan_confidence: float | None,
    reward_history: list[float],
) -> float:
    """Detect when reported confidence is high but rewards are low.

    The system thinks it's doing well but it isn't.
    """
    if plan_confidence is None or len(reward_history) < PLATEAU_WINDOW:
        return 0.0

    recent_avg = sum(reward_history[-PLATEAU_WINDOW:]) / PLATEAU_WINDOW
    mismatch = plan_confidence - recent_avg

    if mismatch < CONFIDENCE_MISMATCH_THRESHOLD:
        return 0.0

    return _clamp(mismatch, 0.0, 1.0)


# ─── Public API ───────────────────────────────────────────────────


def compute_regime_signal(
    reward_history: list[float],
    strategy_scores: dict[str, float],
    plan_confidence: float | None = None,
    objective_trend: str | None = None,
    prior_regime_strength: float = 0.0,
    current_action: str | None = None,
) -> RegimeSignal:
    """Detect whether the system is locked into a suboptimal strategy regime.

    Deterministic: same inputs → same signal, always.
    No randomness. No side effects. Pure function.

    Args:
        reward_history: List of recent reward values (oldest first).
        strategy_scores: Current strategy scores {name: score}.
        plan_confidence: Current plan confidence [0, 1]. None if unknown.
        objective_trend: "improving", "degrading", or "flat".
        prior_regime_strength: Strength from previous turn (for decay).
        current_action: The action the system most recently selected.

    Returns:
        RegimeSignal with dampening and exploration boost parameters.
    """
    if not strategy_scores or len(strategy_scores) < 2:
        return NO_REGIME_BREAK

    plateau = _compute_plateau_signal(reward_history)
    dominance, dominant_name = _compute_dominance_signal(strategy_scores)
    mismatch = _compute_confidence_mismatch(plan_confidence, reward_history)

    trend_boost = 0.0
    if objective_trend == "degrading":
        trend_boost = 0.3
    elif objective_trend == "flat" and plateau > 0:
        trend_boost = 0.1

    co_occurrence = 0.0
    if plateau > 0 and dominance > 0:
        co_occurrence = plateau * dominance * 0.5

    raw_strength = max(
        plateau * 0.5 + dominance * 0.3 + trend_boost * 0.2 + co_occurrence,
        mismatch * 0.6 + dominance * 0.4,
        plateau * 0.7 + mismatch * 0.3,
    )

    strength = _clamp(raw_strength, 0.0, 1.0)

    secondary_support = (
        sum(
            [
                dominance > 0.0,
                mismatch > 0.0,
                trend_boost > 0.0,
            ]
        )
        >= 1
    )

    if plateau == 0.0 or (not secondary_support and strength < 0.3):
        return NO_REGIME_BREAK

    if dominant_name is None:
        if (
            current_action
            and current_action in strategy_scores
            and current_action not in PROTECTED_STRATEGIES
        ):
            dominant_name = current_action
        else:
            sorted_strats = sorted(strategy_scores.items(), key=lambda x: -x[1])
            dominant_name = sorted_strats[0][0]
            if dominant_name in PROTECTED_STRATEGIES:
                dominant_name = sorted_strats[1][0] if len(sorted_strats) > 1 else None

    if dominant_name and dominant_name in PROTECTED_STRATEGIES:
        return NO_REGIME_BREAK

    final_strength = _clamp(strength, 0.0, 1.0)

    dampening_factor = _clamp(1.0 - final_strength * 0.7, MIN_DAMPENING, 1.0)
    exploration_boost = _clamp(final_strength * 0.5, 0.0, 0.5)

    if plateau > 0.3 and dominance > 0.3:
        dampening_factor = _clamp(1.0 - final_strength, MIN_DAMPENING, dampening_factor)

    reasons: list[str] = []
    if plateau > 0:
        reasons.append("reward_plateau")
    if dominance > 0:
        reasons.append("strategy_dominance")
    if mismatch > 0:
        reasons.append("confidence_mismatch")
    if trend_boost > 0:
        reasons.append("trend_pressure")

    return RegimeSignal(
        active=True,
        strength=final_strength,
        reason="+".join(reasons) if reasons else "regime_detected",
        dampened_strategy=dominant_name,
        dampening_factor=dampening_factor,
        exploration_boost=exploration_boost,
    )


def apply_regime_dampening(
    strategy_scores: dict[str, float],
    signal: RegimeSignal,
) -> dict[str, float]:
    """Apply regime break dampening to strategy scores.

    When regime is detected, compresses all non-protected scores toward
    the mean, proportional to signal strength. This gives untried strategies
    a competitive chance without permanently overriding any score.

    Returns a new dict — never mutates the input.
    """
    if not signal.active or signal.dampened_strategy is None:
        return dict(strategy_scores)

    target = signal.dampened_strategy
    if target not in strategy_scores:
        return dict(strategy_scores)

    if target in PROTECTED_STRATEGIES:
        return dict(strategy_scores)

    adjustable = {
        k: v for k, v in strategy_scores.items() if k not in PROTECTED_STRATEGIES
    }
    if len(adjustable) < 2:
        return dict(strategy_scores)

    values = list(adjustable.values())
    mean = sum(values) / len(values)

    compression = signal.strength * 0.8

    result: dict[str, float] = {}
    for name, score in strategy_scores.items():
        if name in PROTECTED_STRATEGIES:
            result[name] = score
        elif name in adjustable:
            compressed = score + (mean - score) * compression
            result[name] = max(0.0, compressed)
        else:
            result[name] = score

    return result


def select_regime_override(
    signal: RegimeSignal,
    strategy_scores: dict[str, float],
    step: int,
) -> str | None:
    """When regime is active, nominate an untried strategy for forced trial.

    Only fires when:
    1. Regime is active with strength >= 0.4
    2. There are strategies with score = 0 (never tried)
    3. Step-based rotation ensures each untried gets exactly one trial

    Returns strategy name to force-select, or None.
    """
    if not signal.active or signal.strength < 0.4:
        return None

    untried = sorted(
        k
        for k, v in strategy_scores.items()
        if v == 0.0 and k not in PROTECTED_STRATEGIES
    )

    if not untried:
        return None

    idx = step % len(untried)
    return untried[idx]
