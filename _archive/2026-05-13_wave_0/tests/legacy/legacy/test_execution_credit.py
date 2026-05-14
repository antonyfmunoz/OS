"""Tests for runtime.execution_credit — credit assignment and policy learning.

Validates: credit assignment, attribution scaling, confidence weighting,
effective credit bounds, unknown outcome safety, learning signal generation,
integration with strategy memory / objective arbiter / multi-world policy,
DecisionTrace enrichment, and round-trip serialization.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from types import SimpleNamespace

from umh.runtime_engine.execution_credit import (
    BASE_CREDIT_MAP,
    BIAS_BOUND,
    BIAS_SCALE,
    MIN_CONFIDENCE_FOR_LEARNING,
    CreditAssignment,
    CreditComputationResult,
    PolicyLearningSignal,
    _compute_attribution,
    apply_credit_to_strategy_memory,
    apply_signal_to_arbiter,
    compute_credit_assignment,
    compute_full_credit,
    compute_risk_penalty_adjustment,
    credit_to_learning_signal,
)


def _make_action(confidence: float = 0.8, action_id: str = "act_1") -> SimpleNamespace:
    return SimpleNamespace(action_id=action_id, confidence=confidence)


def _make_feedback(
    outcome_type: str = "success",
    signal_strength: float = 0.8,
    action_id: str = "act_1",
) -> SimpleNamespace:
    return SimpleNamespace(
        action_id=action_id,
        action_name="test_action",
        outcome_type=outcome_type,
        signal_strength=signal_strength,
        handler_name="log",
        error=None,
    )


def _make_trace(**kwargs) -> SimpleNamespace:
    defaults = {
        "planner_uncertainty": None,
        "synthesized_strategy": None,
        "exploration_rate": None,
        "meta_control_mode": "full",
        "meta_control_instability": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ─── Base credit mapping ─────────────────────────────────────────


class TestBaseCreditMapping(unittest.TestCase):
    def test_success_maps_positive(self) -> None:
        self.assertEqual(BASE_CREDIT_MAP["success"], 1.0)

    def test_failure_maps_negative(self) -> None:
        self.assertEqual(BASE_CREDIT_MAP["failure"], -1.0)

    def test_partial_maps_small_positive(self) -> None:
        self.assertEqual(BASE_CREDIT_MAP["partial"], 0.2)

    def test_unknown_maps_zero(self) -> None:
        self.assertEqual(BASE_CREDIT_MAP["unknown"], 0.0)

    def test_all_four_outcomes(self) -> None:
        self.assertEqual(len(BASE_CREDIT_MAP), 4)


# ─── Attribution ─────────────────────────────────────────────────


class TestAttribution(unittest.TestCase):
    def test_full_attribution_clean_trace(self) -> None:
        attr = _compute_attribution("success", _make_trace())
        self.assertAlmostEqual(attr, 1.0)

    def test_unknown_always_zero(self) -> None:
        attr = _compute_attribution("unknown", _make_trace())
        self.assertAlmostEqual(attr, 0.0)

    def test_unknown_zero_even_with_good_trace(self) -> None:
        trace = _make_trace(meta_control_mode="full")
        attr = _compute_attribution("unknown", trace)
        self.assertAlmostEqual(attr, 0.0)

    def test_high_uncertainty_reduces(self) -> None:
        trace = _make_trace(planner_uncertainty=0.8)
        attr = _compute_attribution("success", trace)
        self.assertAlmostEqual(attr, 0.6)

    def test_synthesis_reduces(self) -> None:
        trace = _make_trace(synthesized_strategy="blended_clarity")
        attr = _compute_attribution("success", trace)
        self.assertAlmostEqual(attr, 0.7)

    def test_exploration_reduces(self) -> None:
        trace = _make_trace(exploration_rate=0.5)
        attr = _compute_attribution("failure", trace)
        self.assertAlmostEqual(attr, 0.7)

    def test_meta_control_non_full_reduces(self) -> None:
        trace = _make_trace(meta_control_mode="conservative")
        attr = _compute_attribution("success", trace)
        self.assertAlmostEqual(attr, 0.8)

    def test_multiple_penalties_compound(self) -> None:
        trace = _make_trace(
            planner_uncertainty=0.8,
            synthesized_strategy="x",
            exploration_rate=0.5,
            meta_control_mode="conservative",
        )
        attr = _compute_attribution("success", trace)
        expected = 1.0 * 0.6 * 0.7 * 0.7 * 0.8
        self.assertAlmostEqual(attr, expected, places=4)

    def test_none_trace_gives_full_attribution(self) -> None:
        attr = _compute_attribution("success", None)
        self.assertAlmostEqual(attr, 1.0)

    def test_attribution_clamped_to_unit(self) -> None:
        attr = _compute_attribution("success", _make_trace())
        self.assertGreaterEqual(attr, 0.0)
        self.assertLessEqual(attr, 1.0)


# ─── Credit assignment ───────────────────────────────────────────


class TestCreditAssignment(unittest.TestCase):
    def test_success_positive_credit(self) -> None:
        c = compute_credit_assignment(_make_action(0.8), _make_feedback("success", 0.8))
        self.assertEqual(c.outcome_type, "success")
        self.assertAlmostEqual(c.credit_score, 1.0)
        self.assertGreater(c.effective_credit, 0.0)

    def test_failure_negative_credit(self) -> None:
        c = compute_credit_assignment(
            _make_action(0.7), _make_feedback("failure", -0.7)
        )
        self.assertEqual(c.outcome_type, "failure")
        self.assertAlmostEqual(c.credit_score, -1.0)
        self.assertLess(c.effective_credit, 0.0)

    def test_unknown_zero_credit(self) -> None:
        c = compute_credit_assignment(_make_action(0.9), _make_feedback("unknown", 0.0))
        self.assertAlmostEqual(c.effective_credit, 0.0)
        self.assertAlmostEqual(c.attribution, 0.0)

    def test_confidence_combines_action_and_signal(self) -> None:
        c = compute_credit_assignment(_make_action(0.8), _make_feedback("success", 0.6))
        expected_conf = (0.8 + 0.6) / 2.0
        self.assertAlmostEqual(c.confidence, expected_conf)

    def test_effective_credit_formula(self) -> None:
        action = _make_action(0.8)
        feedback = _make_feedback("success", 0.8)
        trace = _make_trace()
        c = compute_credit_assignment(action, feedback, trace)
        expected = 1.0 * 1.0 * 0.8  # base * attribution * confidence
        self.assertAlmostEqual(c.effective_credit, expected)

    def test_effective_credit_bounded(self) -> None:
        c = compute_credit_assignment(_make_action(1.0), _make_feedback("success", 1.0))
        self.assertLessEqual(c.effective_credit, 1.0)
        self.assertGreaterEqual(c.effective_credit, -1.0)

    def test_partial_small_positive(self) -> None:
        c = compute_credit_assignment(_make_action(0.5), _make_feedback("partial", 0.0))
        self.assertAlmostEqual(c.credit_score, 0.2)
        self.assertGreaterEqual(c.effective_credit, 0.0)

    def test_reason_string_present(self) -> None:
        c = compute_credit_assignment(_make_action(0.8), _make_feedback("success", 0.8))
        self.assertIn("success", c.reason)

    def test_unknown_reason(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("unknown", 0.0))
        self.assertIn("unknown", c.reason)
        self.assertIn("no attribution", c.reason)

    def test_credit_is_frozen(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        with self.assertRaises(AttributeError):
            c.effective_credit = 999.0

    def test_attribution_reduces_with_uncertain_trace(self) -> None:
        trace = _make_trace(planner_uncertainty=0.9)
        c = compute_credit_assignment(
            _make_action(0.8), _make_feedback("success", 0.8), trace
        )
        c_clean = compute_credit_assignment(
            _make_action(0.8), _make_feedback("success", 0.8), _make_trace()
        )
        self.assertLess(abs(c.effective_credit), abs(c_clean.effective_credit))


# ─── Learning signal ─────────────────────────────────────────────


class TestLearningSignal(unittest.TestCase):
    def test_success_positive_reward_bias(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        s = credit_to_learning_signal(c)
        self.assertGreater(s.reward_bias, 0.0)

    def test_failure_negative_reward_bias(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("failure", -0.8))
        s = credit_to_learning_signal(c)
        self.assertLess(s.reward_bias, 0.0)

    def test_failure_increases_risk_bias(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("failure", -0.8))
        s = credit_to_learning_signal(c)
        self.assertGreater(s.risk_bias, 0.0)

    def test_success_slightly_reduces_risk(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        s = credit_to_learning_signal(c)
        self.assertLess(s.risk_bias, 0.0)

    def test_unknown_zero_biases(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("unknown", 0.0))
        s = credit_to_learning_signal(c)
        self.assertAlmostEqual(s.reward_bias, 0.0)
        self.assertAlmostEqual(s.risk_bias, 0.0)
        self.assertAlmostEqual(s.stability_bias, 0.0)

    def test_all_biases_bounded(self) -> None:
        c = compute_credit_assignment(_make_action(1.0), _make_feedback("success", 1.0))
        s = credit_to_learning_signal(c)
        self.assertLessEqual(abs(s.reward_bias), BIAS_BOUND)
        self.assertLessEqual(abs(s.risk_bias), BIAS_BOUND)
        self.assertLessEqual(abs(s.stability_bias), BIAS_BOUND)

    def test_low_confidence_zero_signal(self) -> None:
        c = CreditAssignment(
            action_id="x",
            outcome_type="success",
            credit_score=1.0,
            confidence=0.1,
            attribution=1.0,
            effective_credit=0.1,
            reason="test",
        )
        s = credit_to_learning_signal(c)
        self.assertAlmostEqual(s.reward_bias, 0.0)

    def test_stability_boost_on_failure_with_instability(self) -> None:
        trace = _make_trace(meta_control_instability=0.5)
        c = compute_credit_assignment(
            _make_action(), _make_feedback("failure", -0.8), trace
        )
        s = credit_to_learning_signal(c, trace)
        self.assertGreater(s.stability_bias, 0.0)

    def test_stability_reinforcement_on_success(self) -> None:
        trace = _make_trace()
        c = compute_credit_assignment(
            _make_action(), _make_feedback("success", 0.8), trace
        )
        s = credit_to_learning_signal(c, trace)
        self.assertGreaterEqual(s.stability_bias, 0.0)

    def test_source_always_execution_credit(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        s = credit_to_learning_signal(c)
        self.assertEqual(s.source, "execution_credit")

    def test_signal_is_frozen(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        s = credit_to_learning_signal(c)
        with self.assertRaises(AttributeError):
            s.reward_bias = 999.0


# ─── Strategy memory integration ─────────────────────────────────


class TestStrategyMemoryIntegration(unittest.TestCase):
    def test_apply_credit_succeeds(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("clarity", 0.8)

        c = compute_credit_assignment(_make_action(), _make_feedback("success", 0.8))
        applied = apply_credit_to_strategy_memory(c, mem, "clarity")
        self.assertTrue(applied)

    def test_apply_credit_unknown_skipped(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("clarity", 0.8)

        c = compute_credit_assignment(_make_action(), _make_feedback("unknown", 0.0))
        applied = apply_credit_to_strategy_memory(c, mem, "clarity")
        self.assertFalse(applied)

    def test_apply_credit_no_strategy_skipped(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        applied = apply_credit_to_strategy_memory(c, mem, "")
        self.assertFalse(applied)

    def test_record_execution_credit_method(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("clarity", 0.8)
        original_ema = mem.get_stats("clarity").ema_score

        result = mem.record_execution_credit("act_1", 0.5)
        self.assertTrue(result)
        self.assertNotAlmostEqual(mem.get_stats("clarity").ema_score, original_ema)

    def test_record_execution_credit_no_data(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        result = mem.record_execution_credit("act_1", 0.5)
        self.assertFalse(result)


# ─── Objective arbiter integration ───────────────────────────────


class TestArbiterIntegration(unittest.TestCase):
    def test_apply_signal_changes_weights(self) -> None:
        from umh.runtime_engine.objective_arbitration import ObjectiveArbiter

        arb = ObjectiveArbiter()
        original_reward = arb.weights.reward_weight

        signal = PolicyLearningSignal(
            action_id="x",
            reward_bias=0.03,
            risk_bias=0.01,
            stability_bias=0.0,
            confidence=0.8,
            source="execution_credit",
        )
        applied = apply_signal_to_arbiter(signal, arb)
        self.assertTrue(applied)
        self.assertAlmostEqual(
            arb.weights.reward_weight, original_reward + 0.03, places=4
        )

    def test_apply_signal_low_confidence_skipped(self) -> None:
        from umh.runtime_engine.objective_arbitration import ObjectiveArbiter

        arb = ObjectiveArbiter()
        original = arb.weights.reward_weight

        signal = PolicyLearningSignal(
            action_id="x",
            reward_bias=0.05,
            risk_bias=0.0,
            stability_bias=0.0,
            confidence=0.1,
            source="execution_credit",
        )
        applied = apply_signal_to_arbiter(signal, arb)
        self.assertFalse(applied)
        self.assertAlmostEqual(arb.weights.reward_weight, original)

    def test_apply_execution_credit_bias_method(self) -> None:
        from umh.runtime_engine.objective_arbitration import ObjectiveArbiter

        arb = ObjectiveArbiter()
        original = arb.weights.risk_weight

        changed = arb.apply_execution_credit_bias(0.0, 0.02, 0.0)
        self.assertTrue(changed)
        self.assertAlmostEqual(arb.weights.risk_weight, original + 0.02, places=4)

    def test_apply_execution_credit_bias_clamps(self) -> None:
        from umh.runtime_engine.objective_arbitration import ObjectiveArbiter, RISK_WEIGHT_MAX

        arb = ObjectiveArbiter()
        arb.apply_execution_credit_bias(0.0, 10.0, 0.0)
        self.assertLessEqual(arb.weights.risk_weight, RISK_WEIGHT_MAX)

    def test_zero_bias_no_change(self) -> None:
        from umh.runtime_engine.objective_arbitration import ObjectiveArbiter

        arb = ObjectiveArbiter()
        signal = PolicyLearningSignal(
            action_id="x",
            reward_bias=0.0,
            risk_bias=0.0,
            stability_bias=0.0,
            confidence=0.8,
            source="execution_credit",
        )
        applied = apply_signal_to_arbiter(signal, arb)
        self.assertFalse(applied)


# ─── Risk penalty adjustment ─────────────────────────────────────


class TestRiskPenaltyAdjustment(unittest.TestCase):
    def test_failure_increases_risk(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("failure", -0.8))
        adj = compute_risk_penalty_adjustment(c)
        self.assertGreater(adj, 0.0)

    def test_success_reduces_risk(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success", 0.8))
        adj = compute_risk_penalty_adjustment(c)
        self.assertLess(adj, 0.0)

    def test_unknown_zero_adjustment(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("unknown", 0.0))
        adj = compute_risk_penalty_adjustment(c)
        self.assertAlmostEqual(adj, 0.0)

    def test_adjustment_bounded(self) -> None:
        c = compute_credit_assignment(
            _make_action(1.0), _make_feedback("failure", -1.0)
        )
        adj = compute_risk_penalty_adjustment(c)
        self.assertLessEqual(abs(adj), BIAS_BOUND)


# ─── Full pipeline ───────────────────────────────────────────────


class TestFullPipeline(unittest.TestCase):
    def test_compute_full_credit_success(self) -> None:
        result = compute_full_credit(
            _make_action(), _make_feedback("success"), _make_trace()
        )
        self.assertGreater(result.credit.effective_credit, 0.0)
        self.assertGreater(result.learning_signal.reward_bias, 0.0)
        self.assertEqual(len(result.warnings), 0)

    def test_compute_full_credit_unknown_warns(self) -> None:
        result = compute_full_credit(_make_action(), _make_feedback("unknown", 0.0))
        self.assertAlmostEqual(result.credit.effective_credit, 0.0)
        self.assertTrue(any("unknown" in w for w in result.warnings))

    def test_compute_full_credit_low_confidence_warns(self) -> None:
        result = compute_full_credit(
            _make_action(0.05), _make_feedback("success", 0.05)
        )
        self.assertTrue(any("confidence" in w for w in result.warnings))


# ─── DecisionTrace integration ───────────────────────────────────


class TestDecisionTraceIntegration(unittest.TestCase):
    def test_credit_fields_on_trace(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            credit_score=0.8,
            credit_attribution=0.9,
            effective_credit=0.72,
            learning_signal_applied=True,
            learning_signal_strength=0.03,
        )
        self.assertAlmostEqual(trace.credit_score, 0.8)
        self.assertAlmostEqual(trace.credit_attribution, 0.9)
        self.assertAlmostEqual(trace.effective_credit, 0.72)
        self.assertTrue(trace.learning_signal_applied)
        self.assertAlmostEqual(trace.learning_signal_strength, 0.03)

    def test_credit_fields_default_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=2)
        self.assertIsNone(trace.credit_score)
        self.assertIsNone(trace.credit_attribution)
        self.assertIsNone(trace.effective_credit)
        self.assertIsNone(trace.learning_signal_applied)
        self.assertIsNone(trace.learning_signal_strength)

    def test_credit_fields_in_to_dict(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=3,
            credit_score=-0.5,
            credit_attribution=0.6,
            effective_credit=-0.3,
            learning_signal_applied=False,
            learning_signal_strength=0.0,
        )
        d = trace.to_dict()
        self.assertAlmostEqual(d["credit_score"], -0.5, places=4)
        self.assertAlmostEqual(d["credit_attribution"], 0.6, places=4)
        self.assertAlmostEqual(d["effective_credit"], -0.3, places=4)
        self.assertFalse(d["learning_signal_applied"])
        self.assertAlmostEqual(d["learning_signal_strength"], 0.0, places=4)

    def test_credit_fields_omitted_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=4)
        d = trace.to_dict()
        self.assertNotIn("credit_score", d)
        self.assertNotIn("credit_attribution", d)
        self.assertNotIn("effective_credit", d)
        self.assertNotIn("learning_signal_applied", d)
        self.assertNotIn("learning_signal_strength", d)


# ─── Round-trip serialization ────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_credit_round_trip(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("failure", -0.7))
        d = c.to_dict()
        restored = CreditAssignment.from_dict(d)
        self.assertEqual(restored.action_id, c.action_id)
        self.assertEqual(restored.outcome_type, c.outcome_type)
        self.assertAlmostEqual(restored.effective_credit, c.effective_credit, places=4)

    def test_signal_round_trip(self) -> None:
        c = compute_credit_assignment(_make_action(), _make_feedback("success"))
        s = credit_to_learning_signal(c)
        d = s.to_dict()
        restored = PolicyLearningSignal.from_dict(d)
        self.assertAlmostEqual(restored.reward_bias, s.reward_bias, places=6)
        self.assertEqual(restored.source, "execution_credit")

    def test_full_result_round_trip(self) -> None:
        result = compute_full_credit(_make_action(), _make_feedback("success"))
        d = result.to_dict()
        restored = CreditComputationResult.from_dict(d)
        self.assertEqual(restored.credit.outcome_type, result.credit.outcome_type)
        self.assertAlmostEqual(
            restored.learning_signal.reward_bias,
            result.learning_signal.reward_bias,
            places=6,
        )


# ─── Edge cases ──────────────────────────────────────────────────


class TestEdgeCases(unittest.TestCase):
    def test_bare_namespace_action(self) -> None:
        bare = SimpleNamespace()
        c = compute_credit_assignment(bare, _make_feedback("success"))
        self.assertEqual(c.outcome_type, "success")

    def test_bare_namespace_feedback(self) -> None:
        bare = SimpleNamespace()
        c = compute_credit_assignment(_make_action(), bare)
        self.assertEqual(c.outcome_type, "unknown")
        self.assertAlmostEqual(c.effective_credit, 0.0)

    def test_none_confidence_defaults(self) -> None:
        action = SimpleNamespace(action_id="x", confidence=None)
        c = compute_credit_assignment(action, _make_feedback("success"))
        self.assertAlmostEqual(c.confidence, (0.5 + 0.8) / 2.0)

    def test_deterministic_same_inputs(self) -> None:
        a = _make_action(0.7)
        f = _make_feedback("success", 0.7)
        t = _make_trace()
        c1 = compute_credit_assignment(a, f, t)
        c2 = compute_credit_assignment(a, f, t)
        self.assertAlmostEqual(c1.effective_credit, c2.effective_credit)
        self.assertEqual(c1.reason, c2.reason)


# ─── No regression checks ───────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_strategy_memory_basic_ops(self) -> None:
        from umh.strategy.memory import StrategyMemory

        mem = StrategyMemory()
        mem.record_win("a", 0.7)
        mem.record_win("b", 0.9)
        ranked = mem.rank_strategies()
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0][0], "b")

    def test_arbiter_basic_ops(self) -> None:
        from umh.runtime_engine.objective_arbitration import (
            ContextSignals,
            ObjectiveArbiter,
        )

        arb = ObjectiveArbiter()
        result = arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        self.assertTrue(result.active)
        self.assertEqual(result.mode, "stable")

    def test_feedback_tests_still_work(self) -> None:
        from umh.runtime_engine.execution_feedback import execution_to_feedback

        er = SimpleNamespace(
            action_id="x",
            action_name="test",
            handler_name="log",
            status="success",
            output={},
            error=None,
        )
        fb = execution_to_feedback(er, confidence=0.8)
        self.assertEqual(fb.outcome_type, "success")


if __name__ == "__main__":
    unittest.main()
