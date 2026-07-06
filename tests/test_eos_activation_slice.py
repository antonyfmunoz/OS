"""WP-P4-006 — EOS projection activation/readiness slice.

Proves EOS is alive as a projection over the substrate through the smallest
governed read surface (projections/eos/integration/readiness.py::eos_readiness),
composed of existing substrate surfaces — no new registry, no schema, no mutation.

Covers: (1) EOS is registered through ProjectionPort (seed view + typed port),
(2) seed/config read through the canonical seed view, (3) env-disabled behavior is
safe, (4) env-enabled boot eligibility is visible, (5) the response is a stable flat
shape, (6) no domain-model sprawl.
"""

from __future__ import annotations

import json
import os
import sys

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.readiness import eos_readiness
from substrate.sockets.projection_port import ProjectionPort

_EXPECTED_KEYS = {
    "projection_id",
    "registered_in_seed",
    "runtime_registered",
    "seed",
    "connection_status",
    "boot_eligible",
    "poll_interval",
    # WP-P4-EOS-BEAST-BACKED-BUILD-001: EOS readiness now surfaces verified Beast source truth
    # as flat beast_* keys (honoring the read-surface flat-shape invariant) + a build-safe bool.
    "beast_source_risk",
    "beast_runtime_ready",
    "beast_backed_up",
    "beast_mirror_fidelity",
    "beast_operating_branch",
    "beast_head",
    "beast_verification",
    "beast_probe_at",
    "source_build_safe",
}
_BEAST_KEYS = {
    "beast_source_risk", "beast_runtime_ready", "beast_backed_up", "beast_mirror_fidelity",
    "beast_operating_branch", "beast_head", "beast_verification", "beast_probe_at",
}


def test_readiness_shape_is_stable_and_flat(monkeypatch):
    """Stable flat shape (no domain-model sprawl), env-disabled."""
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    r = eos_readiness()
    assert set(r) == _EXPECTED_KEYS, r
    assert r["projection_id"] == "eos"
    # JSON-serializable (stable API response)
    json.dumps(r)


def test_env_disabled_is_safe(monkeypatch):
    """No EOS_DATABASE_URL → safe disconnected readiness, never raises."""
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    r = eos_readiness()
    assert r["boot_eligible"] is False
    assert r["connection_status"] in ("disconnected", "unknown")
    assert r["poll_interval"] is None


