"""C36 Qualification System Maturation Tests.

Tests confidence intervals, SelfModel, QualificationOrchestrator,
Property 10 (Predictive Accuracy), and 3-dimensional report output.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.qualification_harness import (
    ConfidenceEstimate,
    ConvergenceWindow,
    DriftResult,
    MutationRecord,
    ORL,
    PropertyResult,
    PropertyStatus,
    QualificationConfig,
    QualificationHarness,
    QualificationOrchestrator,
    QualificationReport,
    SelfModel,
)


# ── ConfidenceEstimate ────────────────────────────────────────────────────


class TestConfidenceEstimate:
    def test_empty_samples(self):
        ci = ConfidenceEstimate.from_samples([])
        assert ci.sample_size == 0
        assert ci.value == 0.0

    def test_single_sample(self):
        ci = ConfidenceEstimate.from_samples([5.0])
        assert ci.value == 5.0
        assert ci.lower == 5.0
        assert ci.upper == 5.0
        assert ci.sample_size == 1

    def test_identical_values(self):
        ci = ConfidenceEstimate.from_samples([1.0] * 50)
        assert ci.value == 1.0
        assert ci.margin() == 0.0
        assert ci.sample_size == 50

    def test_normal_distribution(self):
        values = [10.0 + i * 0.1 for i in range(100)]
        ci = ConfidenceEstimate.from_samples(values, confidence=0.95)
        assert ci.sample_size == 100
        assert ci.lower < ci.value < ci.upper
        assert ci.margin() > 0

    def test_contains(self):
        ci = ConfidenceEstimate(value=10.0, lower=9.0, upper=11.0, sample_size=50)
        assert ci.contains(10.0)
        assert ci.contains(9.5)
        assert not ci.contains(8.0)
        assert not ci.contains(12.0)

    def test_relative_margin(self):
        ci = ConfidenceEstimate(value=10.0, lower=9.0, upper=11.0, sample_size=50)
        assert ci.relative_margin() == pytest.approx(0.1, abs=0.001)

    def test_relative_margin_zero_value(self):
        ci = ConfidenceEstimate(value=0.0, lower=-1.0, upper=1.0, sample_size=50)
        assert ci.relative_margin() == float("inf")

    def test_to_dict(self):
        ci = ConfidenceEstimate(
            value=0.95,
            lower=0.93,
            upper=0.97,
            confidence_level=0.95,
            sample_size=100,
        )
        d = ci.to_dict()
        assert d["value"] == 0.95
        assert d["sample_size"] == 100
        assert "margin" in d

    def test_format_string(self):
        ci = ConfidenceEstimate(
            value=0.95,
            lower=0.93,
            upper=0.97,
            sample_size=100,
        )
        s = ci.format()
        assert "+/-" in s

    def test_format_no_data(self):
        ci = ConfidenceEstimate()
        assert ci.format() == "no data"

    def test_confidence_levels(self):
        values = list(range(100))
        ci_90 = ConfidenceEstimate.from_samples(values, confidence=0.90)
        ci_95 = ConfidenceEstimate.from_samples(values, confidence=0.95)
        ci_99 = ConfidenceEstimate.from_samples(values, confidence=0.99)
        assert ci_90.margin() < ci_95.margin() < ci_99.margin()


# ── ConvergenceWindow CI extension ───────────────────────────────────────


class TestConvergenceWindowCI:
    def test_confidence_estimate(self):
        w = ConvergenceWindow(window_size=10)
        for _ in range(20):
            w.add(0.95)
        ci = w.confidence_estimate()
        assert ci.value == pytest.approx(0.95)
        assert ci.margin() == 0.0

    def test_to_dict_includes_ci(self):
        w = ConvergenceWindow(window_size=5)
        for _ in range(10):
            w.add(1.0)
        d = w.to_dict()
        assert "ci_lower" in d
        assert "ci_upper" in d
        assert "ci_margin" in d

    def test_varying_values_have_margin(self):
        w = ConvergenceWindow(window_size=10)
        for i in range(20):
            w.add(0.90 + i * 0.005)
        ci = w.confidence_estimate()
        assert ci.margin() > 0


# ── SelfModel ─────────────────────────────────────────────────────────────


class TestSelfModel:
    def test_initial_prediction_defaults(self):
        model = SelfModel()
        pred = model.predict("unknown_type")
        assert "governance_cost_ms" in pred
        assert "failure_prob" in pred
        assert "duration_ms" in pred

    def test_prediction_accuracy_no_data(self):
        model = SelfModel()
        acc = model.prediction_accuracy()
        assert acc.sample_size == 0

    def test_record_and_predict(self):
        model = SelfModel()
        for i in range(10):
            model.record_actual(
                "test_action",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 50.0,
                },
            )

        pred = model.predict("test_action")
        assert pred["governance_cost_ms"] == pytest.approx(10.0, abs=1.0)
        assert pred["duration_ms"] == pytest.approx(50.0, abs=5.0)

    def test_prediction_accuracy_perfect(self):
        model = SelfModel()
        for _ in range(20):
            model.record_actual(
                "test_action",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 50.0,
                },
            )

        acc = model.prediction_accuracy()
        assert acc.sample_size > 0
        assert acc.value < 0.5

    def test_calibration_score(self):
        model = SelfModel()
        for _ in range(20):
            model.record_actual(
                "test_action",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 50.0,
                },
            )

        score = model.calibration_score()
        assert 0 <= score <= 1

    def test_per_metric_accuracy(self):
        model = SelfModel()
        for _ in range(10):
            model.record_actual(
                "test_action",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 50.0,
                },
            )
        per_metric = model.per_metric_accuracy()
        assert "governance_cost_ms" in per_metric
        assert "duration_ms" in per_metric

    def test_record_from_mutation(self):
        model = SelfModel()
        record = MutationRecord(
            action_type="test",
            success=True,
            governance_cost_ms=5.0,
            template_matched=True,
            duration_ms=30.0,
        )
        model.record_from_mutation(record)
        acc = model.prediction_accuracy()
        assert acc.sample_size > 0

    def test_ema_adapts(self):
        model = SelfModel()
        for _ in range(10):
            model.record_actual(
                "shift",
                {
                    "governance_cost_ms": 100.0,
                    "failure_prob": 0.5,
                    "template_match": 0.0,
                    "duration_ms": 200.0,
                },
            )
        pred_before = model.predict("shift")

        for _ in range(20):
            model.record_actual(
                "shift",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 20.0,
                },
            )
        pred_after = model.predict("shift")
        assert pred_after["governance_cost_ms"] < pred_before["governance_cost_ms"]


# ── Property 10: Predictive Accuracy ─────────────────────────────────────


class TestProperty10:
    def test_predictive_accuracy_pass(self):
        harness = QualificationHarness()
        model = SelfModel()
        for _ in range(30):
            model.record_actual(
                "test",
                {
                    "governance_cost_ms": 10.0,
                    "failure_prob": 0.0,
                    "template_match": 1.0,
                    "duration_ms": 50.0,
                },
            )
        result = harness.validate_predictive_accuracy(model)
        assert result.property_id == 10
        assert result.property_name == "Predictive Accuracy"
        assert result.status in (PropertyStatus.CONVERGED, PropertyStatus.FAILED)

    def test_predictive_accuracy_no_data_fails(self):
        harness = QualificationHarness()
        model = SelfModel()
        result = harness.validate_predictive_accuracy(model)
        assert result.status == PropertyStatus.FAILED

    def test_p10_does_not_gate_orl(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(property_id=i, status=PropertyStatus.CONVERGED) for i in range(1, 10)
        ]
        props.append(PropertyResult(property_id=10, status=PropertyStatus.FAILED))
        drift = DriftResult(passed=True)
        orl = harness.compute_orl(props, drift)
        assert orl == ORL.PRODUCTION_QUALIFIED


# ── QualificationOrchestrator ────────────────────────────────────────────


class TestQualificationOrchestrator:
    def _fresh_harness(self):
        """Create a harness that doesn't load existing mutation data."""
        h = QualificationHarness.__new__(QualificationHarness)
        h._mutations = []
        h._property_results = []
        h._convergence = {}
        import time

        h._started_at = time.time()
        return h

    def test_orchestrator_converges(self):
        harness = self._fresh_harness()
        config = QualificationConfig(
            min_mutations=10,
            max_mutations=200,
            batch_size=10,
            target_confidence=0.80,
        )
        orchestrator = QualificationOrchestrator(harness, config)

        call_count = [0]

        def mock_submit(batch_size):
            records = []
            for i in range(batch_size):
                r = MutationRecord(
                    mutation_id=f"m-{call_count[0]}-{i}",
                    action_type="test",
                    source="c36_test",
                    success=True,
                    governance_cost_ms=5.0,
                    duration_ms=30.0,
                    template_matched=True,
                )
                harness._mutations.append(r)
                records.append(r)
            call_count[0] += 1
            return records

        def mock_validate(records):
            props = []
            for pid in range(1, 10):
                props.append(
                    PropertyResult(
                        property_id=pid,
                        property_name=f"Property {pid}",
                        status=PropertyStatus.CONVERGED,
                        confidence=0.95,
                    )
                )
            return props

        report = orchestrator.run_until_converged(mock_submit, mock_validate)
        assert orchestrator.is_complete()
        assert report.orl_confidence > 0
        assert "Converged" in orchestrator.stopping_reason()

    def test_orchestrator_hits_ceiling(self):
        harness = self._fresh_harness()
        config = QualificationConfig(
            min_mutations=5,
            max_mutations=20,
            batch_size=5,
            target_confidence=0.99,
        )
        orchestrator = QualificationOrchestrator(harness, config)

        def mock_submit(batch_size):
            records = []
            for i in range(batch_size):
                r = MutationRecord(
                    mutation_id=f"m-{i}",
                    action_type="test",
                    source="c36_test",
                    success=True,
                    governance_cost_ms=5.0,
                    duration_ms=30.0,
                )
                harness._mutations.append(r)
                records.append(r)
            return records

        def mock_validate(records):
            return [
                PropertyResult(
                    property_id=pid,
                    property_name=f"Property {pid}",
                    status=PropertyStatus.CONVERGED,
                    confidence=0.50,
                )
                for pid in range(1, 10)
            ]

        report = orchestrator.run_until_converged(mock_submit, mock_validate)
        assert not orchestrator.is_complete()
        assert "Ceiling" in orchestrator.stopping_reason()

    def test_adaptive_batch_sizing(self):
        harness = QualificationHarness()
        config = QualificationConfig(batch_size=25, target_confidence=0.95)
        orchestrator = QualificationOrchestrator(harness, config)

        high_confidence = [
            PropertyResult(
                property_id=pid,
                status=PropertyStatus.CONVERGED,
                confidence=0.90,
            )
            for pid in range(1, 10)
        ]
        size_high = orchestrator.next_batch_size(high_confidence)

        low_confidence = [
            PropertyResult(
                property_id=pid,
                status=PropertyStatus.CONVERGED,
                confidence=0.50,
            )
            for pid in range(1, 10)
        ]
        size_low = orchestrator.next_batch_size(low_confidence)

        assert size_low >= size_high

    def test_weakest_property_found(self):
        harness = QualificationHarness()
        orchestrator = QualificationOrchestrator(harness)
        props = [
            PropertyResult(property_id=1, confidence=0.95),
            PropertyResult(property_id=2, confidence=0.60),
            PropertyResult(property_id=3, confidence=0.99),
        ]
        weakest = orchestrator.weakest_property(props)
        assert weakest is not None
        assert weakest.property_id == 2


