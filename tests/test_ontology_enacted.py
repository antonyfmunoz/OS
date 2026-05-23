"""Tests for substrate.ontology — primitives, laws, and domain bridges.

Phase 6 invariant verification.
"""
from __future__ import annotations

import uuid
import pytest

from substrate.ontology.primitives import PrimitiveObservation
from substrate.ontology.laws import Law, LawCategory, LawRegistry, Severity
from substrate.ontology.domains.contract import DomainProjection, DomainBridge, make_projection_id
from substrate.types import PrimitiveType, RelationshipType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_observation(**kwargs) -> PrimitiveObservation:
    defaults = dict(
        id=str(uuid.uuid4()),
        primitive_type=PrimitiveType.STATE,
        label="test observation",
        description="a test observation",
        evidence="some evidence text",
        source_ref="test-source",
        confidence=0.9,
        relationships=[],
        metadata={},
    )
    defaults.update(kwargs)
    return PrimitiveObservation(**defaults)


def _make_projection(**kwargs) -> DomainProjection:
    defaults = dict(
        projection_id=make_projection_id(),
        domain_id="test",
        domain_primitive_type="test_type",
        label="test projection",
        description="test description",
        properties={},
        ontology_observation_ref=str(uuid.uuid4()),
        confidence=0.85,
        evidence="some evidence",
    )
    defaults.update(kwargs)
    return DomainProjection(**defaults)


def _make_law(**kwargs) -> Law:
    defaults = dict(
        category=LawCategory.GOVERNANCE,
        name="test-law-" + uuid.uuid4().hex[:6],
        statement="must hold true",
        severity=Severity.WARNING,
    )
    defaults.update(kwargs)
    return Law(**defaults)


# ---------------------------------------------------------------------------
# PrimitiveObservation
# ---------------------------------------------------------------------------

class TestPrimitiveObservation:
    def test_creates_with_required_fields(self):
        obs = _make_observation()
        assert obs.primitive_type == PrimitiveType.STATE
        assert obs.label == "test observation"

    def test_all_primitive_types_valid(self):
        for pt in PrimitiveType:
            obs = _make_observation(primitive_type=pt)
            assert obs.primitive_type == pt

    def test_confidence_range(self):
        obs = _make_observation(confidence=0.0)
        assert obs.confidence == 0.0
        obs2 = _make_observation(confidence=1.0)
        assert obs2.confidence == 1.0

    def test_relationships_default_empty(self):
        obs = _make_observation()
        assert isinstance(obs.relationships, list)

    def test_is_pydantic_model(self):
        obs = _make_observation()
        data = obs.model_dump()
        assert "primitive_type" in data
        assert "label" in data


# ---------------------------------------------------------------------------
# Laws
# ---------------------------------------------------------------------------

class TestLaws:
    def test_law_creates(self):
        law = _make_law(name="test-creates", category=LawCategory.ONTOLOGICAL)
        assert law.category == LawCategory.ONTOLOGICAL

    def test_law_is_pydantic(self):
        law = _make_law(name="test-pydantic")
        data = law.model_dump()
        assert "id" in data
        assert "statement" in data

    def test_law_check_passes_when_no_context_key(self):
        law = _make_law(name="test-check-pass", context_key="")
        # No context_key — check should always pass (return None)
        result = law.check({})
        assert result is None

    def test_law_check_violation_when_key_missing(self):
        law = _make_law(
            name="test-check-violation",
            context_key="required_flag",
            expected_value=True,
            severity=Severity.HARD_BLOCK,
        )
        result = law.check({})
        assert result is not None  # violation: key absent

    def test_law_check_passes_when_key_matches(self):
        law = _make_law(
            name="test-check-ok",
            context_key="required_flag",
            expected_value=True,
        )
        result = law.check({"required_flag": True})
        assert result is None

    def test_law_registry_pre_populated(self):
        registry = LawRegistry()
        assert len(registry.all()) > 0

    def test_law_registry_get_existing(self):
        registry = LawRegistry()
        all_laws = registry.all()
        first = all_laws[0]
        retrieved = registry.get(first.name)
        assert retrieved is not None
        assert retrieved.name == first.name

    def test_law_registry_get_missing_returns_none(self):
        registry = LawRegistry()
        result = registry.get("nonexistent-law-xyz")
        assert result is None

    def test_law_registry_check_all_returns_list(self):
        registry = LawRegistry()
        violations = registry.check_all({})
        assert isinstance(violations, list)

    def test_law_registry_hard_violations_subset(self):
        registry = LawRegistry()
        all_v = registry.check_all({})
        hard_v = registry.hard_violations({})
        # Hard violations are a subset of all violations
        for v in hard_v:
            assert v in all_v


# ---------------------------------------------------------------------------
# DomainProjection (Pydantic, not dataclass — invariant 10)
# ---------------------------------------------------------------------------

class TestDomainProjection:
    def test_creates_as_pydantic_model(self):
        proj = _make_projection()
        assert isinstance(proj, DomainProjection)
        assert hasattr(proj, "to_dict")

    def test_to_dict_returns_all_fields(self):
        proj = _make_projection(label="specific label")
        d = proj.to_dict()
        assert d["label"] == "specific label"
        assert "projection_id" in d
        assert "domain_id" in d
        assert "confidence" in d

    def test_authority_tier_defaults_to_5(self):
        proj = _make_projection()
        assert proj.authority_tier == 5

    def test_make_projection_id_format(self):
        pid = make_projection_id()
        assert pid.startswith("proj-")
        assert len(pid) > 5

    def test_serialization_roundtrip(self):
        proj = _make_projection(domain_id="business", confidence=0.77)
        data = proj.to_dict()
        proj2 = DomainProjection(**data)
        assert proj2.domain_id == "business"
        assert proj2.confidence == 0.77
