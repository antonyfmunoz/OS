"""Tests for C26F Reality Correspondence Benchmark.

Validates all 50 scenarios exist, scoring engine is correct,
C25 bug is always detected, and detection_rate >= 0.9.
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.reality_correspondence import (
    BenchmarkDomain,
    BenchmarkResult,
    BenchmarkScenario,
    RealityCorrespondenceBenchmark,
)


@pytest.fixture(scope="module")
def benchmark():
    b = RealityCorrespondenceBenchmark()
    b.run_all()
    return b


class TestBenchmarkScenarios:

    def test_total_50_scenarios(self):
        b = RealityCorrespondenceBenchmark()
        assert len(b.scenarios) == 50

    def test_10_per_domain(self):
        b = RealityCorrespondenceBenchmark()
        for domain in BenchmarkDomain:
            count = sum(1 for s in b.scenarios if s.domain == domain)
            assert count == 10, f"{domain.value} has {count} scenarios, expected 10"

    def test_all_scenario_ids_unique(self):
        b = RealityCorrespondenceBenchmark()
        ids = [s.scenario_id for s in b.scenarios]
        assert len(ids) == len(set(ids))

    def test_all_scenarios_expect_detection(self):
        b = RealityCorrespondenceBenchmark()
        for s in b.scenarios:
            assert s.expected_detection is True, (
                f"{s.scenario_id} has expected_detection=False"
            )


class TestBenchmarkResults:

    def test_run_all_returns_50_results(self, benchmark):
        assert len(benchmark._results) == 50

    def test_c25_scenario_detected(self, benchmark):
        c25 = next(
            r for r in benchmark._results if r.scenario_id == "BUILD-01"
        )
        assert c25.detected is True, "C25 bug (BUILD-01) MUST be detected"

    def test_detection_rate_at_least_90_percent(self, benchmark):
        scores = benchmark.score()
        assert scores["detection_rate"] >= 0.9, (
            f"Detection rate {scores['detection_rate']:.0%} is below 90%"
        )

    def test_c25_bug_detected_in_score(self, benchmark):
        scores = benchmark.score()
        assert scores["c25_bug_detected"] is True


class TestScoringEngine:

    def test_domain_breakdown_sums_to_total(self, benchmark):
        scores = benchmark.score()
        domain_total = sum(
            d["total"] for d in scores["by_domain"].values()
        )
        assert domain_total == scores["total_scenarios"]

    def test_detected_count_matches(self, benchmark):
        scores = benchmark.score()
        manual_count = sum(1 for r in benchmark._results if r.detected)
        assert scores["detected"] == manual_count

    def test_classification_accuracy_is_ratio(self, benchmark):
        scores = benchmark.score()
        assert 0.0 <= scores["classification_accuracy"] <= 1.0


class TestBenchmarkTypes:

    def test_scenario_to_dict(self):
        s = BenchmarkScenario(
            scenario_id="TEST-01",
            domain=BenchmarkDomain.BUILD,
            name="test",
            description="test scenario",
        )
        d = s.to_dict()
        assert d["scenario_id"] == "TEST-01"
        assert d["domain"] == "build"

    def test_result_to_dict(self):
        r = BenchmarkResult(
            scenario_id="TEST-01",
            detected=True,
            classified_correctly=True,
            detection_method="certification",
            time_to_detect_ms=5,
            detected_severity="critical",
            notes="found it",
        )
        d = r.to_dict()
        assert d["detected"] is True
        assert d["detection_method"] == "certification"

    def test_benchmark_summary_is_string(self, benchmark):
        summary = benchmark.summary()
        assert isinstance(summary, str)
        assert "Reality Correspondence Benchmark" in summary
        assert "BUILD" in summary


class TestCanonicalTypes:

    def test_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES
        for name in ["BenchmarkDomain", "BenchmarkScenario", "BenchmarkResult"]:
            assert name in CANONICAL_TYPES, f"{name} not registered"
