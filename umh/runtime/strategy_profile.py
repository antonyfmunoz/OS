"""Strategy-regime compatibility — per-strategy regime preference profiles.

Declares which regimes each strategy type is best suited for and computes
a compatibility factor. Different strategies become preferred under
different confirmed regimes.

Factor rules:
    regime in preferred_regimes → factor = 1.0 + max_bonus
    regime in penalized_regimes → factor = 1.0 - max_penalty
    otherwise                   → factor = 1.0  (neutral)

Duration scaling (TREND regimes only):
    For preferred TREND: bonus scales from 0 to max_bonus over duration
    For penalized TREND: penalty scales from 0 to max_penalty over duration
    SPIKE and STABLE regimes get flat factors (no duration scaling).

Bounds: factor ∈ [0.85, 1.15]

Stateless computation. No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.regime import RegimeType

_DEFAULT_MIN_FACTOR = 0.85
_DEFAULT_MAX_FACTOR = 1.15
_DEFAULT_MAX_BONUS = 0.10
_DEFAULT_MAX_PENALTY = 0.10
_DEFAULT_DURATION_SCALE_CAP = 10


@dataclass(frozen=True)
class StrategyRegimeProfile:
    """Declares a strategy's regime compatibility."""

    strategy_name: str
    preferred_regimes: frozenset[RegimeType] = field(default_factory=frozenset)
    neutral_regimes: frozenset[RegimeType] = field(default_factory=frozenset)
    penalized_regimes: frozenset[RegimeType] = field(default_factory=frozenset)
    max_bonus: float = _DEFAULT_MAX_BONUS
    max_penalty: float = _DEFAULT_MAX_PENALTY

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_bonus", max(0.0, self.max_bonus))
        object.__setattr__(self, "max_penalty", max(0.0, self.max_penalty))

    def compatibility_class(self, regime: RegimeType) -> str:
        if regime in self.preferred_regimes:
            return "preferred"
        if regime in self.penalized_regimes:
            return "penalized"
        return "neutral"

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "preferred_regimes": sorted(r.value for r in self.preferred_regimes),
            "neutral_regimes": sorted(r.value for r in self.neutral_regimes),
            "penalized_regimes": sorted(r.value for r in self.penalized_regimes),
            "max_bonus": round(self.max_bonus, 4),
            "max_penalty": round(self.max_penalty, 4),
        }


AGGRESSIVE_PROFILE = StrategyRegimeProfile(
    strategy_name="aggressive",
    preferred_regimes=frozenset({RegimeType.SPIKE_UP, RegimeType.TREND_UP}),
    neutral_regimes=frozenset({RegimeType.STABLE}),
    penalized_regimes=frozenset({RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN}),
)

CONSERVATIVE_PROFILE = StrategyRegimeProfile(
    strategy_name="conservative",
    preferred_regimes=frozenset({RegimeType.STABLE, RegimeType.TREND_DOWN}),
    neutral_regimes=frozenset({RegimeType.TREND_UP}),
    penalized_regimes=frozenset({RegimeType.SPIKE_UP, RegimeType.SPIKE_DOWN}),
)

BALANCED_PROFILE = StrategyRegimeProfile(
    strategy_name="balanced",
    preferred_regimes=frozenset({RegimeType.STABLE, RegimeType.TREND_UP}),
    neutral_regimes=frozenset({RegimeType.TREND_DOWN}),
    penalized_regimes=frozenset(),
    max_bonus=0.05,
    max_penalty=0.05,
)

RECOVERY_PROFILE = StrategyRegimeProfile(
    strategy_name="recovery",
    preferred_regimes=frozenset({RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN}),
    neutral_regimes=frozenset({RegimeType.STABLE}),
    penalized_regimes=frozenset({RegimeType.SPIKE_UP, RegimeType.TREND_UP}),
)

DEFAULT_PROFILES: dict[str, StrategyRegimeProfile] = {
    "aggressive": AGGRESSIVE_PROFILE,
    "conservative": CONSERVATIVE_PROFILE,
    "balanced": BALANCED_PROFILE,
    "recovery": RECOVERY_PROFILE,
}

NEUTRAL_PROFILE = StrategyRegimeProfile(
    strategy_name="neutral",
    preferred_regimes=frozenset(),
    neutral_regimes=frozenset(RegimeType),
    penalized_regimes=frozenset(),
    max_bonus=0.0,
    max_penalty=0.0,
)


def _is_trend(regime: RegimeType) -> bool:
    return regime in (RegimeType.TREND_UP, RegimeType.TREND_DOWN)


def _duration_scale(duration: int, cap: int = _DEFAULT_DURATION_SCALE_CAP) -> float:
    """Scale factor from 0.0 to 1.0 based on duration, capped."""
    dur = max(0, duration)
    if cap <= 0:
        return 1.0
    return min(1.0, dur / cap)


