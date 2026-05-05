"""Tests for eos_ai.world_substrate — deterministic world model engine."""

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
from umh.world.substrate import (
    ALPHA_MAX,
    ALPHA_MIN,
    ALPHA_SCALE,
    MAX_ENTITIES,
    MAX_OBSERVATIONS,
    MAX_RELATIONS,
    MAX_STATE_FACTS,
    SUBSTRATE_VERSION,
    WorldSubstrate,
)


# ─── Helpers ────────────────────────────────────────────────────


def _make_entity(eid: str = "e1", etype: str = "market") -> Entity:
    return Entity(entity_id=eid, entity_type=etype, attributes={"score": 0.5})


def _make_obs(
    entity_id: str = "e1",
    signal_type: str = "price",
    value: float | int | str | bool = 100.0,
    turn: int = 1,
    confidence: float = 0.8,
    obs_id: str | None = None,
) -> Observation:
    return Observation(
        observation_id=obs_id or f"obs_{entity_id}_{signal_type}_{turn}",
        timestamp_turn=turn,
        source="test",
        entity_id=entity_id,
        signal_type=signal_type,
        value=value,
        confidence=confidence,
        metadata={},
    )


def _make_relation(
    src: str = "e1",
    rtype: str = "affects",
    tgt: str = "e2",
    weight: float = 1.0,
) -> Relation:
    return Relation(source_id=src, relation_type=rtype, target_id=tgt, weight=weight)


# ─── Entity registration ───────────────────────────────────────


