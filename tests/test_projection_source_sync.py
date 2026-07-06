"""WP-P4-BEAST-SOURCE-SYNC-001 — guards for the Beast projection source-readiness harness.

The harness (scripts/probe_beast_source_readiness.sh) turns the ad-hoc Beast probe into a
repeatable governed source-sync/readiness record. These tests enforce that the recorded
classification cannot lie: a dirty/unpushed repo cannot read source_current, a repo without
the op-run protocol cannot read runtime_ready, a schema-only mirror cannot read full, an
unreachable probe yields no current rows, and no secret values appear in the record.

Reads JSON/source as data — no imports, no network, no Beast access.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SYNC = REPO / "data" / "umh" / "projection_reconciliation" / "projection_source_sync.json"
DOC = REPO / "docs" / "PROJECTION_BEAST_SOURCE_SYNC.md"
PROBE = REPO / "scripts" / "probe_beast_source_readiness.sh"

EXPECTED_PROJECTIONS = {"eos", "cos", "lyfeos"}
VALID_RISK = {"source_current", "source_dirty", "source_unpushed", "source_at_risk"}

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk_live_[0-9a-zA-Z]{16,}"),
    re.compile(r"sk_test_[0-9a-zA-Z]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"(?:postgres|postgresql|mongodb(?:\+srv)?|mysql|redis)://[^:@/\s]+:[^@\s]{6,}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def _sync() -> dict:
    return json.loads(SYNC.read_text())


def _projections() -> list[dict]:
    return _sync()["projections"]


def test_sync_record_present_and_parses():
    assert SYNC.exists(), "projection_source_sync.json must exist"
    d = _sync()
    assert d["beast_status"] in {"REACHABLE", "UNREACHABLE"}


def test_all_projections_probed():
    if _sync()["beast_status"] != "REACHABLE":
        return  # unreachable record legitimately has no rows
    ids = {p["projection_id"] for p in _projections()}
    assert ids == EXPECTED_PROJECTIONS, f"expected {EXPECTED_PROJECTIONS}, got {ids}"


def test_risk_class_is_valid_and_present():
    for p in _projections():
        assert p["source_risk"] in VALID_RISK, f"{p['projection_id']}: {p['source_risk']}"


def test_dirty_or_unpushed_repo_is_never_source_current():
    """The core guardrail: a repo with local-only work must not read source_current."""
    for p in _projections():
        if p["source_risk"] == "source_current":
            assert p["dirty_count"] == 0, f"{p['projection_id']} source_current but dirty"
            assert p["unpushed_commits"] == 0, f"{p['projection_id']} source_current but unpushed"
            assert p["backed_up"] == "yes", f"{p['projection_id']} source_current but not backed up"


def test_repo_without_op_protocol_is_never_runtime_ready():
    for p in _projections():
        if p["runtime_ready"] == "yes":
            assert p["env_op_tpl_present"] == "yes", p["projection_id"]
            assert p["env_gitignored"] == "yes", p["projection_id"]
            assert p["plaintext_env"] == "retired", p["projection_id"]


def test_mirror_without_app_body_is_never_full():
    for p in _projections():
        if p["mirror_fidelity"] == "full":
            # a full mirror claim must correspond to an app body on the source
            assert p["app_body_present"] == "yes", f"{p['projection_id']} full mirror w/o app body"


def test_unreachable_probe_yields_no_current_rows():
    d = _sync()
    if d["beast_status"] != "REACHABLE":
        assert d["projections"] == [], "unreachable probe must not carry projection rows"


def test_every_row_is_beast_verified_when_reachable():
    if _sync()["beast_status"] != "REACHABLE":
        return
    for p in _projections():
        assert p["beast_verification"] == "VERIFIED", p["projection_id"]


def test_unpushed_without_backup_is_at_risk_not_current_or_unpushed():
    """Fail-toward-risk: unpushed + no backup must escalate to source_at_risk."""
    for p in _projections():
        if p["unpushed_commits"] and p["backed_up"] == "no":
            assert p["source_risk"] == "source_at_risk", p["projection_id"]


def test_no_secret_values_in_sync_record():
    text = SYNC.read_text()
    for pat in SECRET_VALUE_PATTERNS:
        hits = pat.findall(text)
        assert not hits, f"secret-value pattern {pat.pattern} in sync record: {hits}"


def test_no_secret_values_in_handoff_doc():
    text = DOC.read_text()
    for pat in SECRET_VALUE_PATTERNS:
        hits = pat.findall(text)
        assert not hits, f"secret-value pattern {pat.pattern} in handoff doc: {hits}"


def test_probe_is_read_only_no_beast_writes():
    """The harness must not mutate the Beast — no write git verbs over ssh_beast."""
    body = PROBE.read_text()
    # forbid mutating git operations inside the probe
    for verb in ["git add", "git commit", "git push", "git reset", "git clean",
                 "git checkout", "git stash", "git rm", "Remove-Item", "del "]:
        assert verb not in body, f"probe must be read-only; found '{verb}'"
    # reachability gate + no false-current on unreachable
    assert "UNREACHABLE" in body
    assert "@{upstream}" in body, "probe must record ahead/behind"
