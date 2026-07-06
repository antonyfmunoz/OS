"""WP-P4-EOS-ACTION-EXECUTOR-SEAM-001 — action-executor seam map regression tests.

Proves the packet's hard constraints:

1. No Beast source is copied (no TS files in projections/, no TS code markers
   in the map or accessor).
2. source_build_safe=True is required for any seam to be actionable.
3. The map contains no secret values.
4. Every mapped seam names a sanctioned UMH primitive and a substrate target owner.
5. No CreatorOS/LyfeOS files are included.
6. No schema change occurred (no DDL, no DB clients in the accessor).
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.action_seam import (
    UMH_SEAM_PRIMITIVES,
    load_eos_action_seam_map,
    mappable_seams,
)

_MAP_PATH = os.path.join(
    _WORKTREE,
    "data",
    "umh",
    "projection_reconciliation",
    "eos_action_executor_seam_map.json",
)
_ACCESSOR_PATH = os.path.join(_WORKTREE, "projections", "eos", "integration", "action_seam.py")


def _raw_map() -> dict:
    with open(_MAP_PATH, "r") as f:
        return json.load(f)


# ── 1. No Beast source copied ────────────────────────────────────────────────


def test_no_typescript_files_in_projections():
    """The projection shell holds no copied app-body files."""
    for pattern in ("**/*.ts", "**/*.tsx"):
        hits = glob.glob(os.path.join(_WORKTREE, "projections", pattern), recursive=True)
        assert hits == [], f"TypeScript files found in projections/: {hits}"


def test_map_and_accessor_contain_no_copied_code():
    """The seam map and accessor carry semantics, not Beast source."""
    ts_markers = [
        "async function",
        "await db.",
        "drizzle-orm",
        "pgTable(",
        "export const",
        "=> {",
        "req.isAuthenticated",
    ]
    for path in (_MAP_PATH, _ACCESSOR_PATH):
        text = open(path, "r").read()
        for marker in ts_markers:
            assert marker not in text, f"copied-code marker {marker!r} in {os.path.basename(path)}"
    assert _raw_map()["code_copied_from_beast"] is False


# ── 2. source_build_safe is required ─────────────────────────────────────────


def test_no_seams_when_source_not_build_safe(monkeypatch):
    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": False, "beast_head": "9c8725f"},
    )
    assert mappable_seams(_MAP_PATH) == []


def test_no_seams_when_head_drifts(monkeypatch):
    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": True, "beast_head": "deadbeef"},
    )
    assert mappable_seams(_MAP_PATH) == []


def test_no_seams_when_readiness_unavailable(monkeypatch):
    import projections.eos.integration.readiness as readiness_mod

    def broken():
        raise RuntimeError("readiness unavailable")

    monkeypatch.setattr(readiness_mod, "eos_readiness", broken)
    assert mappable_seams(_MAP_PATH) == []


def test_seams_flow_under_full_safety(monkeypatch):
    import projections.eos.integration.readiness as readiness_mod

    doc = _raw_map()
    live_head = doc["provenance"]["head"]
    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": True, "beast_head": live_head},
    )
    rows = mappable_seams(_MAP_PATH)
    assert len(rows) == len(doc["seams"]), "all authored seams should be well-formed"
    for row in rows:
        assert row["source_build_safe"] is True
        assert row["provenance"]["head"] == live_head
        assert row["provenance"]["beast_verification"] == "VERIFIED"


def test_missing_map_yields_empty(tmp_path):
    doc = load_eos_action_seam_map(str(tmp_path / "missing.json"))
    assert doc["seams"] == []
    assert mappable_seams(str(tmp_path / "missing.json")) == []


# ── 3. No secret values ──────────────────────────────────────────────────────


def test_map_contains_no_secret_values():
    raw_text = open(_MAP_PATH, "r").read()
    secret_patterns = [
        r"sk-ant-[A-Za-z0-9_-]{10,}",
        r"sk-[A-Za-z0-9]{40,}",
        r"AKIA[0-9A-Z]{16}",
        r"AIza[0-9A-Za-z_-]{30,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"postgres(?:ql)?://[^\s\"]+:[^\s\"]+@",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"ya29\.[A-Za-z0-9_-]{20,}",
    ]
    for pattern in secret_patterns:
        assert not re.search(pattern, raw_text), f"secret-like value matches {pattern}"


# ── 4. Every seam has a sanctioned primitive + substrate target owner ────────


def test_every_seam_is_complete_and_owned():
    doc = _raw_map()
    required = {
        "seam",
        "beast_source",
        "semantic_responsibility",
        "umh_primitive",
        "target_owner",
        "universal_or_eos_specific",
        "owner_approval_required",
    }
    assert doc["seams"], "seam map has no seams"
    for seam in doc["seams"]:
        missing = required - set(seam)
        assert not missing, f"seam {seam.get('seam')} missing {missing}"
        assert seam["umh_primitive"] in UMH_SEAM_PRIMITIVES, (
            f"seam {seam['seam']} maps to unsanctioned primitive {seam['umh_primitive']!r}"
        )
        assert str(seam["target_owner"]).strip(), f"seam {seam['seam']} has no target owner"
        assert isinstance(seam["owner_approval_required"], bool)


def test_gate_drops_malformed_seams(tmp_path, monkeypatch):
    """A seam with an unsanctioned primitive or empty owner never flows."""
    doc = _raw_map()
    doc["seams"] = [
        {**doc["seams"][0], "umh_primitive": "MagicRuntime"},
        {**doc["seams"][1], "target_owner": "  "},
    ]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))

    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": True, "beast_head": doc["provenance"]["head"]},
    )
    assert mappable_seams(str(bad)) == []


# ── 5. EOS only ──────────────────────────────────────────────────────────────


def test_map_is_eos_only():
    doc = _raw_map()
    assert doc["projection_id"] == "eos"
    assert set(doc["excluded_projections"].keys()) == {"cos", "lyfeos"}
    seam_text = json.dumps(doc["seams"]).lower()
    for name in ("creatoros", "lyfeos"):
        assert name not in seam_text, f"{name} leaked into seam rows"


def test_gate_rejects_non_eos_map(tmp_path, monkeypatch):
    doc = _raw_map()
    doc["projection_id"] = "cos"
    alien = tmp_path / "alien.json"
    alien.write_text(json.dumps(doc))

    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": True, "beast_head": doc["provenance"]["head"]},
    )
    assert mappable_seams(str(alien)) == []


# ── 6. No schema change occurred ─────────────────────────────────────────────


def test_no_schema_change():
    doc = _raw_map()
    assert doc["schema_changes"] == "none"
    raw_text = open(_MAP_PATH, "r").read()
    for ddl in ("CREATE TABLE", "ALTER TABLE", "DROP TABLE", "drizzle-kit push"):
        assert ddl not in raw_text, f"DDL marker {ddl!r} in seam map"


def test_accessor_touches_no_database():
    """The accessor is a pure file-read surface — no DB clients, no writes."""
    text = open(_ACCESSOR_PATH, "r").read()
    for forbidden in (
        "psycopg2",
        "sqlalchemy",
        "drizzle",
        "postgres",
        "neon",
        "INSERT ",
        "UPDATE ",
    ):
        assert forbidden not in text, f"accessor references {forbidden!r}"
    # File writes are also out: the accessor only opens the map read-only.
    assert '"w"' not in text and "'w'" not in text


# ── Provenance ───────────────────────────────────────────────────────────────


def test_map_records_beast_provenance():
    prov = _raw_map()["provenance"]
    assert prov["source_authority"] == "beast"
    assert prov["beast_repo"] == "EntrepreneurOS"
    assert re.fullmatch(r"[0-9a-f]{7,40}", prov["head"])
    assert prov["beast_verification"] == "VERIFIED"
    assert prov["inspection_mirror"]["is_source_authority"] is False
    assert prov["files_read"], "provenance must list the Beast files that were read"
