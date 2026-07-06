"""P4S-10 — LifeOS + CreatorOS projection read-surface accessors.

Mirrors the shape-test pattern from tests/test_eos_activation_slice.py for the
second and third projections to ship a governed read surface
(rules/projection-read-surfaces.md, RT-PROJECTION-READ-SURFACE template).

Covers per projection: (1) stable flat JSON-serializable shape, (2) registered
in the canonical seed view, (3) env-disabled-safe (never raises, returns a
"disconnected" dict when the DB env var is unset).
"""

from __future__ import annotations

import json
import os
import sys

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.creatoros.integration.readiness import creatoros_readiness
from projections.lyfeos.integration.readiness import lyfeos_readiness

_EXPECTED_KEYS = {
    "projection_id",
    "registered_in_seed",
    "runtime_registered",
    "seed",
    "connection_status",
    "boot_eligible",
    "poll_interval",
}


# ── LyfeOS ─────────────────────────────────────────────────────────────────


def test_lyfeos_readiness_shape_is_stable_and_flat(monkeypatch):
    monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
    r = lyfeos_readiness()
    assert set(r) == _EXPECTED_KEYS, r
    assert r["projection_id"] == "lyfeos"
    json.dumps(r)  # JSON-serializable


def test_lyfeos_env_disabled_is_safe(monkeypatch):
    monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
    r = lyfeos_readiness()
    assert r["boot_eligible"] is False
    assert r["connection_status"] == "disconnected"
    assert r["poll_interval"] is None


def test_lyfeos_env_enabled_boot_eligibility_visible(monkeypatch):
    monkeypatch.setenv("LYFEOS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("LYFEOS_USER_IDS", "1")
    r = lyfeos_readiness()
    assert r["connection_status"] == "configured"
    assert r["boot_eligible"] is True
    assert r["poll_interval"] is not None
    monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
    monkeypatch.delenv("LYFEOS_USER_IDS", raising=False)


def test_lyfeos_registered_in_canonical_seed_view(monkeypatch):
    monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
    r = lyfeos_readiness()
    assert r["registered_in_seed"] is True
    assert r["seed"]["app_name"] == "lyfeos-app"
    assert r["seed"]["public_url"]


def test_lyfeos_readiness_never_raises_on_bad_env(monkeypatch):
    """Even a garbage poll-interval env value must not raise."""
    monkeypatch.setenv("LYFEOS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("LYFEOS_POLL_INTERVAL", "not-a-number")
    r = lyfeos_readiness()
    assert r["connection_status"] == "configured"
    json.dumps(r)
    monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
    monkeypatch.delenv("LYFEOS_POLL_INTERVAL", raising=False)


def test_lyfeos_readiness_does_not_open_registry_file_directly():
    """Read-surface invariant #6: the accessor composes the port, never opens
    the registry/reconciliation file directly."""
    src = os.path.join(
        _WORKTREE, "projections", "lyfeos", "integration", "readiness.py"
    )
    body = open(src).read()
    assert "open(" not in body and "Path(" not in body
    assert "load_umh_projection_seed" in body


# ── CreatorOS ──────────────────────────────────────────────────────────────


def test_creatoros_readiness_shape_is_stable_and_flat(monkeypatch):
    monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
    r = creatoros_readiness()
    assert set(r) == _EXPECTED_KEYS, r
    assert r["projection_id"] == "cos"
    json.dumps(r)  # JSON-serializable


def test_creatoros_env_disabled_is_safe(monkeypatch):
    monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
    r = creatoros_readiness()
    assert r["boot_eligible"] is False
    assert r["connection_status"] == "disconnected"
    assert r["poll_interval"] is None


def test_creatoros_env_enabled_boot_eligibility_visible(monkeypatch):
    monkeypatch.setenv("CREATOROS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("CREATOROS_USER_IDS", "1")
    r = creatoros_readiness()
    assert r["connection_status"] == "configured"
    assert r["boot_eligible"] is True
    assert r["poll_interval"] is not None
    monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
    monkeypatch.delenv("CREATOROS_USER_IDS", raising=False)


def test_creatoros_registered_in_canonical_seed_view(monkeypatch):
    monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
    r = creatoros_readiness()
    assert r["registered_in_seed"] is True
    assert r["seed"]["app_name"] == "creatoros-app"
    assert r["seed"]["public_url"]


def test_creatoros_readiness_never_raises_on_bad_env(monkeypatch):
    monkeypatch.setenv("CREATOROS_DATABASE_URL", "postgres://test")
    monkeypatch.setenv("CREATOROS_POLL_INTERVAL", "not-a-number")
    r = creatoros_readiness()
    assert r["connection_status"] == "configured"
    json.dumps(r)
    monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
    monkeypatch.delenv("CREATOROS_POLL_INTERVAL", raising=False)


def test_creatoros_readiness_does_not_open_registry_file_directly():
    src = os.path.join(
        _WORKTREE, "projections", "creatoros", "integration", "readiness.py"
    )
    body = open(src).read()
    assert "open(" not in body and "Path(" not in body
    assert "load_umh_projection_seed" in body