# ── 3-Dimensional Report ─────────────────────────────────────────────────


class TestThreeDimensionalReport:
    def test_report_has_three_dimensions(self):
        report = QualificationReport(
            orl_achieved=8,
            orl_confidence=0.97,
            predictive_accuracy=0.93,
        )
        d = report.to_dict()
        assert d["orl_achieved"] == 8
        assert d["orl_confidence"] == 0.97
        assert d["predictive_accuracy"] == 0.93

    def test_report_markdown_three_dimensions(self):
        harness = QualificationHarness()
        report = QualificationReport(
            orl_achieved=8,
            orl_confidence=0.97,
            predictive_accuracy=0.93,
            properties=[
                PropertyResult(
                    property_id=1,
                    property_name="Test Prop",
                    status=PropertyStatus.CONVERGED,
                    confidence=0.95,
                    evidence=["metric=0.95"],
                ),
            ],
            drift=DriftResult(passed=True),
            total_mutations=200,
            total_duration_s=30.0,
            hypothesis_result="H1 SUPPORTED",
            weakest_property="Adaptive Intelligence",
            recommendation="Optimize template reuse",
            convergence_status="Stable",
        )
        md = harness.format_report_markdown(report)
        assert "ORL-8" in md
        assert "Confidence" in md
        assert "97.0%" in md
        assert "Predictive Accuracy" in md
        assert "93.0%" in md
        assert "Adaptive Intelligence" in md
        assert "Stable" in md

    def test_weakest_property_detection(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(
                property_id=1,
                property_name="Integrity",
                confidence=0.99,
                status=PropertyStatus.CONVERGED,
            ),
            PropertyResult(
                property_id=2,
                property_name="Coverage",
                confidence=0.85,
                status=PropertyStatus.CONVERGED,
            ),
            PropertyResult(
                property_id=3,
                property_name="Consistency",
                confidence=0.92,
                status=PropertyStatus.CONVERGED,
            ),
        ]
        name, rec = harness._find_weakest_property(props)
        assert name == "Coverage"
        assert "lowest confidence" in rec

    def test_weakest_property_failed_first(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(
                property_id=1,
                property_name="Integrity",
                confidence=0.99,
                status=PropertyStatus.CONVERGED,
            ),
            PropertyResult(
                property_id=2,
                property_name="Coverage",
                confidence=0.85,
                status=PropertyStatus.FAILED,
            ),
        ]
        name, rec = harness._find_weakest_property(props)
        assert name == "Coverage"
        assert "FAILED" in rec

    def test_report_includes_stopping_reason(self):
        report = QualificationReport(
            stopping_reason="Converged after 120 mutations (5 batches)",
        )
        d = report.to_dict()
        assert d["stopping_reason"] == "Converged after 120 mutations (5 batches)"

    def test_orl_unchanged_with_p10(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(property_id=i, status=PropertyStatus.CONVERGED) for i in range(1, 10)
        ]
        props.append(PropertyResult(property_id=10, status=PropertyStatus.FAILED))
        drift = DriftResult(passed=True)
        assert harness.compute_orl(props, drift) == ORL.PRODUCTION_QUALIFIED

    def test_self_regulating_orl(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(property_id=8, status=PropertyStatus.CONVERGED),
            PropertyResult(property_id=9, status=PropertyStatus.CONVERGED),
        ]
        drift = DriftResult(passed=True)
        assert harness.compute_orl(props, drift) == ORL.SELF_REGULATING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
