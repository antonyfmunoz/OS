"""Tests for EOS capability handler — Phase 2 write capabilities."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.umh.integrations.eos.handlers import EOSCapabilityHandler
from substrate.sockets.envelopes import CapabilityRequest


def _make_request(
    capability_name: str,
    params: dict[str, Any] | None = None,
) -> CapabilityRequest:
    return CapabilityRequest(
        request_id=uuid4(),
        capability_name=capability_name,
        integration_id="eos",
        params=params or {},
        governance_verdict_id=uuid4(),
        trace_id=uuid4(),
    )


def _mock_conn(return_id: str = "new-id") -> MagicMock:
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = (return_id,)
    return conn


class TestHandlerDispatch:
    def test_noop_still_works(self) -> None:
        handler = EOSCapabilityHandler()
        req = _make_request("noop", {"org_id": "org-1", "table_name": "events", "row_id": "r1"})
        resp = handler.handle_capability(req)
        assert resp.success is True
        assert resp.result_data["received"] is True

    def test_unsupported_capability(self) -> None:
        handler = EOSCapabilityHandler()
        req = _make_request("delete_everything")
        resp = handler.handle_capability(req)
        assert resp.success is False
        assert "unsupported" in resp.error

    def test_describe_includes_phase2_capabilities(self) -> None:
        handler = EOSCapabilityHandler()
        names = {d.name for d in handler.describe_capabilities()}
        assert "create_event" in names
        assert "create_client" in names
        assert "update_venture" in names
        assert "noop" in names


class TestCreateEvent:
    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_success(self, mock_get_conn: MagicMock) -> None:
        conn = _mock_conn("evt-111")
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request("create_event", {"org_id": "org-1", "event_type": "test.created"})
        resp = handler.handle_capability(req)

        assert resp.success is True
        assert resp.result_data["event_id"] == "evt-111"

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_missing_org_id(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request("create_event", {"event_type": "test"})
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_missing_event_type(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request("create_event", {"org_id": "org-1"})
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error


class TestCreateClient:
    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_success(self, mock_get_conn: MagicMock) -> None:
        conn = _mock_conn("cli-222")
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "create_client",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Alice",
                "email": "a@b.com",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is True
        assert resp.result_data["client_id"] == "cli-222"

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_invalid_status_returns_failure(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "create_client",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Bob",
                "email": "b@b.com",
                "status": "vip",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_missing_email_returns_failure(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "create_client",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "name": "Charlie",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error


class TestUpdateVenture:
    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_update_revenue_success(self, mock_get_conn: MagicMock) -> None:
        conn = _mock_conn("v-1")
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "update_venture",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "monthly_revenue": "5000",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is True
        assert resp.result_data["venture_id"] == "v-1"
        assert resp.result_data["updated"] is True
        assert "monthly_revenue" in resp.result_data["fields_changed"]

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_update_stage_success(self, mock_get_conn: MagicMock) -> None:
        conn = _mock_conn("v-1")
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "update_venture",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "stage": "pre_revenue",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is True
        assert "stage" in resp.result_data["fields_changed"]

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_invalid_stage_returns_failure(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "update_venture",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
                "stage": "unicorn",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_no_fields_returns_failure(self, mock_get_conn: MagicMock) -> None:
        mock_get_conn.return_value = _mock_conn()

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "update_venture",
            {
                "org_id": "org-1",
                "venture_id": "v-1",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_venture_not_found_returns_failure(self, mock_get_conn: MagicMock) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = None
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request(
            "update_venture",
            {
                "org_id": "org-1",
                "venture_id": "v-missing",
                "stage": "early",
            },
        )
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "validation failed" in resp.error


class TestDbErrorHandling:
    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_psycopg2_error_returns_db_error(self, mock_get_conn: MagicMock) -> None:
        import psycopg2

        mock_get_conn.side_effect = psycopg2.OperationalError("connection refused")

        handler = EOSCapabilityHandler(database_url="fake://url")
        req = _make_request("create_event", {"org_id": "org-1", "event_type": "test"})
        resp = handler.handle_capability(req)

        assert resp.success is False
        assert "database error" in resp.error

    def test_health_without_db_url_is_healthy(self) -> None:
        handler = EOSCapabilityHandler()
        health = handler.health()
        assert health.status == "healthy"

    @patch.object(EOSCapabilityHandler, "_get_connection")
    def test_health_with_connection_success(self, mock_get_conn: MagicMock) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = conn

        handler = EOSCapabilityHandler(database_url="fake://url")
        health = handler.health()
        assert health.status == "healthy"

    def test_latency_tracked(self) -> None:
        handler = EOSCapabilityHandler()
        req = _make_request("noop", {"org_id": "org-1"})
        resp = handler.handle_capability(req)
        assert resp.latency_ms >= 0
