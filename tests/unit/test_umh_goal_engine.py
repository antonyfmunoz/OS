"""Tests for umh.goals.engine — adaptive weight tuning."""

from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.goals.engine import (
    DEFAULT_WEIGHTS,
    DIMENSIONS,
    EMA_ALPHA,
    EPSILON,
    MAX_ADJUSTMENT_RATIO,
    MIN_HISTORY,
    NO_ADAPTATION,
    GoalAdaptationResult,
    GoalEngineState,
    GoalWeightAdjustment,
    _clamp,
    _compute_dimension_correlation,
    _compute_regret,
    _detect_regime,
    _normalize_weights,
    _regime_pressure,
    apply_adapted_weights,
    compute_weight_adjustments,
)


# ── Import boundary ─────────────────────────────────────────────


class TestImportBoundary:
    def test_no_forbidden_imports(self):
        with open("umh/goals/engine.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"eos", "core", "services", "scripts"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"from {node.module}"

    def test_clean_import(self):
        from umh.goals import engine

        assert hasattr(engine, "compute_weight_adjustments")
        assert hasattr(engine, "GoalEngineState")


# ── Helpers ──────────────────────────────────────────────────────


class TestHelpers:
    def test_clamp_within_bounds(self):
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_clamp_below(self):
        assert _clamp(-1.0, 0.0, 1.0) == 0.0

    def test_clamp_above(self):
        assert _clamp(2.0, 0.0, 1.0) == 1.0

    def test_normalize_preserves_proportions(self):
        raw = {"a": 2.0, "b": 3.0}
        normed = _normalize_weights(raw)
        assert abs(normed["a"] - 0.4) < 1e-9
        assert abs(normed["b"] - 0.6) < 1e-9

    def test_normalize_zero_returns_defaults(self):
        raw = {dim: 0.0 for dim in DIMENSIONS}
        normed = _normalize_weights(raw)
        assert normed == DEFAULT_WEIGHTS

    def test_normalize_sums_to_one(self):
        raw = {"a": 0.1, "b": 0.3, "c": 0.7}
        normed = _normalize_weights(raw)
        assert abs(sum(normed.values()) - 1.0) < 1e-9


# ── Data structures ──────────────────────────────────────────────


class TestDataStructures:
    def test_weight_adjustment_to_dict(self):
        adj = GoalWeightAdjustment(
            dimension="goal_progress",
            default_weight=0.30,
            adjusted_weight=0.32,
            delta=0.02,
            reason="corr=0.45",
        )
        d = adj.to_dict()
        assert d["dimension"] == "goal_progress"
        assert d["delta"] == 0.02

    def test_adaptation_result_to_dict(self):
        result = NO_ADAPTATION
        d = result.to_dict()
        assert d["active"] is False
        assert d["regime_alignment"] == "neutral"
        assert d["reasoning"] == "insufficient_history"
        assert sum(d["weights"].values()) == pytest.approx(1.0, abs=1e-6)


# ── Regime detection ─────────────────────────────────────────────


class TestRegimeDetection:
    def test_stable_default(self):
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.5, 0.6, 0.4],
            risk_level=0.0,
        )
        assert regime == "stable"

    def test_unstable_on_streak(self):
        regime = _detect_regime(
            failure_streak=3,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.5] * 10,
            risk_level=0.0,
        )
        assert regime == "unstable"

    def test_risk_spike(self):
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.5] * 10,
            risk_level=0.8,
        )
        assert regime == "risk_spike"

    def test_plateau_from_variance(self):
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.500] * 10,
            risk_level=0.0,
        )
        assert regime == "plateau"

    def test_plateau_from_regime_flag(self):
        regime = _detect_regime(
            failure_streak=0,
            regime_active=True,
            regime_strength=0.5,
            reward_history=[0.5, 0.6, 0.7],
            risk_level=0.0,
        )
        assert regime == "plateau"

    def test_recovery_on_ascending(self):
        regime = _detect_regime(
            failure_streak=0,
            regime_active=False,
            regime_strength=0.0,
            reward_history=[0.3, 0.4, 0.5],
            risk_level=0.0,
        )
        assert regime == "recovery"


# ── Regime pressure ──────────────────────────────────────────────


class TestRegimePressure:
    def test_stable_zero_pressure(self):
        p = _regime_pressure("stable")
        assert all(v == 0.0 for v in p.values())

    def test_unstable_boosts_stability(self):
        p = _regime_pressure("unstable")
        assert p["stability"] == 1.0
        assert p["goal_progress"] < 0

    def test_plateau_boosts_goal_progress(self):
        p = _regime_pressure("plateau")
        assert p["goal_progress"] > 0
        assert p["stability"] < 0


# ── Correlation ──────────────────────────────────────────────────


class TestCorrelation:
    def test_insufficient_samples(self):
        corrs = _compute_dimension_correlation(
            {"goal_progress": [0.5, 0.6]},
            [0.5, 0.6],
        )
        assert corrs == {}

    def test_perfect_positive(self):
        n = 10
        rewards = [float(i) / n for i in range(n)]
        components = {"goal_progress": list(rewards)}
        corrs = _compute_dimension_correlation(components, rewards)
        assert corrs["goal_progress"] == pytest.approx(1.0, abs=0.01)

    def test_zero_variance_reward(self):
        corrs = _compute_dimension_correlation(
            {"goal_progress": [0.5] * 10},
            [0.5] * 10,
        )
        assert corrs == {}


# ── Regret ───────────────────────────────────────────────────────


