"""Tests for Projection Readiness Benchmark — C23A Phase 9."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.benchmarks.projection_readiness import (
    PROJECTION_REQUIREMENTS,
    ProjectionCoverage,
    ProjectionReadinessBenchmark,
    ProjectionReadinessResult,
)


@pytest.fixture
def benchmark():
    return ProjectionReadinessBenchmark()


class TestProjectionRequirements:
    def test_three_projections_defined(self):
        assert "EOS" in PROJECTION_REQUIREMENTS
        assert "LOS" in PROJECTION_REQUIREMENTS
        assert "COS" in PROJECTION_REQUIREMENTS

    def test_each_has_ten_requirements(self):
        for proj, reqs in PROJECTION_REQUIREMENTS.items():
            assert len(reqs) == 10, f"{proj} has {len(reqs)} requirements, expected 10"

    def test_no_duplicate_requirements_within_projection(self):
        for proj, reqs in PROJECTION_REQUIREMENTS.items():
            assert len(reqs) == len(set(reqs)), f"{proj} has duplicate requirements"


class TestProjectionCoverage:
    def test_defaults(self):
        pc = ProjectionCoverage()
        assert pc.existing_coverage_pct == 0.0
        assert pc.net_new_pct == 1.0

    def test_to_dict(self):
        pc = ProjectionCoverage(
            projection_name="EOS",
            required_capabilities=["a", "b", "c"],
            matched_capabilities=["a"],
            unmatched_capabilities=["b", "c"],
            existing_coverage_pct=0.333,
            net_new_pct=0.667,
        )
        d = pc.to_dict()
        assert d["projection_name"] == "EOS"
        assert d["required_count"] == 3
        assert d["matched_count"] == 1
        assert d["unmatched_count"] == 2


class TestProjectionReadinessResult:
    def test_to_dict(self):
        r = ProjectionReadinessResult(
            projections=[{"name": "EOS"}],
            cross_projection_reuse=0.1,
            total_unique_capabilities=30,
            shared_capabilities=3,
            overall_readiness=0.5,
        )
        d = r.to_dict()
        assert d["cross_projection_reuse"] == 0.1
        assert d["total_unique_capabilities"] == 30


class TestFuzzyMatching:
    def test_exact_match(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["outreach_automation"])
        result = b.evaluate({"test": ["outreach_automation"]})
        assert result.projections[0]["matched_count"] == 1

    def test_case_insensitive(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["Outreach_Automation"])
        result = b.evaluate({"test": ["outreach_automation"]})
        assert result.projections[0]["matched_count"] == 1

    def test_substring_match(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["outreach_automation_engine"])
        result = b.evaluate({"test": ["outreach_automation"]})
        assert result.projections[0]["matched_count"] == 1

    def test_reverse_substring(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["outreach"])
        result = b.evaluate({"test": ["outreach_automation"]})
        assert result.projections[0]["matched_count"] == 1

    def test_word_overlap(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["lead_management_system"])
        result = b.evaluate({"test": ["lead_tracking"]})
        # "lead" overlaps → 1 out of 2 words = 50% ≥ threshold
        assert result.projections[0]["matched_count"] == 1

    def test_no_match(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["completely_different"])
        result = b.evaluate({"test": ["outreach_automation"]})
        assert result.projections[0]["matched_count"] == 0
        assert result.projections[0]["unmatched_count"] == 1


class TestEvaluate:
    def test_zero_capabilities(self, benchmark):
        result = benchmark.evaluate()
        assert result.overall_readiness == 0.0
        for proj in result.projections:
            assert proj["matched_count"] == 0

    def test_full_coverage(self):
        all_caps = []
        for reqs in PROJECTION_REQUIREMENTS.values():
            all_caps.extend(reqs)
        b = ProjectionReadinessBenchmark(existing_capabilities=all_caps)
        result = b.evaluate()
        assert result.overall_readiness == 1.0

    def test_partial_coverage(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=[
            "outreach_automation", "lead_tracking", "pipeline_management",
        ])
        result = b.evaluate()
        eos = next(p for p in result.projections if p["projection_name"] == "EOS")
        assert eos["matched_count"] >= 3
        assert eos["existing_coverage_pct"] >= 0.3

    def test_cross_projection_reuse(self):
        custom = {
            "P1": ["analytics", "scheduling", "tracking"],
            "P2": ["analytics", "reporting", "scheduling"],
        }
        b = ProjectionReadinessBenchmark()
        result = b.evaluate(custom)
        # Shared: analytics, scheduling → 2 out of 4 unique = 0.5
        assert result.shared_capabilities == 2
        assert result.cross_projection_reuse == 0.5

    def test_no_cross_reuse(self):
        custom = {
            "P1": ["a", "b"],
            "P2": ["c", "d"],
        }
        b = ProjectionReadinessBenchmark()
        result = b.evaluate(custom)
        assert result.shared_capabilities == 0
        assert result.cross_projection_reuse == 0.0

    def test_set_existing_capabilities(self, benchmark):
        benchmark.set_existing_capabilities(["habit_tracking", "goal_setting"])
        result = benchmark.evaluate()
        los = next(p for p in result.projections if p["projection_name"] == "LOS")
        assert los["matched_count"] >= 2

    def test_overall_readiness_is_average(self):
        custom = {
            "P1": ["a"],
            "P2": ["b"],
        }
        b = ProjectionReadinessBenchmark(existing_capabilities=["a"])
        result = b.evaluate(custom)
        # P1: 100%, P2: 0% → average = 50%
        assert result.overall_readiness == 0.5

    def test_empty_projections(self):
        b = ProjectionReadinessBenchmark()
        result = b.evaluate({"empty": []})
        assert result.overall_readiness == 0.0


class TestNetNew:
    def test_net_new_complement(self):
        b = ProjectionReadinessBenchmark(existing_capabilities=["outreach_automation", "lead_tracking"])
        result = b.evaluate({"EOS": PROJECTION_REQUIREMENTS["EOS"]})
        eos = result.projections[0]
        assert abs(eos["existing_coverage_pct"] + eos["net_new_pct"] - 1.0) < 0.001
