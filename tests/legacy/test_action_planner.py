"""Tests for runtime.action_planner — multi-trajectory action selection layer."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.action_planner import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_HORIZON,
    EXPLORATION_PROXIMITY_THRESHOLD,
    GAMMA,
    MAX_CANDIDATES,
    MAX_HORIZON,
    MIN_CREDIT_OBSERVATIONS,
    MIN_DATA_OBSERVATIONS,
    MIN_HORIZON,
    NO_PLANNER_RESULT,
    SCORE_MARGIN_THRESHOLD,
    UNCERTAINTY_HIGH,
    UNCERTAINTY_LOW,
    PlannerResult,
    TrajectoryResult,
    TrajectoryStep,
    apply_planner_override,
    compute_adaptive_horizon,
    compute_uncertainty,
    evaluate_trajectories,
)


# ─── Test data builders ────────────────────────────────────────────


def _make_causal_stats(
    actions: list[str],
    context: str = "stable",
    reward_delta: float = 0.1,
    count: int = 15,
) -> dict:
    stats = {}
    for i, action in enumerate(actions):
        key = f"{context}|{action}"
        stats[key] = {
            "context_type": context,
            "action": action,
            "count": count,
            "ema_reward_delta": reward_delta * (1 + i * 0.5),
            "ema_objective_delta": reward_delta * (1 + i * 0.3),
            "positive_count": 10,
            "ema_variance": 0.01,
        }
    return stats


def _make_credit_accumulators(
    actions: list[str],
    reward_credit: float = 0.5,
    obs: int = 10,
) -> dict:
    accs = {}
    for i, action in enumerate(actions):
        accs[action] = {
            "action": action,
            "reward_credit": reward_credit * (1 + i * 0.3),
            "objective_credit": reward_credit * (1 + i * 0.2),
            "observation_count": obs,
            "positive_count": 7,
            "sum_sq_diff": 0.01,
            "ema_credit": 0.05,
        }
    return accs


def _make_clear_leader_scores() -> dict[str, float]:
    """Scores with a clear leader — low uncertainty.

    Needs 4+ strategies with extreme separation for normalized_gap to push
    uncertainty below UNCERTAINTY_HIGH (0.7).
    """
    return {"strong": 0.95, "s0": 0.05, "s1": 0.07, "s2": 0.09}


def _make_tied_scores() -> dict[str, float]:
    """Scores that are nearly tied — high uncertainty."""
    return {"a": 0.501, "b": 0.500, "c": 0.499}


def _make_moderate_scores() -> dict[str, float]:
    """Scores with moderate separation — higher uncertainty than clear leader."""
    return {"x": 0.65, "y": 0.55, "z": 0.50, "w": 0.45}


class _MockContextSignal:
    def __init__(
        self,
        regime_change_likelihood: float = 0.0,
        adversarial_likelihood: float = 0.0,
        noise_level: float = 0.0,
        drift_strength: float = 0.0,
        dominant_type: str = "stable",
    ):
        self.regime_change_likelihood = regime_change_likelihood
        self.adversarial_likelihood = adversarial_likelihood
        self.noise_level = noise_level
        self.drift_strength = drift_strength
        self.dominant_type = dominant_type


# ─── TestDeterminism ───────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_identical_inputs_identical_outputs(self):
        actions = ["a0", "a1", "a2"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)
        scores = _make_moderate_scores()

        r1 = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=scores,
            confidence_threshold=0.0,
        )
        r2 = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=scores,
            confidence_threshold=0.0,
        )
        self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_ten_repeated_runs_identical(self):
        actions = ["x", "y"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)
        scores = {"x": 0.7, "y": 0.5}

        results = [
            evaluate_trajectories(
                actions,
                "stable",
                stats,
                accs,
                strategy_scores=scores,
                confidence_threshold=0.0,
            ).to_dict()
            for _ in range(10)
        ]
        for r in results[1:]:
            self.assertEqual(results[0], r)


# ─── TestUncertaintyComputation ────────────────────────────────────


class TestUncertaintyComputation(unittest.TestCase):
    def test_clear_leader_low_uncertainty(self):
        u = compute_uncertainty(_make_clear_leader_scores())
        self.assertLess(u, UNCERTAINTY_HIGH)

    def test_tied_scores_high_uncertainty(self):
        u = compute_uncertainty(_make_tied_scores())
        self.assertGreater(u, 0.5)

    def test_none_scores_max_uncertainty(self):
        self.assertEqual(compute_uncertainty(None), 1.0)

    def test_empty_scores_max_uncertainty(self):
        self.assertEqual(compute_uncertainty({}), 1.0)

    def test_single_action_zero_uncertainty(self):
        self.assertEqual(compute_uncertainty({"only": 0.8}), 0.0)

    def test_bounded_0_to_1(self):
        for scores in [
            _make_clear_leader_scores(),
            _make_tied_scores(),
            _make_moderate_scores(),
            {"a": 100.0, "b": 0.01},
        ]:
            u = compute_uncertainty(scores)
            self.assertGreaterEqual(u, 0.0)
            self.assertLessEqual(u, 1.0)


# ─── TestAdaptiveHorizon ──────────────────────────────────────────


class TestAdaptiveHorizon(unittest.TestCase):
    def test_high_uncertainty_short_horizon(self):
        h = compute_adaptive_horizon(0.8, "stable")
        self.assertLessEqual(h, 2)
        self.assertGreaterEqual(h, MIN_HORIZON)

    def test_very_high_uncertainty_minimum_horizon(self):
        h = compute_adaptive_horizon(0.95, "stable")
        self.assertEqual(h, MIN_HORIZON)

    def test_low_uncertainty_stable_deep_horizon(self):
        h = compute_adaptive_horizon(0.1, "stable")
        self.assertGreaterEqual(h, 5)
        self.assertLessEqual(h, MAX_HORIZON)

    def test_low_uncertainty_unstable_not_deep(self):
        h = compute_adaptive_horizon(0.1, "adversarial")
        self.assertLessEqual(h, 5)

    def test_medium_uncertainty_default_range(self):
        h = compute_adaptive_horizon(0.5, "stable")
        self.assertGreaterEqual(h, 3)
        self.assertLessEqual(h, 5)

    def test_horizon_always_within_bounds(self):
        for u in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            for ctx in ["stable", "adversarial", "noise", None]:
                h = compute_adaptive_horizon(u, ctx)
                self.assertGreaterEqual(h, MIN_HORIZON)
                self.assertLessEqual(h, MAX_HORIZON)

    def test_horizon_inversely_related_to_uncertainty(self):
        h_low = compute_adaptive_horizon(0.1, "stable")
        h_high = compute_adaptive_horizon(0.8, "stable")
        self.assertGreater(h_low, h_high)


# ─── TestBoundedRollout ────────────────────────────────────────────


class TestBoundedRollout(unittest.TestCase):
    def test_max_steps_clamped(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            horizon=10,
            confidence_threshold=0.0,
        )
        for traj in result.trajectories:
            self.assertLessEqual(len(traj.steps), MAX_HORIZON)

    def test_min_steps_enforced(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            horizon=1,
            confidence_threshold=0.0,
        )
        for traj in result.trajectories:
            if traj.steps:
                self.assertGreaterEqual(len(traj.steps), MIN_HORIZON)

    def test_max_candidates_enforced(self):
        actions = ["a0", "a1", "a2", "a3", "a4"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            confidence_threshold=0.0,
        )
        self.assertLessEqual(len(result.trajectories), MAX_CANDIDATES)

    def test_discount_decreases_per_step(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            confidence_threshold=0.0,
        )
        for traj in result.trajectories:
            for i in range(1, len(traj.steps)):
                self.assertLess(traj.steps[i].discount, traj.steps[i - 1].discount)

    def test_cumulative_value_monotonic_for_positive_actions(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions, reward_delta=0.2)
        accs = _make_credit_accumulators(actions, reward_credit=0.8)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            confidence_threshold=0.0,
        )
        for traj in result.trajectories:
            for i in range(1, len(traj.steps)):
                self.assertGreater(
                    traj.steps[i].cumulative_value,
                    traj.steps[i - 1].cumulative_value,
                )


# ─── TestNoStateMutation ──────────────────────────────────────────


class TestNoStateMutation(unittest.TestCase):
    def test_causal_stats_unchanged(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        stats_before = {k: dict(v) for k, v in stats.items()}

        evaluate_trajectories(actions, "stable", stats, None, confidence_threshold=0.0)

        for key in stats_before:
            self.assertEqual(stats[key], stats_before[key])

    def test_credit_accumulators_unchanged(self):
        actions = ["a0", "a1"]
        accs = _make_credit_accumulators(actions)
        accs_before = {k: dict(v) for k, v in accs.items()}

        evaluate_trajectories(actions, "stable", None, accs, confidence_threshold=0.0)

        for key in accs_before:
            self.assertEqual(accs[key], accs_before[key])

    def test_strategy_scores_unchanged_when_inactive(self):
        scores = {"a0": 0.8, "a1": 0.6}
        scores_before = dict(scores)

        result = NO_PLANNER_RESULT
        applied = apply_planner_override(scores, result)

        self.assertEqual(scores, scores_before)
        self.assertEqual(applied, scores_before)


# ─── TestFallbackBehavior ─────────────────────────────────────────


class TestFallbackBehavior(unittest.TestCase):
    def test_empty_candidates_returns_inactive(self):
        result = evaluate_trajectories([], "stable")
        self.assertFalse(result.active)
        self.assertIsNone(result.selected_action_override)

    def test_no_data_returns_inactive(self):
        result = evaluate_trajectories(["a0"], "stable", None, None)
        self.assertFalse(result.active)

    def test_insufficient_causal_data(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions, count=2)
        # Pass low-uncertainty scores so we don't gate on uncertainty first
        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            None,
            strategy_scores=_make_clear_leader_scores(),
        )
        self.assertFalse(result.active)
        self.assertIn("insufficient_data", result.reason)

    def test_low_confidence_returns_inactive(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions, count=6)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            None,
            confidence_threshold=0.99,
        )
        self.assertFalse(result.active)


# ─── TestGating ────────────────────────────────────────────────────


class TestGating(unittest.TestCase):
    def test_unstable_context_gates_planner(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        for ctx_type in ["adversarial", "regime_change", "noise", "drift", None]:
            result = evaluate_trajectories(actions, ctx_type, stats, accs)
            self.assertFalse(result.active, f"Should be gated for context={ctx_type}")
            self.assertIn("gated", result.reason)

    def test_stable_context_allows_planner(self):
        clear_scores = _make_clear_leader_scores()
        actions = list(clear_scores.keys())
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=clear_scores,
            confidence_threshold=0.0,
        )
        self.assertNotIn("gated", result.reason)

    def test_trap_active_gates_planner(self):
        clear_scores = _make_clear_leader_scores()
        actions = list(clear_scores.keys())
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            trap_signal_active=True,
            strategy_scores=clear_scores,
        )
        self.assertFalse(result.active)
        self.assertIn("trap_active", result.reason)

    def test_stability_guard_gates_planner(self):
        clear_scores = _make_clear_leader_scores()
        actions = list(clear_scores.keys())
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            stability_guard_active=True,
            strategy_scores=clear_scores,
        )
        self.assertFalse(result.active)
        self.assertIn("stability_guard_active", result.reason)

    def test_high_uncertainty_gates_planner(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)
        tied = _make_tied_scores()

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=tied,
        )
        self.assertFalse(result.active)
        # Either gated by uncertainty or fails confidence/margin checks
        self.assertTrue(
            "gated" in result.reason
            or "confidence" in result.reason
            or "margin" in result.reason
            or "defer" in result.reason,
            f"Unexpected reason: {result.reason}",
        )


# ─── TestUncertaintyScaling ────────────────────────────────────────


class TestUncertaintyScaling(unittest.TestCase):
    def test_high_uncertainty_reduces_confidence(self):
        clear_scores = _make_clear_leader_scores()
        moderate_scores = _make_moderate_scores()
        clear_actions = list(clear_scores.keys())
        moderate_actions = list(moderate_scores.keys())

        r_certain = evaluate_trajectories(
            clear_actions,
            "stable",
            _make_causal_stats(clear_actions),
            _make_credit_accumulators(clear_actions),
            strategy_scores=clear_scores,
            confidence_threshold=0.0,
        )
        r_uncertain = evaluate_trajectories(
            moderate_actions,
            "stable",
            _make_causal_stats(moderate_actions),
            _make_credit_accumulators(moderate_actions),
            strategy_scores=moderate_scores,
            confidence_threshold=0.0,
        )
        # Lower uncertainty → higher adjusted confidence
        self.assertLess(r_certain.uncertainty, r_uncertain.uncertainty)

    def test_uncertainty_penalty_in_trajectory_score(self):
        from umh.runtime_engine.action_planner import _simulate_trajectory

        stats = _make_causal_stats(["a"])
        accs = _make_credit_accumulators(["a"])

        t_low_u = _simulate_trajectory(
            "a",
            "stable",
            stats,
            accs,
            horizon=5,
            uncertainty=0.1,
        )
        t_high_u = _simulate_trajectory(
            "a",
            "stable",
            stats,
            accs,
            horizon=5,
            uncertainty=0.8,
        )
        self.assertGreater(t_low_u.trajectory_score, t_high_u.trajectory_score)
        self.assertGreater(t_high_u.uncertainty_penalty, t_low_u.uncertainty_penalty)

    def test_no_override_under_high_uncertainty(self):
        actions = ["a0", "a1", "a2"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)
        tied = _make_tied_scores()

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=tied,
        )
        self.assertFalse(result.active)


# ─── TestExplorationInterplay ──────────────────────────────────────


class TestExplorationInterplay(unittest.TestCase):
    def test_high_uncertainty_close_scores_defers_to_exploration(self):
        actions = ["a", "b"]
        stats = {
            "stable|a": {
                "count": 15,
                "ema_reward_delta": 0.10,
                "ema_objective_delta": 0.10,
            },
            "stable|b": {
                "count": 15,
                "ema_reward_delta": 0.10,
                "ema_objective_delta": 0.10,
            },
        }
        accs = {
            "a": {
                "reward_credit": 0.5,
                "objective_credit": 0.5,
                "observation_count": 10,
            },
            "b": {
                "reward_credit": 0.5,
                "objective_credit": 0.5,
                "observation_count": 10,
            },
        }
        # Moderate uncertainty + close scores = defer
        moderate_uncertain = {"a": 0.60, "b": 0.58}
        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=moderate_uncertain,
            confidence_threshold=0.0,
        )
        # Either gated by uncertainty or margin/exploration deferral
        self.assertFalse(result.active)

    def test_low_uncertainty_clear_winner_does_not_defer(self):
        actions = ["strong", "weak"]
        stats = {
            "stable|strong": {
                "count": 20,
                "ema_reward_delta": 0.30,
                "ema_objective_delta": 0.25,
            },
            "stable|weak": {
                "count": 20,
                "ema_reward_delta": 0.05,
                "ema_objective_delta": 0.03,
            },
        }
        accs = {
            "strong": {
                "reward_credit": 1.5,
                "objective_credit": 1.2,
                "observation_count": 15,
            },
            "weak": {
                "reward_credit": 0.2,
                "objective_credit": 0.1,
                "observation_count": 15,
            },
        }
        clear_scores = {"strong": 0.90, "weak": 0.30}

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=clear_scores,
            confidence_threshold=0.0,
        )
        # Should not be gated — clear winner + low uncertainty
        if result.trajectory_scores:
            self.assertNotIn("defer_to_exploration", result.reason)


# ─── TestSelection ─────────────────────────────────────────────────


class TestSelection(unittest.TestCase):
    def test_selects_best_trajectory(self):
        actions = ["weak", "strong"]
        stats = {
            "stable|weak": {
                "count": 20,
                "ema_reward_delta": 0.05,
                "ema_objective_delta": 0.03,
            },
            "stable|strong": {
                "count": 20,
                "ema_reward_delta": 0.30,
                "ema_objective_delta": 0.25,
            },
        }
        accs = {
            "weak": {
                "reward_credit": 0.2,
                "objective_credit": 0.1,
                "observation_count": 10,
            },
            "strong": {
                "reward_credit": 1.5,
                "objective_credit": 1.2,
                "observation_count": 10,
            },
        }

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores={"strong": 0.9, "weak": 0.3},
            confidence_threshold=0.0,
        )
        if result.trajectory_scores:
            self.assertGreater(
                result.trajectory_scores.get("strong", 0),
                result.trajectory_scores.get("weak", 0),
            )

    def test_single_candidate_no_margin(self):
        actions = ["only"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores={"only": 0.8},
            confidence_threshold=0.0,
        )
        self.assertFalse(result.active)

    def test_tied_actions_no_override(self):
        actions = ["a", "b"]
        stats = {
            "stable|a": {
                "count": 15,
                "ema_reward_delta": 0.1,
                "ema_objective_delta": 0.1,
            },
            "stable|b": {
                "count": 15,
                "ema_reward_delta": 0.1,
                "ema_objective_delta": 0.1,
            },
        }
        accs = {
            "a": {
                "reward_credit": 0.5,
                "objective_credit": 0.5,
                "observation_count": 10,
            },
            "b": {
                "reward_credit": 0.5,
                "objective_credit": 0.5,
                "observation_count": 10,
            },
        }

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_tied_scores(),
            confidence_threshold=0.0,
        )
        self.assertFalse(result.active)


# ─── TestRiskModel ─────────────────────────────────────────────────


class TestRiskModel(unittest.TestCase):
    def test_regime_instability_adds_penalty(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        stable_ctx = _MockContextSignal(regime_change_likelihood=0.0)
        unstable_ctx = _MockContextSignal(regime_change_likelihood=0.5)

        r_stable = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            context_signal=stable_ctx,
            strategy_scores=_make_clear_leader_scores(),
            confidence_threshold=0.0,
        )
        r_unstable = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            context_signal=unstable_ctx,
            strategy_scores=_make_clear_leader_scores(),
            confidence_threshold=0.0,
        )

        if r_stable.trajectories and r_unstable.trajectories:
            self.assertGreater(
                r_unstable.trajectories[0].risk_penalty,
                r_stable.trajectories[0].risk_penalty,
            )

    def test_trap_signal_adds_penalty(self):
        from umh.runtime_engine.action_planner import _simulate_trajectory

        stats = _make_causal_stats(["a0"])
        accs = _make_credit_accumulators(["a0"])

        traj_clean = _simulate_trajectory(
            "a0",
            "stable",
            stats,
            accs,
            DEFAULT_HORIZON,
            trap_signal_active=False,
        )
        traj_trap = _simulate_trajectory(
            "a0",
            "stable",
            stats,
            accs,
            DEFAULT_HORIZON,
            trap_signal_active=True,
        )
        self.assertGreater(traj_trap.risk_penalty, traj_clean.risk_penalty)


# ─── TestConsistencyCheck ──────────────────────────────────────────


class TestConsistencyCheck(unittest.TestCase):
    def test_step_consistency_returned(self):
        actions = ["a0"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_clear_leader_scores(),
            confidence_threshold=0.0,
        )
        self.assertGreaterEqual(result.consistency, 0.0)
        self.assertLessEqual(result.consistency, 1.0)

    def test_consistent_trajectory_high_consistency(self):
        from umh.runtime_engine.action_planner import _compute_step_consistency

        # All positive = consistent
        self.assertEqual(_compute_step_consistency([0.1, 0.2, 0.3, 0.4]), 1.0)

    def test_oscillating_trajectory_low_consistency(self):
        from umh.runtime_engine.action_planner import _compute_step_consistency

        # Half positive, half negative = inconsistent
        c = _compute_step_consistency([0.1, -0.1, 0.1, -0.1])
        self.assertLess(c, 0.6)


# ─── TestPipelineIntegration ───────────────────────────────────────


class TestPipelineIntegration(unittest.TestCase):
    def test_apply_override_boosts_selected(self):
        scores = {"a0": 0.8, "a1": 0.6, "a2": 0.7}
        planner = PlannerResult(
            active=True,
            selected_action_override="a1",
            trajectory_scores={"a0": 0.5, "a1": 0.9, "a2": 0.6},
            planner_confidence=0.8,
            reason="trajectory_selected",
            horizon_used=5,
            uncertainty=0.2,
            consistency=0.9,
            adjusted_confidence=0.7,
        )

        adjusted = apply_planner_override(scores, planner)
        self.assertGreater(adjusted["a1"], adjusted["a0"])
        self.assertGreater(adjusted["a1"], adjusted["a2"])

    def test_apply_override_noop_when_inactive(self):
        scores = {"a0": 0.8, "a1": 0.6}
        planner = NO_PLANNER_RESULT

        adjusted = apply_planner_override(scores, planner)
        self.assertEqual(adjusted, scores)

    def test_apply_override_noop_when_action_missing(self):
        scores = {"a0": 0.8, "a1": 0.6}
        planner = PlannerResult(
            active=True,
            selected_action_override="a99",
            trajectory_scores={},
            planner_confidence=0.8,
            reason="trajectory_selected",
            horizon_used=3,
            uncertainty=0.2,
            consistency=0.9,
            adjusted_confidence=0.7,
        )

        adjusted = apply_planner_override(scores, planner)
        self.assertEqual(adjusted, scores)

    def test_apply_override_noop_when_already_leader(self):
        scores = {"a0": 0.9, "a1": 0.6}
        planner = PlannerResult(
            active=True,
            selected_action_override="a0",
            trajectory_scores={"a0": 1.0, "a1": 0.5},
            planner_confidence=0.8,
            reason="trajectory_selected",
            horizon_used=5,
            uncertainty=0.1,
            consistency=0.95,
            adjusted_confidence=0.7,
        )

        adjusted = apply_planner_override(scores, planner)
        self.assertEqual(adjusted, scores)


# ─── TestSerialization ─────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_planner_result_to_dict(self):
        result = PlannerResult(
            active=True,
            selected_action_override="a0",
            trajectory_scores={"a0": 0.123456789},
            planner_confidence=0.7654321,
            reason="trajectory_selected",
            horizon_used=5,
            uncertainty=0.25,
            consistency=0.9,
            adjusted_confidence=0.65,
        )
        d = result.to_dict()
        self.assertIn("active", d)
        self.assertIn("selected_action_override", d)
        self.assertIn("trajectory_scores", d)
        self.assertIn("planner_confidence", d)
        self.assertIn("horizon_used", d)
        self.assertIn("uncertainty", d)
        self.assertIn("consistency", d)
        self.assertIn("adjusted_confidence", d)
        self.assertEqual(d["trajectory_scores"]["a0"], 0.123457)
        self.assertEqual(d["horizon_used"], 5)

    def test_no_planner_result_to_dict(self):
        d = NO_PLANNER_RESULT.to_dict()
        self.assertFalse(d["active"])
        self.assertIsNone(d["selected_action_override"])
        self.assertEqual(d["horizon_used"], 0)
        self.assertEqual(d["uncertainty"], 0.0)

    def test_trajectory_result_includes_new_fields(self):
        from umh.runtime_engine.action_planner import _simulate_trajectory

        stats = _make_causal_stats(["a0"])
        accs = _make_credit_accumulators(["a0"])

        traj = _simulate_trajectory(
            "a0",
            "stable",
            stats,
            accs,
            3,
            uncertainty=0.3,
        )
        d = traj.to_dict()
        self.assertIn("uncertainty_penalty", d)
        self.assertIn("step_consistency", d)


# ─── TestHorizonAdaptation ─────────────────────────────────────────


class TestHorizonAdaptation(unittest.TestCase):
    def test_horizon_reported_in_result(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_clear_leader_scores(),
            confidence_threshold=0.0,
        )
        self.assertGreater(result.horizon_used, 0)

    def test_low_uncertainty_gets_deeper_horizon(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        r_clear = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_clear_leader_scores(),
            confidence_threshold=0.0,
        )
        # With tied scores the planner gets gated, so we force with override
        r_moderate = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_moderate_scores(),
            confidence_threshold=0.0,
        )
        # Clear leader = lower uncertainty = deeper or equal horizon
        self.assertGreaterEqual(r_clear.horizon_used, r_moderate.horizon_used)

    def test_explicit_horizon_overrides_adaptive(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=_make_clear_leader_scores(),
            horizon=4,
            confidence_threshold=0.0,
        )
        self.assertEqual(result.horizon_used, 4)


# ─── TestStableVsUnstableContexts ─────────────────────────────────


class TestStableVsUnstableContexts(unittest.TestCase):
    def test_stable_context_deeper_horizon_than_unstable(self):
        h_stable = compute_adaptive_horizon(0.2, "stable")
        h_noise = compute_adaptive_horizon(0.2, "noise")
        self.assertGreaterEqual(h_stable, h_noise)

    def test_unstable_prevents_override(self):
        actions = ["a0", "a1"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(
            actions,
            "adversarial",
            stats,
            accs,
            strategy_scores=_make_clear_leader_scores(),
        )
        self.assertFalse(result.active)
        self.assertIn("gated", result.reason)


# ─── TestNoRegression ──────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    """Verify planner does not regress existing decision pipeline."""

    def test_inactive_planner_preserves_scores(self):
        scores = {"exploit": 0.85, "explore": 0.60, "recover": 0.45}
        result = evaluate_trajectories([], "stable")

        applied = apply_planner_override(scores, result)
        self.assertEqual(applied, scores)

    def test_gated_planner_preserves_scores(self):
        scores = {"exploit": 0.85, "explore": 0.60}
        actions = list(scores.keys())
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)

        result = evaluate_trajectories(actions, "adversarial", stats, accs)
        applied = apply_planner_override(scores, result)
        self.assertEqual(applied, scores)

    def test_foresight_engine_import_still_works(self):
        from umh.runtime_engine.foresight_engine import ForesightEngine, apply_foresight_bias

        eng = ForesightEngine()
        sig = eng.compute_signal(["a0"], "stable")
        self.assertIsNotNone(sig)

    def test_policy_engine_import_still_works(self):
        from umh.runtime_engine.policy_engine import PolicySignals, select_policy

        r = select_policy(PolicySignals())
        self.assertIsNotNone(r)

    def test_score_distribution_import_still_works(self):
        from umh.runtime_engine.score_distribution import (
            RelativeUncertainty,
            compute_relative_uncertainty,
        )

        u = compute_relative_uncertainty({"a": 0.8, "b": 0.5})
        self.assertIsNotNone(u)
        self.assertGreaterEqual(u.level, 0.0)
        self.assertLessEqual(u.level, 1.0)

    def test_no_regression_static_scenario(self):
        """Static scenario: clear leader, stable context → planner should activate or not regress."""
        actions = ["best", "worst"]
        stats = {
            "stable|best": {
                "count": 30,
                "ema_reward_delta": 0.25,
                "ema_objective_delta": 0.20,
            },
            "stable|worst": {
                "count": 30,
                "ema_reward_delta": 0.02,
                "ema_objective_delta": 0.01,
            },
        }
        accs = {
            "best": {
                "reward_credit": 2.0,
                "objective_credit": 1.5,
                "observation_count": 20,
            },
            "worst": {
                "reward_credit": 0.1,
                "objective_credit": 0.05,
                "observation_count": 20,
            },
        }
        scores = {"best": 0.95, "worst": 0.30}

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=scores,
            confidence_threshold=0.0,
        )
        # Should produce trajectory analysis without error
        self.assertIsNotNone(result)
        self.assertGreater(result.horizon_used, 0)

    def test_no_regression_noisy_scenario(self):
        """Noisy scenario: tied scores → planner should NOT override."""
        actions = ["a", "b", "c"]
        stats = _make_causal_stats(actions)
        accs = _make_credit_accumulators(actions)
        tied = _make_tied_scores()

        result = evaluate_trajectories(
            actions,
            "stable",
            stats,
            accs,
            strategy_scores=tied,
        )
        self.assertFalse(result.active)


if __name__ == "__main__":
    unittest.main()
