"""Tests for CapabilityValidationRuntime — C23A Phase 1."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.capability_validation_runtime import (
    BENCHMARK_TYPES,
    BenchmarkRun,
    CapabilityFreshness,
    CapabilityValidationRuntime,
    CompoundingVerdict,
    QualityVerdict,
    ValidationReport,
)


@pytest.fixture
def tmp_store(tmp_path):
    return CapabilityValidationRuntime(store_dir=str(tmp_path))


# -- BenchmarkRun --

class TestBenchmarkRun:
    def test_auto_generates_id(self):
        run = BenchmarkRun(benchmark_type="reality_recovery")
        assert run.run_id
        assert len(run.run_id) > 10

    def test_auto_generates_timestamp(self):
        run = BenchmarkRun(benchmark_type="reality_recovery")
        assert run.timestamp > 0

    def test_to_dict_roundtrip(self):
        run = BenchmarkRun(
            benchmark_type="production_quality",
            track="baseline",
            metrics={"precision": 0.9, "recall": 0.8},
            outcomes=[{"question": "q1", "correct": True}],
        )
        d = run.to_dict()
        restored = BenchmarkRun.from_dict(d)
        assert restored.benchmark_type == "production_quality"
        assert restored.metrics["precision"] == 0.9
        assert restored.track == "baseline"

    def test_default_track_is_baseline(self):
        run = BenchmarkRun(benchmark_type="reality_recovery")
        assert run.track == "baseline"


# -- CapabilityFreshness --

class TestCapabilityFreshness:
    def test_confidence_with_recent_success(self):
        now = time.time()
        cf = CapabilityFreshness(
            capability_id="cap1",
            last_successful_use=now - 3600,  # 1 hour ago
            success_count=9,
            failure_count=1,
        )
        score = cf.compute_confidence(now)
        assert score > 0.8  # 90% success, very recent

    def test_confidence_decays_with_age(self):
        now = time.time()
        cf_recent = CapabilityFreshness(
            capability_id="cap1",
            last_successful_use=now - 86400,  # 1 day ago
            success_count=10,
            failure_count=0,
        )
        cf_old = CapabilityFreshness(
            capability_id="cap2",
            last_successful_use=now - (80 * 86400),  # 80 days ago
            success_count=10,
            failure_count=0,
        )
        cf_recent.compute_confidence(now)
        cf_old.compute_confidence(now)
        assert cf_recent.confidence_score > cf_old.confidence_score

    def test_confidence_zero_at_90_days(self):
        now = time.time()
        cf = CapabilityFreshness(
            capability_id="cap1",
            last_successful_use=now - (91 * 86400),
            success_count=10,
            failure_count=0,
        )
        score = cf.compute_confidence(now)
        assert score == 0.0

    def test_confidence_zero_with_no_uses(self):
        cf = CapabilityFreshness(capability_id="cap1")
        score = cf.compute_confidence()
        assert score == 0.0

    def test_is_stale_threshold(self):
        now = time.time()
        cf = CapabilityFreshness(
            capability_id="cap1",
            last_successful_use=now - (85 * 86400),
            success_count=5,
            failure_count=5,
        )
        cf.compute_confidence(now)
        assert cf.is_stale

    def test_not_stale_when_fresh(self):
        now = time.time()
        cf = CapabilityFreshness(
            capability_id="cap1",
            last_successful_use=now - 3600,
            success_count=10,
            failure_count=0,
        )
        cf.compute_confidence(now)
        assert not cf.is_stale

    def test_roundtrip(self):
        cf = CapabilityFreshness(capability_id="test", success_count=5, failure_count=2)
        d = cf.to_dict()
        restored = CapabilityFreshness.from_dict(d)
        assert restored.capability_id == "test"
        assert restored.success_count == 5


# -- Storage --

class TestStorage:
    def test_record_and_retrieve(self, tmp_store):
        run = BenchmarkRun(
            benchmark_type="reality_recovery",
            metrics={"accuracy": 0.92},
        )
        run_id = tmp_store.record_run(run)
        assert run_id == run.run_id

        all_runs = tmp_store.all_runs()
        assert len(all_runs) == 1
        assert all_runs[0].metrics["accuracy"] == 0.92

    def test_multiple_runs(self, tmp_store):
        for i in range(5):
            tmp_store.record_run(BenchmarkRun(
                benchmark_type="reality_recovery",
                metrics={"accuracy": 0.8 + i * 0.02},
            ))
        assert len(tmp_store.all_runs()) == 5

    def test_runs_by_type_filters(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(benchmark_type="reality_recovery", metrics={"a": 1}))
        tmp_store.record_run(BenchmarkRun(benchmark_type="production_quality", metrics={"b": 2}))
        tmp_store.record_run(BenchmarkRun(benchmark_type="reality_recovery", metrics={"c": 3}))

        rr_runs = tmp_store.runs_by_type("reality_recovery")
        assert len(rr_runs) == 2
        pq_runs = tmp_store.runs_by_type("production_quality")
        assert len(pq_runs) == 1

    def test_runs_by_type_and_track(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(benchmark_type="capability_reuse", track="reuse_on", metrics={"a": 1}))
        tmp_store.record_run(BenchmarkRun(benchmark_type="capability_reuse", track="reuse_off", metrics={"b": 2}))
        tmp_store.record_run(BenchmarkRun(benchmark_type="capability_reuse", track="reuse_on", metrics={"c": 3}))

        on_runs = tmp_store.runs_by_type("capability_reuse", track="reuse_on")
        assert len(on_runs) == 2
        off_runs = tmp_store.runs_by_type("capability_reuse", track="reuse_off")
        assert len(off_runs) == 1

    def test_latest_run(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(benchmark_type="reality_recovery", timestamp=100, metrics={"a": 1}))
        tmp_store.record_run(BenchmarkRun(benchmark_type="reality_recovery", timestamp=200, metrics={"b": 2}))
        latest = tmp_store.latest_run("reality_recovery")
        assert latest is not None
        assert latest.metrics["b"] == 2

    def test_latest_run_none_when_empty(self, tmp_store):
        assert tmp_store.latest_run("reality_recovery") is None

    def test_run_by_id(self, tmp_store):
        run = BenchmarkRun(benchmark_type="reality_recovery", metrics={"x": 42})
        tmp_store.record_run(run)
        found = tmp_store.run_by_id(run.run_id)
        assert found is not None
        assert found.metrics["x"] == 42

    def test_run_by_id_not_found(self, tmp_store):
        assert tmp_store.run_by_id("nonexistent") is None

    def test_empty_store_returns_empty(self, tmp_store):
        assert tmp_store.all_runs() == []
        assert tmp_store.all_freshness() == []


# -- Freshness Storage --

class TestFreshnessStorage:
    def test_record_and_retrieve_freshness(self, tmp_store):
        cf = CapabilityFreshness(
            capability_id="cap1",
            success_count=10,
            failure_count=2,
            last_successful_use=time.time(),
        )
        tmp_store.record_freshness(cf)
        all_cf = tmp_store.all_freshness()
        assert len(all_cf) == 1
        assert all_cf[0].capability_id == "cap1"

    def test_latest_per_capability(self, tmp_store):
        tmp_store.record_freshness(CapabilityFreshness(capability_id="cap1", success_count=5))
        tmp_store.record_freshness(CapabilityFreshness(capability_id="cap1", success_count=10))
        all_cf = tmp_store.all_freshness()
        assert len(all_cf) == 1
        assert all_cf[0].success_count == 10

    def test_stale_capabilities(self, tmp_store):
        now = time.time()
        tmp_store.record_freshness(CapabilityFreshness(
            capability_id="fresh", success_count=10, failure_count=0,
            last_successful_use=now - 3600,
        ))
        tmp_store.record_freshness(CapabilityFreshness(
            capability_id="stale", success_count=5, failure_count=5,
            last_successful_use=now - (85 * 86400),
        ))
        stale = tmp_store.stale_capabilities()
        assert len(stale) == 1
        assert stale[0].capability_id == "stale"

    def test_capability_freshness_lookup(self, tmp_store):
        tmp_store.record_freshness(CapabilityFreshness(capability_id="cap1", success_count=7))
        cf = tmp_store.capability_freshness("cap1")
        assert cf is not None
        assert cf.success_count == 7

    def test_capability_freshness_not_found(self, tmp_store):
        assert tmp_store.capability_freshness("nonexistent") is None


# -- Compounding Curve --

class TestCompoundingCurve:
    def test_empty_curve(self, tmp_store):
        curve = tmp_store.compounding_curve()
        assert curve["reuse_on"] == {}
        assert curve["reuse_off"] == {}

    def test_curve_with_data(self, tmp_store):
        for i, dur in enumerate([100, 80, 60]):
            tmp_store.record_run(BenchmarkRun(
                benchmark_type="compounding", track="reuse_on",
                timestamp=1000 + i, metrics={"production_duration": dur},
            ))
        for i, dur in enumerate([100, 95, 90]):
            tmp_store.record_run(BenchmarkRun(
                benchmark_type="compounding", track="reuse_off",
                timestamp=1000 + i, metrics={"production_duration": dur},
            ))
        curve = tmp_store.compounding_curve()
        assert curve["reuse_on"]["production_duration"] == [100, 80, 60]
        assert curve["reuse_off"]["production_duration"] == [100, 95, 90]


# -- Control Comparison --

class TestControlComparison:
    def test_empty_comparison(self, tmp_store):
        assert tmp_store.control_comparison() == {}

    def test_comparison_with_data(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="capability_reuse", track="reuse_on",
            metrics={"reuse_pct": 0.4},
        ))
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="capability_reuse", track="reuse_off",
            metrics={"reuse_pct": 0.0},
        ))
        comp = tmp_store.control_comparison()
        assert "capability_reuse" in comp
        assert comp["capability_reuse"]["delta"]["reuse_pct"] == 0.4


# -- Verdicts --

class TestVerdicts:
    def test_not_proven_when_empty(self, tmp_store):
        assert tmp_store.compute_compounding_verdict() == CompoundingVerdict.NOT_PROVEN

    def test_proven_when_metrics_improve(self, tmp_store):
        metrics_a = {"production_duration": 100, "reuse_pct": 0.0, "operator_touches": 10, "net_new_pct": 1.0, "first_pass_rate": 0.5}
        metrics_c = {"production_duration": 60, "reuse_pct": 0.4, "operator_touches": 4, "net_new_pct": 0.6, "first_pass_rate": 0.9}

        # Reuse ON track improves
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_on", timestamp=100, metrics=metrics_a))
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_on", timestamp=200, metrics=metrics_c))

        # Reuse OFF track doesn't improve as much
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_off", timestamp=100, metrics=metrics_a))
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_off", timestamp=200, metrics={
            "production_duration": 95, "reuse_pct": 0.0, "operator_touches": 9, "net_new_pct": 0.95, "first_pass_rate": 0.55,
        }))

        assert tmp_store.compute_compounding_verdict() == CompoundingVerdict.PROVEN

    def test_harmful_when_quality_degrades(self, tmp_store):
        metrics_a = {"production_duration": 100, "reuse_pct": 0.0, "operator_touches": 10, "net_new_pct": 1.0, "first_pass_rate": 0.5}
        metrics_c = {"production_duration": 60, "reuse_pct": 0.4, "operator_touches": 4, "net_new_pct": 0.6, "first_pass_rate": 0.9}

        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_on", timestamp=100, metrics=metrics_a))
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_on", timestamp=200, metrics=metrics_c))
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_off", timestamp=100, metrics=metrics_a))
        tmp_store.record_run(BenchmarkRun(benchmark_type="compounding", track="reuse_off", timestamp=200, metrics=metrics_a))

        # Quality degraded
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="outcome_quality", track="reuse_on",
            metrics={"defect_density_trend": 0.5},
        ))

        assert tmp_store.compute_compounding_verdict() == CompoundingVerdict.HARMFUL

    def test_quality_verdict_positive(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="production_velocity", track="reuse_on",
            metrics={"duration_trend": -0.3},
        ))
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="outcome_quality", track="reuse_on",
            metrics={"defect_density_trend": -0.1},
        ))
        assert tmp_store.compute_quality_verdict() == QualityVerdict.POSITIVE_COMPOUNDING

    def test_quality_verdict_negative(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="production_velocity", track="reuse_on",
            metrics={"duration_trend": -0.3},
        ))
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="outcome_quality", track="reuse_on",
            metrics={"defect_density_trend": 0.5},
        ))
        assert tmp_store.compute_quality_verdict() == QualityVerdict.NEGATIVE_COMPOUNDING

    def test_quality_verdict_no_compounding(self, tmp_store):
        assert tmp_store.compute_quality_verdict() == QualityVerdict.NO_COMPOUNDING


# -- Report Generation --

class TestReportGeneration:
    def test_empty_report(self, tmp_store):
        report = tmp_store.generate_report()
        assert report.compounding_verdict == CompoundingVerdict.NOT_PROVEN
        assert len(report.recommendations) > 0

    def test_report_with_data(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="reality_recovery", metrics={"accuracy": 0.92},
        ))
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="capability_reuse", metrics={"reuse_pct": 0.3, "capability_roi": 1.5},
        ))
        tmp_store.record_run(BenchmarkRun(
            benchmark_type="operator_compression", metrics={"touches_per_production": 5, "autonomy_ratio": 0.7},
        ))
        report = tmp_store.generate_report()
        assert report.reuse_metrics["reuse_pct"] == 0.3
        assert report.operator_leverage_metrics["touches_per_production"] == 5
        assert len(report.runs) == 3

    def test_report_includes_freshness_alerts(self, tmp_store):
        now = time.time()
        tmp_store.record_freshness(CapabilityFreshness(
            capability_id="stale_cap", success_count=3, failure_count=7,
            last_successful_use=now - (80 * 86400),
        ))
        report = tmp_store.generate_report()
        assert len(report.freshness_alerts) == 1

    def test_report_to_dict(self, tmp_store):
        report = tmp_store.generate_report()
        d = report.to_dict()
        assert "compounding_verdict" in d
        assert "recommendations" in d


# -- Summary --

class TestSummary:
    def test_empty_summary(self, tmp_store):
        s = tmp_store.summary()
        assert "No benchmark data" in s

    def test_summary_with_data(self, tmp_store):
        tmp_store.record_run(BenchmarkRun(benchmark_type="reality_recovery", metrics={"a": 1}))
        s = tmp_store.summary()
        assert "1 runs" in s
        assert "1 types" in s
