"""WP-P4-EOS-ACTION-PROPOSAL-READ-001 — EOS ActionProposal read seam tests.

Proves the packet's hard constraints:

1. source_build_safe is required; env-disabled/unavailable states return safe
   disconnected output (never raise).
2. The /eos/action-proposals route is a thin wrapper over the accessor.
3. The response shape is flat and stable.
4. execute_enabled: False on the envelope (the read surface never executes);
   per-row it represents the #185 executor contract — True only for approved +
   allowlisted non-provider action types.
5. No mutation/write is possible (readonly session, SELECT-only SQL, no write
   verbs in the accessor).
6. No Beast code is copied.
7. No secret values appear.
8. Only EOS is touched.
9. The #182 seam map is the mapping source.
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

from projections.eos.integration.action_proposals import eos_action_proposals

_ACCESSOR_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "action_proposals.py"
_TABLES_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "tables.py"
_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_core_eos_routes.py"

_ENVELOPE_KEYS = {
    "projection_id",
    "surface",
    "connection_status",
    "source_build_safe",
    "execute_enabled",
    "executor_scope",
    "allowed_action_types",
    "retry_policy",
    "beast_head",
    "seam_id",
    "seam_primitive",
    "seam_target",
    "proposal_count",
    "proposals",
    "error",
}

_ROW_KEYS = {
    "proposal_id",
    "agent_id",
    "agent_name",
    "user_id",
    "action_type",
    "target_domain",
    "requested_operation",
    "summary",
    "status",
    "approval_state",
    "requires_approval",
    "priority",
    "retry_count",
    "max_retries",
    "created_at",
    "updated_at",
    "source",
    "beast_head",
    "umh_primitive",
    "execute_enabled",
}


@dataclass(frozen=True)
class _FakeRow:
    id: str = "action_1"
    agent_id: str = "agent_1"
    agent_name: str = "Test Agent"
    user_id: str = "user_1"
    action_type: str = "send_email"
    action_name: str = "Send Email"
    description: str = "Send follow-up"
    status: str = "pending"
    requires_approval: bool = True
    priority: str = "medium"
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = datetime(2026, 7, 6, 12, 0, 0)
    updated_at: datetime = datetime(2026, 7, 6, 12, 0, 0)


_SEAM_MAP_PATH = os.path.join(
    _WORKTREE,
    "data",
    "umh",
    "projection_reconciliation",
    "eos_action_executor_seam_map.json",
)


def _safe_readiness(monkeypatch, safe: bool = True, head: str = "9c8725f") -> None:
    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": safe, "beast_head": head},
    )
    # Pin the seam map to this worktree's copy so tests are self-contained
    # regardless of the main checkout's sync state.
    import projections.eos.integration.action_seam as seam_mod

    monkeypatch.setattr(seam_mod, "_SEAM_MAP_PATH", _SEAM_MAP_PATH)


def _assert_safe_empty(result: dict, expected_status: str) -> None:
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["connection_status"] == expected_status
    assert result["execute_enabled"] is False
    assert result["proposal_count"] == 0
    assert result["proposals"] == []


# ── 1. Gates: build safety + env-disabled + unavailable are safe ─────────────


def test_env_disabled_returns_safe_disconnected(monkeypatch):
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    _safe_readiness(monkeypatch, safe=True)
    result = eos_action_proposals()
    _assert_safe_empty(result, "disconnected")
    assert result["source_build_safe"] is True


def test_not_build_safe_returns_zero_rows(monkeypatch):
    _safe_readiness(monkeypatch, safe=False)
    result = eos_action_proposals()
    _assert_safe_empty(result, "source_not_build_safe")
    assert result["source_build_safe"] is False


def test_readiness_unavailable_is_safe(monkeypatch):
    import projections.eos.integration.readiness as readiness_mod

    def broken():
        raise RuntimeError("readiness down")

    monkeypatch.setattr(readiness_mod, "eos_readiness", broken)
    result = eos_action_proposals()
    _assert_safe_empty(result, "readiness_unavailable")


def test_missing_seam_map_returns_zero_rows(monkeypatch, tmp_path):
    _safe_readiness(monkeypatch, safe=True)
    import projections.eos.integration.action_seam as seam_mod

    monkeypatch.setattr(
        seam_mod,
        "load_eos_action_seam_map",
        lambda map_path="": {"seams": []},
    )
    result = eos_action_proposals()
    _assert_safe_empty(result, "seam_map_unavailable")


def test_db_failure_is_safe_not_raised(monkeypatch):
    _safe_readiness(monkeypatch, safe=True)
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://localhost:1/nonexistent_db_for_test")
    result = eos_action_proposals()
    _assert_safe_empty(result, "unavailable")
    # Stable error code only — a raw psycopg2 OperationalError can embed the
    # DSN (host/user/password), so the driver text must never reach the wire.
    assert result["error"] == "eos_database_unavailable"
    assert "nonexistent_db_for_test" not in json.dumps(result)


# ── 2+3+4+9. Connected path: shape, mapping, execute_enabled, seam source ────


def _connected(monkeypatch, rows):
    _safe_readiness(monkeypatch, safe=True)
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
        "fetch_pending_agent_actions",
        lambda conn, user_ids=None, limit=50, statuses=("pending",): rows,
    )
    result = eos_action_proposals()
    return result, _FakeConn


def test_connected_shape_is_flat_and_stable(monkeypatch):
    result, fake_conn = _connected(monkeypatch, [_FakeRow()])
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["connection_status"] == "connected"
    assert result["proposal_count"] == 1
    # flat: every envelope value is a scalar except the single proposals list
    for k, v in result.items():
        if k == "proposals":
            assert isinstance(v, list)
            continue
        assert not isinstance(v, (list, dict)), f"envelope key {k} is not flat"
    row = result["proposals"][0]
    assert set(row.keys()) == _ROW_KEYS
    for k, v in row.items():
        assert not isinstance(v, (list, dict)), f"row key {k} is not flat"


def test_connected_session_is_readonly(monkeypatch):
    _, fake_conn = _connected(monkeypatch, [_FakeRow()])
    assert fake_conn.readonly_set is True, "DB session must be opened read-only"


def test_envelope_execute_enabled_stays_false(monkeypatch):
    """The read surface itself never executes anything."""
    result, _ = _connected(monkeypatch, [_FakeRow()])
    assert result["execute_enabled"] is False


def test_row_execute_enabled_mirrors_185_executor_contract(monkeypatch):
    """Per-row execute_enabled: approved + allowlisted non-provider only."""
    rows = [
        _FakeRow(id="p1", status="pending", action_type="create_task"),
        _FakeRow(id="p2", status="approved", action_type="create_task"),
        _FakeRow(id="p3", status="approved", action_type="create_document"),
        _FakeRow(id="p4", status="approved", action_type="send_email"),
        _FakeRow(id="p5", status="rejected", action_type="create_task"),
        _FakeRow(id="p6", status="completed", action_type="create_task"),
        _FakeRow(id="p7", status="failed", action_type="create_document"),
    ]
    result, _ = _connected(monkeypatch, rows)
    flags = {r["proposal_id"]: r["execute_enabled"] for r in result["proposals"]}
    assert flags == {
        "p1": False,  # pending — needs approval first
        "p2": True,  # approved + allowlisted
        "p3": True,  # approved + allowlisted
        "p4": False,  # provider-coupled — blocked by #185 allowlist
        "p5": False,  # rejected — never executable
        "p6": False,  # already executed — never again
        "p7": False,  # terminal failure — human re-approval path only
    }
    assert result["allowed_action_types"] == "create_document,create_task"
    assert result["executor_scope"] == "non_provider_allowlist"


def test_lifecycle_statuses_reach_the_real_sql(monkeypatch):
    """Reachability, not just expression logic: through the REAL
    fetch_pending_agent_actions, the accessor's SELECT must ask the database
    for approved (and terminal) rows — otherwise per-row execute_enabled could
    never be True on the wire and the execute surface would be dead code."""
    _safe_readiness(monkeypatch, safe=True)
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://ignored-by-fake")

    captured: dict = {}

    class _FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

        def fetchall(self):
            return []

    class _FakeConn:
        def set_session(self, readonly=False):
            captured["readonly"] = readonly

        def cursor(self, cursor_factory=None):
            return _FakeCursor()

        def close(self):
            pass

    import projections.eos.integration.tables as tables_mod

    fake_extras = type("_FakeExtras", (), {"DictCursor": object})
    fake_pg = type(
        "_FakePg",
        (),
        {"connect": staticmethod(lambda dsn: _FakeConn()), "extras": fake_extras},
    )
    # action_proposals lazy-imports psycopg2 for connect(); tables.py binds it
    # at module level for the cursor factory — patch both.
    monkeypatch.setitem(sys.modules, "psycopg2", fake_pg)
    monkeypatch.setattr(tables_mod, "psycopg2", fake_pg)

    result = eos_action_proposals()

    assert result["connection_status"] == "connected"
    assert captured["readonly"] is True
    assert "a.status = ANY(%s)" in captured["query"]
    statuses = set(captured["params"][0])
    assert {"pending", "approved"} <= statuses, (
        "the lifecycle SELECT must surface approved rows or execute_enabled is unreachable"
    )
    assert {"executing", "completed", "failed", "rejected"} <= statuses


def test_approval_state_mapping_is_deterministic(monkeypatch):
    rows = [
        _FakeRow(id="a1", status="pending"),
        _FakeRow(id="a2", status="rejected"),
        _FakeRow(id="a3", status="failed"),
        _FakeRow(id="a4", status="completed"),
    ]
    result, _ = _connected(monkeypatch, rows)
    states = {r["proposal_id"]: r["approval_state"] for r in result["proposals"]}
    assert states == {"a1": "PENDING", "a2": "REJECTED", "a3": "EXPIRED", "a4": "APPROVED"}


def test_seam_map_182_is_the_mapping_source(monkeypatch):
    """The seam fields come from the #182 map's approval-queue-row entry."""
    result, _ = _connected(monkeypatch, [_FakeRow()])
    from projections.eos.integration.action_seam import load_eos_action_seam_map

    seam_doc = load_eos_action_seam_map(_SEAM_MAP_PATH)
    seam_row = next(s for s in seam_doc["seams"] if s["seam"] == "approval-queue-row")
    assert result["seam_id"] == "approval-queue-row"
    assert result["seam_primitive"] == seam_row["umh_primitive"] == "Approval"
    assert result["seam_target"] == seam_row["target_owner"]
    for row in result["proposals"]:
        assert row["umh_primitive"] == "Approval"


