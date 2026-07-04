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
    """The home set may only shrink. This count freezes today's membership (27).
    A NEW home must be a deliberate edit here AND to the gate ledger."""
    assert len(FROZEN_ONTOLOGY_HOMES) <= 27, (
        f"FROZEN_ONTOLOGY_HOMES grew to {len(FROZEN_ONTOLOGY_HOMES)}; new homes must be "
        "reviewed, not silently added"
    )


def test_frozen_competitors_are_shrink_only_with_metadata():
    assert len(FROZEN_ONTOLOGY_COMPETITORS) <= 3, (
        f"FROZEN_ONTOLOGY_COMPETITORS grew to {len(FROZEN_ONTOLOGY_COMPETITORS)}; new leaks "
        "must be fixed, not frozen"
    )
    for rel, (disposition, sunset) in FROZEN_ONTOLOGY_COMPETITORS.items():
        assert (ROOT / rel).exists(), f"frozen competitor missing: {rel}"
        assert disposition and sunset, f"{rel} missing disposition/sunset metadata"


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
