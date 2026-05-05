"""Phase 22 — Adaptive Prediction Weighting + Threshold System v1.

Tests cover:
  - PredictionWeight (creation, success_rate, serialization)
  - WeightStore (get, update, bounding, determinism, learning_rate)
  - ConfidenceCalibrator (adjustment, success_rate correction, clamping)
  - ThresholdAdapter (adapt up, adapt down, clamping, step size)
  - Predictor integration (weights affect confidence)
  - Advisor integration (weights updated per tick, threshold adapts)
  - Loop integration (adaptation flows through ticks)
  - Safety controls (bounded weights, bounded threshold, max_delta)
  - Boundary invariants (no cells/environments/subprocess imports)
  - Determinism (same sequence → same results)
  - Regression (prior phase tests unaffected)

Hard invariants:
  45. Adaptation based ONLY on observed outcomes
  46. No retroactive mutation of prediction history
  47. Weight updates are deterministic
  48. Adaptation is bounded (no runaway amplification)
  49. System remains stable under poor accuracy
"""

from __future__ import annotations

import ast
import os
from datetime import datetime, timezone
from typing import Any

import pytest

from umh.learning.feedback import ExecutionFeedback, FeedbackStore
from umh.prediction.calibrator import (
    CalibrationResult,
    ConfidenceCalibrator,
    ThresholdAdapter,
)
from umh.prediction.evaluator import PredictionEvaluator
from umh.prediction.intent import UserIntent, make_intent_id
from umh.prediction.metrics import PredictionMetrics
from umh.prediction.predictor import PredictionContext, Predictor
from umh.prediction.store import (
    PredictionRecord,
    PredictionStatus,
    PredictionStore,
    record_from_intent,
)
from umh.prediction.weights import PredictionWeight, WeightStore


# ── helpers ──────────────────────────────────────────────────────────


def _make_intent(
    goal: str = "repeat_outreach",
    confidence: float = 0.8,
    actions: tuple[str, ...] = ("submit_outreach",),
    entities: tuple[str, ...] = ("outreach",),
    source: str = "repeated_workflow",
) -> UserIntent:
    return UserIntent(
        intent_id=make_intent_id(),
        inferred_goal=goal,
        confidence=confidence,
        predicted_actions=actions,
        related_entities=entities,
        source=source,
        timestamp="2026-04-30T09:00:00Z",
    )


def _make_feedback(
    task_type: str = "outreach",
    job_id: str = "",
    success: bool = True,
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id or f"job_{task_type}",
        node_id="node-1",
        task_type=task_type,
        success=success,
        duration_ms=500,
        timestamp="2026-04-30T09:00:00+00:00",
    )


def _ref_time(hour: int = 9) -> datetime:
    return datetime(2026, 4, 30, hour, 0, 0, tzinfo=timezone.utc)


# ── PREDICTION WEIGHT ────────────────────────────────────────────────


class TestPredictionWeight:
    def test_creation(self) -> None:
        pw = PredictionWeight(pattern_key="outreach")
        assert pw.pattern_key == "outreach"
        assert pw.weight == 1.0
        assert pw.total_predictions == 0

    def test_success_rate_no_data(self) -> None:
        pw = PredictionWeight(pattern_key="x")
        assert pw.success_rate == 0.5

    def test_success_rate_with_data(self) -> None:
        pw = PredictionWeight(
            pattern_key="x", success_count=7, failure_count=3
        )
        assert pw.success_rate == 0.7

    def test_serialization(self) -> None:
        pw = PredictionWeight(
            pattern_key="outreach",
            weight=1.5,
            success_count=10,
            failure_count=5,
        )
        d = pw.to_dict()
        assert d["pattern_key"] == "outreach"
        assert d["weight"] == 1.5
        assert d["total_predictions"] == 15
        assert d["success_rate"] == round(10 / 15, 4)


# ── WEIGHT STORE ─────────────────────────────────────────────────────


