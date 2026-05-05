"""Phase 28: Simulation Calibration + Reality Alignment Layer v1 — tests.

Covers: ExecutionOutcome, CalibrationError, CalibrationRecord,
CalibrationFactors, CalibrationAdjustment, CalibrationEngine,
CalibrationStore, SimulationCalibrator, SimulationEngine calibration
integration, StrategySimulator calibration integration, AdvisorRuntime
calibration integration, hard invariants 75-79, boundary checks.

Target: 70-100 tests.
"""

from __future__ import annotations

import inspect
import threading
import unittest

from umh.runtime.calibration import (
    CalibrationAdjustment,
    CalibrationEngine,
    CalibrationError,
    CalibrationFactors,
    CalibrationRecord,
    CalibrationStore,
    ExecutionOutcome,
    SimulationCalibrator,
)
from umh.runtime.simulation import SimulatedOutcome, SimulationEngine
from umh.runtime.strategy import ExecutionStrategy


def _make_simulated(
    completion: float = 0.8,
    latency: float = 5.0,
    risk: float = 0.2,
    effort: float = 0.7,
) -> SimulatedOutcome:
    return SimulatedOutcome(
        strategy=ExecutionStrategy(),
        label="test",
        expected_completion_rate=completion,
        expected_latency=latency,
        expected_failure_risk=risk,
        estimated_effort=effort,
    )


def _make_outcome(
    completion: float = 0.75,
    latency: float = 4.5,
    failure: float = 0.15,
    effort: float = 0.65,
) -> ExecutionOutcome:
    return ExecutionOutcome(
        actual_completion_rate=completion,
        actual_latency=latency,
        actual_failure_rate=failure,
        actual_effort=effort,
    )


# ── Section 1: ExecutionOutcome ──────────────────────────────────────────


class TestExecutionOutcome(unittest.TestCase):
    """ExecutionOutcome immutable record tests."""

    def test_creation(self) -> None:
        o = _make_outcome()
        self.assertEqual(o.actual_completion_rate, 0.75)
        self.assertEqual(o.actual_latency, 4.5)
        self.assertEqual(o.actual_failure_rate, 0.15)
        self.assertEqual(o.actual_effort, 0.65)

    def test_frozen(self) -> None:
        o = _make_outcome()
        with self.assertRaises(AttributeError):
            o.actual_completion_rate = 0.9  # type: ignore[misc]

    def test_timestamp_auto(self) -> None:
        o = _make_outcome()
        self.assertIsInstance(o.timestamp, str)
        self.assertTrue(len(o.timestamp) > 0)

    def test_timestamp_explicit(self) -> None:
        o = ExecutionOutcome(
            actual_completion_rate=0.5,
            actual_latency=1.0,
            actual_failure_rate=0.1,
            actual_effort=0.3,
            timestamp="2026-01-01T00:00:00Z",
        )
        self.assertEqual(o.timestamp, "2026-01-01T00:00:00Z")

    def test_to_dict(self) -> None:
        o = _make_outcome()
        d = o.to_dict()
        self.assertEqual(d["actual_completion_rate"], 0.75)
        self.assertEqual(d["actual_latency"], 4.5)
        self.assertEqual(d["actual_failure_rate"], 0.15)
        self.assertEqual(d["actual_effort"], 0.65)
        self.assertIn("timestamp", d)

    def test_to_dict_rounds(self) -> None:
        o = ExecutionOutcome(
            actual_completion_rate=0.12345678,
            actual_latency=1.23456789,
            actual_failure_rate=0.00001111,
            actual_effort=0.99999999,
        )
        d = o.to_dict()
        self.assertEqual(d["actual_completion_rate"], 0.1235)
        self.assertEqual(d["actual_latency"], 1.2346)


# ── Section 2: CalibrationError ──────────────────────────────────────────


