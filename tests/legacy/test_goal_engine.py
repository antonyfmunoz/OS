"""Tests for runtime.goal_engine — goal formation + self-directed optimization."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.goals.engine import (
    CORRELATION_MIN_SAMPLES,
    DEFAULT_WEIGHTS,
    DIMENSIONS,
    EMA_ALPHA,
    EPSILON,
    INSTABILITY_STREAK_THRESHOLD,
    MAX_ADJUSTMENT_RATIO,
    MIN_HISTORY,
    NO_ADAPTATION,
    PLATEAU_VARIANCE_THRESHOLD,
    PLATEAU_WINDOW,
    RISK_SPIKE_THRESHOLD,
    GoalAdaptationResult,
    GoalEngineState,
    GoalWeightAdjustment,
    apply_adapted_weights,
    compute_weight_adjustments,
    _compute_dimension_correlation,
    _compute_regret,
    _detect_regime,
    _normalize_weights,
    _regime_pressure,
)


# ─── Test data builders ──────────────────────────────────────────


def _flat_rewards(n: int = 20, value: float = 0.5) -> list[float]:
    return [value] * n


def _improving_rewards(n: int = 20) -> list[float]:
    return [0.3 + 0.02 * i for i in range(n)]


def _degrading_rewards(n: int = 20) -> list[float]:
    return [0.7 - 0.02 * i for i in range(n)]


def _make_component_history(
    n: int = 20,
    correlated_dim: str | None = None,
    rewards: list[float] | None = None,
) -> dict[str, list[float]]:
    """Build component history. Optionally correlate one dim with rewards."""
    history: dict[str, list[float]] = {}
    for dim in DIMENSIONS:
        if dim == correlated_dim and rewards:
            history[dim] = list(rewards[-n:])
        else:
            history[dim] = [0.5] * n
    return history


def _make_anticorrelated_history(
    n: int = 20,
    dim: str = "stability",
    rewards: list[float] | None = None,
) -> dict[str, list[float]]:
    """One dimension anti-correlated with reward."""
    if rewards is None:
        rewards = _improving_rewards(n)
    history: dict[str, list[float]] = {}
    for d in DIMENSIONS:
        if d == dim:
            history[d] = [1.0 - r for r in rewards[-n:]]
        else:
            history[d] = [0.5] * n
    return history


# ─── Normalization ───────────────────────────────────────────────


class TestNormalization(unittest.TestCase):
    def test_weights_sum_to_one(self) -> None:
        weights = {"a": 0.3, "b": 0.5, "c": 0.2}
        normed = _normalize_weights(weights)
        self.assertAlmostEqual(sum(normed.values()), 1.0)

    def test_zero_weights_return_defaults(self) -> None:
        weights = {"a": 0.0, "b": 0.0}
        normed = _normalize_weights(weights)
        self.assertEqual(normed, DEFAULT_WEIGHTS)

    def test_preserves_proportions(self) -> None:
        weights = {"a": 2.0, "b": 1.0}
        normed = _normalize_weights(weights)
        self.assertAlmostEqual(normed["a"] / normed["b"], 2.0)


# ─── Regime detection ────────────────────────────────────────────


class TestRegimeDetection(unittest.TestCase):
    def test_stable_default(self) -> None:
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.5, 0.6, 0.55, 0.6],
            risk_level=0.0,
        )
        self.assertEqual(regime, "stable")

    def test_unstable_on_failure_streak(self) -> None:
        regime = _detect_regime(
            failure_streak=INSTABILITY_STREAK_THRESHOLD,
            regime_active=False,
            regime_strength=0.0,
            reward_history=_flat_rewards(),
            risk_level=0.0,
        )
        self.assertEqual(regime, "unstable")

    def test_risk_spike(self) -> None:
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=_flat_rewards(),
            risk_level=RISK_SPIKE_THRESHOLD,
        )
        self.assertEqual(regime, "risk_spike")

    def test_plateau_from_regime_engine(self) -> None:
        regime = _detect_regime(
            failure_streak=0,
            regime_active=True,
            regime_strength=0.5,
            reward_history=_flat_rewards(),
            risk_level=0.0,
        )
        self.assertEqual(regime, "plateau")

    def test_plateau_from_flat_rewards(self) -> None:
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=_flat_rewards(PLATEAU_WINDOW + 5),
            risk_level=0.0,
        )
        self.assertEqual(regime, "plateau")

    def test_recovery_on_improving_streak(self) -> None:
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.3, 0.4, 0.5, 0.6],
            risk_level=0.0,
        )
        self.assertEqual(regime, "recovery")


# ─── Regime pressure ─────────────────────────────────────────────


class TestRegimePressure(unittest.TestCase):
    def test_unstable_boosts_stability(self) -> None:
        p = _regime_pressure("unstable")
        self.assertGreater(p["stability"], 0.0)
        self.assertLess(p["goal_progress"], 0.0)

    def test_plateau_boosts_goal_progress(self) -> None:
        p = _regime_pressure("plateau")
        self.assertGreater(p["goal_progress"], 0.0)

    def test_risk_spike_boosts_stability_and_confidence(self) -> None:
        p = _regime_pressure("risk_spike")
        self.assertGreater(p["stability"], 0.0)
        self.assertGreater(p["confidence"], 0.0)

    def test_stable_has_zero_pressure(self) -> None:
        p = _regime_pressure("stable")
        self.assertTrue(all(v == 0.0 for v in p.values()))


# ─── Correlation ─────────────────────────────────────────────────


class TestDimensionCorrelation(unittest.TestCase):
    def test_correlated_dimension_positive(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        corr = _compute_dimension_correlation(components, rewards)
        self.assertGreater(corr.get("goal_progress", 0.0), 0.3)

    def test_anticorrelated_dimension_negative(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_anticorrelated_history(20, "stability", rewards)
        corr = _compute_dimension_correlation(components, rewards)
        self.assertLess(corr.get("stability", 0.0), -0.3)

    def test_flat_dimension_near_zero(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20)
        corr = _compute_dimension_correlation(components, rewards)
        for dim in DIMENSIONS:
            self.assertAlmostEqual(corr.get(dim, 0.0), 0.0, places=1)

    def test_insufficient_samples_returns_empty(self) -> None:
        corr = _compute_dimension_correlation({}, [0.5, 0.6])
        self.assertEqual(corr, {})

    def test_correlation_bounded(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        corr = _compute_dimension_correlation(components, rewards)
        for v in corr.values():
            self.assertGreaterEqual(v, -1.0)
            self.assertLessEqual(v, 1.0)


# ─── Regret ──────────────────────────────────────────────────────


class TestRegret(unittest.TestCase):
    def test_no_regret_at_peak(self) -> None:
        rewards = [1.0] * 10
        components = _make_component_history(10)
        for dim in DIMENSIONS:
            components[dim] = [1.0] * 10
        regret = _compute_regret(rewards, components)
        for v in regret.values():
            self.assertAlmostEqual(v, 0.0, places=2)

    def test_regret_positive_when_below_peak(self) -> None:
        rewards = [0.8, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        components = _make_component_history(10)
        regret = _compute_regret(rewards, components)
        for v in regret.values():
            self.assertGreaterEqual(v, 0.0)

    def test_insufficient_samples(self) -> None:
        regret = _compute_regret([0.5, 0.6], {})
        self.assertEqual(regret, {})


# ─── Weight adjustment computation ───────────────────────────────


class TestWeightAdjustments(unittest.TestCase):
    def test_insufficient_history_returns_no_adaptation(self) -> None:
        result = compute_weight_adjustments(
            reward_history=[0.5] * (MIN_HISTORY - 1),
            component_history=_make_component_history(MIN_HISTORY - 1),
        )
        self.assertFalse(result.active)
        self.assertEqual(result.weights, DEFAULT_WEIGHTS)

    def test_weights_sum_to_one(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        self.assertAlmostEqual(sum(result.weights.values()), 1.0, places=6)

    def test_all_dimensions_present(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        for dim in DIMENSIONS:
            self.assertIn(dim, result.weights)

    def test_weights_bounded(self) -> None:
        """No weight should deviate more than MAX_ADJUSTMENT_RATIO from default."""
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        for dim in DIMENSIONS:
            default = DEFAULT_WEIGHTS[dim]
            max_delta = default * MAX_ADJUSTMENT_RATIO
            actual_delta = abs(result.weights[dim] - default)
            self.assertLessEqual(
                actual_delta,
                max_delta + 0.02,
                f"{dim}: delta {actual_delta:.4f} exceeds max {max_delta:.4f}",
            )

    def test_instability_increases_stability_weight(self) -> None:
        rewards = _flat_rewards(20)
        components = _make_component_history(20)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
            failure_streak=3,
        )
        self.assertGreater(
            result.weights["stability"],
            DEFAULT_WEIGHTS["stability"],
        )

    def test_plateau_shifts_toward_goal_progress(self) -> None:
        rewards = _flat_rewards(PLATEAU_WINDOW + 10)
        components = _make_component_history(PLATEAU_WINDOW + 10)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        self.assertGreater(
            result.weights["goal_progress"],
            DEFAULT_WEIGHTS["goal_progress"],
        )

    def test_risk_spike_increases_stability(self) -> None:
        rewards = _flat_rewards(20)
        components = _make_component_history(20)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
            risk_level=0.8,
        )
        self.assertGreater(
            result.weights["stability"],
            DEFAULT_WEIGHTS["stability"],
        )

    def test_regime_alignment_set(self) -> None:
        rewards = _flat_rewards(20)
        components = _make_component_history(20)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
            failure_streak=3,
        )
        self.assertEqual(result.regime_alignment, "unstable")


# ─── No oscillation ──────────────────────────────────────────────


class TestNoOscillation(unittest.TestCase):
    def test_ema_smoothing_prevents_oscillation(self) -> None:
        """EMA-blended weights should converge, not oscillate."""
        state = GoalEngineState()

        for i in range(30):
            reward = 0.5 + 0.01 * (i % 5)
            components = {dim: 0.5 for dim in DIMENSIONS}
            components["stability"] = 0.3 if i % 2 == 0 else 0.7
            state.record_turn(reward, components)

        weights_over_time = []
        for _ in range(10):
            result = state.adapt()
            weights_over_time.append(result.weights["stability"])
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        if len(weights_over_time) >= 3:
            diffs = [
                abs(weights_over_time[i] - weights_over_time[i - 1])
                for i in range(1, len(weights_over_time))
            ]
            self.assertLess(diffs[-1], diffs[0] + 0.01)

    def test_repeated_adaptation_converges(self) -> None:
        state = GoalEngineState()

        for i in range(20):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        results = []
        for _ in range(20):
            r = state.adapt()
            results.append(dict(r.weights))
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        final_diff = sum(abs(results[-1][d] - results[-2][d]) for d in DIMENSIONS)
        self.assertLess(final_diff, 0.01)


# ─── GoalEngineState ─────────────────────────────────────────────


class TestGoalEngineState(unittest.TestCase):
    def test_initial_weights_are_defaults(self) -> None:
        state = GoalEngineState()
        self.assertEqual(state.current_weights, DEFAULT_WEIGHTS)

    def test_record_turn_accumulates(self) -> None:
        state = GoalEngineState()
        state.record_turn(0.5, {"goal_progress": 0.6})
        state.record_turn(0.6, {"goal_progress": 0.7})
        self.assertEqual(len(state.reward_history), 2)
        self.assertEqual(state.turn_count, 2)

    def test_history_bounded(self) -> None:
        state = GoalEngineState()
        for i in range(100):
            state.record_turn(
                float(i) / 100,
                {dim: 0.5 for dim in DIMENSIONS},
            )
        self.assertLessEqual(len(state.reward_history), state._max_history)
        for dim in DIMENSIONS:
            self.assertLessEqual(
                len(state.component_history.get(dim, [])),
                state._max_history,
            )

    def test_ema_update_blends(self) -> None:
        state = GoalEngineState()
        target = {dim: DEFAULT_WEIGHTS[dim] * 1.1 for dim in DIMENSIONS}
        target = _normalize_weights(target)

        updated = state.update_weights(target)
        for dim in DIMENSIONS:
            expected = (
                EMA_ALPHA * target[dim] + (1.0 - EMA_ALPHA) * DEFAULT_WEIGHTS[dim]
            )
            self.assertAlmostEqual(updated[dim], expected, places=4)

    def test_snapshot_restore_roundtrip(self) -> None:
        state = GoalEngineState()
        for i in range(10):
            state.record_turn(
                0.5 + 0.01 * i,
                {dim: 0.5 for dim in DIMENSIONS},
            )
        state.adapt()

        data = state.snapshot()
        state2 = GoalEngineState()
        state2.restore(data)

        self.assertEqual(state2.turn_count, state.turn_count)
        self.assertEqual(len(state2.reward_history), len(state.reward_history))
        for dim in DIMENSIONS:
            self.assertAlmostEqual(
                state2.current_weights[dim],
                state.current_weights[dim],
                places=6,
            )

    def test_restore_from_none(self) -> None:
        state = GoalEngineState()
        state.restore(None)
        self.assertEqual(state.current_weights, DEFAULT_WEIGHTS)

    def test_adapt_without_sufficient_history(self) -> None:
        state = GoalEngineState()
        state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})
        result = state.adapt()
        self.assertFalse(result.active)


# ─── Regime-aware shifts ─────────────────────────────────────────


class TestRegimeAwareShifts(unittest.TestCase):
    def test_unstable_regime_prioritizes_stability(self) -> None:
        state = GoalEngineState()
        for i in range(20):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        result = state.adapt(failure_streak=3)
        self.assertGreater(
            result.weights["stability"],
            DEFAULT_WEIGHTS["stability"],
        )

    def test_plateau_regime_prioritizes_progress(self) -> None:
        state = GoalEngineState()
        for i in range(20):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        result = state.adapt(regime_active=True, regime_strength=0.5)
        self.assertGreater(
            result.weights["goal_progress"],
            DEFAULT_WEIGHTS["goal_progress"],
        )

    def test_risk_spike_regime_prioritizes_safety(self) -> None:
        state = GoalEngineState()
        for i in range(20):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        result = state.adapt(risk_level=0.8)
        self.assertGreater(
            result.weights["stability"],
            DEFAULT_WEIGHTS["stability"],
        )

    def test_stable_regime_near_defaults(self) -> None:
        state = GoalEngineState()
        for i in range(20):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})

        result = state.adapt()
        for dim in DIMENSIONS:
            self.assertAlmostEqual(
                result.weights[dim],
                DEFAULT_WEIGHTS[dim],
                places=2,
            )


# ─── Long-horizon improvement ───────────────────────────────────


class TestLongHorizonImprovement(unittest.TestCase):
    def test_correlated_dimension_gets_more_weight(self) -> None:
        """Dimension strongly correlated with reward should gain weight."""
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        self.assertGreaterEqual(
            result.weights["goal_progress"],
            DEFAULT_WEIGHTS["goal_progress"],
        )

    def test_anticorrelated_dimension_loses_weight(self) -> None:
        """Dimension anti-correlated with reward should lose weight."""
        rewards = _improving_rewards(20)
        components = _make_anticorrelated_history(20, "policy_coherence", rewards)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        self.assertLessEqual(
            result.weights["policy_coherence"],
            DEFAULT_WEIGHTS["policy_coherence"],
        )


# ─── Integration with ObjectiveEngine ────────────────────────────


class TestObjectiveIntegration(unittest.TestCase):
    def test_apply_adapted_weights_bounded(self) -> None:
        components = {dim: 0.5 for dim in DIMENSIONS}
        value = apply_adapted_weights(DEFAULT_WEIGHTS, components)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)

    def test_apply_adapted_weights_matches_default(self) -> None:
        """With default weights, should match objective_engine result."""
        from umh.runtime_engine.objective_engine import compute_objective, ObjectiveSnapshot

        snap = ObjectiveSnapshot(
            goal_score=0.6,
            goal_delta=0.05,
            goal_confidence=0.8,
            plan_confidence=0.7,
            plan_steps_completed=3,
            plan_steps_total=5,
            failure_streak=0,
            quality_score=0.8,
            system_confidence=0.7,
            policy_changes=1,
            current_policy="exploit",
            previous_policy="exploit",
        )
        obj_result = compute_objective(snap)
        adapted_value = apply_adapted_weights(DEFAULT_WEIGHTS, obj_result.components)
        self.assertAlmostEqual(adapted_value, obj_result.value, places=4)

    def test_adapted_weights_change_objective_value(self) -> None:
        """Shifted weights should produce a different objective value."""
        from umh.runtime_engine.objective_engine import compute_objective, ObjectiveSnapshot

        snap = ObjectiveSnapshot(
            goal_score=0.9,
            goal_delta=0.1,
            goal_confidence=0.9,
            plan_confidence=0.3,
            plan_steps_completed=1,
            plan_steps_total=5,
            failure_streak=2,
            quality_score=0.4,
            system_confidence=0.3,
            policy_changes=3,
        )
        obj_result = compute_objective(snap)

        shifted_weights = dict(DEFAULT_WEIGHTS)
        shifted_weights["goal_progress"] = 0.50
        shifted_weights["stability"] = 0.10
        shifted_weights = _normalize_weights(shifted_weights)

        default_value = obj_result.value
        shifted_value = apply_adapted_weights(shifted_weights, obj_result.components)

        self.assertNotAlmostEqual(default_value, shifted_value, places=2)


# ─── Trace fields ────────────────────────────────────────────────


class TestTraceFields(unittest.TestCase):
    def test_to_dict_has_required_fields(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        d = result.to_dict()
        self.assertIn("weights", d)
        self.assertIn("adjustments", d)
        self.assertIn("regime_alignment", d)
        self.assertIn("reasoning", d)

    def test_adjustment_to_dict(self) -> None:
        adj = GoalWeightAdjustment(
            dimension="stability",
            default_weight=0.20,
            adjusted_weight=0.22,
            delta=0.02,
            reason="regime=unstable",
        )
        d = adj.to_dict()
        self.assertEqual(d["dimension"], "stability")
        self.assertIn("delta", d)


# ─── Determinism ─────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_outputs(self) -> None:
        rewards = _improving_rewards(20)
        components = _make_component_history(20, "goal_progress", rewards)

        results = []
        for _ in range(5):
            r = compute_weight_adjustments(
                reward_history=rewards,
                component_history=components,
                failure_streak=1,
                regime_active=True,
                regime_strength=0.4,
            )
            results.append(r.to_dict())

        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])


# ─── No regression ───────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_objective_engine_import_still_works(self) -> None:
        from umh.runtime_engine.objective_engine import (
            compute_objective,
            ObjectiveSnapshot,
            ObjectiveResult,
            WEIGHT_GOAL_PROGRESS,
        )

        self.assertEqual(WEIGHT_GOAL_PROGRESS, 0.30)

    def test_default_weights_match_objective_engine(self) -> None:
        from umh.runtime_engine.objective_engine import (
            WEIGHT_GOAL_PROGRESS,
            WEIGHT_PLAN_EXECUTION,
            WEIGHT_STABILITY,
            WEIGHT_CONFIDENCE,
            WEIGHT_POLICY_COHERENCE,
        )

        self.assertAlmostEqual(DEFAULT_WEIGHTS["goal_progress"], WEIGHT_GOAL_PROGRESS)
        self.assertAlmostEqual(DEFAULT_WEIGHTS["plan_execution"], WEIGHT_PLAN_EXECUTION)
        self.assertAlmostEqual(DEFAULT_WEIGHTS["stability"], WEIGHT_STABILITY)
        self.assertAlmostEqual(DEFAULT_WEIGHTS["confidence"], WEIGHT_CONFIDENCE)
        self.assertAlmostEqual(
            DEFAULT_WEIGHTS["policy_coherence"], WEIGHT_POLICY_COHERENCE
        )

    def test_weights_sum_matches_objective_engine(self) -> None:
        self.assertAlmostEqual(sum(DEFAULT_WEIGHTS.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
