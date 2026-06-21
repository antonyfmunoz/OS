"""Benchmark 7 — Compounding Proof (Integration).

Orchestrates all benchmarks across 3 sequential builds with dual-track
(reuse ON vs OFF) control comparison. Produces the compounding curve
and final verdict.

All metrics numerical. No subjective scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BuildMetrics:
    """Metrics captured for a single build in the compounding experiment."""

    build_id: str = ""
    build_number: int = 0
    track: str = "baseline"  # "reuse_on" or "reuse_off"
    production_duration: float = 0.0
    reuse_pct: float = 0.0
    capability_roi: float = 0.0
    operator_touches: int = 0
    review_cycles: int = 0
    defects_found: int = 0
    first_pass_rate: float = 0.0
    net_new_pct: float = 1.0
    total_code_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "build_id": self.build_id,
            "build_number": self.build_number,
            "track": self.track,
            "production_duration": self.production_duration,
            "reuse_pct": self.reuse_pct,
            "capability_roi": self.capability_roi,
            "operator_touches": self.operator_touches,
            "review_cycles": self.review_cycles,
            "defects_found": self.defects_found,
            "first_pass_rate": self.first_pass_rate,
            "net_new_pct": self.net_new_pct,
            "total_code_lines": self.total_code_lines,
        }


class CompoundingVerdict:
    PROVEN = "PROVEN"
    PARTIALLY_PROVEN = "PARTIALLY_PROVEN"
    NOT_PROVEN = "NOT_PROVEN"
    HARMFUL = "HARMFUL"


@dataclass
class CompoundingCurve:
    """Trend data for a single metric across builds."""

    metric_name: str = ""
    reuse_on_values: list[float] = field(default_factory=list)
    reuse_off_values: list[float] = field(default_factory=list)
    on_improved: bool = False
    on_better_than_off: bool = False
    lower_is_better: bool = True

    def compute(self) -> None:
        """Compute whether the metric improved and whether ON beat OFF."""
        if len(self.reuse_on_values) < 2:
            return

        first = self.reuse_on_values[0]
        last = self.reuse_on_values[-1]

        if self.lower_is_better:
            self.on_improved = last < first
        else:
            self.on_improved = last > first

        if self.reuse_off_values and len(self.reuse_off_values) >= 2:
            on_delta = last - first
            off_first = self.reuse_off_values[0]
            off_last = self.reuse_off_values[-1]
            off_delta = off_last - off_first

            if self.lower_is_better:
                self.on_better_than_off = on_delta < off_delta
            else:
                self.on_better_than_off = on_delta > off_delta

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "reuse_on_values": self.reuse_on_values,
            "reuse_off_values": self.reuse_off_values,
            "on_improved": self.on_improved,
            "on_better_than_off": self.on_better_than_off,
            "lower_is_better": self.lower_is_better,
        }


@dataclass
class CompoundingProofResult:
    """Final result of the compounding proof experiment."""

    verdict: str = CompoundingVerdict.NOT_PROVEN
    curves: list[dict[str, Any]] = field(default_factory=list)
    metrics_improved: int = 0
    metrics_beat_control: int = 0
    total_core_metrics: int = 5
    quality_degraded: bool = False
    builds_on: list[dict[str, Any]] = field(default_factory=list)
    builds_off: list[dict[str, Any]] = field(default_factory=list)
    control_delta: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "curves": self.curves,
            "metrics_improved": self.metrics_improved,
            "metrics_beat_control": self.metrics_beat_control,
            "total_core_metrics": self.total_core_metrics,
            "quality_degraded": self.quality_degraded,
            "control_delta": self.control_delta,
        }


# ---------------------------------------------------------------------------
# Core metrics definition
# ---------------------------------------------------------------------------

CORE_METRICS = [
    {"name": "production_duration", "lower_is_better": True},
    {"name": "reuse_pct", "lower_is_better": False},
    {"name": "operator_touches", "lower_is_better": True},
    {"name": "net_new_pct", "lower_is_better": True},
    {"name": "first_pass_rate", "lower_is_better": False},
]


class CompoundingProofBenchmark:
    """Orchestrates the compounding proof across sequential builds."""

    def evaluate(
        self,
        builds_on: list[BuildMetrics],
        builds_off: list[BuildMetrics],
    ) -> CompoundingProofResult:
        """Evaluate compounding across dual-track sequential builds.

        Args:
            builds_on: Sequential builds with reuse enabled (A1, A2, A3).
            builds_off: Sequential builds with reuse disabled (B1, B2, B3).

        Returns:
            CompoundingProofResult with verdict, curves, and control delta.
        """
        result = CompoundingProofResult(
            builds_on=[b.to_dict() for b in builds_on],
            builds_off=[b.to_dict() for b in builds_off],
        )

        if len(builds_on) < 2:
            result.verdict = CompoundingVerdict.NOT_PROVEN
            return result

        # Compute curves for each core metric
        curves: list[CompoundingCurve] = []
        for metric_def in CORE_METRICS:
            name = metric_def["name"]
            lower = metric_def["lower_is_better"]

            curve = CompoundingCurve(
                metric_name=name,
                reuse_on_values=[getattr(b, name, 0) for b in builds_on],
                reuse_off_values=[getattr(b, name, 0) for b in builds_off] if builds_off else [],
                lower_is_better=lower,
            )
            curve.compute()
            curves.append(curve)

        result.curves = [c.to_dict() for c in curves]
        result.metrics_improved = sum(1 for c in curves if c.on_improved)
        result.metrics_beat_control = sum(1 for c in curves if c.on_better_than_off)

        # Check quality degradation
        on_first = builds_on[0]
        on_last = builds_on[-1]
        if on_last.defects_found > on_first.defects_found:
            result.quality_degraded = True

        # Control delta: last build ON vs last build OFF
        if builds_off:
            off_last = builds_off[-1]
            result.control_delta = {
                "production_duration": round(on_last.production_duration - off_last.production_duration, 2),
                "reuse_pct": round(on_last.reuse_pct - off_last.reuse_pct, 4),
                "operator_touches": on_last.operator_touches - off_last.operator_touches,
                "net_new_pct": round(on_last.net_new_pct - off_last.net_new_pct, 4),
                "first_pass_rate": round(on_last.first_pass_rate - off_last.first_pass_rate, 4),
            }

        # Verdict
        if result.quality_degraded and result.metrics_improved >= 3:
            result.verdict = CompoundingVerdict.HARMFUL
        elif result.metrics_improved >= 3 and result.metrics_beat_control >= 3:
            result.verdict = CompoundingVerdict.PROVEN
        elif result.metrics_improved >= 3:
            result.verdict = CompoundingVerdict.PARTIALLY_PROVEN
        else:
            result.verdict = CompoundingVerdict.NOT_PROVEN

        return result