class TestEntityRegistration(unittest.TestCase):
    def test_add_and_get(self) -> None:
        ws = WorldSubstrate()
        e = _make_entity("market")
        ws.add_entity(e)
        self.assertIsNotNone(ws.get_entity("market"))
        self.assertEqual(ws.get_entity("market").entity_type, "market")

    def test_overwrite_existing(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1", "old_type"))
        ws.add_entity(_make_entity("e1", "new_type"))
        self.assertEqual(ws.get_entity("e1").entity_type, "new_type")

    def test_get_missing_returns_none(self) -> None:
        ws = WorldSubstrate()
        self.assertIsNone(ws.get_entity("nonexistent"))

    def test_upsert_attributes(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        result = ws.upsert_entity_attributes("e1", {"new_attr": 42})
        self.assertIsNotNone(result)
        self.assertEqual(result.attributes["new_attr"], 42)
        self.assertEqual(result.attributes["score"], 0.5)

    def test_upsert_missing_returns_none(self) -> None:
        ws = WorldSubstrate()
        self.assertIsNone(ws.upsert_entity_attributes("missing", {"a": 1}))

    def test_entity_cap(self) -> None:
        ws = WorldSubstrate()
        for i in range(MAX_ENTITIES):
            ws.add_entity(_make_entity(f"e{i}"))
        ws.add_entity(_make_entity("overflow"))
        self.assertIsNone(ws.get_entity("overflow"))
        self.assertEqual(len(ws._entities), MAX_ENTITIES)


# ─── Relation management ───────────────────────────────────────


class TestRelationManagement(unittest.TestCase):
    def test_add_relation(self) -> None:
        ws = WorldSubstrate()
        self.assertTrue(ws.add_relation(_make_relation()))
        self.assertEqual(len(ws.get_relations()), 1)

    def test_deduplicate(self) -> None:
        ws = WorldSubstrate()
        ws.add_relation(_make_relation("a", "x", "b"))
        self.assertFalse(ws.add_relation(_make_relation("a", "x", "b")))
        self.assertEqual(len(ws.get_relations()), 1)

    def test_different_type_not_duplicate(self) -> None:
        ws = WorldSubstrate()
        ws.add_relation(_make_relation("a", "affects", "b"))
        self.assertTrue(ws.add_relation(_make_relation("a", "influences", "b")))
        self.assertEqual(len(ws.get_relations()), 2)

    def test_query_by_entity(self) -> None:
        ws = WorldSubstrate()
        ws.add_relation(_make_relation("a", "x", "b"))
        ws.add_relation(_make_relation("c", "y", "d"))
        self.assertEqual(len(ws.get_relations(entity_id="a")), 1)
        self.assertEqual(len(ws.get_relations(entity_id="b")), 1)
        self.assertEqual(len(ws.get_relations(entity_id="z")), 0)

    def test_query_by_type(self) -> None:
        ws = WorldSubstrate()
        ws.add_relation(_make_relation("a", "affects", "b"))
        ws.add_relation(_make_relation("c", "influences", "d"))
        self.assertEqual(len(ws.get_relations(relation_type="affects")), 1)

    def test_relation_cap(self) -> None:
        ws = WorldSubstrate()
        for i in range(MAX_RELATIONS):
            ws.add_relation(_make_relation(f"s{i}", "r", f"t{i}"))
        self.assertFalse(
            ws.add_relation(_make_relation("overflow_s", "r", "overflow_t"))
        )


# ─── Numeric state EMA update ──────────────────────────────────


class TestNumericStateUpdate(unittest.TestCase):
    def test_first_observation_sets_value(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "price", 100.0, turn=1))
        fact = ws.get_state_fact("e1", "price")
        self.assertIsNotNone(fact)
        self.assertAlmostEqual(fact.value, 100.0)
        self.assertEqual(fact.update_count, 1)

    def test_ema_update(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "price", 100.0, turn=1, confidence=0.8))
        ws.record_observation(_make_obs("e1", "price", 200.0, turn=2, confidence=0.8))
        fact = ws.get_state_fact("e1", "price")
        alpha = min(max(0.8 * ALPHA_SCALE, ALPHA_MIN), ALPHA_MAX)
        expected = alpha * 200.0 + (1.0 - alpha) * 100.0
        self.assertAlmostEqual(fact.value, expected, places=4)
        self.assertEqual(fact.update_count, 2)

    def test_low_confidence_small_alpha(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "v", 100.0, turn=1, confidence=0.1))
        ws.record_observation(_make_obs("e1", "v", 200.0, turn=2, confidence=0.1))
        fact = ws.get_state_fact("e1", "v")
        expected = ALPHA_MIN * 200.0 + (1.0 - ALPHA_MIN) * 100.0
        self.assertAlmostEqual(fact.value, expected, places=4)

    def test_high_confidence_max_alpha(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "v", 100.0, turn=1, confidence=1.0))
        ws.record_observation(_make_obs("e1", "v", 200.0, turn=2, confidence=1.0))
        fact = ws.get_state_fact("e1", "v")
        expected = ALPHA_MAX * 200.0 + (1.0 - ALPHA_MAX) * 100.0
        self.assertAlmostEqual(fact.value, expected, places=4)

    def test_confidence_weighted_ema_on_confidence(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "v", 50.0, turn=1, confidence=0.3))
        ws.record_observation(_make_obs("e1", "v", 80.0, turn=2, confidence=0.9))
        fact = ws.get_state_fact("e1", "v")
        self.assertGreater(fact.confidence, 0.3)

    def test_timestamp_updated(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "v", 10.0, turn=5))
        ws.record_observation(_make_obs("e1", "v", 20.0, turn=10))
        fact = ws.get_state_fact("e1", "v")
        self.assertEqual(fact.last_updated_turn, 10)


# ─── Categorical overwrite behavior ────────────────────────────