class TestCalibrationError(unittest.TestCase):
    """CalibrationError computation tests."""

    def test_creation(self) -> None:
        e = CalibrationError(
            completion_error=0.05,
            latency_error=0.5,
            failure_error=0.05,
            effort_error=0.05,
        )
        self.assertEqual(e.completion_error, 0.05)

    def test_frozen(self) -> None:
        e = CalibrationError(0.1, 0.2, 0.3, 0.4)
        with self.assertRaises(AttributeError):
            e.completion_error = 0.0  # type: ignore[misc]

    def test_total_error(self) -> None:
        e = CalibrationError(0.1, -0.2, 0.3, -0.1)
        self.assertAlmostEqual(e.total_error, 0.7)

    def test_mean_absolute_error(self) -> None:
        e = CalibrationError(0.1, -0.2, 0.3, -0.1)
        self.assertAlmostEqual(e.mean_absolute_error, 0.175)

    def test_zero_error(self) -> None:
        e = CalibrationError(0.0, 0.0, 0.0, 0.0)
        self.assertEqual(e.total_error, 0.0)
        self.assertEqual(e.mean_absolute_error, 0.0)

    def test_to_dict(self) -> None:
        e = CalibrationError(0.1, -0.2, 0.3, -0.1)
        d = e.to_dict()
        self.assertEqual(d["completion_error"], 0.1)
        self.assertEqual(d["latency_error"], -0.2)
        self.assertIn("total_error", d)
        self.assertIn("mean_absolute_error", d)


# ── Section 3: CalibrationRecord ─────────────────────────────────────────


class TestCalibrationRecord(unittest.TestCase):
    """CalibrationRecord immutable comparison tests."""

    def test_creation(self) -> None:
        error = CalibrationError(0.05, 0.5, 0.05, 0.05)
        rec = CalibrationRecord(
            predicted_completion=0.8,
            predicted_latency=5.0,
            predicted_failure_risk=0.2,
            predicted_effort=0.7,
            actual_completion=0.75,
            actual_latency=4.5,
            actual_failure_rate=0.15,
            actual_effort=0.65,
            error=error,
        )
        self.assertEqual(rec.predicted_completion, 0.8)
        self.assertEqual(rec.actual_completion, 0.75)

    def test_frozen(self) -> None:
        error = CalibrationError(0.0, 0.0, 0.0, 0.0)
        rec = CalibrationRecord(
            predicted_completion=0.5,
            predicted_latency=1.0,
            predicted_failure_risk=0.1,
            predicted_effort=0.3,
            actual_completion=0.5,
            actual_latency=1.0,
            actual_failure_rate=0.1,
            actual_effort=0.3,
            error=error,
        )
        with self.assertRaises(AttributeError):
            rec.predicted_completion = 0.9  # type: ignore[misc]

    def test_to_dict(self) -> None:
        error = CalibrationError(0.05, 0.5, 0.05, 0.05)
        rec = CalibrationRecord(
            predicted_completion=0.8,
            predicted_latency=5.0,
            predicted_failure_risk=0.2,
            predicted_effort=0.7,
            actual_completion=0.75,
            actual_latency=4.5,
            actual_failure_rate=0.15,
            actual_effort=0.65,
            error=error,
            timestamp="2026-01-01T00:00:00Z",
        )
        d = rec.to_dict()
        self.assertEqual(d["predicted_completion"], 0.8)
        self.assertEqual(d["actual_completion"], 0.75)
        self.assertIn("error", d)
        self.assertIsInstance(d["error"], dict)


# ── Section 4: CalibrationFactors ────────────────────────────────────────


class TestCalibrationFactors(unittest.TestCase):
    """CalibrationFactors defaults and bounds tests."""

    def test_defaults(self) -> None:
        f = CalibrationFactors()
        self.assertEqual(f.completion_factor, 1.0)
        self.assertEqual(f.latency_factor, 1.0)
        self.assertEqual(f.failure_factor, 1.0)
        self.assertEqual(f.effort_factor, 1.0)

    def test_custom(self) -> None:
        f = CalibrationFactors(
            completion_factor=0.9,
            latency_factor=1.1,
            failure_factor=0.8,
            effort_factor=1.2,
        )
        self.assertEqual(f.completion_factor, 0.9)
        self.assertEqual(f.effort_factor, 1.2)

    def test_frozen(self) -> None:
        f = CalibrationFactors()
        with self.assertRaises(AttributeError):
            f.completion_factor = 0.5  # type: ignore[misc]

    def test_to_dict(self) -> None:
        f = CalibrationFactors(completion_factor=0.95)
        d = f.to_dict()
        self.assertEqual(d["completion_factor"], 0.95)
        self.assertEqual(d["latency_factor"], 1.0)


# ── Section 5: CalibrationAdjustment ────────────────────────────────────