def test_retry_policy_default_is_human_reapproval(monkeypatch):
    """#182 finding preserved: retry requires human re-approval by default."""
    result, _ = _connected(monkeypatch, [_FakeRow()])
    assert result["retry_policy"] == "human_reapproval_required"


def test_no_parameters_payload_in_rows(monkeypatch):
    """The parameters jsonb (may carry email bodies/PII) is never exposed."""
    result, _ = _connected(monkeypatch, [_FakeRow()])
    for row in result["proposals"]:
        assert "parameters" not in row
        assert "execution_result" not in row


# ── 2. Route thinness ────────────────────────────────────────────────────────


def _route_fn(route_path: str) -> ast.FunctionDef:
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
    raise AssertionError(f"route {route_path} not found")


def test_route_is_thin_wrapper_over_accessor():
    fn = _route_fn("/eos/action-proposals")
    # imports the projection accessor lazily
    assert any(
        isinstance(n, ast.ImportFrom)
        and (n.module or "") == "projections.eos.integration.action_proposals"
        for n in ast.walk(fn)
    ), "route must lazy-import the accessor"
    # no inline domain construction (no Capitalized calls)
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            name = (
                f.id
                if isinstance(f, ast.Name)
                else (f.attr if isinstance(f, ast.Attribute) else "")
            )
            assert not (name and name[0].isupper()), f"route constructs {name} inline"
    # wraps in try/except
    assert any(isinstance(n, ast.Try) for n in fn.body), "route must not 500"


