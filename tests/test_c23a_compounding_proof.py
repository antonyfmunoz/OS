"""Tests for Compounding Proof Benchmark — C23A Phase 8."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.benchmarks.compounding_proof import (
    BuildMetrics,
    CompoundingCurve,
    CompoundingProofBenchmark,
    CompoundingProofResult,
    CompoundingVerdict,
    CORE_METRICS,
)


@pytest.fixture
def benchmark():
    return CompoundingProofBenchmark()


class TestBuildMetrics:
    def test_defaults(self):
        m = BuildMetrics()
        assert m.build_id == ""
        assert m.track == "baseline"
        assert m.production_duration == 0.0
        assert m.net_new_pct == 1.0

    def test_to_dict(self):
        m = BuildMetrics(build_id="b1", build_number=1, track="reuse_on")
        d = m.to_dict()
        assert d["build_id"] == "b1"
        assert d["track"] == "reuse_on"
        assert d["build_number"] == 1

    def test_all_fields_in_dict(self):
        m = BuildMetrics()
        d = m.to_dict()
        expected = {
            "build_id", "build_number", "track", "production_duration",
            "reuse_pct", "capability_roi", "operator_touches",
            "review_cycles", "defects_found", "first_pass_rate",
            "net_new_pct", "total_code_lines",
        }
        assert set(d.keys()) == expected


class TestCompoundingCurve:
    def test_improving_lower_is_better(self):
        curve = CompoundingCurve(
            metric_name="production_duration",
            reuse_on_values=[100.0, 80.0, 60.0],
            reuse_off_values=[100.0, 95.0, 90.0],
            lower_is_better=True,
        )
        curve.compute()
        assert curve.on_improved is True
        assert curve.on_better_than_off is True

    def test_improving_higher_is_better(self):
        curve = CompoundingCurve(
            metric_name="reuse_pct",
            reuse_on_values=[0.1, 0.3, 0.5],
            reuse_off_values=[0.0, 0.0, 0.0],
            lower_is_better=False,
        )
        curve.compute()
        assert curve.on_improved is True
        assert curve.on_better_than_off is True

    def test_not_improving(self):
        curve = CompoundingCurve(
            metric_name="production_duration",
            reuse_on_values=[60.0, 80.0, 100.0],
            lower_is_better=True,
        )
        curve.compute()
        assert curve.on_improved is False

    def test_no_control_data(self):
        curve = CompoundingCurve(
            metric_name="reuse_pct",
            reuse_on_values=[0.1, 0.3, 0.5],
            reuse_off_values=[],
            lower_is_better=False,
        )
        curve.compute()
        assert curve.on_improved is True
        assert curve.on_better_than_off is False

    def test_insufficient_data(self):
        curve = CompoundingCurve(
            metric_name="test",
            reuse_on_values=[1.0],
            lower_is_better=True,
        )
        curve.compute()
        assert curve.on_improved is False

    def test_to_dict(self):
        curve = CompoundingCurve(metric_name="test", reuse_on_values=[1.0, 2.0])
        d = curve.to_dict()
        assert d["metric_name"] == "test"
        assert d["reuse_on_values"] == [1.0, 2.0]


class TestCompoundingProofBenchmark:
    def test_proven_verdict(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on",
                         production_duration=100, reuse_pct=0.1, operator_touches=10,
                         net_new_pct=0.9, first_pass_rate=0.6, defects_found=3),
            BuildMetrics(build_id="a2", build_number=2, track="reuse_on",
                         production_duration=80, reuse_pct=0.3, operator_touches=7,
                         net_new_pct=0.7, first_pass_rate=0.8, defects_found=2),
            BuildMetrics(build_id="a3", build_number=3, track="reuse_on",
                         production_duration=60, reuse_pct=0.5, operator_touches=5,
                         net_new_pct=0.5, first_pass_rate=0.9, defects_found=1),
        ]
        builds_off = [
            BuildMetrics(build_id="b1", build_number=1, track="reuse_off",
                         production_duration=100, reuse_pct=0.0, operator_touches=10,
                         net_new_pct=1.0, first_pass_rate=0.6, defects_found=3),
            BuildMetrics(build_id="b2", build_number=2, track="reuse_off",
                         production_duration=95, reuse_pct=0.0, operator_touches=9,
                         net_new_pct=0.95, first_pass_rate=0.65, defects_found=3),
            BuildMetrics(build_id="b3", build_number=3, track="reuse_off",
                         production_duration=90, reuse_pct=0.0, operator_touches=8,
                         net_new_pct=0.9, first_pass_rate=0.7, defects_found=3),
        ]
        result = benchmark.evaluate(builds_on, builds_off)
        assert result.verdict == CompoundingVerdict.PROVEN
        assert result.metrics_improved >= 3
        assert result.metrics_beat_control >= 3
        assert result.quality_degraded is False

    def test_partially_proven_verdict(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on",
                         production_duration=100, reuse_pct=0.1, operator_touches=10,
                         net_new_pct=0.9, first_pass_rate=0.6, defects_found=3),
            BuildMetrics(build_id="a2", build_number=2, track="reuse_on",
                         production_duration=80, reuse_pct=0.3, operator_touches=7,
                         net_new_pct=0.7, first_pass_rate=0.8, defects_found=2),
            BuildMetrics(build_id="a3", build_number=3, track="reuse_on",
                         production_duration=60, reuse_pct=0.5, operator_touches=5,
                         net_new_pct=0.5, first_pass_rate=0.9, defects_found=1),
        ]
        # No control data → partially proven at best
        result = benchmark.evaluate(builds_on, [])
        assert result.verdict == CompoundingVerdict.PARTIALLY_PROVEN
        assert result.metrics_improved >= 3

    def test_not_proven_verdict(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on",
                         production_duration=60, reuse_pct=0.5, operator_touches=5,
                         net_new_pct=0.5, first_pass_rate=0.9, defects_found=1),
            BuildMetrics(build_id="a2", build_number=2, track="reuse_on",
                         production_duration=80, reuse_pct=0.3, operator_touches=7,
                         net_new_pct=0.7, first_pass_rate=0.7, defects_found=2),
            BuildMetrics(build_id="a3", build_number=3, track="reuse_on",
                         production_duration=100, reuse_pct=0.1, operator_touches=10,
                         net_new_pct=0.9, first_pass_rate=0.5, defects_found=3),
        ]
        result = benchmark.evaluate(builds_on, [])
        assert result.verdict == CompoundingVerdict.NOT_PROVEN
        assert result.metrics_improved < 3

    def test_harmful_verdict(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on",
                         production_duration=100, reuse_pct=0.1, operator_touches=10,
                         net_new_pct=0.9, first_pass_rate=0.8, defects_found=1),
            BuildMetrics(build_id="a2", build_number=2, track="reuse_on",
                         production_duration=80, reuse_pct=0.3, operator_touches=7,
                         net_new_pct=0.7, first_pass_rate=0.7, defects_found=3),
            BuildMetrics(build_id="a3", build_number=3, track="reuse_on",
                         production_duration=60, reuse_pct=0.5, operator_touches=5,
                         net_new_pct=0.5, first_pass_rate=0.6, defects_found=5),
        ]
        result = benchmark.evaluate(builds_on, [])
        assert result.verdict == CompoundingVerdict.HARMFUL
        assert result.quality_degraded is True

    def test_insufficient_builds(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on"),
        ]
        result = benchmark.evaluate(builds_on, [])
        assert result.verdict == CompoundingVerdict.NOT_PROVEN

    def test_control_delta_computed(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, track="reuse_on",
                         production_duration=100, reuse_pct=0.0, operator_touches=10,
                         net_new_pct=1.0, first_pass_rate=0.5),
            BuildMetrics(build_id="a2", build_number=2, track="reuse_on",
                         production_duration=50, reuse_pct=0.5, operator_touches=5,
                         net_new_pct=0.5, first_pass_rate=0.9),
        ]
        builds_off = [
            BuildMetrics(build_id="b1", build_number=1, track="reuse_off",
                         production_duration=100, reuse_pct=0.0, operator_touches=10,
                         net_new_pct=1.0, first_pass_rate=0.5),
            BuildMetrics(build_id="b2", build_number=2, track="reuse_off",
                         production_duration=90, reuse_pct=0.0, operator_touches=9,
                         net_new_pct=0.95, first_pass_rate=0.55),
        ]
        result = benchmark.evaluate(builds_on, builds_off)
        assert "production_duration" in result.control_delta
        assert result.control_delta["production_duration"] == -40.0  # 50 - 90

    def test_result_to_dict(self, benchmark):
        builds_on = [
            BuildMetrics(build_id="a1", build_number=1, production_duration=100),
            BuildMetrics(build_id="a2", build_number=2, production_duration=80),
        ]
        result = benchmark.evaluate(builds_on, [])
        d = result.to_dict()
        assert "verdict" in d
        assert "curves" in d
        assert "metrics_improved" in d

    def test_core_metrics_count(self):
        assert len(CORE_METRICS) == 5

    def test_empty_builds(self, benchmark):
        result = benchmark.evaluate([], [])
        assert result.verdict == CompoundingVerdict.NOT_PROVEN