class TestRegret:
    def test_insufficient_samples(self):
        regret = _compute_regret([0.5, 0.6], {"goal_progress": [0.5, 0.6]})
        assert regret == {}

    def test_no_regret_at_peak(self):
        rewards = [1.0] * 10
        components = {"goal_progress": [1.0] * 10}
        regret = _compute_regret(rewards, components)
        assert regret["goal_progress"] == pytest.approx(0.0, abs=0.01)

    def test_positive_regret_below_peak(self):
        rewards = [0.8, 0.3, 0.3, 0.3, 0.3]
        components = {"goal_progress": [0.8, 0.3, 0.3, 0.3, 0.3]}
        regret = _compute_regret(rewards, components)
        assert regret["goal_progress"] > 0


# ── Core adaptation ──────────────────────────────────────────────


class TestComputeWeightAdjustments:
    def test_insufficient_history_returns_no_adaptation(self):
        result = compute_weight_adjustments(
            reward_history=[0.5] * 3,
            component_history={dim: [0.5] * 3 for dim in DIMENSIONS},
        )
        assert result.active is False
        assert result.reasoning == "insufficient_history"

    def test_sufficient_history_returns_result(self):
        n = 10
        rewards = [0.3 + 0.05 * i for i in range(n)]
        components = {dim: [0.5] * n for dim in DIMENSIONS}
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        assert isinstance(result, GoalAdaptationResult)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_weights_bounded(self):
        n = 20
        rewards = [0.1 * i for i in range(n)]
        components = {dim: [float(i) / n for i in range(n)] for dim in DIMENSIONS}
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
        )
        for adj in result.adjustments:
            max_delta = adj.default_weight * MAX_ADJUSTMENT_RATIO
            assert abs(adj.adjusted_weight - adj.default_weight) <= max_delta + 0.01

    def test_unstable_regime_shifts_to_stability(self):
        n = 10
        rewards = [0.5] * n
        components = {dim: [0.5] * n for dim in DIMENSIONS}
        result = compute_weight_adjustments(
            reward_history=rewards,
            component_history=components,
            failure_streak=5,
        )
        assert result.regime_alignment == "unstable"
        stability_adj = next(a for a in result.adjustments if a.dimension == "stability")
        assert stability_adj.delta > 0


# ── GoalEngineState ──────────────────────────────────────────────


class TestGoalEngineState:
    def test_initial_state(self):
        state = GoalEngineState()
        assert state.turn_count == 0
        assert state.current_weights == DEFAULT_WEIGHTS
        assert state.reward_history == []

    def test_record_turn(self):
        state = GoalEngineState()
        state.record_turn(0.7, {dim: 0.5 for dim in DIMENSIONS})
        assert state.turn_count == 1
        assert len(state.reward_history) == 1
        assert state.reward_history[0] == 0.7

    def test_history_capped(self):
        state = GoalEngineState()
        for i in range(60):
            state.record_turn(float(i) / 60, {dim: 0.5 for dim in DIMENSIONS})
        assert len(state.reward_history) == 50
        assert len(state.component_history["goal_progress"]) == 50

    def test_ema_blending(self):
        state = GoalEngineState()
        target = {dim: 0.2 for dim in DIMENSIONS}
        target["goal_progress"] = 1.0
        blended = state.update_weights(target)
        assert abs(sum(blended.values()) - 1.0) < 1e-6
        # goal_progress should be the largest weight after blending toward 1.0
        assert blended["goal_progress"] == max(blended.values())

    def test_adapt_insufficient_history(self):
        state = GoalEngineState()
        state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})
        result = state.adapt()
        assert result.active is False

    def test_adapt_with_history(self):
        state = GoalEngineState()
        for i in range(15):
            state.record_turn(
                0.3 + 0.03 * i,
                {dim: 0.3 + 0.03 * i for dim in DIMENSIONS},
            )
        result = state.adapt()
        assert isinstance(result, GoalAdaptationResult)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_snapshot_restore_roundtrip(self):
        state = GoalEngineState()
        for i in range(10):
            state.record_turn(0.5, {dim: 0.5 for dim in DIMENSIONS})
        state.adapt()
        snap = state.snapshot()

        restored = GoalEngineState()
        restored.restore(snap)
        assert restored.turn_count == state.turn_count
        assert restored.current_weights == pytest.approx(state.current_weights, abs=1e-6)
        assert restored.reward_history == pytest.approx(state.reward_history, abs=1e-6)

    def test_restore_handles_none(self):
        state = GoalEngineState()
        state.restore(None)
        assert state.current_weights == DEFAULT_WEIGHTS

    def test_restore_handles_bad_data(self):
        state = GoalEngineState()
        state.restore({"current_weights": "bad", "turn_count": "nope"})
        assert state.turn_count == 0


# ── apply_adapted_weights ────────────────────────────────────────


class TestApplyAdaptedWeights:
    def test_default_weights_produce_expected(self):
        components = {dim: 1.0 for dim in DIMENSIONS}
        value = apply_adapted_weights(DEFAULT_WEIGHTS, components)
        assert value == pytest.approx(1.0, abs=1e-6)

    def test_zero_components(self):
        components = {dim: 0.0 for dim in DIMENSIONS}
        value = apply_adapted_weights(DEFAULT_WEIGHTS, components)
        assert value == 0.0

    def test_clamps_to_range(self):
        components = {dim: 2.0 for dim in DIMENSIONS}
        value = apply_adapted_weights(DEFAULT_WEIGHTS, components)
        assert value == 1.0
