"""Tenant-isolation regression test for EOS task polling (WP-P0-010).

Defect: ``fetch_tasks_since`` accepted ``user_id`` but never bound it — the
WHERE clause ``a.id IN (SELECT id FROM agents)`` was tautological, so the poll
returned tasks across ALL tenants. This test seeds two tenants with distinct
agents/tasks and asserts each poll returns ONLY its own tenant's rows.

Deterministic. No live Neon. An in-memory sqlite database backs a thin
psycopg2-compatible connection shim so the REAL SQL string from
``tables.fetch_tasks_since`` is executed unchanged (``%s`` placeholders are
translated to sqlite ``?`` and rows are exposed as dict-like ``sqlite3.Row``).
"""

import sqlite3
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest

from projections.eos.integration.tables import fetch_tasks_since


class _ShimCursor:
    """psycopg2-style cursor over sqlite. Translates %s -> ? placeholders.

    DictCursor rows are dict-indexable (row["col"]); sqlite3.Row provides the
    same access pattern, so the production row-mapping code runs untouched.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._cur: sqlite3.Cursor | None = None

    def execute(self, query: str, params=()):
        self._cur = self._conn.execute(query.replace("%s", "?"), params)
        return self

    def fetchall(self):
        assert self._cur is not None
        return self._cur.fetchall()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ShimConnection:
    """Minimal psycopg2-compatible connection backed by in-memory sqlite."""

    def __init__(self, sqlite_conn: sqlite3.Connection):
        self._conn = sqlite_conn

    def cursor(self, cursor_factory=None):
        # cursor_factory (DictCursor) is irrelevant: sqlite3.Row already gives
        # dict-style access, which is what the production code relies on.
        return _ShimCursor(self._conn)


@pytest.fixture
def two_tenant_conn():
    """Two tenants, distinct agents and tasks, agent ownership via agent_actions/metrics."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE agents (id TEXT PRIMARY KEY);
        CREATE TABLE agent_actions (id TEXT PRIMARY KEY, agent_id TEXT, user_id TEXT);
        CREATE TABLE agent_metrics (id TEXT PRIMARY KEY, agent_id TEXT, user_id TEXT);
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY, title TEXT, description TEXT, status TEXT,
            priority TEXT, agent_id TEXT, task_type TEXT, created_at TEXT
        );

        -- Tenant A: user_a owns agent_a
        INSERT INTO agents (id) VALUES ('agent_a'), ('agent_b');
        INSERT INTO agent_actions (id, agent_id, user_id) VALUES ('act_a', 'agent_a', 'user_a');
        -- Tenant B: user_b owns agent_b (ownership expressed via metrics only)
        INSERT INTO agent_metrics (id, agent_id, user_id) VALUES ('met_b', 'agent_b', 'user_b');

        INSERT INTO tasks
            (id, title, description, status, priority, agent_id, task_type, created_at)
        VALUES
            ('task_a1', 'A one', 'd', 'todo', 'medium', 'agent_a', 'standard', '2026-01-01T00:00:01'),
            ('task_a2', 'A two', 'd', 'todo', 'medium', 'agent_a', 'standard', '2026-01-01T00:00:02'),
            ('task_b1', 'B one', 'd', 'todo', 'medium', 'agent_b', 'standard', '2026-01-01T00:00:03');
        """
    )
    return _ShimConnection(db)


def test_tenant_a_sees_only_its_own_tasks(two_tenant_conn):
    rows = fetch_tasks_since(two_tenant_conn, "user_a", "2026-01-01T00:00:00")
    ids = {r.id for r in rows}
    assert ids == {"task_a1", "task_a2"}
    assert "task_b1" not in ids  # cross-tenant row NOT returned


def test_tenant_b_sees_only_its_own_tasks(two_tenant_conn):
    rows = fetch_tasks_since(two_tenant_conn, "user_b", "2026-01-01T00:00:00")
    ids = {r.id for r in rows}
    assert ids == {"task_b1"}
    assert "task_a1" not in ids and "task_a2" not in ids  # cross-tenant rows NOT returned


def test_unknown_tenant_sees_nothing(two_tenant_conn):
    rows = fetch_tasks_since(two_tenant_conn, "user_c", "2026-01-01T00:00:00")
    assert rows == []  # no owned agents -> no tasks; scope is bound, not tautological


def test_since_watermark_still_applies_within_tenant(two_tenant_conn):
    # Bind user_a AND advance the watermark past task_a1: only task_a2 remains.
    rows = fetch_tasks_since(two_tenant_conn, "user_a", "2026-01-01T00:00:01")
    ids = {r.id for r in rows}
    assert ids == {"task_a2"}
