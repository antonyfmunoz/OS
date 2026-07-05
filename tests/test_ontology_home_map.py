"""WP-P3 — ontology-home consolidation tests.

Proves the ontology-home map is unambiguous and enforced:
- substrate/ontology is L2-only (no L3 vocab, no projection/BIS imports).
- substrate/reality_model is L1/current-reality-oriented (no projection/BIS imports).
- substrate/understanding/domains is L4 bridge/grounding.
- no new projection-domain object can enter L2 (existing ontology gate).
- known legacy homes/competitors are frozen and cannot grow (shrink-only).
- the new home gate blocks new unclassified homes and competing registries.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.check_ontology_homes import (  # noqa: E402
    FROZEN_ONTOLOGY_COMPETITORS,
    FROZEN_ONTOLOGY_HOMES,
)


def _run(gate: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / gate), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


# ── substrate/ontology is L2-only ────────────────────────────────────────────


def test_substrate_ontology_has_no_projection_or_bis_imports():
    for py in (ROOT / "substrate" / "ontology").rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            s = line.strip()
            # allow the noqa re-export shims of understanding/domains bridges
            if s.startswith(("from projections", "import projections")):
                raise AssertionError(f"{py}: L2 ontology imports a projection: {s}")
            if s.startswith(("from substrate.state.business", "import substrate.state.business")):
                raise AssertionError(f"{py}: L2 ontology imports BIS state: {s}")


def test_substrate_ontology_l2_gate_still_active():
    # the existing L2-surface gate must remain green on substrate/ontology
    r = _run("check_ontology_layers.py", "--all")
    assert r.returncode == 0, r.stdout


# ── substrate/reality_model is L1/current-reality-oriented ───────────────────


def test_reality_model_has_no_projection_or_bis_imports():
    for py in (ROOT / "substrate" / "reality_model").rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("from projections", "import projections")):
                raise AssertionError(f"{py}: L1 reality_model imports a projection: {s}")
            if s.startswith(("from substrate.state.business", "import substrate.state.business")):
                raise AssertionError(f"{py}: L1 reality_model imports BIS state: {s}")


def test_reality_model_is_classified_l1_and_l4_write():
    # every reality_model home is frozen as L1 (or the L4 write path)
    rm = {
        k: v for k, v in FROZEN_ONTOLOGY_HOMES.items() if k.startswith("substrate/reality_model/")
    }
    assert rm, "reality_model homes must be classified"
    assert rm["substrate/reality_model/canonical_reality_write.py"] == "L4-write"
    for k, v in rm.items():
        if k.endswith("canonical_reality_write.py"):
            continue
        assert v == "L1", f"{k} should be L1, got {v}"


# ── substrate/understanding/domains is L4 ────────────────────────────────────


def test_understanding_domains_is_l4():
    dom = {
        k: v
        for k, v in FROZEN_ONTOLOGY_HOMES.items()
        if k.startswith("substrate/understanding/domains/")
    }
    assert dom, "understanding/domains homes must be classified"
    for k, v in dom.items():
        assert v == "L4", f"{k} should be L4, got {v}"


# ── shrink-only ledgers ──────────────────────────────────────────────────────


def test_frozen_home_set_matches_disk():
    """Every frozen home exists; no frozen home has silently disappeared."""
    for rel in FROZEN_ONTOLOGY_HOMES:
        assert (ROOT / rel).exists(), f"frozen home missing on disk: {rel}"


def test_frozen_home_set_is_shrink_only():
    """The home set may only shrink. This count freezes today's membership (25,
    down from 27 after the WP-P3 primitives relocation evicted
    understanding/ontology/primitives.py, then to 25 after the WP-P3 rehome moved
    understanding/ontology/primitive_decomposition_v1.py to the perception home).
    A NEW home must be a deliberate edit here AND to the gate ledger."""
    assert len(FROZEN_ONTOLOGY_HOMES) <= 25, (
        f"FROZEN_ONTOLOGY_HOMES grew to {len(FROZEN_ONTOLOGY_HOMES)}; new homes must be "
        "reviewed, not silently added"
    )


def test_frozen_competitors_are_shrink_only_with_metadata():
    # Shrank 3 → 2 at the WP-P3 world-model sunset (understanding/world_model
    # resolved via disambiguation), 2 → 1 at the WP-P3 primitives relocation
    # (understanding/ontology/primitives.py → substrate/state/business/), then
    # 1 → 0 at the WP-P3 rehome (understanding/ontology/primitive_decomposition_v1.py
    # split: enums repointed to substrate.types, perception dataclasses moved to
    # substrate/understanding/perception/). No frozen ontology-home competitors remain.
    assert len(FROZEN_ONTOLOGY_COMPETITORS) == 0, (
        f"FROZEN_ONTOLOGY_COMPETITORS is {len(FROZEN_ONTOLOGY_COMPETITORS)}; all P3 "
        "ontology-home competitors are resolved — none may reappear"
    )
    for rel, (disposition, sunset) in FROZEN_ONTOLOGY_COMPETITORS.items():
        assert (ROOT / rel).exists(), f"frozen competitor missing: {rel}"
        assert disposition and sunset, f"{rel} missing disposition/sunset metadata"


def test_world_model_resolved_out_of_competitor_ledger():
    """The understanding world model is a distinct concern, not a competitor:
    removed from the competitor ledger, still a classified home, and both
    world_model modules carry reciprocal disambiguation docstrings."""
    assert "substrate/understanding/world_model/world_model.py" not in FROZEN_ONTOLOGY_COMPETITORS
    assert (
        FROZEN_ONTOLOGY_HOMES["substrate/understanding/world_model/world_model.py"]
        == "understanding-world-model"
    )
    understanding = (ROOT / "substrate/understanding/world_model/world_model.py").read_text()
    organism = (ROOT / "substrate/organism/world_model.py").read_text()
    assert "NOT the organism self-model" in understanding
    assert "NOT the understanding/world_model" in organism


def test_primitives_relocated_out_of_both_ledgers():
    """The L3 business-rule primitives were EVICTED by relocation (not
    disambiguation): git-moved from understanding/ontology/ to its L3 state home
    substrate/state/business/. It is gone from BOTH Gate-13 ledgers, absent at the
    old path, present at the new path, and no longer under a guarded ontology dir."""
    old = "substrate/understanding/ontology/primitives.py"
    new = "substrate/state/business/primitives.py"
    assert old not in FROZEN_ONTOLOGY_COMPETITORS
    assert old not in FROZEN_ONTOLOGY_HOMES
    assert not (ROOT / old).exists(), "old ontology-dir path must be gone (no shim)"
    assert (ROOT / new).exists(), "primitives.py must live at its L3 state home"
    # the new home is NOT a guarded ontology-home dir, so it needs no home entry
    assert new not in FROZEN_ONTOLOGY_HOMES


def test_primitive_decomposition_v1_rehomed_and_split():
    """The last frozen competitor was resolved by a SPLIT (WP-P3 rehome):
    - the PrimitiveType / RelationshipType enum fork is gone — the moved module
      imports the *canonical* substrate.types enums (identity-equal objects);
    - the perception dataclasses (PrimitiveObservation v1 / PrimitiveRelationship /
      DecompositionResult / REQUIRED_PRIMITIVE_TYPES) moved intact to the perception
      home with behavior unchanged;
    - the old ontology-dir path is gone (no shim) and the module is out of both
      Gate-13 ledgers; the perception home is not a guarded ontology dir."""
    import importlib

    old_rel = "substrate/understanding/ontology/primitive_decomposition_v1.py"
    new_rel = "substrate/understanding/perception/primitive_decomposition_v1.py"

    # ledgers: gone from both, competitor count is zero
    assert old_rel not in FROZEN_ONTOLOGY_COMPETITORS
    assert old_rel not in FROZEN_ONTOLOGY_HOMES
    assert new_rel not in FROZEN_ONTOLOGY_HOMES  # perception is not a guarded home

    # disk: old gone (no shim), new present
    assert not (ROOT / old_rel).exists(), "old ontology-dir path must be gone (no shim)"
    assert (ROOT / new_rel).exists(), "perception model must live at its perception home"

    # old import path must not resolve (no shim)
    try:
        importlib.import_module("substrate.understanding.ontology.primitive_decomposition_v1")
        raise AssertionError("old module path still importable — a shim leaked")
    except ModuleNotFoundError:
        pass

    # enum fork removed: the moved module's PrimitiveType/RelationshipType ARE the
    # canonical substrate.types objects (same identity, not a parallel definition)
    import substrate.types as canon

    moved = importlib.import_module(
        "substrate.understanding.perception.primitive_decomposition_v1"
    )
    assert moved.PrimitiveType is canon.PrimitiveType
    assert moved.RelationshipType is canon.RelationshipType

    # perception dataclasses preserved with behavior unchanged
    obs = moved.PrimitiveObservation(
        observation_id="OBS-1",
        primitive_type=canon.PrimitiveType.GOAL,
        label="ship",
        description="ship the thing",
        confidence=0.9,
        source_reference="doc:1",
        evidence="e",
        is_inferred=False,
        authority_tier=3,
    )
    d = obs.to_dict()
    assert d["observation_id"] == "OBS-1"
    assert d["primitive_type"] == "goal"
    assert d["is_inferred"] is False
    assert d["authority_tier"] == 3

    rel = moved.PrimitiveRelationship(
        from_observation_id="OBS-1",
        to_observation_id="OBS-2",
        relationship_type=canon.RelationshipType.ENABLES,
        confidence=0.8,
    )
    assert rel.to_dict()["relationship_type"] == "enables"

    result = moved.DecompositionResult(
        decomposition_id="D-1",
        source_content_hash="abc",
        observations=[obs],
        relationships=[rel],
    )
    cov = result.compute_coverage()
    assert cov == {"goal": 1}
    assert result.to_dict()["primitive_type_coverage"] == {"goal": 1}

    # REQUIRED_PRIMITIVE_TYPES preserved and equal to all canonical primitive types
    assert moved.REQUIRED_PRIMITIVE_TYPES == frozenset(canon.PrimitiveType)


# ── the home gate enforces the map (negative controls) ───────────────────────


def test_home_gate_passes_on_current_tree():
    r = _run("check_ontology_homes.py", "--all")
    assert r.returncode == 0, r.stdout


def test_home_gate_blocks_new_unclassified_home(tmp_path):
    victim = ROOT / "substrate" / "ontology" / "_tmp_test_new_home.py"
    victim.write_text("class X:\n    pass\n")
    try:
        r = _run("check_ontology_homes.py", "--file", "substrate/ontology/_tmp_test_new_home.py")
        assert r.returncode == 1, r.stdout
    finally:
        victim.unlink()


def test_home_gate_blocks_competing_ontology_registry():
    victim = ROOT / "substrate" / "organism" / "_tmp_test_comp_registry.py"
    victim.write_text("class OntologyRegistry:\n    pass\n")
    try:
        r = _run(
            "check_ontology_homes.py", "--file", "substrate/organism/_tmp_test_comp_registry.py"
        )
        assert r.returncode == 1, r.stdout
    finally:
        victim.unlink()


def test_home_gate_allows_ordinary_registry():
    victim = ROOT / "substrate" / "organism" / "_tmp_test_ok_registry.py"
    victim.write_text("class WidgetRegistry:\n    pass\n")
    try:
        r = _run("check_ontology_homes.py", "--file", "substrate/organism/_tmp_test_ok_registry.py")
        assert r.returncode == 0, r.stdout
    finally:
        victim.unlink()


def test_canonical_domain_registry_not_flagged():
    r = _run("check_ontology_homes.py", "--file", "substrate/organism/domain_registry.py")
    assert r.returncode == 0, r.stdout
