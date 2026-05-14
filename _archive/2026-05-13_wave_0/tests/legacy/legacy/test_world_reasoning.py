"""Tests for runtime.world_reasoning — deterministic derived understanding."""

from __future__ import annotations

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
    DEGRADING_THRESHOLD,
    HEALTH_GOOD_THRESHOLD,
    HEALTH_WATCH_THRESHOLD,
    INSUFFICIENT_DATA_MIN,
    MIN_TREND_POINTS,
    PROPAGATION_MAX,
    PROPAGATION_SCALE,
    SLOPE_EPSILON,
    VOLATILE_THRESHOLD,
    EntityAssessment,
    EntityTrend,
    RelationImpact,
    WorldReasoningEngine,
    WorldUnderstanding,
    detect_trend,
    get_entity_assessment,
    get_impacted_targets,
    get_riskiest_entities,
    summarize_understanding,
    _classify_health,
    _classify_stability,
    _compute_global_flags,
    _compute_stability_score,
    _health_score_from_facts_and_trends,
    _propagate_risk,
)


# ─── Test helpers ───────────────────────────────────────────────


def _obs(
    entity_id: str,
    signal_type: str,
    value: float | int | str | bool,
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


def _relation(
    src: str,
    rtype: str,
    tgt: str,
    weight: float = 1.0,
) -> Relation:
    return Relation(source_id=src, relation_type=rtype, target_id=tgt, weight=weight)


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


# ─── Trend detection ───────────────────────────────────────────


class TestTrendDetection(unittest.TestCase):
    def test_increasing_series(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        trend = detect_trend("e1", "price", values)
        self.assertEqual(trend.direction, "up")
        self.assertGreater(trend.slope, 0)
        self.assertGreater(trend.confidence, 0)

    def test_decreasing_series(self) -> None:
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        trend = detect_trend("e1", "price", values)
        self.assertEqual(trend.direction, "down")
        self.assertLess(trend.slope, 0)

    def test_flat_series(self) -> None:
        values = [5.0, 5.001, 5.0, 4.999, 5.0]
        trend = detect_trend("e1", "price", values)
        self.assertEqual(trend.direction, "flat")

    def test_volatile_series(self) -> None:
        values = [1.0, 10.0, 2.0, 9.0, 3.0, 8.0, 4.0]
        trend = detect_trend("e1", "price", values)
        self.assertEqual(trend.direction, "volatile")

    def test_insufficient_data(self) -> None:
        values = [1.0, 2.0]
        trend = detect_trend("e1", "price", values)
        self.assertEqual(trend.direction, "unknown")
        self.assertEqual(trend.confidence, 0.0)

    def test_empty_data(self) -> None:
        trend = detect_trend("e1", "price", [])
        self.assertEqual(trend.direction, "unknown")

    def test_confidence_bounded(self) -> None:
        values = [float(i) for i in range(50)]
        trend = detect_trend("e1", "v", values)
        self.assertGreaterEqual(trend.confidence, 0.0)
        self.assertLessEqual(trend.confidence, 1.0)

    def test_slope_sign_matches_direction(self) -> None:
        up = detect_trend("e1", "v", [1.0, 3.0, 5.0, 7.0])
        self.assertGreater(up.slope, 0)
        down = detect_trend("e1", "v", [7.0, 5.0, 3.0, 1.0])
        self.assertLess(down.slope, 0)

    def test_trend_to_dict(self) -> None:
        trend = detect_trend("e1", "v", [1.0, 2.0, 3.0])
        d = trend.to_dict()
        self.assertIn("direction", d)
        self.assertIn("slope", d)
        self.assertIn("confidence", d)


# ─── Health classification ──────────────────────────────────────


class TestHealthClassification(unittest.TestCase):
    def test_good_entity(self) -> None:
        facts = [_fact("e1", "score", 0.8)]
        trends = [
            EntityTrend("e1", "score", "up", 0.1, 0.8, "up"),
            EntityTrend("e1", "score2", "up", 0.05, 0.9, "up"),
            EntityTrend("e1", "score3", "up", 0.08, 0.85, "up"),
        ]
        score = _health_score_from_facts_and_trends(facts, trends)
        self.assertEqual(_classify_health(score), "good")

    def test_watch_entity(self) -> None:
        facts = [_fact("e1", "score", 0.5)]
        trends = [EntityTrend("e1", "score", "down", -0.1, 0.9, "down")]
        score = _health_score_from_facts_and_trends(facts, trends)
        self.assertEqual(_classify_health(score), "watch")

    def test_bad_entity_from_warning_flag(self) -> None:
        facts = [_fact("e1", "risk_active", True, confidence=0.9)]
        trends = [
            EntityTrend("e1", "v", "down", -0.2, 0.9, "down"),
            EntityTrend("e1", "w", "down", -0.2, 0.9, "down"),
        ]
        score = _health_score_from_facts_and_trends(facts, trends)
        self.assertEqual(_classify_health(score), "bad")

    def test_unknown_entity_no_data(self) -> None:
        score = _health_score_from_facts_and_trends([], [])
        self.assertAlmostEqual(score, 0.5)

    def test_warning_keyword_detection(self) -> None:
        facts = [_fact("e1", "error_count", True, confidence=1.0)]
        score = _health_score_from_facts_and_trends(facts, [])
        self.assertLess(score, 0.5)

    def test_non_warning_key_no_penalty(self) -> None:
        facts = [_fact("e1", "status", True, confidence=1.0)]
        score = _health_score_from_facts_and_trends(facts, [])
        self.assertAlmostEqual(score, 0.5)

    def test_health_thresholds(self) -> None:
        self.assertEqual(_classify_health(0.8), "good")
        self.assertEqual(_classify_health(HEALTH_GOOD_THRESHOLD), "good")
        self.assertEqual(_classify_health(0.5), "watch")
        self.assertEqual(_classify_health(HEALTH_WATCH_THRESHOLD), "watch")
        self.assertEqual(_classify_health(0.1), "bad")


# ─── Stability classification ──────────────────────────────────


class TestStabilityClassification(unittest.TestCase):
    def test_stable_entity(self) -> None:
        trends = [
            EntityTrend("e1", "v", "flat", 0.0, 0.9, "flat"),
            EntityTrend("e1", "w", "flat", 0.0, 0.95, "flat"),
        ]
        score = _compute_stability_score(trends)
        self.assertEqual(_classify_stability(score), "stable")

    def test_volatile_entity(self) -> None:
        trends = [
            EntityTrend("e1", "v", "volatile", 0.0, 0.7, "vol"),
            EntityTrend("e1", "w", "volatile", 0.0, 0.7, "vol"),
        ]
        score = _compute_stability_score(trends)
        self.assertEqual(_classify_stability(score), "volatile")

    def test_unstable_entity(self) -> None:
        trends = [
            EntityTrend("e1", "v", "up", 0.1, 0.5, "up"),
            EntityTrend("e1", "w", "down", -0.1, 0.5, "down"),
            EntityTrend("e1", "x", "volatile", 0.0, 0.5, "vol"),
        ]
        score = _compute_stability_score(trends)
        stability = _classify_stability(score)
        self.assertIn(stability, ("unstable", "volatile"))

    def test_unknown_no_trends(self) -> None:
        score = _compute_stability_score([])
        self.assertAlmostEqual(score, 0.5)

    def test_all_unknown_trends(self) -> None:
        trends = [EntityTrend("e1", "v", "unknown", 0.0, 0.0, "unk")]
        score = _compute_stability_score(trends)
        self.assertAlmostEqual(score, 0.5)

    def test_stability_bounded(self) -> None:
        for dirs in [["up"], ["down"], ["volatile"], ["flat"]]:
            trends = [EntityTrend("e1", "v", d, 0.1, 0.9, d) for d in dirs]
            score = _compute_stability_score(trends)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


# ─── Relation risk propagation ──────────────────────────────────


class TestRelationPropagation(unittest.TestCase):
    def test_bad_source_propagates(self) -> None:
        assessments = {
            "src": EntityAssessment(
                entity_id="src",
                health="bad",
                stability="stable",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.8,
            ),
        }
        relations = (_relation("src", "affects", "tgt"),)
        impacts = _propagate_risk(relations, assessments)
        self.assertEqual(len(impacts), 1)
        self.assertGreater(impacts[0].propagated_risk, 0)

    def test_good_source_no_propagation(self) -> None:
        assessments = {
            "src": EntityAssessment(
                entity_id="src",
                health="good",
                stability="stable",
                trend_summary=(),
                risk_flags=(),
                confidence=0.8,
            ),
        }
        relations = (_relation("src", "affects", "tgt"),)
        impacts = _propagate_risk(relations, assessments)
        self.assertEqual(len(impacts), 0)

    def test_propagation_bounded(self) -> None:
        assessments = {
            "src": EntityAssessment(
                entity_id="src",
                health="bad",
                stability="volatile",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=1.0,
            ),
        }
        relations = (_relation("src", "affects", "tgt", weight=10.0),)
        impacts = _propagate_risk(relations, assessments)
        self.assertLessEqual(impacts[0].propagated_risk, PROPAGATION_MAX)

    def test_watch_source_lower_risk(self) -> None:
        bad_a = {
            "src": EntityAssessment(
                entity_id="src",
                health="bad",
                stability="stable",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.8,
            ),
        }
        watch_a = {
            "src": EntityAssessment(
                entity_id="src",
                health="watch",
                stability="stable",
                trend_summary=(),
                risk_flags=(),
                confidence=0.8,
            ),
        }
        rels = (_relation("src", "x", "tgt"),)
        bad_impact = _propagate_risk(rels, bad_a)
        watch_impact = _propagate_risk(rels, watch_a)
        self.assertGreater(
            bad_impact[0].propagated_risk,
            watch_impact[0].propagated_risk,
        )

    def test_no_recursive_propagation(self) -> None:
        assessments = {
            "a": EntityAssessment(
                entity_id="a",
                health="bad",
                stability="stable",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.8,
            ),
            "b": EntityAssessment(
                entity_id="b",
                health="good",
                stability="stable",
                trend_summary=(),
                risk_flags=(),
                confidence=0.8,
            ),
        }
        relations = (
            _relation("a", "affects", "b"),
            _relation("b", "affects", "c"),
        )
        impacts = _propagate_risk(relations, assessments)
        target_ids = [i.target_id for i in impacts]
        self.assertIn("b", target_ids)
        self.assertNotIn("c", target_ids)

    def test_impact_has_reason(self) -> None:
        assessments = {
            "src": EntityAssessment(
                entity_id="src",
                health="bad",
                stability="stable",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.8,
            ),
        }
        impacts = _propagate_risk((_relation("src", "x", "tgt"),), assessments)
        self.assertTrue(len(impacts[0].propagated_reason) > 0)


# ─── Global flags ──────────────────────────────────────────────


class TestGlobalFlags(unittest.TestCase):
    def test_degrading_world(self) -> None:
        assessments = tuple(
            EntityAssessment(
                entity_id=f"e{i}",
                health="bad",
                stability="stable",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.8,
            )
            for i in range(6)
        )
        snap = _snapshot(obs_count=20)
        flags = _compute_global_flags(assessments, snap)
        self.assertIn("world_degrading", flags)

    def test_volatile_world(self) -> None:
        assessments = tuple(
            EntityAssessment(
                entity_id=f"e{i}",
                health="good",
                stability="volatile",
                trend_summary=(),
                risk_flags=(),
                confidence=0.8,
            )
            for i in range(5)
        )
        snap = _snapshot(obs_count=20)
        flags = _compute_global_flags(assessments, snap)
        self.assertIn("world_volatile", flags)

    def test_insufficient_data(self) -> None:
        snap = _snapshot(obs_count=1)
        flags = _compute_global_flags((), snap)
        self.assertIn("insufficient_world_data", flags)

    def test_risk_cluster(self) -> None:
        assessments = tuple(
            EntityAssessment(
                entity_id=f"e{i}",
                health="watch",
                stability="stable",
                trend_summary=(),
                risk_flags=(f"flag_{i}",),
                confidence=0.8,
            )
            for i in range(4)
        )
        snap = _snapshot(obs_count=20)
        flags = _compute_global_flags(assessments, snap)
        self.assertIn("risk_cluster_detected", flags)

    def test_healthy_world_no_flags(self) -> None:
        assessments = tuple(
            EntityAssessment(
                entity_id=f"e{i}",
                health="good",
                stability="stable",
                trend_summary=(),
                risk_flags=(),
                confidence=0.8,
            )
            for i in range(5)
        )
        snap = _snapshot(obs_count=20)
        flags = _compute_global_flags(assessments, snap)
        self.assertEqual(flags, [])


# ─── Full engine integration ───────────────────────────────────


class TestWorldReasoningEngine(unittest.TestCase):
    def _build_scenario(self) -> tuple[WorldSnapshot, tuple[Observation, ...]]:
        entities = [_entity("good_e"), _entity("bad_e"), _entity("tgt")]
        relations = [_relation("bad_e", "affects", "tgt")]
        facts = [
            _fact("good_e", "score", 0.9),
            _fact("bad_e", "risk_level", True),
            _fact("bad_e", "performance", 0.2),
        ]
        snap = _snapshot(entities, relations, facts, obs_count=30)

        observations: list[Observation] = []
        for i in range(10):
            observations.append(_obs("good_e", "score", 0.8 + i * 0.01, turn=i))
            observations.append(_obs("bad_e", "performance", 0.5 - i * 0.03, turn=i))
        return snap, tuple(observations)

    def test_produces_world_understanding(self) -> None:
        snap, obs = self._build_scenario()
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, obs)
        self.assertIsInstance(result, WorldUnderstanding)
        self.assertEqual(result.snapshot_version, snap.version)
        self.assertEqual(result.derived_count, 3)

    def test_all_entities_assessed(self) -> None:
        snap, obs = self._build_scenario()
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, obs)
        ids = {a.entity_id for a in result.entity_assessments}
        self.assertEqual(ids, {"good_e", "bad_e", "tgt"})

    def test_good_entity_classified_well(self) -> None:
        snap, obs = self._build_scenario()
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, obs)
        good = get_entity_assessment(result, "good_e")
        self.assertIsNotNone(good)
        self.assertIn(good.health, ("good", "watch"))

    def test_bad_entity_has_risk_flags(self) -> None:
        snap, obs = self._build_scenario()
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, obs)
        bad = get_entity_assessment(result, "bad_e")
        self.assertIsNotNone(bad)
        self.assertTrue(len(bad.risk_flags) > 0)

    def test_relation_impact_propagated(self) -> None:
        snap, obs = self._build_scenario()
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, obs)
        impacts = get_impacted_targets(result, "bad_e")
        if impacts:
            self.assertEqual(impacts[0].target_id, "tgt")

    def test_no_observations_still_works(self) -> None:
        snap = _snapshot([_entity("e1")], [], [_fact("e1", "v", 1.0)], obs_count=10)
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap, None)
        self.assertEqual(result.derived_count, 1)
        a = get_entity_assessment(result, "e1")
        self.assertIsNotNone(a)
        self.assertEqual(len(a.trend_summary), 0)

    def test_empty_snapshot(self) -> None:
        snap = _snapshot(obs_count=0)
        engine = WorldReasoningEngine()
        result = engine.derive_understanding(snap)
        self.assertEqual(result.derived_count, 0)
        self.assertIn("insufficient_world_data", result.global_flags)


