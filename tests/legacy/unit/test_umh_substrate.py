"""Tests for umh.world.substrate — WorldSubstrate.

Covers: import boundary, construction, entity CRUD, relation CRUD,
observation recording, numeric EMA state updates, snapshot/restore
round-trip, and capacity bounds enforcement.
"""

from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.world.substrate import (
    MAX_ENTITIES,
    MAX_RELATIONS,
    WorldSubstrate,
)
from umh.world.types import Entity, Observation, Relation


# ─── Import boundary ────────────────────────────────────────────


def test_no_eos_ai_imports() -> None:
    """substrate.py must not import anything from eos."""
    with open("/opt/OS/umh/world/substrate.py") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("umh.runtime_engine."), (
                    f"Forbidden import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"Forbidden import: {node.module}"
                )


# ─── Construction ────────────────────────────────────────────────


def test_construction() -> None:
    """WorldSubstrate() initializes with empty state."""
    ws = WorldSubstrate()
    s = ws.summary()
    assert s["entity_count"] == 0
    assert s["relation_count"] == 0
    assert s["observation_count"] == 0
    assert s["state_fact_count"] == 0
    assert s["version"] == 0


# ─── Entity CRUD ─────────────────────────────────────────────────


def test_add_and_get_entity() -> None:
    ws = WorldSubstrate()
    e = Entity(entity_id="e1", entity_type="person", attributes={"name": "Alice"})
    ws.add_entity(e)
    got = ws.get_entity("e1")
    assert got is not None
    assert got.entity_id == "e1"
    assert got.entity_type == "person"
    assert got.attributes["name"] == "Alice"


def test_get_missing_entity_returns_none() -> None:
    ws = WorldSubstrate()
    assert ws.get_entity("nonexistent") is None


# ─── Relation CRUD ───────────────────────────────────────────────


def test_add_and_query_relation() -> None:
    ws = WorldSubstrate()
    ws.add_entity(Entity(entity_id="a", entity_type="person"))
    ws.add_entity(Entity(entity_id="b", entity_type="company"))
    r = Relation(source_id="a", relation_type="works_at", target_id="b")
    assert ws.add_relation(r) is True

    # Query by entity
    rels = ws.get_relations(entity_id="a")
    assert len(rels) == 1
    assert rels[0].target_id == "b"

    # Query by type
    rels2 = ws.get_relations(relation_type="works_at")
    assert len(rels2) == 1

    # Duplicate rejected
    assert ws.add_relation(r) is False


# ─── Observation recording ───────────────────────────────────────


def test_add_observation() -> None:
    ws = WorldSubstrate()
    ws.add_entity(Entity(entity_id="e1", entity_type="metric"))
    obs = Observation(
        observation_id="obs1",
        timestamp_turn=1,
        source="test",
        entity_id="e1",
        signal_type="revenue",
        value=100.0,
        confidence=0.9,
    )
    ws.record_observation(obs)
    results = ws.get_observations(entity_id="e1")
    assert len(results) == 1
    assert results[0].observation_id == "obs1"


# ─── Numeric EMA state update ───────────────────────────────────


def test_numeric_ema_update() -> None:
    """Two numeric observations should produce an EMA-blended state fact."""
    ws = WorldSubstrate()
    ws.add_entity(Entity(entity_id="e1", entity_type="metric"))

    obs1 = Observation(
        observation_id="o1",
        timestamp_turn=1,
        source="test",
        entity_id="e1",
        signal_type="score",
        value=100.0,
        confidence=0.8,
    )
    ws.record_observation(obs1)

    fact1 = ws.get_state_fact("e1", "score")
    assert fact1 is not None
    assert fact1.value == 100.0
    assert fact1.update_count == 1

    obs2 = Observation(
        observation_id="o2",
        timestamp_turn=2,
        source="test",
        entity_id="e1",
        signal_type="score",
        value=200.0,
        confidence=0.8,
    )
    ws.record_observation(obs2)

    fact2 = ws.get_state_fact("e1", "score")
    assert fact2 is not None
    assert fact2.update_count == 2
    # EMA: value should be between 100 and 200, closer to 100 (alpha ~0.24)
    assert 100.0 < fact2.value < 200.0


# ─── Snapshot / Restore round-trip ───────────────────────────────


def test_snapshot_restore_roundtrip() -> None:
    ws = WorldSubstrate()
    ws.add_entity(Entity(entity_id="e1", entity_type="person"))
    ws.add_entity(Entity(entity_id="e2", entity_type="company"))
    ws.add_relation(Relation(source_id="e1", relation_type="owns", target_id="e2"))
    ws.record_observation(
        Observation(
            observation_id="obs1",
            timestamp_turn=1,
            source="test",
            entity_id="e1",
            signal_type="mood",
            value="happy",
            confidence=0.9,
        )
    )

    data = ws.snapshot()

    ws2 = WorldSubstrate()
    assert ws2.restore(data) is True

    assert ws2.get_entity("e1") is not None
    assert ws2.get_entity("e2") is not None
    assert len(ws2.get_relations(entity_id="e1")) == 1
    assert len(ws2.get_observations(entity_id="e1")) == 1
    assert ws2.get_state_fact("e1", "mood") is not None

    s = ws2.summary()
    assert s["entity_count"] == 2
    assert s["relation_count"] == 1
    assert s["observation_count"] == 1
    assert s["state_fact_count"] == 1


def test_restore_returns_false_on_none() -> None:
    ws = WorldSubstrate()
    assert ws.restore(None) is False


def test_restore_returns_false_on_bad_version() -> None:
    ws = WorldSubstrate()
    assert ws.restore({"version": 999, "data": {}}) is False


# ─── Capacity bounds ────────────────────────────────────────────


def test_entity_capacity_bound() -> None:
    """Adding more than MAX_ENTITIES new entities should be rejected."""
    ws = WorldSubstrate()
    for i in range(MAX_ENTITIES):
        ws.add_entity(Entity(entity_id=f"e{i}", entity_type="t"))
    assert ws.summary()["entity_count"] == MAX_ENTITIES

    # One more new entity should be silently rejected
    ws.add_entity(Entity(entity_id="overflow", entity_type="t"))
    assert ws.get_entity("overflow") is None
    assert ws.summary()["entity_count"] == MAX_ENTITIES

    # But overwriting an existing entity should still work
    ws.add_entity(Entity(entity_id="e0", entity_type="updated"))
    assert ws.get_entity("e0").entity_type == "updated"


def test_relation_capacity_bound() -> None:
    """Adding more than MAX_RELATIONS should be rejected."""
    ws = WorldSubstrate()
    for i in range(MAX_RELATIONS):
        ws.add_relation(Relation(source_id="a", relation_type=f"r{i}", target_id="b"))
    assert ws.summary()["relation_count"] == MAX_RELATIONS

    # One more should be rejected
    result = ws.add_relation(
        Relation(source_id="a", relation_type="overflow", target_id="b")
    )
    assert result is False
    assert ws.summary()["relation_count"] == MAX_RELATIONS
