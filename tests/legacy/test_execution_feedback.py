"""Tests for runtime.execution_feedback — execution feedback normalization layer.

Validates: outcome mapping, signal strength computation, feedback_signals dict,
observation text format, combined normalization, round-trip serialization,
edge cases, and integration with DecisionTrace + SessionInterface.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from types import SimpleNamespace

from umh.runtime_engine.execution_feedback import (
    NEGATIVE_OUTCOMES,
    NEUTRAL_OUTCOMES,
    OUTCOME_MAP,
    POSITIVE_OUTCOMES,
    ExecutionFeedback,
    FeedbackNormalizationResult,
    FeedbackObservation,
    _build_feedback_signals,
    _compute_signal_strength,
    execution_to_feedback,
    feedback_to_observation,
    normalize_execution_feedback,
)


def _make_exec_result(
    action_id: str = "abc123",
    action_name: str = "test_action",
    handler_name: str | None = "log",
    status: str = "success",
    output: dict | None = None,
    error: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        action_id=action_id,
        action_name=action_name,
        handler_name=handler_name,
        status=status,
        output=output or {},
        error=error,
    )


# ─── Outcome mapping ─────────────────────────────────────────────


class TestOutcomeMapping(unittest.TestCase):
    def test_success_maps_to_success(self) -> None:
        self.assertEqual(OUTCOME_MAP["success"], "success")

    def test_failed_maps_to_failure(self) -> None:
        self.assertEqual(OUTCOME_MAP["failed"], "failure")

    def test_skipped_maps_to_partial(self) -> None:
        self.assertEqual(OUTCOME_MAP["skipped"], "partial")

    def test_unhandled_maps_to_unknown(self) -> None:
        self.assertEqual(OUTCOME_MAP["unhandled"], "unknown")

    def test_all_four_statuses_mapped(self) -> None:
        self.assertEqual(len(OUTCOME_MAP), 4)

    def test_outcome_sets_are_disjoint(self) -> None:
        self.assertEqual(len(POSITIVE_OUTCOMES & NEGATIVE_OUTCOMES), 0)
        self.assertEqual(len(POSITIVE_OUTCOMES & NEUTRAL_OUTCOMES), 0)
        self.assertEqual(len(NEGATIVE_OUTCOMES & NEUTRAL_OUTCOMES), 0)

    def test_all_outcomes_classified(self) -> None:
        all_outcomes = POSITIVE_OUTCOMES | NEGATIVE_OUTCOMES | NEUTRAL_OUTCOMES
        for outcome in OUTCOME_MAP.values():
            self.assertIn(outcome, all_outcomes)


# ─── Signal strength ─────────────────────────────────────────────


class TestSignalStrength(unittest.TestCase):
    def test_success_positive_signal(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("success", 0.8), 0.8)

    def test_failure_negative_signal(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("failure", 0.8), -0.8)

    def test_partial_zero_signal(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("partial", 0.8), 0.0)

    def test_unknown_zero_signal(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("unknown", 0.9), 0.0)

    def test_success_full_confidence(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("success", 1.0), 1.0)

    def test_failure_full_confidence(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("failure", 1.0), -1.0)

    def test_success_zero_confidence(self) -> None:
        self.assertAlmostEqual(_compute_signal_strength("success", 0.0), 0.0)

    def test_clamped_above_one(self) -> None:
        result = _compute_signal_strength("success", 1.5)
        self.assertLessEqual(result, 1.0)

    def test_clamped_below_neg_one(self) -> None:
        result = _compute_signal_strength("failure", 1.5)
        self.assertGreaterEqual(result, -1.0)


# ─── Feedback signals dict ───────────────────────────────────────


class TestFeedbackSignals(unittest.TestCase):
    def test_success_signals(self) -> None:
        signals = _build_feedback_signals("success", 0.8, 0.8, "log", None)
        self.assertEqual(signals["execution_success"], 1)
        self.assertEqual(signals["execution_failure"], 0)
        self.assertEqual(signals["execution_partial"], 0)
        self.assertEqual(signals["execution_unknown"], 0)
        self.assertAlmostEqual(signals["execution_confidence"], 0.8)
        self.assertAlmostEqual(signals["execution_signal_strength"], 0.8)
        self.assertTrue(signals["execution_handler_present"])
        self.assertFalse(signals["execution_error_present"])

    def test_failure_signals(self) -> None:
        signals = _build_feedback_signals("failure", -0.7, 0.7, None, "boom")
        self.assertEqual(signals["execution_success"], 0)
        self.assertEqual(signals["execution_failure"], 1)
        self.assertFalse(signals["execution_handler_present"])
        self.assertTrue(signals["execution_error_present"])

    def test_all_eight_keys_present(self) -> None:
        signals = _build_feedback_signals("unknown", 0.0, 0.5, None, None)
        expected_keys = {
            "execution_success",
            "execution_failure",
            "execution_partial",
            "execution_unknown",
            "execution_confidence",
            "execution_signal_strength",
            "execution_handler_present",
            "execution_error_present",
        }
        self.assertEqual(set(signals.keys()), expected_keys)


# ─── execution_to_feedback ───────────────────────────────────────


class TestExecutionToFeedback(unittest.TestCase):
    def test_success_result(self) -> None:
        er = _make_exec_result(status="success")
        fb = execution_to_feedback(er, confidence=0.9)
        self.assertEqual(fb.outcome_type, "success")
        self.assertAlmostEqual(fb.signal_strength, 0.9)
        self.assertEqual(fb.action_id, "abc123")
        self.assertEqual(fb.action_name, "test_action")
        self.assertEqual(fb.handler_name, "log")
        self.assertIsNone(fb.error)
        self.assertEqual(len(fb.warnings), 0)

    def test_failed_result(self) -> None:
        er = _make_exec_result(status="failed", error="timeout")
        fb = execution_to_feedback(er, confidence=0.6)
        self.assertEqual(fb.outcome_type, "failure")
        self.assertAlmostEqual(fb.signal_strength, -0.6)
        self.assertEqual(fb.error, "timeout")

    def test_skipped_result(self) -> None:
        er = _make_exec_result(status="skipped")
        fb = execution_to_feedback(er, confidence=0.8)
        self.assertEqual(fb.outcome_type, "partial")
        self.assertAlmostEqual(fb.signal_strength, 0.0)

    def test_unhandled_result(self) -> None:
        er = _make_exec_result(status="unhandled", handler_name=None)
        fb = execution_to_feedback(er, confidence=0.7)
        self.assertEqual(fb.outcome_type, "unknown")
        self.assertAlmostEqual(fb.signal_strength, 0.0)
        self.assertIsNone(fb.handler_name)

    def test_unknown_status_produces_warning(self) -> None:
        er = _make_exec_result(status="weird_status")
        fb = execution_to_feedback(er, confidence=0.5)
        self.assertEqual(fb.outcome_type, "unknown")
        self.assertEqual(len(fb.warnings), 1)
        self.assertIn("weird_status", fb.warnings[0])

    def test_default_confidence(self) -> None:
        er = _make_exec_result(status="success")
        fb = execution_to_feedback(er)
        self.assertAlmostEqual(fb.signal_strength, 0.5)

    def test_confidence_clamped_high(self) -> None:
        er = _make_exec_result(status="success")
        fb = execution_to_feedback(er, confidence=2.0)
        self.assertLessEqual(fb.signal_strength, 1.0)

    def test_confidence_clamped_low(self) -> None:
        er = _make_exec_result(status="success")
        fb = execution_to_feedback(er, confidence=-0.5)
        self.assertGreaterEqual(fb.signal_strength, 0.0)

    def test_zero_confidence_handled(self) -> None:
        er = _make_exec_result(status="failed")
        fb = execution_to_feedback(er, confidence=0.0)
        self.assertAlmostEqual(fb.signal_strength, 0.0)

    def test_feedback_is_frozen(self) -> None:
        er = _make_exec_result()
        fb = execution_to_feedback(er)
        with self.assertRaises(AttributeError):
            fb.outcome_type = "changed"


# ─── feedback_to_observation ─────────────────────────────────────


class TestFeedbackToObservation(unittest.TestCase):
    def test_observation_text_format(self) -> None:
        er = _make_exec_result(action_id="x1", status="success")
        fb = execution_to_feedback(er, confidence=0.8)
        obs = feedback_to_observation(fb)
        self.assertIn("action=x1", obs.text)
        self.assertIn("outcome=success", obs.text)
        self.assertIn("execution_success=1", obs.text)
        self.assertIn("execution_signal_strength=0.8", obs.text)
        self.assertTrue(obs.text.startswith("execution"))

    def test_observation_source(self) -> None:
        er = _make_exec_result()
        fb = execution_to_feedback(er)
        obs = feedback_to_observation(fb)
        self.assertEqual(obs.source, "execution_feedback")

    def test_observation_carries_ids(self) -> None:
        er = _make_exec_result(action_id="abc")
        fb = execution_to_feedback(er)
        obs = feedback_to_observation(fb)
        self.assertEqual(obs.action_id, "abc")
        self.assertEqual(obs.outcome_type, "success")

    def test_failed_observation_text(self) -> None:
        er = _make_exec_result(action_id="f1", status="failed")
        fb = execution_to_feedback(er, confidence=0.7)
        obs = feedback_to_observation(fb)
        self.assertIn("outcome=failure", obs.text)
        self.assertIn("execution_success=0", obs.text)

    def test_observation_is_frozen(self) -> None:
        er = _make_exec_result()
        fb = execution_to_feedback(er)
        obs = feedback_to_observation(fb)
        with self.assertRaises(AttributeError):
            obs.text = "changed"


# ─── normalize_execution_feedback ────────────────────────────────


class TestNormalizeExecutionFeedback(unittest.TestCase):
    def test_combined_success(self) -> None:
        er = _make_exec_result(status="success", action_id="n1")
        result = normalize_execution_feedback(er, confidence=0.9)
        self.assertEqual(result.feedback.outcome_type, "success")
        self.assertAlmostEqual(result.feedback.signal_strength, 0.9)
        self.assertIn("action=n1", result.observation.text)
        self.assertIn("outcome=success", result.observation.text)

    def test_combined_preserves_warnings(self) -> None:
        er = _make_exec_result(status="bogus")
        result = normalize_execution_feedback(er)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("bogus", result.warnings[0])

    def test_combined_no_warnings_on_clean(self) -> None:
        er = _make_exec_result(status="success")
        result = normalize_execution_feedback(er)
        self.assertEqual(len(result.warnings), 0)


# ─── Round-trip serialization ────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_feedback_round_trip(self) -> None:
        er = _make_exec_result(status="failed", error="boom")
        fb = execution_to_feedback(er, confidence=0.6)
        d = fb.to_dict()
        restored = ExecutionFeedback.from_dict(d)
        self.assertEqual(restored.action_id, fb.action_id)
        self.assertEqual(restored.outcome_type, fb.outcome_type)
        self.assertAlmostEqual(restored.signal_strength, fb.signal_strength, places=4)
        self.assertEqual(restored.error, fb.error)

    def test_observation_round_trip(self) -> None:
        er = _make_exec_result()
        fb = execution_to_feedback(er)
        obs = feedback_to_observation(fb)
        d = obs.to_dict()
        restored = FeedbackObservation.from_dict(d)
        self.assertEqual(restored.text, obs.text)
        self.assertEqual(restored.source, obs.source)
        self.assertEqual(restored.action_id, obs.action_id)

    def test_normalization_result_round_trip(self) -> None:
        er = _make_exec_result(status="skipped")
        result = normalize_execution_feedback(er, confidence=0.4)
        d = result.to_dict()
        restored = FeedbackNormalizationResult.from_dict(d)
        self.assertEqual(restored.feedback.outcome_type, "partial")
        self.assertEqual(restored.observation.outcome_type, "partial")


# ─── DecisionTrace integration ───────────────────────────────────


class TestDecisionTraceIntegration(unittest.TestCase):
    def test_feedback_fields_on_trace(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            feedback_outcome_type="success",
            feedback_signal_strength=0.85,
            feedback_action_id="fb_act_1",
            feedback_ingested=True,
            feedback_warnings=("minor warning",),
        )
        self.assertEqual(trace.feedback_outcome_type, "success")
        self.assertAlmostEqual(trace.feedback_signal_strength, 0.85)
        self.assertEqual(trace.feedback_action_id, "fb_act_1")
        self.assertTrue(trace.feedback_ingested)
        self.assertEqual(trace.feedback_warnings, ("minor warning",))

    def test_feedback_fields_default_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=2)
        self.assertIsNone(trace.feedback_outcome_type)
        self.assertIsNone(trace.feedback_signal_strength)
        self.assertIsNone(trace.feedback_action_id)
        self.assertIsNone(trace.feedback_ingested)
        self.assertIsNone(trace.feedback_warnings)

    def test_feedback_fields_in_to_dict(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=3,
            feedback_outcome_type="failure",
            feedback_signal_strength=-0.6,
            feedback_action_id="fb_act_2",
            feedback_ingested=False,
            feedback_warnings=("w1", "w2"),
        )
        d = trace.to_dict()
        self.assertEqual(d["feedback_outcome_type"], "failure")
        self.assertAlmostEqual(d["feedback_signal_strength"], -0.6, places=4)
        self.assertEqual(d["feedback_action_id"], "fb_act_2")
        self.assertFalse(d["feedback_ingested"])
        self.assertEqual(d["feedback_warnings"], ["w1", "w2"])

    def test_feedback_fields_omitted_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=4)
        d = trace.to_dict()
        self.assertNotIn("feedback_outcome_type", d)
        self.assertNotIn("feedback_signal_strength", d)
        self.assertNotIn("feedback_action_id", d)
        self.assertNotIn("feedback_ingested", d)
        self.assertNotIn("feedback_warnings", d)


# ─── Edge cases ──────────────────────────────────────────────────


class TestEdgeCases(unittest.TestCase):
    def test_empty_action_id(self) -> None:
        er = _make_exec_result(action_id="", status="success")
        fb = execution_to_feedback(er)
        self.assertEqual(fb.action_id, "")

    def test_missing_attributes_graceful(self) -> None:
        bare = SimpleNamespace()
        fb = execution_to_feedback(bare)
        self.assertEqual(fb.action_id, "")
        self.assertEqual(fb.action_name, "")
        self.assertEqual(fb.outcome_type, "unknown")
        self.assertAlmostEqual(fb.signal_strength, 0.0)

    def test_none_confidence_defaults(self) -> None:
        er = _make_exec_result(status="success")
        fb = execution_to_feedback(er, confidence=None)
        self.assertAlmostEqual(fb.signal_strength, 0.5)


if __name__ == "__main__":
    unittest.main()
