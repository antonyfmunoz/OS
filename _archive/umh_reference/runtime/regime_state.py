"""Composite regime modeling — multi-signal regime state for nuanced strategy selection.

Combines multiple regime dimensions into a single composite state:
    - trend:      STABLE / TREND_UP / TREND_DOWN / SPIKE_UP / SPIKE_DOWN  (from Phase 42)
    - risk:       LOW / MEDIUM / HIGH  (derived from delta magnitude)
    - urgency:    LOW / MEDIUM / HIGH  (derived from delta velocity)
    - stability:  HIGH / MEDIUM / LOW  (derived from regime duration)
    - confidence: LOW / MEDIUM / HIGH  (derived from duration + confirmation strength)

Strategy profiles declare preferences across ALL dimensions. Match scoring
weights each dimension independently and aggregates into a bounded factor.

Default weights:
    trend=0.4, risk=0.25, urgency=0.2, stability=0.15

Bounds: factor ∈ [0.85, 1.15]

Stateless computation. No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.runtime.regime import RegimeType

_DEFAULT_MIN_FACTOR = 0.85
_DEFAULT_MAX_FACTOR = 1.15
_DEFAULT_MATCH_SCALE = 0.10

_RISK_LOW_THRESHOLD = 0.08
_RISK_HIGH_THRESHOLD = 0.20
_URGENCY_LOW_THRESHOLD = 0.05
_URGENCY_HIGH_THRESHOLD = 0.15
_STABILITY_HIGH_THRESHOLD = 10
_STABILITY_MEDIUM_THRESHOLD = 3
_CONFIDENCE_HIGH_THRESHOLD = 10
_CONFIDENCE_MEDIUM_THRESHOLD = 3

_DEFAULT_TREND_WEIGHT = 0.40
_DEFAULT_RISK_WEIGHT = 0.25
_DEFAULT_URGENCY_WEIGHT = 0.20
_DEFAULT_STABILITY_WEIGHT = 0.15


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UrgencyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StabilityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def classify_risk(delta_magnitude: float) -> RiskLevel:
    mag = abs(delta_magnitude)
    if mag >= _RISK_HIGH_THRESHOLD:
        return RiskLevel.HIGH
    if mag >= _RISK_LOW_THRESHOLD:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def classify_urgency(delta_velocity: float) -> UrgencyLevel:
    vel = abs(delta_velocity)
    if vel >= _URGENCY_HIGH_THRESHOLD:
        return UrgencyLevel.HIGH
    if vel >= _URGENCY_LOW_THRESHOLD:
        return UrgencyLevel.MEDIUM
    return UrgencyLevel.LOW


def classify_stability(duration: int) -> StabilityLevel:
    dur = max(0, duration)
    if dur >= _STABILITY_HIGH_THRESHOLD:
        return StabilityLevel.HIGH
    if dur >= _STABILITY_MEDIUM_THRESHOLD:
        return StabilityLevel.MEDIUM
    return StabilityLevel.LOW


def classify_confidence(duration: int, is_confirmed: bool = True) -> ConfidenceLevel:
    dur = max(0, duration)
    if not is_confirmed:
        return ConfidenceLevel.LOW
    if dur >= _CONFIDENCE_HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if dur >= _CONFIDENCE_MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


@dataclass(frozen=True)
class CompositeRegimeState:
    """Multi-dimensional regime state for a single signal."""

    signal_name: str
    trend: RegimeType
    risk: RiskLevel
    urgency: UrgencyLevel
    stability: StabilityLevel
    confidence: ConfidenceLevel

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "trend": self.trend.value,
            "risk": self.risk.value,
            "urgency": self.urgency.value,
            "stability": self.stability.value,
            "confidence": self.confidence.value,
        }


NEUTRAL_COMPOSITE = CompositeRegimeState(
    signal_name="neutral",
    trend=RegimeType.STABLE,
    risk=RiskLevel.LOW,
    urgency=UrgencyLevel.LOW,
    stability=StabilityLevel.HIGH,
    confidence=ConfidenceLevel.HIGH,
)


def build_composite_state(
    signal_name: str,
    trend: RegimeType,
    delta_magnitude: float = 0.0,
    delta_velocity: float = 0.0,
    duration: int = 0,
    is_confirmed: bool = True,
) -> CompositeRegimeState:
    """Build a composite regime state from raw signal data.

    All classification is deterministic and bounded.
    """
    return CompositeRegimeState(
        signal_name=signal_name,
        trend=trend,
        risk=classify_risk(delta_magnitude),
        urgency=classify_urgency(delta_velocity),
        stability=classify_stability(duration),
        confidence=classify_confidence(duration, is_confirmed),
    )


@dataclass(frozen=True)
class RegimeStateSnapshot:
    """Frozen snapshot of composite regime states for all signals."""

    states: dict[str, CompositeRegimeState]
    tick: int = 0

    def get(self, signal_name: str) -> CompositeRegimeState | None:
        return self.states.get(signal_name)

    def get_or_neutral(self, signal_name: str) -> CompositeRegimeState:
        return self.states.get(signal_name, NEUTRAL_COMPOSITE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "states": {k: v.to_dict() for k, v in sorted(self.states.items())},
            "tick": self.tick,
        }


def build_all_composite_states(
    trends: dict[str, RegimeType],
    delta_magnitudes: dict[str, float] | None = None,
    delta_velocities: dict[str, float] | None = None,
    durations: dict[str, int] | None = None,
    confirmations: dict[str, bool] | None = None,
    tick: int = 0,
) -> RegimeStateSnapshot:
    """Build composite states for all signals."""
    mags = delta_magnitudes or {}
    vels = delta_velocities or {}
    durs = durations or {}
    confs = confirmations or {}

    states: dict[str, CompositeRegimeState] = {}
    for name in sorted(trends):
        states[name] = build_composite_state(
            signal_name=name,
            trend=trends[name],
            delta_magnitude=mags.get(name, 0.0),
            delta_velocity=vels.get(name, 0.0),
            duration=durs.get(name, 0),
            is_confirmed=confs.get(name, True),
        )
    return RegimeStateSnapshot(states=states, tick=tick)


# ── Composite strategy profiles ─────────────────────────────────────


@dataclass(frozen=True)
class DimensionWeights:
    """Weights for each dimension in composite match scoring."""

    trend: float = _DEFAULT_TREND_WEIGHT
    risk: float = _DEFAULT_RISK_WEIGHT
    urgency: float = _DEFAULT_URGENCY_WEIGHT
    stability: float = _DEFAULT_STABILITY_WEIGHT

    def __post_init__(self) -> None:
        t = max(0.0, self.trend)
        r = max(0.0, self.risk)
        u = max(0.0, self.urgency)
        s = max(0.0, self.stability)
        total = t + r + u + s
        if total <= 0:
            t, r, u, s = 0.25, 0.25, 0.25, 0.25
            total = 1.0
        object.__setattr__(self, "trend", t / total)
        object.__setattr__(self, "risk", r / total)
        object.__setattr__(self, "urgency", u / total)
        object.__setattr__(self, "stability", s / total)

    def to_dict(self) -> dict[str, float]:
        return {
            "trend": round(self.trend, 4),
            "risk": round(self.risk, 4),
            "urgency": round(self.urgency, 4),
            "stability": round(self.stability, 4),
        }


DEFAULT_DIMENSION_WEIGHTS = DimensionWeights()


@dataclass(frozen=True)
class CompositeStrategyProfile:
    """Strategy preferences across all regime dimensions."""

    strategy_name: str
    preferred_trends: frozenset[RegimeType] = field(default_factory=frozenset)
    penalized_trends: frozenset[RegimeType] = field(default_factory=frozenset)
    preferred_risk: frozenset[RiskLevel] = field(default_factory=frozenset)
    penalized_risk: frozenset[RiskLevel] = field(default_factory=frozenset)
    preferred_urgency: frozenset[UrgencyLevel] = field(default_factory=frozenset)
    penalized_urgency: frozenset[UrgencyLevel] = field(default_factory=frozenset)
    preferred_stability: frozenset[StabilityLevel] = field(default_factory=frozenset)
    penalized_stability: frozenset[StabilityLevel] = field(default_factory=frozenset)
    match_scale: float = _DEFAULT_MATCH_SCALE

    def __post_init__(self) -> None:
        object.__setattr__(self, "match_scale", max(0.0, self.match_scale))

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "preferred_trends": sorted(r.value for r in self.preferred_trends),
            "penalized_trends": sorted(r.value for r in self.penalized_trends),
            "preferred_risk": sorted(r.value for r in self.preferred_risk),
            "penalized_risk": sorted(r.value for r in self.penalized_risk),
            "preferred_urgency": sorted(r.value for r in self.preferred_urgency),
            "penalized_urgency": sorted(r.value for r in self.penalized_urgency),
            "preferred_stability": sorted(r.value for r in self.preferred_stability),
            "penalized_stability": sorted(r.value for r in self.penalized_stability),
            "match_scale": round(self.match_scale, 4),
        }


COMPOSITE_AGGRESSIVE = CompositeStrategyProfile(
    strategy_name="aggressive",
    preferred_trends=frozenset({RegimeType.SPIKE_UP, RegimeType.TREND_UP}),
    penalized_trends=frozenset({RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN}),
    preferred_risk=frozenset({RiskLevel.HIGH}),
    penalized_risk=frozenset({RiskLevel.LOW}),
    preferred_urgency=frozenset({UrgencyLevel.HIGH}),
    penalized_urgency=frozenset(),
    preferred_stability=frozenset({StabilityLevel.LOW}),
    penalized_stability=frozenset({StabilityLevel.HIGH}),
)

COMPOSITE_CONSERVATIVE = CompositeStrategyProfile(
    strategy_name="conservative",
    preferred_trends=frozenset({RegimeType.STABLE, RegimeType.TREND_DOWN}),
    penalized_trends=frozenset({RegimeType.SPIKE_UP, RegimeType.SPIKE_DOWN}),
    preferred_risk=frozenset({RiskLevel.LOW}),
    penalized_risk=frozenset({RiskLevel.HIGH}),
    preferred_urgency=frozenset({UrgencyLevel.LOW}),
    penalized_urgency=frozenset({UrgencyLevel.HIGH}),
    preferred_stability=frozenset({StabilityLevel.HIGH}),
    penalized_stability=frozenset({StabilityLevel.LOW}),
)

COMPOSITE_BALANCED = CompositeStrategyProfile(
    strategy_name="balanced",
    preferred_trends=frozenset({RegimeType.STABLE, RegimeType.TREND_UP}),
    penalized_trends=frozenset(),
    preferred_risk=frozenset({RiskLevel.MEDIUM}),
    penalized_risk=frozenset(),
    preferred_urgency=frozenset({UrgencyLevel.MEDIUM}),
    penalized_urgency=frozenset(),
    preferred_stability=frozenset({StabilityLevel.MEDIUM, StabilityLevel.HIGH}),
    penalized_stability=frozenset(),
    match_scale=0.05,
)

COMPOSITE_RECOVERY = CompositeStrategyProfile(
    strategy_name="recovery",
    preferred_trends=frozenset({RegimeType.SPIKE_DOWN, RegimeType.TREND_DOWN}),
    penalized_trends=frozenset({RegimeType.SPIKE_UP, RegimeType.TREND_UP}),
    preferred_risk=frozenset({RiskLevel.HIGH, RiskLevel.MEDIUM}),
    penalized_risk=frozenset(),
    preferred_urgency=frozenset({UrgencyLevel.HIGH}),
    penalized_urgency=frozenset({UrgencyLevel.LOW}),
    preferred_stability=frozenset({StabilityLevel.LOW}),
    penalized_stability=frozenset(),
)

DEFAULT_COMPOSITE_PROFILES: dict[str, CompositeStrategyProfile] = {
    "aggressive": COMPOSITE_AGGRESSIVE,
    "conservative": COMPOSITE_CONSERVATIVE,
    "balanced": COMPOSITE_BALANCED,
    "recovery": COMPOSITE_RECOVERY,
}

NEUTRAL_COMPOSITE_PROFILE = CompositeStrategyProfile(
    strategy_name="neutral",
    match_scale=0.0,
)


# ── Match scoring ───────────────────────────────────────────────────


def _dimension_match(value: Any, preferred: frozenset, penalized: frozenset) -> int:
    if value in preferred:
        return 1
    if value in penalized:
        return -1
    return 0


@dataclass(frozen=True)
class DimensionScore:
    """Match result for a single dimension."""

    dimension: str
    value: str
    match: int
    weight: float
    contribution: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "value": self.value,
            "match": self.match,
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 6),
        }


@dataclass(frozen=True)
class CompositeMatchResult:
    """Full match result for a strategy against a composite regime state."""

    strategy_name: str
    dimensions: tuple[DimensionScore, ...]
    total_match: float
    raw_factor: float
    factor: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "total_match": round(self.total_match, 6),
            "raw_factor": round(self.raw_factor, 6),
            "factor": round(self.factor, 6),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class CompositeMatchSnapshot:
    """Frozen snapshot of composite match results for multiple strategies."""

    results: dict[str, CompositeMatchResult]

    def get(self, strategy_name: str) -> CompositeMatchResult | None:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": {k: v.to_dict() for k, v in sorted(self.results.items())},
        }


def compute_composite_match(
    profile: CompositeStrategyProfile,
    state: CompositeRegimeState,
    weights: DimensionWeights | None = None,
    min_factor: float = _DEFAULT_MIN_FACTOR,
    max_factor: float = _DEFAULT_MAX_FACTOR,
) -> CompositeMatchResult:
    """Compute composite match factor for a strategy against a regime state.

    Deterministic, stateless. Same inputs always produce the same factor.
    """
    w = weights or DEFAULT_DIMENSION_WEIGHTS

    trend_match = _dimension_match(state.trend, profile.preferred_trends, profile.penalized_trends)
    risk_match = _dimension_match(state.risk, profile.preferred_risk, profile.penalized_risk)
    urgency_match = _dimension_match(
        state.urgency, profile.preferred_urgency, profile.penalized_urgency
    )
    stability_match = _dimension_match(
        state.stability, profile.preferred_stability, profile.penalized_stability
    )

    trend_contrib = trend_match * w.trend
    risk_contrib = risk_match * w.risk
    urgency_contrib = urgency_match * w.urgency
    stability_contrib = stability_match * w.stability

    total_match = trend_contrib + risk_contrib + urgency_contrib + stability_contrib

    dimensions = (
        DimensionScore("trend", state.trend.value, trend_match, w.trend, trend_contrib),
        DimensionScore("risk", state.risk.value, risk_match, w.risk, risk_contrib),
        DimensionScore("urgency", state.urgency.value, urgency_match, w.urgency, urgency_contrib),
        DimensionScore(
            "stability", state.stability.value, stability_match, w.stability, stability_contrib
        ),
    )

    raw_factor = 1.0 + total_match * profile.match_scale
    factor = max(min_factor, min(max_factor, raw_factor))

    parts = []
    for d in dimensions:
        if d.match != 0:
            label = "preferred" if d.match > 0 else "penalized"
            parts.append(f"{d.dimension}={d.value}({label})")
    explanation = f"{profile.strategy_name}: " + (", ".join(parts) if parts else "all neutral")

    return CompositeMatchResult(
        strategy_name=profile.strategy_name,
        dimensions=dimensions,
        total_match=total_match,
        raw_factor=raw_factor,
        factor=factor,
        explanation=explanation,
    )


def compute_all_composite_matches(
    profiles: dict[str, CompositeStrategyProfile],
    state: CompositeRegimeState,
    weights: DimensionWeights | None = None,
    min_factor: float = _DEFAULT_MIN_FACTOR,
    max_factor: float = _DEFAULT_MAX_FACTOR,
) -> CompositeMatchSnapshot:
    """Compute composite match factors for all strategies against a single state."""
    results: dict[str, CompositeMatchResult] = {}
    for name in sorted(profiles):
        results[name] = compute_composite_match(
            profiles[name], state, weights, min_factor, max_factor
        )
    return CompositeMatchSnapshot(results=results)


def get_composite_profile(strategy_name: str) -> CompositeStrategyProfile:
    """Look up a composite strategy profile, defaulting to neutral."""
    return DEFAULT_COMPOSITE_PROFILES.get(strategy_name, NEUTRAL_COMPOSITE_PROFILE)


def apply_composite_factor(base_score: float, factor: float) -> float:
    """Apply composite match factor to a base score."""
    return base_score * factor
