"""Tests for Layer 0 foundation — ontological primitives, laws, epistemology, derived constructs.

Adapted from umh_mvp/tests/test_layer0.py. Validates structural completeness
and integrity of services/umh/foundation/ against its own type system.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.foundation.primitives import (
    CausalRole,
    Modality,
    OntologicalCategory,
    OntologicalPrimitive,
    Relation,
    TemporalMode,
)
from services.umh.foundation.laws import (
    Law,
    LawCategory,
    Severity,
    SUBSTRATE_LAWS,
)
from services.umh.foundation.epistemology import (
    Belief,
    ConfidenceLevel,
    EpistemicRevision,
    EpistemicStatus,
    EvidenceType,
    KnowledgeGap,
)
from services.umh.foundation.derived_constructs import (
    Commitment,
    Context,
    Goal,
    GoalStatus,
    Plan,
    PlanStep,
)


def test_ontological_category_count():
    assert len(list(OntologicalCategory)) == 8


def test_temporal_mode_count():
    assert len(list(TemporalMode)) == 4


def test_modality_count():
    assert len(list(Modality)) == 5


def test_substrate_law_count():
    assert len(SUBSTRATE_LAWS) == 6


def test_substrate_laws_all_have_names():
    for law in SUBSTRATE_LAWS:
        assert law.name, f"Law {law.id} has no name"
        assert len(law.name) > 0


def test_substrate_laws_all_enforceable():
    for law in SUBSTRATE_LAWS:
        assert law.enforceable, f"Law '{law.name}' is not enforceable"


def test_hard_block_laws_exist():
    hard_laws = [l for l in SUBSTRATE_LAWS if l.severity == Severity.HARD_BLOCK]
    assert len(hard_laws) >= 5, f"Expected ≥5 hard-block laws, got {len(hard_laws)}"


def test_epistemic_status_count():
    assert len(list(EpistemicStatus)) == 6


def test_law_immutability():
    law = SUBSTRATE_LAWS[0]
    try:
        law.name = "changed"
        assert False, "Law should reject field assignment"
    except Exception:
        pass


def test_ontological_primitive_creation():
    prim = OntologicalPrimitive(
        category=OntologicalCategory.ENTITY,
        label="test entity",
        temporal_mode=TemporalMode.DURATIVE,
        modality=Modality.ACTUAL,
        causal_role=CausalRole.CAUSE,
    )
    assert prim.is_temporal()
    assert prim.is_actual()
    assert prim.category == OntologicalCategory.ENTITY


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
