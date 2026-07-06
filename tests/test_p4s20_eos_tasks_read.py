"""P4S-20 — EOS `/eos/tasks` read surface tests (governed-effect visibility).

Proves the packet's hard constraints:

1. Env-disabled (EOS_DATABASE_URL unset) → safe "disconnected" envelope, never raise.
2. DB failure → safe "unavailable" envelope, never raise, no secret leakage.
3. Connected path: flat, stable, JSON-serializable shape; readonly session.
4. The accessor (tasks_read.py) contains no INSERT/UPDATE/DELETE statement —
   source-level scan, not just behavioral.
5. The /eos/tasks route is a thin wrapper (conforms to
   .claude/rules/projection-read-surfaces.md) and passes the shared
   read-surface-discipline regression test.
6. A live task row (fake-conn) maps correctly, including governed-action linkage.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.tasks_read import eos_tasks

_ACCESSOR_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "tasks_read.py"
_TABLES_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "tables.py"
_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_core_eos_routes.py"

_ENVELOPE_KEYS = {
    "projection_id",
    "surface",
    "connected",
    "connection_status",
    "count",
    "tasks",
    "error",
}

_ROW_KEYS = {
    "id",
    "title",
    "status",
    "created_at",
    "action_id",
    "action_type",
    "action_status",
}


@dataclass(frozen=True)
class _FakeRow:
    id: str = "e455ff56-fc73-48fc-aa27-a91116e1c254"
    title: str = "Follow up with Demo Lead"
    status: str = "todo"
    created_at: datetime = datetime(2026, 7, 6, 12, 0, 0)
    action_id: str | None = "action_1"
    action_type: str | None = "create_task"
    action_status: str | None = "completed"


def _assert_safe_empty(result: dict, expected_status: str) -> None:
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["connected"] is False
    assert result["connection_status"] == expected_status
    assert result["count"] == 0
    assert result["tasks"] == []


# ── 1. Env-disabled / DB failure are safe, never raise ──────────────────────


def test_env_disabled_returns_safe_disconnected(monkeypatch):
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    result = eos_tasks()
    _assert_safe_empty(result, "disconnected")
    assert result["error"] is None


def test_db_failure_is_safe_not_raised(monkeypatch):
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://localhost:1/nonexistent_db_for_test")
    result = eos_tasks()
    _assert_safe_empty(result, "unavailable")
    # Stable error code only — a raw psycopg2 OperationalError can embed the
    # DSN (host/user/password), so the driver text must never reach the wire.
    assert result["error"] == "eos_database_unavailable"
    assert "nonexistent_db_for_test" not in json.dumps(result)


# ── 2. Connected path: shape, readonly session, governed-action linkage ─────


def _connected(monkeypatch, rows, limit=25):
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://ignored-by-fake")

    class _FakeConn:
        readonly_set = False

        def set_session(self, readonly=False):
            _FakeConn.readonly_set = readonly

        def close(self):
            pass

    import projections.eos.integration.tables as tables_mod

    fake_psycopg2 = type("_FakePg", (), {"connect": staticmethod(lambda dsn: _FakeConn())})
    monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)
    monkeypatch.setattr(
        tables_mod,
        "fetch_recent_tasks_with_action_link",
        lambda conn, limit=25: rows,
    )
    result = eos_tasks(limit=limit)
    return result, _FakeConn


def test_connected_shape_is_flat_and_stable(monkeypatch):
    result, _ = _connected(monkeypatch, [_FakeRow()])
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["connection_status"] == "connected"
    assert result["connected"] is True
    assert result["count"] == 1
    for k, v in result.items():
        if k == "tasks":
            assert isinstance(v, list)
            continue
        assert not isinstance(v, (list, dict)), f"envelope key {k} is not flat"
    row = result["tasks"][0]
    assert set(row.keys()) == _ROW_KEYS
    for k, v in row.items():
        assert not isinstance(v, (list, dict)), f"row key {k} is not flat"


def test_connected_session_is_readonly(monkeypatch):
    _, fake_conn = _connected(monkeypatch, [_FakeRow()])
    assert fake_conn.readonly_set is True, "DB session must be opened read-only"


def test_governed_action_linkage_surfaces_on_row(monkeypatch):
    """Proves the packet's core claim: a task row surfaces the agent_actions
    id/type/status that governed execution created it from."""
    result, _ = _connected(monkeypatch, [_FakeRow()])
    row = result["tasks"][0]
    assert row["id"] == "e455ff56-fc73-48fc-aa27-a91116e1c254"
    assert row["action_id"] == "action_1"
    assert row["action_type"] == "create_task"
    assert row["action_status"] == "completed"


def test_task_without_action_link_surfaces_none(monkeypatch):
    """Tasks created outside the governed executor still surface, with None
    action fields (LEFT JOIN, never filtered out)."""
    unlinked = _FakeRow(id="t2", action_id=None, action_type=None, action_status=None)
    result, _ = _connected(monkeypatch, [unlinked])
    row = result["tasks"][0]
    assert row["action_id"] is None
    assert row["action_type"] is None
    assert row["action_status"] is None


def test_limit_is_passed_through(monkeypatch):
    captured = {}

    def fake_fetch(conn, limit=25):
        captured["limit"] = limit
        return []

    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://ignored-by-fake")

    class _FakeConn:
        def set_session(self, readonly=False):
            pass

        def close(self):
            pass

    import projections.eos.integration.tables as tables_mod

    fake_psycopg2 = type("_FakePg", (), {"connect": staticmethod(lambda dsn: _FakeConn())})
    monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)
    monkeypatch.setattr(tables_mod, "fetch_recent_tasks_with_action_link", fake_fetch)

    eos_tasks(limit=7)
    assert captured["limit"] == 7


# ── 3. Source-level: no write verb anywhere in the accessor ─────────────────


def test_accessor_contains_no_write_sql():
    """The tasks_read.py accessor module must never contain an INSERT, UPDATE,
    or DELETE statement anywhere in its source — read-only by construction."""
    source = _ACCESSOR_PATH.read_text(encoding="utf-8")
    upper = source.upper()
    for verb in ("INSERT INTO", "UPDATE ", "DELETE FROM"):
        assert verb not in upper, f"tasks_read.py contains a write verb: {verb!r}"


def test_accessor_fetch_function_is_select_only():
    """The new tables.py fetch function used by this surface must be SELECT-only."""
    source = _TABLES_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "fetch_recent_tasks_with_action_link"
        ),
        None,
    )
    assert fn is not None, "fetch_recent_tasks_with_action_link not found in tables.py"
    fn_source = ast.get_source_segment(source, fn) or ""
    upper = fn_source.upper()
    assert "SELECT" in upper
    for verb in ("INSERT INTO", "UPDATE ", "DELETE FROM"):
        assert verb not in upper, (
            f"fetch_recent_tasks_with_action_link contains write verb: {verb!r}"
        )


def test_accessor_imports_only_downward():
    """tasks_read.py (projection layer) imports only substrate/projections/stdlib
    — downward, never transports."""
    tree = ast.parse(_ACCESSOR_PATH.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
        elif isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
    offenders = [m for m in mods if m.split(".")[0] == "transports"]
    assert not offenders, f"tasks_read.py imports transports: {offenders}"


# ── 4. Route-level: thin wrapper, present, and the shared discipline test ───


def _route_handler(route_path: str):
    tree = ast.parse(_ROUTES_PATH.read_text(encoding="utf-8"))
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
                        and dec.args[0].value == route_path
                    ):
                        return fn
    return None


def test_route_is_registered_and_thin_wrapper():
    fn = _route_handler("/eos/tasks")
    assert fn is not None, "/eos/tasks route not found in register_eos_routes"
    imports_projection = any(
        isinstance(n, ast.ImportFrom) and (n.module or "").startswith("projections.eos")
        for n in ast.walk(fn)
    )
    assert imports_projection, "/eos/tasks must import a projection accessor"
    has_try = any(isinstance(n, ast.Try) for n in fn.body)
    assert has_try, "/eos/tasks must wrap in try/except (never 500)"
    ctors = [
        (n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None))
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
    ]
    ctors = [c for c in ctors if c and c[0].isupper()]
    assert not ctors, f"/eos/tasks constructs domain model(s) inline: {ctors}"


def test_read_surface_discipline_suite_passes_with_new_route():
    """Runs the shared cross-route discipline test module in-process — the new
    /eos/tasks route must conform (it is NOT added to the legacy allowlist)."""
    import importlib

    mod = importlib.import_module("tests.test_projection_read_surface_discipline")
    importlib.reload(mod)
    mod.test_new_eos_routes_conform_to_read_surface_discipline()
    mod.test_reference_activation_route_is_the_conforming_pattern()
    mod.test_legacy_allowlist_is_shrink_only_and_matches_reality()
