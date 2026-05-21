"""Outcome decay — time-weighted statistics with exponential decay.

Computes strategy statistics where recent outcomes count more than old ones.
Uses deterministic exponential decay: weight = 0.5 ^ (age / half_life).

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from umh.runtime.outcome import OutcomeStatus, StrategyOutcome


@dataclass(frozen=True)
class DecayConfig:
    """Configuration for temporal decay."""

    half_life_seconds: float = 86400.0
    min_weight: float = 0.01
    max_weight: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "half_life_seconds", max(1.0, self.half_life_seconds))
        object.__setattr__(self, "min_weight", max(0.0, min(1.0, self.min_weight)))
        object.__setattr__(self, "max_weight", max(self.min_weight, min(1.0, self.max_weight)))


@dataclass(frozen=True)
class DecayResult:
    """Time-weighted aggregate statistics."""

    raw_count: int
    effective_count: float
    weighted_success_rate: float
    weighted_average_score: float
    weighted_average_latency: float
    weighted_average_effort: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_count": self.raw_count,
            "effective_count": round(self.effective_count, 4),
            "weighted_success_rate": round(self.weighted_success_rate, 4),
            "weighted_average_score": round(self.weighted_average_score, 4),
            "weighted_average_latency": round(self.weighted_average_latency, 4),
            "weighted_average_effort": round(self.weighted_average_effort, 4),
        }


def _parse_timestamp(ts: str) -> float | None:
    try:
        from datetime import datetime, timezone

        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def compute_decay_weight(age_seconds: float, config: DecayConfig) -> float:
    if age_seconds <= 0:
        return config.max_weight
    raw = math.pow(0.5, age_seconds / config.half_life_seconds)
    return max(config.min_weight, min(config.max_weight, raw))


def compute_decayed_stats(
    outcomes: list[StrategyOutcome],
    now_epoch: float,
    config: DecayConfig | None = None,
) -> DecayResult:
    cfg = config or DecayConfig()

    if not outcomes:
        return DecayResult(
            raw_count=0,
            effective_count=0.0,
            weighted_success_rate=0.0,
            weighted_average_score=0.0,
            weighted_average_latency=0.0,
            weighted_average_effort=0.0,
        )

    total_weight = 0.0
    weighted_success = 0.0
    weighted_score = 0.0
    weighted_latency = 0.0
    weighted_effort = 0.0

    for o in outcomes:
        ts = _parse_timestamp(o.timestamp)
        if ts is None:
            age = 0.0
        else:
            age = max(0.0, now_epoch - ts)

        w = compute_decay_weight(age, cfg)
        total_weight += w
        if o.status == OutcomeStatus.SUCCESS:
            weighted_success += w
        weighted_score += w * o.success_score
        weighted_latency += w * o.latency
        weighted_effort += w * o.effort

    if total_weight == 0.0:
        return DecayResult(
            raw_count=len(outcomes),
            effective_count=0.0,
            weighted_success_rate=0.0,
            weighted_average_score=0.0,
            weighted_average_latency=0.0,
            weighted_average_effort=0.0,
        )

    return DecayResult(
        raw_count=len(outcomes),
        effective_count=total_weight,
        weighted_success_rate=weighted_success / total_weight,
        weighted_average_score=weighted_score / total_weight,
        weighted_average_latency=weighted_latency / total_weight,
        weighted_average_effort=weighted_effort / total_weight,
    )
