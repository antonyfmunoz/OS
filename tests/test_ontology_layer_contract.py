"""WP-P3-001 — ontology/metamodel layer contract tests.

Proves the L1/L2/L3/L4 boundary is enforced: the L2 metamodel surface
(substrate/types.py, substrate/ontology/) must not contain L3 projection domain
objects, must not import L3 state/projection modules, and the frozen
contamination ledger may only shrink.

Mirrors the grep-boundary pattern of tests/test_sprint2_boundary.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GATE = _REPO_ROOT / "scripts" / "check_ontology_layers.py"
_ONTOLOGY_DIR = _REPO_ROOT / "substrate" / "ontology"


def _run_gate(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE), *extra],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )


# ── L2 ontology must not import L3 (grep-boundary, like test_sprint2_boundary) ──


def _ontology_py_files() -> list[Path]:
    return [p for p in _ONTOLOGY_DIR.rglob("*.py") if "__pycache__" not in str(p)]


def test_ontology_does_not_import_business_state():
    bad = []
    pat = re.compile(r"^\s*(?:from|import)\s+substrate\.state\.business\b", re.M)
    for f in _ontology_py_files():
        if pat.search(f.read_text(encoding="utf-8", errors="replace")):
            bad.append(str(f.relative_to(_REPO_ROOT)))
    assert not bad, f"substrate/ontology/ (L2) imports L3 BIS state: {bad}"


def test_ontology_does_not_import_projections():
    bad = []
    pat = re.compile(r"^\s*(?:from|import)\s+projections\b", re.M)
    for f in _ontology_py_files():
        if pat.search(f.read_text(encoding="utf-8", errors="replace")):
            bad.append(str(f.relative_to(_REPO_ROOT)))
    assert not bad, f"substrate/ontology/ (L2) imports projections/ (L3): {bad}"


# ── the gate itself ──────────────────────────────────────────────────────────


def test_gate_passes_on_real_tree():
    """--all is green: only frozen legacy leaks remain."""
    result = _run_gate("--all")
    assert result.returncode == 0, f"gate red on real tree:\n{result.stdout}"


def test_gate_supports_file_mode():
    result = _run_gate("--file", "substrate/types.py")
    # types.py is now CLEAN (not grandfathered) — the L3 fields stage_name/
    # north_star were evicted to BusinessInstance in WP-P4-002, so the file
    # passes on its own merit with no ledger exemption.
    assert result.returncode == 0, result.stdout


def test_company_l2_model_has_no_l3_fields():
    """WP-P4-002: Company is an abstract L2 org primitive — it must carry NO L3
    EOS vocabulary. stage_name/north_star live on BusinessInstance (L3)."""
    from substrate.types import Company

    fields = set(Company.model_fields)
    leaked = fields & {"stage_name", "north_star", "monthly_revenue", "icp_description", "offer_name"}
    assert not leaked, f"Company (L2) leaked L3 field(s): {leaked} — relocate to BusinessInstance/projections"


def test_gate_blocks_reintroduced_company_l3_field(tmp_path: Path):
    """The field-level guard actively blocks re-adding stage_name/north_star to an
    L2 class now that the substrate/types.py grandfather is removed (WP-P4-002)."""
    bad = _ONTOLOGY_DIR / "_test_readded_company_field.py"
    bad.write_text(
        "class Company:\n    id: str\n    name: str\n    stage_name: str\n    north_star: str\n",
        encoding="utf-8",
    )
    try:
        result = _run_gate("--file", "substrate/ontology/_test_readded_company_field.py")
        assert result.returncode == 1, "gate must block re-added stage_name/north_star on an L2 class"
        assert "l3_field" in result.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_injected_l3_field_class_fails(tmp_path: Path):
    """A NEW L2 class with L3 vocabulary must fail the gate."""
    bad = _ONTOLOGY_DIR / "_test_injected_l3.py"
    bad.write_text(
        "class InjectedDomain:\n"
        "    id: str\n"
        "    monthly_revenue: float\n"
        "    icp_description: str\n",
        encoding="utf-8",
    )
    try:
        result = _run_gate("--file", "substrate/ontology/_test_injected_l3.py")
        assert result.returncode == 1, "gate must block injected L3 field class"
        assert "l3_field" in result.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_injected_ontology_import_fails():
    bad = _ONTOLOGY_DIR / "_test_injected_import.py"
    bad.write_text("from substrate.state.business import business_instance\n", encoding="utf-8")
    try:
        result = _run_gate("--file", "substrate/ontology/_test_injected_import.py")
        assert result.returncode == 1, "gate must block ontology→BIS import"
        assert "ontology_imports_bis" in result.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_injected_instance_literal_fails():
    bad = _ONTOLOGY_DIR / "_test_injected_literal.py"
    bad.write_text('QUERIES = ["scan lyfe_institute"]\n', encoding="utf-8")
    try:
        result = _run_gate("--file", "substrate/ontology/_test_injected_literal.py")
        assert result.returncode == 1, "gate must block instance literal in L2"
        assert "instance_literal" in result.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_false_positive_control():
    """A clean universal L2 class must NOT trip the gate."""
    ok = _ONTOLOGY_DIR / "_test_clean.py"
    ok.write_text(
        "class UniversalPrimitive:\n    id: str\n    name: str\n    created_at: str\n",
        encoding="utf-8",
    )
    try:
        result = _run_gate("--file", "substrate/ontology/_test_clean.py")
        assert result.returncode == 0, f"clean class wrongly blocked:\n{result.stdout}"
    finally:
        ok.unlink(missing_ok=True)


# ── shrink-only ledgers (non-growth caps) ────────────────────────────────────

# Baselines frozen at WP-P3-001 (main bb39b3abd). These may only SHRINK.
# Ontology ledger shrank 1→0 at WP-P4-002 (Company.stage_name/north_star evicted
# to L3 BusinessInstance; substrate/types.py grandfather removed).
_ONTOLOGY_LEDGER_BASELINE = 0  # files in LEGACY_ONTOLOGY_LEAKS
_INSTANCE_VENTURE_SLUG_BASELINE = 19  # files grandfathered for venture_slug


def test_ontology_ledger_shrink_only():
    from check_ontology_layers import LEGACY_ONTOLOGY_LEAKS

    n = sum(1 for cats in LEGACY_ONTOLOGY_LEAKS.values() if cats)
    assert n <= _ONTOLOGY_LEDGER_BASELINE, (
        f"LEGACY_ONTOLOGY_LEAKS grew to {n} (baseline {_ONTOLOGY_LEDGER_BASELINE}); "
        "the ledger may only shrink — do not add new frozen leaks"
    )


def test_instance_venture_slug_ledger_shrink_only():
    from check_instance_leak import LEGACY_INSTANCE_LEAKS

    n = sum(1 for cats in LEGACY_INSTANCE_LEAKS.values() if "venture_slug" in cats)
    assert n <= _INSTANCE_VENTURE_SLUG_BASELINE, (
        f"venture_slug legacy leaks grew to {n} "
        f"(baseline {_INSTANCE_VENTURE_SLUG_BASELINE}); ledger may only shrink"
    )


@pytest.fixture(autouse=True)
def _ensure_scripts_importable():
    """scripts/ is not a package; make its modules importable for the ledger tests."""
    scripts_dir = str(_REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    yield
