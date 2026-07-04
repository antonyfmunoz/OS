"""WP-P3-004 — projection registration/port convergence tests.

Proves there is ONE canonical projection registration surface
(substrate/sockets/projection_port.py), that the legacy module-level functions
delegate to a single store (not a second registry), that the daemon registers
through the canonical port exactly once, that the UMH registry JSON seeds the
port (not competes with it), and that the organism state-broadcast port is a
distinct concern that is not confused with projection registration.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from substrate.sockets import projection_port as pp
from substrate.sockets.projection_port import (
    ProjectionPort,
    get_default_projection_port,
)

# ── one canonical registration surface ───────────────────────────────────────


def test_canonical_singleton_is_stable():
    a = get_default_projection_port()
    b = get_default_projection_port()
    assert a is b
    assert isinstance(a, ProjectionPort)


def test_canonical_types_point_to_sockets_port():
    from substrate.canonical_types import CANONICAL_TYPES

    for name in ("ProjectionPort", "ProjectionRegistration", "ProjectionPortProtocol"):
        assert CANONICAL_TYPES.get(name) == ["substrate.sockets.projection_port"]


# ── legacy functions delegate to a single store (not a second registry) ──────


def test_legacy_functions_share_one_store():
    pp._legacy_config_store.clear()
    pp.register_projection("p1", {"routes": ["/a"]})
    # every legacy accessor reads the SAME store
    assert pp.get_projection("p1") == {"routes": ["/a"]}
    assert "p1" in pp.list_projections()
    assert pp.unregister_projection("p1") is True
    assert pp.get_projection("p1") is None
    # there is no separate `_projections` name left behind
    assert not hasattr(pp, "_projections")


def test_legacy_preserves_freeform_config():
    pp._legacy_config_store.clear()
    pp.register_projection("free", {"anything": 1, "nested": {"x": 2}})
    assert pp.get_projection("free")["nested"]["x"] == 2


# ── UMH registry JSON seeds the port (does not compete) ──────────────────────


def test_seed_from_umh_registry_registers_into_the_port(tmp_path: Path):
    reg = {
        "umh": {"app_name": "umh-substrate", "health_url": "/api/health"},
        "eos": {"app_name": "eos-app", "public_url": "https://entrepreneuros.net"},
    }
    reg_path = tmp_path / "projection_registry.json"
    reg_path.write_text(json.dumps(reg))

    port = ProjectionPort(store_path=str(tmp_path / "regs.jsonl"))
    added = port.seed_from_umh_registry(str(reg_path))
    assert added == 2
    ids = {r.projection_id for r in port.list_registrations()}
    assert ids == {"umh", "eos"}
    # idempotent — re-seeding adds nothing (not a competing second registry)
    assert port.seed_from_umh_registry(str(reg_path)) == 0


def test_seed_missing_registry_is_noop(tmp_path: Path):
    port = ProjectionPort(store_path=str(tmp_path / "regs.jsonl"))
    assert port.seed_from_umh_registry(str(tmp_path / "nope.json")) == 0


# ── daemon registers through the canonical port exactly once ─────────────────


def test_daemon_registration_flows_through_the_port(tmp_path: Path):
    """_register_umh_projection uses port.register + port.seed_from_umh_registry,
    with no inline JSON walk (one registration path)."""
    import inspect

    from substrate.organism import daemon

    src = inspect.getsource(daemon.OrganismDaemon._register_umh_projection)
    # registers UMH via the port, seeds the rest via the port's own method
    assert "seed_from_umh_registry" in src
    # the old inline hand-rolled JSON walk is gone
    assert "for proj_id, cfg in entries.items()" not in src


# ── organism state-broadcast port is a DISTINCT concern ──────────────────────


def test_state_broadcast_port_is_not_the_registration_port():
    from substrate.organism.projection_port import (
        OrganismStatePort,
        ProjectionSubscriber,
    )
    from substrate.sockets.projection_port import ProjectionPort as RegPort

    # different classes, different modules
    assert OrganismStatePort is not RegPort
    assert OrganismStatePort.__module__ == "substrate.organism.projection_port"
    assert RegPort.__module__ == "substrate.sockets.projection_port"
    # the broadcast port registers a SUBSCRIBER (live sink), not a registration
    assert "subscriber" in str(inspect.signature(OrganismStatePort.register)).lower()
    # registration port registers a ProjectionRegistration (static declaration)
    assert "registration" in str(inspect.signature(RegPort.register)).lower()
    assert ProjectionSubscriber is not None


def test_state_broadcast_types_registered_distinctly():
    from substrate.canonical_types import CANONICAL_TYPES

    for name in ("OrganismStatePort", "ProjectionSubscriber", "StateSlice"):
        assert CANONICAL_TYPES.get(name) == ["substrate.organism.projection_port"]


# ── P3-001 ontology gate still blocks L3-in-L2 (regression guard) ────────────


def test_ontology_gate_still_active():
    import subprocess
    import sys

    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_ontology_layers.py"), "--all"],
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    assert result.returncode == 0, result.stdout


@pytest.fixture(autouse=True)
def _clean_legacy_store():
    pp._legacy_config_store.clear()
    yield
    pp._legacy_config_store.clear()