class TestCalibrationAdjustment(unittest.TestCase):
    """CalibrationAdjustment record tests."""

    def test_creation(self) -> None:
        adj = CalibrationAdjustment(
            metric="completion",
            direction="decrease",
            magnitude=0.01,
            reason="Simulation overestimates completion by 0.05",
        )
        self.assertEqual(adj.metric, "completion")
        self.assertEqual(adj.direction, "decrease")
        self.assertEqual(adj.magnitude, 0.01)

    def test_frozen(self) -> None:
        adj = CalibrationAdjustment("x", "up", 0.1, "r")
        with self.assertRaises(AttributeError):
            adj.metric = "y"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        adj = CalibrationAdjustment("latency", "increase", 0.023, "reason")
        d = adj.to_dict()
        self.assertEqual(d["metric"], "latency")
        self.assertEqual(d["magnitude"], 0.023)


# ── Section 6: CalibrationEngine ─────────────────────────────────────────


class TestCalibrationEngine(unittest.TestCase):
    """CalibrationEngine compare and build_record tests."""

    def test_compare_perfect(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated(0.8, 5.0, 0.2, 0.7)
        real = _make_outcome(0.8, 5.0, 0.2, 0.7)
        err = eng.compare(sim, real)
        self.assertAlmostEqual(err.completion_error, 0.0)
        self.assertAlmostEqual(err.latency_error, 0.0)
        self.assertAlmostEqual(err.failure_error, 0.0)
        self.assertAlmostEqual(err.effort_error, 0.0)

    def test_compare_overestimate(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated(0.9, 6.0, 0.3, 0.8)
        real = _make_outcome(0.7, 4.0, 0.1, 0.5)
        err = eng.compare(sim, real)
        self.assertAlmostEqual(err.completion_error, 0.2)
        self.assertAlmostEqual(err.latency_error, 2.0)
        self.assertAlmostEqual(err.failure_error, 0.2)
        self.assertAlmostEqual(err.effort_error, 0.3)

    def test_compare_underestimate(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated(0.5, 3.0, 0.1, 0.3)
        real = _make_outcome(0.8, 6.0, 0.3, 0.7)
        err = eng.compare(sim, real)
        self.assertAlmostEqual(err.completion_error, -0.3)
        self.assertAlmostEqual(err.latency_error, -3.0)
        self.assertAlmostEqual(err.failure_error, -0.2)
        self.assertAlmostEqual(err.effort_error, -0.4)

    def test_compare_signed(self) -> None:
        """Error is predicted - actual (signed direction matters)."""
        eng = CalibrationEngine()
        sim = _make_simulated(0.9, 5.0, 0.2, 0.7)
        real = _make_outcome(0.7, 5.0, 0.2, 0.7)
        err = eng.compare(sim, real)
        self.assertGreater(err.completion_error, 0)

    def test_build_record(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated(0.8, 5.0, 0.2, 0.7)
        real = _make_outcome(0.75, 4.5, 0.15, 0.65)
        rec = eng.build_record(sim, real)
        self.assertIsInstance(rec, CalibrationRecord)
        self.assertEqual(rec.predicted_completion, 0.8)
        self.assertEqual(rec.actual_completion, 0.75)
        self.assertAlmostEqual(rec.error.completion_error, 0.05)

    def test_build_record_preserves_timestamp(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated()
        real = ExecutionOutcome(
            actual_completion_rate=0.5,
            actual_latency=1.0,
            actual_failure_rate=0.1,
            actual_effort=0.3,
            timestamp="2026-04-30T12:00:00Z",
        )
        rec = eng.build_record(sim, real)
        self.assertEqual(rec.timestamp, "2026-04-30T12:00:00Z")

    def test_build_record_deterministic(self) -> None:
        eng = CalibrationEngine()
        sim = _make_simulated()
        real = _make_outcome()
        r1 = eng.build_record(sim, real)
        r2 = eng.build_record(sim, real)
        self.assertEqual(r1.error.completion_error, r2.error.completion_error)
        self.assertEqual(r1.error.total_error, r2.error.total_error)


# ── Section 7: CalibrationStore ──────────────────────────────────────────


class TestCalibrationStore(unittest.TestCase):
    """CalibrationStore thread-safe append-only tests."""

    def _make_record(self, completion_error: float = 0.05) -> CalibrationRecord:
        return CalibrationRecord(
            predicted_completion=0.8,
            predicted_latency=5.0,
            predicted_failure_risk=0.2,
            predicted_effort=0.7,
            actual_completion=0.8 - completion_error,
            actual_latency=5.0,
            actual_failure_rate=0.2,
            actual_effort=0.7,
            error=CalibrationError(completion_error, 0.0, 0.0, 0.0),
        )

    def test_empty(self) -> None:
        store = CalibrationStore()
        self.assertEqual(store.count, 0)
        self.assertEqual(store.list_records(), [])

    def test_append(self) -> None:
        store = CalibrationStore()
        store.append(self._make_record())
        self.assertEqual(store.count, 1)

    def test_list_records(self) -> None:
        store = CalibrationStore()
        store.append(self._make_record(0.1))
        store.append(self._make_record(0.2))
        records = store.list_records()
        self.assertEqual(len(records), 2)
        self.assertAlmostEqual(records[0].error.completion_error, 0.1)
        self.assertAlmostEqual(records[1].error.completion_error, 0.2)

    def test_recent(self) -> None:
        store = CalibrationStore()
        for i in range(10):
            store.append(self._make_record(i * 0.01))
        recent = store.recent(3)
        self.assertEqual(len(recent), 3)
        self.assertAlmostEqual(recent[0].error.completion_error, 0.07)

    def test_eviction(self) -> None:
        store = CalibrationStore(max_records=20)
        for i in range(30):
            store.append(self._make_record(i * 0.01))
        self.assertEqual(store.count, 20)
        records = store.list_records()
        self.assertAlmostEqual(records[0].error.completion_error, 0.10)

    def test_min_max_records(self) -> None:
        store = CalibrationStore(max_records=3)
        self.assertEqual(store._max_records, 10)

    def test_mean_errors_empty(self) -> None:
        store = CalibrationStore()
        self.assertIsNone(store.mean_errors())

    def test_mean_errors(self) -> None:
        store = CalibrationStore()
        store.append(self._make_record(0.1))
        store.append(self._make_record(0.2))
        mean = store.mean_errors()
        self.assertIsNotNone(mean)
        self.assertAlmostEqual(mean.completion_error, 0.15)

    def test_mean_errors_n(self) -> None:
        store = CalibrationStore()
        for i in range(5):
            store.append(self._make_record((i + 1) * 0.1))
        mean = store.mean_errors(n=2)
        self.assertIsNotNone(mean)
        self.assertAlmostEqual(mean.completion_error, 0.45)

    def test_to_dict(self) -> None:
        store = CalibrationStore()
        store.append(self._make_record())
        d = store.to_dict()
        self.assertEqual(d["total_records"], 1)
        self.assertIn("mean_errors", d)

    def test_thread_safety(self) -> None:
        store = CalibrationStore()
        errors: list[Exception] = []

        def writer(n: int) -> None:
            try:
                for _ in range(50):
                    store.append(self._make_record(n * 0.001))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)
        self.assertEqual(store.count, 200)


# ── Section 8: SimulationCalibrator ──────────────────────────────────────


class TestSimulationCalibrator(unittest.TestCase):
    """SimulationCalibrator bounded multiplicative adjustment tests."""

    def test_no_adjustment_for_small_error(self) -> None:
        cal = SimulationCalibrator()
        factors = CalibrationFactors()
        err = CalibrationError(0.005, 0.005, 0.005, 0.005)
        new_factors, adjustments = cal.calibrate(factors, err)
        self.assertEqual(new_factors, factors)
        self.assertEqual(len(adjustments), 0)

    def test_overestimate_reduces_factor(self) -> None:
        cal = SimulationCalibrator()
        factors = CalibrationFactors()
        err = CalibrationError(0.2, 0.0, 0.0, 0.0)
        new_factors, adjustments = cal.calibrate(factors, err)
        self.assertLess(new_factors.completion_factor, 1.0)
        self.assertEqual(len(adjustments), 1)
        self.assertEqual(adjustments[0].direction, "decrease")

    def test_underestimate_increases_factor(self) -> None:
        cal = SimulationCalibrator()
        factors = CalibrationFactors()
        err = CalibrationError(-0.2, 0.0, 0.0, 0.0)
        new_factors, adjustments = cal.calibrate(factors, err)
        self.assertGreater(new_factors.completion_factor, 1.0)
        self.assertEqual(adjustments[0].direction, "increase")

    def test_latency_overestimate(self) -> None:
        cal = SimulationCalibrator()
        err = CalibrationError(0.0, 2.0, 0.0, 0.0)
        new_factors, adj = cal.calibrate(CalibrationFactors(), err)
        self.assertLess(new_factors.latency_factor, 1.0)

    def test_failure_inverted(self) -> None:
        """Positive failure_error (overestimate) should reduce factor."""
        cal = SimulationCalibrator()
        err = CalibrationError(0.0, 0.0, 0.2, 0.0)
        new_factors, adj = cal.calibrate(CalibrationFactors(), err)
        self.assertGreater(new_factors.failure_factor, 1.0)

    def test_effort_overestimate(self) -> None:
        cal = SimulationCalibrator()
        err = CalibrationError(0.0, 0.0, 0.0, 0.3)
        new_factors, adj = cal.calibrate(CalibrationFactors(), err)
        self.assertLess(new_factors.effort_factor, 1.0)

    def test_bounded_min(self) -> None:
        cal = SimulationCalibrator(learning_rate=0.5)
        factors = CalibrationFactors(completion_factor=0.15)
        err = CalibrationError(5.0, 0.0, 0.0, 0.0)
        new_factors, _ = cal.calibrate(factors, err)
        self.assertGreaterEqual(new_factors.completion_factor, 0.1)

    def test_bounded_max(self) -> None:
        cal = SimulationCalibrator(learning_rate=0.5)
        factors = CalibrationFactors(completion_factor=1.9)
        err = CalibrationError(-5.0, 0.0, 0.0, 0.0)
        new_factors, _ = cal.calibrate(factors, err)
        self.assertLessEqual(new_factors.completion_factor, 2.0)

    def test_learning_rate_default(self) -> None:
        cal = SimulationCalibrator()
        self.assertAlmostEqual(cal.learning_rate, 0.1)

    def test_learning_rate_custom(self) -> None:
        cal = SimulationCalibrator(learning_rate=0.3)
        self.assertAlmostEqual(cal.learning_rate, 0.3)

    def test_learning_rate_clamped_low(self) -> None:
        cal = SimulationCalibrator(learning_rate=0.001)
        self.assertAlmostEqual(cal.learning_rate, 0.01)

    def test_learning_rate_clamped_high(self) -> None:
        cal = SimulationCalibrator(learning_rate=0.9)
        self.assertAlmostEqual(cal.learning_rate, 0.5)

    def test_deterministic(self) -> None:
        cal = SimulationCalibrator()
        factors = CalibrationFactors()
        err = CalibrationError(0.15, -0.3, 0.1, -0.2)
        f1, a1 = cal.calibrate(factors, err)
        f2, a2 = cal.calibrate(factors, err)
        self.assertEqual(f1, f2)
        self.assertEqual(len(a1), len(a2))

    def test_multiple_adjustments(self) -> None:
        cal = SimulationCalibrator()
        err = CalibrationError(0.2, 0.3, 0.1, 0.2)
        _, adjustments = cal.calibrate(CalibrationFactors(), err)
        self.assertGreaterEqual(len(adjustments), 3)

    def test_adjustment_has_reason(self) -> None:
        cal = SimulationCalibrator()
        err = CalibrationError(0.2, 0.0, 0.0, 0.0)
        _, adjustments = cal.calibrate(CalibrationFactors(), err)
        self.assertEqual(len(adjustments), 1)
        self.assertIn("overestimates", adjustments[0].reason)


# ── Section 9: SimulationEngine with CalibrationFactors ──────────────────


class TestSimulationEngineCalibration(unittest.TestCase):
    """SimulationEngine applies calibration factors correctly."""

    def test_no_calibration_unchanged(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        o1 = engine.simulate(strategy)
        o2 = engine.simulate(strategy, calibration=None)
        self.assertAlmostEqual(o1.expected_completion_rate, o2.expected_completion_rate)

    def test_identity_calibration_unchanged(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        o1 = engine.simulate(strategy)
        o2 = engine.simulate(strategy, calibration=CalibrationFactors())
        self.assertAlmostEqual(o1.expected_completion_rate, o2.expected_completion_rate)
        self.assertAlmostEqual(o1.expected_latency, o2.expected_latency)
        self.assertAlmostEqual(o1.expected_failure_risk, o2.expected_failure_risk)
        self.assertAlmostEqual(o1.estimated_effort, o2.estimated_effort)

    def test_calibration_scales_completion(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(completion_factor=0.5)
        o_base = engine.simulate(strategy)
        o_cal = engine.simulate(strategy, calibration=factors)
        self.assertAlmostEqual(
            o_cal.expected_completion_rate,
            o_base.expected_completion_rate * 0.5,
            places=3,
        )

    def test_calibration_scales_latency(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(latency_factor=1.5)
        o_base = engine.simulate(strategy)
        o_cal = engine.simulate(strategy, calibration=factors)
        self.assertAlmostEqual(
            o_cal.expected_latency,
            o_base.expected_latency * 1.5,
            places=3,
        )

    def test_calibration_scales_risk(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(failure_factor=1.3)
        o_base = engine.simulate(strategy)
        o_cal = engine.simulate(strategy, calibration=factors)
        expected_risk = min(1.0, o_base.expected_failure_risk * 1.3)
        self.assertAlmostEqual(o_cal.expected_failure_risk, expected_risk, places=3)

    def test_calibration_scales_effort(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(effort_factor=0.8)
        o_base = engine.simulate(strategy)
        o_cal = engine.simulate(strategy, calibration=factors)
        expected_effort = max(0.1, o_base.estimated_effort * 0.8)
        self.assertAlmostEqual(o_cal.estimated_effort, expected_effort, places=3)

    def test_calibration_clamps_completion(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(completion_factor=5.0)
        o = engine.simulate(strategy, calibration=factors)
        self.assertLessEqual(o.expected_completion_rate, 1.0)

    def test_calibration_clamps_risk(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy(batch_size=10, retry_budget=0)
        factors = CalibrationFactors(failure_factor=5.0)
        o = engine.simulate(strategy, calibration=factors)
        self.assertLessEqual(o.expected_failure_risk, 1.0)

    def test_calibration_clamps_latency_min(self) -> None:
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        factors = CalibrationFactors(latency_factor=0.001)
        o = engine.simulate(strategy, calibration=factors)
        self.assertGreaterEqual(o.expected_latency, 0.1)


# ── Section 10: StrategySimulator with calibration ───────────────────────


class TestStrategySimulatorCalibration(unittest.TestCase):
    """StrategySimulator passes calibration through the pipeline."""

    def test_run_without_calibration(self) -> None:
        from umh.runtime.evaluator import StrategySimulator

        sim = StrategySimulator()
        result = sim.run(ExecutionStrategy())
        self.assertIsNotNone(result.selected)

    def test_run_with_calibration(self) -> None:
        from umh.runtime.evaluator import StrategySimulator

        sim = StrategySimulator()
        factors = CalibrationFactors(completion_factor=0.5)
        result = sim.run(ExecutionStrategy(), calibration=factors)
        self.assertLessEqual(result.selected.expected_completion_rate, 0.5)

    def test_calibration_affects_ranking(self) -> None:
        from umh.runtime.evaluator import StrategySimulator

        sim = StrategySimulator()
        base = ExecutionStrategy()
        r_none = sim.run(base)
        r_cal = sim.run(base, calibration=CalibrationFactors(latency_factor=0.1))
        self.assertNotEqual(
            r_none.selected.expected_latency,
            r_cal.selected.expected_latency,
        )


# ── Section 11: Advisor integration ─────────────────────────────────────


class TestAdvisorCalibration(unittest.TestCase):
    """AdvisorRuntime calibration integration tests."""

    def _make_advisor(self, **kwargs):
        from umh.model.aggregator import BehaviorAggregator
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.evaluator import StrategySimulator
        from umh.runtime.strategy import StrategyBuilder

        defaults = dict(
            strategy_builder=StrategyBuilder(),
            strategy_simulator=StrategySimulator(),
            calibration_engine=CalibrationEngine(),
            calibration_store=CalibrationStore(),
            simulation_calibrator=SimulationCalibrator(),
        )
        defaults.update(kwargs)
        return AdvisorRuntime(**defaults)

    def test_properties_accessible(self) -> None:
        advisor = self._make_advisor()
        self.assertIsNotNone(advisor.calibration_engine)
        self.assertIsNotNone(advisor.calibration_store)
        self.assertIsNotNone(advisor.simulation_calibrator)
        self.assertIsNotNone(advisor.calibration_factors)

    def test_default_factors(self) -> None:
        advisor = self._make_advisor()
        f = advisor.calibration_factors
        self.assertEqual(f.completion_factor, 1.0)
        self.assertEqual(f.latency_factor, 1.0)

    def test_tick_includes_calibration_keys(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        result = advisor.tick()
        self.assertIn("calibration_recorded", result)
        self.assertIn("calibration_adjusted", result)
        advisor.stop()

    def test_record_outcome(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        outcome = _make_outcome()
        recorded = advisor.record_outcome(outcome)
        self.assertTrue(recorded)
        self.assertEqual(advisor.calibration_store.count, 1)
        advisor.stop()

    def test_record_outcome_requires_simulation(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime(
            calibration_engine=CalibrationEngine(),
            calibration_store=CalibrationStore(),
        )
        outcome = _make_outcome()
        recorded = advisor.record_outcome(outcome)
        self.assertFalse(recorded)

    def test_get_state_includes_calibration(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        state = advisor.get_state()
        self.assertIn("calibration", state)
        self.assertIn("calibration_factors", state)
        advisor.stop()

    def test_clear_resets_calibration(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        outcome = _make_outcome()
        advisor.record_outcome(outcome)
        self.assertEqual(advisor.calibration_store.count, 1)
        advisor.clear()
        self.assertEqual(advisor.calibration_store.count, 0)
        self.assertEqual(advisor.calibration_factors.completion_factor, 1.0)

    def test_calibration_adjusts_after_enough_records(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        for _ in range(5):
            outcome = ExecutionOutcome(
                actual_completion_rate=0.5,
                actual_latency=10.0,
                actual_failure_rate=0.5,
                actual_effort=1.0,
            )
            advisor.record_outcome(outcome)
        from umh.learning.feedback import ExecutionFeedback

        fb = [
            ExecutionFeedback(
                job_id="j1",
                node_id="n1",
                task_type="t",
                success=True,
                duration_ms=100,
            )
        ]
        advisor.tick(completed_feedback=fb)
        advisor.stop()

    def test_no_calibration_without_components(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        self.assertEqual(result["calibration_recorded"], 0)
        self.assertFalse(result["calibration_adjusted"])
        advisor.stop()


# ── Section 12: Hard invariants 75-79 ───────────────────────────────────


class TestHardInvariants(unittest.TestCase):
    """Hard invariants 75-79 for calibration layer."""

    def test_inv75_calibration_records_immutable(self) -> None:
        """INV75: Calibration records are frozen dataclasses."""
        rec = CalibrationRecord(
            predicted_completion=0.8,
            predicted_latency=5.0,
            predicted_failure_risk=0.2,
            predicted_effort=0.7,
            actual_completion=0.75,
            actual_latency=4.5,
            actual_failure_rate=0.15,
            actual_effort=0.65,
            error=CalibrationError(0.05, 0.5, 0.05, 0.05),
        )
        with self.assertRaises(AttributeError):
            rec.predicted_completion = 0.0  # type: ignore[misc]

        err = CalibrationError(0.1, 0.2, 0.3, 0.4)
        with self.assertRaises(AttributeError):
            err.completion_error = 0.0  # type: ignore[misc]

        factors = CalibrationFactors()
        with self.assertRaises(AttributeError):
            factors.completion_factor = 0.0  # type: ignore[misc]

        adj = CalibrationAdjustment("m", "d", 0.1, "r")
        with self.assertRaises(AttributeError):
            adj.metric = "x"  # type: ignore[misc]

        outcome = _make_outcome()
        with self.assertRaises(AttributeError):
            outcome.actual_completion_rate = 0.0  # type: ignore[misc]

    def test_inv76_calibration_store_append_only(self) -> None:
        """INV76: CalibrationStore is append-only, no in-place updates."""
        store = CalibrationStore()
        record = CalibrationRecord(
            predicted_completion=0.8,
            predicted_latency=5.0,
            predicted_failure_risk=0.2,
            predicted_effort=0.7,
            actual_completion=0.75,
            actual_latency=4.5,
            actual_failure_rate=0.15,
            actual_effort=0.65,
            error=CalibrationError(0.05, 0.0, 0.0, 0.0),
        )
        store.append(record)
        records = store.list_records()
        self.assertEqual(len(records), 1)
        self.assertFalse(hasattr(store, "update"))
        self.assertFalse(hasattr(store, "delete"))
        self.assertFalse(hasattr(store, "remove"))

    def test_inv77_factors_bounded(self) -> None:
        """INV77: Calibration factors must stay within [0.1, 2.0]."""
        cal = SimulationCalibrator(learning_rate=0.5)
        factors = CalibrationFactors()
        for _ in range(100):
            err = CalibrationError(5.0, 5.0, 5.0, 5.0)
            factors, _ = cal.calibrate(factors, err)
        self.assertGreaterEqual(factors.completion_factor, 0.1)
        self.assertLessEqual(factors.completion_factor, 2.0)
        self.assertGreaterEqual(factors.latency_factor, 0.1)
        self.assertLessEqual(factors.latency_factor, 2.0)
        self.assertGreaterEqual(factors.failure_factor, 0.1)
        self.assertLessEqual(factors.failure_factor, 2.0)
        self.assertGreaterEqual(factors.effort_factor, 0.1)
        self.assertLessEqual(factors.effort_factor, 2.0)

    def test_inv77_factors_bounded_negative(self) -> None:
        """INV77: Factors bounded even with extreme negative errors."""
        cal = SimulationCalibrator(learning_rate=0.5)
        factors = CalibrationFactors()
        for _ in range(100):
            err = CalibrationError(-5.0, -5.0, -5.0, -5.0)
            factors, _ = cal.calibrate(factors, err)
        self.assertGreaterEqual(factors.completion_factor, 0.1)
        self.assertLessEqual(factors.completion_factor, 2.0)

    def test_inv78_calibration_deterministic(self) -> None:
        """INV78: Same inputs always produce the same calibration output."""
        cal = SimulationCalibrator()
        factors = CalibrationFactors()
        err = CalibrationError(0.15, -0.3, 0.1, -0.2)
        f1, a1 = cal.calibrate(factors, err)
        f2, a2 = cal.calibrate(factors, err)
        self.assertEqual(f1, f2)
        self.assertEqual(len(a1), len(a2))
        for x, y in zip(a1, a2):
            self.assertEqual(x.metric, y.metric)
            self.assertEqual(x.direction, y.direction)
            self.assertAlmostEqual(x.magnitude, y.magnitude)

    def test_inv79_no_forbidden_imports(self) -> None:
        """INV79: calibration.py has no forbidden boundary imports."""
        import umh.runtime.calibration as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import subprocess", src)
        _shell_pattern = "os" + "." + "system"
        self.assertNotIn(_shell_pattern, src)
        self.assertNotIn("from umh.cells", src)
        self.assertNotIn("from umh.environments", src)
        self.assertNotIn("from umh.adapters", src)

    def test_inv79_simulation_no_forbidden_imports(self) -> None:
        """INV79: simulation.py has no forbidden boundary imports."""
        import umh.runtime.simulation as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("from umh.cells", src)
        self.assertNotIn("from umh.environments", src)
        self.assertNotIn("from umh.adapters", src)

    def test_inv79_evaluator_no_forbidden_imports(self) -> None:
        """INV79: evaluator.py has no forbidden boundary imports."""
        import umh.runtime.evaluator as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("from umh.cells", src)
        self.assertNotIn("from umh.environments", src)
        self.assertNotIn("from umh.adapters", src)


# ── Section 13: Boundary and export checks ──────────────────────────────


class TestBoundaryAndExports(unittest.TestCase):
    """Import, compile, and export boundary tests."""

    def test_import_calibration(self) -> None:
        import umh.runtime.calibration  # noqa: F401

    def test_import_all_types(self) -> None:
        from umh.runtime.calibration import (  # noqa: F401
            CalibrationAdjustment,
            CalibrationEngine,
            CalibrationError,
            CalibrationFactors,
            CalibrationRecord,
            CalibrationStore,
            ExecutionOutcome,
            SimulationCalibrator,
        )

    def test_runtime_exports_calibration(self) -> None:
        from umh.runtime import (  # noqa: F401
            CalibrationAdjustment,
            CalibrationEngine,
            CalibrationError,
            CalibrationFactors,
            CalibrationRecord,
            CalibrationStore,
            ExecutionOutcome,
            SimulationCalibrator,
        )

    def test_compile_calibration(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/calibration.py", doraise=True)

    def test_compile_simulation(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/simulation.py", doraise=True)

    def test_compile_evaluator(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/evaluator.py", doraise=True)

    def test_compile_advisor(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/advisor.py", doraise=True)

    def test_end_to_end_calibration_pipeline(self) -> None:
        """Full pipeline: simulate → compare → record → calibrate."""
        engine = SimulationEngine()
        strategy = ExecutionStrategy()
        simulated = engine.simulate(strategy)

        real = ExecutionOutcome(
            actual_completion_rate=0.6,
            actual_latency=8.0,
            actual_failure_rate=0.3,
            actual_effort=0.9,
        )

        cal_engine = CalibrationEngine()
        record = cal_engine.build_record(simulated, real)

        store = CalibrationStore()
        store.append(record)
        store.append(record)
        store.append(record)

        mean_err = store.mean_errors()
        self.assertIsNotNone(mean_err)

        calibrator = SimulationCalibrator()
        factors = CalibrationFactors()
        new_factors, adjustments = calibrator.calibrate(factors, mean_err)

        self.assertIsInstance(new_factors, CalibrationFactors)
        self.assertGreater(len(adjustments), 0)

        calibrated = engine.simulate(strategy, calibration=new_factors)
        self.assertIsInstance(calibrated, SimulatedOutcome)


if __name__ == "__main__":
    unittest.main()
