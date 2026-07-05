"""Projection drift reconciliation — WP-P4-SOURCE-RECONCILIATION-001.

Enforces the three-way (Beast ↔ GitHub ↔ /opt/OS mirror) drift classification in
data/umh/projection_reconciliation/projection_drift_reconciliation.json against the
Projection Source-Truth Law (docs/PROJECTION_SOURCE_TRUTH.md, PR #173).

Non-mutating: asserts on the recorded reconciliation report only. Proves the law
holds — no projection may be called source-current while its Beast tree is
dirty/unpushed and unreconciled, and no mirror may claim full fidelity without the
app body (client/server/build).
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_REPORT = _ROOT / "data" / "umh" / "projection_reconciliation" / "projection_drift_reconciliation.json"


def _rows() -> dict[str, dict]:
    data = json.loads(_REPORT.read_text(encoding="utf-8"))
    return {r["projection_id"]: r for r in data["projections"]}


def test_report_exists_and_covers_the_three_projections():
    assert _REPORT.exists(), f"reconciliation report missing: {_REPORT}"
    rows = _rows()
    assert {"eos", "cos", "lyfeos"} <= set(rows), f"missing projections: {rows.keys()}"


def test_no_projection_is_source_current_when_beast_dirty_or_unpushed():
    """THE CORE LAW: a dirty or unpushed (or behind) Beast tree cannot be source_current."""
    offenders = []
    for pid, r in _rows().items():
        b = r["beast"]
        unreconciled = b.get("dirty_count", 0) > 0 or b.get("ahead", 0) > 0 or b.get("behind", 0) > 0
        if unreconciled and r.get("source_current") is True:
            offenders.append(f"{pid}: source_current=True but beast dirty={b.get('dirty_count')} ahead={b.get('ahead')} behind={b.get('behind')}")
        if unreconciled and "source_current" in r.get("classification", []):
            offenders.append(f"{pid}: classification includes source_current but beast is unreconciled")
    assert not offenders, "Source-current claimed on an unreconciled Beast tree:\n  " + "\n  ".join(offenders)


def test_mirror_cannot_claim_full_fidelity_without_app_body():
    """A mirror missing client/server/build may not be classified mirror_full."""
    offenders = []
    for pid, r in _rows().items():
        m = r["mirror"]
        has_body = m.get("client") and m.get("server") and m.get("build")
        if m.get("fidelity") == "mirror_full" and not has_body:
            offenders.append(f"{pid}: mirror_full but client={m.get('client')} server={m.get('server')} build={m.get('build')}")
        if not has_body and "mirror_full" in r.get("classification", []):
            offenders.append(f"{pid}: classification mirror_full without app body")
    assert not offenders, "Mirror overclaims fidelity without app body:\n  " + "\n  ".join(offenders)


def test_lyfeos_is_beast_only_dirty_and_unpushed_not_dormant():
    r = _rows()["lyfeos"]
    assert r["beast"]["dirty_count"] >= 1, "LyfeOS Beast must be dirty"
    assert r["beast"]["ahead"] >= 1, "LyfeOS Beast must be ahead of GitHub (unpushed)"
    assert "source_unpushed" in r["classification"]
    assert "source_dirty" in r["classification"]
    assert r["github"].get("beast_head_pushed") is False, "LyfeOS Beast head must be unpushed"
    assert r["dormant_claim_refuted"] is True, "LyfeOS must be classified NOT dormant"
    assert r["source_current"] is False


def test_creatoros_is_active_dirty_not_dormant():
    r = _rows()["cos"]
    assert r["beast"]["dirty_count"] >= 1, "CreatorOS Beast must have uncommitted work"
    assert "source_dirty" in r["classification"]
    assert r["dormant_claim_refuted"] is True, "CreatorOS must be classified NOT dormant"
    assert r["source_current"] is False


def test_entrepreneuros_is_clean_but_branch_diverged_from_default_main():
    r = _rows()["eos"]
    assert r["beast"]["dirty_count"] == 0, "EOS Beast must be clean"
    assert "branch_diverged" in r["classification"], "EOS must be branch-diverged"
    # branch-diverged means Beast branch != GitHub default branch
    assert r["beast"]["branch"] != r["github"]["default_branch"], "EOS must be on a non-default branch"
    assert r["beast"]["head"] != r["github"]["default_head"], "EOS head must differ from GitHub default head"
    # clean + pushed on its feature branch => source_current is allowed HERE
    assert r["source_current"] is True
    assert r["github"]["beast_head_pushed"] is True


def test_schema_only_mirrors_are_flagged_not_treated_as_app_body():
    """CreatorOS and LyfeOS mirrors are schema-only and must be labeled so."""
    for pid in ("cos", "lyfeos"):
        m = _rows()[pid]["mirror"]
        assert m["fidelity"] == "mirror_schema_only", f"{pid} mirror must be mirror_schema_only"
        assert not m["client"] and not m["server"], f"{pid} mirror must lack client/server"


def test_report_is_non_mutating_and_declares_method():
    """The report must document its read-only three-way method (no Beast writes)."""
    data = json.loads(_REPORT.read_text(encoding="utf-8"))
    method = data.get("_method", "")
    assert "NON-MUTATING" in method, "report must declare non-mutating method"
    assert "No Beast writes" in method or "no Beast writes" in method.lower()
    assert "no code copied" in method.lower()