class TestCategoricalOverwrite(unittest.TestCase):
    def test_first_categorical_sets_value(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "status", "active", turn=1))
        fact = ws.get_state_fact("e1", "status")
        self.assertEqual(fact.value, "active")

    def test_higher_confidence_wins(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "status", "old", turn=1, confidence=0.5))
        ws.record_observation(_make_obs("e1", "status", "new", turn=2, confidence=0.9))
        fact = ws.get_state_fact("e1", "status")
        self.assertEqual(fact.value, "new")

    def test_lower_confidence_does_not_replace(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "status", "high", turn=1, confidence=0.9))
        ws.record_observation(_make_obs("e1", "status", "low", turn=2, confidence=0.3))
        fact = ws.get_state_fact("e1", "status")
        self.assertEqual(fact.value, "high")
        self.assertEqual(fact.update_count, 2)

    def test_same_confidence_later_turn_wins(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "status", "old", turn=1, confidence=0.7))
        ws.record_observation(_make_obs("e1", "status", "new", turn=5, confidence=0.7))
        fact = ws.get_state_fact("e1", "status")
        self.assertEqual(fact.value, "new")

    def test_bool_update(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "active", True, turn=1, confidence=0.6))
        ws.record_observation(_make_obs("e1", "active", False, turn=2, confidence=0.8))
        fact = ws.get_state_fact("e1", "active")
        self.assertEqual(fact.value, False)


# ─── Bounded observation log ───────────────────────────────────