# ── 5. No mutation possible ──────────────────────────────────────────────────


def test_accessor_has_no_write_verbs():
    text = _ACCESSOR_PATH.read_text(encoding="utf-8")
    for verb in ("INSERT", "UPDATE ", "DELETE", ".commit(", "executemany"):
        assert verb not in text, f"accessor contains write verb {verb!r}"
    assert "set_session(readonly=True)" in text


def test_pending_fetch_is_select_only():
    """The one SQL path this packet adds is a SELECT."""
    import inspect

    from projections.eos.integration.tables import fetch_pending_agent_actions

    src = inspect.getsource(fetch_pending_agent_actions)
    assert "SELECT" in src
    for verb in ("INSERT", "UPDATE ", "DELETE", "commit"):
        assert verb not in src, f"pending fetch contains {verb!r}"


# ── 6. No Beast code copied ──────────────────────────────────────────────────


def test_no_copied_beast_code():
    ts_markers = ["async function", "await db.", "drizzle-orm", "pgTable(", "=> {"]
    for path in (_ACCESSOR_PATH, _TABLES_PATH):
        text = path.read_text(encoding="utf-8")
        for marker in ts_markers:
            assert marker not in text, f"copied-code marker {marker!r} in {path.name}"


# ── 7. No secrets ────────────────────────────────────────────────────────────


def test_no_secret_values_in_output(monkeypatch):
    import re

    result, _ = _connected(monkeypatch, [_FakeRow()])
    raw = json.dumps(result)
    for pattern in (
        r"sk-ant-[A-Za-z0-9_-]{10,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"postgres(?:ql)?://[^\s\"]+:[^\s\"]+@",
        r"ya29\.[A-Za-z0-9_-]{20,}",
    ):
        assert not re.search(pattern, raw), f"secret-like value matches {pattern}"
    # the DSN itself must never leak into the response
    assert "ignored-by-fake" not in raw


# ── 8. Only EOS ──────────────────────────────────────────────────────────────


def test_only_eos_is_touched(monkeypatch):
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    _safe_readiness(monkeypatch, safe=True)
    result = eos_action_proposals()
    assert result["projection_id"] == "eos"
    text = _ACCESSOR_PATH.read_text(encoding="utf-8").lower()
    for name in ("creatoros", "lyfeos"):
        assert name not in text


# ── Accessor layering ────────────────────────────────────────────────────────


def test_accessor_imports_only_downward():
    tree = ast.parse(_ACCESSOR_PATH.read_text(encoding="utf-8"))
    allowed_roots = {"substrate", "projections", "__future__", "typing", "logging", "psycopg2"}
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root not in allowed_roots:
                offenders.append(node.module)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in allowed_roots:
                    offenders.append(a.name)
    assert not offenders, f"accessor imports non-downward modules: {offenders}"
