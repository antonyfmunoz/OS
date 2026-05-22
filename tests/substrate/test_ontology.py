import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/substrate-unification")

import pytest

from substrate.ontology.primitives import OntologicalCategory, PrimitiveType
from substrate.ontology.relationships import RelationshipType
from substrate.ontology.laws import get_laws


class TestOntologyEnums:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10
        expected = {
            "state",
            "change",
            "constraint",
            "resource",
            "signal",
            "action",
            "outcome",
            "feedback",
            "goal",
            "time",
        }
        assert {p.value for p in PrimitiveType} == expected

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8
        expected = {
            "entity",
            "relation",
            "event",
            "property",
            "process",
            "state",
            "constraint",
            "boundary",
        }
        assert {c.value for c in OntologicalCategory} == expected

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10

    def test_primitive_observation_uses_pydantic(self):
        from substrate.types import PrimitiveObservation

        from pydantic import BaseModel

        assert issubclass(PrimitiveObservation, BaseModel)

    def test_primitive_observation_validates_label_length(self):
        from pydantic import ValidationError

        from substrate.types import PrimitiveObservation, PrimitiveType

        with pytest.raises(ValidationError):
            PrimitiveObservation(
                primitive_type=PrimitiveType.STATE,
                label="x" * 81,
                description="test",
            )


class TestLaws:
    def test_laws_exist(self):
        laws = get_laws()
        assert isinstance(laws, list)
        assert len(laws) > 0

    def test_each_law_has_name_and_description(self):
        laws = get_laws()
        for law in laws:
            assert "name" in law
            assert "description" in law

    def test_spec_invariants_present(self):
        """All 8 spec invariants must be in the registry."""
        laws = get_laws()
        names = {law["name"] for law in laws}
        required = {
            "identity_before_execution",
            "governance_before_action",
            "trace_everything",
            "feedback_closes_loops",
            "registry_is_truth",
            "memory_discipline",
            "deterministic_first",
            "pydantic_only",
        }
        assert required.issubset(names)

    def test_foundation_laws_present(self):
        """Foundation laws from services/umh/foundation/laws.py must be included."""
        laws = get_laws()
        names = {law["name"] for law in laws}
        foundation = {
            "signal_intake",
            "no_direct_execution",
            "adapter_mediation",
            "memory_pathway",
            "traceability",
            "epistemic_humility",
        }
        assert foundation.issubset(names)

    def test_no_duplicate_law_names(self):
        laws = get_laws()
        names = [law["name"] for law in laws]
        assert len(names) == len(set(names))

    def test_enforcement_values(self):
        laws = get_laws()
        for law in laws:
            assert law["enforcement"] in ("hard", "soft")
