"""Tests for EOS tables.py — typed query helpers with org_id filtering."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.umh.integrations.eos.tables import (
    VALID_CLIENT_STATUSES,
    VALID_VENTURE_STAGES,
    EventRow,
    fetch_events_since,
    fetch_org_ids,
    insert_client,
    insert_event,
    insert_test_event,
    update_venture,
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
    return FakeDictRow(
        {
            "id": row_id,
            "org_id": org_id,
            "event_type": event_type,
            "payload_json": payload or {"name": "Test Lead"},
            "handled_by": handled_by,
            "created_at": datetime.fromisoformat(created_at),
        }
    )


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


# ---------------------------------------------------------------------------
# Phase 2: write helpers
# ---------------------------------------------------------------------------


def _mock_conn_with_returning(return_id: str = "new-id") -> MagicMock:
    """Create a mock connection that returns a single-column row on RETURNING."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = (return_id,)
    return conn


class TestInsertEvent:
    def test_returns_event_id(self) -> None:
        conn = _mock_conn_with_returning("evt-123")
        result = insert_event(conn, {"org_id": "org-1", "event_type": "test.created"})
        assert result == "evt-123"
        conn.commit.assert_called_once()

    def test_missing_org_id_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="org_id"):
            insert_event(conn, {"event_type": "test"})

    def test_missing_event_type_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="event_type"):
            insert_event(conn, {"org_id": "org-1"})

    def test_empty_string_org_id_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="org_id"):
            insert_event(conn, {"org_id": "", "event_type": "test"})

    def test_payload_defaults_to_empty_dict(self) -> None:
        conn = _mock_conn_with_returning()
        insert_event(conn, {"org_id": "org-1", "event_type": "test"})
        cursor = conn.cursor.return_value.__enter__.return_value
        sql_params = cursor.execute.call_args[0][1]
        assert sql_params[2].adapted == {}

    def test_invalid_payload_type_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="payload_json"):
            insert_event(
                conn, {"org_id": "org-1", "event_type": "test", "payload_json": "not-a-dict"}
            )

    def test_handled_by_passed_through(self) -> None:
        conn = _mock_conn_with_returning()
        insert_event(conn, {"org_id": "org-1", "event_type": "test", "handled_by": "umh"})
        cursor = conn.cursor.return_value.__enter__.return_value
        sql_params = cursor.execute.call_args[0][1]
        assert sql_params[3] == "umh"


class TestInsertClient:
    def test_returns_client_id(self) -> None:
        conn = _mock_conn_with_returning("client-456")
        result = insert_client(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Alice",
                "email": "a@b.com",
            },
        )
        assert result == "client-456"
        conn.commit.assert_called_once()

    def test_missing_name_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="name"):
            insert_client(conn, {"org_id": "org-1", "venture_id": "v-1", "email": "a@b.com"})

    def test_missing_email_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="email"):
            insert_client(conn, {"org_id": "org-1", "venture_id": "v-1", "name": "Alice"})

    def test_missing_venture_id_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="venture_id"):
            insert_client(conn, {"org_id": "org-1", "name": "Alice", "email": "a@b.com"})

    def test_invalid_status_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="invalid client status"):
            insert_client(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "name": "Alice",
                    "email": "a@b.com",
                    "status": "invalid_status",
                },
            )

    def test_default_source_is_umh(self) -> None:
        conn = _mock_conn_with_returning()
        insert_client(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Alice",
                "email": "a@b.com",
            },
        )
        cursor = conn.cursor.return_value.__enter__.return_value
        sql_params = cursor.execute.call_args[0][1]
        assert sql_params[4] == "umh"

    def test_default_status_is_lead(self) -> None:
        conn = _mock_conn_with_returning()
        insert_client(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Alice",
                "email": "a@b.com",
            },
        )
        cursor = conn.cursor.return_value.__enter__.return_value
        sql_params = cursor.execute.call_args[0][1]
        assert sql_params[7] == "lead"

    def test_all_valid_statuses_accepted(self) -> None:
        for status in VALID_CLIENT_STATUSES:
            conn = _mock_conn_with_returning()
            insert_client(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "name": "Alice",
                    "email": "a@b.com",
                    "status": status,
                },
            )


class TestUpdateVenture:
    def test_update_revenue(self) -> None:
        conn = _mock_conn_with_returning("v-1")
        result = update_venture(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "monthly_revenue": "5000.50",
            },
        )
        assert result["venture_id"] == "v-1"
        assert result["updated"] is True
        assert "monthly_revenue" in result["fields_changed"]

    def test_update_stage(self) -> None:
        conn = _mock_conn_with_returning("v-1")
        result = update_venture(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "stage": "early",
            },
        )
        assert "stage" in result["fields_changed"]

    def test_update_both(self) -> None:
        conn = _mock_conn_with_returning("v-1")
        result = update_venture(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "monthly_revenue": "10000",
                "stage": "growth",
            },
        )
        assert sorted(result["fields_changed"]) == ["monthly_revenue", "stage"]

    def test_no_fields_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="at least one"):
            update_venture(conn, {"org_id": "org-1", "venture_id": "v-1"})

    def test_invalid_stage_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="invalid venture stage"):
            update_venture(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "stage": "unicorn",
                },
            )

    def test_negative_revenue_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="non-negative"):
            update_venture(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "monthly_revenue": "-100",
                },
            )

    def test_invalid_revenue_format_raises(self) -> None:
        conn = _mock_conn_with_returning()
        with pytest.raises(ValueError, match="valid decimal"):
            update_venture(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "monthly_revenue": "not-a-number",
                },
            )

    def test_venture_not_found_raises(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="not found"):
            update_venture(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-nonexistent",
                    "stage": "early",
                },
            )

    def test_all_valid_stages_accepted(self) -> None:
        for stage in VALID_VENTURE_STAGES:
            conn = _mock_conn_with_returning("v-1")
            update_venture(
                conn,
                {
                    "org_id": "org-1",
                    "venture_id": "v-1",
                    "stage": stage,
                },
            )

    def test_numeric_revenue_coerced(self) -> None:
        conn = _mock_conn_with_returning("v-1")
        result = update_venture(
            conn,
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "monthly_revenue": 7500,
            },
        )
        assert result["updated"] is True
