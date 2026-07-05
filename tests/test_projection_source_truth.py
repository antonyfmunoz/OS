"""Projection Source-Truth Law — governance test (P4-PROJECTION-SOURCE-TRUTH).

Enforces docs/PROJECTION_SOURCE_TRUTH.md: declared/mirror truth is NOT source
truth. Every projection with a UMH shell must appear in the machine-readable
source-truth map, declare a Beast-verification status, and NEVER claim
source-currency while that status is UNVERIFIED.

The map is data/umh/projection_reconciliation/projection_source_truth.json,
established by a read-only Beast filesystem probe
(scripts/probe_beast_projection_source.sh).
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MAP = _ROOT / "data" / "umh" / "projection_reconciliation" / "projection_source_truth.json"
_PROJECTIONS_DIR = _ROOT / "projections"

_VALID_STATUS = {"VERIFIED", "UNVERIFIED", "UNREACHABLE", "NOT_APPLICABLE"}
_REQUIRED_TIERS = (
    "tier1_canonical_github",
    "tier2_beast_working_tree",
    "tier3_vps_mirror",
    "tier4_deploy_url",
)
# Projection shells that live under projections/ and MUST have a source-truth row.
_SHELL_PROJECTIONS = {"eos": "eos", "creatoros": "cos", "lyfeos": "lyfeos"}


def _load_map() -> dict:
    return json.loads(_MAP.read_text(encoding="utf-8"))


def _rows() -> dict[str, dict]:
    return {r["projection_id"]: r for r in _load_map()["projections"]}


def test_map_exists_and_is_valid_json():
    assert _MAP.exists(), f"source-truth map missing: {_MAP}"
    data = _load_map()
    assert data["projections"], "map has no projection rows"


def test_every_projection_shell_has_a_source_truth_row():
    """Every projections/<name>/ shell must be declared in the map — no undeclared
    shell may exist (that would be a projection whose source truth is unmodeled)."""
    rows = _rows()
    shells = {d.name for d in _PROJECTIONS_DIR.iterdir() if d.is_dir() and not d.name.startswith("_") and d.name != "__pycache__"}
    missing = []
    for shell in shells:
        pid = _SHELL_PROJECTIONS.get(shell)
        if pid is None:
            missing.append(f"projections/{shell}: no known projection_id mapping (add to map + _SHELL_PROJECTIONS)")
        elif pid not in rows:
            missing.append(f"projections/{shell} (id={pid}): absent from source-truth map")
    assert not missing, "Undeclared projection shell(s):\n  " + "\n  ".join(missing)


def test_every_row_declares_a_valid_beast_verification_status():
    for pid, row in _rows().items():
        status = row.get("beast_verification")
        assert status in _VALID_STATUS, f"{pid}: invalid beast_verification {status!r} (must be one of {_VALID_STATUS})"


def test_every_row_declares_all_four_tiers():
    for pid, row in _rows().items():
        for tier in _REQUIRED_TIERS:
            assert tier in row, f"{pid}: missing tier field {tier!r}"


def test_no_row_is_source_current_while_unverified():
    """THE CORE LAW: a projection may not be treated as source-current unless its
    Beast working tree was VERIFIED (or it has no Beast tree — NOT_APPLICABLE)."""
    offenders = []
    for pid, row in _rows().items():
        if row.get("source_current") is True and row.get("beast_verification") not in {"VERIFIED", "NOT_APPLICABLE"}:
            offenders.append(f"{pid}: source_current=True but beast_verification={row.get('beast_verification')!r}")
    assert not offenders, (
        "Projection(s) claim source-currency without Beast verification:\n  "
        + "\n  ".join(offenders)
        + "\n\nSee docs/PROJECTION_SOURCE_TRUTH.md — no row is source-current while UNVERIFIED."
    )


def test_verified_rows_carry_probe_evidence():
    """A VERIFIED status must be backed by recorded observation, not asserted."""
    for pid, row in _rows().items():
        if row.get("beast_verification") == "VERIFIED":
            assert row.get("beast_probe_at"), f"{pid}: VERIFIED but no beast_probe_at timestamp"
            obs = row.get("beast_observed") or {}
            for k in ("git_remote", "branch", "head", "dirty_count"):
                assert k in obs, f"{pid}: VERIFIED but beast_observed missing {k!r}"


def test_mirror_fidelity_does_not_overclaim():
    """data/repos mirror must declare its real fidelity; a schema-only snapshot may
    not be labeled a full mirror (the drift the probe exposed)."""
    valid = {"near_full_source_mirror", "schema_only_snapshot", "canonical", "absent"}
    for pid, row in _rows().items():
        fid = row.get("tier3_mirror_fidelity")
        assert fid in valid, f"{pid}: tier3_mirror_fidelity {fid!r} not in {valid}"


def test_beast_probe_contract_script_exists():
    """The verification must be reproducible, not a one-off."""
    script = _ROOT / "scripts" / "probe_beast_projection_source.sh"
    assert script.exists(), "Beast probe contract script missing"
    body = script.read_text(encoding="utf-8")
    assert "BatchMode=yes" in body, "probe must be non-interactive"
    # read-only guarantee: no write/push/build commands issued TO the Beast.
    # (Local evidence-file redirection like `> "$OUT"` is fine — that writes to the
    # VPS, not the Windows node. We forbid mutating git/build/delete verbs.)
    for forbidden in ("git push", "git commit", "git checkout", "git reset", "npm run build", "rmdir", "del /"):
        assert forbidden not in body, f"probe contract must be read-only wrt the Beast; found {forbidden!r}"
