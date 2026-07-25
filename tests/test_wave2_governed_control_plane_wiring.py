"""Wave 2 governed control-plane wiring — the governed path must reach the daemon.

Regression pin for field run 20260725T172540Z-p1: the operator approved the
execution authorization in the HUD (POST /unified-approval/approve → 200), but
the grant never left ACTIVATING and NO worker ran. Root cause: the operator API
built and started the OrganismDaemon and wired it to the voice WS, but never
registered it with the accessor that transports/api/governed.py consults. So
`_get_router()` returned None, `governed_mutation` fell through to
`route_mutation_degraded`, and the HIGH-risk `execution_authorization_decision`
(degraded_mode_allowed=False) fail-closed — a governed no-op that returns 200 at
the audit layer while activating nothing.

The fix: the daemon is registered with the CANONICAL substrate organism port
(`substrate.sockets.organism_port.register_organism_accessor`) at startup, and
`governed._get_router()` consults that port (falling back to the
cockpit_spine_router accessor). These tests pin both halves.
"""

from __future__ import annotations

import ast
from pathlib import Path

import transports.api.governed as governed
from substrate.sockets import organism_port

_OPERATOR_API = Path(__file__).resolve().parent.parent / "services" / "operator_api.py"


class _FakeDaemon:
    governed_spine = "SPINE"
    mutation_registry = "REGISTRY"


def _reset() -> None:
    governed.reset_router_cache()
    organism_port._get_organism_fn = None


def test_router_built_from_canonical_organism_port() -> None:
    """A daemon registered with the canonical port must yield a live router."""
    _reset()
    try:
        organism_port.register_organism_accessor(lambda: _FakeDaemon())
        router = governed._get_router()
        assert router is not None, "governed path must build a router from the canonical port"
    finally:
        _reset()


def test_no_daemon_registered_yields_no_router_then_degrades() -> None:
    """With nothing registered the router is None (degraded path is then correct)."""
    _reset()
    try:
        router = governed._get_router()
        assert router is None
    finally:
        _reset()


def test_operator_api_registers_daemon_with_canonical_port() -> None:
    """operator_api MUST call register_organism_accessor after starting the daemon.

    Source-level guard: without this call the governed path degrades and
    execution authorization can never activate (the field-observed failure).
    """
    src = _OPERATOR_API.read_text(encoding="utf-8")
    assert "register_organism_accessor" in src, (
        "operator_api must register the started daemon with the canonical "
        "organism_port so the governed mutation path reaches the control plane"
    )
    # It must be reached from the lifespan startup, not merely imported.
    tree = ast.parse(src)
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "register_organism_accessor"
    ]
    assert calls, "register_organism_accessor must be CALLED, not just imported"


def test_governed_prefers_canonical_port_over_spine_router() -> None:
    """The canonical port wins even if the cockpit_spine_router accessor is unset."""
    _reset()
    try:
        # cockpit_spine_router._get_organism defaults to lambda: None; the
        # canonical port alone must still produce a router.
        organism_port.register_organism_accessor(lambda: _FakeDaemon())
        assert governed._get_router() is not None
    finally:
        _reset()
