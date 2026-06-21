"""Tests for Benchmark 5 — Operator Compression."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.operator_compression import (
    CompressionMetrics,
    OperatorCompressionBenchmark,
    OperatorCompressionResult,
    OperatorInteraction,
    ProductionInteractions,
    classify_operator_message,
    _compute_trend,
)


class TestClassifyOperatorMessage:
    def test_correction_no(self):
        assert classify_operator_message("no that's wrong") == "correction"

    def test_correction_stop(self):
        assert classify_operator_message("stop doing that") == "correction"

    def test_correction_dont(self):
        assert classify_operator_message("don't do that") == "correction"

    def test_correction_fix(self):
        assert classify_operator_message("fix the bug") == "correction"

    def test_approval_yes(self):
        assert classify_operator_message("yes go ahead") == "approval"

    def test_approval_lgtm(self):
        assert classify_operator_message("LGTM") == "approval"

    def test_approval_ship_it(self):
        assert classify_operator_message("ship it") == "approval"

    def test_information(self):
        assert classify_operator_message("here is the context") == "information"

    def test_empty_string(self):
        assert classify_operator_message("") == "information"

    def test_whitespace_only(self):
        assert classify_operator_message("   ") == "information"

    def test_correction_takes_priority(self):
        assert classify_operator_message("no, that looks good but fix it") == "correction"

    def test_case_insensitive(self):
        assert classify_operator_message("APPROVED") == "approval"
        assert classify_operator_message("WRONG") == "correction"


class TestOperatorInteraction:
    def test_auto_classification(self):
        oi = OperatorInteraction(message_text="yes do it")
        assert oi.classification == "approval"

    def test_explicit_classification(self):
        oi = OperatorInteraction(
            message_text="yes do it", classification="information",
        )
        assert oi.classification == "information"

    def test_to_dict(self):
        oi = OperatorInteraction(
            message_id="m1", message_text="looks good", production_id="p1",
        )
        d = oi.to_dict()
        assert d["message_id"] == "m1"
        assert d["classification"] == "approval"


class TestProductionInteractions:
    def test_to_dict(self):
        pi = ProductionInteractions(
            production_id="p1", operator_messages=5, operator_corrections=1,
        )
        d = pi.to_dict()
        assert d["production_id"] == "p1"
        assert d["operator_messages"] == 5


class TestComputeMetrics:
    def test_zero_actions(self):
        pi = ProductionInteractions()
        m = OperatorCompressionBenchmark.compute_metrics(pi)
        assert m.autonomy_ratio == 0.0
        assert m.correction_rate == 0.0

    def test_full_autonomy(self):
        pi = ProductionInteractions(autonomous_actions=10, operator_interventions=0)
        m = OperatorCompressionBenchmark.compute_metrics(pi)
        assert m.autonomy_ratio == 1.0

    def test_mixed_autonomy(self):
        pi = ProductionInteractions(autonomous_actions=7, operator_interventions=3)
        m = OperatorCompressionBenchmark.compute_metrics(pi)
        assert m.autonomy_ratio == 0.7

    def test_correction_rate(self):
        pi = ProductionInteractions(operator_messages=10, operator_corrections=3)
        m = OperatorCompressionBenchmark.compute_metrics(pi)
        assert m.correction_rate == 0.3


class TestFromInteractions:
    def test_aggregates_by_production(self):
        interactions = [
            OperatorInteraction(message_text="fix this", production_id="p1"),
            OperatorInteraction(message_text="looks good", production_id="p1"),
            OperatorInteraction(message_text="yes", production_id="p2"),
        ]
        by_prod = OperatorCompressionBenchmark.from_interactions(interactions)
        assert len(by_prod) == 2
        assert by_prod["p1"].operator_messages == 2
        assert by_prod["p1"].operator_corrections == 1
        assert by_prod["p2"].operator_approvals == 1


class TestComputeTrend:
    def test_empty(self):
        assert _compute_trend([]) == 0.0

    def test_single_value(self):
        assert _compute_trend([5.0]) == 0.0

    def test_increasing(self):
        assert _compute_trend([1.0, 2.0, 3.0, 4.0]) > 0

    def test_decreasing(self):
        assert _compute_trend([4.0, 3.0, 2.0, 1.0]) < 0

    def test_flat(self):
        assert _compute_trend([5.0, 5.0, 5.0]) == 0.0


class TestOperatorCompressionBenchmark:
    def test_empty_productions(self):
        bench = OperatorCompressionBenchmark()
        result = bench.run([])
        assert result.productions == 0

    def test_single_production(self):
        bench = OperatorCompressionBenchmark()
        result = bench.run([
            ProductionInteractions(
                production_id="p1", operator_messages=5,
                autonomous_actions=10, operator_interventions=2,
            ),
        ])
        assert result.productions == 1
        assert len(result.per_production_metrics) == 1

    def test_improving_compression(self):
        bench = OperatorCompressionBenchmark()
        result = bench.run([
            ProductionInteractions(
                production_id="p1", operator_messages=10,
                autonomous_actions=5, operator_corrections=4,
            ),
            ProductionInteractions(
                production_id="p2", operator_messages=6,
                autonomous_actions=10, operator_corrections=1,
            ),
            ProductionInteractions(
                production_id="p3", operator_messages=3,
                autonomous_actions=15, operator_corrections=0,
            ),
        ])
        assert result.trend["touches_trend"] < 0
        assert result.trend["correction_trend"] < 0

    def test_aggregate_metrics(self):
        bench = OperatorCompressionBenchmark()
        result = bench.run([
            ProductionInteractions(
                production_id="p1", operator_messages=10, autonomous_actions=10,
            ),
            ProductionInteractions(
                production_id="p2", operator_messages=5, autonomous_actions=15,
            ),
        ])
        assert "avg_touches_per_production" in result.aggregate_metrics
        assert "avg_autonomy_ratio" in result.aggregate_metrics

    def test_to_dict(self):
        bench = OperatorCompressionBenchmark()
        result = bench.run([
            ProductionInteractions(production_id="p1", operator_messages=5),
        ])
        d = result.to_dict()
        assert "productions" in d
        assert "trend" in d
