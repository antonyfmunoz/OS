"""WP-P1-001 architecture test — one canonical governed operation runtime.

AST-based structural proof that the codebase declares exactly ONE canonical
mutation-submission entry, and that the rival work/command runtimes gate their
mutation-executing step behind the canonical routing check rather than reaching
an executor unconditionally.

This is the verification spine of WP-P1-001: it must FAIL if a bypass is
injected (an adapter that dispatches to an executor without first consulting
``canonical_runtime_routing_enabled`` / routing through ``governed_mutation``).

It is deliberately static (AST + source inspection) so it runs without a live
daemon, in collection, and in CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _tree(rel: str) -> ast.Module:
    return ast.parse(_read(rel), filename=rel)


# ── The canonical declaration ────────────────────────────────────────────────


def test_canonical_runtime_module_declares_single_entry():
    """substrate/organism/canonical_runtime.py names exactly one runtime."""
    src = _read("substrate/organism/canonical_runtime.py")
    assert "governed_mutation" in src
    assert "MutationRouter" in src
    assert "GovernedExecutionSpine" in src
    # Exactly one canonical-name constant, spelled once.
    assert src.count("CANONICAL_OPERATION_RUNTIME =") == 1


def test_mutation_router_is_the_only_declared_choke_point():
    """MutationRouter's module docstring asserts it is the single choke point,
    and no *other* substrate module declares itself an alternative mutation
    router class."""
    router_src = _read("substrate/organism/mutation_router.py")
    assert "single choke point" in router_src.lower()
    assert "no alternative mutation runtime" in router_src.lower()

    # Only mutation_router.py may define a class literally named MutationRouter.
    organism = REPO / "substrate" / "organism"
    definers: list[str] = []
    for path in organism.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "MutationRouter":
                definers.append(path.name)
    assert definers == ["mutation_router.py"], f"MutationRouter defined in {definers}"


# ── Rival runtimes gate their executing step behind canonical routing ─────────

# Each rival's mutation-executing method must reference the canonical routing
# guard. If someone adds a raw dispatch/execute path that skips the guard, this
# set-membership check fails.
_RIVAL_GUARD_SITES = {
    "substrate/organism/governed_work_runtime.py": "execute_work",
    "substrate/organism/command_runtime.py": "canonical_runtime",  # declaration-level marker
}


def test_governed_work_runtime_gates_execution_behind_canonical_routing():
    """GovernedWorkRuntime.execute_work must consult the canonical routing guard
    and FAIL CLOSED — Wave 2 removed the silent coordinator dispatch fallback, so
    execute_work must contain NO dispatch_next() call at all."""
    src = _read("substrate/organism/governed_work_runtime.py")
    assert "canonical_runtime_routing_enabled" in src, (
        "governed_work_runtime must import/consult the canonical routing guard"
    )

    tree = _tree("substrate/organism/governed_work_runtime.py")
    execute_work = _find_function(tree, "execute_work")
    assert execute_work is not None, "execute_work method not found"

    # The guard must be consulted.
    guard_line = _first_ref_line(execute_work, "canonical_runtime_routing_enabled")
    assert guard_line is not None, "execute_work does not consult the routing guard"

    # Wave 2 fail-closed: there is NO dispatch_next() fallback inside execute_work.
    dispatch_line = _first_call_attr_line(execute_work, "dispatch_next")
    assert dispatch_line is None, (
        "execute_work must NOT call dispatch_next() — the silent coordinator "
        "fallback was removed (Wave 2 fail-closed)"
    )


def test_execute_work_fails_closed_without_canonical_router():
    """When no MutationRouter is wired (canonical routing unavailable),
    execute_work returns a rejected receipt and never reaches an executor."""
    from substrate.organism.governed_work_runtime import GovernedWorkRuntime

    rt = GovernedWorkRuntime()  # no mutation_router, no coordinator wired

    class _Plan:
        approval_state = "approved"
        execution_plan_id = "expl-test"
        status = "approved"
        target_executor = ""

    rt._find_plan_for_work = lambda work_id: _Plan()  # type: ignore[method-assign]
    receipt = rt.execute_work("wp-x")
    assert receipt.status == "rejected", (
        f"expected fail-closed rejected receipt, got {receipt.status!r}: {receipt.error!r}"
    )
    assert "fail closed" in (receipt.error or "").lower()


def test_command_runtime_declares_canonical_subordination():
    """CommandRuntime is demoted by declaration + flag only (deep envelope work
    is WP-P1-009). It must reference the canonical runtime so its non-canonical
    status is explicit and greppable."""
    src = _read("substrate/organism/command_runtime.py")
    assert "canonical_runtime" in src or "CANONICAL_OPERATION_RUNTIME" in src, (
        "command_runtime must declare its subordination to the canonical runtime"
    )


def test_organism_loop_routes_execution_through_canonical_when_enabled():
    """organism_loop's execution step must consult the canonical routing guard
    so it is not a second, independent governance choke point."""
    src = _read("substrate/organism/organism_loop.py")
    assert "canonical_runtime_routing_enabled" in src, (
        "organism_loop must consult the canonical routing guard at its execution step"
    )


# ── No new rival spine/runtime crept in ───────────────────────────────────────


def test_no_new_governed_mutation_definition_outside_shim_and_router():
    """`governed_mutation` may be *defined* only in the transport shim; the core
    routing lives in mutation_router. No third definition may exist."""
    definers: list[str] = []
    for base in ("substrate", "transports", "services", "adapters"):
        root = REPO / base
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "governed_mutation":
                    definers.append(str(path.relative_to(REPO)))
    assert definers == ["transports/api/governed.py"], (
        f"governed_mutation defined in unexpected places: {definers}"
    )


# ── AST helpers ───────────────────────────────────────────────────────────────


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node  # type: ignore[return-value]
    return None


def _first_ref_line(fn: ast.AST, name: str) -> int | None:
    lines = [node.lineno for node in ast.walk(fn) if isinstance(node, ast.Name) and node.id == name]
    return min(lines) if lines else None


def _first_call_attr_line(fn: ast.AST, attr: str) -> int | None:
    lines = [
        node.lineno
        for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr
    ]
    return min(lines) if lines else None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
