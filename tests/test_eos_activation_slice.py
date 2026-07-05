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
