"""Identity layer — persistent preference formation and trait tracking.

Tracks traits derived from behavioral signals, stores preferences that
emerge over time, and produces identity-influenced scoring factors.
All updates are append-only and bounded — traits drift slowly, never
spike.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_DEFAULT_LEARNING_RATE = 0.08
_MIN_LEARNING_RATE = 0.01
_MAX_LEARNING_RATE = 0.20
_MAX_DELTA_PER_UPDATE = 0.15
_MIN_TRAIT_VALUE = 0.0
_MAX_TRAIT_VALUE = 1.0
_DEFAULT_TRAIT_VALUE = 0.5
_MIN_IDENTITY_FACTOR = 0.80
_MAX_IDENTITY_FACTOR = 1.20


@dataclass(frozen=True)
class TraitSnapshot:
    """Immutable snapshot of a trait at a point in time."""

    trait_name: str
    value: float
    confidence: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trait_name": self.trait_name,
            "value": round(self.value, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class IdentityProfile:
    """Frozen view of the current identity state."""

    traits: dict[str, float]
    preferences: dict[str, float]
    confidence: dict[str, float]
    update_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "traits": {k: round(v, 4) for k, v in sorted(self.traits.items())},
            "preferences": {k: round(v, 4) for k, v in sorted(self.preferences.items())},
            "confidence": {k: round(v, 4) for k, v in sorted(self.confidence.items())},
            "update_count": self.update_count,
        }


@dataclass(frozen=True)
class IdentityInfluence:
    """Result of computing identity's influence on a scoring decision."""

    factor: float
    trait_contributions: dict[str, float]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": round(self.factor, 4),
            "trait_contributions": {
                k: round(v, 4) for k, v in sorted(self.trait_contributions.items())
            },
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BehaviorSignals:
    """Extracted behavioral signals for trait updates."""

    completion_rate: float = 0.5
    switch_frequency: float = 0.0
    success_rate: float = 0.5
    avg_sequence_length: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "completion_rate", max(0.0, min(1.0, self.completion_rate)))
        object.__setattr__(self, "switch_frequency", max(0.0, min(1.0, self.switch_frequency)))
        object.__setattr__(self, "success_rate", max(0.0, min(1.0, self.success_rate)))
        object.__setattr__(self, "avg_sequence_length", max(0.0, self.avg_sequence_length))

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion_rate": round(self.completion_rate, 4),
            "switch_frequency": round(self.switch_frequency, 4),
            "success_rate": round(self.success_rate, 4),
            "avg_sequence_length": round(self.avg_sequence_length, 4),
        }


_TRAIT_SIGNAL_MAP: dict[str, list[tuple[str, float, bool]]] = {
    "persistence": [
        ("completion_rate", 0.5, False),
        ("switch_frequency", 0.5, True),
    ],
    "ambition": [
        ("avg_sequence_length", 0.6, False),
        ("success_rate", 0.4, False),
    ],
    "risk_tolerance": [
        ("switch_frequency", 0.4, False),
        ("success_rate", 0.6, True),
    ],
    "efficiency": [
        ("completion_rate", 0.7, False),
        ("success_rate", 0.3, False),
    ],
}


class SignalExtractor:
    """Extracts behavioral signals from goal state and commitment history."""

    def extract(
        self,
        *,
        total_ticks: int = 0,
        goals_completed: int = 0,
        goals_attempted: int = 0,
        switches: int = 0,
        total_sequence_steps: int = 0,
        sequences_evaluated: int = 0,
    ) -> BehaviorSignals:
        completion_rate = goals_completed / goals_attempted if goals_attempted > 0 else 0.5
        switch_frequency = switches / total_ticks if total_ticks > 0 else 0.0
        success_rate = goals_completed / goals_attempted if goals_attempted > 0 else 0.5
        avg_seq_len = total_sequence_steps / sequences_evaluated if sequences_evaluated > 0 else 1.0
        return BehaviorSignals(
            completion_rate=completion_rate,
            switch_frequency=switch_frequency,
            success_rate=success_rate,
            avg_sequence_length=avg_seq_len,
        )


