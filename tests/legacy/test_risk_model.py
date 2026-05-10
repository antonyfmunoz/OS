"""Tests for eos_ai.risk_model — counterfactual risk + irreversibility layer."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.risk_model import (
    CONFIDENCE_HIGH,
    EPSILON,
    FAILURE_RATE_FLOOR,
    IRREVERSIBILITY_BASE,
    IRREVERSIBILITY_CAUSAL_WEIGHT,
    IRREVERSIBILITY_RECOVERY_WEIGHT,
    IRREVERSIBILITY_REGIME_WEIGHT,
    IRREVERSIBILITY_TRAP_WEIGHT,
    LAMBDA_DEFAULT,
    LAMBDA_MAX,
    LAMBDA_MIN,
    MIN_OBSERVATIONS_FOR_HISTORY,
    NO_RISK_ASSESSMENT,
    RISK_BLOCK_THRESHOLD,
    VARIANCE_WORST_CASE_MULTIPLIER,
    CounterfactualEstimate,
    RiskAssessment,
    apply_risk_adjustment,
    assess_actions,
    compute_counterfactual_risk,
    select_safest_action,
    _clamp,
    _compute_irreversibility,
    _compute_lambda,
    _estimate_worst_case_reward,
)


# ─── Test data builders ──────────────────────────────────────────


def _make_causal_stats(
    actions: list[str],
    context: str = "stable",
    reward_delta: float = 0.1,
    count: int = 15,
    positive_ratio: float = 0.7,
    variance: float = 0.01,
) -> dict:
    """Build causal stats dict matching causal_memory format."""
    stats = {}
    for i, action in enumerate(actions):
        key = f"{context}|{action}"
        pos = int(count * positive_ratio)
        stats[key] = {
            "context_type": context,
            "action": action,
            "count": count,
            "ema_reward_delta": reward_delta * (1 + i * 0.5),
            "ema_objective_delta": reward_delta * (1 + i * 0.3),
            "positive_count": pos,
            "ema_variance": variance * (1 + i),
        }
    return stats


def _make_dangerous_stats(
    action: str,
    context: str = "stable",
) -> dict:
    """Stats for an action that looks okay but has high failure + variance."""
    key = f"{context}|{action}"
    return {
        key: {
            "context_type": context,
            "action": action,
            "count": 20,
            "ema_reward_delta": 0.15,
            "ema_objective_delta": 0.10,
            "positive_count": 6,
            "ema_variance": 0.25,
        }
    }


def _make_safe_stats(
    action: str,
    context: str = "stable",
) -> dict:
    """Stats for a reliable, low-variance action."""
    key = f"{context}|{action}"
    return {
        key: {
            "context_type": context,
            "action": action,
            "count": 30,
            "ema_reward_delta": 0.10,
            "ema_objective_delta": 0.08,
            "positive_count": 27,
            "ema_variance": 0.001,
        }
    }


# ─── Worst case estimation ───────────────────────────────────────


class TestWorstCaseEstimation(unittest.TestCase):
    def test_zero_variance_zero_failure_returns_expected(self) -> None:
        wc = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.0,
            failure_rate=0.0,
            historical_worst=None,
        )
        self.assertAlmostEqual(wc, 0.5)

    def test_high_variance_lowers_worst_case(self) -> None:
        low_var = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.01,
            failure_rate=0.1,
            historical_worst=None,
        )
        high_var = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.25,
            failure_rate=0.1,
            historical_worst=None,
        )
        self.assertGreater(low_var, high_var)

    def test_high_failure_rate_lowers_worst_case(self) -> None:
        low_fail = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.01,
            failure_rate=0.1,
            historical_worst=None,
        )
        high_fail = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.01,
            failure_rate=0.9,
            historical_worst=None,
        )
        self.assertGreater(low_fail, high_fail)

    def test_historical_worst_used_as_floor(self) -> None:
        wc = _estimate_worst_case_reward(
            expected_reward=0.5,
            variance=0.01,
            failure_rate=0.1,
            historical_worst=-0.5,
        )
        self.assertLess(wc, 0.5)

    def test_negative_expected_reward(self) -> None:
        wc = _estimate_worst_case_reward(
            expected_reward=-0.2,
            variance=0.05,
            failure_rate=0.3,
            historical_worst=None,
        )
        self.assertLess(wc, -0.2)


# ─── Irreversibility detection ───────────────────────────────────


class TestIrreversibility(unittest.TestCase):
    def test_base_irreversibility_with_no_signals(self) -> None:
        factor = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        self.assertAlmostEqual(factor, IRREVERSIBILITY_BASE)

    def test_recovery_history_increases_irreversibility(self) -> None:
        base = _compute_irreversibility(
            action="outreach",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        with_recovery = _compute_irreversibility(
            action="outreach",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history={"outreach": 0.8},
        )
        self.assertGreater(with_recovery, base)

    def test_regime_increases_irreversibility(self) -> None:
        without = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        with_regime = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=True,
            trap_signal_active=False,
            recovery_history=None,
        )
        self.assertGreater(with_regime, without)
        self.assertAlmostEqual(with_regime - without, IRREVERSIBILITY_REGIME_WEIGHT)

    def test_trap_increases_irreversibility(self) -> None:
        without = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        with_trap = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=True,
            recovery_history=None,
        )
        self.assertGreater(with_trap, without)

    def test_causal_failure_increases_irreversibility(self) -> None:
        stats = _make_dangerous_stats("risky_action")
        factor = _compute_irreversibility(
            action="risky_action",
            causal_stats=stats,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        self.assertGreater(factor, IRREVERSIBILITY_BASE)

    def test_all_signals_clamped_to_one(self) -> None:
        stats = _make_dangerous_stats("risky_action")
        factor = _compute_irreversibility(
            action="risky_action",
            causal_stats=stats,
            context_type="stable",
            regime_active=True,
            trap_signal_active=True,
            recovery_history={"risky_action": 1.0},
        )
        self.assertLessEqual(factor, 1.0)

    def test_irreversibility_bounded(self) -> None:
        factor = _compute_irreversibility(
            action="test",
            causal_stats=None,
            context_type="stable",
            regime_active=False,
            trap_signal_active=False,
            recovery_history=None,
        )
        self.assertGreaterEqual(factor, 0.0)
        self.assertLessEqual(factor, 1.0)


# ─── Lambda computation ─────────────────────────────────────────


class TestLambda(unittest.TestCase):
    def test_default_lambda_at_medium_uncertainty(self) -> None:
        lam = _compute_lambda(
            uncertainty=0.5,
            regime_active=False,
            trap_signal_active=False,
        )
        self.assertAlmostEqual(lam, LAMBDA_DEFAULT)

    def test_high_uncertainty_increases_lambda(self) -> None:
        low = _compute_lambda(0.2, False, False)
        high = _compute_lambda(0.9, False, False)
        self.assertGreater(high, low)

    def test_lambda_bounded(self) -> None:
        for u in [0.0, 0.5, 1.0]:
            for r in [False, True]:
                for t in [False, True]:
                    lam = _compute_lambda(u, r, t)
                    self.assertGreaterEqual(lam, LAMBDA_MIN)
                    self.assertLessEqual(lam, LAMBDA_MAX)

    def test_regime_and_trap_increase_lambda(self) -> None:
        base = _compute_lambda(0.5, False, False)
        with_regime = _compute_lambda(0.5, True, False)
        with_both = _compute_lambda(0.5, True, True)
        self.assertGreater(with_regime, base)
        self.assertGreater(with_both, with_regime)


# ─── Core risk computation ───────────────────────────────────────


class TestCounterfactualRisk(unittest.TestCase):
    def test_safe_action_has_low_risk(self) -> None:
        stats = _make_safe_stats("safe_action")
        est = compute_counterfactual_risk(
            action="safe_action",
            expected_reward=0.10,
            causal_stats=stats,
            context_type="stable",
        )
        self.assertLess(est.risk_score, 0.1)
        self.assertFalse(est.blocked)

    def test_dangerous_action_has_high_risk(self) -> None:
        stats = _make_dangerous_stats("risky_action")
        est = compute_counterfactual_risk(
            action="risky_action",
            expected_reward=0.15,
            causal_stats=stats,
            context_type="stable",
        )
        safe_stats = _make_safe_stats("safe_action")
        safe_est = compute_counterfactual_risk(
            action="safe_action",
            expected_reward=0.10,
            causal_stats=safe_stats,
            context_type="stable",
        )
        self.assertGreater(est.risk_score, safe_est.risk_score)

    def test_risk_adjusted_score_lower_than_expected(self) -> None:
        stats = _make_dangerous_stats("risky_action")
        est = compute_counterfactual_risk(
            action="risky_action",
            expected_reward=0.15,
            causal_stats=stats,
            context_type="stable",
        )
        self.assertLessEqual(est.risk_adjusted_score, est.expected_reward)

    def test_no_causal_data_uses_defaults(self) -> None:
        est = compute_counterfactual_risk(
            action="unknown",
            expected_reward=0.5,
            causal_stats=None,
            context_type="stable",
        )
        self.assertGreater(est.risk_score, 0.0)
        self.assertFalse(est.blocked)

    def test_worst_case_below_expected(self) -> None:
        stats = _make_causal_stats(["test_action"])
        est = compute_counterfactual_risk(
            action="test_action",
            expected_reward=0.1,
            causal_stats=stats,
            context_type="stable",
        )
        self.assertLessEqual(est.worst_case_reward, est.expected_reward)

    def test_reward_gap_non_negative(self) -> None:
        for reward in [-0.5, 0.0, 0.5, 1.0]:
            est = compute_counterfactual_risk(
                action="test",
                expected_reward=reward,
                causal_stats=None,
                context_type="stable",
            )
            self.assertGreaterEqual(est.reward_gap, 0.0)


# ─── Safety blocking ────────────────────────────────────────────


class TestSafetyBlocking(unittest.TestCase):
    def test_high_risk_low_confidence_blocked(self) -> None:
        stats = _make_dangerous_stats("dangerous")
        est = compute_counterfactual_risk(
            action="dangerous",
            expected_reward=2.0,
            causal_stats=stats,
            context_type="stable",
            uncertainty=0.9,
            regime_active=True,
            trap_signal_active=True,
            recovery_history={"dangerous": 1.0},
            confidence=0.1,
        )
        self.assertTrue(est.blocked)
        self.assertIn("risk_score", est.block_reason)

    def test_high_risk_high_confidence_not_blocked(self) -> None:
        stats = _make_dangerous_stats("risky")
        est = compute_counterfactual_risk(
            action="risky",
            expected_reward=2.0,
            causal_stats=stats,
            context_type="stable",
            confidence=0.9,
        )
        self.assertFalse(est.blocked)

    def test_low_risk_always_passes(self) -> None:
        stats = _make_safe_stats("safe")
        est = compute_counterfactual_risk(
            action="safe",
            expected_reward=0.1,
            causal_stats=stats,
            context_type="stable",
            confidence=0.1,
        )
        self.assertFalse(est.blocked)


# ─── Batch assessment ────────────────────────────────────────────


class TestBatchAssessment(unittest.TestCase):
    def test_empty_actions_returns_no_assessment(self) -> None:
        result = assess_actions([], {})
        self.assertIs(result, NO_RISK_ASSESSMENT)

    def test_identifies_safest_and_riskiest(self) -> None:
        safe_stats = _make_safe_stats("safe")
        dangerous_stats = _make_dangerous_stats("risky")
        combined = {**safe_stats, **dangerous_stats}

        result = assess_actions(
            actions=["safe", "risky"],
            expected_rewards={"safe": 0.10, "risky": 0.15},
            causal_stats=combined,
            context_type="stable",
        )
        self.assertEqual(result.safest_action, "safe")
        self.assertEqual(result.riskiest_action, "risky")

    def test_blocked_actions_flagged(self) -> None:
        stats = _make_dangerous_stats("dangerous")
        result = assess_actions(
            actions=["dangerous"],
            expected_rewards={"dangerous": 2.0},
            causal_stats=stats,
            context_type="stable",
            uncertainty=0.9,
            regime_active=True,
            trap_signal_active=True,
            recovery_history={"dangerous": 1.0},
            confidences={"dangerous": 0.1},
        )
        self.assertTrue(result.any_blocked)

    def test_lambda_consistent_across_batch(self) -> None:
        result = assess_actions(
            actions=["a", "b", "c"],
            expected_rewards={"a": 0.1, "b": 0.2, "c": 0.3},
            uncertainty=0.8,
        )
        self.assertGreater(result.lambda_used, LAMBDA_DEFAULT)

    def test_get_estimate_by_action(self) -> None:
        result = assess_actions(
            actions=["alpha", "beta"],
            expected_rewards={"alpha": 0.1, "beta": 0.2},
        )
        est = result.get_estimate("alpha")
        self.assertIsNotNone(est)
        self.assertEqual(est.action, "alpha")

        missing = result.get_estimate("gamma")
        self.assertIsNone(missing)


# ─── Planner integration ────────────────────────────────────────


class TestPlannerIntegration(unittest.TestCase):
    def test_apply_risk_adjustment_penalizes(self) -> None:
        scores = {"safe": 0.5, "risky": 0.6}
        safe_stats = _make_safe_stats("safe")
        dangerous_stats = _make_dangerous_stats("risky")
        combined = {**safe_stats, **dangerous_stats}

        assessment = assess_actions(
            actions=["safe", "risky"],
            expected_rewards=scores,
            causal_stats=combined,
            context_type="stable",
        )
        adjusted = apply_risk_adjustment(scores, assessment)

        self.assertLess(adjusted["risky"], scores["risky"])
        self.assertLess(adjusted["safe"], scores["safe"])
        risky_penalty = scores["risky"] - adjusted["risky"]
        safe_penalty = scores["safe"] - adjusted["safe"]
        self.assertGreater(risky_penalty, safe_penalty)

    def test_blocked_action_zeroed(self) -> None:
        scores = {"dangerous": 1.0, "safe": 0.5}
        stats = _make_dangerous_stats("dangerous")
        safe_s = _make_safe_stats("safe")
        combined = {**stats, **safe_s}

        assessment = assess_actions(
            actions=["dangerous", "safe"],
            expected_rewards={"dangerous": 2.0, "safe": 0.5},
            causal_stats=combined,
            context_type="stable",
            uncertainty=0.9,
            regime_active=True,
            trap_signal_active=True,
            recovery_history={"dangerous": 1.0},
            confidences={"dangerous": 0.1, "safe": 0.8},
        )
        adjusted = apply_risk_adjustment(scores, assessment)
        if assessment.any_blocked:
            blocked_est = assessment.get_estimate("dangerous")
            if blocked_est and blocked_est.blocked:
                self.assertEqual(adjusted["dangerous"], 0.0)

    def test_empty_assessment_returns_unchanged(self) -> None:
        scores = {"a": 0.5, "b": 0.3}
        adjusted = apply_risk_adjustment(scores, NO_RISK_ASSESSMENT)
        self.assertEqual(adjusted, scores)

    def test_select_safest_action_prefers_risk_adjusted(self) -> None:
        safe_stats = _make_safe_stats("conservative")
        dangerous_stats = _make_dangerous_stats("aggressive")
        combined = {**safe_stats, **dangerous_stats}

        scores = {"conservative": 0.4, "aggressive": 0.5}
        assessment = assess_actions(
            actions=["conservative", "aggressive"],
            expected_rewards=scores,
            causal_stats=combined,
            context_type="stable",
        )
        safest = select_safest_action(scores, assessment)
        self.assertIsNotNone(safest)

    def test_all_blocked_returns_none(self) -> None:
        stats = _make_dangerous_stats("dangerous")
        assessment = assess_actions(
            actions=["dangerous"],
            expected_rewards={"dangerous": 2.0},
            causal_stats=stats,
            context_type="stable",
            uncertainty=0.9,
            regime_active=True,
            trap_signal_active=True,
            recovery_history={"dangerous": 1.0},
            confidences={"dangerous": 0.1},
        )
        if assessment.any_blocked:
            safest = select_safest_action({"dangerous": 1.0}, assessment)
            self.assertIsNone(safest)

    def test_no_regression_with_existing_planner_scores(self) -> None:
        """Verify risk adjustment doesn't break normal action ordering.

        When all actions have similar risk profiles, the original ordering
        should be preserved after risk adjustment.
        """
        stats = _make_causal_stats(
            ["alpha", "beta", "gamma"],
            count=20,
            reward_delta=0.1,
            variance=0.01,
        )
        scores = {"alpha": 0.3, "beta": 0.5, "gamma": 0.4}
        assessment = assess_actions(
            actions=["alpha", "beta", "gamma"],
            expected_rewards=scores,
            causal_stats=stats,
            context_type="stable",
            uncertainty=0.3,
        )
        adjusted = apply_risk_adjustment(scores, assessment)

        original_order = sorted(scores, key=scores.get, reverse=True)
        adjusted_order = sorted(adjusted, key=adjusted.get, reverse=True)
        self.assertEqual(original_order, adjusted_order)


# ─── Adversarial trap avoidance ──────────────────────────────────


class TestAdversarialTrapAvoidance(unittest.TestCase):
    def test_trap_action_penalized_more(self) -> None:
        """An action with trap signal should get higher risk than without."""
        stats = _make_causal_stats(["action_a"])
        no_trap = compute_counterfactual_risk(
            action="action_a",
            expected_reward=0.3,
            causal_stats=stats,
            context_type="stable",
            trap_signal_active=False,
        )
        with_trap = compute_counterfactual_risk(
            action="action_a",
            expected_reward=0.3,
            causal_stats=stats,
            context_type="stable",
            trap_signal_active=True,
        )
        self.assertGreater(with_trap.risk_score, no_trap.risk_score)

    def test_regime_instability_increases_risk(self) -> None:
        stats = _make_causal_stats(["action_a"])
        stable = compute_counterfactual_risk(
            action="action_a",
            expected_reward=0.3,
            causal_stats=stats,
            context_type="stable",
            regime_active=False,
        )
        unstable = compute_counterfactual_risk(
            action="action_a",
            expected_reward=0.3,
            causal_stats=stats,
            context_type="stable",
            regime_active=True,
        )
        self.assertGreater(unstable.risk_score, stable.risk_score)

    def test_high_uncertainty_conservative_selection(self) -> None:
        """Under high uncertainty, prefer the safer action."""
        safe_stats = _make_safe_stats("conservative")
        dangerous_stats = _make_dangerous_stats("aggressive")
        combined = {**safe_stats, **dangerous_stats}

        assessment = assess_actions(
            actions=["conservative", "aggressive"],
            expected_rewards={"conservative": 0.10, "aggressive": 0.15},
            causal_stats=combined,
            context_type="stable",
            uncertainty=0.9,
        )

        conservative_est = assessment.get_estimate("conservative")
        aggressive_est = assessment.get_estimate("aggressive")
        self.assertIsNotNone(conservative_est)
        self.assertIsNotNone(aggressive_est)

        self.assertGreater(
            conservative_est.risk_adjusted_score,
            aggressive_est.risk_adjusted_score,
        )


# ─── Serialization ───────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_estimate_to_dict_round_trips(self) -> None:
        est = compute_counterfactual_risk(
            action="test",
            expected_reward=0.5,
            causal_stats=None,
            context_type="stable",
        )
        d = est.to_dict()
        self.assertIn("risk_score", d)
        self.assertIn(
            "worst_case_estimate"
            if "worst_case_estimate" in d
            else "worst_case_reward",
            d,
        )
        self.assertIn("irreversibility_factor", d)
        self.assertIn("risk_adjusted_score", d)
        self.assertEqual(d["action"], "test")

    def test_assessment_to_dict(self) -> None:
        result = assess_actions(
            actions=["a", "b"],
            expected_rewards={"a": 0.1, "b": 0.2},
        )
        d = result.to_dict()
        self.assertIn("estimates", d)
        self.assertIn("lambda_used", d)
        self.assertEqual(len(d["estimates"]), 2)


# ─── Determinism ─────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_outputs(self) -> None:
        """Risk computation must be deterministic — no randomness."""
        stats = _make_causal_stats(["a", "b", "c"])
        rewards = {"a": 0.1, "b": 0.2, "c": 0.3}

        results = []
        for _ in range(5):
            r = assess_actions(
                actions=["a", "b", "c"],
                expected_rewards=rewards,
                causal_stats=stats,
                context_type="stable",
                uncertainty=0.5,
            )
            results.append(r.to_dict())

        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])


if __name__ == "__main__":
    unittest.main()