@dataclass(frozen=True)
class StrategyRegimeResult:
    """Output of strategy-regime compatibility computation."""

    strategy_name: str
    regime: RegimeType
    duration: int
    compatibility: str
    raw_factor: float
    factor: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "regime": self.regime.value,
            "duration": self.duration,
            "compatibility": self.compatibility,
            "raw_factor": round(self.raw_factor, 6),
            "factor": round(self.factor, 6),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class StrategyRegimeSnapshot:
    """Frozen snapshot of strategy-regime factors for multiple strategies."""

    results: dict[str, StrategyRegimeResult]

    def get(self, strategy_name: str) -> StrategyRegimeResult | None:
        return self.results.get(strategy_name)

    def get_factor(self, strategy_name: str, default: float = 1.0) -> float:
        r = self.results.get(strategy_name)
        return r.factor if r is not None else default

    def best_strategy(self) -> str | None:
        if not self.results:
            return None
        return max(self.results, key=lambda n: self.results[n].factor)

    def worst_strategy(self) -> str | None:
        if not self.results:
            return None
        return min(self.results, key=lambda n: self.results[n].factor)

    def preferred_strategies(self) -> list[str]:
        return sorted(n for n, r in self.results.items() if r.compatibility == "preferred")

    def penalized_strategies(self) -> list[str]:
        return sorted(n for n, r in self.results.items() if r.compatibility == "penalized")

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": {k: v.to_dict() for k, v in sorted(self.results.items())},
        }


def compute_strategy_regime_factor(
    profile: StrategyRegimeProfile,
    regime: RegimeType,
    duration: int = 0,
    min_factor: float = _DEFAULT_MIN_FACTOR,
    max_factor: float = _DEFAULT_MAX_FACTOR,
) -> StrategyRegimeResult:
    """Compute compatibility factor for a strategy under a given regime.

    Deterministic, stateless. Same inputs always produce the same factor.

    Args:
        profile: The strategy's regime preference profile.
        regime: Current confirmed regime.
        duration: How many ticks the regime has been confirmed.
        min_factor: Lower bound for the factor.
        max_factor: Upper bound for the factor.

    Returns:
        StrategyRegimeResult with the computed factor.
    """
    dur = max(0, duration)
    compatibility = profile.compatibility_class(regime)

    if compatibility == "preferred":
        if _is_trend(regime):
            scale = _duration_scale(dur)
            bonus = profile.max_bonus * scale
            reason = (
                f"{profile.strategy_name} preferred in {regime.value}, duration scale {scale:.2f}"
            )
        else:
            bonus = profile.max_bonus
            reason = f"{profile.strategy_name} preferred in {regime.value}, flat bonus"
        raw = 1.0 + bonus

    elif compatibility == "penalized":
        if _is_trend(regime):
            scale = _duration_scale(dur)
            penalty = profile.max_penalty * scale
            reason = (
                f"{profile.strategy_name} penalized in {regime.value}, duration scale {scale:.2f}"
            )
        else:
            penalty = profile.max_penalty
            reason = f"{profile.strategy_name} penalized in {regime.value}, flat penalty"
        raw = 1.0 - penalty

    else:
        raw = 1.0
        reason = f"{profile.strategy_name} neutral in {regime.value}"

    factor = max(min_factor, min(max_factor, raw))

    return StrategyRegimeResult(
        strategy_name=profile.strategy_name,
        regime=regime,
        duration=dur,
        compatibility=compatibility,
        raw_factor=raw,
        factor=factor,
        reason=reason,
    )


def compute_all_strategy_factors(
    profiles: dict[str, StrategyRegimeProfile],
    regime: RegimeType,
    duration: int = 0,
    min_factor: float = _DEFAULT_MIN_FACTOR,
    max_factor: float = _DEFAULT_MAX_FACTOR,
) -> StrategyRegimeSnapshot:
    """Compute compatibility factors for all strategies under a given regime.

    Args:
        profiles: strategy_name → StrategyRegimeProfile.
        regime: Current confirmed regime.
        duration: Current regime duration.
        min_factor: Lower bound for factors.
        max_factor: Upper bound for factors.

    Returns:
        StrategyRegimeSnapshot with per-strategy results.
    """
    results: dict[str, StrategyRegimeResult] = {}
    for name in sorted(profiles):
        results[name] = compute_strategy_regime_factor(
            profiles[name], regime, duration, min_factor, max_factor
        )
    return StrategyRegimeSnapshot(results=results)


def get_profile(strategy_name: str) -> StrategyRegimeProfile:
    """Look up a strategy's regime profile, defaulting to neutral."""
    return DEFAULT_PROFILES.get(strategy_name, NEUTRAL_PROFILE)


def apply_strategy_regime_factor(base_score: float, factor: float) -> float:
    """Apply strategy-regime compatibility factor to a base score."""
    return base_score * factor
