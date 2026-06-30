"""C35 Organism Qualification Tests.

Tests the qualification harness, convergence math, property validators,
drift detection, ORL scoring, and self-maintenance bridge.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.qualification_harness import (
    ConvergenceWindow,
    DriftResult,
    GapType,
    MutationRecord,
    ORL,
    PropertyResult,
    PropertyStatus,
    QualificationHarness,
    QualificationReport,
    ROLLING_WINDOW_SIZE,
    CONVERGENCE_THRESHOLD,
    CONSECUTIVE_WINDOWS_REQUIRED,
    DRIFT_DEVIATION_LIMIT,
)


# ── Convergence math ───────────────────────────────────────────────────────


class TestConvergenceWindow:
    def test_empty_window(self):
        w = ConvergenceWindow()
        assert w.mean() == 0.0
        assert not w.has_converged()
        assert not w.is_fully_converged()

    def test_add_values(self):
        w = ConvergenceWindow()
        for i in range(10):
            w.add(1.0)
        assert w.mean() == 1.0
        assert len(w.values) == 10

    def test_convergence_identical_values(self):
        w = ConvergenceWindow(window_size=10)
        for _ in range(30):
            w.add(0.95)
        assert w.has_converged()
        assert w.stddev() == 0.0
        assert w.coefficient_of_variation() == 0.0

    def test_no_convergence_high_variance(self):
        w = ConvergenceWindow(window_size=10)
        for i in range(30):
            w.add(float(i % 5))
        assert not w.has_converged()

    def test_not_enough_data(self):
        w = ConvergenceWindow(window_size=50)
        for _ in range(10):
            w.add(1.0)
        assert not w.has_converged()

    def test_consecutive_convergence(self):
        w = ConvergenceWindow(window_size=10)
        for _ in range(50):
            w.add(0.95)
        count = w.consecutive_convergence_count()
        assert count >= CONSECUTIVE_WINDOWS_REQUIRED
        assert w.is_fully_converged()

    def test_to_dict(self):
        w = ConvergenceWindow(window_size=5)
        for _ in range(15):
            w.add(1.0)
        d = w.to_dict()
        assert "count" in d
        assert "mean" in d
        assert "converged" in d
        assert d["count"] == 15
        assert d["mean"] == 1.0

    def test_mean_zero_cv(self):
        w = ConvergenceWindow(window_size=5)
        for _ in range(10):
            w.add(0.0)
        assert w.coefficient_of_variation() == float("inf")


# ── MutationRecord ─────────────────────────────────────────────────────────


class TestMutationRecord:
    def test_defaults(self):
        r = MutationRecord()
        assert r.mutation_id == ""
        assert r.success is False
        assert r.duration_ms == 0.0

    def test_to_dict(self):
        r = MutationRecord(
            mutation_id="test-1",
            mutation_name="log_rotation",
            success=True,
            duration_ms=42.0,
        )
        d = r.to_dict()
        assert d["mutation_id"] == "test-1"
        assert d["success"] is True
        assert d["duration_ms"] == 42.0


# ── PropertyResult ─────────────────────────────────────────────────────────


class TestPropertyResult:
    def test_defaults(self):
        p = PropertyResult()
        assert p.status == PropertyStatus.NOT_STARTED
        assert p.property_id == 0

    def test_to_dict(self):
        p = PropertyResult(
            property_id=1,
            property_name="Test Property",
            status=PropertyStatus.CONVERGED,
            mutation_count=50,
        )
        d = p.to_dict()
        assert d["property_id"] == 1
        assert d["status"] == "converged"


# ── Drift Detection ───────────────────────────────────────────────────────


class TestDriftDetection:
    def test_insufficient_data(self):
        harness = QualificationHarness()
        mutations = [
            MutationRecord(success=True, governance_cost_ms=10.0, duration_ms=100.0)
            for _ in range(50)
        ]
        drift = harness.compute_drift(mutations)
        assert drift.passed is True

    def test_no_drift_identical(self):
        harness = QualificationHarness()
        mutations = [
            MutationRecord(
                success=True,
                governance_cost_ms=10.0,
                duration_ms=100.0,
                template_matched=True,
                fast_path_used=True,
            )
            for _ in range(200)
        ]
        drift = harness.compute_drift(mutations)
        assert drift.passed is True
        assert len(drift.violations) == 0

    def test_drift_detected(self):
        harness = QualificationHarness()
        mutations = []
        for i in range(100):
            mutations.append(MutationRecord(
                success=True,
                governance_cost_ms=100.0,
                duration_ms=100.0,
            ))
        for i in range(100):
            mutations.append(MutationRecord(
                success=False,
                governance_cost_ms=200.0,
                duration_ms=300.0,
            ))
        drift = harness.compute_drift(mutations)
        assert drift.passed is False
        assert len(drift.violations) > 0

    def test_governance_improvement_not_violation(self):
        harness = QualificationHarness()
        mutations = []
        for i in range(100):
            mutations.append(MutationRecord(
                success=True,
                governance_cost_ms=100.0,
                duration_ms=100.0,
            ))
        for i in range(100):
            mutations.append(MutationRecord(
                success=True,
                governance_cost_ms=50.0,
                duration_ms=80.0,
            ))
        drift = harness.compute_drift(mutations)
        gov_violations = [v for v in drift.violations if "governance" in v]
        assert len(gov_violations) == 0


# ── ORL Scoring ────────────────────────────────────────────────────────────


class TestORLScoring:
    def _make_result(self, pid: int, status: PropertyStatus) -> PropertyResult:
        return PropertyResult(property_id=pid, status=status)

    def test_all_pass_orl8(self):
        harness = QualificationHarness()
        props = [self._make_result(i, PropertyStatus.CONVERGED) for i in range(1, 10)]
        drift = DriftResult(passed=True)
        assert harness.compute_orl(props, drift) == ORL.PRODUCTION_QUALIFIED

    def test_drift_fail_blocks_orl8(self):
        harness = QualificationHarness()
        props = [self._make_result(i, PropertyStatus.CONVERGED) for i in range(1, 10)]
        drift = DriftResult(passed=False, violations=["test drift"])
        orl = harness.compute_orl(props, drift)
        assert orl == ORL.SELF_MAINTAINING

    def test_partial_pass_orl4(self):
        harness = QualificationHarness()
        props = [
            self._make_result(1, PropertyStatus.CONVERGED),
            self._make_result(2, PropertyStatus.CONVERGED),
            self._make_result(3, PropertyStatus.CONVERGED),
            self._make_result(4, PropertyStatus.FAILED),
            self._make_result(5, PropertyStatus.FAILED),
        ]
        drift = DriftResult(passed=True)
        orl = harness.compute_orl(props, drift)
        assert orl == ORL.STABLE_UNDER_LOAD

    def test_nothing_passes_orl3(self):
        harness = QualificationHarness()
        props = [self._make_result(i, PropertyStatus.FAILED) for i in range(1, 10)]
        drift = DriftResult(passed=True)
        orl = harness.compute_orl(props, drift)
        assert orl == ORL.CANONICAL_MUTATION_ENFORCED


# ── Property Validators ───────────────────────────────────────────────────


class TestPropertyValidators:
    def test_adaptive_intelligence_converges(self):
        harness = QualificationHarness()
        mutations = []
        for i in range(100):
            mutations.append(MutationRecord(
                mutation_id=f"m-{i}",
                action_type="test_action",
                success=True,
                governance_cost_ms=max(5.0, 100.0 - i),
                fast_path_used=i > 50,
                template_matched=i > 30,
            ))

        from unittest.mock import MagicMock
        learning = MagicMock()
        result = harness.validate_adaptive_intelligence(learning, mutations)
        assert result.property_id == 4
        assert result.status == PropertyStatus.CONVERGED

    def test_operational_entropy_low(self):
        harness = QualificationHarness()
        mutations = [
            MutationRecord(
                mutation_id=f"m-{i}",
                success=True,
                governance_cost_ms=10.0,
                duration_ms=50.0,
            )
            for i in range(100)
        ]

        from unittest.mock import MagicMock
        journal_entries = [MagicMock(envelope_id=f"m-{i}") for i in range(100)]
        events = [MagicMock() for _ in range(500)]

        result = harness.validate_operational_entropy(mutations, journal_entries, events)
        assert result.property_id == 5
        assert result.status == PropertyStatus.CONVERGED

    def test_autonomous_coordination_clean(self):
        harness = QualificationHarness()
        results = [
            {"conflict": False, "cancellation_attempted": False, "contention_ms": 5}
            for _ in range(20)
        ]
        result = harness.validate_autonomous_coordination(results)
        assert result.property_id == 6
        assert result.status == PropertyStatus.CONVERGED

    def test_autonomous_coordination_conflicts(self):
        harness = QualificationHarness()
        results = [{"conflict": True, "contention_ms": 100} for _ in range(10)]
        result = harness.validate_autonomous_coordination(results)
        assert result.status == PropertyStatus.FAILED

    def test_recovery_homeostasis_pass(self):
        harness = QualificationHarness()
        injections = [
            {
                "recovered": True,
                "recovery_time_s": 5.0,
                "state_preserved": True,
                "learning_signal_produced": True,
                "stress_duration_s": 30.0,
                "time_outside_band_s": 3.0,
            }
            for _ in range(9)
        ]
        result = harness.validate_recovery_homeostasis(injections, {})
        assert result.property_id == 8
        assert result.status == PropertyStatus.CONVERGED

    def test_recovery_homeostasis_fail(self):
        harness = QualificationHarness()
        injections = [
            {
                "recovered": False,
                "recovery_time_s": 120.0,
                "state_preserved": False,
                "stress_duration_s": 60.0,
                "time_outside_band_s": 55.0,
            }
            for _ in range(9)
        ]
        result = harness.validate_recovery_homeostasis(injections, {})
        assert result.status == PropertyStatus.FAILED

    def test_self_maintenance_detected(self):
        harness = QualificationHarness()
        events = [
            {
                "degradation_detected": True,
                "work_packet_created": True,
                "proposal_latency_s": 5.0,
                "repair_succeeded": True,
                "reliability_recovered": True,
            }
            for _ in range(5)
        ]
        result = harness.validate_self_maintenance(events)
        assert result.property_id == 9
        assert result.status == PropertyStatus.CONVERGED

    def test_self_maintenance_not_detected(self):
        harness = QualificationHarness()
        events = [
            {
                "degradation_detected": False,
                "work_packet_created": False,
            }
            for _ in range(5)
        ]
        result = harness.validate_self_maintenance(events)
        assert result.status == PropertyStatus.FAILED

    def test_meta_orchestration_pass(self):
        harness = QualificationHarness()
        decisions = [
            {
                "correct_harness": True,
                "correct_model": True,
                "visible": True,
            }
            for _ in range(50)
        ]
        result = harness.validate_meta_orchestration(decisions)
        assert result.property_id == 7
        assert result.status == PropertyStatus.CONVERGED

    def test_operational_coverage_full(self):
        harness = QualificationHarness()

        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.rejected_reason = ""

        operations = [{"mutation_name": f"op_{i}"} for i in range(10)]
        result = harness.validate_operational_coverage(
            operations,
            governed_mutation_fn=lambda **kw: mock_response,
        )
        assert result.property_id == 2
        assert result.status == PropertyStatus.CONVERGED


# ── Self-Maintenance Bridge ───────────────────────────────────────────────


class TestSelfMaintenanceBridge:
    def test_callback_creation(self):
        from unittest.mock import MagicMock
        from substrate.organism.self_maintenance_bridge import create_degradation_callback

        wpe = MagicMock()
        callback = create_degradation_callback(wpe)
        assert callable(callback)

    def test_callback_creates_work_packet(self):
        from unittest.mock import MagicMock
        from substrate.organism.self_maintenance_bridge import create_degradation_callback
        from substrate.organism.outcome_learning import LearningSignal, SignalType

        wpe = MagicMock()
        callback = create_degradation_callback(wpe)

        signals = [
            LearningSignal(
                signal_type=SignalType.REPEATED_FAILURE,
                action_type="test_action",
                description="3 failures",
            )
        ]
        callback("test_action", 0.4, signals)

        wpe.create_packet_from_intent.assert_called_once()
        call_kwargs = wpe.create_packet_from_intent.call_args
        assert call_kwargs.kwargs.get("source_type") == "self_maintenance"

    def test_wire_self_maintenance(self):
        from unittest.mock import MagicMock
        from substrate.organism.self_maintenance_bridge import wire_self_maintenance

        learning = MagicMock()
        wpe = MagicMock()
        wire_self_maintenance(learning, wpe, threshold=0.6)

        learning.register_degradation_callback.assert_called_once()
        call_args = learning.register_degradation_callback.call_args
        assert call_args.kwargs.get("threshold") == 0.6

    def test_degradation_callback_registration(self):
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        loop = OutcomeLearningLoop.__new__(OutcomeLearningLoop)
        loop._store_path = "/dev/null"
        loop._outcomes = []
        loop._signals = []
        from collections import defaultdict
        loop._reliability = defaultdict(lambda: 0.5)
        loop._outcome_counts = defaultdict(lambda: defaultdict(int))
        loop._seen_action_types = set()
        loop._degradation_callback = None
        loop._degradation_threshold = 0.7
        loop._degradation_fired = set()

        called_with = {}

        def mock_callback(action_type, reliability, signals):
            called_with["action_type"] = action_type
            called_with["reliability"] = reliability

        loop.register_degradation_callback(mock_callback, threshold=0.5)
        assert loop._degradation_callback is not None
        assert loop._degradation_threshold == 0.5


# ── Report Generation ─────────────────────────────────────────────────────


class TestReportGeneration:
    def test_report_generation(self):
        harness = QualificationHarness()
        props = [
            PropertyResult(
                property_id=i,
                property_name=f"Prop {i}",
                status=PropertyStatus.CONVERGED,
                evidence=[f"test evidence {i}"],
                mutation_count=50,
            )
            for i in range(1, 10)
        ]
        report = harness.generate_report(props)
        assert report.orl_achieved == ORL.PRODUCTION_QUALIFIED
        assert "H1 SUPPORTED" in report.hypothesis_result

    def test_report_markdown(self):
        harness = QualificationHarness()
        report = QualificationReport(
            orl_achieved=5,
            properties=[
                PropertyResult(
                    property_id=1,
                    property_name="Test",
                    status=PropertyStatus.CONVERGED,
                    evidence=["test=0.95"],
                ),
            ],
            drift=DriftResult(passed=True),
            total_mutations=100,
            total_duration_s=60.0,
            hypothesis_result="H0 NOT FULLY REJECTED",
        )
        md = harness.format_report_markdown(report)
        assert "ORL-5" in md
        assert "PASS" in md
        assert "Test" in md

    def test_report_to_dict(self):
        report = QualificationReport(
            orl_achieved=8,
            total_mutations=500,
            hypothesis_result="H1 SUPPORTED",
        )
        d = report.to_dict()
        assert d["orl_achieved"] == 8
        assert d["orl_label"] == "PRODUCTION_QUALIFIED"
        assert d["total_mutations"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
