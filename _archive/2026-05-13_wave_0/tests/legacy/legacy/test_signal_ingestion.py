"""Tests for runtime.signal_ingestion — raw signal → structured observation."""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.world.types import Entity, Observation, Relation
from umh.world.substrate import WorldSubstrate
from umh.runtime_engine.signal_ingestion import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    MAX_PAYLOAD_KEYS,
    RELATION_METADATA_KEYS,
    RawSignal,
    SignalIngestionEngine,
    StructuredSignal,
)


# ─── Helpers ────────────────────────────────────────────────────


def _make_signal(
    source: str = "test_source",
    signal_type: str = "metric",
    target: str = "market",
    payload: dict | None = None,
    confidence: float = 0.8,
    turn: int = 1,
) -> RawSignal:
    return RawSignal(
        source=source,
        signal_type=signal_type,
        target_entity=target,
        payload=payload if payload is not None else {"price": 100.0, "volume": 50},
        confidence=confidence,
        timestamp_turn=turn,
    )


# ─── Validation ─────────────────────────────────────────────────


class TestValidation(unittest.TestCase):
    def test_valid_signal_accepted(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        result = eng.ingest(_make_signal(), ws)
        self.assertIsNotNone(result)

    def test_empty_source_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(source="")
        self.assertIsNone(eng.ingest(sig, ws))

    def test_whitespace_source_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(source="   ")
        self.assertIsNone(eng.ingest(sig, ws))

    def test_empty_target_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(target="")
        self.assertIsNone(eng.ingest(sig, ws))

    def test_negative_confidence_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(confidence=-0.1)
        self.assertIsNone(eng.ingest(sig, ws))

    def test_over_max_confidence_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(confidence=1.5)
        self.assertIsNone(eng.ingest(sig, ws))

    def test_boundary_confidence_accepted(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        self.assertIsNotNone(eng.ingest(_make_signal(confidence=0.0), ws))
        ws2 = WorldSubstrate()
        self.assertIsNotNone(eng.ingest(_make_signal(confidence=1.0), ws2))

    def test_negative_turn_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(turn=-1)
        self.assertIsNone(eng.ingest(sig, ws))

    def test_too_many_payload_keys_rejected(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        big_payload = {f"k{i}": i for i in range(MAX_PAYLOAD_KEYS + 1)}
        sig = _make_signal(payload=big_payload)
        self.assertIsNone(eng.ingest(sig, ws))

    def test_max_payload_keys_accepted(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        payload = {f"k{i}": i for i in range(MAX_PAYLOAD_KEYS)}
        sig = _make_signal(payload=payload)
        self.assertIsNotNone(eng.ingest(sig, ws))


# ─── Payload → observations mapping ────────────────────────────


class TestPayloadMapping(unittest.TestCase):
    def test_each_key_becomes_observation(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"a": 1, "b": 2, "c": 3})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.observations), 3)

    def test_none_values_skipped(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"a": 1, "b": None})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.observations), 1)

    def test_relation_keys_not_observations(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"price": 10, "related_to": "other"})
        result = eng.ingest(sig, ws)
        signal_types = [o.signal_type for o in result.observations]
        self.assertIn("price", signal_types)
        self.assertNotIn("related_to", signal_types)

    def test_observation_confidence_propagated(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(confidence=0.42, payload={"x": 1})
        result = eng.ingest(sig, ws)
        self.assertAlmostEqual(result.observations[0].confidence, 0.42)

    def test_observation_ids_unique(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"a": 1, "b": 2})
        result = eng.ingest(sig, ws)
        ids = [o.observation_id for o in result.observations]
        self.assertEqual(len(ids), len(set(ids)))

    def test_observations_sorted_by_key(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"z": 1, "a": 2, "m": 3})
        result = eng.ingest(sig, ws)
        types = [o.signal_type for o in result.observations]
        self.assertEqual(types, ["a", "m", "z"])

    def test_empty_payload_produces_no_observations(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.observations), 0)


# ─── Relation inference ────────────────────────────────────────


