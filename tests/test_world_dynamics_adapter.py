"""Tests for WorldDynamicsAdapter — calibration-driven simulation adjustment.

Covers:
1. Bias update correctness
2. EMA behavior
3. Clamping
4. Stability over time
5. Deterministic behavior
6. No effect when gated off
7. Integration with simulation
8. Trace fields
9. No regressions
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.world.dynamics_adapter import (
    ADAPTER_EMA_ALPHA,
    BIAS_MAX,
    BIAS_MIN,
    CONFIDENCE_SCALE_MAX,
    CONFIDENCE_SCALE_MIN,
    DynamicsAdjustment,
    DynamicsAdjustmentState,
    MAX_UNCERTAINTY_FOR_ADAPTATION,
    MIN_CALIBRATION_CONFIDENCE,
    NEUTRAL_ADJUSTMENT,
    NEUTRAL_STATE,
    RISK_MULTIPLIER_MAX,
    RISK_MULTIPLIER_MIN,
    STABILITY_DECAY_MODIFIER_MAX,
    STABILITY_DECAY_MODIFIER_MIN,
    TREND_MULTIPLIER_MAX,
    TREND_MULTIPLIER_MIN,
    WorldDynamicsAdapter,
    bias_to_adjustment,
)
from umh.world.calibration import CalibrationSummary
from umh.world.types import (
    Entity,
    Observation,
    Relation,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import WorldReasoningEngine
from umh.world.simulation import (
    SimulatedAction,
    WorldSimulationEngine,
    step_world_dynamics,
    TREND_CARRY_FORWARD,
    RISK_PROPAGATION_PENALTY,
    STABILITY_DECAY,
)


def _make_summary(
    *,
    action_id: str = "test",
    avg_error: float = 0.3,
    max_error: float = 0.5,
    stability_error: float = 0.2,
    trend_error: float = 0.4,
    confidence_score: float = 0.7,
    error_count: int = 5,
    timestamp_step: int = 10,
) -> CalibrationSummary:
    return CalibrationSummary(
        action_id=action_id,
        avg_error=avg_error,
        max_error=max_error,
        stability_error=stability_error,
        trend_error=trend_error,
        confidence_score=confidence_score,
        error_count=error_count,
        timestamp_step=timestamp_step,
    )


def _make_snapshot(
    entities: list[tuple[str, str]] | None = None,
    facts: list[tuple[str, str, float]] | None = None,
    relations: list[tuple[str, str, str]] | None = None,
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
    rels = tuple(
        Relation(source_id=s, relation_type=rt, target_id=t, weight=1.0)
        for s, rt, t in (relations or [])
    )
    return WorldSnapshot(
        entities=ents,
        relations=rels,
        state_facts=sf,
        observation_count=obs_count,
        version=1,
    )


# ─── Test Classes ────────────────────────────────────────────────


class TestBiasUpdateCorrectness(unittest.TestCase):
    def test_single_update_changes_state(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(trend_error=0.5, avg_error=0.3)
        applied = adapter.update_from_calibration(summary, context_type="stable")
        self.assertTrue(applied)
        self.assertNotEqual(adapter.state, NEUTRAL_STATE)

    def test_trend_bias_direction(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(trend_error=0.8)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertGreater(adapter.state.trend_bias, 0.0)

    def test_risk_bias_direction(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(avg_error=0.6)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertGreater(adapter.state.risk_bias, 0.0)

    def test_stability_bias_direction(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(stability_error=0.7)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertGreater(adapter.state.stability_bias, 0.0)

    def test_confidence_bias_positive_when_high(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(confidence_score=0.9)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertGreater(adapter.state.confidence_bias, 0.0)

    def test_confidence_bias_negative_when_low(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(confidence_score=0.3)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertLess(adapter.state.confidence_bias, 0.0)

    def test_last_update_step_recorded(self):
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(timestamp_step=42)
        adapter.update_from_calibration(summary, context_type="stable")
        self.assertEqual(adapter.state.last_update_step, 42)


class TestEMABehavior(unittest.TestCase):
    def test_ema_converges_toward_signal(self):
        adapter = WorldDynamicsAdapter()
        for i in range(100):
            s = _make_summary(trend_error=0.5, timestamp_step=i)
            adapter.update_from_calibration(s, context_type="stable")
        self.assertAlmostEqual(adapter.state.trend_bias, 0.3, delta=0.15)

    def test_slow_ema_alpha(self):
        """First update should only shift by alpha * signal."""
        adapter = WorldDynamicsAdapter()
        summary = _make_summary(trend_error=1.0)
        adapter.update_from_calibration(summary, context_type="stable")
        expected = ADAPTER_EMA_ALPHA * 1.0
        self.assertAlmostEqual(adapter.state.trend_bias, expected, places=6)

    def test_ema_recency_weight(self):
        adapter = WorldDynamicsAdapter()
        for _ in range(50):
            adapter.update_from_calibration(
                _make_summary(trend_error=0.0), context_type="stable"
            )
        for _ in range(5):
            adapter.update_from_calibration(
                _make_summary(trend_error=1.0), context_type="stable"
            )
        self.assertGreater(adapter.state.trend_bias, 0.0)

    def test_multiple_summaries_sequential(self):
        adapter = WorldDynamicsAdapter()
        s1 = _make_summary(trend_error=0.2, timestamp_step=1)
        s2 = _make_summary(trend_error=0.8, timestamp_step=2)
        adapter.update_from_calibration(s1, context_type="stable")
        b1 = adapter.state.trend_bias
        adapter.update_from_calibration(s2, context_type="stable")
        b2 = adapter.state.trend_bias
        self.assertGreater(b2, b1)


class TestClamping(unittest.TestCase):
    def test_bias_bounded_upper(self):
        adapter = WorldDynamicsAdapter()
        for i in range(1000):
            s = _make_summary(
                trend_error=1.0, avg_error=1.0, stability_error=1.0, timestamp_step=i
            )
            adapter.update_from_calibration(s, context_type="stable")
        self.assertLessEqual(adapter.state.trend_bias, BIAS_MAX)
        self.assertLessEqual(adapter.state.risk_bias, BIAS_MAX)
        self.assertLessEqual(adapter.state.stability_bias, BIAS_MAX)

    def test_bias_bounded_lower(self):
        adapter = WorldDynamicsAdapter()
        for i in range(1000):
            s = _make_summary(
                trend_error=0.0,
                avg_error=0.0,
                stability_error=0.0,
                confidence_score=0.3,
                timestamp_step=i,
            )
            adapter.update_from_calibration(s, context_type="stable")
        self.assertGreaterEqual(adapter.state.trend_bias, BIAS_MIN)
        self.assertGreaterEqual(adapter.state.confidence_bias, BIAS_MIN)

    def test_adjustment_multipliers_bounded(self):
        state = DynamicsAdjustmentState(
            trend_bias=10.0,
            risk_bias=-10.0,
            stability_bias=5.0,
            confidence_bias=-5.0,
            last_update_step=0,
        )
        adj = bias_to_adjustment(state)
        self.assertGreaterEqual(adj.trend_multiplier, TREND_MULTIPLIER_MIN)
        self.assertLessEqual(adj.trend_multiplier, TREND_MULTIPLIER_MAX)
        self.assertGreaterEqual(adj.risk_multiplier, RISK_MULTIPLIER_MIN)
        self.assertLessEqual(adj.risk_multiplier, RISK_MULTIPLIER_MAX)
        self.assertGreaterEqual(
            adj.stability_decay_modifier, STABILITY_DECAY_MODIFIER_MIN
        )
        self.assertLessEqual(adj.stability_decay_modifier, STABILITY_DECAY_MODIFIER_MAX)
        self.assertGreaterEqual(adj.confidence_scale, CONFIDENCE_SCALE_MIN)
        self.assertLessEqual(adj.confidence_scale, CONFIDENCE_SCALE_MAX)

    def test_neutral_state_produces_neutral_adjustment(self):
        adj = bias_to_adjustment(NEUTRAL_STATE)
        self.assertAlmostEqual(adj.trend_multiplier, 1.0, places=6)
        self.assertAlmostEqual(adj.risk_multiplier, 1.0, places=6)
        self.assertAlmostEqual(adj.stability_decay_modifier, 0.0, places=6)
        self.assertAlmostEqual(adj.confidence_scale, 1.0, places=6)


class TestStabilityOverTime(unittest.TestCase):
    def test_no_sign_reversal_under_consistent_signal(self):
        """Bias should not reverse sign under consistently positive error signals."""
        adapter = WorldDynamicsAdapter()
        biases = []
        for i in range(50):
            adapter.update_from_calibration(
                _make_summary(trend_error=0.4, timestamp_step=i),
                context_type="stable",
            )
            biases.append(adapter.state.trend_bias)
        sign_reversals = sum(
            1 for j in range(1, len(biases)) if biases[j] * biases[j - 1] < 0
        )
        self.assertEqual(sign_reversals, 0)

    def test_gradual_change(self):
        adapter = WorldDynamicsAdapter()
        prev_bias = 0.0
        for i in range(20):
            adapter.update_from_calibration(
                _make_summary(trend_error=0.8, timestamp_step=i),
                context_type="stable",
            )
            curr = adapter.state.trend_bias
            self.assertLess(abs(curr - prev_bias), 0.1)
            prev_bias = curr

    def test_reset_to_neutral(self):
        adapter = WorldDynamicsAdapter()
        adapter.update_from_calibration(
            _make_summary(trend_error=0.5), context_type="stable"
        )
        self.assertTrue(adapter.is_active())
        adapter.reset()
        self.assertFalse(adapter.is_active())
        self.assertEqual(adapter.state, NEUTRAL_STATE)


class TestDeterministicBehavior(unittest.TestCase):
    def test_same_inputs_same_outputs(self):
        summaries = [
            _make_summary(trend_error=0.3 + i * 0.05, timestamp_step=i)
            for i in range(10)
        ]

        adapter1 = WorldDynamicsAdapter()
        adapter2 = WorldDynamicsAdapter()
        for s in summaries:
            adapter1.update_from_calibration(s, context_type="stable")
            adapter2.update_from_calibration(s, context_type="stable")

        self.assertEqual(adapter1.state, adapter2.state)
        self.assertEqual(adapter1.get_adjustments(), adapter2.get_adjustments())

    def test_order_matters(self):
        s_low = _make_summary(trend_error=0.1, timestamp_step=1)
        s_high = _make_summary(trend_error=0.9, timestamp_step=2)

        a1 = WorldDynamicsAdapter()
        a1.update_from_calibration(s_low, context_type="stable")
        a1.update_from_calibration(s_high, context_type="stable")

        a2 = WorldDynamicsAdapter()
        a2.update_from_calibration(s_high, context_type="stable")
        a2.update_from_calibration(s_low, context_type="stable")

        self.assertNotEqual(a1.state.trend_bias, a2.state.trend_bias)

    def test_adjustment_to_dict_roundtrip(self):
        adapter = WorldDynamicsAdapter()
        adapter.update_from_calibration(
            _make_summary(trend_error=0.5), context_type="stable"
        )
        d = adapter.get_adjustments().to_dict()
        self.assertIn("trend_multiplier", d)
        self.assertIn("risk_multiplier", d)
        self.assertIn("stability_decay_modifier", d)
        self.assertIn("confidence_scale", d)


class TestGatingOffBehavior(unittest.TestCase):
    def test_non_stable_context_rejected(self):
        adapter = WorldDynamicsAdapter()
        for ctx in [None, "volatile", "exploratory", "unknown", ""]:
            applied = adapter.update_from_calibration(_make_summary(), context_type=ctx)
            self.assertFalse(applied)
        self.assertEqual(adapter.state, NEUTRAL_STATE)

    def test_high_uncertainty_rejected(self):
        adapter = WorldDynamicsAdapter()
        applied = adapter.update_from_calibration(
            _make_summary(),
            context_type="stable",
            uncertainty=0.8,
        )
        self.assertFalse(applied)
        self.assertEqual(adapter.state, NEUTRAL_STATE)

    def test_low_confidence_rejected(self):
        adapter = WorldDynamicsAdapter()
        applied = adapter.update_from_calibration(
            _make_summary(confidence_score=0.1),
            context_type="stable",
        )
        self.assertFalse(applied)
        self.assertEqual(adapter.state, NEUTRAL_STATE)

    def test_boundary_uncertainty_rejected(self):
        adapter = WorldDynamicsAdapter()
        applied = adapter.update_from_calibration(
            _make_summary(),
            context_type="stable",
            uncertainty=MAX_UNCERTAINTY_FOR_ADAPTATION + 0.01,
        )
        self.assertFalse(applied)
        self.assertEqual(adapter.state, NEUTRAL_STATE)

    def test_boundary_confidence_at_min_accepted(self):
        adapter = WorldDynamicsAdapter()
        applied = adapter.update_from_calibration(
            _make_summary(confidence_score=MIN_CALIBRATION_CONFIDENCE),
            context_type="stable",
        )
        self.assertTrue(applied)

    def test_just_above_min_confidence_accepted(self):
        adapter = WorldDynamicsAdapter()
        applied = adapter.update_from_calibration(
            _make_summary(confidence_score=MIN_CALIBRATION_CONFIDENCE + 0.01),
            context_type="stable",
        )
        self.assertTrue(applied)


class TestSimulationIntegration(unittest.TestCase):
    def _build_world(self):
        snap = _make_snapshot(
            entities=[("e1", "metric"), ("e2", "metric")],
            facts=[
                ("e1", "revenue", 100.0),
                ("e2", "cost", 50.0),
            ],
            relations=[("e1", "impacts", "e2")],
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
        ) + tuple(
            Observation(
                observation_id=f"obs_e2_cost_{i}",
                timestamp_turn=i,
                source="test",
                entity_id="e2",
                signal_type="cost",
                value=50.0 + i * 0.5,
                confidence=0.9,
            )
            for i in range(10)
        )
        engine = WorldReasoningEngine()
        understanding = engine.derive_understanding(snap, obs)
        return snap, understanding, obs

    def test_neutral_adjustment_matches_no_adjustment(self):
        snap, und, obs = self._build_world()
        engine = WorldSimulationEngine()
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.1},
        )
        r1 = engine.simulate_action(
            snap, und, action, horizon=3, observation_history=obs
        )
        r2 = engine.simulate_action(
            snap,
            und,
            action,
            horizon=3,
            observation_history=obs,
            adjustment=NEUTRAL_ADJUSTMENT,
        )
        self.assertEqual(r1.final_snapshot_version, r2.final_snapshot_version)
        self.assertAlmostEqual(
            r1.aggregate_improvement, r2.aggregate_improvement, places=8
        )
        self.assertAlmostEqual(r1.aggregate_risk, r2.aggregate_risk, places=8)
        self.assertAlmostEqual(r1.confidence, r2.confidence, places=8)

    def test_high_trend_multiplier_increases_trend_effect(self):
        snap, und, obs = self._build_world()
        engine = WorldSimulationEngine()
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
        )
        adj_high = DynamicsAdjustment(
            trend_multiplier=1.3,
            risk_multiplier=1.0,
            stability_decay_modifier=0.0,
            confidence_scale=1.0,
        )
        r_base = engine.simulate_action(
            snap, und, action, horizon=3, observation_history=obs
        )
        r_high = engine.simulate_action(
            snap,
            und,
            action,
            horizon=3,
            observation_history=obs,
            adjustment=adj_high,
        )
        base_deltas = sum(
            1 for s in r_base.steps for d in s.deltas if d.delta_type == "trend_carry"
        )
        high_deltas = sum(
            1 for s in r_high.steps for d in s.deltas if d.delta_type == "trend_carry"
        )
        self.assertGreaterEqual(high_deltas, base_deltas)

    def test_step_dynamics_with_adjustment(self):
        snap = _make_snapshot(
            entities=[("e1", "metric")],
            facts=[("e1", "revenue", 100.0)],
        )
        obs = tuple(
            Observation(
                observation_id=f"obs_e1_rev_{i}",
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
        und = engine.derive_understanding(snap, obs)

        has_up_trend = any(
            t.direction == "up" for a in und.entity_assessments for t in a.trend_summary
        )
        if not has_up_trend:
            return

        adj = DynamicsAdjustment(
            trend_multiplier=1.3,
            risk_multiplier=1.0,
            stability_decay_modifier=0.0,
            confidence_scale=1.0,
        )
        snap_neutral, deltas_neutral = step_world_dynamics(snap, und)
        snap_adj, deltas_adj = step_world_dynamics(snap, und, adjustment=adj)

        neutral_trend = [d for d in deltas_neutral if d.delta_type == "trend_carry"]
        adj_trend = [d for d in deltas_adj if d.delta_type == "trend_carry"]
        if neutral_trend and adj_trend:
            n_mag = abs(float(neutral_trend[0].after) - float(neutral_trend[0].before))
            a_mag = abs(float(adj_trend[0].after) - float(adj_trend[0].before))
            self.assertGreater(a_mag, n_mag)

    def test_confidence_scale_affects_result(self):
        snap, und, obs = self._build_world()
        engine = WorldSimulationEngine()
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
        )
        adj_low = DynamicsAdjustment(
            trend_multiplier=1.0,
            risk_multiplier=1.0,
            stability_decay_modifier=0.0,
            confidence_scale=0.8,
        )
        adj_high = DynamicsAdjustment(
            trend_multiplier=1.0,
            risk_multiplier=1.0,
            stability_decay_modifier=0.0,
            confidence_scale=1.2,
        )
        r_low = engine.simulate_action(
            snap,
            und,
            action,
            horizon=3,
            observation_history=obs,
            adjustment=adj_low,
        )
        r_high = engine.simulate_action(
            snap,
            und,
            action,
            horizon=3,
            observation_history=obs,
            adjustment=adj_high,
        )
        self.assertLessEqual(r_low.confidence, r_high.confidence)

    def test_simulate_actions_passes_adjustment(self):
        snap, und, obs = self._build_world()
        engine = WorldSimulationEngine()
        actions = (
            SimulatedAction(action_id="a1", action_type="boost", target_entity="e1"),
        )
        adj = DynamicsAdjustment(
            trend_multiplier=1.2,
            risk_multiplier=0.8,
            stability_decay_modifier=0.01,
            confidence_scale=0.9,
        )
        results = engine.simulate_actions(
            snap,
            und,
            actions,
            horizon=2,
            observation_history=obs,
            adjustment=adj,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action_id, "a1")


class TestTraceFields(unittest.TestCase):
    def test_trace_fields_neutral(self):
        adapter = WorldDynamicsAdapter()
        fields = adapter.get_trace_fields()
        self.assertAlmostEqual(fields["dynamics_trend_multiplier"], 1.0)
        self.assertAlmostEqual(fields["dynamics_risk_multiplier"], 1.0)
        self.assertAlmostEqual(fields["dynamics_stability_modifier"], 0.0)
        self.assertAlmostEqual(fields["dynamics_confidence_scale"], 1.0)

    def test_trace_fields_after_update(self):
        adapter = WorldDynamicsAdapter()
        adapter.update_from_calibration(
            _make_summary(trend_error=0.8, avg_error=0.6),
            context_type="stable",
        )
        fields = adapter.get_trace_fields()
        self.assertNotAlmostEqual(fields["dynamics_trend_multiplier"], 1.0)

    def test_decision_trace_has_dynamics_fields(self):
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
            dynamics_trend_multiplier=1.1,
            dynamics_risk_multiplier=0.9,
            dynamics_stability_modifier=0.01,
            dynamics_confidence_scale=1.05,
        )
        self.assertAlmostEqual(t.dynamics_trend_multiplier, 1.1)
        d = t.to_dict()
        self.assertIn("dynamics_trend_multiplier", d)
        self.assertAlmostEqual(d["dynamics_trend_multiplier"], 1.1, places=4)

    def test_build_trace_accepts_dynamics_params(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(
            turn_id=1,
            dynamics_trend_multiplier=1.2,
            dynamics_risk_multiplier=0.8,
            dynamics_stability_modifier=-0.01,
            dynamics_confidence_scale=1.1,
        )
        self.assertAlmostEqual(t.dynamics_trend_multiplier, 1.2)
        self.assertAlmostEqual(t.dynamics_risk_multiplier, 0.8)
        self.assertAlmostEqual(t.dynamics_stability_modifier, -0.01)
        self.assertAlmostEqual(t.dynamics_confidence_scale, 1.1)

    def test_trace_omits_dynamics_when_none(self):
        from umh.runtime_engine.decision_trace import build_trace

        t = build_trace(turn_id=1)
        d = t.to_dict()
        self.assertNotIn("dynamics_trend_multiplier", d)

    def test_state_to_dict(self):
        state = DynamicsAdjustmentState(
            trend_bias=0.1,
            risk_bias=-0.05,
            stability_bias=0.03,
            confidence_bias=0.02,
            last_update_step=5,
        )
        d = state.to_dict()
        self.assertAlmostEqual(d["trend_bias"], 0.1, places=4)
        self.assertEqual(d["last_update_step"], 5)

    def test_adjustment_to_dict(self):
        adj = DynamicsAdjustment(
            trend_multiplier=1.15,
            risk_multiplier=0.85,
            stability_decay_modifier=0.01,
            confidence_scale=1.1,
        )
        d = adj.to_dict()
        self.assertAlmostEqual(d["trend_multiplier"], 1.15, places=4)


class TestAdapterEndToEnd(unittest.TestCase):
    def test_full_cycle(self):
        """Adapter receives summaries → biases accumulate → adjustments change."""
        adapter = WorldDynamicsAdapter()

        self.assertFalse(adapter.is_active())
        adj0 = adapter.get_adjustments()
        self.assertEqual(adj0, NEUTRAL_ADJUSTMENT)

        for i in range(10):
            adapter.update_from_calibration(
                _make_summary(
                    trend_error=0.6,
                    avg_error=0.4,
                    stability_error=0.3,
                    confidence_score=0.8,
                    timestamp_step=i,
                ),
                context_type="stable",
            )

        self.assertTrue(adapter.is_active())
        adj = adapter.get_adjustments()
        self.assertNotEqual(adj.trend_multiplier, 1.0)
        self.assertNotEqual(adj.risk_multiplier, 1.0)

        self.assertGreaterEqual(adj.trend_multiplier, TREND_MULTIPLIER_MIN)
        self.assertLessEqual(adj.trend_multiplier, TREND_MULTIPLIER_MAX)


class TestNoRegression(unittest.TestCase):
    def test_world_dynamics_adapter_imports(self):
        from umh.world.dynamics_adapter import (
            WorldDynamicsAdapter,
            DynamicsAdjustment,
            DynamicsAdjustmentState,
            NEUTRAL_ADJUSTMENT,
        )

        self.assertIsNotNone(WorldDynamicsAdapter)

    def test_world_simulation_imports(self):
        from umh.world.simulation import WorldSimulationEngine, step_world_dynamics

        self.assertIsNotNone(WorldSimulationEngine)

    def test_world_calibration_imports(self):
        from umh.world.calibration import WorldCalibrationEngine

        self.assertIsNotNone(WorldCalibrationEngine)

    def test_decision_trace_imports(self):
        from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

        self.assertIsNotNone(DecisionTrace)

    def test_world_reasoning_imports(self):
        from umh.world.reasoning import WorldReasoningEngine

        self.assertIsNotNone(WorldReasoningEngine)


if __name__ == "__main__":
    unittest.main()