class TestWeightStore:
    def test_get_creates_default(self) -> None:
        store = WeightStore()
        pw = store.get_weight("new_pattern")
        assert pw.weight == 1.0
        assert pw.total_predictions == 0

    def test_get_weight_value(self) -> None:
        store = WeightStore()
        assert store.get_weight_value("unknown") == 1.0

    def test_update_on_match_increases(self) -> None:
        store = WeightStore()
        store.update_weight("p", matched=True)
        store.update_weight("p", matched=True)
        new_weight = store.update_weight("p", matched=True)
        assert new_weight > 1.0

    def test_update_on_miss_decreases(self) -> None:
        store = WeightStore()
        store.update_weight("p", matched=False)
        store.update_weight("p", matched=False)
        new_weight = store.update_weight("p", matched=False)
        assert new_weight < 1.0

    def test_weight_bounded_above(self) -> None:
        store = WeightStore(learning_rate=1.0, max_delta=10.0)
        for _ in range(100):
            store.update_weight("p", matched=True)
        assert store.get_weight_value("p") <= 3.0

    def test_weight_bounded_below(self) -> None:
        store = WeightStore(learning_rate=1.0, max_delta=10.0)
        for _ in range(100):
            store.update_weight("p", matched=False)
        assert store.get_weight_value("p") >= 0.1

    def test_no_update_below_min_samples(self) -> None:
        store = WeightStore()
        w1 = store.update_weight("p", matched=True)
        assert w1 == 1.0

    def test_delta_clamped(self) -> None:
        store = WeightStore(max_delta=0.1, learning_rate=1.0)
        store.update_weight("p", matched=True)
        w_before = store.get_weight_value("p")
        store.update_weight("p", matched=True)
        w_after = store.get_weight_value("p")
        assert abs(w_after - w_before) <= 0.1 + 1e-9

    def test_determinism(self) -> None:
        s1 = WeightStore()
        s2 = WeightStore()
        for matched in [True, True, False, True, False]:
            s1.update_weight("p", matched=matched)
            s2.update_weight("p", matched=matched)
        assert s1.get_weight_value("p") == s2.get_weight_value("p")

    def test_learning_rate_validation(self) -> None:
        with pytest.raises(ValueError):
            WeightStore(learning_rate=0.0)
        with pytest.raises(ValueError):
            WeightStore(learning_rate=-0.1)

    def test_list_weights(self) -> None:
        store = WeightStore()
        store.get_weight("a")
        store.get_weight("b")
        assert len(store.list_weights()) == 2

    def test_get_state(self) -> None:
        store = WeightStore()
        store.get_weight("test")
        state = store.get_state()
        assert state["patterns"] == 1
        assert "weights" in state

    def test_clear(self) -> None:
        store = WeightStore()
        store.get_weight("a")
        store.clear()
        assert len(store.list_weights()) == 0

    def test_multiple_patterns_independent(self) -> None:
        store = WeightStore()
        for _ in range(5):
            store.update_weight("good", matched=True)
        for _ in range(5):
            store.update_weight("bad", matched=False)
        assert store.get_weight_value("good") > 1.0
        assert store.get_weight_value("bad") < 1.0


# ── CONFIDENCE CALIBRATOR ────────────────────────────────────────────


class TestConfidenceCalibrator:
    def test_no_history_returns_weighted(self) -> None:
        ws = WeightStore()
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.8, "test")
        assert result.calibrated_confidence == pytest.approx(0.8, abs=0.01)

    def test_high_weight_increases_confidence(self) -> None:
        ws = WeightStore()
        ws.get_weight("good").weight = 2.0
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.5, "good")
        assert result.calibrated_confidence > 0.5

    def test_low_weight_decreases_confidence(self) -> None:
        ws = WeightStore()
        ws.get_weight("bad").weight = 0.3
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.8, "bad")
        assert result.calibrated_confidence < 0.8

    def test_clamped_minimum(self) -> None:
        ws = WeightStore()
        ws.get_weight("terrible").weight = 0.1
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.01, "terrible")
        assert result.calibrated_confidence >= 0.01

    def test_clamped_maximum(self) -> None:
        ws = WeightStore()
        ws.get_weight("great").weight = 3.0
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.95, "great")
        assert result.calibrated_confidence <= 0.99

    def test_success_rate_correction(self) -> None:
        ws = WeightStore()
        pw = ws.get_weight("overconfident")
        pw.success_count = 2
        pw.failure_count = 8
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.9, "overconfident")
        assert result.calibrated_confidence < 0.9

    def test_serialization(self) -> None:
        result = CalibrationResult(
            raw_confidence=0.8,
            pattern_weight=1.5,
            calibrated_confidence=0.75,
            pattern_key="test",
            adjustments_applied=("weight_1.500",),
        )
        d = result.to_dict()
        assert d["raw_confidence"] == 0.8
        assert d["pattern_key"] == "test"


# ── THRESHOLD ADAPTER ────────────────────────────────────────────────


