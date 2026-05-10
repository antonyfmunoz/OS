"""Tests for eos_ai.world_simulation — bounded deterministic forward model."""

from __future__ import annotations

import copy
import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.world.types import (
    Entity,
    Observation,
    Relation,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import (
    EntityAssessment,
    EntityTrend,
    WorldReasoningEngine,
    WorldUnderstanding,
)
from umh.world.simulation import (
    BOOST_DEFAULT_MAGNITUDE,
    MAX_CANDIDATE_ACTIONS,
    MAX_DERIVED_ACTIONS,
    MAX_HORIZON,
    RISK_PROPAGATION_PENALTY,
    STABILITY_DECAY,
    STABILIZE_REDUCTION,
    SUPPRESS_DEFAULT_MAGNITUDE,
    TREND_CARRY_FORWARD,
    SimulatedAction,
    SimulationResult,
    SimulationStep,
    StateDelta,
    WorldSimulationEngine,
    apply_action_to_snapshot,
    derive_simulation_actions,
    recompute_understanding,
    step_world_dynamics,
    _compute_aggregate_improvement,
    _compute_aggregate_risk,
    _compute_simulation_confidence,
)


# ─── Test helpers ───────────────────────────────────────────────


def _entity(eid: str, etype: str = "generic") -> Entity:
    return Entity(entity_id=eid, entity_type=etype, attributes={})


def _fact(
    entity_id: str,
    key: str,
    value: float | int | str | bool | None,
    confidence: float = 0.8,
    turn: int = 1,
) -> StateFact:
    return StateFact(
        entity_id=entity_id,
        key=key,
        value=value,
        confidence=confidence,
        last_updated_turn=turn,
        update_count=1,
    )


def _relation(src: str, rtype: str, tgt: str, weight: float = 1.0) -> Relation:
    return Relation(source_id=src, relation_type=rtype, target_id=tgt, weight=weight)


def _obs(
    entity_id: str,
    signal_type: str,
    value: float,
    turn: int,
    confidence: float = 0.8,
) -> Observation:
    return Observation(
        observation_id=f"obs_{entity_id}_{signal_type}_{turn}",
        timestamp_turn=turn,
        source="test",
        entity_id=entity_id,
        signal_type=signal_type,
        value=value,
        confidence=confidence,
        metadata={},
    )


def _snapshot(
    entities: list[Entity] | None = None,
    relations: list[Relation] | None = None,
    facts: list[StateFact] | None = None,
    obs_count: int = 10,
    version: int = 1,
) -> WorldSnapshot:
    return WorldSnapshot(
        entities=tuple(entities or []),
        relations=tuple(relations or []),
        state_facts=tuple(facts or []),
        observation_count=obs_count,
        version=version,
    )


def _understanding(
    assessments: list[EntityAssessment] | None = None,
    global_flags: list[str] | None = None,
    version: int = 1,
) -> WorldUnderstanding:
    a = assessments or []
    return WorldUnderstanding(
        entity_assessments=tuple(a),
        relation_impacts=(),
        global_flags=tuple(global_flags or []),
        snapshot_version=version,
        derived_count=len(a),
    )


def _assessment(
    entity_id: str,
    health: str = "good",
    stability: str = "stable",
    trends: list[EntityTrend] | None = None,
    risk_flags: list[str] | None = None,
    confidence: float = 0.8,
) -> EntityAssessment:
    return EntityAssessment(
        entity_id=entity_id,
        health=health,
        stability=stability,
        trend_summary=tuple(trends or []),
        risk_flags=tuple(risk_flags or []),
        confidence=confidence,
    )


def _trend(
    entity_id: str,
    key: str,
    direction: str = "up",
    slope: float = 0.1,
    confidence: float = 0.8,
) -> EntityTrend:
    return EntityTrend(
        entity_id=entity_id,
        key=key,
        direction=direction,
        slope=slope,
        confidence=confidence,
        reason=f"test {direction}",
    )


# ─── A. Action application ─────────────────────────────────────


class TestBoostAction(unittest.TestCase):
    def test_boost_increases_numeric_facts(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.5},
        )
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].delta_type, "numeric_shift")
        self.assertAlmostEqual(deltas[0].after, 5.5)
        fact = next(f for f in new_snap.state_facts if f.key == "score")
        self.assertAlmostEqual(fact.value, 5.5)

    def test_boost_default_magnitude(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 1.0)],
        )
        action = SimulatedAction(
            action_id="a1", action_type="boost", target_entity="e1"
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertAlmostEqual(deltas[0].after, 1.0 + BOOST_DEFAULT_MAGNITUDE)

    def test_boost_no_numeric_facts_produces_noop(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "status", "active")],
        )
        action = SimulatedAction(
            action_id="a1", action_type="boost", target_entity="e1"
        )
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].delta_type, "no_op")

    def test_boost_no_target_entity(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        action = SimulatedAction(action_id="a1", action_type="boost")
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 0)