class TestObservationBounds(unittest.TestCase):
    def test_fifo_eviction(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        for i in range(MAX_OBSERVATIONS + 100):
            ws.record_observation(_make_obs("e1", "v", float(i), turn=i))
        self.assertLessEqual(len(ws._observations), MAX_OBSERVATIONS)

    def test_recent_observations_preserved(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        for i in range(MAX_OBSERVATIONS + 50):
            ws.record_observation(_make_obs("e1", "v", float(i), turn=i))
        last = ws.get_observations("e1", "v", limit=1)
        self.assertEqual(len(last), 1)
        self.assertEqual(last[0].timestamp_turn, MAX_OBSERVATIONS + 49)


# ─── Snapshot / restore ────────────────────────────────────────


class TestSnapshotRestore(unittest.TestCase):
    def test_snapshot_produces_valid_dict(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.add_relation(_make_relation("e1", "x", "e2"))
        ws.record_observation(_make_obs("e1", "price", 50.0, turn=1))
        snap = ws.snapshot()
        self.assertEqual(snap["version"], SUBSTRATE_VERSION)
        self.assertIn("data", snap)
        self.assertEqual(len(snap["data"]["entities"]), 1)
        self.assertEqual(len(snap["data"]["relations"]), 1)
        self.assertEqual(len(snap["data"]["observations"]), 1)
        self.assertEqual(len(snap["data"]["state_facts"]), 1)

    def test_restore_roundtrip(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.add_entity(_make_entity("e2", "campaign"))
        ws.add_relation(_make_relation("e1", "targets", "e2"))
        ws.record_observation(_make_obs("e1", "price", 50.0, turn=1))
        ws.record_observation(_make_obs("e1", "price", 60.0, turn=2))
        snap = ws.snapshot()

        ws2 = WorldSubstrate()
        self.assertTrue(ws2.restore(snap))
        self.assertIsNotNone(ws2.get_entity("e1"))
        self.assertIsNotNone(ws2.get_entity("e2"))
        self.assertEqual(len(ws2.get_relations()), 1)
        fact = ws2.get_state_fact("e1", "price")
        self.assertIsNotNone(fact)
        self.assertEqual(fact.update_count, 2)

    def test_restore_none_returns_false(self) -> None:
        ws = WorldSubstrate()
        self.assertFalse(ws.restore(None))

    def test_restore_bad_version(self) -> None:
        ws = WorldSubstrate()
        self.assertFalse(ws.restore({"version": 999, "data": {}}))

    def test_restore_corrupt_data(self) -> None:
        ws = WorldSubstrate()
        self.assertFalse(ws.restore({"version": 1, "data": "not_a_dict"}))

    def test_restore_missing_data_key(self) -> None:
        ws = WorldSubstrate()
        self.assertFalse(ws.restore({"version": 1}))

    def test_snapshot_version_increments(self) -> None:
        ws = WorldSubstrate()
        s1 = ws.build_snapshot()
        s2 = ws.build_snapshot()
        self.assertEqual(s2.version, s1.version + 1)


# ─── WorldSnapshot dataclass ───────────────────────────────────


class TestWorldSnapshot(unittest.TestCase):
    def test_snapshot_to_dict_roundtrip(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "v", 1.0, turn=1))
        snap = ws.build_snapshot()
        d = snap.to_dict()
        restored = WorldSnapshot.from_dict(d)
        self.assertEqual(restored.version, snap.version)
        self.assertEqual(len(restored.entities), 1)
        self.assertEqual(len(restored.state_facts), 1)

    def test_snapshot_immutable(self) -> None:
        ws = WorldSubstrate()
        snap = ws.build_snapshot()
        with self.assertRaises(AttributeError):
            snap.version = 999


# ─── Entity state query ────────────────────────────────────────


class TestEntityStateQuery(unittest.TestCase):
    def test_get_entity_state_returns_all_facts(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.record_observation(_make_obs("e1", "price", 100.0, turn=1))
        ws.record_observation(_make_obs("e1", "volume", 50.0, turn=1))
        facts = ws.get_entity_state("e1")
        self.assertEqual(len(facts), 2)
        keys = {f.key for f in facts}
        self.assertEqual(keys, {"price", "volume"})

    def test_get_entity_state_empty(self) -> None:
        ws = WorldSubstrate()
        self.assertEqual(ws.get_entity_state("nonexistent"), [])


# ─── Deterministic ordering ────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_snapshot(self) -> None:
        def build() -> dict:
            ws = WorldSubstrate()
            ws.add_entity(_make_entity("a"))
            ws.add_entity(_make_entity("b"))
            ws.add_relation(_make_relation("a", "x", "b"))
            ws.record_observation(_make_obs("a", "v", 10.0, turn=1))
            ws.record_observation(_make_obs("b", "v", 20.0, turn=1))
            return ws.build_snapshot().to_dict()

        self.assertEqual(build(), build())

    def test_same_inputs_same_state_facts(self) -> None:
        def build() -> dict:
            ws = WorldSubstrate()
            ws.add_entity(_make_entity("e"))
            for i in range(10):
                ws.record_observation(
                    _make_obs("e", "v", float(i), turn=i, confidence=0.5)
                )
            return ws.get_state_fact("e", "v").to_dict()

        self.assertEqual(build(), build())


# ─── Summary diagnostic ────────────────────────────────────────


class TestSummary(unittest.TestCase):
    def test_summary_fields(self) -> None:
        ws = WorldSubstrate()
        ws.add_entity(_make_entity("e1"))
        ws.add_relation(_make_relation("e1", "x", "e2"))
        ws.record_observation(_make_obs("e1", "v", 1.0))
        s = ws.summary()
        self.assertEqual(s["entity_count"], 1)
        self.assertEqual(s["relation_count"], 1)
        self.assertEqual(s["observation_count"], 1)
        self.assertEqual(s["state_fact_count"], 1)


# ─── Serialization ─────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_entity_roundtrip(self) -> None:
        e = _make_entity("x", "test")
        self.assertEqual(Entity.from_dict(e.to_dict()), e)

    def test_relation_roundtrip(self) -> None:
        r = _make_relation("a", "b", "c", 0.5)
        self.assertEqual(Relation.from_dict(r.to_dict()), r)

    def test_observation_roundtrip(self) -> None:
        o = _make_obs("e1", "price", 100.0, turn=5, confidence=0.7, obs_id="obs1")
        self.assertEqual(Observation.from_dict(o.to_dict()), o)

    def test_state_fact_roundtrip(self) -> None:
        f = StateFact(
            entity_id="e1",
            key="price",
            value=99.5,
            confidence=0.8,
            last_updated_turn=3,
            update_count=5,
        )
        self.assertEqual(StateFact.from_dict(f.to_dict()), f)


if __name__ == "__main__":
    unittest.main()
