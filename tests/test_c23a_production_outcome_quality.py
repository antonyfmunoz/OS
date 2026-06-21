"""Tests for Benchmark 6 — Production Outcome Quality."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.production_outcome_quality import (
    AcceptanceCriterion,
    ProductionOutcome,
    ProductionOutcomeQualityBenchmark,
    ProductionOutcomeResult,
    QualityComparison,
    TrackMetrics,
)


class TestAcceptanceCriterion:
    def test_defaults(self):
        c = AcceptanceCriterion()
        assert c.met is False

    def test_to_dict(self):
        c = AcceptanceCriterion(criterion_id="c1", description="tests pass", met=True)
        d = c.to_dict()
        assert d["criterion_id"] == "c1"
        assert d["met"] is True


class TestProductionOutcome:
    def test_test_pass_rate(self):
        o = ProductionOutcome(test_pass_count=9, test_total_count=10)
        assert o.test_pass_rate == 0.9

    def test_test_pass_rate_zero(self):
        o = ProductionOutcome(test_pass_count=0, test_total_count=0)
        assert o.test_pass_rate == 0.0

    def test_acceptance_rate(self):
        o = ProductionOutcome(acceptance_criteria=[
            AcceptanceCriterion(met=True),
            AcceptanceCriterion(met=True),
            AcceptanceCriterion(met=False),
        ])
        assert abs(o.acceptance_rate - 2 / 3) < 0.001

    def test_acceptance_rate_empty(self):
        o = ProductionOutcome()
        assert o.acceptance_rate == 0.0

    def test_defect_density(self):
        o = ProductionOutcome(defect_count=5, lines_of_code=1000)
        assert o.defect_density == 5.0

    def test_defect_density_zero_loc(self):
        o = ProductionOutcome(defect_count=5, lines_of_code=0)
        assert o.defect_density == 0.0

    def test_to_dict(self):
        o = ProductionOutcome(
            production_id="p1", track="reuse_on",
            test_pass_count=8, test_total_count=10,
            lines_of_code=500, defect_count=2,
        )
        d = o.to_dict()
        assert d["production_id"] == "p1"
        assert d["test_pass_rate"] == 0.8
        assert d["defect_density"] == 4.0


class TestTrackMetrics:
    def test_to_dict(self):
        tm = TrackMetrics(track="reuse_on", productions=3, avg_test_pass_rate=0.95)
        d = tm.to_dict()
        assert d["track"] == "reuse_on"
        assert d["avg_test_pass_rate"] == 0.95


class TestProductionOutcomeQualityBenchmark:
    def test_empty_outcomes(self):
        bench = ProductionOutcomeQualityBenchmark()
        result = bench.run([])
        assert result.total_outcomes == 0

    def test_positive_compounding(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=10, test_total_count=10,
                defect_count=0, lines_of_code=1000, rework_count=0,
                acceptance_criteria=[AcceptanceCriterion(met=True)],
            ),
            ProductionOutcome(
                production_id="b1", track="reuse_off",
                test_pass_count=7, test_total_count=10,
                defect_count=5, lines_of_code=1000, rework_count=3,
                acceptance_criteria=[AcceptanceCriterion(met=False)],
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.quality_verdict == "POSITIVE_COMPOUNDING"

    def test_negative_compounding(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=5, test_total_count=10,
                defect_count=8, lines_of_code=1000, rework_count=5,
                acceptance_criteria=[AcceptanceCriterion(met=False)],
            ),
            ProductionOutcome(
                production_id="b1", track="reuse_off",
                test_pass_count=10, test_total_count=10,
                defect_count=0, lines_of_code=1000, rework_count=0,
                acceptance_criteria=[AcceptanceCriterion(met=True)],
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.quality_verdict == "NEGATIVE_COMPOUNDING"

    def test_neutral_compounding(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=9, test_total_count=10,
                defect_count=1, lines_of_code=1000, rework_count=1,
                acceptance_criteria=[AcceptanceCriterion(met=True)],
            ),
            ProductionOutcome(
                production_id="b1", track="reuse_off",
                test_pass_count=9, test_total_count=10,
                defect_count=1, lines_of_code=1000, rework_count=1,
                acceptance_criteria=[AcceptanceCriterion(met=True)],
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.quality_verdict == "NEUTRAL_COMPOUNDING"

    def test_no_compounding_insufficient_data(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=10, test_total_count=10,
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.quality_verdict == "NO_COMPOUNDING"

    def test_deltas_computed(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=10, test_total_count=10,
                defect_count=1, lines_of_code=1000,
            ),
            ProductionOutcome(
                production_id="b1", track="reuse_off",
                test_pass_count=8, test_total_count=10,
                defect_count=3, lines_of_code=1000,
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.test_pass_delta > 0
        assert result.comparison.defect_density_delta < 0

    def test_per_production_in_result(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(production_id="a1", track="reuse_on"),
            ProductionOutcome(production_id="b1", track="reuse_off"),
        ]
        result = bench.run(outcomes)
        assert len(result.per_production) == 2

    def test_to_dict(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(production_id="a1", track="reuse_on"),
            ProductionOutcome(production_id="b1", track="reuse_off"),
        ]
        result = bench.run(outcomes)
        d = result.to_dict()
        assert "total_outcomes" in d
        assert "comparison" in d

    def test_multiple_outcomes_per_track(self):
        bench = ProductionOutcomeQualityBenchmark()
        outcomes = [
            ProductionOutcome(
                production_id="a1", track="reuse_on",
                test_pass_count=10, test_total_count=10,
                defect_count=0, lines_of_code=500,
            ),
            ProductionOutcome(
                production_id="a2", track="reuse_on",
                test_pass_count=9, test_total_count=10,
                defect_count=1, lines_of_code=500,
            ),
            ProductionOutcome(
                production_id="b1", track="reuse_off",
                test_pass_count=7, test_total_count=10,
                defect_count=3, lines_of_code=500,
            ),
            ProductionOutcome(
                production_id="b2", track="reuse_off",
                test_pass_count=6, test_total_count=10,
                defect_count=4, lines_of_code=500,
            ),
        ]
        result = bench.run(outcomes)
        assert result.comparison.track_a.productions == 2
        assert result.comparison.track_b.productions == 2
        assert result.comparison.quality_verdict == "POSITIVE_COMPOUNDING"
