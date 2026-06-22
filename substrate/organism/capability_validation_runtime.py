"""Capability Validation Runtime — benchmark storage, reporting, and freshness tracking.

Campaign 23A: Capability Compounding Proof. Every metric is numerical.
No subjective scoring. No qualitative ratings. Only measurable data.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

BENCHMARK_TYPES = frozenset({
    "reality_recovery",
    "production_quality",
    "production_velocity",
    "capability_reuse",
    "operator_compression",
    "outcome_quality",
    "compounding",
    "projection_readiness",
    "autonomous_execution",
    "outcome_accuracy",
    "efficiency",
    "reliability",
    "context_capacity",
    "operational_awareness",
    "source_truth",
    "organism_awareness",
    "empire_readiness",
    "model_correspondence",
    "strategic_compression",
    "human_amplification",
    "external_benchmark",
    "competitive_matrix",
})

TRACK_TYPES = frozenset({"reuse_on", "reuse_off", "baseline"})


@dataclass
class BenchmarkRun:
    """Single benchmark execution with numerical results."""

    run_id: str = ""
    benchmark_type: str = ""
    track: str = "baseline"
    timestamp: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            self.run_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkRun:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CapabilityFreshness:
    """Tracks whether a capability is still reliable or has gone stale."""

    capability_id: str = ""
    last_successful_use: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    age_days: float = 0.0
    confidence_score: float = 0.0

    def compute_confidence(self, now: float | None = None) -> float:
        now = now or time.time()
        total = self.success_count + self.failure_count
        if total == 0:
            self.confidence_score = 0.0
            return 0.0

        success_rate = self.success_count / total

        if self.last_successful_use > 0:
            self.age_days = (now - self.last_successful_use) / 86400.0
        recency_weight = max(0.0, 1.0 - (self.age_days / 90.0))

        self.confidence_score = round(success_rate * recency_weight, 4)
        return self.confidence_score

    @property
    def is_stale(self) -> bool:
        return self.confidence_score < 0.3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityFreshness:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CompoundingVerdict:
    PROVEN = "PROVEN"
    PARTIALLY_PROVEN = "PARTIALLY_PROVEN"
    NOT_PROVEN = "NOT_PROVEN"
    HARMFUL = "HARMFUL"


class QualityVerdict:
    POSITIVE_COMPOUNDING = "POSITIVE_COMPOUNDING"
    NEUTRAL_COMPOUNDING = "NEUTRAL_COMPOUNDING"
    NEGATIVE_COMPOUNDING = "NEGATIVE_COMPOUNDING"
    NO_COMPOUNDING = "NO_COMPOUNDING"


@dataclass
class ValidationReport:
    """Complete validation report composing all benchmark results."""

    report_id: str = ""
    timestamp: float = 0.0
    runs: list[dict[str, Any]] = field(default_factory=list)
    compounding_metrics: dict[str, Any] = field(default_factory=dict)
    reuse_metrics: dict[str, Any] = field(default_factory=dict)
    operator_leverage_metrics: dict[str, Any] = field(default_factory=dict)
    outcome_quality_metrics: dict[str, Any] = field(default_factory=dict)
    freshness_alerts: list[dict[str, Any]] = field(default_factory=list)
    projection_readiness: dict[str, Any] = field(default_factory=dict)
    control_comparison: dict[str, Any] = field(default_factory=dict)
    compounding_verdict: str = CompoundingVerdict.NOT_PROVEN
    quality_verdict: str = QualityVerdict.NO_COMPOUNDING
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.report_id:
            self.report_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

class CapabilityValidationRuntime:
    """Stores benchmark runs, computes compounding curves, tracks capability freshness."""

    def __init__(self, store_dir: str | Path = "") -> None:
        self._store_dir = Path(store_dir) if store_dir else Path(_REPO_ROOT) / "data" / "umh" / "validation"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._runs_path = self._store_dir / "benchmark_runs.jsonl"
        self._freshness_path = self._store_dir / "capability_freshness.jsonl"

    # -- Storage --

    def record_run(self, run: BenchmarkRun) -> str:
        """Append a benchmark run to the store. Returns run_id."""
        record = run.to_dict()
        with open(self._runs_path, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")
        logger.info("Recorded benchmark run %s type=%s track=%s", run.run_id, run.benchmark_type, run.track)
        return run.run_id

    def all_runs(self) -> list[BenchmarkRun]:
        """Load all benchmark runs from store."""
        if not self._runs_path.exists():
            return []
        runs: list[BenchmarkRun] = []
        with open(self._runs_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        runs.append(BenchmarkRun.from_dict(json.loads(line)))
                    except Exception as e:
                        logger.debug("Skipping malformed run record: %s", e)
        return runs

    def runs_by_type(self, benchmark_type: str, track: str | None = None) -> list[BenchmarkRun]:
        """Retrieve runs filtered by type and optionally by track."""
        runs = [r for r in self.all_runs() if r.benchmark_type == benchmark_type]
        if track is not None:
            runs = [r for r in runs if r.track == track]
        return sorted(runs, key=lambda r: r.timestamp)

    def latest_run(self, benchmark_type: str, track: str | None = None) -> BenchmarkRun | None:
        """Get the most recent run for a benchmark type."""
        runs = self.runs_by_type(benchmark_type, track)
        return runs[-1] if runs else None

    def run_by_id(self, run_id: str) -> BenchmarkRun | None:
        """Find a specific run by ID."""
        for run in self.all_runs():
            if run.run_id == run_id:
                return run
        return None

    # -- Freshness --

    def record_freshness(self, freshness: CapabilityFreshness) -> None:
        """Append a freshness record."""
        record = freshness.to_dict()
        with open(self._freshness_path, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

    def all_freshness(self) -> list[CapabilityFreshness]:
        """Load all freshness records, keeping latest per capability_id."""
        if not self._freshness_path.exists():
            return []
        latest: dict[str, CapabilityFreshness] = {}
        with open(self._freshness_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        cf = CapabilityFreshness.from_dict(json.loads(line))
                        latest[cf.capability_id] = cf
                    except Exception as e:
                        logger.debug("Skipping malformed freshness record: %s", e)
        return list(latest.values())

    def capability_freshness(self, capability_id: str) -> CapabilityFreshness | None:
        """Get freshness for a specific capability."""
        for cf in self.all_freshness():
            if cf.capability_id == capability_id:
                return cf
        return None

    def stale_capabilities(self, threshold: float = 0.3) -> list[CapabilityFreshness]:
        """Return capabilities with confidence_score below threshold."""
        now = time.time()
        stale: list[CapabilityFreshness] = []
        for cf in self.all_freshness():
            cf.compute_confidence(now)
            if cf.confidence_score < threshold:
                stale.append(cf)
        return stale

    # -- Compounding Curve --

    def compounding_curve(self, benchmark_type: str = "compounding") -> dict[str, Any]:
        """Compute trend across sequential builds for both tracks.

        Returns per-metric values across builds for reuse_on and reuse_off tracks.
        """
        on_runs = self.runs_by_type(benchmark_type, track="reuse_on")
        off_runs = self.runs_by_type(benchmark_type, track="reuse_off")

        def _extract_series(runs: list[BenchmarkRun]) -> dict[str, list[float]]:
            series: dict[str, list[float]] = {}
            for run in runs:
                for key, val in run.metrics.items():
                    series.setdefault(key, []).append(val)
            return series

        return {
            "reuse_on": _extract_series(on_runs),
            "reuse_off": _extract_series(off_runs),
            "reuse_on_count": len(on_runs),
            "reuse_off_count": len(off_runs),
        }

    def control_comparison(self) -> dict[str, Any]:
        """Compare reuse_on vs reuse_off tracks across all benchmark types.

        Returns delta per metric: positive = reuse_on is better.
        """
        result: dict[str, Any] = {}
        for btype in BENCHMARK_TYPES:
            on_runs = self.runs_by_type(btype, track="reuse_on")
            off_runs = self.runs_by_type(btype, track="reuse_off")
            if not on_runs or not off_runs:
                continue

            on_latest = on_runs[-1]
            off_latest = off_runs[-1]

            deltas: dict[str, float] = {}
            for key in on_latest.metrics:
                if key in off_latest.metrics:
                    deltas[key] = round(on_latest.metrics[key] - off_latest.metrics[key], 4)

            result[btype] = {
                "reuse_on": on_latest.metrics,
                "reuse_off": off_latest.metrics,
                "delta": deltas,
            }
        return result

    # -- Compounding Verdict --

    def compute_compounding_verdict(self) -> str:
        """Determine whether compounding is proven based on sequential build metrics.

        Rules:
        - PROVEN: ≥3 of 5 core metrics improve A→C AND Track A > Track B AND quality maintained
        - PARTIALLY_PROVEN: ≥3 improve but control comparison inconclusive
        - NOT_PROVEN: <3 improve or Track B improves equally
        - HARMFUL: metrics improve but quality degrades
        """
        curve = self.compounding_curve()
        on_series = curve.get("reuse_on", {})
        off_series = curve.get("reuse_off", {})

        if not on_series:
            return CompoundingVerdict.NOT_PROVEN

        core_metrics = [
            "production_duration",
            "reuse_pct",
            "operator_touches",
            "net_new_pct",
            "first_pass_rate",
        ]

        improving_count = 0
        control_better_count = 0

        for metric in core_metrics:
            on_vals = on_series.get(metric, [])
            off_vals = off_series.get(metric, [])

            if len(on_vals) < 2:
                continue

            first_val = on_vals[0]
            last_val = on_vals[-1]

            # Lower is better for duration, touches, net_new_pct
            # Higher is better for reuse_pct, first_pass_rate
            lower_is_better = metric in ("production_duration", "operator_touches", "net_new_pct")

            if lower_is_better:
                improved = last_val < first_val
            else:
                improved = last_val > first_val

            if improved:
                improving_count += 1

            # Compare against control
            if off_vals and len(off_vals) >= 2:
                on_delta = last_val - first_val
                off_delta = off_vals[-1] - off_vals[0]
                if lower_is_better:
                    if on_delta < off_delta:
                        control_better_count += 1
                else:
                    if on_delta > off_delta:
                        control_better_count += 1

        # Check quality
        quality_run = self.latest_run("outcome_quality", track="reuse_on")
        quality_degraded = False
        if quality_run:
            defect_trend = quality_run.metrics.get("defect_density_trend", 0.0)
            if defect_trend > 0:
                quality_degraded = True

        if quality_degraded and improving_count >= 3:
            return CompoundingVerdict.HARMFUL

        if improving_count >= 3 and control_better_count >= 3:
            return CompoundingVerdict.PROVEN

        if improving_count >= 3:
            return CompoundingVerdict.PARTIALLY_PROVEN

        return CompoundingVerdict.NOT_PROVEN

    def compute_quality_verdict(self) -> str:
        """Determine whether compounding is positive, neutral, negative, or absent."""
        velocity_run = self.latest_run("production_velocity", track="reuse_on")
        quality_run = self.latest_run("outcome_quality", track="reuse_on")

        if not velocity_run or not quality_run:
            return QualityVerdict.NO_COMPOUNDING

        faster = velocity_run.metrics.get("duration_trend", 0.0) < 0
        better = quality_run.metrics.get("defect_density_trend", 0.0) <= 0

        if faster and better:
            return QualityVerdict.POSITIVE_COMPOUNDING
        if faster and not better:
            return QualityVerdict.NEGATIVE_COMPOUNDING
        if not faster and better:
            return QualityVerdict.NEUTRAL_COMPOUNDING
        return QualityVerdict.NO_COMPOUNDING

    # -- Report Generation --

    def generate_report(self) -> ValidationReport:
        """Compose all benchmark results into a complete ValidationReport."""
        all_runs = self.all_runs()
        stale = self.stale_capabilities()

        # Gather latest per benchmark type
        latest_by_type: dict[str, BenchmarkRun] = {}
        for btype in BENCHMARK_TYPES:
            latest = self.latest_run(btype)
            if latest:
                latest_by_type[btype] = latest

        # Reuse metrics
        reuse_run = latest_by_type.get("capability_reuse")
        reuse_metrics: dict[str, Any] = {}
        if reuse_run:
            reuse_metrics = {
                "reuse_pct": reuse_run.metrics.get("reuse_pct", 0.0),
                "net_new_pct": reuse_run.metrics.get("net_new_pct", 0.0),
                "capability_roi": reuse_run.metrics.get("capability_roi", 0.0),
                "capability_leverage": reuse_run.metrics.get("capability_leverage", 0.0),
            }

        # Operator leverage
        operator_run = latest_by_type.get("operator_compression")
        operator_metrics: dict[str, Any] = {}
        if operator_run:
            operator_metrics = {
                "touches_per_production": operator_run.metrics.get("touches_per_production", 0.0),
                "autonomy_ratio": operator_run.metrics.get("autonomy_ratio", 0.0),
                "correction_rate": operator_run.metrics.get("correction_rate", 0.0),
            }

        # Outcome quality
        quality_run = latest_by_type.get("outcome_quality")
        quality_metrics: dict[str, Any] = {}
        if quality_run:
            quality_metrics = {
                "first_pass_rate": quality_run.metrics.get("first_pass_rate", 0.0),
                "defect_density": quality_run.metrics.get("defect_density", 0.0),
                "rollback_rate": quality_run.metrics.get("rollback_rate", 0.0),
            }

        # Projection readiness
        proj_run = latest_by_type.get("projection_readiness")
        proj_readiness: dict[str, Any] = {}
        if proj_run:
            proj_readiness = proj_run.metrics

        compounding_verdict = self.compute_compounding_verdict()
        quality_verdict = self.compute_quality_verdict()

        recommendations: list[str] = []
        if compounding_verdict == CompoundingVerdict.NOT_PROVEN:
            recommendations.append("Compounding not yet proven. Run sequential builds to generate data.")
        if compounding_verdict == CompoundingVerdict.HARMFUL:
            recommendations.append("ALERT: Negative compounding detected. Quality is degrading with speed.")
        if stale:
            recommendations.append(f"{len(stale)} stale capabilities detected. Review before reuse.")
        if reuse_metrics.get("capability_roi", 0.0) <= 0 and reuse_metrics.get("reuse_pct", 0.0) > 0:
            recommendations.append("Reuse is occurring but ROI is zero or negative. Investigate reuse quality.")

        return ValidationReport(
            runs=[r.to_dict() for r in all_runs[-20:]],
            compounding_metrics=self.compounding_curve(),
            reuse_metrics=reuse_metrics,
            operator_leverage_metrics=operator_metrics,
            outcome_quality_metrics=quality_metrics,
            freshness_alerts=[cf.to_dict() for cf in stale],
            projection_readiness=proj_readiness,
            control_comparison=self.control_comparison(),
            compounding_verdict=compounding_verdict,
            quality_verdict=quality_verdict,
            recommendations=recommendations,
        )

    # -- Summary --

    def summary(self) -> str:
        """One-line health assessment."""
        runs = self.all_runs()
        if not runs:
            return "No benchmark data. Run benchmarks to begin validation."

        types_covered = {r.benchmark_type for r in runs}
        verdict = self.compute_compounding_verdict()
        stale_count = len(self.stale_capabilities())

        return (
            f"Benchmarks: {len(runs)} runs across {len(types_covered)} types. "
            f"Verdict: {verdict}. "
            f"Stale capabilities: {stale_count}."
        )
