"""Tests for EOS tables.py — typed query helpers with org_id filtering."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.umh.integrations.eos.tables import (
    EventRow,
    fetch_events_since,
    fetch_org_ids,
    insert_test_event,
)


class FakeDictRow(dict):
    """Dict subclass that acts like a psycopg2 DictRow."""
    pass


def _make_row(
    row_id: str = "aaaa-1111",
    org_id: str = "org-1",
    event_type: str = "lead_created",
    payload: dict | None = None,
    handled_by: str | None = None,
    created_at: str = "2026-05-19T10:00:00+00:00",
) -> FakeDictRow:
    return FakeDictRow({
        "id": row_id,
        "org_id": org_id,
        "event_type": event_type,
        "payload_json": payload or {"name": "Test Lead"},
        "handled_by": handled_by,
        "created_at": datetime.fromisoformat(created_at),
    })


class TestFetchOrgIds:
    def test_returns_org_ids(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [("org-1",), ("org-2",), ("org-3",)]

        result = fetch_org_ids(conn)

        assert result == ["org-1", "org-2", "org-3"]

    def test_empty_database_returns_empty(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []

        result = fetch_org_ids(conn)

        assert result == []


class TestFetchEventsSince:
    def test_returns_typed_event_rows(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            _make_row(row_id="r1", org_id="org-1"),
        ]

        rows = fetch_events_since(conn, "org-1", "2000-01-01T00:00:00+00:00")

        assert len(rows) == 1
        assert isinstance(rows[0], EventRow)
        assert rows[0].id == "r1"
        assert rows[0].org_id == "org-1"
        assert rows[0].event_type == "lead_created"

    def test_multi_row_result(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            _make_row(row_id="r1", org_id="org-1", created_at="2026-05-19T10:00:00+00:00"),
            _make_row(row_id="r2", org_id="org-1", created_at="2026-05-19T11:00:00+00:00"),
            _make_row(row_id="r3", org_id="org-1", created_at="2026-05-19T12:00:00+00:00"),
        ]

        rows = fetch_events_since(conn, "org-1", "2026-05-19T09:00:00+00:00")

        assert len(rows) == 3
        assert rows[0].id == "r1"
        assert rows[2].id == "r3"

    def test_empty_result(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []

        rows = fetch_events_since(conn, "org-1", "2026-05-19T10:00:00+00:00")

        assert rows == []

    def test_passes_org_id_to_query(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []

        fetch_events_since(conn, "org-42", "2026-05-19T10:00:00+00:00", limit=50)

        call_args = cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == "org-42"
        assert params[2] == 50

    def test_payload_json_non_dict_becomes_empty(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        row = _make_row()
        row["payload_json"] = "not a dict"
        cursor.fetchall.return_value = [row]

        rows = fetch_events_since(conn, "org-1", "2000-01-01T00:00:00+00:00")

        assert rows[0].payload_json == {}

    def test_org_id_filtering_different_orgs(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            _make_row(row_id="r1", org_id="org-A"),
        ]

        rows = fetch_events_since(conn, "org-A", "2000-01-01T00:00:00+00:00")

        assert len(rows) == 1
        assert rows[0].org_id == "org-A"

    def test_handled_by_preserved(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            _make_row(handled_by="agent-ceo"),
        ]

        rows = fetch_events_since(conn, "org-1", "2000-01-01T00:00:00+00:00")

        assert rows[0].handled_by == "agent-ceo"

    def test_created_at_is_datetime(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [_make_row()]

        rows = fetch_events_since(conn, "org-1", "2000-01-01T00:00:00+00:00")

        assert isinstance(rows[0].created_at, datetime)


class TestInsertTestEvent:
    def test_returns_id(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = ("new-event-id",)

        result = insert_test_event(conn, "org-1")

        assert result == "new-event-id"
        conn.commit.assert_called_once()
