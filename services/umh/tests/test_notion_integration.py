"""Tests for Notion integration — handler, transforms, auth, protocol satisfaction."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.umh.sockets.envelopes import CapabilityRequest, CapabilityResponse
from services.umh.sockets.protocols import (
    CapabilityHandler,
    OutcomeReceiver,
    SignalEmitter,
)


class TestTransforms:
    def test_build_create_page_payload_minimal(self) -> None:
        from services.umh.integrations.notion.transforms import build_create_page_payload

        payload = build_create_page_payload("db-123", "Test Page")
        assert payload["parent"]["database_id"] == "db-123"
        assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Test Page"

    def test_build_create_page_payload_with_properties(self) -> None:
        from services.umh.integrations.notion.transforms import build_create_page_payload

        extra = {"Status": {"select": {"name": "Active"}}}
        payload = build_create_page_payload("db-123", "Test", properties=extra)
        assert payload["properties"]["Status"] == {"select": {"name": "Active"}}
        assert "Name" in payload["properties"]

    def test_extract_create_page_result(self) -> None:
        from services.umh.integrations.notion.transforms import extract_create_page_result

        response = {"id": "page-abc", "url": "https://notion.so/page-abc", "extra": "ignored"}
        result = extract_create_page_result(response)
        assert result == {"page_id": "page-abc", "url": "https://notion.so/page-abc"}

    def test_extract_create_page_result_missing_fields(self) -> None:
        from services.umh.integrations.notion.transforms import extract_create_page_result

        result = extract_create_page_result({})
        assert result == {"page_id": "", "url": ""}


class TestAuth:
    def test_discover_database_ids_from_env(self) -> None:
        from services.umh.integrations.notion.auth import discover_database_ids

        env = {
            "NOTION_API_KEY": "secret",
            "NOTION_TOKEN": "secret",
            "NOTION_LYFE_INSTITUTE_TASKS_DB": "uuid-1",
            "NOTION_EMPYREAN_CREATIVE_PIPELINE_CRM_DB": "uuid-2",
            "NOTION_PORTFOLIO_ID": "uuid-3",
            "UNRELATED_VAR": "nope",
            "NOTION_SOMETHING": "no-suffix",
        }
        with patch.dict(os.environ, env, clear=True):
            result = discover_database_ids()

        assert result["lyfe_institute_tasks"] == "uuid-1"
        assert result["empyrean_creative_pipeline_crm"] == "uuid-2"
        assert result["portfolio"] == "uuid-3"
        assert "api_key" not in result
        assert "token" not in result
        assert "UNRELATED_VAR" not in result
        assert "something" not in result

    def test_discover_skips_empty_values(self) -> None:
        from services.umh.integrations.notion.auth import discover_database_ids

        with patch.dict(os.environ, {"NOTION_EMPTY_DB": ""}, clear=True):
            result = discover_database_ids()
        assert "empty" not in result

    def test_get_notion_client_raises_without_key(self) -> None:
        from services.umh.integrations.notion.auth import get_notion_client

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("services.umh.integrations.notion.auth.load_dotenv"),
        ):
            with pytest.raises(RuntimeError, match="NOTION_API_KEY not set"):
                get_notion_client()


class TestNotionCapabilityHandler:
    @pytest.fixture()
    def handler(self) -> Any:
        with (
            patch.dict(os.environ, {
                "NOTION_API_KEY": "test-key",
                "NOTION_TEST_TASKS_DB": "db-uuid-123",
            }),
            patch("services.umh.integrations.notion.auth.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            from services.umh.integrations.notion.handlers import NotionCapabilityHandler

            h = NotionCapabilityHandler()
            h._client = mock_client
            yield h

    def test_integration_id(self, handler: Any) -> None:
        assert handler.integration_id == "notion"

    def test_describe_capabilities_nonempty(self, handler: Any) -> None:
        caps = handler.describe_capabilities()
        assert len(caps) > 0
        names = [c.name for c in caps]
        assert "create_page" in names

    def test_satisfies_capability_handler_protocol(self, handler: Any) -> None:
        assert isinstance(handler, CapabilityHandler)

    def test_create_page_success(self, handler: Any) -> None:
        handler._client.pages.create.return_value = {
            "id": "new-page-id",
            "url": "https://notion.so/new-page-id",
        }

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={
                "title": "Test Page",
                "database_id": "test_tasks",
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        assert response.result_data["page_id"] == "new-page-id"
        assert response.result_data["url"] == "https://notion.so/new-page-id"
        assert response.latency_ms > 0

    def test_create_page_with_logical_name(self, handler: Any) -> None:
        handler._client.pages.create.return_value = {
            "id": "page-1",
            "url": "https://notion.so/page-1",
        }

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={
                "title": "Logical Name Test",
                "database_id": "test_tasks",
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        call_kwargs = handler._client.pages.create.call_args
        assert call_kwargs[1]["parent"]["database_id"] == "db-uuid-123"

    def test_create_page_missing_database_id(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={"title": "No DB"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "database_id is required" in (response.raw_error or "")

    def test_create_page_unknown_logical_name(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={"title": "Bad DB", "database_id": "nonexistent_db"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "unknown database" in (response.raw_error or "")

    def test_unsupported_capability(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="delete_page",
            integration_id="notion",
            params={},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "unsupported" in (response.error or "")

    def test_api_error_returns_raw_error(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        handler._client.pages.create.side_effect = APIResponseError(
            code="validation_error",
            status=400,
            message="invalid request",
            headers=Headers(),
            raw_body_text="{}",
        )

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={"title": "Fail", "database_id": "test_tasks"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "400" in (response.raw_error or "")

    def test_429_retries_once(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        handler._client.pages.create.side_effect = [
            rate_limit_error,
            {"id": "retry-page", "url": "https://notion.so/retry-page"},
        ]

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="create_page",
            integration_id="notion",
            params={"title": "Retry Test", "database_id": "test_tasks"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        with patch("services.umh.integrations.notion.handlers.time.sleep"):
            response = handler.handle_capability(request)

        assert response.success
        assert response.result_data["page_id"] == "retry-page"
        assert response.metadata.get("retried") is True

    def test_health_healthy(self, handler: Any) -> None:
        handler._client.users.me.return_value = {"id": "user-1"}
        h = handler.health()
        assert h.status == "healthy"

    def test_health_unavailable(self, handler: Any) -> None:
        handler._client.users.me.side_effect = Exception("auth failed")
        h = handler.health()
        assert h.status == "unavailable"

    def test_database_id_passthrough_uuid(self, handler: Any) -> None:
        resolved = handler._resolve_database_id("32eda8b9-6e4f-8121-9cae-e31327db0459")
        assert resolved == "32eda8b9-6e4f-8121-9cae-e31327db0459"


class TestNotionSignalEmitter:
    def test_satisfies_protocol(self) -> None:
        from services.umh.integrations.notion.signals import NotionSignalEmitter

        emitter = NotionSignalEmitter()
        assert isinstance(emitter, SignalEmitter)
        assert emitter.integration_id == "notion"
        assert len(emitter.describe_signals()) > 0


class TestNotionOutcomeReceiver:
    def test_satisfies_protocol(self) -> None:
        from services.umh.integrations.notion.outcomes import NotionOutcomeReceiver

        receiver = NotionOutcomeReceiver()
        assert isinstance(receiver, OutcomeReceiver)
        assert receiver.integration_id == "notion"

    def test_accepts_all_outcomes(self) -> None:
        from services.umh.integrations.notion.outcomes import NotionOutcomeReceiver

        receiver = NotionOutcomeReceiver()
        assert receiver.accepts_outcomes() == []