class TestSuppressAction(unittest.TestCase):
    def test_suppress_decreases_numeric_facts(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="suppress",
            target_entity="e1",
            parameters={"magnitude": 0.3},
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "numeric_shift")
        self.assertAlmostEqual(deltas[0].after, 4.7)

    def test_suppress_default_magnitude(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "v", 2.0)],
        )
        action = SimulatedAction(
            action_id="a1", action_type="suppress", target_entity="e1"
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertAlmostEqual(deltas[0].after, 2.0 - SUPPRESS_DEFAULT_MAGNITUDE)


class TestStabilizeAction(unittest.TestCase):
    def test_stabilize_reduces_risk_keys(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "risk_score", 0.8)],
        )
        action = SimulatedAction(
            action_id="a1", action_type="stabilize", target_entity="e1"
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].delta_type, "numeric_shift")
        self.assertAlmostEqual(deltas[0].after, 0.8 - STABILIZE_REDUCTION)

    def test_stabilize_no_risk_keys_produces_noop(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        action = SimulatedAction(
            action_id="a1", action_type="stabilize", target_entity="e1"
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "no_op")


class TestLinkAction(unittest.TestCase):
    def test_link_adds_relation(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="link",
            target_entity="e1",
            parameters={"other_entity": "e2", "relation_type": "depends_on"},
        )
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].delta_type, "relation_added")
        self.assertEqual(len(new_snap.relations), 1)
        self.assertEqual(new_snap.relations[0].source_id, "e1")
        self.assertEqual(new_snap.relations[0].target_id, "e2")

    def test_link_duplicate_produces_noop(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            relations=[_relation("e1", "related_to", "e2")],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="link",
            target_entity="e1",
            parameters={"other_entity": "e2"},
        )
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "no_op")
        self.assertEqual(len(new_snap.relations), 1)

    def test_link_missing_other_entity(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        action = SimulatedAction(action_id="a1", action_type="link", target_entity="e1")
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "no_op")


