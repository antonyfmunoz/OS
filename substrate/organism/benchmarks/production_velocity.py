"""Benchmark 3 — Production Velocity.

Measures time-to-completion for productions using real timestamps.
Tracks duration trends across sequential productions to detect acceleration.
No LLM calls. All scoring deterministic.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProductionRecord:
    """A single production with start/end timestamps."""

    production_id: str = ""
    start_epoch: float = 0.0
    end_epoch: float = 0.0
    reuse_enabled: bool = True
    description: str = ""

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_epoch - self.start_epoch)


@dataclass
class VelocityResult:
    """Benchmark result with duration trends and acceleration metrics."""

    productions: int = 0
    total_duration_seconds: float = 0.0
    avg_duration_seconds: float = 0.0
    first_half_avg: float = 0.0
    second_half_avg: float = 0.0
    acceleration_ratio: float = 0.0
    trend_direction: str = "stable"
    durations: list[float] = field(default_factory=list)
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProductionVelocityBenchmark:
    """Measures production velocity trends from timestamp records.

    Acceleration ratio = first_half_avg / second_half_avg.
    > 1.0 means later productions are faster (compounding working).
    < 1.0 means later productions are slower (compounding not working).
    = 1.0 means no change.
    """

    def __init__(self) -> None:
        self._records: list[ProductionRecord] = []

    def add_record(self, record: ProductionRecord) -> None:
        self._records.append(record)

    def add_records(self, records: list[ProductionRecord]) -> None:
        self._records.extend(records)

    @property
    def record_count(self) -> int:
        return len(self._records)

    def run(self, track_filter: bool | None = None) -> VelocityResult:
        """Compute velocity metrics.

        Args:
            track_filter: If set, only include records where reuse_enabled matches.
                         None = include all records.
        """
        records = self._records
        if track_filter is not None:
            records = [r for r in records if r.reuse_enabled == track_filter]

        if not records:
            return VelocityResult()

        records_sorted = sorted(records, key=lambda r: r.start_epoch)
        durations = [r.duration_seconds for r in records_sorted]
        total = sum(durations)
        avg = total / len(durations)

        mid = len(durations) // 2
        first_half = durations[:mid] if mid > 0 else durations
        second_half = durations[mid:] if mid > 0 else durations

        first_avg = sum(first_half) / len(first_half) if first_half else 0.0
        second_avg = sum(second_half) / len(second_half) if second_half else 0.0

        if second_avg > 0:
            accel = first_avg / second_avg
        else:
            accel = 1.0

        if accel > 1.05:
            trend = "accelerating"
        elif accel < 0.95:
            trend = "decelerating"
        else:
            trend = "stable"

        details = []
        for r in records_sorted:
            details.append({
                "production_id": r.production_id,
                "duration_seconds": round(r.duration_seconds, 2),
                "reuse_enabled": r.reuse_enabled,
                "description": r.description,
            })

        return VelocityResult(
            productions=len(records_sorted),
            total_duration_seconds=round(total, 2),
            avg_duration_seconds=round(avg, 2),
            first_half_avg=round(first_avg, 2),
            second_half_avg=round(second_avg, 2),
            acceleration_ratio=round(accel, 4),
            trend_direction=trend,
            durations=[round(d, 2) for d in durations],
            details=details,
        )

    def compare_tracks(self) -> dict[str, Any]:
        """Compare Track A (reuse ON) vs Track B (reuse OFF)."""
        track_a = self.run(track_filter=True)
        track_b = self.run(track_filter=False)

        if track_b.avg_duration_seconds > 0:
            speedup = track_b.avg_duration_seconds / track_a.avg_duration_seconds
        else:
            speedup = 1.0

        return {
            "track_a_reuse_on": track_a.to_dict(),
            "track_b_reuse_off": track_b.to_dict(),
            "speedup_ratio": round(speedup, 4),
            "reuse_faster": speedup > 1.0,
        }
