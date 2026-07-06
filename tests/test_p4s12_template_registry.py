"""P4S-12 — RealityTemplate registry: metamodel + registry enforcement.

Verifies the substrate home for the RealityTemplate ontology
(``substrate/templates/``) against the compiled seed
(``data/umh/templates/reality_template_taxonomy.json``) and the six essentialism
rules from ``docs/REALITY_TEMPLATE_GRAPH.md``:

  - taxonomy loads and every entry validates,
  - resolve-by-id works,
  - zero-instance-beyond-CANDIDATE is rejected (rule 2),
  - N≥2 extraction rule is enforced (rule 3),
  - instance-literal in a template body is rejected (rule 4),
  - cycle in a TemplateGraph is rejected + proof gates edges (rules 5),
  - revision history is append-only and immutable (rule 6),
  - RT-GOVERNED-PROPOSAL-LOOP is recorded PROVEN_1_INSTANCE with a #201 pointer.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from substrate.templates import (  # noqa: E402
    CapabilityRevision,
    RealityTemplate,
    RealityTemplateRegistry,
    RealityTemplateStatus,
    TemplateEdge,
    TemplateGraph,
    TemplateInstance,
    TemplateInvariant,
    TemplateProofRequirement,
    TemplateVariable,
    configure_instance_denylist,
    load_reality_template_registry,
)

_TAXONOMY = Path(_WORKTREE) / "data/umh/templates/reality_template_taxonomy.json"

# The substrate module ships identity-free: instance-literal scanning is a no-op
# until a denylist is configured for the running instance (loaded from BIS/config
# at runtime, never hardcoded in substrate). These tests configure a stand-in
# denylist of GENERIC placeholder tokens to exercise the rule-4 enforcement path
# without embedding any real tenant identity in the test either.
_DENYLIST = ("acme", "widgetco", "node-x")


@pytest.fixture(autouse=True)
def _configure_denylist():
    configure_instance_denylist(_DENYLIST)
    yield
    configure_instance_denylist(())  # reset to identity-free default


def _valid_bits() -> dict:
    """Minimal valid invariants/variables/proof for a template."""
    return {
        "invariants": [TemplateInvariant(statement="pending row is insert-only")],
        "variables": [TemplateVariable(name="tenant_id")],
        "proof_requirement": TemplateProofRequirement(description="server-truth chain"),
    }


# ── Taxonomy load + resolve ───────────────────────────────────────────────────


def test_taxonomy_loads_and_validates():
    registry = load_reality_template_registry(_TAXONOMY)
    assert len(registry) >= 6
    # Every loaded template is a validated RealityTemplate.
    for tpl in registry.list_templates():
        assert isinstance(tpl, RealityTemplate)
        assert tpl.invariants and tpl.variables and tpl.proof_requirement


def test_registry_class_constructs_and_loads():
    registry = RealityTemplateRegistry()
    assert len(registry) == 0
    n = registry.load_taxonomy(_TAXONOMY)
    assert n == len(registry) >= 6


def test_resolve_by_id_works():
    registry = load_reality_template_registry(_TAXONOMY)
    tpl = registry.resolve("RT-GOVERNED-PROPOSAL-LOOP")
    assert tpl is not None
    assert tpl.id == "RT-GOVERNED-PROPOSAL-LOOP"
    assert registry.resolve("RT-DOES-NOT-EXIST") is None
    assert "RT-GOVERNED-PROPOSAL-LOOP" in registry


def test_eos_loop_recorded_proven_1_instance_with_201_pointer():
    registry = load_reality_template_registry(_TAXONOMY)
    tpl = registry.resolve("RT-GOVERNED-PROPOSAL-LOOP")
    assert tpl.status is RealityTemplateStatus.PROVEN_1_INSTANCE
    assert tpl.source_instance  # no speculative proof
    assert tpl.instance_count >= 1
    # Proof pointer wired to PR #201 / the execution-proof audit doc.
    assert tpl.proof_pointer is not None
    assert "201" in tpl.proof_pointer
    assert "first_loop_execution_proof" in tpl.proof_pointer


# ── Rule 2: no speculative proof ──────────────────────────────────────────────


def test_proven_status_requires_source_instance():
    with pytest.raises(ValidationError):
        RealityTemplate(
            id="RT-SPECULATIVE",
            status=RealityTemplateStatus.PROVEN_1_INSTANCE,
            instance_count=1,
            source_instance=None,  # missing → speculative proof, rejected
            **_valid_bits(),
        )


def test_proven_1_instance_requires_count_at_least_one():
    with pytest.raises(ValidationError):
        RealityTemplate(
            id="RT-COUNT-ZERO",
            status=RealityTemplateStatus.PROVEN_1_INSTANCE,
            source_instance="eos/<tenant>",
            instance_count=0,  # incoherent with PROVEN_1_INSTANCE
            **_valid_bits(),
        )


def test_candidate_may_have_zero_instances():
    tpl = RealityTemplate(
        id="RT-CANDIDATE",
        status=RealityTemplateStatus.CANDIDATE,
        instance_count=0,
        **_valid_bits(),
    )
    assert tpl.status is RealityTemplateStatus.CANDIDATE
    assert tpl.instance_count == 0


# ── Rule 3: N≥2 before extraction ─────────────────────────────────────────────


def test_extraction_requires_two_instances():
    with pytest.raises(ValidationError):
        RealityTemplate(
            id="RT-EXTRACT-EARLY",
            status=RealityTemplateStatus.PROVEN_1_INSTANCE,
            source_instance="eos/<tenant>",
            instance_count=1,
            extraction_enabled=True,  # N=1 → extraction forbidden
            **_valid_bits(),
        )


def test_extraction_allowed_at_two_instances():
    tpl = RealityTemplate(
        id="RT-EXTRACT-OK",
        status=RealityTemplateStatus.PROVEN_N_INSTANCES,
        source_instance="eos/<tenant>",
        instance_count=2,
        extraction_enabled=True,
        **_valid_bits(),
    )
    assert tpl.extraction_enabled is True


# ── Rule 4: no instance literal in a template body ────────────────────────────


def test_instance_literal_in_invariant_rejected():
    with pytest.raises(ValueError):
        TemplateInvariant(statement="the node-x node approves the row")


def test_instance_literal_in_description_rejected():
    with pytest.raises(ValidationError):
        RealityTemplate(
            id="RT-LEAK",
            status=RealityTemplateStatus.CANDIDATE,
            description="acme's personal proposal loop",  # instance literal → rejected
            **_valid_bits(),
        )


def test_instance_literal_in_variable_name_rejected():
    # underscore-joined leak: 'widgetco_column' — plain \b would miss it.
    with pytest.raises(ValueError):
        TemplateVariable(name="widgetco_column")


def test_scanning_is_noop_when_denylist_empty():
    configure_instance_denylist(())
    # With no denylist configured, an arbitrary literal passes (substrate ships
    # identity-agnostic; the running instance opts in to its own identity list).
    inv = TemplateInvariant(statement="acme approves the widgetco row")
    assert inv.statement


# ── Rules 5: proof gates edges + DAG ─────────────────────────────────────────


def _proven_instance(ref: str) -> TemplateInstance:
    return TemplateInstance(
        template_id="RT-GOVERNED-PROPOSAL-LOOP",
        instance_ref=ref,
        proof_pointer="PR #201",
        proof_satisfied=True,
    )


def test_graph_rejects_edge_from_unproven_producer():
    unproven = TemplateInstance(template_id="RT-X", instance_ref="a")
    consumer = _proven_instance("b")
    graph = TemplateGraph(
        instances=[unproven, consumer],
        edges=[
            TemplateEdge(
                producer_instance_id=unproven.id,
                producer_proof_field="proof",
                consumer_instance_id=consumer.id,
                consumer_variable="tenant_id",
            )
        ],
    )
    with pytest.raises(ValueError, match="unproven producer"):
        graph.validate_graph()


def test_graph_rejects_cycle():
    a = _proven_instance("a")
    b = _proven_instance("b")
    graph = TemplateGraph(
        instances=[a, b],
        edges=[
            TemplateEdge(
                producer_instance_id=a.id,
                producer_proof_field="proof",
                consumer_instance_id=b.id,
                consumer_variable="x",
            ),
            TemplateEdge(
                producer_instance_id=b.id,
                producer_proof_field="proof",
                consumer_instance_id=a.id,
                consumer_variable="y",
            ),
        ],
    )
    with pytest.raises(ValueError, match="cycle"):
        graph.validate_graph()


def test_graph_accepts_valid_dag_with_proven_producers():
    a = _proven_instance("a")
    b = _proven_instance("b")
    graph = TemplateGraph(
        instances=[a, b],
        edges=[
            TemplateEdge(
                producer_instance_id=a.id,
                producer_proof_field="proof",
                consumer_instance_id=b.id,
                consumer_variable="x",
            )
        ],
    )
    graph.validate_graph()  # no raise


def test_self_edge_rejected():
    a = _proven_instance("a")
    with pytest.raises(ValidationError):
        TemplateEdge(
            producer_instance_id=a.id,
            producer_proof_field="p",
            consumer_instance_id=a.id,
            consumer_variable="v",
        )


# ── Rule 6: revision append-only + immutable ─────────────────────────────────


def test_revision_is_immutable():
    rev = CapabilityRevision(
        template_id="RT-GOVERNED-PROPOSAL-LOOP",
        from_version=1,
        to_version=2,
        change_summary="registered MutationSpec promoted to invariant",
        motivating_proofs=["PR #197"],
    )
    with pytest.raises(ValidationError):
        rev.change_summary = "mutated"  # frozen model


def test_revision_must_advance_version():
    with pytest.raises(ValidationError):
        CapabilityRevision(
            template_id="RT-X",
            from_version=2,
            to_version=2,  # not forward
            change_summary="noop",
            motivating_proofs=["PR #201"],
        )


def test_registry_revision_history_is_append_only():
    registry = load_reality_template_registry(_TAXONOMY)
    tid = "RT-GOVERNED-PROPOSAL-LOOP"
    registry.record_revision(
        CapabilityRevision(
            template_id=tid,
            from_version=1,
            to_version=2,
            change_summary="FK-safe principal stamping",
            motivating_proofs=["PR #198"],
        )
    )
    # A revision that does not advance beyond the last recorded version is rejected.
    with pytest.raises(ValueError, match="append-only"):
        registry.record_revision(
            CapabilityRevision(
                template_id=tid,
                from_version=1,
                to_version=2,
                change_summary="duplicate",
                motivating_proofs=["PR #198"],
            )
        )
    assert len(registry.revisions_for(tid)) == 1


# ── Instance registration ─────────────────────────────────────────────────────


def test_register_instance_requires_known_template():
    registry = load_reality_template_registry(_TAXONOMY)
    with pytest.raises(ValueError, match="unknown template"):
        registry.register_instance(TemplateInstance(template_id="RT-NOPE", instance_ref="x"))


def test_register_instance_for_known_template():
    registry = load_reality_template_registry(_TAXONOMY)
    inst = _proven_instance("eos/<tenant>")
    registry.register_instance(inst)
    got = registry.instances_for("RT-GOVERNED-PROPOSAL-LOOP")
    assert len(got) == 1
    assert got[0].is_proven