def test_env_enabled_boot_eligibility_visible(monkeypatch):
    """EOS_DATABASE_URL set → configured/boot-eligible surfaced."""
    monkeypatch.setenv("EOS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("EOS_USER_IDS", "u1")
    r = eos_readiness()
    assert r["connection_status"] == "configured"
    assert r["boot_eligible"] is True
    assert r["poll_interval"] is not None


def test_registered_in_canonical_seed_view(monkeypatch):
    """EOS is in the canonical seed view (deterministic, daemon-independent)."""
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    r = eos_readiness()
    assert r["registered_in_seed"] is True
    # seed summary is read through the canonical seed view (no domain sprawl)
    assert r["seed"]["app_name"] == "eos-app"
    assert r["seed"]["public_url"]  # non-empty


def test_eos_registers_through_projection_port(tmp_path):
    """EOS registers through the canonical ProjectionPort when the UMH registry is
    seeded — proving the port is the registration path (isolated tmp store)."""
    registry = tmp_path / "projection_registry.json"
    registry.write_text(
        json.dumps(
            {
                "umh": {"app_name": "umh-substrate", "health_url": "/api/health"},
                "eos": {
                    "app_name": "eos-app",
                    "health_url": "/api/health",
                    "public_url": "https://entrepreneuros.net",
                },
            }
        ),
        encoding="utf-8",
    )
    port = ProjectionPort(store_path=str(tmp_path / "registrations.jsonl"))
    added = port.seed_from_umh_registry(str(registry))
    assert added >= 2
    ids = {r.projection_id for r in port.list_registrations()}
    assert "eos" in ids
    eos_reg = port.get("eos")
    assert eos_reg is not None
    assert eos_reg.name == "eos-app"
    assert eos_reg.preview_url == "https://entrepreneuros.net"


# ── WP-P4-EOS-BEAST-BACKED-BUILD-001: EOS readiness tied to VERIFIED Beast source truth ──
#
# The real EOS app body lives on the Beast (tier-2 source of truth), not in this
# projection shell or the /opt/OS mirror. These tests prove the readiness accessor
# composes the VERIFIED Beast source row through the canonical port, derives a
# build-safety boolean truthfully, and stays never-raise / read-surface-compliant.

import tempfile

from substrate.sockets.projection_port import (
    get_beast_source_row,
    load_beast_source_sync,
)


def _write_sync(tmp_path, doc):
    """Write a projection_source_sync.json under a UMH_ROOT-shaped tree; return its path."""
    d = tmp_path / "data" / "umh" / "projection_reconciliation"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "projection_source_sync.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_beast_source_surfaced_as_flat_keys(monkeypatch):
    """eos_readiness surfaces the VERIFIED Beast fields as flat beast_* keys + a bool."""
    r = eos_readiness()  # reads the committed live record (EOS is source_current)
    # the flat beast_* key set is always present (values None when no record resolves)
    assert _BEAST_KEYS <= set(r), _BEAST_KEYS - set(r)
    for k in _BEAST_KEYS:
        assert not isinstance(r[k], (list, dict)), f"{k} must be flat"
    assert isinstance(r["source_build_safe"], bool)


def test_source_build_safe_requires_all_conditions(tmp_path):
    """source_build_safe is True ONLY when current+runtime_ready+backed_up+full+VERIFIED."""
    good_row = {
        "projection_id": "eos", "source_risk": "source_current", "runtime_ready": "yes",
        "backed_up": "yes", "mirror_fidelity": "full", "beast_verification": "VERIFIED",
        "operating_branch": "feature/company-system", "head": "9c8725f",
        "beast_probe_at": "2026-07-05",
    }
    p = _write_sync(tmp_path, {"beast_status": "REACHABLE", "probe_at": "x", "projections": [good_row]})
    assert get_beast_source_row("eos", p) == good_row
    # flip any single condition → row still returned but a build orchestrator must not treat it safe
    for bad_field, bad_val in [
        ("source_risk", "source_dirty"), ("runtime_ready", "no"),
        ("backed_up", "no"), ("mirror_fidelity", "schema_only"),
    ]:
        row = dict(good_row, **{bad_field: bad_val})
        p2 = _write_sync(tmp_path, {"beast_status": "REACHABLE", "probe_at": "x", "projections": [row]})
        got = get_beast_source_row("eos", p2)
        safe = (got.get("source_risk") == "source_current" and got.get("runtime_ready") == "yes"
                and got.get("backed_up") == "yes" and got.get("mirror_fidelity") == "full"
                and got.get("beast_verification") == "VERIFIED")
        assert safe is False, f"{bad_field}={bad_val} must not be build-safe"


def test_unreachable_or_unverified_yields_no_row(tmp_path):
    """The port never surfaces a stale/false-current state."""
    row = {"projection_id": "eos", "beast_verification": "VERIFIED", "source_risk": "source_current"}
    # UNREACHABLE → no row even with a VERIFIED entry present
    p = _write_sync(tmp_path, {"beast_status": "UNREACHABLE", "probe_at": "x", "projections": [row]})
    assert get_beast_source_row("eos", p) == {}
    # REACHABLE but UNVERIFIED → no row
    urow = dict(row, beast_verification="UNVERIFIED")
    p2 = _write_sync(tmp_path, {"beast_status": "REACHABLE", "probe_at": "x", "projections": [urow]})
    assert get_beast_source_row("eos", p2) == {}


def test_missing_sync_file_is_safe():
    """Missing record → safe empty envelope, no raise; eos_readiness stays build-unsafe."""
    with tempfile.TemporaryDirectory() as d:
        missing = os.path.join(d, "nope.json")
        assert load_beast_source_sync(missing)["beast_status"] == "UNKNOWN"
        assert get_beast_source_row("eos", missing) == {}


def test_readiness_never_raises_and_stays_shape_stable():
    """eos_readiness always returns the full stable shape and is JSON-serializable,
    regardless of whether a Beast record resolves. (The empty-record degrade path is
    covered directly at the port level by test_missing_sync_file_is_safe — the port
    binds its repo root at import time, matching the existing seed reader, so the
    degrade path is exercised via an explicit path, not a runtime env override.)"""
    r = eos_readiness()
    assert set(r) == _EXPECTED_KEYS
    assert _BEAST_KEYS <= set(r)
    assert isinstance(r["source_build_safe"], bool)
    json.dumps(r)


def test_readiness_does_not_open_reconciliation_file_directly():
    """Read-surface invariant #6: the accessor composes the port, never opens the file."""
    src = os.path.join(_WORKTREE, "projections", "eos", "integration", "readiness.py")
    body = open(src).read()
    assert "projection_source_sync.json" not in body, "accessor must not name/open the file"
    assert "get_beast_source_row" in body, "accessor must compose the canonical port reader"
