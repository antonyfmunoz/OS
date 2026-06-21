"""Benchmark 4 — Capability Reuse (Dual-Track).

Track A: reuse ON — system can leverage prior capabilities.
Track B: reuse OFF — system builds from scratch each time.
Measures ROI: reuse_benefit = (time_saved + review_reduction + defect_reduction) / reuse_count.
No LLM calls. All scoring deterministic.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReusableCapability:
    """A capability that can be reused across productions."""

    capability_id: str = ""
    name: str = ""
    category: str = ""
    times_reused: int = 0
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class TrackRecord:
    """A single production in one track."""

    production_id: str = ""
    track: str = "A"
    duration_seconds: float = 0.0
    review_rounds: int = 0
    defect_count: int = 0
    capabilities_reused: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CapabilityROI:
    """ROI calculation for a single capability."""

    capability_id: str = ""
    name: str = ""
    reuse_count: int = 0
    time_saved_seconds: float = 0.0
    review_reduction: float = 0.0
    defect_reduction: float = 0.0
    roi: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityReuseResult:
    """Benchmark result comparing dual tracks."""

    track_a_count: int = 0
    track_b_count: int = 0
    track_a_avg_duration: float = 0.0
    track_b_avg_duration: float = 0.0
    track_a_avg_reviews: float = 0.0
    track_b_avg_reviews: float = 0.0
    track_a_avg_defects: float = 0.0
    track_b_avg_defects: float = 0.0
    time_saved_pct: float = 0.0
    review_reduction_pct: float = 0.0
    defect_reduction_pct: float = 0.0
    total_reuses: int = 0
    unique_capabilities_reused: int = 0
    capability_roi: list[dict[str, Any]] = field(default_factory=list)
    aggregate_roi: float = 0.0
    verdict: str = "INCONCLUSIVE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapabilityReuseBenchmark:
    """Dual-track benchmark isolating compounding from noise.

    Track A (reuse ON): system leverages prior capabilities.
    Track B (reuse OFF): system builds from scratch.
    Delta between tracks = compounding signal.
    """

    def __init__(self) -> None:
        self._track_a: list[TrackRecord] = []
        self._track_b: list[TrackRecord] = []
        self._capabilities: dict[str, ReusableCapability] = {}

    def register_capability(self, cap: ReusableCapability) -> None:
        self._capabilities[cap.capability_id] = cap

    def add_track_a(self, record: TrackRecord) -> None:
        record.track = "A"
        self._track_a.append(record)

    def add_track_b(self, record: TrackRecord) -> None:
        record.track = "B"
        self._track_b.append(record)

    def add_records(self, records: list[TrackRecord]) -> None:
        for r in records:
            if r.track == "A":
                self._track_a.append(r)
            else:
                self._track_b.append(r)

    @property
    def track_a_count(self) -> int:
        return len(self._track_a)

    @property
    def track_b_count(self) -> int:
        return len(self._track_b)

    def run(self) -> CapabilityReuseResult:
        """Execute dual-track comparison and compute ROI."""
        if not self._track_a or not self._track_b:
            return CapabilityReuseResult(
                track_a_count=len(self._track_a),
                track_b_count=len(self._track_b),
                verdict="INSUFFICIENT_DATA",
            )

        # Track averages
        a_dur = _avg([r.duration_seconds for r in self._track_a])
        b_dur = _avg([r.duration_seconds for r in self._track_b])
        a_rev = _avg([r.review_rounds for r in self._track_a])
        b_rev = _avg([r.review_rounds for r in self._track_b])
        a_def = _avg([r.defect_count for r in self._track_a])
        b_def = _avg([r.defect_count for r in self._track_b])

        # Percentage improvements (positive = Track A better)
        time_saved = _pct_improvement(b_dur, a_dur)
        review_reduction = _pct_improvement(b_rev, a_rev)
        defect_reduction = _pct_improvement(b_def, a_def)

        # Capability-level ROI
        all_reused = set()
        for r in self._track_a:
            all_reused.update(r.capabilities_reused)

        total_reuses = sum(len(r.capabilities_reused) for r in self._track_a)

        cap_roi_list = []
        for cap_id in all_reused:
            cap = self._capabilities.get(cap_id)
            reuse_count = sum(
                1 for r in self._track_a if cap_id in r.capabilities_reused
            )
            time_contrib = (b_dur - a_dur) * (reuse_count / max(total_reuses, 1))
            review_contrib = (b_rev - a_rev) * (reuse_count / max(total_reuses, 1))
            defect_contrib = (b_def - a_def) * (reuse_count / max(total_reuses, 1))

            benefit = time_contrib + review_contrib + defect_contrib
            roi = benefit / reuse_count if reuse_count > 0 else 0.0

            cap_roi_list.append(CapabilityROI(
                capability_id=cap_id,
                name=cap.name if cap else cap_id,
                reuse_count=reuse_count,
                time_saved_seconds=round(time_contrib, 2),
                review_reduction=round(review_contrib, 2),
                defect_reduction=round(defect_contrib, 2),
                roi=round(roi, 4),
            ))

        # Aggregate ROI
        if total_reuses > 0:
            total_benefit = (b_dur - a_dur) + (b_rev - a_rev) + (b_def - a_def)
            aggregate_roi = total_benefit / total_reuses
        else:
            aggregate_roi = 0.0

        # Verdict
        verdict = self._compute_verdict(time_saved, review_reduction, defect_reduction)

        return CapabilityReuseResult(
            track_a_count=len(self._track_a),
            track_b_count=len(self._track_b),
            track_a_avg_duration=round(a_dur, 2),
            track_b_avg_duration=round(b_dur, 2),
            track_a_avg_reviews=round(a_rev, 2),
            track_b_avg_reviews=round(b_rev, 2),
            track_a_avg_defects=round(a_def, 2),
            track_b_avg_defects=round(b_def, 2),
            time_saved_pct=round(time_saved, 2),
            review_reduction_pct=round(review_reduction, 2),
            defect_reduction_pct=round(defect_reduction, 2),
            total_reuses=total_reuses,
            unique_capabilities_reused=len(all_reused),
            capability_roi=[c.to_dict() for c in cap_roi_list],
            aggregate_roi=round(aggregate_roi, 4),
            verdict=verdict,
        )

    def _compute_verdict(
        self, time_pct: float, review_pct: float, defect_pct: float
    ) -> str:
        """Mechanical verdict based on improvement thresholds."""
        improvements = sum(1 for v in [time_pct, review_pct, defect_pct] if v > 10.0)
        regressions = sum(1 for v in [time_pct, review_pct, defect_pct] if v < -10.0)

        if improvements >= 2 and regressions == 0:
            return "PROVEN"
        if improvements >= 1 and regressions == 0:
            return "PARTIALLY_PROVEN"
        if regressions >= 2:
            return "HARMFUL"
        return "NOT_PROVEN"


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct_improvement(baseline: float, improved: float) -> float:
    """Positive means improvement (improved < baseline)."""
    if baseline == 0:
        return 0.0
    return ((baseline - improved) / baseline) * 100.0
