"""Tests for umh.protocols.state."""

import pytest
from pydantic import ValidationError

from umh.protocols.state import (
    Fact,
    MemoryRecord,
    WorldEntity,
    WorldState,
)
from umh.protocols.common import MemoryType, PromotionStatus


class TestWorldEntity:
    def test_minimal_construction(self) -> None:
        e = WorldEntity(
            entity_id="ent-1",
            type="person",
            name="Antony",
            confidence=0.95,
            source="user_input",
            timestamp=1700000000,
        )
        assert e.SCHEMA_VERSION == "1.0.0"
        assert e.attributes == {}

    def test_roundtrip(self) -> None:
        e = WorldEntity(
            entity_id="ent-2",
            type="company",
            name="Lyfe Institute",
            attributes={"revenue": 0, "stage": "pre_revenue"},
            confidence=0.9,
            source="crm",
            timestamp=1700000001,
        )
        assert WorldEntity.model_validate(e.model_dump()) == e

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            WorldEntity(
                entity_id="x", type="x", name="x",
                confidence=1.0, source="x", timestamp=0,
                bogus="bad",
            )


class TestFact:
    def test_minimal_construction(self) -> None:
        f = Fact(
            value="Portland, Oregon",
            confidence=1.0,
            source="user_profile",
            timestamp=1700000000,
            scope="personal",
        )
        assert f.SCHEMA_VERSION == "1.0.0"
        assert f.expiry is None

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            Fact(value="x", confidence=1.0)  # type: ignore[call-arg]


class TestWorldState:
    def test_minimal_construction(self) -> None:
        ws = WorldState()
        assert ws.entities == []
        assert ws.SCHEMA_VERSION == "1.0.0"

    def test_roundtrip(self) -> None:
        ws = WorldState(
            entities=[
                WorldEntity(
                    entity_id="e-1", type="person", name="test",
                    confidence=1.0, source="test", timestamp=0,
                )
            ],
            state_values={"mode": "developer"},
        )
        assert WorldState.model_validate(ws.model_dump()) == ws


class TestMemoryRecord:
    def test_minimal_construction(self) -> None:
        mr = MemoryRecord(
            memory_id="mem-1",
            type=MemoryType.EPISODIC,
            content="user completed onboarding",
            source="system",
            confidence=0.95,
            timestamp=1700000000,
            scope="user",
            promotion_status=PromotionStatus.CANDIDATE,
            reason="first interaction",
        )
        assert mr.SCHEMA_VERSION == "1.0.0"
        assert mr.tags == []

    def test_roundtrip(self) -> None:
        mr = MemoryRecord(
            memory_id="mem-2",
            type=MemoryType.CANONICAL,
            content={"fact": "UMH is governed orchestration"},
            source="synthesis",
            confidence=1.0,
            timestamp=1700000001,
            scope="system",
            promotion_status=PromotionStatus.CANONICAL,
            reason="invariant law",
        )
        assert MemoryRecord.model_validate(mr.model_dump()) == mr

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            MemoryRecord(
                memory_id="x", type=MemoryType.WORKING, content="x",
                source="x", confidence=1.0, timestamp=0, scope="x",
                promotion_status=PromotionStatus.CANDIDATE, reason="x",
                extra_field="bad",
            )

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            MemoryRecord(memory_id="x", type=MemoryType.WORKING)  # type: ignore[call-arg]
