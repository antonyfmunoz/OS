"""Tests for runtime.world_calibration — prediction vs reality error measurement."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.world.types import (
    Entity,
    Relation,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import (
    EntityAssessment,
    EntityTrend,
    WorldUnderstanding,
)
from umh.world.calibration import (
    BIAS_EMA_ALPHA,
    ERROR_CLAMP,
    MAX_CALIBRATION_SUMMARIES,
    MAX_PREDICTION_RECORDS,
    CalibrationError,
    CalibrationMemory,
    CalibrationSummary,
    ModelBias,
    OutcomeRecord,
    PredictionRecord,
    WorldCalibrationEngine,
    build_calibration_summary,
    compute_classification_errors,
    compute_fact_errors,
    compute_model_bias,
)


# ─── Test helpers ───────────────────────────────────────────────


def _entity(eid: str) -> Entity:
    return Entity(entity_id=eid, entity_type="generic", attributes={})


def _fact(
    entity_id: str,
    key: str,
    value: float | int | str | bool | None,
    confidence: float = 0.8,
) -> StateFact:
    return StateFact(
        entity_id=entity_id,
        key=key,
        value=value,
        confidence=confidence,
        last_updated_turn=1,
        update_count=1,
    )


def _snapshot(
    entities: list[Entity] | None = None,
    facts: list[StateFact] | None = None,
    obs_count: int = 10,
    version: int = 1,
) -> WorldSnapshot:
    return WorldSnapshot(
        entities=tuple(entities or []),
        relations=(),
        state_facts=tuple(facts or []),
        observation_count=obs_count,
        version=version,
    )


def _assessment(
    entity_id: str,
    health: str = "good",
    stability: str = "stable",
    confidence: float = 0.8,
) -> EntityAssessment:
    return EntityAssessment(
        entity_id=entity_id,
        health=health,
        stability=stability,
        trend_summary=(),
        risk_flags=(),
        confidence=confidence,
    )


def _understanding(
    assessments: list[EntityAssessment] | None = None,
    global_flags: list[str] | None = None,
    version: int = 1,
) -> WorldUnderstanding:
    a = assessments or []
    return WorldUnderstanding(
        entity_assessments=tuple(a),
        relation_impacts=(),
        global_flags=tuple(global_flags or []),
        snapshot_version=version,
        derived_count=len(a),
    )


# ─── 1. Prediction recording ──────────────────────────────────


class TestPredictionRecording(unittest.TestCase):
    def test_record_prediction(self) -> None:
        engine = WorldCalibrationEngine()
        snap = _snapshot(entities=[_entity("e1")])
        und = _understanding(assessments=[_assessment("e1")])
        record = engine.record_prediction(
            action_id="a1",
            predicted_snapshot=snap,
            predicted_understanding=und,
            horizon=3,
            timestamp_step=10,
        )
        self.assertEqual(record.action_id, "a1")
        self.assertEqual(record.horizon, 3)
        self.assertEqual(record.timestamp_step, 10)
        self.assertEqual(len(engine.memory.predictions), 1)

    def test_record_outcome(self) -> None:
        engine = WorldCalibrationEngine()
        snap = _snapshot(entities=[_entity("e1")])
        und = _understanding(assessments=[_assessment("e1")])
        record = engine.record_outcome(
            action_id="a1",
            actual_snapshot=snap,
            actual_understanding=und,
            timestamp_step=13,
        )
        self.assertEqual(record.action_id, "a1")
        self.assertEqual(record.timestamp_step, 13)
        self.assertEqual(len(engine.memory.outcomes), 1)

    def test_prediction_to_dict(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        und = _understanding()
        record = PredictionRecord(
            action_id="a1",
            predicted_snapshot=snap,
            predicted_understanding=und,
            horizon=3,
            timestamp_step=10,
        )
        d = record.to_dict()
        self.assertEqual(d["action_id"], "a1")
        self.assertEqual(d["horizon"], 3)

    def test_outcome_to_dict(self) -> None:
        snap = _snapshot()
        und = _understanding()
        record = OutcomeRecord(
            action_id="a1",
            actual_snapshot=snap,
            actual_understanding=und,
            timestamp_step=13,
        )
        d = record.to_dict()
        self.assertEqual(d["action_id"], "a1")


# ─── 2. Delayed outcome matching ──────────────────────────────


class TestDelayedMatching(unittest.TestCase):
    def test_match_mature_prediction(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        p_und = _understanding(assessments=[_assessment("e1")])
        engine.record_prediction("a1", p_snap, p_und, horizon=3, timestamp_step=10)

        a_snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.2)],
        )
        a_und = _understanding(assessments=[_assessment("e1")])
        engine.record_outcome("a1", a_snap, a_und, timestamp_step=13)

        summaries = engine.match_predictions(current_step=13)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].action_id, "a1")

    def test_no_match_before_maturity(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot(entities=[_entity("e1")])
        p_und = _understanding()
        engine.record_prediction("a1", p_snap, p_und, horizon=3, timestamp_step=10)

        a_snap = _snapshot(entities=[_entity("e1")])
        a_und = _understanding()
        engine.record_outcome("a1", a_snap, a_und, timestamp_step=11)

        summaries = engine.match_predictions(current_step=11)
        self.assertEqual(len(summaries), 0)

    def test_no_match_without_outcome(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot()
        p_und = _understanding()
        engine.record_prediction("a1", p_snap, p_und, horizon=2, timestamp_step=5)

        summaries = engine.match_predictions(current_step=10)
        self.assertEqual(len(summaries), 0)

    def test_no_duplicate_match(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "v", 1.0)],
        )
        p_und = _understanding(assessments=[_assessment("e1")])
        engine.record_prediction("a1", p_snap, p_und, horizon=1, timestamp_step=5)

        a_snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "v", 1.1)],
        )
        a_und = _understanding(assessments=[_assessment("e1")])
        engine.record_outcome("a1", a_snap, a_und, timestamp_step=6)

        s1 = engine.match_predictions(current_step=6)
        s2 = engine.match_predictions(current_step=7)
        self.assertEqual(len(s1), 1)
        self.assertEqual(len(s2), 0)

    def test_multiple_predictions_matched_independently(self) -> None:
        engine = WorldCalibrationEngine()
        for i in range(3):
            p_snap = _snapshot(
                entities=[_entity("e1")],
                facts=[_fact("e1", "v", float(i))],
            )
            p_und = _understanding(assessments=[_assessment("e1")])
            engine.record_prediction(
                f"a{i}", p_snap, p_und, horizon=2, timestamp_step=i
            )
            a_snap = _snapshot(
                entities=[_entity("e1")],
                facts=[_fact("e1", "v", float(i) + 0.1)],
            )
            a_und = _understanding(assessments=[_assessment("e1")])
            engine.record_outcome(f"a{i}", a_snap, a_und, timestamp_step=i + 2)

        summaries = engine.match_predictions(current_step=5)
        self.assertEqual(len(summaries), 3)


# ─── 3. Error computation correctness ──────────────────────────


class TestErrorComputation(unittest.TestCase):
    def test_numeric_error(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "score", 5.0)])
        actual = _snapshot(facts=[_fact("e1", "score", 5.5)])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, "numeric")
        self.assertGreater(errors[0].error_magnitude, 0.0)
        self.assertLessEqual(errors[0].error_magnitude, ERROR_CLAMP)

    def test_numeric_error_normalization(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "v", 100.0)])
        actual = _snapshot(facts=[_fact("e1", "v", 101.0)])
        errors = compute_fact_errors(predicted, actual)
        self.assertLess(errors[0].error_magnitude, 0.05)

    def test_perfect_prediction_zero_error(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "v", 5.0)])
        actual = _snapshot(facts=[_fact("e1", "v", 5.0)])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(errors[0].error_magnitude, 0.0)

    def test_categorical_match(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "status", "active")])
        actual = _snapshot(facts=[_fact("e1", "status", "active")])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(errors[0].error_magnitude, 0.0)
        self.assertEqual(errors[0].error_type, "categorical")

    def test_categorical_mismatch(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "status", "active")])
        actual = _snapshot(facts=[_fact("e1", "status", "inactive")])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(errors[0].error_magnitude, ERROR_CLAMP)

    def test_bool_comparison(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "flag", True)])
        actual = _snapshot(facts=[_fact("e1", "flag", False)])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(errors[0].error_magnitude, ERROR_CLAMP)
        self.assertEqual(errors[0].error_type, "categorical")

    def test_missing_predicted_fact(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "v", 1.0)])
        actual = _snapshot(facts=[])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, "missing")
        self.assertEqual(errors[0].error_magnitude, ERROR_CLAMP)

    def test_extra_actual_fact(self) -> None:
        predicted = _snapshot(facts=[])
        actual = _snapshot(facts=[_fact("e1", "v", 1.0)])
        errors = compute_fact_errors(predicted, actual)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].error_type, "missing")

    def test_error_bounded(self) -> None:
        predicted = _snapshot(facts=[_fact("e1", "v", 0.0)])
        actual = _snapshot(facts=[_fact("e1", "v", 1000.0)])
        errors = compute_fact_errors(predicted, actual)
        self.assertLessEqual(errors[0].error_magnitude, ERROR_CLAMP)

    def test_empty_snapshots_no_errors(self) -> None:
        errors = compute_fact_errors(_snapshot(), _snapshot())
        self.assertEqual(len(errors), 0)


class TestClassificationErrors(unittest.TestCase):
    def test_matching_classifications_zero_error(self) -> None:
        pred = _understanding(
            assessments=[_assessment("e1", health="good", stability="stable")]
        )
        actual = _understanding(
            assessments=[_assessment("e1", health="good", stability="stable")]
        )
        trend_err, stab_err = compute_classification_errors(pred, actual)
        self.assertEqual(trend_err, 0.0)
        self.assertEqual(stab_err, 0.0)

    def test_health_mismatch(self) -> None:
        pred = _understanding(assessments=[_assessment("e1", health="good")])
        actual = _understanding(assessments=[_assessment("e1", health="bad")])
        trend_err, _ = compute_classification_errors(pred, actual)
        self.assertGreater(trend_err, 0.0)

    def test_stability_mismatch(self) -> None:
        pred = _understanding(assessments=[_assessment("e1", stability="stable")])
        actual = _understanding(assessments=[_assessment("e1", stability="volatile")])
        _, stab_err = compute_classification_errors(pred, actual)
        self.assertGreater(stab_err, 0.0)

    def test_missing_entity_counts_as_error(self) -> None:
        pred = _understanding(assessments=[_assessment("e1"), _assessment("e2")])
        actual = _understanding(assessments=[_assessment("e1")])
        trend_err, stab_err = compute_classification_errors(pred, actual)
        self.assertGreater(trend_err, 0.0)
        self.assertGreater(stab_err, 0.0)

    def test_empty_understandings_zero_error(self) -> None:
        trend_err, stab_err = compute_classification_errors(
            _understanding(), _understanding()
        )
        self.assertEqual(trend_err, 0.0)
        self.assertEqual(stab_err, 0.0)

    def test_errors_bounded(self) -> None:
        pred = _understanding(
            assessments=[_assessment(f"e{i}", health="good") for i in range(10)]
        )
        actual = _understanding(
            assessments=[_assessment(f"e{i}", health="bad") for i in range(10)]
        )
        trend_err, stab_err = compute_classification_errors(pred, actual)
        self.assertLessEqual(trend_err, ERROR_CLAMP)
        self.assertLessEqual(stab_err, ERROR_CLAMP)


# ─── 4. Bounded memory ────────────────────────────────────────


class TestBoundedMemory(unittest.TestCase):
    def test_prediction_buffer_bounded(self) -> None:
        mem = CalibrationMemory(max_records=5)
        for i in range(10):
            mem.record_prediction(
                PredictionRecord(
                    action_id=f"a{i}",
                    predicted_snapshot=_snapshot(),
                    predicted_understanding=_understanding(),
                    horizon=1,
                    timestamp_step=i,
                )
            )
        self.assertEqual(len(mem.predictions), 5)

    def test_outcome_buffer_bounded(self) -> None:
        mem = CalibrationMemory(max_records=5)
        for i in range(10):
            mem.record_outcome(
                OutcomeRecord(
                    action_id=f"a{i}",
                    actual_snapshot=_snapshot(),
                    actual_understanding=_understanding(),
                    timestamp_step=i,
                )
            )
        self.assertEqual(len(mem.outcomes), 5)

    def test_summary_buffer_bounded(self) -> None:
        mem = CalibrationMemory(max_records=5)
        for i in range(MAX_CALIBRATION_SUMMARIES + 10):
            mem.add_summary(
                CalibrationSummary(
                    action_id=f"a{i}",
                    avg_error=0.1,
                    max_error=0.2,
                    stability_error=0.0,
                    trend_error=0.0,
                    confidence_score=0.9,
                    error_count=1,
                    timestamp_step=i,
                )
            )
        self.assertLessEqual(len(mem.summaries), MAX_CALIBRATION_SUMMARIES)

    def test_pending_count(self) -> None:
        mem = CalibrationMemory()
        mem.record_prediction(
            PredictionRecord("a1", _snapshot(), _understanding(), 1, 0)
        )
        mem.record_prediction(
            PredictionRecord("a2", _snapshot(), _understanding(), 1, 0)
        )
        self.assertEqual(mem.pending_count(), 2)
        mem.add_summary(CalibrationSummary("a1", 0.1, 0.2, 0.0, 0.0, 0.9, 1, 1))
        self.assertEqual(mem.pending_count(), 1)

    def test_memory_summary(self) -> None:
        mem = CalibrationMemory()
        s = mem.summary()
        self.assertEqual(s["prediction_count"], 0)
        self.assertEqual(s["outcome_count"], 0)
        self.assertEqual(s["summary_count"], 0)


# ─── 5. Deterministic behavior ────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_errors(self) -> None:
        pred = _snapshot(facts=[_fact("e1", "v", 5.0), _fact("e2", "w", 3.0)])
        actual = _snapshot(facts=[_fact("e1", "v", 5.3), _fact("e2", "w", 2.8)])
        e1 = compute_fact_errors(pred, actual)
        e2 = compute_fact_errors(pred, actual)
        self.assertEqual(len(e1), len(e2))
        for a, b in zip(e1, e2):
            self.assertEqual(a.error_magnitude, b.error_magnitude)

    def test_same_inputs_same_summary(self) -> None:
        errors = [
            CalibrationError("e1", "v", 5.0, 5.3, 0.05, "numeric"),
        ]
        s1 = build_calibration_summary("a1", errors, 0.1, 0.05, 10)
        s2 = build_calibration_summary("a1", errors, 0.1, 0.05, 10)
        self.assertEqual(s1.avg_error, s2.avg_error)
        self.assertEqual(s1.confidence_score, s2.confidence_score)

    def test_same_inputs_same_bias(self) -> None:
        summaries = [
            CalibrationSummary("a1", 0.1, 0.2, 0.05, 0.1, 0.9, 3, 10),
            CalibrationSummary("a2", 0.15, 0.3, 0.08, 0.12, 0.85, 4, 11),
        ]
        b1 = compute_model_bias(summaries)
        b2 = compute_model_bias(summaries)
        self.assertEqual(b1.trend_bias, b2.trend_bias)
        self.assertEqual(b1.risk_propagation_bias, b2.risk_propagation_bias)


# ─── 6. Bias signals ──────────────────────────────────────────


class TestBiasSignals(unittest.TestCase):
    def test_empty_history_zero_bias(self) -> None:
        bias = compute_model_bias([])
        self.assertEqual(bias.trend_bias, 0.0)
        self.assertEqual(bias.risk_propagation_bias, 0.0)
        self.assertEqual(bias.stability_drift_bias, 0.0)
        self.assertEqual(bias.confidence_bias, 0.0)

    def test_high_trend_error_produces_trend_bias(self) -> None:
        summaries = [
            CalibrationSummary("a1", 0.1, 0.2, 0.0, 0.8, 0.9, 3, 10),
            CalibrationSummary("a2", 0.1, 0.2, 0.0, 0.9, 0.9, 3, 11),
        ]
        bias = compute_model_bias(summaries)
        self.assertGreater(bias.trend_bias, 0.3)

    def test_high_stability_error_produces_stability_bias(self) -> None:
        summaries = [
            CalibrationSummary("a1", 0.1, 0.2, 0.7, 0.0, 0.9, 3, 10),
            CalibrationSummary("a2", 0.1, 0.2, 0.8, 0.0, 0.9, 3, 11),
        ]
        bias = compute_model_bias(summaries)
        self.assertGreater(bias.stability_drift_bias, 0.3)

    def test_bias_bounded(self) -> None:
        summaries = [
            CalibrationSummary("a1", 1.0, 1.0, 1.0, 1.0, 1.0, 10, 10),
        ]
        bias = compute_model_bias(summaries)
        self.assertGreaterEqual(bias.trend_bias, -1.0)
        self.assertLessEqual(bias.trend_bias, 1.0)
        self.assertGreaterEqual(bias.confidence_bias, -1.0)
        self.assertLessEqual(bias.confidence_bias, 1.0)

    def test_confidence_bias_direction(self) -> None:
        high_conf = [
            CalibrationSummary("a1", 0.1, 0.2, 0.0, 0.0, 0.95, 3, 10),
        ]
        low_conf = [
            CalibrationSummary("a1", 0.1, 0.2, 0.0, 0.0, 0.2, 3, 10),
        ]
        high_bias = compute_model_bias(high_conf)
        low_bias = compute_model_bias(low_conf)
        self.assertGreater(high_bias.confidence_bias, low_bias.confidence_bias)

    def test_model_bias_to_dict(self) -> None:
        bias = ModelBias(0.1, -0.05, 0.2, 0.15)
        d = bias.to_dict()
        self.assertIn("trend_bias", d)
        self.assertIn("risk_propagation_bias", d)
        self.assertIn("stability_drift_bias", d)
        self.assertIn("confidence_bias", d)


# ─── 7. No mutation of world state ────────────────────────────


class TestNoMutation(unittest.TestCase):
    def test_compute_error_does_not_mutate_snapshots(self) -> None:
        p_snap = _snapshot(facts=[_fact("e1", "v", 5.0)])
        a_snap = _snapshot(facts=[_fact("e1", "v", 5.3)])
        p_und = _understanding(assessments=[_assessment("e1")])
        a_und = _understanding(assessments=[_assessment("e1")])

        original_p_facts = p_snap.state_facts
        original_a_facts = a_snap.state_facts

        engine = WorldCalibrationEngine()
        pred = engine.record_prediction("a1", p_snap, p_und, 1, 10)
        outcome = engine.record_outcome("a1", a_snap, a_und, 11)
        engine.compute_error(pred, outcome)

        self.assertEqual(p_snap.state_facts, original_p_facts)
        self.assertEqual(a_snap.state_facts, original_a_facts)

    def test_match_does_not_mutate_inputs(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot(facts=[_fact("e1", "v", 5.0)])
        a_snap = _snapshot(facts=[_fact("e1", "v", 5.5)])
        p_und = _understanding(assessments=[_assessment("e1")])
        a_und = _understanding(assessments=[_assessment("e1")])

        original_version = p_snap.version
        engine.record_prediction("a1", p_snap, p_und, 1, 0)
        engine.record_outcome("a1", a_snap, a_und, 1)
        engine.match_predictions(1)

        self.assertEqual(p_snap.version, original_version)


# ─── 8. Integration trace fields ──────────────────────────────


class TestTraceIntegration(unittest.TestCase):
    def test_decision_trace_has_calibration_fields(self) -> None:
        from umh.runtime_engine.decision_trace import DecisionTrace

        self.assertTrue(hasattr(DecisionTrace, "calibration_error"))
        self.assertTrue(hasattr(DecisionTrace, "calibration_confidence"))
        self.assertTrue(hasattr(DecisionTrace, "calibration_trend_bias"))
        self.assertTrue(hasattr(DecisionTrace, "calibration_risk_bias"))

    def test_build_trace_accepts_calibration_params(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            calibration_error=0.15,
            calibration_confidence=0.85,
            calibration_trend_bias=0.1,
            calibration_risk_bias=-0.05,
        )
        self.assertAlmostEqual(trace.calibration_error, 0.15)
        self.assertAlmostEqual(trace.calibration_confidence, 0.85)
        self.assertAlmostEqual(trace.calibration_trend_bias, 0.1)
        self.assertAlmostEqual(trace.calibration_risk_bias, -0.05)

    def test_trace_serializes_calibration_fields(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            calibration_error=0.1,
            calibration_confidence=0.9,
            calibration_trend_bias=0.05,
            calibration_risk_bias=-0.02,
        )
        d = trace.to_dict()
        self.assertIn("calibration_error", d)
        self.assertIn("calibration_confidence", d)
        self.assertIn("calibration_trend_bias", d)
        self.assertIn("calibration_risk_bias", d)

    def test_trace_omits_calibration_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        self.assertNotIn("calibration_error", d)
        self.assertNotIn("calibration_confidence", d)

    def test_get_calibration_trace_fields(self) -> None:
        engine = WorldCalibrationEngine()
        fields = engine.get_calibration_trace_fields()
        self.assertIn("calibration_error", fields)
        self.assertIn("calibration_confidence", fields)
        self.assertIn("calibration_trend_bias", fields)
        self.assertIn("calibration_risk_bias", fields)

    def test_trace_fields_after_calibration(self) -> None:
        engine = WorldCalibrationEngine()
        p_snap = _snapshot(facts=[_fact("e1", "v", 5.0)])
        a_snap = _snapshot(facts=[_fact("e1", "v", 5.3)])
        p_und = _understanding(assessments=[_assessment("e1")])
        a_und = _understanding(assessments=[_assessment("e1")])

        engine.record_prediction("a1", p_snap, p_und, 1, 0)
        engine.record_outcome("a1", a_snap, a_und, 1)
        engine.match_predictions(1)

        fields = engine.get_calibration_trace_fields()
        self.assertIsNotNone(fields["calibration_error"])
        self.assertIsNotNone(fields["calibration_confidence"])


# ─── Calibration summary ──────────────────────────────────────


class TestCalibrationSummary(unittest.TestCase):
    def test_summary_from_errors(self) -> None:
        errors = [
            CalibrationError("e1", "v", 5.0, 5.3, 0.058, "numeric"),
            CalibrationError("e1", "w", 3.0, 3.5, 0.143, "numeric"),
        ]
        summary = build_calibration_summary("a1", errors, 0.1, 0.05, 10)
        self.assertEqual(summary.action_id, "a1")
        self.assertGreater(summary.avg_error, 0.0)
        self.assertGreater(summary.max_error, summary.avg_error)
        self.assertEqual(summary.error_count, 2)

    def test_summary_empty_errors(self) -> None:
        summary = build_calibration_summary("a1", [], 0.0, 0.0, 10)
        self.assertEqual(summary.avg_error, 0.0)
        self.assertEqual(summary.max_error, 0.0)
        self.assertEqual(summary.confidence_score, 1.0)
        self.assertEqual(summary.error_count, 0)

    def test_summary_confidence_inversely_related_to_error(self) -> None:
        low_errors = [CalibrationError("e1", "v", 5.0, 5.01, 0.002, "numeric")]
        high_errors = [CalibrationError("e1", "v", 5.0, 6.0, 0.5, "numeric")]
        s_low = build_calibration_summary("a1", low_errors, 0.0, 0.0, 10)
        s_high = build_calibration_summary("a2", high_errors, 0.0, 0.0, 10)
        self.assertGreater(s_low.confidence_score, s_high.confidence_score)

    def test_summary_to_dict(self) -> None:
        summary = CalibrationSummary("a1", 0.1, 0.2, 0.05, 0.1, 0.9, 3, 10)
        d = summary.to_dict()
        self.assertEqual(d["action_id"], "a1")
        self.assertIn("avg_error", d)
        self.assertIn("confidence_score", d)


# ─── Engine end-to-end ─────────────────────────────────────────


class TestEngineEndToEnd(unittest.TestCase):
    def test_full_calibration_cycle(self) -> None:
        engine = WorldCalibrationEngine()

        p_snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            facts=[_fact("e1", "v", 5.0), _fact("e2", "w", 3.0)],
        )
        p_und = _understanding(
            assessments=[
                _assessment("e1", health="good"),
                _assessment("e2", health="watch"),
            ]
        )
        engine.record_prediction("a1", p_snap, p_und, horizon=3, timestamp_step=0)

        a_snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            facts=[_fact("e1", "v", 5.2), _fact("e2", "w", 2.8)],
        )
        a_und = _understanding(
            assessments=[
                _assessment("e1", health="good"),
                _assessment("e2", health="bad"),
            ]
        )
        engine.record_outcome("a1", a_snap, a_und, timestamp_step=3)

        summaries = engine.match_predictions(current_step=3)
        self.assertEqual(len(summaries), 1)

        bias = engine.get_model_bias()
        self.assertIsInstance(bias, ModelBias)

        latest = engine.get_latest_summary()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.action_id, "a1")


# ─── No regression ──────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_world_substrate_imports(self) -> None:
        from umh.world.substrate import WorldSubstrate

        self.assertIsNotNone(WorldSubstrate())

    def test_world_reasoning_imports(self) -> None:
        from umh.world.reasoning import WorldReasoningEngine

        self.assertIsNotNone(WorldReasoningEngine())

    def test_world_simulation_imports(self) -> None:
        from umh.world.simulation import WorldSimulationEngine

        self.assertIsNotNone(WorldSimulationEngine())

    def test_world_calibration_imports(self) -> None:
        from umh.world.calibration import WorldCalibrationEngine

        self.assertIsNotNone(WorldCalibrationEngine())

    def test_signal_ingestion_imports(self) -> None:
        from umh.runtime_engine.signal_ingestion import SignalIngestionEngine

        self.assertIsNotNone(SignalIngestionEngine())


if __name__ == "__main__":
    unittest.main()
