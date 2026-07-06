"""WP-P4-EOS-APP-MODULE-MAP-001 — EOS app-body module map regression tests.

Proves the source-to-substrate module map honors the packet's hard constraints:

1. No row is build-mappable unless source_build_safe=True (fail-closed gate).
2. The map records Beast source provenance (repo/branch/head/probe/VERIFIED).
3. The map contains no secret values (env key NAMES only).
4. The map does not treat data/repos as source authority.
5. No CreatorOS/LyfeOS modules are included.
"""

from __future__ import annotations

import json
import os
import re
import sys

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.module_map import (
    build_mappable_modules,
    load_eos_app_module_map,
)

_MAP_PATH = os.path.join(
    _WORKTREE, "data", "umh", "projection_reconciliation", "eos_app_module_map.json"
)


def _raw_map() -> dict:
    with open(_MAP_PATH, "r") as f:
        return json.load(f)


# ── 1. Build-mappability is gated on source_build_safe ─────────────────────


def test_no_rows_mappable_when_source_not_build_safe(monkeypatch):
    """If eos_readiness reports source_build_safe=False, the mappable set is []."""

    def fake_readiness():
        return {"source_build_safe": False, "beast_head": "9c8725f"}

    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(readiness_mod, "eos_readiness", fake_readiness)
    assert build_mappable_modules(_MAP_PATH) == []


def test_no_rows_mappable_when_head_drifts(monkeypatch):
    """A map recorded at an older Beast head than live truth is not mappable."""
    import projections.eos.integration.readiness as readiness_mod

    def fake_readiness():
        return {"source_build_safe": True, "beast_head": "deadbeef"}

    monkeypatch.setattr(readiness_mod, "eos_readiness", fake_readiness)
    assert build_mappable_modules(_MAP_PATH) == []


def test_no_rows_mappable_when_readiness_unavailable(monkeypatch):
    """If the readiness accessor raises, the gate fails closed."""
    import projections.eos.integration.readiness as readiness_mod

    def broken_readiness():
        raise RuntimeError("readiness unavailable")

    monkeypatch.setattr(readiness_mod, "eos_readiness", broken_readiness)
    assert build_mappable_modules(_MAP_PATH) == []


def test_rows_mappable_only_under_full_safety(monkeypatch):
    """With live source_build_safe=True and matching head, rows flow — each
    carrying Beast provenance and the safety flag."""
    import projections.eos.integration.readiness as readiness_mod

    doc = _raw_map()
    live_head = doc["provenance"]["head"]

    def fake_readiness():
        return {"source_build_safe": True, "beast_head": live_head}

    monkeypatch.setattr(readiness_mod, "eos_readiness", fake_readiness)
    rows = build_mappable_modules(_MAP_PATH)
    assert rows, "expected mappable rows under full build safety"
    for row in rows:
        assert row["source_build_safe"] is True
        assert row["provenance"]["head"] == live_head
        assert row["provenance"]["beast_verification"] == "VERIFIED"


def test_missing_map_yields_empty_envelope(tmp_path):
    doc = load_eos_app_module_map(str(tmp_path / "nonexistent.json"))
    assert doc["modules"] == []
    assert build_mappable_modules(str(tmp_path / "nonexistent.json")) == []


# ── 2. Beast provenance is recorded ─────────────────────────────────────────


def test_map_records_beast_provenance():
    doc = _raw_map()
    prov = doc["provenance"]
    assert prov["source_authority"] == "beast"
    assert prov["beast_repo"] == "EntrepreneurOS"
    assert prov["operating_branch"]
    assert re.fullmatch(r"[0-9a-f]{7,40}", prov["head"])
    assert prov["beast_probe_at"]
    assert prov["beast_verification"] == "VERIFIED"
    assert prov["source_risk"] == "source_current"


# ── 3. No secret values ──────────────────────────────────────────────────────


def test_map_contains_no_secret_values():
    """Env entries are key NAMES only; no credential material anywhere."""
    raw_text = open(_MAP_PATH, "r").read()

    secret_patterns = [
        r"sk-ant-[A-Za-z0-9_-]{10,}",  # Anthropic keys
        r"sk-[A-Za-z0-9]{40,}",  # OpenAI-style keys
        r"AKIA[0-9A-Z]{16}",  # AWS access keys
        r"AIza[0-9A-Za-z_-]{30,}",  # Google API keys
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"postgres(?:ql)?://[^\s\"]+:[^\s\"]+@",  # DSN with embedded password
        r"xox[baprs]-[A-Za-z0-9-]{10,}",  # Slack tokens
        r"ghp_[A-Za-z0-9]{20,}",  # GitHub PATs
    ]
    for pattern in secret_patterns:
        assert not re.search(pattern, raw_text), f"secret-like value matches {pattern}"

    doc = _raw_map()
    env = doc["env_keys_referenced"]
    for section in ("server", "client_vite"):
        for key in env[section]:
            # A key NAME: uppercase identifier, no separators that carry values.
            assert re.fullmatch(r"[A-Z][A-Z0-9_]*", key), f"not a bare key name: {key!r}"
            assert "=" not in key and ":" not in key


# ── 4. data/repos is not source authority ───────────────────────────────────


def test_mirror_is_not_source_authority():
    doc = _raw_map()
    mirror = doc["provenance"]["inspection_mirror"]
    assert mirror["path"] == "data/repos/entrepreneuros"
    assert mirror["is_source_authority"] is False
    # No module names the mirror as its beast_path — paths are Beast-repo-relative.
    for module in doc["modules"]:
        assert not module["beast_path"].startswith("data/repos"), (
            f"module {module['module']} treats the mirror as source"
        )


# ── 5. EOS only — no CreatorOS/LyfeOS ────────────────────────────────────────


def test_map_is_eos_only():
    doc = _raw_map()
    assert doc["projection_id"] == "eos"
    # The only sanctioned mentions of the excluded projections are in the
    # excluded_projections block itself.
    assert set(doc["excluded_projections"].keys()) == {"cos", "lyfeos"}
    module_text = json.dumps(doc["modules"]).lower()
    for name in ("creatoros", "lyfeos"):
        assert name not in module_text, f"{name} leaked into module rows"


def test_gate_rejects_non_eos_map(tmp_path, monkeypatch):
    """A map claiming a different projection is never mappable."""
    doc = _raw_map()
    doc["projection_id"] = "cos"
    alien = tmp_path / "alien_map.json"
    alien.write_text(json.dumps(doc))

    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": True, "beast_head": doc["provenance"]["head"]},
    )
    assert build_mappable_modules(str(alien)) == []


# ── Shape sanity ─────────────────────────────────────────────────────────────


def test_every_module_row_is_complete():
    doc = _raw_map()
    required = {
        "module",
        "beast_path",
        "kind",
        "what_it_is",
        "substrate_mapping",
        "target_layer",
        "copy_policy",
        "mutation_requires_owner_approval",
    }
    assert doc["modules"], "map has no modules"
    for module in doc["modules"]:
        missing = required - set(module)
        assert not missing, f"module {module.get('module')} missing {missing}"
        assert module["copy_policy"] in {
            "do_not_copy",
            "already_mirrored_no_further_copy",
        }, f"unsanctioned copy policy on {module['module']}"
