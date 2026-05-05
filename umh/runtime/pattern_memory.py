"""Contextual pattern memory — append-only storage of composite state patterns.

Records composite dimension states alongside outcome scores so the system
can later recognize "this situation has happened before." Phase 67 is
purely observational — patterns are recorded but never influence scoring.

Key design:
    - PatternKey: discrete-only (string enums), no floats — safe for dict keys
    - PatternRecord: immutable snapshot of key + outcome + timestamp
    - PatternMemory: append-only list, no delete, no mutation (inv 313, 314)
    - PatternStats: aggregated view per key (count, avg_score, success_rate)

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
No circular dependency: reads regime_aggregation types only.
Never mutates historical records (inv 314).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.runtime.regime_aggregation import (
    AggregatedRegimeState,
    DimensionName,
    DimensionRegime,
    DirectionCategory,
)


class TrendDirection(Enum):
    """Discrete trend direction for pattern keys."""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class RiskLevel(Enum):
    """Discrete risk level for pattern keys."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StabilityLevel(Enum):
    """Discrete stability level for pattern keys."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UrgencyLevel(Enum):
    """Discrete urgency level for pattern keys."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class PatternKey:
    """Discrete composite state key — no floats, safe for dict lookup (inv 316)."""

    trend_direction: TrendDirection = TrendDirection.NEUTRAL
    risk_level: RiskLevel = RiskLevel.MEDIUM
    stability_level: StabilityLevel = StabilityLevel.MEDIUM
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM

    def to_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.trend_direction.value,
            self.risk_level.value,
            self.stability_level.value,
            self.urgency_level.value,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "trend_direction": self.trend_direction.value,
            "risk_level": self.risk_level.value,
            "stability_level": self.stability_level.value,
            "urgency_level": self.urgency_level.value,
        }

    @property
    def dimensions(self) -> tuple[str, str, str, str]:
        return self.to_tuple()


