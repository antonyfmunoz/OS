"""Tests for umh.protocols.understanding."""

import pytest
from pydantic import ValidationError

from control_plane.protocols.understanding import (
    DomainMap,
    IntentCandidate,
    InterpretedSignal,
    Primitive,
    PrimitiveMapping,
    Relationship,
    Signal,
)
from control_plane.protocols.common import (
    EvidenceRef,
    EvidenceType,
    PrimitiveType,
    RelationshipType,
    SignalModality,
)


class TestSignal:
    def test_minimal_construction(self) -> None:
        s = Signal(
            signal_id="sig-1",
            modality=SignalModality.TEXT,
            source="discord",
            content="hello",
            timestamp=1700000000,
            confidence=0.9,
        )
        assert s.SCHEMA_VERSION == "1.0.0"
        assert s.environment is None

    def test_serialization_roundtrip(self) -> None:
        s = Signal(
            signal_id="sig-2",
            modality=SignalModality.API_EVENT,
            source="webhook",
            content={"data": [1, 2, 3]},
            timestamp=1700000001,
            confidence=0.95,
            metadata={"source_ip": "127.0.0.1"},
        )
        assert Signal.model_validate(s.model_dump()) == s

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Signal(
                signal_id="sig-3",
                modality=SignalModality.TEXT,
                source="test",
                content="x",
                timestamp=0,
                confidence=1.0,
                bogus="field",
            )

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            Signal(signal_id="sig-4", modality=SignalModality.TEXT)  # type: ignore[call-arg]


class TestInterpretedSignal:
    def test_minimal_construction(self) -> None:
        interp = InterpretedSignal(
            signal_id="sig-1",
            ambiguity_score=0.2,
            risk_score=0.1,
            confidence=0.85,
            explanation="simple text input",
        )
        assert interp.intent_candidates == []
        assert interp.SCHEMA_VERSION == "1.0.0"

    def test_with_intent_candidates(self) -> None:
        interp = InterpretedSignal(
            signal_id="sig-2",
            intent_candidates=[
                IntentCandidate(
                    intent_id="i-1",
                    description="deploy code",
                    confidence=0.9,
                    domain="software",
                )
            ],
            ambiguity_score=0.1,
            risk_score=0.3,
            confidence=0.9,
            explanation="clear deploy intent",
        )
        assert len(interp.intent_candidates) == 1
        assert interp.intent_candidates[0].domain == "software"


class TestPrimitiveMapping:
    def test_minimal_construction(self) -> None:
        pm = PrimitiveMapping(
            source_id="doc-1",
            source_type="document",
            confidence=0.8,
        )
        assert pm.primitives == []
        assert pm.SCHEMA_VERSION == "1.0.0"

    def test_with_primitives_and_relationships(self) -> None:
        pm = PrimitiveMapping(
            source_id="doc-2",
            source_type="email",
            primitives=[
                Primitive(
                    primitive_id="p-1",
                    type=PrimitiveType.GOAL,
                    label="escape default life",
                    confidence=0.9,
                )
            ],
            relationships=[
                Relationship(
                    relationship_id="r-1",
                    type=RelationshipType.ENABLES,
                    source_id="p-1",
                    target_id="p-2",
                )
            ],
            confidence=0.85,
            evidence=[EvidenceRef(ref_id="ev-1", source="llm", evidence_type=EvidenceType.RUNTIME_ASSERTION)],
        )
        assert len(pm.primitives) == 1
        assert pm.primitives[0].type == PrimitiveType.GOAL

    def test_roundtrip(self) -> None:
        pm = PrimitiveMapping(
            source_id="doc-3",
            source_type="note",
            confidence=0.7,
        )
        assert PrimitiveMapping.model_validate(pm.model_dump()) == pm


class TestDomainMap:
    def test_minimal_construction(self) -> None:
        dm = DomainMap(domain_id="d-1", name="business")
        assert dm.subdomains == []
        assert dm.domain_laws == []
        assert dm.SCHEMA_VERSION == "1.0.0"

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DomainMap(domain_id="d-2", name="test", extra="bad")