class TestThresholdAdapter:
    def test_default_threshold(self) -> None:
        ta = ThresholdAdapter()
        assert ta.threshold == 0.6

    def test_low_accuracy_raises_threshold(self) -> None:
        ta = ThresholdAdapter()
        before = ta.threshold
        ta.adapt(0.1)
        assert ta.threshold > before

    def test_high_accuracy_lowers_threshold(self) -> None:
        ta = ThresholdAdapter()
        before = ta.threshold
        ta.adapt(0.9)
        assert ta.threshold < before

    def test_mid_accuracy_no_change(self) -> None:
        ta = ThresholdAdapter()
        before = ta.threshold
        ta.adapt(0.5)
        assert ta.threshold == before

    def test_threshold_bounded_above(self) -> None:
        ta = ThresholdAdapter()
        for _ in range(100):
            ta.adapt(0.0)
        assert ta.threshold <= 0.9

    def test_threshold_bounded_below(self) -> None:
        ta = ThresholdAdapter()
        for _ in range(100):
            ta.adapt(1.0)
        assert ta.threshold >= 0.4

    def test_step_size_respected(self) -> None:
        ta = ThresholdAdapter(step=0.05)
        before = ta.threshold
        ta.adapt(0.0)
        assert abs(ta.threshold - before) <= 0.05 + 1e-9

    def test_update_count(self) -> None:
        ta = ThresholdAdapter()
        assert ta.update_count == 0
        ta.adapt(0.5)
        ta.adapt(0.5)
        assert ta.update_count == 2

    def test_get_state(self) -> None:
        ta = ThresholdAdapter()
        state = ta.get_state()
        assert state["threshold"] == 0.6
        assert state["update_count"] == 0

    def test_reset(self) -> None:
        ta = ThresholdAdapter()
        ta.adapt(0.0)
        ta.adapt(0.0)
        ta.reset()
        assert ta.threshold == 0.6
        assert ta.update_count == 0

    def test_initial_threshold_clamped(self) -> None:
        ta = ThresholdAdapter(initial_threshold=0.0)
        assert ta.threshold >= 0.4
        ta2 = ThresholdAdapter(initial_threshold=1.0)
        assert ta2.threshold <= 0.9


# ── INTEGRATION: CALIBRATOR + PREDICTOR ──────────────────────────────


class TestCalibratorPredictorIntegration:
    def test_calibrator_reduces_overconfident_pattern(self) -> None:
        ws = WeightStore()
        pw = ws.get_weight("repeated_workflow")
        pw.weight = 0.5
        pw.success_count = 1
        pw.failure_count = 4

        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.8, "repeated_workflow")
        assert result.calibrated_confidence < 0.8

    def test_calibrator_boosts_underconfident_pattern(self) -> None:
        ws = WeightStore()
        pw = ws.get_weight("repeated_workflow")
        pw.weight = 2.0

        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.4, "repeated_workflow")
        assert result.calibrated_confidence > 0.4

    def test_weight_store_evolves_with_outcomes(self) -> None:
        ws = WeightStore()
        for _ in range(10):
            ws.update_weight("reliable", matched=True)
        for _ in range(10):
            ws.update_weight("unreliable", matched=False)

        assert ws.get_weight_value("reliable") > 1.0
        assert ws.get_weight_value("unreliable") < 1.0


# ── ADVISOR INTEGRATION ──────────────────────────────────────────────