@dataclass(frozen=True)
class PatternRecord:
    """A single observation of a pattern with its outcome (inv 314: immutable)."""

    key: PatternKey
    outcome_score: float = 0.0
    confidence: float = 0.0
    timestamp: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_score", max(0.0, min(1.0, self.outcome_score)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))
        object.__setattr__(self, "timestamp", max(0, self.timestamp))

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key.to_dict(),
            "outcome_score": round(self.outcome_score, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class PatternStats:
    """Aggregated statistics for a single pattern key."""

    key: PatternKey
    count: int = 0
    avg_score: float = 0.0
    success_rate: float = 0.0
    avg_confidence: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "count", max(0, self.count))
        object.__setattr__(self, "avg_score", max(0.0, min(1.0, self.avg_score)))
        object.__setattr__(self, "success_rate", max(0.0, min(1.0, self.success_rate)))
        object.__setattr__(self, "avg_confidence", max(0.0, min(1.0, self.avg_confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key.to_dict(),
            "count": self.count,
            "avg_score": round(self.avg_score, 4),
            "success_rate": round(self.success_rate, 4),
            "avg_confidence": round(self.avg_confidence, 4),
        }


_SUCCESS_THRESHOLD: float = 0.6
_DEFAULT_MIN_SAMPLES: int = 10


class PatternMemory:
    """Append-only pattern memory (inv 313).

    Records are never deleted or mutated. The only write operation is append.
    Stats are computed on-demand from the full record list.
    """

    def __init__(self) -> None:
        self._records: list[PatternRecord] = []

    @property
    def size(self) -> int:
        return len(self._records)

    def append(self, record: PatternRecord) -> None:
        """Append a record. No mutation of existing records (inv 313, 314)."""
        self._records.append(record)

    def get_records(self) -> tuple[PatternRecord, ...]:
        """Return all records as an immutable tuple (inv 314)."""
        return tuple(self._records)

    def get_records_for_key(self, key: PatternKey) -> tuple[PatternRecord, ...]:
        """Return records matching the exact key."""
        return tuple(r for r in self._records if r.key == key)

    def compute_stats(self, key: PatternKey) -> PatternStats:
        """Compute aggregated stats for a given pattern key."""
        matching = [r for r in self._records if r.key == key]

        if not matching:
            return PatternStats(key=key)

        count = len(matching)
        avg_score = sum(r.outcome_score for r in matching) / count
        success_count = sum(1 for r in matching if r.outcome_score >= _SUCCESS_THRESHOLD)
        success_rate = success_count / count
        avg_confidence = sum(r.confidence for r in matching) / count

        return PatternStats(
            key=key,
            count=count,
            avg_score=avg_score,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
        )

    def compute_all_stats(self) -> dict[tuple[str, str, str, str], PatternStats]:
        """Compute stats for all unique keys in memory."""
        keys_seen: set[tuple[str, str, str, str]] = set()
        for r in self._records:
            keys_seen.add(r.key.to_tuple())

        result: dict[tuple[str, str, str, str], PatternStats] = {}
        for key_tuple in sorted(keys_seen):
            key = PatternKey(
                trend_direction=TrendDirection(key_tuple[0]),
                risk_level=RiskLevel(key_tuple[1]),
                stability_level=StabilityLevel(key_tuple[2]),
                urgency_level=UrgencyLevel(key_tuple[3]),
            )
            result[key_tuple] = self.compute_stats(key)

        return result

    def unique_keys(self) -> set[tuple[str, str, str, str]]:
        """Return the set of unique pattern key tuples."""
        return {r.key.to_tuple() for r in self._records}

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "unique_keys": len(self.unique_keys()),
            "records": [r.to_dict() for r in self._records],
        }


def _direction_to_trend(direction: DirectionCategory) -> TrendDirection:
    """Map DirectionCategory to discrete TrendDirection."""
    if direction is DirectionCategory.POSITIVE:
        return TrendDirection.UP
    if direction is DirectionCategory.NEGATIVE:
        return TrendDirection.DOWN
    return TrendDirection.NEUTRAL


def _label_to_risk(label: str) -> RiskLevel:
    """Map risk regime label to discrete RiskLevel."""
    label = label.lower()
    if label == "high":
        return RiskLevel.HIGH
    if label == "low":
        return RiskLevel.LOW
    return RiskLevel.MEDIUM


def _label_to_stability(label: str) -> StabilityLevel:
    """Map stability regime label to discrete StabilityLevel."""
    label = label.lower()
    if label == "high":
        return StabilityLevel.HIGH
    if label == "low":
        return StabilityLevel.LOW
    return StabilityLevel.MEDIUM


def _label_to_urgency(label: str) -> UrgencyLevel:
    """Map urgency regime label to discrete UrgencyLevel."""
    label = label.lower()
    if label == "high":
        return UrgencyLevel.HIGH
    if label == "low":
        return UrgencyLevel.LOW
    return UrgencyLevel.MEDIUM


def extract_pattern_key(
    aggregated: AggregatedRegimeState | None = None,
) -> PatternKey | None:
    """Extract a discrete PatternKey from an AggregatedRegimeState.

    Returns None if aggregated is None (inv 317).
    Uses direction for trend (not label), labels for risk/stability/urgency.
    """
    if aggregated is None:
        return None

    trend_regime = aggregated.get(DimensionName.TREND)
    risk_regime = aggregated.get(DimensionName.RISK)
    stability_regime = aggregated.get(DimensionName.STABILITY)
    urgency_regime = aggregated.get(DimensionName.URGENCY)

    trend_dir = (
        _direction_to_trend(trend_regime.direction)
        if trend_regime is not None
        else TrendDirection.NEUTRAL
    )
    risk_lvl = (
        _label_to_risk(risk_regime.regime_label) if risk_regime is not None else RiskLevel.MEDIUM
    )
    stab_lvl = (
        _label_to_stability(stability_regime.regime_label)
        if stability_regime is not None
        else StabilityLevel.MEDIUM
    )
    urg_lvl = (
        _label_to_urgency(urgency_regime.regime_label)
        if urgency_regime is not None
        else UrgencyLevel.MEDIUM
    )

    return PatternKey(
        trend_direction=trend_dir,
        risk_level=risk_lvl,
        stability_level=stab_lvl,
        urgency_level=urg_lvl,
    )
