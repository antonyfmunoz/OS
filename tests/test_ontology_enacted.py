"""Tests that ontology primitives are enacted constraints, not just enums."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from substrate.types import PrimitiveType, OntologicalCategory, RelationshipType


class TestOntologyEnums:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10


class TestOntologyPrimitivesModule:
    def test_reexports_all_types(self):
        from substrate.ontology.primitives import (
            PrimitiveType,
            OntologicalCategory,
            PrimitiveObservation,
            TemporalMode,
            CausalRole,
        )

        assert len(PrimitiveType) == 10
        assert len(TemporalMode) == 4
        assert len(CausalRole) == 5

    def test_primitive_observation_has_required_fields(self):
        from substrate.ontology.primitives import PrimitiveObservation

        obs = PrimitiveObservation(
            primitive_type=PrimitiveType.STATE,
            label="test",
            description="test observation",
        )
        assert obs.primitive_type == PrimitiveType.STATE
        assert obs.confidence == 0.8  # default


from substrate.ontology.laws import LawRegistry, Law, LawCategory, Severity


class TestLawsAreCallable:
    def test_law_registry_has_laws(self):
        registry = LawRegistry()
        laws = registry.all()
        assert len(laws) >= 12  # 6 foundation + 8 spec (some overlap)

    def test_law_is_pydantic_model(self):
        registry = LawRegistry()
        for law in registry.all():
            assert isinstance(law, Law)
            assert hasattr(law, "name")
            assert hasattr(law, "severity")

    def test_check_returns_violation_or_none(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        result = law.check({"has_governance_verdict": True})
        assert result is None  # no violation

    def test_check_returns_violation_string(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        result = law.check({"has_governance_verdict": False})
        assert isinstance(result, str)  # violation message

    def test_hard_block_severity(self):
        registry = LawRegistry()
        law = registry.get("governance_before_action")
        assert law is not None
        assert law.severity == Severity.HARD_BLOCK