# ─── Query helpers ─────────────────────────────────────────────


class TestQueryHelpers(unittest.TestCase):
    def _build_understanding(self) -> WorldUnderstanding:
        assessments = (
            EntityAssessment(
                entity_id="healthy",
                health="good",
                stability="stable",
                trend_summary=(),
                risk_flags=(),
                confidence=0.9,
            ),
            EntityAssessment(
                entity_id="risky",
                health="bad",
                stability="volatile",
                trend_summary=(),
                risk_flags=("entity_unhealthy",),
                confidence=0.7,
            ),
            EntityAssessment(
                entity_id="mid",
                health="watch",
                stability="unstable",
                trend_summary=(),
                risk_flags=("declining:v",),
                confidence=0.6,
            ),
        )
        impacts = (
            RelationImpact(
                source_id="risky",
                target_id="healthy",
                relation_type="affects",
                propagated_risk=0.3,
                propagated_reason="source is unhealthy",
            ),
        )
        return WorldUnderstanding(
            entity_assessments=assessments,
            relation_impacts=impacts,
            global_flags=("risk_cluster_detected",),
            snapshot_version=5,
            derived_count=3,
        )

    def test_get_entity_assessment_found(self) -> None:
        u = self._build_understanding()
        a = get_entity_assessment(u, "risky")
        self.assertIsNotNone(a)
        self.assertEqual(a.health, "bad")

    def test_get_entity_assessment_missing(self) -> None:
        u = self._build_understanding()
        self.assertIsNone(get_entity_assessment(u, "nonexistent"))

    def test_get_riskiest_entities_ordered(self) -> None:
        u = self._build_understanding()
        riskiest = get_riskiest_entities(u, limit=3)
        self.assertEqual(riskiest[0].entity_id, "risky")

    def test_get_riskiest_entities_limit(self) -> None:
        u = self._build_understanding()
        self.assertEqual(len(get_riskiest_entities(u, limit=1)), 1)

    def test_get_impacted_targets(self) -> None:
        u = self._build_understanding()
        impacts = get_impacted_targets(u, "risky")
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].target_id, "healthy")

    def test_get_impacted_targets_none(self) -> None:
        u = self._build_understanding()
        self.assertEqual(get_impacted_targets(u, "healthy"), [])

    def test_summarize_understanding(self) -> None:
        u = self._build_understanding()
        s = summarize_understanding(u)
        self.assertEqual(s["entity_count"], 3)
        self.assertEqual(s["derived_count"], 3)
        self.assertEqual(s["riskiest_entity"], "risky")
        self.assertEqual(s["riskiest_entity_health"], "bad")
        self.assertIn("risk_cluster_detected", s["global_flags"])


