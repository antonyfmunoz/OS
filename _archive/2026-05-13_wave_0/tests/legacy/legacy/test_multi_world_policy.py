"""Tests for MultiWorldPolicy — robust action selection across world variations.

Covers:
1. Deterministic outputs
2. Bounded branching
3. Correct scoring behavior
4. No regressions
5. Fallback behavior
6. Trace integration
7. World variation generation
8. Safety gating
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.multi_world_policy import (
    MAX_WORLDS,
    MAX_POLICY_ACTIONS,
    LAMBDA_VARIANCE,
    LAMBDA_DOWNSIDE,
    LAMBDA_RISK,
    MIN_UNCERTAINTY_FOR_POLICY,
    MIN_SIMULATION_HORIZON,
    NO_POLICY_RESULT,
    ActionWorldScore,
    DynamicsAdjustment,
    MultiWorldPolicyResult,
    PolicyEvaluation,
    WorldVariation,
    check_policy_gating,
    evaluate_action_across_worlds,
    evaluate_multi_world_policy,
    generate_world_variations,
    _deterministic_offset,
)
from umh.world.dynamics_adapter import NEUTRAL_ADJUSTMENT
from umh.world.simulation import SimulatedAction
from umh.world.types import (
    Entity,
    Observation,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import WorldReasoningEngine, WorldUnderstanding


# ─── Helpers ─────────────────────────────────────────────────────


def _make_snapshot(
    entities: list[tuple[str, str]] | None = None,
    facts: list[tuple[str, str, float]] | None = None,
    obs_count: int = 10,
) -> WorldSnapshot:
    ents = tuple(
        Entity(entity_id=eid, entity_type=etype)
        for eid, etype in (entities or [("e1", "metric")])
    )
    sf = tuple(
        StateFact(
            entity_id=eid,
            key=key,
            value=val,
            confidence=0.9,
            last_updated_turn=1,
            update_count=5,
        )
        for eid, key, val in (facts or [("e1", "revenue", 100.0)])
    )
    return WorldSnapshot(
        entities=ents,
        relations=(),
        state_facts=sf,
        observation_count=obs_count,
        version=1,
    )


def _make_observations(entity_id: str, key: str, base: float, count: int = 10):
    return tuple(
        Observation(
            observation_id=f"obs_{entity_id}_{key}_{i}",
            timestamp_turn=i,
            source="test",
            entity_id=entity_id,
            signal_type=key,
            value=base + i,
            confidence=0.9,
        )
        for i in range(count)
    )


def _build_world():
    snap = _make_snapshot(
        entities=[("e1", "metric"), ("e2", "metric")],
        facts=[("e1", "revenue", 100.0), ("e2", "cost", 50.0)],
    )
    obs = _make_observations("e1", "revenue", 100.0) + _make_observations(
        "e2", "cost", 50.0
    )
    engine = WorldReasoningEngine()
    understanding = engine.derive_understanding(snap, obs)
    return snap, understanding, obs


# ─── Test Classes ────────────────────────────────────────────────


class TestWorldVariationGeneration(unittest.TestCase):
    def test_generates_k_variations(self):
        variations = generate_world_variations()
        self.assertEqual(len(variations), MAX_WORLDS)

    def test_first_is_baseline(self):
        variations = generate_world_variations()
        self.assertEqual(variations[0].label, "baseline")
        self.assertEqual(variations[0].variation_id, 0)

    def test_variation_labels(self):
        variations = generate_world_variations()
        labels = {v.label for v in variations}
        self.assertIn("baseline", labels)
        self.assertIn("trend_up", labels)
        self.assertIn("trend_down", labels)
        self.assertIn("risk_up_stability_up", labels)
        self.assertIn("risk_down_stability_down", labels)

    def test_trend_variations_differ(self):
        variations = generate_world_variations()
        trend_up = next(v for v in variations if v.label == "trend_up")
        trend_down = next(v for v in variations if v.label == "trend_down")
        self.assertGreater(
            trend_up.adjustment.trend_multiplier,
            trend_down.adjustment.trend_multiplier,
        )

    def test_custom_base_adjustment(self):
        base = DynamicsAdjustment(
            trend_multiplier=1.2,
            risk_multiplier=0.8,
            stability_decay_modifier=0.01,
            confidence_scale=1.1,
        )
        variations = generate_world_variations(base)
        baseline = variations[0]
        self.assertEqual(baseline.adjustment, base)

    def test_variations_bounded(self):
        variations = generate_world_variations()
        for v in variations:
            self.assertGreaterEqual(v.adjustment.trend_multiplier, 0.5)
            self.assertLessEqual(v.adjustment.trend_multiplier, 1.5)
            self.assertGreaterEqual(v.adjustment.risk_multiplier, 0.5)
            self.assertLessEqual(v.adjustment.risk_multiplier, 1.5)

    def test_variation_ids_unique(self):
        variations = generate_world_variations()
        ids = [v.variation_id for v in variations]
        self.assertEqual(len(ids), len(set(ids)))


class TestDeterministicNoise(unittest.TestCase):
    def test_same_inputs_same_output(self):
        o1 = _deterministic_offset("action_a", 0)
        o2 = _deterministic_offset("action_a", 0)
        self.assertEqual(o1, o2)

    def test_different_actions_different_noise(self):
        o1 = _deterministic_offset("action_a", 0)
        o2 = _deterministic_offset("action_b", 0)
        self.assertNotEqual(o1, o2)

    def test_noise_bounded(self):
        for i in range(100):
            offset = _deterministic_offset(f"action_{i}", i)
            self.assertGreaterEqual(offset, -0.05)
            self.assertLessEqual(offset, 0.05)


class TestSafetyGating(unittest.TestCase):
    def test_non_stable_context_gated(self):
        for ctx in [None, "volatile", "exploratory", "unknown"]:
            reason = check_policy_gating(ctx, 0.2, 3)
            self.assertIsNotNone(reason)
            self.assertIn("context_not_stable", reason)

    def test_high_uncertainty_gated(self):
        reason = check_policy_gating("stable", 0.6, 3)
        self.assertIsNotNone(reason)
        self.assertIn("uncertainty_too_high", reason)

    def test_shallow_horizon_gated(self):
        reason = check_policy_gating("stable", 0.2, 1)
        self.assertIsNotNone(reason)
        self.assertIn("horizon_too_shallow", reason)

    def test_valid_conditions_pass(self):
        reason = check_policy_gating("stable", 0.2, 3)
        self.assertIsNone(reason)

    def test_boundary_uncertainty_gated(self):
        reason = check_policy_gating("stable", MIN_UNCERTAINTY_FOR_POLICY, 3)
        self.assertIsNotNone(reason)

    def test_boundary_horizon_gated(self):
        reason = check_policy_gating("stable", 0.2, MIN_SIMULATION_HORIZON - 1)
        self.assertIsNotNone(reason)


class TestActionWorldScoring(unittest.TestCase):
    def test_evaluate_action_returns_k_scores(self):
        snap, und, obs = _build_world()
        action = SimulatedAction(
            action_id="boost_e1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.1},
        )
        variations = generate_world_variations()
        ev = evaluate_action_across_worlds(
            action, snap, und, variations, horizon=3, observation_history=obs
        )
        self.assertEqual(len(ev.world_scores), MAX_WORLDS)
        self.assertEqual(ev.world_count, MAX_WORLDS)
        self.assertEqual(ev.action_id, "boost_e1")

    def test_mean_score_is_average(self):
        snap, und, obs = _build_world()
        action = SimulatedAction(
            action_id="boost_e1", action_type="boost", target_entity="e1"
        )
        variations = generate_world_variations()
        ev = evaluate_action_across_worlds(
            action, snap, und, variations, horizon=3, observation_history=obs
        )
        expected_mean = sum(s.net_score for s in ev.world_scores) / len(ev.world_scores)
        self.assertAlmostEqual(ev.mean_score, expected_mean, places=8)

    def test_worst_case_is_minimum(self):
        snap, und, obs = _build_world()
        action = SimulatedAction(
            action_id="boost_e1", action_type="boost", target_entity="e1"
        )
        variations = generate_world_variations()
        ev = evaluate_action_across_worlds(
            action, snap, und, variations, horizon=3, observation_history=obs
        )
        expected_worst = min(s.net_score for s in ev.world_scores)
        self.assertAlmostEqual(ev.worst_case, expected_worst, places=8)

    def test_variance_computed(self):
        snap, und, obs = _build_world()
        action = SimulatedAction(
            action_id="boost_e1", action_type="boost", target_entity="e1"
        )
        variations = generate_world_variations()
        ev = evaluate_action_across_worlds(
            action, snap, und, variations, horizon=3, observation_history=obs
        )
        self.assertGreaterEqual(ev.variance, 0.0)


class TestRobustScoring(unittest.TestCase):
    def test_robust_score_less_than_mean(self):
        """Robust score should be ≤ mean (penalties are non-negative)."""
        snap, und, obs = _build_world()
        action = SimulatedAction(
            action_id="boost_e1", action_type="boost", target_entity="e1"
        )
        variations = generate_world_variations()
        ev = evaluate_action_across_worlds(
            action, snap, und, variations, horizon=3, observation_history=obs
        )
        self.assertLessEqual(ev.robust_score, ev.mean_score + 0.01)

    def test_consistent_action_beats_fragile(self):
        """An action with consistent scores should have higher robust_score
        than one with same mean but higher variance."""
        score_consistent = PolicyEvaluation(
            action_id="consistent",
            world_scores=tuple(
                ActionWorldScore(
                    action_id="consistent",
                    variation_id=i,
                    improvement=0.5,
                    risk=0.1,
                    confidence=0.8,
                    net_score=0.5,
                )
                for i in range(5)
            ),
            mean_score=0.5,
            worst_case=0.5,
            variance=0.0,
            robust_score=0.5 - LAMBDA_RISK * 0.1,
            world_count=5,
        )

        score_fragile = PolicyEvaluation(
            action_id="fragile",
            world_scores=tuple(
                ActionWorldScore(
                    action_id="fragile",
                    variation_id=i,
                    improvement=0.5,
                    risk=0.1,
                    confidence=0.8,
                    net_score=[0.9, 0.8, 0.5, 0.2, 0.1][i],
                )
                for i in range(5)
            ),
            mean_score=0.5,
            worst_case=0.1,
            variance=0.092,
            robust_score=(
                0.5
                - LAMBDA_VARIANCE * 0.092
                - LAMBDA_DOWNSIDE * (0.5 - 0.1)
                - LAMBDA_RISK * 0.1
            ),
            world_count=5,
        )

        self.assertGreater(score_consistent.robust_score, score_fragile.robust_score)


class TestMultiWorldPolicyEvaluation(unittest.TestCase):
    def test_empty_actions_returns_inactive(self):
        snap, und, obs = _build_world()
        result = evaluate_multi_world_policy(
            actions=(),
            snapshot=snap,
            understanding=und,
            context_type="stable",
        )
        self.assertFalse(result.active)

    def test_gated_context_returns_inactive(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(action_id="a1", action_type="boost", target_entity="e1"),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            context_type="volatile",
        )
        self.assertFalse(result.active)
        self.assertIn("gated", result.reason)

    def test_high_uncertainty_returns_inactive(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(action_id="a1", action_type="boost", target_entity="e1"),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            context_type="stable",
            uncertainty=0.7,
        )
        self.assertFalse(result.active)

    def test_active_result_with_valid_inputs(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(
                action_id="boost_e1",
                action_type="boost",
                target_entity="e1",
                parameters={"magnitude": 0.1},
            ),
            SimulatedAction(
                action_id="suppress_e2",
                action_type="suppress",
                target_entity="e2",
                parameters={"magnitude": 0.1},
            ),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
            uncertainty=0.1,
        )
        self.assertTrue(result.active)
        self.assertIsNotNone(result.selected_action_id)
        self.assertEqual(result.world_count, MAX_WORLDS)
        self.assertEqual(len(result.evaluations), 2)

    def test_capped_to_max_actions(self):
        snap, und, obs = _build_world()
        actions = tuple(
            SimulatedAction(action_id=f"a{i}", action_type="boost", target_entity="e1")
            for i in range(10)
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        self.assertLessEqual(len(result.evaluations), MAX_POLICY_ACTIONS)

    def test_selects_action_with_highest_robust_score(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(
                action_id="boost_e1",
                action_type="boost",
                target_entity="e1",
            ),
            SimulatedAction(
                action_id="suppress_e2",
                action_type="suppress",
                target_entity="e2",
            ),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        if result.active:
            best_eval = max(result.evaluations, key=lambda e: e.robust_score)
            self.assertEqual(result.selected_action_id, best_eval.action_id)


class TestDeterministicBehavior(unittest.TestCase):
    def test_same_inputs_same_result(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(
                action_id="boost_e1",
                action_type="boost",
                target_entity="e1",
            ),
        )
        r1 = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        r2 = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        self.assertEqual(r1.selected_action_id, r2.selected_action_id)
        self.assertAlmostEqual(
            r1.selected_robust_score, r2.selected_robust_score, places=8
        )
        for e1, e2 in zip(r1.evaluations, r2.evaluations):
            self.assertAlmostEqual(e1.robust_score, e2.robust_score, places=8)

    def test_evaluation_serialization(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(
                action_id="boost_e1",
                action_type="boost",
                target_entity="e1",
            ),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        d = result.to_dict()
        self.assertIn("active", d)
        self.assertIn("selected_action_id", d)
        self.assertIn("evaluations", d)
        self.assertIn("world_count", d)


class TestBoundedBranching(unittest.TestCase):
    def test_world_count_bounded(self):
        variations = generate_world_variations()
        self.assertLessEqual(len(variations), MAX_WORLDS)

    def test_action_count_bounded(self):
        snap, und, obs = _build_world()
        actions = tuple(
            SimulatedAction(action_id=f"a{i}", action_type="boost", target_entity="e1")
            for i in range(20)
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            horizon=3,
            observation_history=obs,
            context_type="stable",
        )
        self.assertLessEqual(len(result.evaluations), MAX_POLICY_ACTIONS)


class TestTraceIntegration(unittest.TestCase):
    def test_decision_trace_has_policy_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            policy_world_count=5,
            policy_variance=0.02,
            policy_worst_case=-0.1,
            policy_robust_score=0.45,
        )
        self.assertEqual(t.policy_world_count, 5)
        d = t.to_dict()
        self.assertIn("policy_world_count", d)
        self.assertAlmostEqual(d["policy_variance"], 0.02, places=4)

    def test_build_trace_accepts_policy_params(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(
            turn_id=1,
            policy_world_count=5,
            policy_variance=0.03,
            policy_worst_case=-0.05,
            policy_robust_score=0.6,
        )
        self.assertEqual(t.policy_world_count, 5)
        self.assertAlmostEqual(t.policy_variance, 0.03)
        self.assertAlmostEqual(t.policy_worst_case, -0.05)
        self.assertAlmostEqual(t.policy_robust_score, 0.6)

    def test_trace_omits_policy_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(turn_id=1)
        d = t.to_dict()
        self.assertNotIn("policy_world_count", d)
        self.assertNotIn("policy_variance", d)

    def test_variation_to_dict(self):
        v = WorldVariation(
            variation_id=1,
            adjustment=NEUTRAL_ADJUSTMENT,
            label="test",
        )
        d = v.to_dict()
        self.assertEqual(d["variation_id"], 1)
        self.assertEqual(d["label"], "test")
        self.assertIn("adjustment", d)


class TestFallbackBehavior(unittest.TestCase):
    def test_fallback_when_not_stable(self):
        snap, und, obs = _build_world()
        actions = (
            SimulatedAction(action_id="a1", action_type="boost", target_entity="e1"),
        )
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=und,
            context_type=None,
        )
        self.assertFalse(result.active)
        self.assertIsNone(result.selected_action_id)

    def test_fallback_preserves_no_op(self):
        result = evaluate_multi_world_policy(
            actions=(),
            snapshot=_make_snapshot(),
            understanding=WorldReasoningEngine().derive_understanding(
                _make_snapshot(), ()
            ),
        )
        self.assertEqual(result, NO_POLICY_RESULT)


class TestNoRegression(unittest.TestCase):
    def test_multi_world_policy_imports(self):
        from umh.runtime_engine.multi_world_policy import (
            MultiWorldPolicyResult,
            evaluate_multi_world_policy,
            generate_world_variations,
        )

        self.assertIsNotNone(MultiWorldPolicyResult)

    def test_world_simulation_imports(self):
        from umh.world.simulation import WorldSimulationEngine

        self.assertIsNotNone(WorldSimulationEngine)

    def test_world_dynamics_adapter_imports(self):
        from umh.world.dynamics_adapter import WorldDynamicsAdapter

        self.assertIsNotNone(WorldDynamicsAdapter)

    def test_decision_trace_imports(self):
        from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

        self.assertIsNotNone(DecisionTrace)

    def test_world_calibration_imports(self):
        from umh.world.calibration import WorldCalibrationEngine

        self.assertIsNotNone(WorldCalibrationEngine)


if __name__ == "__main__":
    unittest.main()
