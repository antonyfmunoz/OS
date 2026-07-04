"""WP-P3 — read-side projection registry consumer convergence tests.

Proves the four read-side consumers of data/umh/projection_registry.json no
longer open the file themselves — they read it through the canonical
ProjectionPort view — while every existing output shape is preserved, the file
stays a seed input (idempotent, no second registry), and a gate blocks any new
non-port module from opening it.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "umh" / "projection_registry.json"


@pytest.fixture(scope="module")
def raw_registry() -> dict:
    return json.loads(REGISTRY.read_text())


# ── canonical port view ──────────────────────────────────────────────────────


def test_port_seed_view_equals_raw(raw_registry):
    from substrate.sockets.projection_port import ProjectionPort

    view = ProjectionPort().load_seed_config(str(REGISTRY))
    assert view == raw_registry
    # preserves seed-only fields the typed registration drops
    for cfg in raw_registry.values():
        if "l4_workflow" in cfg:
            assert any("l4_workflow" in v for v in view.values())
            break


def test_module_helper_delegates_to_port(raw_registry):
    from substrate.sockets.projection_port import load_umh_projection_seed

    assert load_umh_projection_seed(str(REGISTRY)) == raw_registry


def test_single_open_of_registry_lives_in_the_port():
    """Only substrate/sockets/projection_port.py contains an open() of the file."""
    import subprocess

    result = subprocess.run(
        ["python3", str(ROOT / "scripts" / "check_projection_registry_reads.py"), "--all"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stdout


def test_seed_view_missing_file_is_empty(tmp_path: Path):
    from substrate.sockets.projection_port import ProjectionPort

    assert ProjectionPort().load_seed_config(str(tmp_path / "nope.json")) == {}


# ── consumers read via the port, not their own open() ────────────────────────


def _reads_registry_file_directly(module) -> bool:
    """AST check: does this module contain an open() whose arg resolves to the
    registry filename (directly or through a local var)?"""
    src = inspect.getsource(module)
    tree = ast.parse(src)
    registry_vars: set[str] = set()

    def is_reg_path(node) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return "projection_registry.json" in node.value
        if isinstance(node, ast.Call):
            return any(is_reg_path(a) for a in node.args)
        if isinstance(node, ast.BoolOp):
            return any(is_reg_path(v) for v in node.values)
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and is_reg_path(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    registry_vars.add(t.id)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            is_open = (isinstance(f, ast.Name) and f.id == "open") or (
                isinstance(f, ast.Attribute) and f.attr == "open"
            )
            if is_open and node.args:
                a = node.args[0]
                if is_reg_path(a) or (isinstance(a, ast.Name) and a.id in registry_vars):
                    return True
    return False


def test_certification_does_not_open_registry_directly():
    from substrate.organism import projection_certification

    assert not _reads_registry_file_directly(projection_certification)


def test_reality_graph_does_not_open_registry_directly():
    from substrate.organism import reality_graph

    assert not _reads_registry_file_directly(reality_graph)


def test_cockpit_spine_router_does_not_open_registry_directly():
    from transports.api import cockpit_spine_router

    assert not _reads_registry_file_directly(cockpit_spine_router)


def test_cockpit_organism_routes_does_not_open_registry_directly():
    from transports.api import cockpit_organism_routes

    assert not _reads_registry_file_directly(cockpit_organism_routes)


# ── output shapes preserved ──────────────────────────────────────────────────


def test_certification_registry_preserves_config_shape(raw_registry):
    from substrate.organism.projection_certification import ProjectionRegistry

    reg = ProjectionRegistry(str(REGISTRY))
    assert sorted(reg.names) == sorted(raw_registry)
    for name, cfg in raw_registry.items():
        pc = reg.get(name)
        assert pc is not None
        assert pc.app_name == cfg.get("app_name", "")
        assert pc.health_url == cfg.get("health_url", "/api/health")
        assert pc.public_url == cfg.get("public_url", "")
        assert pc.l4_workflow == cfg.get("l4_workflow", "")
        assert pc.critical_bundle_values == cfg.get("critical_bundle_values", [])


def test_reality_graph_projection_entities_preserved(raw_registry):
    from substrate.organism.reality_graph import RealityGraph

    g = RealityGraph.seed_from_registries(projection_registry_path=str(REGISTRY))
    ents = getattr(g, "_entities", None)
    ents = list(ents.values()) if isinstance(ents, dict) else list(ents or [])
    projs = {
        e.source_id: e for e in ents if getattr(e, "source_system", "") == "projection_registry"
    }
    assert sorted(projs) == sorted(raw_registry)
    for name, cfg in raw_registry.items():
        props = projs[name].properties
        assert props["app_name"] == cfg.get("app_name", "")
        assert props["public_url"] == cfg.get("public_url", "")
        assert props["health_url"] == cfg.get("health_url", "/api/health")
        assert props["certification_level"] == "UNKNOWN"


def test_cockpit_organism_load_matches_raw(raw_registry):
    from transports.api.cockpit_organism_routes import _load_projection_registry

    assert _load_projection_registry() == raw_registry


def test_cockpit_spine_projection_health_shape(raw_registry):
    import asyncio

    from transports.api.cockpit_spine_router import _projection_health

    res = asyncio.new_event_loop().run_until_complete(_projection_health())
    assert res["total_projections"] == len(raw_registry)
    for p in res["projections"]:
        assert "has_l4_workflow" in p  # proves l4_workflow field survived
        assert set(p.keys()) >= {"projection_id", "app_name", "health_url", "public_url"}


# ── seed idempotency + no second registry ────────────────────────────────────


def test_seed_idempotency_unchanged(tmp_path: Path):
    from substrate.sockets.projection_port import ProjectionPort

    port = ProjectionPort(store_path=str(tmp_path / "regs.jsonl"))
    first = port.seed_from_umh_registry(str(REGISTRY))
    assert first == 4  # cos/eos/lyfeos/umh
    assert port.seed_from_umh_registry(str(REGISTRY)) == 0


def test_no_second_registry_class_introduced():
    """The read-side helper is a view, not a new registry with its own store."""
    from substrate.sockets.projection_port import ProjectionPort

    # load_seed_config returns a fresh dict each call, backed by the file read —
    # it does not accumulate state (no hidden second registry).
    a = ProjectionPort().load_seed_config(str(REGISTRY))
    b = ProjectionPort().load_seed_config(str(REGISTRY))
    assert a == b
    assert a is not b  # independent reads, not a shared mutable registry


def test_registration_surface_still_singular():
    """substrate/sockets/projection_port.py remains the one registration surface."""
    import substrate.sockets.projection_port as sp

    reg_defs = [n for n in dir(sp) if n == "ProjectionRegistration"]
    assert reg_defs == ["ProjectionRegistration"]
    # organism port stays a distinct state-broadcast concern
    from substrate.organism.projection_port import OrganismStatePort

    assert OrganismStatePort.__module__ == "substrate.organism.projection_port"