class TestRelationInference(unittest.TestCase):
    def test_related_to_creates_relation(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"price": 10, "related_to": "campaign_alpha"})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.inferred_relations), 1)
        rel = result.inferred_relations[0]
        self.assertEqual(rel.relation_type, "related_to")
        self.assertEqual(rel.target_id, "campaign_alpha")

    def test_influences_creates_relation(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"influences": "user_segment"})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.inferred_relations), 1)
        self.assertEqual(result.inferred_relations[0].relation_type, "influences")

    def test_no_relation_from_non_string_target(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"related_to": 42})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.inferred_relations), 0)

    def test_no_relation_from_empty_string(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"related_to": "   "})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.inferred_relations), 0)

    def test_relation_weight_equals_confidence(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(confidence=0.65, payload={"related_to": "x"})
        result = eng.ingest(sig, ws)
        self.assertAlmostEqual(result.inferred_relations[0].weight, 0.65)

    def test_both_relation_types(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(payload={"related_to": "a", "influences": "b"})
        result = eng.ingest(sig, ws)
        self.assertEqual(len(result.inferred_relations), 2)


# ─── Entity auto-creation ──────────────────────────────────────


class TestEntityAutoCreation(unittest.TestCase):
    def test_creates_entity_if_missing(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(target="new_entity", payload={"v": 1})
        eng.ingest(sig, ws)
        self.assertIsNotNone(ws.get_entity("new_entity"))

    def test_does_not_overwrite_existing_entity(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        ws.add_entity(
            Entity(entity_id="existing", entity_type="custom", attributes={"k": 1})
        )
        sig = _make_signal(target="existing", payload={"v": 1})
        eng.ingest(sig, ws)
        self.assertEqual(ws.get_entity("existing").entity_type, "custom")


# ─── Entity ID normalization ───────────────────────────────────


class TestEntityNormalization(unittest.TestCase):
    def test_lowercase(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(target="Market")
        eng.ingest(sig, ws)
        self.assertIsNotNone(ws.get_entity("market"))

    def test_strip_whitespace(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(target="  market  ")
        eng.ingest(sig, ws)
        self.assertIsNotNone(ws.get_entity("market"))

    def test_spaces_to_underscores(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        sig = _make_signal(target="user segment")
        eng.ingest(sig, ws)
        self.assertIsNotNone(ws.get_entity("user_segment"))


# ─── Integration: signals → world state ─────────────────────


class TestIntegration(unittest.TestCase):
    def test_signal_updates_state_facts(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        ws.add_entity(Entity(entity_id="market", entity_type="market", attributes={}))
        eng.ingest(_make_signal(target="market", payload={"price": 100.0}), ws)
        fact = ws.get_state_fact("market", "price")
        self.assertIsNotNone(fact)
        self.assertAlmostEqual(fact.value, 100.0)

    def test_multiple_signals_accumulate(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        eng.ingest(_make_signal(target="m", payload={"v": 10.0}, turn=1), ws)
        eng.ingest(_make_signal(target="m", payload={"v": 20.0}, turn=2), ws)
        fact = ws.get_state_fact("m", "v")
        self.assertEqual(fact.update_count, 2)

    def test_ingestion_count_tracks(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        eng.ingest(_make_signal(), ws)
        eng.ingest(_make_signal(turn=2), ws)
        self.assertEqual(eng.ingestion_count, 2)

    def test_sources_tracked(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        eng.ingest(_make_signal(source="src_a"), ws)
        eng.ingest(_make_signal(source="src_b"), ws)
        self.assertEqual(eng.sources_seen, frozenset({"src_a", "src_b"}))


# ─── Trace fields ──────────────────────────────────────────────


class TestTraceFields(unittest.TestCase):
    def test_trace_fields_after_ingestion(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        eng.ingest(_make_signal(source="alpha"), ws)
        eng.ingest(_make_signal(source="beta", turn=2), ws)
        fields = eng.get_trace_fields()
        self.assertEqual(fields["ingested_signal_count"], 2)
        self.assertIn("alpha", fields["ingested_signal_sources"])
        self.assertIn("beta", fields["ingested_signal_sources"])

    def test_trace_fields_empty(self) -> None:
        eng = SignalIngestionEngine()
        fields = eng.get_trace_fields()
        self.assertEqual(fields["ingested_signal_count"], 0)
        self.assertEqual(fields["ingested_signal_sources"], ())


# ─── Determinism ────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_outputs(self) -> None:
        def build() -> dict:
            eng = SignalIngestionEngine()
            ws = WorldSubstrate()
            result = eng.ingest(
                _make_signal(payload={"a": 1, "b": 2, "related_to": "x"}),
                ws,
            )
            return result.to_dict()

        self.assertEqual(build(), build())


# ─── StructuredSignal serialization ─────────────────────────────


class TestStructuredSignalSerialization(unittest.TestCase):
    def test_to_dict(self) -> None:
        eng = SignalIngestionEngine()
        ws = WorldSubstrate()
        result = eng.ingest(
            _make_signal(payload={"v": 1, "related_to": "other"}),
            ws,
        )
        d = result.to_dict()
        self.assertEqual(d["entity_id"], "market")
        self.assertEqual(len(d["observations"]), 1)
        self.assertEqual(len(d["inferred_relations"]), 1)


# ─── RawSignal serialization ───────────────────────────────────


class TestRawSignalSerialization(unittest.TestCase):
    def test_to_dict(self) -> None:
        sig = _make_signal()
        d = sig.to_dict()
        self.assertEqual(d["source"], "test_source")
        self.assertEqual(d["confidence"], 0.8)


# ─── No effect when no signals ──────────────────────────────────


class TestNoSignalNoEffect(unittest.TestCase):
    def test_empty_world_unchanged(self) -> None:
        ws = WorldSubstrate()
        snap_before = ws.build_snapshot()
        snap_after = ws.build_snapshot()
        self.assertEqual(snap_before.observation_count, snap_after.observation_count)
        self.assertEqual(len(snap_before.entities), len(snap_after.entities))


if __name__ == "__main__":
    unittest.main()