class TestUnlinkAction(unittest.TestCase):
    def test_unlink_removes_relation(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            relations=[_relation("e1", "related_to", "e2")],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="unlink",
            target_entity="e1",
            parameters={"other_entity": "e2"},
        )
        new_snap, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].delta_type, "relation_removed")
        self.assertEqual(len(new_snap.relations), 0)

    def test_unlink_nonexistent_produces_noop(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        action = SimulatedAction(
            action_id="a1",
            action_type="unlink",
            target_entity="e1",
            parameters={"other_entity": "e2"},
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "no_op")


class TestUnknownAction(unittest.TestCase):
    def test_unknown_action_type_produces_noop(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        action = SimulatedAction(
            action_id="a1", action_type="teleport", target_entity="e1"
        )
        _, deltas = apply_action_to_snapshot(snap, action)
        self.assertEqual(deltas[0].delta_type, "no_op")
        self.assertIn("unknown action type", deltas[0].reason)


# ─── B. Dynamics ───────────────────────────────────────────────


class TestWorldDynamics(unittest.TestCase):
    def test_up_trending_entity_continues_upward(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment(
                    "e1",
                    trends=[_trend("e1", "score", "up")],
                )
            ]
        )
        new_snap, deltas = step_world_dynamics(snap, understanding)
        score_delta = next(
            (d for d in deltas if d.key == "score" and d.delta_type == "trend_carry"),
            None,
        )
        self.assertIsNotNone(score_delta)
        self.assertGreater(score_delta.after, score_delta.before)

    def test_down_trending_entity_continues_downward(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment(
                    "e1",
                    trends=[_trend("e1", "score", "down", slope=-0.1)],
                )
            ]
        )
        _, deltas = step_world_dynamics(snap, understanding)
        score_delta = next(
            (d for d in deltas if d.key == "score" and d.delta_type == "trend_carry"),
            None,
        )
        self.assertIsNotNone(score_delta)
        self.assertLess(score_delta.after, score_delta.before)

    def test_volatile_entity_no_trend_boost(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment(
                    "e1",
                    trends=[_trend("e1", "score", "volatile")],
                )
            ]
        )
        _, deltas = step_world_dynamics(snap, understanding)
        trend_deltas = [d for d in deltas if d.delta_type == "trend_carry"]
        self.assertEqual(len(trend_deltas), 0)

    def test_risk_propagation_single_hop(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            relations=[_relation("e1", "depends_on", "e2")],
            facts=[_fact("e1", "v", 1.0), _fact("e2", "w", 3.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment("e1", health="bad"),
                _assessment("e2", health="good"),
            ]
        )
        _, deltas = step_world_dynamics(snap, understanding)
        risk_deltas = [d for d in deltas if d.delta_type == "risk_propagation"]
        self.assertTrue(len(risk_deltas) > 0)
        for rd in risk_deltas:
            self.assertEqual(rd.entity_id, "e2")
            self.assertLess(rd.after, rd.before)

    def test_stable_entity_no_aggressive_degradation(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment("e1", health="good", stability="stable"),
            ]
        )
        _, deltas = step_world_dynamics(snap, understanding)
        decay_deltas = [d for d in deltas if d.delta_type == "stability_decay"]
        self.assertEqual(len(decay_deltas), 0)

    def test_unstable_entity_decays(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        understanding = _understanding(
            assessments=[
                _assessment("e1", stability="unstable"),
            ]
        )
        _, deltas = step_world_dynamics(snap, understanding)
        decay_deltas = [d for d in deltas if d.delta_type == "stability_decay"]
        self.assertTrue(len(decay_deltas) > 0)
        for dd in decay_deltas:
            self.assertLess(dd.after, dd.before)


# ─── C. Recomputed understanding ───────────────────────────────


class TestRecomputedUnderstanding(unittest.TestCase):
    def test_recompute_produces_understanding(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
            obs_count=10,
        )
        result = recompute_understanding(snap)
        self.assertIsInstance(result, WorldUnderstanding)
        self.assertEqual(len(result.entity_assessments), 1)

    def test_classification_can_change_across_steps(self) -> None:
        engine = WorldSimulationEngine()
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[
                _fact("e1", "risk_score", 0.9, confidence=0.9),
                _fact("e1", "error_rate", 0.8, confidence=0.9),
            ],
            obs_count=10,
        )
        obs = tuple(_obs("e1", "risk_score", 0.9, t) for t in range(5)) + tuple(
            _obs("e1", "error_rate", 0.8, t) for t in range(5)
        )

        initial_und = recompute_understanding(snap, obs)

        action = SimulatedAction(
            action_id="a1",
            action_type="stabilize",
            target_entity="e1",
        )
        result = engine.simulate_action(
            snap, initial_und, action, horizon=1, observation_history=obs
        )
        self.assertIsInstance(result.final_world_understanding, WorldUnderstanding)


# ─── D. Aggregate metrics ──────────────────────────────────────


