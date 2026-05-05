"""Tests for eos/objective_arbitration.py — dynamic objective weighting."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from umh.runtime_engine.objective_arbitration import (
    DEFAULT_WEIGHTS,
    EMA_ALPHA,
    EXPLORATION_WEIGHT_MAX,
    EXPLORATION_WEIGHT_MIN,
    MIN_CONFIDENCE_FOR_ARBITRATION,
    NO_ARBITRATION_RESULT,
    NOVELTY_WEIGHT_MAX,
    NOVELTY_WEIGHT_MIN,
    REWARD_WEIGHT_MAX,
    REWARD_WEIGHT_MIN,
    RISK_WEIGHT_MAX,
    RISK_WEIGHT_MIN,
    STABILITY_WEIGHT_MAX,
    STABILITY_WEIGHT_MIN,
    VALID_MODES,
    ArbitrationResult,
    ContextSignals,
    ObjectiveArbiter,
    ObjectiveWeights,
    compute_weighted_score,
    detect_objective_mode,
    get_target_weights,
    smooth_weights,
)


def _is_bounded(w: ObjectiveWeights) -> bool:
    return (
        REWARD_WEIGHT_MIN <= w.reward_weight <= REWARD_WEIGHT_MAX
        and RISK_WEIGHT_MIN <= w.risk_weight <= RISK_WEIGHT_MAX
        and STABILITY_WEIGHT_MIN <= w.stability_weight <= STABILITY_WEIGHT_MAX
        and EXPLORATION_WEIGHT_MIN <= w.exploration_weight <= EXPLORATION_WEIGHT_MAX
        and NOVELTY_WEIGHT_MIN <= w.novelty_weight <= NOVELTY_WEIGHT_MAX
    )


# ─── Weight bounds ────────────────────────────────────────────


class TestWeightBounds(unittest.TestCase):
    def test_default_weights_bounded(self):
        self.assertTrue(_is_bounded(DEFAULT_WEIGHTS))

    def test_all_mode_targets_bounded(self):
        for mode in VALID_MODES:
            w = get_target_weights(mode)
            self.assertTrue(_is_bounded(w), f"mode={mode} out of bounds: {w}")

    def test_unknown_mode_returns_default(self):
        w = get_target_weights("nonexistent")
        self.assertEqual(w, DEFAULT_WEIGHTS)

    def test_weights_frozen(self):
        w = ObjectiveWeights(0.5, 0.3, 0.3, 0.0, 0.0)
        with self.assertRaises(AttributeError):
            w.reward_weight = 0.9  # type: ignore[misc]


# ─── Mode detection ───────────────────────────────────────────


class TestModeDetection(unittest.TestCase):
    def test_stable_context(self):
        s = ContextSignals(context_type="stable", uncertainty=0.1)
        self.assertEqual(detect_objective_mode(s), "stable")

    def test_adversarial_context(self):
        s = ContextSignals(context_type="adversarial")
        self.assertEqual(detect_objective_mode(s), "adversarial")

    def test_high_risk_triggers_adversarial(self):
        s = ContextSignals(context_type="stable", risk_level=0.8)
        self.assertEqual(detect_objective_mode(s), "adversarial")

    def test_volatile_context(self):
        s = ContextSignals(context_type="volatile")
        self.assertEqual(detect_objective_mode(s), "high_uncertainty")

    def test_high_uncertainty_triggers_mode(self):
        s = ContextSignals(context_type="stable", uncertainty=0.7)
        self.assertEqual(detect_objective_mode(s), "high_uncertainty")

    def test_plateau_detection(self):
        s = ContextSignals(
            context_type="stable",
            uncertainty=0.1,
            exploration_stagnation=0.6,
            improvement_trend=0.05,
        )
        self.assertEqual(detect_objective_mode(s), "plateau")

    def test_default_when_ambiguous(self):
        s = ContextSignals(context_type="drifting", uncertainty=0.4)
        self.assertEqual(detect_objective_mode(s), "default")

    def test_adversarial_beats_uncertainty(self):
        s = ContextSignals(context_type="adversarial", uncertainty=0.9, risk_level=0.8)
        self.assertEqual(detect_objective_mode(s), "adversarial")

    def test_uncertainty_beats_plateau(self):
        s = ContextSignals(
            context_type="volatile",
            exploration_stagnation=0.9,
            improvement_trend=0.01,
        )
        self.assertEqual(detect_objective_mode(s), "high_uncertainty")

    def test_none_context_type_gives_default(self):
        s = ContextSignals(context_type=None, uncertainty=0.2)
        self.assertEqual(detect_objective_mode(s), "default")


# ─── Smooth transitions ──────────────────────────────────────


class TestSmoothTransitions(unittest.TestCase):
    def test_ema_moves_toward_target(self):
        prev = DEFAULT_WEIGHTS
        target = get_target_weights("adversarial")
        result = smooth_weights(prev, target)
        self.assertGreater(result.risk_weight, prev.risk_weight)
        self.assertLess(result.risk_weight, target.risk_weight)

    def test_ema_preserves_bounds(self):
        extreme = ObjectiveWeights(0.3, 0.1, 0.1, 0.0, 0.0)
        target = ObjectiveWeights(0.7, 0.5, 0.5, 0.3, 0.2)
        result = smooth_weights(extreme, target)
        self.assertTrue(_is_bounded(result))

    def test_repeated_ema_converges(self):
        w = DEFAULT_WEIGHTS
        target = get_target_weights("stable")
        for _ in range(200):
            w = smooth_weights(w, target)
        self.assertAlmostEqual(w.reward_weight, target.reward_weight, places=2)
        self.assertAlmostEqual(w.risk_weight, target.risk_weight, places=2)

    def test_no_abrupt_flip(self):
        w = DEFAULT_WEIGHTS
        target = get_target_weights("adversarial")
        result = smooth_weights(w, target)
        max_shift = max(
            abs(result.reward_weight - w.reward_weight),
            abs(result.risk_weight - w.risk_weight),
            abs(result.stability_weight - w.stability_weight),
        )
        self.assertLess(max_shift, 0.05)

    def test_identity_when_same(self):
        w = DEFAULT_WEIGHTS
        result = smooth_weights(w, w)
        self.assertAlmostEqual(result.reward_weight, w.reward_weight, places=6)
        self.assertAlmostEqual(result.risk_weight, w.risk_weight, places=6)


# ─── Scoring function ────────────────────────────────────────


class TestWeightedScoring(unittest.TestCase):
    def test_default_weights_match_old_pattern(self):
        score = compute_weighted_score(DEFAULT_WEIGHTS, improvement=1.0, risk=0.5)
        expected = 0.5 * 1.0 - 0.3 * 0.5
        self.assertAlmostEqual(score, expected, places=6)

    def test_adversarial_penalizes_risk_more(self):
        w_stable = get_target_weights("stable")
        w_adv = get_target_weights("adversarial")
        score_stable = compute_weighted_score(w_stable, improvement=1.0, risk=0.8)
        score_adv = compute_weighted_score(w_adv, improvement=1.0, risk=0.8)
        self.assertGreater(score_stable, score_adv)

    def test_exploration_bonus_adds_value(self):
        w = get_target_weights("plateau")
        base = compute_weighted_score(w, improvement=0.5, risk=0.3)
        with_explore = compute_weighted_score(
            w, improvement=0.5, risk=0.3, exploration_bonus=1.0
        )
        self.assertGreater(with_explore, base)

    def test_novelty_bonus_adds_value(self):
        w = get_target_weights("plateau")
        base = compute_weighted_score(w, improvement=0.5, risk=0.3)
        with_novelty = compute_weighted_score(
            w, improvement=0.5, risk=0.3, novelty_bonus=1.0
        )
        self.assertGreater(with_novelty, base)

    def test_zero_inputs_zero_score(self):
        score = compute_weighted_score(DEFAULT_WEIGHTS, improvement=0.0, risk=0.0)
        self.assertAlmostEqual(score, 0.0, places=6)


# ─── Arbiter engine ──────────────────────────────────────────


class TestObjectiveArbiter(unittest.TestCase):
    def test_initial_state(self):
        arb = ObjectiveArbiter()
        self.assertEqual(arb.mode, "default")
        self.assertEqual(arb.weights, DEFAULT_WEIGHTS)
        self.assertEqual(arb.update_count, 0)

    def test_stable_update(self):
        arb = ObjectiveArbiter()
        result = arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        self.assertTrue(result.active)
        self.assertEqual(result.mode, "stable")
        self.assertEqual(arb.update_count, 1)

    def test_adversarial_update(self):
        arb = ObjectiveArbiter()
        result = arb.update(ContextSignals(context_type="adversarial"))
        self.assertEqual(result.mode, "adversarial")
        self.assertGreater(result.weights.risk_weight, DEFAULT_WEIGHTS.risk_weight)

    def test_mode_shift_reason(self):
        arb = ObjectiveArbiter()
        result = arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        self.assertIn("mode_shift:default->stable", result.shift_reason)

    def test_sustained_mode_reason(self):
        arb = ObjectiveArbiter()
        arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        result = arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        self.assertIn("mode_sustained:stable", result.shift_reason)

    def test_low_confidence_inactive(self):
        arb = ObjectiveArbiter()
        result = arb.update(
            ContextSignals(context_type="adversarial"),
            confidence=0.1,
        )
        self.assertFalse(result.active)
        self.assertEqual(arb.mode, "default")

    def test_boundary_confidence_accepted(self):
        arb = ObjectiveArbiter()
        result = arb.update(
            ContextSignals(context_type="stable", uncertainty=0.1),
            confidence=MIN_CONFIDENCE_FOR_ARBITRATION,
        )
        self.assertTrue(result.active)

    def test_reset(self):
        arb = ObjectiveArbiter()
        arb.update(ContextSignals(context_type="adversarial"))
        arb.reset()
        self.assertEqual(arb.mode, "default")
        self.assertEqual(arb.weights, DEFAULT_WEIGHTS)
        self.assertEqual(arb.update_count, 0)


# ─── Smooth mode transitions ─────────────────────────────────


class TestModeTransitions(unittest.TestCase):
    def test_gradual_shift_stable_to_adversarial(self):
        arb = ObjectiveArbiter()
        for _ in range(5):
            arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        risk_after_stable = arb.weights.risk_weight
        arb.update(ContextSignals(context_type="adversarial"))
        risk_after_one = arb.weights.risk_weight
        self.assertGreater(risk_after_one, risk_after_stable)
        target = get_target_weights("adversarial")
        self.assertLess(risk_after_one, target.risk_weight)

    def test_no_sign_reversal_under_consistent_signal(self):
        arb = ObjectiveArbiter()
        prev_risk = arb.weights.risk_weight
        deltas = []
        for _ in range(20):
            arb.update(ContextSignals(context_type="adversarial"))
            delta = arb.weights.risk_weight - prev_risk
            deltas.append(delta)
            prev_risk = arb.weights.risk_weight
        reversals = sum(
            1
            for i in range(1, len(deltas))
            if (deltas[i] > 0) != (deltas[i - 1] > 0)
            and abs(deltas[i]) > 1e-10
            and abs(deltas[i - 1]) > 1e-10
        )
        self.assertEqual(reversals, 0)

    def test_weights_always_bounded_during_transitions(self):
        arb = ObjectiveArbiter()
        modes = ["stable", "adversarial", "stable", "plateau", "stable"]
        for mode in modes:
            for _ in range(3):
                if mode == "plateau":
                    arb.update(
                        ContextSignals(
                            context_type="stable",
                            uncertainty=0.1,
                            exploration_stagnation=0.7,
                            improvement_trend=0.02,
                        )
                    )
                elif mode == "stable":
                    arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
                else:
                    arb.update(ContextSignals(context_type=mode))
                self.assertTrue(_is_bounded(arb.weights), f"out of bounds after {mode}")


# ─── Deterministic behavior ──────────────────────────────────


class TestDeterministicBehavior(unittest.TestCase):
    def test_same_inputs_same_output(self):
        arb1 = ObjectiveArbiter()
        arb2 = ObjectiveArbiter()
        signals = ContextSignals(context_type="adversarial", risk_level=0.8)
        r1 = arb1.update(signals)
        r2 = arb2.update(signals)
        self.assertEqual(r1.weights, r2.weights)
        self.assertEqual(r1.mode, r2.mode)

    def test_serialization_roundtrip(self):
        arb = ObjectiveArbiter()
        arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        result = arb.update(ContextSignals(context_type="adversarial"))
        d = result.to_dict()
        self.assertIn("mode", d)
        self.assertIn("weights", d)
        self.assertIn("reward_weight", d["weights"])


# ─── Trace integration ───────────────────────────────────────


class TestTraceIntegration(unittest.TestCase):
    def test_trace_fields(self):
        arb = ObjectiveArbiter()
        arb.update(ContextSignals(context_type="stable", uncertainty=0.1))
        fields = arb.get_trace_fields()
        self.assertIn("objective_arb_mode", fields)
        self.assertIn("objective_arb_reward_weight", fields)
        self.assertIn("objective_arb_risk_weight", fields)
        self.assertIn("objective_arb_stability_weight", fields)
        self.assertIn("objective_arb_shift_reason", fields)

    def test_decision_trace_has_arb_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
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
            objective_arb_mode="stable",
            objective_arb_reward_weight=0.65,
            objective_arb_risk_weight=0.15,
            objective_arb_stability_weight=0.2,
            objective_arb_shift_reason="mode_shift:default->stable",
        )
        d = t.to_dict()
        self.assertEqual(d["objective_arb_mode"], "stable")
        self.assertAlmostEqual(d["objective_arb_reward_weight"], 0.65, places=4)

    def test_trace_omits_arb_when_none(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        t = DecisionTrace(
            turn_id=0,
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
        )
        d = t.to_dict()
        self.assertNotIn("objective_arb_mode", d)

    def test_build_trace_accepts_arb_params(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            objective_arb_mode="adversarial",
            objective_arb_reward_weight=0.35,
            objective_arb_risk_weight=0.45,
            objective_arb_stability_weight=0.45,
            objective_arb_shift_reason="mode_shift:default->adversarial",
        )
        self.assertEqual(trace.objective_arb_mode, "adversarial")
        self.assertAlmostEqual(trace.objective_arb_reward_weight, 0.35)


# ─── Multi-world policy integration ──────────────────────────


class TestPolicyIntegration(unittest.TestCase):
    def test_multi_world_policy_accepts_weights(self):
        from umh.runtime_engine.multi_world_policy import evaluate_multi_world_policy
        from umh.world.simulation import SimulatedAction
        from umh.world.reasoning import WorldReasoningEngine
        from umh.world.types import (
            Entity,
            Observation,
            StateFact,
            WorldSnapshot,
        )

        snap = WorldSnapshot(
            entities=(Entity(entity_id="e1", entity_type="metric"),),
            relations=(),
            state_facts=(
                StateFact(
                    entity_id="e1",
                    key="revenue",
                    value=100.0,
                    confidence=0.9,
                    last_updated_turn=1,
                    update_count=5,
                ),
            ),
            observation_count=10,
            version=1,
        )
        obs = tuple(
            Observation(
                observation_id=f"obs_e1_revenue_{i}",
                timestamp_turn=i,
                source="test",
                entity_id="e1",
                signal_type="revenue",
                value=100.0 + i,
                confidence=0.9,
            )
            for i in range(10)
        )
        engine = WorldReasoningEngine()
        understanding = engine.derive_understanding(snap, obs)
        actions = (
            SimulatedAction(
                action_id="a1",
                action_type="improve",
                target_entity="e1",
            ),
        )
        adv_weights = get_target_weights("adversarial")
        result = evaluate_multi_world_policy(
            actions=actions,
            snapshot=snap,
            understanding=understanding,
            horizon=3,
            observation_history=obs,
            context_type="stable",
            uncertainty=0.0,
            objective_weights=adv_weights,
        )
        self.assertTrue(result.active)

    def test_weights_affect_scoring(self):
        reward_heavy = ObjectiveWeights(0.7, 0.1, 0.1, 0.0, 0.0)
        risk_heavy = ObjectiveWeights(0.3, 0.5, 0.1, 0.0, 0.0)
        score_reward = compute_weighted_score(reward_heavy, improvement=1.0, risk=0.5)
        score_risk = compute_weighted_score(risk_heavy, improvement=1.0, risk=0.5)
        self.assertGreater(score_reward, score_risk)


# ─── Fallback behavior ───────────────────────────────────────


class TestFallbackBehavior(unittest.TestCase):
    def test_no_arbitration_result_inactive(self):
        self.assertFalse(NO_ARBITRATION_RESULT.active)
        self.assertEqual(NO_ARBITRATION_RESULT.mode, "default")
        self.assertEqual(NO_ARBITRATION_RESULT.weights, DEFAULT_WEIGHTS)

    def test_default_weights_preserve_original_ranking(self):
        s1 = compute_weighted_score(DEFAULT_WEIGHTS, improvement=1.0, risk=0.2)
        s2 = compute_weighted_score(DEFAULT_WEIGHTS, improvement=0.5, risk=0.1)
        self.assertGreater(s1, s2)


# ─── No regression ───────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_objective_arbitration_imports(self):
        from umh.runtime_engine.objective_arbitration import (
            ObjectiveArbiter,
            ObjectiveWeights,
            ArbitrationResult,
            ContextSignals,
            compute_weighted_score,
            detect_objective_mode,
            smooth_weights,
        )

    def test_multi_world_policy_imports(self):
        from umh.runtime_engine.multi_world_policy import (
            evaluate_multi_world_policy,
            evaluate_action_across_worlds,
        )

    def test_decision_trace_imports(self):
        from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    def test_world_simulation_imports(self):
        from umh.world.simulation import (
            WorldSimulationEngine,
            SimulatedAction,
            SimulationResult,
        )

    def test_context_signals_serialization(self):
        s = ContextSignals(context_type="stable", uncertainty=0.2, risk_level=0.3)
        d = s.to_dict()
        self.assertEqual(d["context_type"], "stable")
        self.assertAlmostEqual(d["uncertainty"], 0.2, places=4)


if __name__ == "__main__":
    unittest.main()