# ─── WorldUnderstanding serialization ──────────────────────────


class TestSerialization(unittest.TestCase):
    def test_understanding_to_dict(self) -> None:
        u = WorldUnderstanding(
            entity_assessments=(
                EntityAssessment(
                    entity_id="e1",
                    health="good",
                    stability="stable",
                    trend_summary=(),
                    risk_flags=(),
                    confidence=0.8,
                ),
            ),
            relation_impacts=(),
            global_flags=("world_volatile",),
            snapshot_version=1,
            derived_count=1,
        )
        d = u.to_dict()
        self.assertEqual(d["snapshot_version"], 1)
        self.assertEqual(len(d["entity_assessments"]), 1)
        self.assertIn("world_volatile", d["global_flags"])

    def test_assessment_to_dict(self) -> None:
        a = EntityAssessment(
            entity_id="e1",
            health="watch",
            stability="unstable",
            trend_summary=(EntityTrend("e1", "v", "down", -0.1, 0.7, "declining"),),
            risk_flags=("declining:v",),
            confidence=0.6,
        )
        d = a.to_dict()
        self.assertEqual(d["health"], "watch")
        self.assertEqual(len(d["trend_summary"]), 1)
        self.assertIn("declining:v", d["risk_flags"])

    def test_impact_to_dict(self) -> None:
        r = RelationImpact(
            source_id="a",
            target_id="b",
            relation_type="x",
            propagated_risk=0.42,
            propagated_reason="test",
        )
        d = r.to_dict()
        self.assertAlmostEqual(d["propagated_risk"], 0.42)