class TestAggregateMetrics(unittest.TestCase):
    def test_improvement_increases_when_health_improves(self) -> None:
        initial = _understanding(
            assessments=[_assessment("e1", health="bad")],
        )
        final = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        improvement = _compute_aggregate_improvement(initial, final)
        self.assertGreater(improvement, 0.0)

    def test_no_improvement_when_unchanged(self) -> None:
        initial = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        final = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        improvement = _compute_aggregate_improvement(initial, final)
        self.assertEqual(improvement, 0.0)

    def test_risk_increases_when_world_degrades(self) -> None:
        initial = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        final = _understanding(
            assessments=[_assessment("e1", health="bad")],
        )
        risk = _compute_aggregate_risk(initial, final)
        self.assertGreater(risk, 0.0)

    def test_risk_zero_when_unchanged(self) -> None:
        initial = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        risk = _compute_aggregate_risk(initial, initial)
        self.assertEqual(risk, 0.0)

    def test_improvement_bounded(self) -> None:
        initial = _understanding(
            assessments=[_assessment(f"e{i}", health="bad") for i in range(20)],
            global_flags=["world_degrading", "world_volatile", "risk_cluster_detected"],
        )
        final = _understanding(
            assessments=[_assessment(f"e{i}", health="good") for i in range(20)],
        )
        improvement = _compute_aggregate_improvement(initial, final)
        self.assertGreaterEqual(improvement, 0.0)
        self.assertLessEqual(improvement, 1.0)

    def test_risk_bounded(self) -> None:
        initial = _understanding(
            assessments=[_assessment("e1", health="good")],
        )
        final = _understanding(
            assessments=[
                _assessment(f"e{i}", health="bad", stability="volatile")
                for i in range(20)
            ],
            global_flags=["world_degrading", "world_volatile"],
        )
        risk = _compute_aggregate_risk(initial, final)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_confidence_with_good_data(self) -> None:
        understanding = _understanding(
            assessments=[
                _assessment("e1", confidence=0.9),
                _assessment("e2", confidence=0.85),
            ],
        )
        conf = _compute_simulation_confidence(understanding, 30)
        self.assertGreater(conf, 0.3)
        self.assertLessEqual(conf, 1.0)

    def test_confidence_with_sparse_data(self) -> None:
        understanding = _understanding(
            assessments=[
                _assessment("e1", confidence=0.3),
            ],
        )
        conf = _compute_simulation_confidence(understanding, 1)
        self.assertGreater(conf, 0.0)
        self.assertLess(conf, 0.5)


# ─── E. Safety/invariants ──────────────────────────────────────


class TestSafetyInvariants(unittest.TestCase):
    def test_input_snapshot_never_mutated(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        original_version = snap.version
        original_facts = snap.state_facts

        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 1.0},
        )
        new_snap, _ = apply_action_to_snapshot(snap, action)

        self.assertEqual(snap.version, original_version)
        self.assertEqual(snap.state_facts, original_facts)
        self.assertNotEqual(new_snap.state_facts, original_facts)

    def test_simulation_is_deterministic(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1"), _entity("e2")],
            facts=[_fact("e1", "score", 5.0), _fact("e2", "v", 3.0)],
            obs_count=10,
        )
        understanding = _understanding(
            assessments=[
                _assessment("e1", health="bad", trends=[_trend("e1", "score", "down")]),
                _assessment("e2", health="good"),
            ]
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.5},
        )
        engine = WorldSimulationEngine()
        r1 = engine.simulate_action(snap, understanding, action, horizon=2)
        r2 = engine.simulate_action(snap, understanding, action, horizon=2)

        self.assertEqual(r1.aggregate_improvement, r2.aggregate_improvement)
        self.assertEqual(r1.aggregate_risk, r2.aggregate_risk)
        self.assertEqual(r1.final_snapshot_version, r2.final_snapshot_version)
        self.assertEqual(len(r1.steps), len(r2.steps))
        for s1, s2 in zip(r1.steps, r2.steps):
            self.assertEqual(len(s1.deltas), len(s2.deltas))

    def test_bounded_horizon(self) -> None:
        snap = _snapshot(entities=[_entity("e1")], facts=[_fact("e1", "v", 1.0)])
        und = _understanding(assessments=[_assessment("e1")])
        action = SimulatedAction(
            action_id="a1", action_type="boost", target_entity="e1"
        )
        engine = WorldSimulationEngine()

        result = engine.simulate_action(snap, und, action, horizon=100)
        self.assertEqual(result.horizon, MAX_HORIZON)

        result2 = engine.simulate_action(snap, und, action, horizon=0)
        self.assertEqual(result2.horizon, 1)

    def test_bounded_candidate_set(self) -> None:
        actions = tuple(
            SimulatedAction(action_id=f"a{i}", action_type="boost", target_entity="e1")
            for i in range(20)
        )
        snap = _snapshot(entities=[_entity("e1")], facts=[_fact("e1", "v", 1.0)])
        und = _understanding(assessments=[_assessment("e1")])
        engine = WorldSimulationEngine()
        results = engine.simulate_actions(snap, und, actions, horizon=1)
        self.assertEqual(len(results), MAX_CANDIDATE_ACTIONS)