class IdentityStore:
    """Manages trait and preference state with append-only update history.

    Every update is bounded by MAX_DELTA_PER_UPDATE to prevent spikes.
    Confidence grows with each update, approaching 1.0 asymptotically.
    """

    def __init__(
        self,
        *,
        learning_rate: float = _DEFAULT_LEARNING_RATE,
        max_delta: float = _MAX_DELTA_PER_UPDATE,
    ) -> None:
        self._traits: dict[str, float] = {}
        self._preferences: dict[str, float] = {}
        self._confidence: dict[str, float] = {}
        self._history: list[TraitSnapshot] = []
        self._update_count: int = 0
        self._learning_rate = max(_MIN_LEARNING_RATE, min(_MAX_LEARNING_RATE, learning_rate))
        self._max_delta = max(0.01, min(0.5, max_delta))

    @property
    def learning_rate(self) -> float:
        return self._learning_rate

    @property
    def max_delta(self) -> float:
        return self._max_delta

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def trait_count(self) -> int:
        return len(self._traits)

    @property
    def history_count(self) -> int:
        return len(self._history)

    def get_trait(self, name: str) -> float:
        """Get current trait value. Returns default (0.5) if not set."""
        return self._traits.get(name, _DEFAULT_TRAIT_VALUE)

    def get_confidence(self, name: str) -> float:
        """Get confidence for a trait. Returns 0.0 if never updated."""
        return self._confidence.get(name, 0.0)

    def get_preference(self, name: str) -> float:
        """Get preference value. Returns 0.5 if not set."""
        return self._preferences.get(name, _DEFAULT_TRAIT_VALUE)

    def update_trait(
        self,
        name: str,
        signal_value: float,
        *,
        timestamp: str = "",
    ) -> TraitSnapshot:
        """Update a trait toward signal_value using EMA with bounded delta.

        trait_new = old + clamp(learning_rate * (signal - old), -max_delta, +max_delta)
        """
        old = self._traits.get(name, _DEFAULT_TRAIT_VALUE)
        raw_delta = self._learning_rate * (signal_value - old)
        clamped_delta = max(-self._max_delta, min(self._max_delta, raw_delta))
        new_val = max(_MIN_TRAIT_VALUE, min(_MAX_TRAIT_VALUE, old + clamped_delta))

        self._traits[name] = new_val

        old_conf = self._confidence.get(name, 0.0)
        new_conf = min(1.0, old_conf + (1.0 - old_conf) * 0.1)
        self._confidence[name] = new_conf

        self._update_count += 1

        ts = timestamp or _iso_now()
        snapshot = TraitSnapshot(
            trait_name=name,
            value=new_val,
            confidence=new_conf,
            timestamp=ts,
        )
        self._history.append(snapshot)
        return snapshot

    def set_preference(self, name: str, value: float) -> None:
        """Set a preference value directly. Clamped to [0, 1]."""
        self._preferences[name] = max(_MIN_TRAIT_VALUE, min(_MAX_TRAIT_VALUE, value))

    def update_from_signals(
        self,
        signals: BehaviorSignals,
        *,
        timestamp: str = "",
    ) -> list[TraitSnapshot]:
        """Update all mapped traits from behavioral signals."""
        snapshots: list[TraitSnapshot] = []
        for trait_name, mappings in sorted(_TRAIT_SIGNAL_MAP.items()):
            weighted_signal = 0.0
            total_weight = 0.0
            for signal_attr, weight, invert in mappings:
                raw = getattr(signals, signal_attr, 0.5)
                val = 1.0 - raw if invert else raw
                weighted_signal += weight * val
                total_weight += weight
            if total_weight > 0:
                composite = weighted_signal / total_weight
                snap = self.update_trait(trait_name, composite, timestamp=timestamp)
                snapshots.append(snap)
        return snapshots

    def get_profile(self) -> IdentityProfile:
        """Return a frozen snapshot of current identity state."""
        return IdentityProfile(
            traits=dict(self._traits),
            preferences=dict(self._preferences),
            confidence=dict(self._confidence),
            update_count=self._update_count,
        )

    def get_history(self) -> list[TraitSnapshot]:
        """Return a copy of the trait update history."""
        return list(self._history)

    def clear(self) -> None:
        """Clear all state."""
        self._traits.clear()
        self._preferences.clear()
        self._confidence.clear()
        self._history.clear()
        self._update_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "traits": {k: round(v, 4) for k, v in sorted(self._traits.items())},
            "preferences": {k: round(v, 4) for k, v in sorted(self._preferences.items())},
            "confidence": {k: round(v, 4) for k, v in sorted(self._confidence.items())},
            "update_count": self._update_count,
            "history_count": len(self._history),
            "learning_rate": self._learning_rate,
        }


