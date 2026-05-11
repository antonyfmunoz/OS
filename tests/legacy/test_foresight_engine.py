"""Tests for runtime.foresight_engine — forward rollout (foresight) layer."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.foresight_engine import (
    MAX_BIAS,
    MAX_DEPTH,
    NO_FORESIGHT_SIGNAL,
    ForesightEngine,
    ForesightSignal,
    RolloutResult,
    apply_foresight_bias,
    extract_causal_stats,
    extract_credit_accumulators,
)


def _make_causal_stats(
    actions: list[str], context: str = "stable", reward_delta: float = 0.1
) -> dict:
    """Build mock causal stats dict keyed as 'context|action'."""
    stats = {}
    for i, action in enumerate(actions):
        key = f"{context}|{action}"
        stats[key] = {
            "context_type": context,
            "action": action,
            "count": 15,
            "ema_reward_delta": reward_delta * (1 + i * 0.5),
            "ema_objective_delta": reward_delta * (1 + i * 0.3),
            "positive_count": 10,
            "ema_variance": 0.01,
        }
    return stats


def _make_credit_accumulators(actions: list[str], reward_credit: float = 0.5) -> dict:
    """Build mock credit accumulators dict."""
    accs = {}
    for i, action in enumerate(actions):
        accs[action] = {
            "action": action,
            "reward_credit": reward_credit * (1 + i * 0.3),
            "objective_credit": reward_credit * (1 + i * 0.2),
            "observation_count": 10,
            "positive_count": 7,
            "sum_sq_diff": 0.01,
            "ema_credit": 0.05,
        }
    return accs


# ─── TestDeterminism ────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_identical_inputs_identical_rollouts(self):
        eng = ForesightEngine()
        actions = ["a0", "a1", "a2"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        s1 = eng.compute_signal(actions, "stable", stats, accs)
        s2 = eng.compute_signal(actions, "stable", stats, accs)
        self.assertEqual(s1.to_dict(), s2.to_dict())

    def test_identical_rollout_results(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"])
        accs = _make_credit_accumulators(["a0"])

        r1 = eng.simulate_action("a0", "stable", stats, accs)
        r2 = eng.simulate_action("a0", "stable", stats, accs)
        self.assertEqual(r1.to_dict(), r2.to_dict())


# ─── TestNoDataNoEffect ─────────────────────────────────────────────


class TestNoDataNoEffect(unittest.TestCase):
    def test_no_actions_returns_no_signal(self):
        eng = ForesightEngine()
        sig = eng.compute_signal([], "stable")
        self.assertEqual(sig, NO_FORESIGHT_SIGNAL)

    def test_no_causal_no_credit_returns_no_signal(self):
        eng = ForesightEngine()
        sig = eng.compute_signal(["a0", "a1"], "stable")
        self.assertEqual(sig.reason, "no_data")

    def test_below_min_observations_no_effect(self):
        eng = ForesightEngine()
        stats = {"stable|a0": {"count": 2, "ema_reward_delta": 0.5}}
        sig = eng.compute_signal(["a0"], "stable", causal_stats=stats)
        self.assertEqual(sig.reason, "no_data")

    def test_no_signal_sentinel_values(self):
        self.assertEqual(NO_FORESIGHT_SIGNAL.action_bias, {})
        self.assertEqual(NO_FORESIGHT_SIGNAL.horizon, 0)
        self.assertEqual(NO_FORESIGHT_SIGNAL.confidence, 0.0)

    def test_apply_no_signal_passthrough(self):
        scores = {"a": 0.5, "b": 0.3}
        result = apply_foresight_bias(scores, NO_FORESIGHT_SIGNAL)
        self.assertEqual(result, scores)


# ─── TestRolloutLogic ───────────────────────────────────────────────


class TestRolloutLogic(unittest.TestCase):
    def test_rollout_uses_gamma_decay(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"], reward_delta=1.0)

        r1 = eng.simulate_action("a0", "stable", stats, depth=1)
        r3 = eng.simulate_action("a0", "stable", stats, depth=3)

        self.assertGreater(r3.trajectory_score, r1.trajectory_score)
        self.assertEqual(r1.steps_used, 1)
        self.assertEqual(r3.steps_used, 3)

    def test_depth_capped_at_max(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"])

        r = eng.simulate_action("a0", "stable", stats, depth=10)
        self.assertLessEqual(r.steps_used, MAX_DEPTH)

    def test_positive_causal_gives_positive_trajectory(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"], reward_delta=0.5)
        r = eng.simulate_action("a0", "stable", stats)
        self.assertGreater(r.trajectory_score, 0)

    def test_negative_causal_gives_negative_trajectory(self):
        eng = ForesightEngine()
        stats = {
            "stable|a0": {
                "count": 15,
                "ema_reward_delta": -0.5,
                "ema_objective_delta": -0.5,
            }
        }
        r = eng.simulate_action("a0", "stable", stats)
        self.assertLess(r.trajectory_score, 0)

    def test_credit_signals_contribute(self):
        eng = ForesightEngine()
        accs = _make_credit_accumulators(["a0"], reward_credit=1.0)
        r = eng.simulate_action("a0", "stable", credit_accumulators=accs)
        self.assertGreater(r.trajectory_score, 0)
        self.assertGreater(r.steps_used, 0)


# ─── TestBoundedOutputs ─────────────────────────────────────────────


class TestBoundedOutputs(unittest.TestCase):
    def test_bias_within_bounds(self):
        eng = ForesightEngine()
        actions = ["a0", "a1", "a2", "a3"]
        stats = _make_causal_stats(actions, reward_delta=10.0)
        accs = _make_credit_accumulators(actions, reward_credit=10.0)

        sig = eng.compute_signal(actions, "stable", stats, accs)
        for bias in sig.action_bias.values():
            self.assertGreaterEqual(bias, -MAX_BIAS)
            self.assertLessEqual(bias, MAX_BIAS)

    def test_confidence_bounded(self):
        eng = ForesightEngine()
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        sig = eng.compute_signal(actions, "stable", stats, accs)
        self.assertGreaterEqual(sig.confidence, 0.0)
        self.assertLessEqual(sig.confidence, 1.0)

    def test_apply_preserves_leader_with_large_gap(self):
        scores = {"a": 0.9, "b": 0.3, "c": 0.2}
        sig = ForesightSignal(
            action_bias={"a": -0.05, "b": 0.05},
            confidence=1.0,
            horizon=3,
            reason="test",
        )
        result = apply_foresight_bias(scores, sig)
        self.assertEqual(result["a"], 0.9)

    def test_apply_adjusts_non_leader(self):
        scores = {"a": 0.5, "b": 0.3}
        sig = ForesightSignal(
            action_bias={"b": 0.04},
            confidence=1.0,
            horizon=3,
            reason="test",
        )
        result = apply_foresight_bias(scores, sig)
        self.assertAlmostEqual(result["b"], 0.34)

    def test_apply_empty_scores_passthrough(self):
        sig = ForesightSignal(
            action_bias={"a": 0.03}, confidence=0.5, horizon=3, reason="test"
        )
        self.assertEqual(apply_foresight_bias({}, sig), {})


# ─── TestConfidence ─────────────────────────────────────────────────


class TestConfidence(unittest.TestCase):
    def test_both_signals_higher_confidence(self):
        eng = ForesightEngine()
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        r_both = eng.simulate_action("a0", "stable", stats, accs)
        r_causal = eng.simulate_action("a0", "stable", stats)
        self.assertGreaterEqual(r_both.confidence, r_causal.confidence)

    def test_no_signals_zero_confidence(self):
        eng = ForesightEngine()
        r = eng.simulate_action("a0", "stable")
        self.assertEqual(r.confidence, 0.0)


# ─── TestActionEvaluation ──────────────────────────────────────────


class TestActionEvaluation(unittest.TestCase):
    def test_better_causal_stats_get_positive_bias(self):
        eng = ForesightEngine()
        stats = {
            "stable|good": {
                "count": 15,
                "ema_reward_delta": 0.5,
                "ema_objective_delta": 0.5,
            },
            "stable|bad": {
                "count": 15,
                "ema_reward_delta": -0.3,
                "ema_objective_delta": -0.3,
            },
        }
        sig = eng.compute_signal(["good", "bad"], "stable", stats)
        if sig.action_bias:
            good_bias = sig.action_bias.get("good", 0)
            bad_bias = sig.action_bias.get("bad", 0)
            self.assertGreater(good_bias, bad_bias)

    def test_all_equal_stats_no_differentiation(self):
        eng = ForesightEngine()
        stats = {}
        for action in ["a0", "a1", "a2"]:
            stats[f"stable|{action}"] = {
                "count": 15,
                "ema_reward_delta": 0.3,
                "ema_objective_delta": 0.3,
            }
        sig = eng.compute_signal(["a0", "a1", "a2"], "stable", stats)
        self.assertIn(sig.reason, ("no_differentiation", "biases_too_small"))

    def test_rollouts_included_in_signal(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0", "a1"])
        sig = eng.compute_signal(["a0", "a1"], "stable", stats)
        self.assertGreater(len(sig.rollouts), 0)


# ─── TestNoRecursion ───────────────────────────────────────────────


class TestNoRecursion(unittest.TestCase):
    def test_simulate_is_flat_loop(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"])

        r = eng.simulate_action("a0", "stable", stats, depth=MAX_DEPTH)
        self.assertEqual(r.steps_used, MAX_DEPTH)

    def test_signal_does_not_call_itself(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0", "a1"])

        sig = eng.compute_signal(["a0", "a1"], "stable", stats)
        self.assertIsInstance(sig, ForesightSignal)


# ─── TestPipelineIntegration ────────────────────────────────────────


class TestPipelineIntegration(unittest.TestCase):
    def test_apply_additive(self):
        scores = {"a": 0.5, "b": 0.3, "c": 0.2}
        sig = ForesightSignal(
            action_bias={"b": 0.03}, confidence=1.0, horizon=3, reason="test"
        )
        result = apply_foresight_bias(scores, sig)
        self.assertAlmostEqual(result["b"], 0.33)
        self.assertAlmostEqual(result["a"], 0.5)

    def test_apply_empty_bias_passthrough(self):
        scores = {"a": 0.5}
        sig = ForesightSignal(action_bias={}, confidence=0.5, horizon=3, reason="test")
        self.assertEqual(apply_foresight_bias(scores, sig), scores)

    def test_to_dict_roundtrip(self):
        sig = ForesightSignal(
            action_bias={"a": 0.03, "b": -0.02},
            confidence=0.75,
            horizon=3,
            reason="foresight_applied",
        )
        d = sig.to_dict()
        self.assertIn("action_bias", d)
        self.assertEqual(d["horizon"], 3)
        self.assertAlmostEqual(d["confidence"], 0.75, places=3)

    def test_rollout_result_to_dict(self):
        r = RolloutResult(
            action="a0",
            expected_reward=0.123,
            expected_objective=0.456,
            trajectory_score=0.789,
            steps_used=3,
            confidence=0.5,
        )
        d = r.to_dict()
        self.assertEqual(d["action"], "a0")
        self.assertEqual(d["steps_used"], 3)


# ─── TestExtractHelpers ────────────────────────────────────────────


class TestExtractHelpers(unittest.TestCase):
    def test_extract_causal_stats(self):
        from umh.runtime_engine.causal_memory import CausalMemoryEngine

        eng = CausalMemoryEngine()
        for i in range(15):
            eng.record_transition("stable", f"a{i % 2}", 0.5 + 0.1 * i, 0.5)
        stats = extract_causal_stats(eng)
        self.assertIsNotNone(stats)
        self.assertIsInstance(stats, dict)

    def test_extract_credit_accumulators(self):
        from umh.runtime_engine.credit_assignment import CreditAssignmentEngine

        eng = CreditAssignmentEngine()
        for i in range(10):
            eng.record_step(f"a{i % 2}", "ctx", 0.5 + 0.1 * i, 0.5)
        accs = extract_credit_accumulators(eng)
        self.assertIsNotNone(accs)
        self.assertIsInstance(accs, dict)

    def test_extract_from_none_returns_none(self):
        self.assertIsNone(extract_causal_stats(None))
        self.assertIsNone(extract_credit_accumulators(None))


# ─── TestNoRegressionBaseline ──────────────────────────────────────


class TestNoRegressionBaseline(unittest.TestCase):
    def _run_scenario_signals(self, rewards):
        from umh.runtime_engine.causal_memory import CausalMemoryEngine
        from umh.runtime_engine.credit_assignment import CreditAssignmentEngine

        causal = CausalMemoryEngine()
        credit = CreditAssignmentEngine()
        for i, r in enumerate(rewards):
            action = f"a{i % 4}"
            causal.record_transition("stable", action, r, r)
            credit.record_step(action, "stable", r, r)

        eng = ForesightEngine()
        stats = extract_causal_stats(causal)
        accs = extract_credit_accumulators(credit)
        actions = [f"a{j}" for j in range(4)]
        return eng.compute_signal(actions, "stable", stats, accs)

    def test_periodic_bounded(self):
        rewards = [1.0 if i % 10 < 5 else 0.0 for i in range(40)]
        sig = self._run_scenario_signals(rewards)
        for bias in sig.action_bias.values():
            self.assertGreaterEqual(bias, -MAX_BIAS)
            self.assertLessEqual(bias, MAX_BIAS)

    def test_static_no_differentiation(self):
        rewards = [0.8] * 40
        sig = self._run_scenario_signals(rewards)
        self.assertIn(
            sig.reason,
            ("no_data", "no_differentiation", "biases_too_small", "foresight_applied"),
        )

    def test_adversarial_bounded(self):
        rewards = [1.0 if i < 20 else 0.0 for i in range(40)]
        sig = self._run_scenario_signals(rewards)
        for bias in sig.action_bias.values():
            self.assertGreaterEqual(bias, -MAX_BIAS)
            self.assertLessEqual(bias, MAX_BIAS)


# ─── TestBenchmarkIntegration ──────────────────────────────────────


class TestBenchmarkIntegration(unittest.TestCase):
    def test_no_regression_periodic(self):
        from umh.runtime_engine.long_horizon_benchmark import (
            SYSTEM_FACTORIES,
            PeriodicShiftScenario,
            run_long_horizon,
        )

        s1 = PeriodicShiftScenario(seed=42, period=200)
        s2 = PeriodicShiftScenario(seed=42, period=200)

        corrected = SYSTEM_FACTORIES["eos_corrected"]()
        substrate = SYSTEM_FACTORIES["eos_substrate"]()

        c = run_long_horizon(corrected, s1, horizon=200, seed=42)
        s = run_long_horizon(substrate, s2, horizon=200, seed=42)

        self.assertGreaterEqual(
            c.reward_metrics.avg_reward, s.reward_metrics.avg_reward
        )

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
            c.reward_metrics.avg_reward, s.reward_metrics.avg_reward
        )


# ─── TestSafetyRules ───────────────────────────────────────────────


class TestSafetyRules(unittest.TestCase):
    def test_max_depth_enforced(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"])
        r = eng.simulate_action("a0", "stable", stats, depth=100)
        self.assertLessEqual(r.steps_used, MAX_DEPTH)

    def test_no_bias_exceeds_max(self):
        eng = ForesightEngine()
        actions = ["a0", "a1", "a2"]
        stats = _make_causal_stats(actions, reward_delta=100.0)
        accs = _make_credit_accumulators(actions, reward_credit=100.0)

        sig = eng.compute_signal(actions, "stable", stats, accs)
        for bias in sig.action_bias.values():
            self.assertGreaterEqual(bias, -MAX_BIAS)
            self.assertLessEqual(bias, MAX_BIAS)

    def test_stateless_no_side_effects(self):
        eng = ForesightEngine()
        stats = _make_causal_stats(["a0"])
        eng.simulate_action("a0", "stable", stats)
        eng.simulate_action("a0", "stable", stats)
        self.assertFalse(hasattr(eng, "_state"))


if __name__ == "__main__":
    unittest.main()