# ─── Candidate action derivation ──────────────────────────────


class TestDeriveSimulationActions(unittest.TestCase):
    def test_bad_entity_gets_boost(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 2.0)],
        )
        und = _understanding(
            assessments=[_assessment("e1", health="bad")],
        )
        actions = derive_simulation_actions(snap, und)
        self.assertTrue(len(actions) > 0)
        self.assertEqual(actions[0].action_type, "boost")

    def test_volatile_entity_gets_stabilize(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        und = _understanding(
            assessments=[_assessment("e1", health="good", stability="volatile")],
        )
        actions = derive_simulation_actions(snap, und)
        self.assertTrue(len(actions) > 0)
        self.assertEqual(actions[0].action_type, "stabilize")

    def test_risky_entity_gets_suppress(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 5.0)],
        )
        und = _understanding(
            assessments=[
                _assessment(
                    "e1",
                    health="good",
                    stability="stable",
                    risk_flags=["declining:score"],
                ),
            ],
        )
        actions = derive_simulation_actions(snap, und)
        self.assertTrue(len(actions) > 0)
        self.assertEqual(actions[0].action_type, "suppress")

    def test_healthy_entity_no_actions(self) -> None:
        snap = _snapshot(entities=[_entity("e1")])
        und = _understanding(
            assessments=[_assessment("e1", health="good", stability="stable")],
        )
        actions = derive_simulation_actions(snap, und)
        self.assertEqual(len(actions), 0)

    def test_capped_at_max(self) -> None:
        entities = [_entity(f"e{i}") for i in range(10)]
        facts = [_fact(f"e{i}", "v", 1.0) for i in range(10)]
        snap = _snapshot(entities=entities, facts=facts)
        und = _understanding(
            assessments=[_assessment(f"e{i}", health="bad") for i in range(10)],
        )
        actions = derive_simulation_actions(snap, und)
        self.assertLessEqual(len(actions), MAX_DERIVED_ACTIONS)


# ─── Full simulation engine ────────────────────────────────────


class TestWorldSimulationEngine(unittest.TestCase):
    def test_simulate_action_produces_result(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "score", 3.0)],
            obs_count=10,
        )
        und = _understanding(
            assessments=[_assessment("e1", health="watch")],
        )
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.5},
        )
        engine = WorldSimulationEngine()
        result = engine.simulate_action(snap, und, action, horizon=2)

        self.assertIsInstance(result, SimulationResult)
        self.assertEqual(result.action_id, "a1")
        self.assertEqual(result.horizon, 2)
        self.assertEqual(len(result.steps), 2)
        self.assertIsInstance(result.final_world_snapshot, WorldSnapshot)
        self.assertIsInstance(result.final_world_understanding, WorldUnderstanding)

    def test_simulate_actions_multiple(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "v", 2.0)],
            obs_count=10,
        )
        und = _understanding(assessments=[_assessment("e1")])
        actions = (
            SimulatedAction(action_id="a1", action_type="boost", target_entity="e1"),
            SimulatedAction(action_id="a2", action_type="suppress", target_entity="e1"),
        )
        engine = WorldSimulationEngine()
        results = engine.simulate_actions(snap, und, actions, horizon=1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].action_id, "a1")
        self.assertEqual(results[1].action_id, "a2")

    def test_empty_snapshot_simulation(self) -> None:
        snap = _snapshot()
        und = _understanding()
        action = SimulatedAction(action_id="a1", action_type="boost")
        engine = WorldSimulationEngine()
        result = engine.simulate_action(snap, und, action, horizon=1)
        self.assertEqual(len(result.steps), 1)

    def test_version_increments_through_steps(self) -> None:
        snap = _snapshot(
            entities=[_entity("e1")],
            facts=[_fact("e1", "v", 1.0)],
            version=5,
        )
        und = _understanding(assessments=[_assessment("e1")])
        action = SimulatedAction(
            action_id="a1", action_type="boost", target_entity="e1"
        )
        engine = WorldSimulationEngine()
        result = engine.simulate_action(snap, und, action, horizon=3)
        self.assertGreater(result.final_snapshot_version, 5)