class TestAdvisorAdaptivePrediction:
    def _build_advisor(self, **kwargs: Any) -> Any:
        from umh.prediction.planner import PredictivePlanner
        from umh.runtime.advisor import AdvisorRuntime

        ws = kwargs.get("weight_store", WeightStore())
        return AdvisorRuntime(
            predictor=Predictor(),
            predictive_planner=PredictivePlanner(),
            prediction_store=kwargs.get("prediction_store", PredictionStore()),
            prediction_evaluator=PredictionEvaluator(),
            prediction_metrics=PredictionMetrics(),
            weight_store=ws,
            confidence_calibrator=ConfidenceCalibrator(ws),
            threshold_adapter=kwargs.get("threshold_adapter", ThresholdAdapter()),
        )

    def _make_context(self, n: int = 5) -> PredictionContext:
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(n)
        )
        return PredictionContext(recent_feedback=feedbacks, current_hour=9)

    def test_weights_updated_on_tick(self) -> None:
        advisor = self._build_advisor()
        advisor.start()

        ctx = self._make_context()
        advisor.tick(prediction_context=ctx)

        completed = [_make_feedback(task_type="outreach", job_id="cj1")]
        result = advisor.tick(completed_feedback=completed)
        assert result["weights_updated"] >= 1
        advisor.stop()

    def test_threshold_adapts_on_tick(self) -> None:
        store = PredictionStore()
        advisor = self._build_advisor(prediction_store=store)
        advisor.start()

        ctx = self._make_context()
        advisor.tick(prediction_context=ctx)

        for i in range(5):
            completed = [_make_feedback(task_type="outreach", job_id=f"c{i}")]
            advisor.tick(completed_feedback=completed)

        assert advisor.threshold_adapter is not None
        assert advisor.threshold_adapter.update_count >= 1
        advisor.stop()

    def test_state_includes_weights_and_threshold(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        state = advisor.get_state()
        assert "prediction_threshold" in state
        assert "prediction_weight_patterns" in state
        advisor.stop()

    def test_advisor_without_adaptation_unchanged(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["weights_updated"] == 0
        assert result["threshold_adapted"] is False
        advisor.stop()

    def test_clear_predictions_resets_weights(self) -> None:
        advisor = self._build_advisor()
        advisor.start()
        ctx = self._make_context()
        advisor.tick(prediction_context=ctx)
        advisor.clear_predictions()
        assert advisor.weight_store is not None
        assert len(advisor.weight_store.list_weights()) == 0
        assert advisor.threshold_adapter is not None
        assert advisor.threshold_adapter.threshold == 0.6
        advisor.stop()


# ── LOOP INTEGRATION ─────────────────────────────────────────────────


class TestLoopAdaptivePrediction:
    def test_loop_adaptation_flows_through(self) -> None:
        from umh.prediction.planner import PredictivePlanner
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        ws = WeightStore()
        advisor = AdvisorRuntime(
            predictor=Predictor(),
            predictive_planner=PredictivePlanner(),
            prediction_store=PredictionStore(),
            prediction_evaluator=PredictionEvaluator(),
            prediction_metrics=PredictionMetrics(),
            weight_store=ws,
            confidence_calibrator=ConfidenceCalibrator(ws),
            threshold_adapter=ThresholdAdapter(),
        )
        loop = RuntimeLoop(advisor=advisor)
        loop.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        loop.tick(prediction_context=ctx)

        completed = [_make_feedback(task_type="outreach", job_id="done")]
        result = loop.tick(completed_feedback=completed)
        assert result["weights_updated"] >= 1

        loop.stop()


# ── SAFETY CONTROLS ──────────────────────────────────────────────────


class TestSafetyControls:
    def test_weight_never_exceeds_bounds(self) -> None:
        store = WeightStore(learning_rate=0.5, max_delta=1.0)
        for _ in range(200):
            store.update_weight("p", matched=True)
        w = store.get_weight_value("p")
        assert 0.1 <= w <= 3.0

    def test_weight_never_below_bounds(self) -> None:
        store = WeightStore(learning_rate=0.5, max_delta=1.0)
        for _ in range(200):
            store.update_weight("p", matched=False)
        w = store.get_weight_value("p")
        assert 0.1 <= w <= 3.0

    def test_threshold_never_exceeds_bounds(self) -> None:
        ta = ThresholdAdapter(step=0.1)
        for _ in range(100):
            ta.adapt(0.0)
        assert 0.4 <= ta.threshold <= 0.9

    def test_threshold_never_below_bounds(self) -> None:
        ta = ThresholdAdapter(step=0.1)
        for _ in range(100):
            ta.adapt(1.0)
        assert 0.4 <= ta.threshold <= 0.9

    def test_system_stable_under_all_misses(self) -> None:
        ws = WeightStore()
        for _ in range(100):
            ws.update_weight("bad", matched=False)
        w = ws.get_weight_value("bad")
        assert w >= 0.1
        assert w == pytest.approx(0.1, abs=0.01)

    def test_system_stable_under_all_matches(self) -> None:
        ws = WeightStore()
        for _ in range(100):
            ws.update_weight("perfect", matched=True)
        w = ws.get_weight_value("perfect")
        assert w <= 3.0

    def test_no_division_by_zero_in_calibrator(self) -> None:
        ws = WeightStore()
        cal = ConfidenceCalibrator(ws)
        result = cal.adjust_confidence(0.0, "empty")
        assert result.calibrated_confidence >= 0.01

    def test_alternating_outcomes_converge(self) -> None:
        ws = WeightStore()
        for i in range(100):
            ws.update_weight("oscillate", matched=(i % 2 == 0))
        w = ws.get_weight_value("oscillate")
        assert 0.5 <= w <= 2.0


# ── DETERMINISM ──────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_sequence_same_weights(self) -> None:
        s1 = WeightStore()
        s2 = WeightStore()
        seq = [True, True, False, True, False, False, True]
        for m in seq:
            s1.update_weight("p", matched=m)
            s2.update_weight("p", matched=m)
        assert s1.get_weight_value("p") == s2.get_weight_value("p")

    def test_same_accuracy_same_threshold(self) -> None:
        t1 = ThresholdAdapter()
        t2 = ThresholdAdapter()
        for acc in [0.1, 0.5, 0.9, 0.2, 0.8]:
            t1.adapt(acc)
            t2.adapt(acc)
        assert t1.threshold == t2.threshold

    def test_same_inputs_same_calibration(self) -> None:
        ws = WeightStore()
        ws.get_weight("p").weight = 1.5
        cal = ConfidenceCalibrator(ws)
        r1 = cal.adjust_confidence(0.7, "p")
        r2 = cal.adjust_confidence(0.7, "p")
        assert r1.calibrated_confidence == r2.calibrated_confidence


# ── INVARIANT ENFORCEMENT ────────────────────────────────────────────


class TestInvariants:
    def test_inv45_adaptation_from_outcomes_only(self) -> None:
        """Inv 45: weights change only via update_weight(matched=...)."""
        ws = WeightStore()
        initial = ws.get_weight_value("p")
        ws.update_weight("p", matched=True)
        ws.update_weight("p", matched=True)
        after = ws.update_weight("p", matched=True)
        assert after != initial

    def test_inv46_no_retroactive_mutation(self) -> None:
        """Inv 46: updating weights does not change prediction records."""
        store = PredictionStore()
        intent = _make_intent()
        rec = record_from_intent(intent)
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        original_goal = rec.inferred_goal
        original_confidence = rec.confidence

        ws = WeightStore()
        ws.update_weight(rec.source, matched=True)
        ws.update_weight(rec.source, matched=True)
        ws.update_weight(rec.source, matched=True)

        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.inferred_goal == original_goal
        assert found.confidence == original_confidence

    def test_inv47_weight_updates_deterministic(self) -> None:
        """Inv 47: same sequence → same weights."""
        s1 = WeightStore()
        s2 = WeightStore()
        for m in [True, False, True, True, False]:
            s1.update_weight("x", matched=m)
            s2.update_weight("x", matched=m)
        assert s1.get_weight_value("x") == s2.get_weight_value("x")

    def test_inv48_bounded_adaptation(self) -> None:
        """Inv 48: no runaway amplification."""
        ws = WeightStore(learning_rate=0.5, max_delta=1.0)
        for _ in range(1000):
            ws.update_weight("p", matched=True)
        assert ws.get_weight_value("p") <= 3.0

        ta = ThresholdAdapter(step=0.1)
        for _ in range(1000):
            ta.adapt(0.0)
        assert ta.threshold <= 0.9

    def test_inv49_stable_under_poor_accuracy(self) -> None:
        """Inv 49: system doesn't crash or diverge with 0% accuracy."""
        ws = WeightStore()
        ta = ThresholdAdapter()
        for _ in range(50):
            ws.update_weight("bad", matched=False)
            ta.adapt(0.0)
        w = ws.get_weight_value("bad")
        assert 0.1 <= w <= 3.0
        assert 0.4 <= ta.threshold <= 0.9


# ── BOUNDARY INVARIANTS ──────────────────────────────────────────────

_PHASE22_FILES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "weights.py"),
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "calibrator.py"),
]


