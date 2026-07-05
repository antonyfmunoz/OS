"""Projection read-surface discipline — P4-SURFACE-DISCIPLINE.

Locks the read-surface pattern established by the EOS activation slice (PR #171)
so the NEXT projection read surface cannot drift into cockpit sprawl, substrate
leakage, or duplicate readiness models.

Governed by .claude/rules/projection-read-surfaces.md. EOS-scoped: EOS is the only
projection with a real governed read surface today. The convention generalizes to
all projections only when a second projection ships one.

Reference conforming route: GET /eos/activation → projections.eos.integration
.readiness.eos_readiness(). Truthful baseline: only /eos/activation conforms; the
five pre-existing /eos/* routes are sanctioned legacy, held in a SHRINK-ONLY
allowlist below. New /eos/* routes must conform (are NOT added to the allowlist).
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

_EOS_ROUTES_FILE = _WORKTREE / "transports" / "api" / "cockpit_core_eos_routes.py"
_READINESS_FILE = _WORKTREE / "projections" / "eos" / "integration" / "readiness.py"

# SHRINK-ONLY: the five /eos/* routes that predate the discipline. They construct
# domain models inline. This list may only ever get SHORTER — when a legacy route
# is refactored to the discipline it is removed. A NEW route must NOT be added.
_SANCTIONED_LEGACY_ROUTES = frozenset(
    {
        "/eos/pipeline",
        "/eos/kpis",
        "/eos/activity",
        "/eos/accountability",
        "/eos/intelligence",
    }
)


def _route_handlers(routes_file: Path):
    """Yield (route_path, FunctionDef) for each @router.get inside register_eos_routes."""
    tree = ast.parse(routes_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_eos_routes":
            for fn in node.body:
                if not isinstance(fn, ast.FunctionDef):
                    continue
                for dec in fn.decorator_list:
                    if (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "get"
                        and dec.args
                        and isinstance(dec.args[0], ast.Constant)
                    ):
                        yield dec.args[0].value, fn


def _imports_projection(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(n, ast.ImportFrom) and (n.module or "").startswith("projections.eos")
        for n in ast.walk(fn)
    )


def _constructs_domain_model(fn: ast.FunctionDef) -> list[str]:
    """Calls to Capitalized names (View/Engine/Runtime/etc.) — inline domain construction."""
    hits: list[str] = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name and name[0].isupper():
                hits.append(name)
    return hits


def _has_try_except(fn: ast.FunctionDef) -> bool:
    return any(isinstance(n, ast.Try) for n in fn.body)


def _imported_modules(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        elif isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
    return mods


# --- route-level discipline -------------------------------------------------


def test_new_eos_routes_conform_to_read_surface_discipline():
    """Every /eos/* route not in the shrink-only legacy allowlist must be a thin
    wrapper: imports a projection accessor and constructs NO domain model inline."""
    offenders: list[str] = []
    seen = set()
    for route, fn in _route_handlers(_EOS_ROUTES_FILE):
        seen.add(route)
        if route in _SANCTIONED_LEGACY_ROUTES:
            continue
        ctors = _constructs_domain_model(fn)
        if not _imports_projection(fn):
            offenders.append(f"{route}: no projection accessor import")
        if ctors:
            offenders.append(f"{route}: constructs domain model(s) inline {ctors}")
        if not _has_try_except(fn):
            offenders.append(f"{route}: no try/except (read surface must not 500)")
    assert not offenders, (
        "Non-conforming projection read surface(s):\n  "
        + "\n  ".join(offenders)
        + "\n\nSee .claude/rules/projection-read-surfaces.md. New /eos/* routes must be a "
        "thin wrapper over a projection-owned accessor. Do NOT add them to the legacy allowlist."
    )
    # the reference route must be present and conforming
    assert "/eos/activation" in seen, "reference route /eos/activation missing"


def test_reference_activation_route_is_the_conforming_pattern():
    """/eos/activation is the reference: projection import, no inline construction, try/except."""
    for route, fn in _route_handlers(_EOS_ROUTES_FILE):
        if route == "/eos/activation":
            assert _imports_projection(fn), "/eos/activation must import a projection accessor"
            assert not _constructs_domain_model(fn), "/eos/activation must not construct domain models inline"
            assert _has_try_except(fn), "/eos/activation must wrap in try/except"
            return
    raise AssertionError("/eos/activation route not found")


def test_legacy_allowlist_is_shrink_only_and_matches_reality():
    """The allowlist must not contain phantom routes and must not silently absorb
    the reference route. Guards against the list drifting to hide new violations."""
    routes = {r for r, _ in _route_handlers(_EOS_ROUTES_FILE)}
    phantom = _SANCTIONED_LEGACY_ROUTES - routes
    assert not phantom, f"legacy allowlist names non-existent routes (remove them): {phantom}"
    assert "/eos/activation" not in _SANCTIONED_LEGACY_ROUTES, (
        "the reference route must never be in the legacy allowlist"
    )


# --- accessor-level discipline ----------------------------------------------


def test_readiness_accessor_does_not_import_transports():
    """A read-surface accessor stays substrate-composed: it must not import transports/."""
    offenders = [m for m in _imported_modules(_READINESS_FILE) if m.split(".")[0] == "transports"]
    assert not offenders, f"projections/eos/integration/readiness.py imports transports: {offenders}"


def test_readiness_accessor_imports_only_downward():
    """readiness.py (projection layer) imports only substrate/projections/stdlib — downward."""
    allowed_roots = {"substrate", "projections", "__future__", "typing"}
    offenders = [
        m for m in _imported_modules(_READINESS_FILE)
        if m.split(".")[0] not in allowed_roots
    ]
    assert not offenders, f"readiness.py imports non-downward modules: {offenders}"


def test_readiness_returns_stable_flat_json_serializable_shape(monkeypatch):
    """Env-disabled accessor returns a stable flat, JSON-serializable dict."""
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    from projections.eos.integration.readiness import eos_readiness

    r = eos_readiness()
    json.dumps(r)  # JSON-serializable
    # flat: no nested container beyond the single small "seed" summary dict
    for k, v in r.items():
        if k == "seed":
            assert isinstance(v, dict)
            continue
        assert not isinstance(v, (list, dict)), f"key {k} is not flat: {type(v)}"
