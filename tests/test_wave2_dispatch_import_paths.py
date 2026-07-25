"""Wave 2 field-dispatch import-path invariant.

Regression pin for the deploy-candidate abort observed 2026-07-24:
``write_manifest`` did ``sys.path.insert(0, str(_ROOT))`` before
``from substrate.execution.attempts.evidence_finalization import ...``.
``_ROOT`` is ``/opt/OS`` — the LIVE main checkout, frozen at Wave 0, which does
NOT contain ``substrate/execution/attempts/`` (that slice exists only in the
candidate worktree). The import raised ``ModuleNotFoundError`` and aborted
``deploy-candidate`` at the very last step, after the container and serve were
already up.

The invariant: every ``substrate.execution.attempts.*`` import in the
dispatcher (Wave-2-only code) must be reached through a ``_WORKTREE`` sys.path
insertion, never ``_ROOT``. Pre-Wave-2 infra imports (e.g.
``substrate.sockets.mesh_dispatch_port``) exist in both trees and are exempt.

This is a source-level test — it parses the dispatcher, it does not execute it.
"""

from __future__ import annotations

import ast
from pathlib import Path

_DISPATCH = (
    Path(__file__).resolve().parent.parent / "scripts" / "wave2_field_dispatch.py"
)

# Modules that are Wave-2-only (exist solely in the candidate worktree, never in
# the stale /opt/OS main checkout). Imports of these MUST be preceded by a
# _WORKTREE sys.path insertion within the same function body.
_WAVE2_ONLY_PREFIX = "substrate.execution.attempts"


def _function_bodies(tree: ast.Module) -> list[ast.AST]:
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _syspath_root_var(node: ast.AST) -> str | None:
    """If ``node`` is ``sys.path.insert(0, str(<VAR>))`` return ``<VAR>`` name."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return None
    call = node.value
    func = call.func
    # match ...sys.path.insert
    if not (isinstance(func, ast.Attribute) and func.attr == "insert"):
        return None
    if not (
        isinstance(func.value, ast.Attribute)
        and func.value.attr == "path"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "sys"
    ):
        return None
    # second arg is str(<VAR>)
    if len(call.args) < 2:
        return None
    arg = call.args[1]
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "str":
        inner = arg.args[0] if arg.args else None
        if isinstance(inner, ast.Name):
            return inner.id
    return None


def _imports_wave2_only(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith(_WAVE2_ONLY_PREFIX)
    )


def test_dispatcher_exists() -> None:
    assert _DISPATCH.exists(), _DISPATCH


def test_wave2_only_imports_resolve_against_worktree_not_root() -> None:
    """Every attempts.* import must be gated by the LAST sys.path insert being _WORKTREE."""
    tree = ast.parse(_DISPATCH.read_text(encoding="utf-8"))
    offenders: list[str] = []
    checked = 0

    for fn in _function_bodies(tree):
        last_syspath_var: str | None = None
        for stmt in ast.walk(fn):
            var = _syspath_root_var(stmt)
            if var is not None:
                last_syspath_var = var
            if _imports_wave2_only(stmt):
                checked += 1
                if last_syspath_var != "_WORKTREE":
                    offenders.append(
                        f"{getattr(fn, 'name', '<anon>')}:{getattr(stmt, 'lineno', '?')} "
                        f"imports {stmt.module} but last sys.path insert was "  # type: ignore[attr-defined]
                        f"{last_syspath_var!r} (must be '_WORKTREE')"
                    )

    assert checked > 0, "expected at least one attempts.* import in the dispatcher"
    assert not offenders, "Wave-2-only imports resolving against stale root:\n" + "\n".join(offenders)