# ─── Determinism ───────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def _build(self) -> WorldUnderstanding:
        entities = [_entity("a"), _entity("b")]
        relations = [_relation("a", "x", "b")]
        facts = [_fact("a", "v", 0.5), _fact("b", "v", 0.3)]
        obs = tuple(_obs("a", "v", 0.5 + i * 0.01, turn=i) for i in range(10)) + tuple(
            _obs("b", "v", 0.3 - i * 0.02, turn=i) for i in range(10)
        )
        snap = _snapshot(entities, relations, facts, obs_count=20)
        engine = WorldReasoningEngine()
        return engine.derive_understanding(snap, obs)

    def test_same_inputs_same_output(self) -> None:
        r1 = self._build()
        r2 = self._build()
        self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_ordering_stable(self) -> None:
        r1 = self._build()
        r2 = self._build()
        ids1 = [a.entity_id for a in r1.entity_assessments]
        ids2 = [a.entity_id for a in r2.entity_assessments]
        self.assertEqual(ids1, ids2)


# ─── No regression ─────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_world_types_imports(self) -> None:
        from umh.world.types import Entity, WorldSnapshot

        self.assertTrue(True)

    def test_world_substrate_imports(self) -> None:
        from umh.world.substrate import WorldSubstrate

        self.assertTrue(True)

    def test_decision_trace_new_fields_exist(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=0,
            world_derived_count=5,
            world_global_flags=("world_volatile",),
            world_riskiest_entity="e1",
            world_riskiest_entity_health="bad",
            world_volatile_entity_count=2,
            world_bad_entity_count=1,
        )
        d = trace.to_dict()
        self.assertEqual(d["world_derived_count"], 5)
        self.assertEqual(d["world_global_flags"], ["world_volatile"])
        self.assertEqual(d["world_riskiest_entity"], "e1")
        self.assertEqual(d["world_bad_entity_count"], 1)


if __name__ == "__main__":
    unittest.main()
