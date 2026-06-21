"""Benchmark 6 — Production Outcome Quality.

Measures whether fast+reuse degrades actual output quality.
Compares Track A (reuse ON) vs Track B (reuse OFF) outcomes.
Quality = defect-free AND meets acceptance criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion for a production."""

    criterion_id: str = ""
    description: str = ""
    met: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "description": self.description,
            "met": self.met,
        }


@dataclass
class ProductionOutcome:
    """Observed outcome of a single production run."""

    production_id: str = ""
    track: str = ""  # "reuse_on" or "reuse_off"
    defect_count: int = 0
    test_pass_count: int = 0
    test_total_count: int = 0
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    lines_of_code: int = 0
    rework_count: int = 0

    @property
    def test_pass_rate(self) -> float:
        if self.test_total_count == 0:
            return 0.0
        return self.test_pass_count / self.test_total_count

    @property
    def acceptance_rate(self) -> float:
        if not self.acceptance_criteria:
            return 0.0
        met = sum(1 for c in self.acceptance_criteria if c.met)
        return met / len(self.acceptance_criteria)

    @property
    def defect_density(self) -> float:
        if self.lines_of_code == 0:
            return 0.0
        return self.defect_count / (self.lines_of_code / 1000.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_id": self.production_id,
            "track": self.track,
            "defect_count": self.defect_count,
            "test_pass_rate": round(self.test_pass_rate, 4),
            "acceptance_rate": round(self.acceptance_rate, 4),
            "defect_density": round(self.defect_density, 4),
            "lines_of_code": self.lines_of_code,
            "rework_count": self.rework_count,
        }


@dataclass
class TrackMetrics:
    """Aggregated metrics for one track."""

    track: str = ""
    productions: int = 0
    avg_test_pass_rate: float = 0.0
    avg_acceptance_rate: float = 0.0
    avg_defect_density: float = 0.0
    avg_rework_count: float = 0.0
    total_defects: int = 0

    def to_dict(self) -> dict[str, float]:
        return {
            "track": self.track,
            "productions": self.productions,
            "avg_test_pass_rate": round(self.avg_test_pass_rate, 4),
            "avg_acceptance_rate": round(self.avg_acceptance_rate, 4),
            "avg_defect_density": round(self.avg_defect_density, 4),
            "avg_rework_count": round(self.avg_rework_count, 4),
            "total_defects": self.total_defects,
        }


@dataclass
class QualityComparison:
    """Comparison between Track A (reuse ON) and Track B (reuse OFF)."""

    track_a: TrackMetrics = field(default_factory=TrackMetrics)
    track_b: TrackMetrics = field(default_factory=TrackMetrics)
    test_pass_delta: float = 0.0
    acceptance_delta: float = 0.0
    defect_density_delta: float = 0.0
    rework_delta: float = 0.0
    quality_verdict: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_a": self.track_a.to_dict(),
            "track_b": self.track_b.to_dict(),
            "deltas": {
                "test_pass_delta": round(self.test_pass_delta, 4),
                "acceptance_delta": round(self.acceptance_delta, 4),
                "defect_density_delta": round(self.defect_density_delta, 4),
                "rework_delta": round(self.rework_delta, 4),
            },
            "quality_verdict": self.quality_verdict,
        }


@dataclass
class ProductionOutcomeResult:
    """Complete benchmark result."""

    total_outcomes: int = 0
    comparison: QualityComparison = field(default_factory=QualityComparison)
    per_production: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_outcomes": self.total_outcomes,
            "comparison": self.comparison.to_dict(),
            "per_production": self.per_production,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class ProductionOutcomeQualityBenchmark:
    """Measures whether reuse degrades production quality."""

    @staticmethod
    def compute_track_metrics(outcomes: list[ProductionOutcome], track: str) -> TrackMetrics:
        """Compute aggregate metrics for a single track."""
        filtered = [o for o in outcomes if o.track == track]
        if not filtered:
            return TrackMetrics(track=track)

        n = len(filtered)
        return TrackMetrics(
            track=track,
            productions=n,
            avg_test_pass_rate=sum(o.test_pass_rate for o in filtered) / n,
            avg_acceptance_rate=sum(o.acceptance_rate for o in filtered) / n,
            avg_defect_density=sum(o.defect_density for o in filtered) / n,
            avg_rework_count=sum(o.rework_count for o in filtered) / n,
            total_defects=sum(o.defect_count for o in filtered),
        )

    @classmethod
    def compute_quality_verdict(
        cls,
        track_a: TrackMetrics,
        track_b: TrackMetrics,
    ) -> str:
        """Determine quality verdict from track comparison.

        POSITIVE_COMPOUNDING: reuse improves quality (fewer defects, higher pass rates)
        NEUTRAL_COMPOUNDING: quality unchanged
        NEGATIVE_COMPOUNDING: reuse degrades quality
        NO_COMPOUNDING: insufficient data
        """
        if track_a.productions < 1 or track_b.productions < 1:
            return "NO_COMPOUNDING"

        improvements = 0
        degradations = 0
        threshold = 0.02  # 2% significance threshold

        # Test pass rate: higher is better
        if track_a.avg_test_pass_rate - track_b.avg_test_pass_rate > threshold:
            improvements += 1
        elif track_b.avg_test_pass_rate - track_a.avg_test_pass_rate > threshold:
            degradations += 1

        # Acceptance rate: higher is better
        if track_a.avg_acceptance_rate - track_b.avg_acceptance_rate > threshold:
            improvements += 1
        elif track_b.avg_acceptance_rate - track_a.avg_acceptance_rate > threshold:
            degradations += 1

        # Defect density: lower is better (negative delta = improvement)
        density_diff = track_a.avg_defect_density - track_b.avg_defect_density
        if density_diff < -threshold:
            improvements += 1
        elif density_diff > threshold:
            degradations += 1

        # Rework count: lower is better
        rework_diff = track_a.avg_rework_count - track_b.avg_rework_count
        if rework_diff < -0.5:
            improvements += 1
        elif rework_diff > 0.5:
            degradations += 1

        if degradations > improvements:
            return "NEGATIVE_COMPOUNDING"
        if improvements > degradations:
            return "POSITIVE_COMPOUNDING"
        return "NEUTRAL_COMPOUNDING"

    def run(self, outcomes: list[ProductionOutcome]) -> ProductionOutcomeResult:
        """Run the benchmark across all production outcomes."""
        if not outcomes:
            return ProductionOutcomeResult()

        track_a = self.compute_track_metrics(outcomes, "reuse_on")
        track_b = self.compute_track_metrics(outcomes, "reuse_off")

        verdict = self.compute_quality_verdict(track_a, track_b)

        comparison = QualityComparison(
            track_a=track_a,
            track_b=track_b,
            test_pass_delta=track_a.avg_test_pass_rate - track_b.avg_test_pass_rate,
            acceptance_delta=track_a.avg_acceptance_rate - track_b.avg_acceptance_rate,
            defect_density_delta=track_a.avg_defect_density - track_b.avg_defect_density,
            rework_delta=track_a.avg_rework_count - track_b.avg_rework_count,
            quality_verdict=verdict,
        )

        per_production = [o.to_dict() for o in outcomes]

        return ProductionOutcomeResult(
            total_outcomes=len(outcomes),
            comparison=comparison,
            per_production=per_production,
        )