class TestBoundaryInvariants:
    @pytest.mark.parametrize("filepath", _PHASE22_FILES)
    def test_no_cells_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                assert "umh.cells" not in mod, f"cells import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE22_FILES)
    def test_no_environments_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                assert "umh.environments" not in mod, f"environments import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE22_FILES)
    def test_no_subprocess_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names] if hasattr(node, "names") else []
                full = mod + " ".join(names)
                assert "subprocess" not in full, f"subprocess import in {filepath}"

    @pytest.mark.parametrize("filepath", _PHASE22_FILES)
    def test_no_shell_true(self, filepath: str) -> None:
        source = open(filepath).read()
        assert "shell=True" not in source, f"shell=True in {filepath}"


# ── REGRESSION ───────────────────────────────────────────────────────


class TestRegression:
    def test_phase21_store_unchanged(self) -> None:
        store = PredictionStore()
        rec = record_from_intent(_make_intent())
        store.append(rec)
        store.mark_matched(rec.prediction_id)
        found = store.get(rec.prediction_id)
        assert found is not None
        assert found.status == PredictionStatus.MATCHED

    def test_phase20_predictor_unchanged(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        intents = p.predict_intent(ctx, now=_ref_time())
        assert len(intents) >= 1

    def test_phase19_feedback_unchanged(self) -> None:
        store = FeedbackStore()
        fb = _make_feedback()
        store.record(fb)
        assert store.total == 1

    def test_advisor_backward_compat(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert "weights_updated" in result
        assert "threshold_adapted" in result
        assert result["weights_updated"] == 0
        assert result["threshold_adapted"] is False
        advisor.stop()
