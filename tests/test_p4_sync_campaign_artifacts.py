"""P4-SYNC campaign artifact validation — tenant safety + schema integrity.

Validates the compile-mode deliverables:
  - the four JSON artifacts parse and carry their declared structure,
  - NO artifact hardcodes the first tenant (Antony) or a device hostname as
    global truth — instance bindings may appear ONLY inside clearly
    instance-scoped fields, and templates/standards must be instance-free,
  - the workgraph respects the provider hard-hold (no provider packet without
    the W1/W2 merge gate dependency),
  - essentialism: no zero-instance template is marked beyond CANDIDATE.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_ROOT = Path(_WORKTREE)
_CAPS = _ROOT / "data/umh/capabilities/cross_projection_capability_inventory.json"
_MATRIX = _ROOT / "data/umh/projections/projection_connection_matrix.json"
_TAXONOMY = _ROOT / "data/umh/templates/reality_template_taxonomy.json"
_WORKGRAPH = _ROOT / "data/umh/roadmap/p4_sync_workgraph.json"

# Identifiers that are FIRST-TENANT instance values, never global truth.
# They may appear only in fields that explicitly declare instance scope.
_TENANT_LITERALS = ("antony", "afm", "munoz", "beast")


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_all_artifacts_parse_and_declare_compile_mode():
    for path in (_CAPS, _MATRIX, _TAXONOMY, _WORKGRAPH):
        data = _load(path)
        assert "compile" in data.get("mode", ""), f"{path.name} must declare compile mode"


def test_no_tenant_literal_as_global_truth_in_templates_and_capabilities():
    """Templates and the capability inventory must be instance-free entirely."""
    for path in (_TAXONOMY, _CAPS):
        text = json.dumps(_load(path)).lower()
        for literal in _TENANT_LITERALS:
            assert literal not in text, (
                f"{path.name} contains first-tenant literal {literal!r} — "
                "instance values bind through variables, never template/capability bodies"
            )


def test_connection_matrix_tenant_values_are_placeholder_scoped():
    """The matrix carries first-tenant ROWS but tenant_id itself must be a
    placeholder and personal identifiers must not appear anywhere."""
    data = _load(_MATRIX)
    text = json.dumps(data).lower()
    for literal in ("antony", "afm", "munoz"):
        assert literal not in text, f"matrix must not name the person: {literal!r}"
    for proj in data["projections"].values():
        assert proj["tenant_id"] == "<tenant>", "tenant_id must be an unbound placeholder in the compiled matrix"
    # device identity may appear only in source_node bindings, nowhere else
    for proj_id, proj in data["projections"].items():
        for slot, value in proj.items():
            if slot in ("source_node", "hardening_open"):
                continue
            assert "beast" not in str(value).lower(), (
                f"{proj_id}.{slot} carries a device literal outside the source_node binding"
            )


def test_connection_matrix_covers_all_17_slots():
    data = _load(_MATRIX)
    slots = data["connection_slots"]
    assert len(slots) == 17
    for proj_id, proj in data["projections"].items():
        for slot in slots:
            assert slot in proj or slot in ("tenant_id", "projection_id") and slot in proj, (
                f"{proj_id} missing slot {slot}"
            )


def test_capability_inventory_rows_are_fully_classified():
    data = _load(_CAPS)
    required = {"name", "location", "maturity", "owner", "duplicates", "candidate",
                "extraction_priority", "mvp_relevant"}
    legend = data["classification_legend"]
    for cap in data["capabilities"]:
        missing = required - set(cap)
        assert not missing, f"capability {cap.get('name')} missing {missing}"
        assert cap["maturity"] in legend["maturity"]
        assert cap["candidate"] in legend["candidate"]
        assert cap["extraction_priority"] in legend["extraction_priority"]


def test_no_speculative_templates():
    data = _load(_TAXONOMY)
    for tpl in data["template_candidates"]:
        status = tpl["status"]
        assert status in ("PROVEN_1_INSTANCE", "PROVEN_N_INSTANCES", "CANDIDATE")
        if status.startswith("PROVEN"):
            assert tpl.get("source_instance"), f"{tpl['id']} proven without a source instance"
        assert tpl.get("invariants") and tpl.get("variables") and tpl.get("proof_requirement"), (
            f"{tpl['id']} must declare invariants, variables, and a proof requirement"
        )


def test_workgraph_provider_packet_is_hard_held_behind_w1_w2():
    data = _load(_WORKGRAPH)
    provider = [p for p in data["packets"] if "provider" in p["objective"].lower()
                or "send_email" in p["objective"].lower()]
    assert provider, "workgraph must carry the provider packet explicitly"
    for p in provider:
        deps = " ".join(p["dependencies"]).lower()
        assert "merge-gate-0" in deps, f"{p['id']} must depend on the W1/W2 merge gate"
        assert p.get("hard_hold"), f"{p['id']} must carry an explicit hard hold"


def test_workgraph_packets_are_executable_runbooks():
    data = _load(_WORKGRAPH)
    required = {"id", "objective", "dependencies", "expected_files", "tests",
                "proof", "rollback", "stop_conditions", "executor", "lane"}
    for p in data["packets"]:
        missing = required - set(p)
        assert not missing, f"packet {p.get('id')} missing {missing}"
        assert p["executor"] in ("Opus", "Sonnet")