# ─── Serialization ──────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_simulated_action_to_dict(self) -> None:
        action = SimulatedAction(
            action_id="a1",
            action_type="boost",
            target_entity="e1",
            parameters={"magnitude": 0.5},
        )
        d = action.to_dict()
        self.assertEqual(d["action_id"], "a1")
        self.assertEqual(d["action_type"], "boost")

    def test_state_delta_to_dict(self) -> None:
        delta = StateDelta(
            entity_id="e1",
            key="score",
            before=1.0,
            after=2.0,
            delta_type="numeric_shift",
            reason="test",
        )
        d = delta.to_dict()
        self.assertEqual(d["before"], 1.0)
        self.assertEqual(d["after"], 2.0)

    def test_simulation_step_to_dict(self) -> None:
        step = SimulationStep(
            step_index=0,
            action_id="a1",
            deltas=(),
            global_flags=("flag1",),
            note="test",
        )
        d = step.to_dict()
        self.assertEqual(d["step_index"], 0)
        self.assertIn("flag1", d["global_flags"])

    def test_simulation_result_to_dict(self) -> None:
        snap = _snapshot()
        und = _understanding()
        result = SimulationResult(
            action_id="a1",
            horizon=3,
            final_snapshot_version=1,
            final_world_snapshot=snap,
            final_world_understanding=und,
            steps=(),
            aggregate_risk=0.1,
            aggregate_improvement=0.2,
            confidence=0.8,
        )
        d = result.to_dict()
        self.assertEqual(d["action_id"], "a1")
        self.assertAlmostEqual(d["aggregate_risk"], 0.1)
        self.assertAlmostEqual(d["aggregate_improvement"], 0.2)


# ─── F. Integration / trace fields ─────────────────────────────


class TestTraceIntegration(unittest.TestCase):
    def test_decision_trace_has_simulation_fields(self) -> None:
        from umh.runtime_engine.decision_trace import DecisionTrace

        self.assertTrue(hasattr(DecisionTrace, "simulation_ran"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_action_count"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_best_action_id"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_best_improvement"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_best_risk"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_horizon"))
        self.assertTrue(hasattr(DecisionTrace, "simulated_global_flags"))

    def test_build_trace_accepts_simulation_params(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            simulation_ran=True,
            simulated_action_count=2,
            simulated_best_action_id="sim_boost_e1",
            simulated_best_improvement=0.3,
            simulated_best_risk=0.1,
            simulated_horizon=3,
            simulated_global_flags=("world_volatile",),
        )
        self.assertTrue(trace.simulation_ran)
        self.assertEqual(trace.simulated_action_count, 2)
        self.assertEqual(trace.simulated_best_action_id, "sim_boost_e1")
        self.assertAlmostEqual(trace.simulated_best_improvement, 0.3)

    def test_trace_serializes_simulation_fields(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            simulation_ran=True,
            simulated_action_count=1,
            simulated_best_action_id="sim_boost_e1",
            simulated_best_improvement=0.25,
            simulated_best_risk=0.05,
            simulated_horizon=3,
            simulated_global_flags=("flag1",),
        )
        d = trace.to_dict()
        self.assertTrue(d["simulation_ran"])
        self.assertEqual(d["simulated_action_count"], 1)
        self.assertIn("flag1", d["simulated_global_flags"])

    def test_trace_omits_simulation_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        d = trace.to_dict()
        self.assertNotIn("simulation_ran", d)
        self.assertNotIn("simulated_action_count", d)


# ─── No regression ──────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_world_substrate_imports(self) -> None:
        from umh.world.substrate import WorldSubstrate

        ws = WorldSubstrate()
        self.assertIsNotNone(ws)

    def test_world_reasoning_imports(self) -> None:
        from umh.world.reasoning import WorldReasoningEngine

        engine = WorldReasoningEngine()
        self.assertIsNotNone(engine)

    def test_world_simulation_imports(self) -> None:
        from umh.world.simulation import WorldSimulationEngine

        engine = WorldSimulationEngine()
        self.assertIsNotNone(engine)

    def test_signal_ingestion_imports(self) -> None:
        from umh.runtime_engine.signal_ingestion import SignalIngestionEngine

        engine = SignalIngestionEngine()
        self.assertIsNotNone(engine)


if __name__ == "__main__":
    unittest.main()