class IdentityScorer:
    """Computes identity-influenced scoring factors.

    Produces a multiplicative factor in [0.80, 1.20] that biases
    sequence scores based on identity traits. The factor never
    overrides the base score — only nudges it.

    Trait-to-scoring mappings:
    - persistence: boosts longer sequences, penalizes very short ones
    - ambition: boosts high-effort objectives
    - risk_tolerance: boosts novel sequences
    - efficiency: boosts low-effort objectives
    """

    def __init__(
        self,
        *,
        identity_store: IdentityStore | None = None,
        enabled: bool = False,
    ) -> None:
        self._store = identity_store
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def identity_store(self) -> IdentityStore | None:
        return self._store

    def compute_factor(
        self,
        *,
        sequence_length: int = 1,
        avg_effort: float = 1.0,
        avg_priority: float = 5.0,
    ) -> IdentityInfluence:
        """Compute identity scoring factor. Pure, no side effects."""
        if not self._enabled or self._store is None:
            return IdentityInfluence(
                factor=1.0,
                trait_contributions={},
                reason="identity scoring disabled",
            )

        contributions: dict[str, float] = {}
        total_bias = 0.0

        persistence = self._store.get_trait("persistence")
        persistence_conf = self._store.get_confidence("persistence")
        if persistence_conf > 0:
            length_signal = min(1.0, sequence_length / 4.0)
            pers_bias = (persistence - 0.5) * length_signal * 0.2
            contributions["persistence"] = pers_bias
            total_bias += pers_bias * persistence_conf

        ambition = self._store.get_trait("ambition")
        ambition_conf = self._store.get_confidence("ambition")
        if ambition_conf > 0:
            effort_signal = min(1.0, avg_effort / 3.0)
            amb_bias = (ambition - 0.5) * effort_signal * 0.15
            contributions["ambition"] = amb_bias
            total_bias += amb_bias * ambition_conf

        efficiency = self._store.get_trait("efficiency")
        efficiency_conf = self._store.get_confidence("efficiency")
        if efficiency_conf > 0:
            inv_effort = 1.0 - min(1.0, avg_effort / 5.0)
            eff_bias = (efficiency - 0.5) * inv_effort * 0.15
            contributions["efficiency"] = eff_bias
            total_bias += eff_bias * efficiency_conf

        risk_tolerance = self._store.get_trait("risk_tolerance")
        risk_conf = self._store.get_confidence("risk_tolerance")
        if risk_conf > 0:
            priority_signal = avg_priority / 10.0
            risk_bias = (risk_tolerance - 0.5) * priority_signal * 0.1
            contributions["risk_tolerance"] = risk_bias
            total_bias += risk_bias * risk_conf

        factor = max(
            _MIN_IDENTITY_FACTOR,
            min(_MAX_IDENTITY_FACTOR, 1.0 + total_bias),
        )

        reason = self._build_reason(contributions, factor)

        return IdentityInfluence(
            factor=factor,
            trait_contributions=contributions,
            reason=reason,
        )

    def _build_reason(
        self,
        contributions: dict[str, float],
        factor: float,
    ) -> str:
        if not contributions:
            return "no trait data available"

        parts: list[str] = []
        for trait, bias in sorted(contributions.items()):
            if abs(bias) > 0.001:
                direction = "boost" if bias > 0 else "penalty"
                parts.append(f"{trait}: {direction} ({bias:+.4f})")

        if not parts:
            return "neutral identity influence"

        direction = "positive" if factor > 1.0 else "negative" if factor < 1.0 else "neutral"
        parts.append(f"net {direction} factor: {factor:.4f}")
        return "; ".join(parts)
