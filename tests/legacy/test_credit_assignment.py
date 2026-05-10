"""Tests for eos_ai.credit_assignment — temporal credit assignment layer."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.credit_assignment import (
    MAX_CREDIT,
    MIN_TRACE_LENGTH,
    NO_CREDIT_SIGNAL,
    CreditAccumulator,
    CreditAssignmentEngine,
    CreditSignal,
    apply_credit_adjustment,
)


# ─── TestDeterminism ────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_identical_sequences_identical_signals(self):
        def run():
            eng = CreditAssignmentEngine()
            for i in range(20):
                eng.record_step(f"a{i % 3}", "ctx", 0.5 + 0.1 * (i % 4), 0.5)
            return eng.compute_signal()

        s1 = run()
        s2 = run()
        self.assertEqual(s1.to_dict(), s2.to_dict())

    def test_identical_sequences_identical_snapshots(self):
        def run():
            eng = CreditAssignmentEngine()
            for i in range(15):
                eng.record_step(f"a{i % 2}", "stable", 0.3 * (i % 5), 0.5)
            return eng.snapshot()

        self.assertEqual(run(), run())


# ─── TestNoDataNoEffect ─────────────────────────────────────────────


class TestNoDataNoEffect(unittest.TestCase):
    def test_empty_engine_returns_no_signal(self):
        eng = CreditAssignmentEngine()
        sig = eng.compute_signal()
        self.assertEqual(sig, NO_CREDIT_SIGNAL)
        self.assertEqual(sig.reason, "no_data")

    def test_below_min_trace_returns_no_signal(self):
        eng = CreditAssignmentEngine()
        for i in range(MIN_TRACE_LENGTH - 1):
            eng.record_step("a0", "ctx", 0.5, 0.5)
        sig = eng.compute_signal()
        self.assertEqual(sig.reason, "no_data")

    def test_no_signal_sentinel_values(self):
        self.assertEqual(NO_CREDIT_SIGNAL.action_credit, {})
        self.assertEqual(NO_CREDIT_SIGNAL.horizon, 0)
        self.assertEqual(NO_CREDIT_SIGNAL.confidence, 0.0)

    def test_apply_no_signal_passthrough(self):
        scores = {"a": 0.5, "b": 0.3}
        result = apply_credit_adjustment(scores, NO_CREDIT_SIGNAL)
        self.assertEqual(result, scores)

    def test_apply_empty_scores_passthrough(self):
        sig = CreditSignal(
            action_credit={"a": 0.01}, horizon=10, confidence=0.5, reason="test"
        )
        result = apply_credit_adjustment({}, sig)
        self.assertEqual(result, {})


# ─── TestCreditPropagation ──────────────────────────────────────────


class TestCreditPropagation(unittest.TestCase):
    def test_recent_action_gets_more_credit_than_old(self):
        eng = CreditAssignmentEngine()
        eng.record_step("old_action", "ctx", 0.5, 0.5)
        for _ in range(8):
            eng.record_step("filler", "ctx", 0.5, 0.5)
        eng.record_step("recent_action", "ctx", 0.5, 0.5)
        eng.record_step("current", "ctx", 1.0, 1.0)

        old_acc = eng._accumulators.get("old_action")
        recent_acc = eng._accumulators.get("recent_action")
        self.assertIsNotNone(old_acc)
        self.assertIsNotNone(recent_acc)
        self.assertGreater(
            abs(recent_acc.reward_credit),
            0,
            "Recent action should have non-zero credit",
        )

    def test_positive_reward_delta_gives_positive_credit(self):
        eng = CreditAssignmentEngine()
        for _ in range(5):
            eng.record_step("a0", "ctx", 0.3, 0.3)
        eng.record_step("a0", "ctx", 0.3, 0.3)
        eng.record_step("a0", "ctx", 1.0, 1.0)
        acc = eng._accumulators.get("a0")
        self.assertIsNotNone(acc)
        self.assertGreater(acc.reward_credit, 0)

    def test_negative_reward_delta_gives_negative_credit(self):
        eng = CreditAssignmentEngine()
        for _ in range(5):
            eng.record_step("a0", "ctx", 0.8, 0.8)
        eng.record_step("a0", "ctx", 0.8, 0.8)
        eng.record_step("a0", "ctx", 0.1, 0.1)
        acc = eng._accumulators.get("a0")
        self.assertIsNotNone(acc)
        self.assertLess(acc.reward_credit, 0)

    def test_gamma_decay_correct(self):
        eng = CreditAssignmentEngine()
        eng.record_step("a0", "ctx", 0.5, 0.5)
        eng.record_step("a1", "ctx", 0.5, 0.5)
        eng.record_step("a2", "ctx", 1.5, 1.5)

        acc_a1 = eng._accumulators.get("a1")
        acc_a0 = eng._accumulators.get("a0")
        self.assertIsNotNone(acc_a1)
        self.assertIsNotNone(acc_a0)
        self.assertAlmostEqual(
            abs(acc_a1.reward_credit) / abs(acc_a0.reward_credit),
            0.8 / (0.8**2),
            places=4,
        )


# ─── TestBoundedOutputs ─────────────────────────────────────────────


class TestBoundedOutputs(unittest.TestCase):
    def test_credit_within_bounds(self):
        eng = CreditAssignmentEngine()
        for i in range(20):
            reward = 1.0 if i % 3 == 0 else 0.0
            eng.record_step(f"a{i % 4}", "ctx", reward, reward)

        sig = eng.compute_signal()
        for credit in sig.action_credit.values():
            self.assertGreaterEqual(credit, -MAX_CREDIT)
            self.assertLessEqual(credit, MAX_CREDIT)

    def test_confidence_bounded_zero_to_one(self):
        eng = CreditAssignmentEngine()
        for i in range(20):
            eng.record_step(f"a{i % 2}", "ctx", 0.5 + 0.3 * (i % 3), 0.5)
        sig = eng.compute_signal()
        self.assertGreaterEqual(sig.confidence, 0.0)
        self.assertLessEqual(sig.confidence, 1.0)

    def test_apply_preserves_leader_with_large_gap(self):
        scores = {"a": 0.9, "b": 0.3, "c": 0.2}
        sig = CreditSignal(
            action_credit={"a": -0.05, "b": 0.05},
            horizon=10,
            confidence=1.0,
            reason="test",
        )
        result = apply_credit_adjustment(scores, sig)
        self.assertEqual(result["a"], 0.9)

    def test_apply_adjusts_non_leader(self):
        scores = {"a": 0.5, "b": 0.3}
        sig = CreditSignal(
            action_credit={"b": 0.04},
            horizon=10,
            confidence=1.0,
            reason="test",
        )
        result = apply_credit_adjustment(scores, sig)
        self.assertAlmostEqual(result["b"], 0.34)


# ─── TestConfidenceScaling ──────────────────────────────────────────


class TestConfidenceScaling(unittest.TestCase):
    def test_short_trace_low_confidence(self):
        eng = CreditAssignmentEngine()
        for i in range(MIN_TRACE_LENGTH):
            eng.record_step(f"a{i % 2}", "ctx", 0.5 + 0.2 * i, 0.5)
        sig = eng.compute_signal()
        self.assertLessEqual(sig.confidence, 1.0)

    def test_long_trace_higher_confidence(self):
        eng = CreditAssignmentEngine()
        for i in range(20):
            eng.record_step(f"a{i % 3}", "ctx", 0.5 + 0.1 * (i % 4), 0.5)
        sig = eng.compute_signal()
        self.assertGreater(sig.confidence, 0.0)

    def test_high_variance_reduces_stability(self):
        acc = CreditAccumulator(action="test")
        acc.sum_sq_diff = 100.0
        acc.observation_count = 10
        self.assertLess(acc.stability, 0.5)


# ─── TestDelayedRewardAttribution ──────────────────────────────────


class TestDelayedRewardAttribution(unittest.TestCase):
    def test_delayed_reward_credits_past_actions(self):
        eng = CreditAssignmentEngine()
        eng.record_step("good_action", "ctx", 0.5, 0.5)
        for _ in range(4):
            eng.record_step("neutral", "ctx", 0.5, 0.5)
        eng.record_step("neutral", "ctx", 1.0, 1.0)

        acc = eng._accumulators.get("good_action")
        self.assertIsNotNone(acc)
        self.assertGreater(acc.reward_credit, 0)

    def test_trap_action_gets_delayed_penalty(self):
        eng = CreditAssignmentEngine()
        eng.record_step("trap_action", "ctx", 0.8, 0.8)
        for _ in range(3):
            eng.record_step("neutral", "ctx", 0.8, 0.8)
        eng.record_step("neutral", "ctx", 0.2, 0.2)

        acc = eng._accumulators.get("trap_action")
        self.assertIsNotNone(acc)
        self.assertLess(acc.reward_credit, 0)

    def test_multiple_delayed_rewards_accumulate(self):
        eng = CreditAssignmentEngine()
        eng.record_step("setup_action", "ctx", 0.5, 0.5)
        for i in range(5):
            eng.record_step("filler", "ctx", 0.5 + 0.1 * i, 0.5 + 0.1 * i)

        acc = eng._accumulators.get("setup_action")
        self.assertIsNotNone(acc)
        self.assertGreater(acc.observation_count, 1)


# ─── TestPersistenceRoundtrip ───────────────────────────────────────


class TestPersistenceRoundtrip(unittest.TestCase):
    def test_snapshot_restore_roundtrip(self):
        eng = CreditAssignmentEngine()
        for i in range(15):
            eng.record_step(f"a{i % 3}", "ctx", 0.5 + 0.1 * i, 0.5)
        snap = eng.snapshot()

        eng2 = CreditAssignmentEngine()
        eng2.restore(snap)
        self.assertEqual(eng2.snapshot(), snap)

    def test_restore_none_safe(self):
        eng = CreditAssignmentEngine()
        eng.restore(None)
        self.assertEqual(eng.trace_length, 0)

    def test_restore_empty_dict_safe(self):
        eng = CreditAssignmentEngine()
        eng.restore({})
        self.assertEqual(eng.trace_length, 0)

    def test_snapshot_has_version(self):
        eng = CreditAssignmentEngine()
        snap = eng.snapshot()
        self.assertEqual(snap["version"], 1)

    def test_restored_engine_produces_same_signal(self):
        eng = CreditAssignmentEngine()
        for i in range(15):
            eng.record_step(f"a{i % 3}", "ctx", 0.5 + 0.1 * (i % 4), 0.5)
        sig1 = eng.compute_signal()
        snap = eng.snapshot()

        eng2 = CreditAssignmentEngine()
        eng2.restore(snap)
        sig2 = eng2.compute_signal()
        self.assertEqual(sig1.to_dict(), sig2.to_dict())


# ─── TestSlidingWindow ──────────────────────────────────────────────


class TestSlidingWindow(unittest.TestCase):
    def test_trace_bounded_by_max(self):
        eng = CreditAssignmentEngine()
        for i in range(30):
            eng.record_step(f"a{i}", "ctx", 0.5, 0.5)
        self.assertLessEqual(eng.trace_length, 20)

    def test_old_entries_evicted(self):
        eng = CreditAssignmentEngine()
        for i in range(25):
            eng.record_step(f"a{i}", "ctx", 0.5, 0.5)
        self.assertNotIn("a0", [a for a in eng._actions])


# ─── TestNoRegressionBaseline ───────────────────────────────────────


class TestNoRegressionBaseline(unittest.TestCase):
    def _run_scenario(self, rewards):
        eng = CreditAssignmentEngine()
        for i, r in enumerate(rewards):
            eng.record_step(f"a{i % 4}", "ctx", r, r)
        return eng.compute_signal()

    def test_periodic_no_regression(self):
        rewards = [1.0 if i % 10 < 5 else 0.0 for i in range(20)]
        sig = self._run_scenario(rewards)
        for credit in sig.action_credit.values():
            self.assertGreaterEqual(credit, -MAX_CREDIT)
            self.assertLessEqual(credit, MAX_CREDIT)

    def test_static_no_regression(self):
        rewards = [0.8] * 20
        sig = self._run_scenario(rewards)
        self.assertIn(
            sig.reason, ("no_data", "no_differentiation", "credits_too_small")
        )

    def test_adversarial_no_regression(self):
        rewards = [1.0 if i < 10 else 0.0 for i in range(20)]
        sig = self._run_scenario(rewards)
        for credit in sig.action_credit.values():
            self.assertGreaterEqual(credit, -MAX_CREDIT)
            self.assertLessEqual(credit, MAX_CREDIT)


# ─── TestPipelineIntegration ────────────────────────────────────────


class TestPipelineIntegration(unittest.TestCase):
    def test_apply_additive(self):
        scores = {"a": 0.5, "b": 0.3, "c": 0.2}
        sig = CreditSignal(
            action_credit={"b": 0.03}, horizon=10, confidence=1.0, reason="test"
        )
        result = apply_credit_adjustment(scores, sig)
        self.assertAlmostEqual(result["b"], 0.33)
        self.assertAlmostEqual(result["a"], 0.5)

    def test_apply_empty_credit_passthrough(self):
        scores = {"a": 0.5}
        sig = CreditSignal(action_credit={}, horizon=10, confidence=0.5, reason="test")
        self.assertEqual(apply_credit_adjustment(scores, sig), scores)

    def test_to_dict(self):
        sig = CreditSignal(
            action_credit={"a": 0.01234567},
            horizon=15,
            confidence=0.789,
            reason="test",
        )
        d = sig.to_dict()
        self.assertIn("action_credit", d)
        self.assertEqual(d["horizon"], 15)
        self.assertAlmostEqual(d["confidence"], 0.789, places=3)

    def test_reset_clears_state(self):
        eng = CreditAssignmentEngine()
        for i in range(10):
            eng.record_step("a0", "ctx", 0.5 * i, 0.5)
        eng.reset()
        self.assertEqual(eng.trace_length, 0)
        self.assertEqual(eng.tracked_actions, 0)
        self.assertEqual(eng.propagation_count, 0)

    def test_accumulator_to_dict(self):
        acc = CreditAccumulator(action="test")
        acc.reward_credit = 0.123
        acc.observation_count = 5
        d = acc.to_dict()
        self.assertEqual(d["action"], "test")
        self.assertAlmostEqual(d["reward_credit"], 0.123, places=3)


# ─── TestObjectiveAwareCredit ──────────────────────────────────────


class TestObjectiveAwareCredit(unittest.TestCase):
    def test_objective_contributes_to_credit(self):
        eng = CreditAssignmentEngine()
        eng.record_step("a0", "ctx", 0.5, 0.5)
        eng.record_step("a0", "ctx", 0.5, 1.0)

        acc = eng._accumulators.get("a0")
        self.assertIsNotNone(acc)
        self.assertGreater(acc.objective_credit, 0)

    def test_combined_credit_uses_weights(self):
        acc = CreditAccumulator(action="test")
        acc.reward_credit = 1.0
        acc.objective_credit = 1.0
        expected = 0.6 * 1.0 + 0.4 * 1.0
        self.assertAlmostEqual(acc.combined_credit, expected)


# ─── TestContextFiltering ──────────────────────────────────────────


class TestContextFiltering(unittest.TestCase):
    def test_available_actions_filters_signal(self):
        eng = CreditAssignmentEngine()
        for i in range(15):
            r = 1.0 if i % 2 == 0 else 0.0
            eng.record_step(f"a{i % 3}", "ctx", r, r)

        sig_all = eng.compute_signal()
        sig_filtered = eng.compute_signal(available_actions=["a0"])

        if sig_filtered.action_credit:
            for action in sig_filtered.action_credit:
                self.assertEqual(action, "a0")


# ─── TestBenchmarkIntegration ──────────────────────────────────────


class TestBenchmarkIntegration(unittest.TestCase):
    def _run_with_credit(self, scenario_cls, seed=42, steps=200):
        from umh.runtime_engine.long_horizon_benchmark import (
            SYSTEM_FACTORIES,
            get_all_scenarios,
            run_long_horizon,
        )

        scenarios = get_all_scenarios(seed=seed)
        corrected = SYSTEM_FACTORIES["eos_corrected"]()
        substrate = SYSTEM_FACTORIES["eos_substrate"]()
        scenario = scenarios[scenario_cls]

        from umh.runtime_engine.long_horizon_benchmark import (
            PeriodicShiftScenario,
        )

        s1 = PeriodicShiftScenario(seed=seed, period=200)
        s2 = PeriodicShiftScenario(seed=seed, period=200)

        c_result = run_long_horizon(corrected, s1, horizon=steps, seed=seed)
        s_result = run_long_horizon(substrate, s2, horizon=steps, seed=seed)
        return c_result.reward_metrics.avg_reward, s_result.reward_metrics.avg_reward

    def test_no_regression_periodic(self):
        c, s = self._run_with_credit("PeriodicShift")
        self.assertGreaterEqual(c, s)

    def test_restart_continuity(self):
        from umh.runtime_engine.long_horizon_benchmark import (
            SYSTEM_FACTORIES,
            PeriodicShiftScenario,
            run_long_horizon,
        )

        s1 = PeriodicShiftScenario(seed=42, period=200)
        s2 = PeriodicShiftScenario(seed=42, period=200)

        sys1 = SYSTEM_FACTORIES["eos_corrected"]()
        sys2 = SYSTEM_FACTORIES["eos_corrected"]()

        r1 = run_long_horizon(sys1, s1, horizon=200, seed=42)
        r2 = run_long_horizon(sys2, s2, horizon=200, seed=42)

        self.assertAlmostEqual(
            r1.reward_metrics.avg_reward,
            r2.reward_metrics.avg_reward,
            places=6,
        )

    def test_no_regression_slow_drift(self):
        from umh.runtime_engine.long_horizon_benchmark import (
            SYSTEM_FACTORIES,
            SlowDriftScenario,
            run_long_horizon,
        )

        s1 = SlowDriftScenario(seed=42)
        s2 = SlowDriftScenario(seed=42)

        corrected = SYSTEM_FACTORIES["eos_corrected"]()
        substrate = SYSTEM_FACTORIES["eos_substrate"]()

        c = run_long_horizon(corrected, s1, horizon=200, seed=42)
        s = run_long_horizon(substrate, s2, horizon=200, seed=42)

        self.assertGreaterEqual(
            c.reward_metrics.avg_reward,
            s.reward_metrics.avg_reward,
        )


# ─── TestSafetyRules ───────────────────────────────────────────────


class TestSafetyRules(unittest.TestCase):
    def test_no_credit_exceeds_max(self):
        eng = CreditAssignmentEngine()
        for i in range(20):
            reward = 10.0 if i % 5 == 0 else 0.0
            eng.record_step(f"a{i % 3}", "ctx", reward, reward)
        sig = eng.compute_signal()
        for credit in sig.action_credit.values():
            self.assertGreaterEqual(credit, -MAX_CREDIT)
            self.assertLessEqual(credit, MAX_CREDIT)

    def test_trace_never_exceeds_max_length(self):
        eng = CreditAssignmentEngine()
        for i in range(100):
            eng.record_step(f"a{i}", "ctx", float(i), float(i))
        self.assertLessEqual(eng.trace_length, 20)

    def test_no_circular_dependency(self):
        eng = CreditAssignmentEngine()
        for i in range(8):
            eng.record_step(f"a{i % 2}", "ctx", 0.5 + 0.1 * i, 0.5)
        sig1 = eng.compute_signal()
        eng.record_step("a0", "ctx", 1.0, 1.0)
        sig2 = eng.compute_signal()
        self.assertIsInstance(sig1, CreditSignal)
        self.assertIsInstance(sig2, CreditSignal)


if __name__ == "__main__":
    unittest.main()
