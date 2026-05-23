"""Tests for Notion integration — handler, transforms, auth, protocol satisfaction."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
from substrate.sockets.protocols import (
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

    def test_build_update_page_payload(self) -> None:
        from services.umh.integrations.notion.transforms import build_update_page_payload

        payload = build_update_page_payload("page-1", {"Status": {"select": {"name": "Done"}}})
        assert payload["page_id"] == "page-1"
        assert payload["properties"]["Status"]["select"]["name"] == "Done"

    def test_extract_update_page_result(self) -> None:
        from services.umh.integrations.notion.transforms import extract_update_page_result

        result = extract_update_page_result({"id": "page-1", "url": "https://notion.so/page-1"})
        assert result == {"page_id": "page-1", "updated": True}

    def test_build_append_block_payload(self) -> None:
        from services.umh.integrations.notion.transforms import build_append_block_payload

        children = [{"paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]
        payload = build_append_block_payload("page-1", children)
        assert payload["block_id"] == "page-1"
        assert len(payload["children"]) == 1

    def test_extract_append_block_result(self) -> None:
        from services.umh.integrations.notion.transforms import extract_append_block_result

        response = {"results": [{"id": "block-1"}, {"id": "block-2"}]}
        result = extract_append_block_result(response)
        assert result == {"block_ids": ["block-1", "block-2"], "count": 2}

    def test_extract_append_block_result_empty(self) -> None:
        from services.umh.integrations.notion.transforms import extract_append_block_result

        result = extract_append_block_result({})
        assert result == {"block_ids": [], "count": 0}

    def test_build_query_database_payload_minimal(self) -> None:
        from services.umh.integrations.notion.transforms import build_query_database_payload

        payload = build_query_database_payload("db-1")
        assert payload["database_id"] == "db-1"
        assert payload["page_size"] == 100
        assert "filter" not in payload
        assert "sorts" not in payload

    def test_build_query_database_payload_with_filter_and_sorts(self) -> None:
        from services.umh.integrations.notion.transforms import build_query_database_payload

        f = {"property": "Status", "select": {"equals": "Active"}}
        s = [{"property": "Created", "direction": "descending"}]
        payload = build_query_database_payload("db-1", filter_obj=f, sorts=s, page_size=25)
        assert payload["filter"] == f
        assert payload["sorts"] == s
        assert payload["page_size"] == 25

    def test_build_query_database_payload_clamps_page_size(self) -> None:
        from services.umh.integrations.notion.transforms import build_query_database_payload

        payload = build_query_database_payload("db-1", page_size=500)
        assert payload["page_size"] == 100

    def test_extract_query_database_result(self) -> None:
        from services.umh.integrations.notion.transforms import extract_query_database_result

        response = {
            "results": [
                {"id": "p1", "url": "https://notion.so/p1", "properties": {"Name": {}}},
                {"id": "p2", "url": "https://notion.so/p2", "properties": {"Name": {}}},
            ],
            "has_more": True,
        }
        result = extract_query_database_result(response)
        assert result["count"] == 2
        assert result["has_more"] is True
        assert result["results"][0]["page_id"] == "p1"

    def test_extract_query_database_result_empty(self) -> None:
        from services.umh.integrations.notion.transforms import extract_query_database_result

        result = extract_query_database_result({"results": [], "has_more": False})
        assert result == {"results": [], "count": 0, "has_more": False}


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
            patch.dict(
                os.environ,
                {
                    "NOTION_API_KEY": "test-key",
                    "NOTION_TEST_TASKS_DB": "db-uuid-123",
                },
            ),
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

    # --- update_page tests ---

    def test_update_page_success(self, handler: Any) -> None:
        handler._client.pages.update.return_value = {
            "id": "page-99",
            "url": "https://notion.so/page-99",
        }

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="update_page",
            integration_id="notion",
            params={
                "page_id": "page-99",
                "properties": {"Status": {"select": {"name": "Done"}}},
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        assert response.result_data["page_id"] == "page-99"
        assert response.result_data["updated"] is True
        handler._client.pages.update.assert_called_once()

    def test_update_page_missing_page_id(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="update_page",
            integration_id="notion",
            params={"properties": {"Status": {"select": {"name": "Done"}}}},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "page_id is required" in (response.raw_error or "")

    def test_update_page_missing_properties(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="update_page",
            integration_id="notion",
            params={"page_id": "page-99"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "properties is required" in (response.raw_error or "")

    def test_update_page_api_error(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        handler._client.pages.update.side_effect = APIResponseError(
            code="object_not_found",
            status=404,
            message="page not found",
            headers=Headers(),
            raw_body_text="{}",
        )

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="update_page",
            integration_id="notion",
            params={
                "page_id": "page-gone",
                "properties": {"Status": {"select": {"name": "Done"}}},
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "404" in (response.raw_error or "")
        assert "object_not_found" in (response.error or "")

    def test_update_page_429_retries(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        handler._client.pages.update.side_effect = [
            rate_limit_error,
            {"id": "page-99", "url": "https://notion.so/page-99"},
        ]

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="update_page",
            integration_id="notion",
            params={
                "page_id": "page-99",
                "properties": {"Status": {"select": {"name": "Done"}}},
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        with patch("services.umh.integrations.notion.handlers.time.sleep"):
            response = handler.handle_capability(request)

        assert response.success
        assert response.metadata.get("retried") is True

    # --- append_block tests ---

    def test_append_block_success(self, handler: Any) -> None:
        handler._client.blocks.children.append.return_value = {
            "results": [{"id": "block-1"}, {"id": "block-2"}],
        }

        children = [
            {"paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}},
            {"paragraph": {"rich_text": [{"text": {"content": "World"}}]}},
        ]

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="append_block",
            integration_id="notion",
            params={"page_id": "page-99", "children": children},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        assert response.result_data["count"] == 2
        assert response.result_data["block_ids"] == ["block-1", "block-2"]

    def test_append_block_missing_page_id(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="append_block",
            integration_id="notion",
            params={"children": [{"paragraph": {}}]},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "page_id is required" in (response.raw_error or "")

    def test_append_block_missing_children(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="append_block",
            integration_id="notion",
            params={"page_id": "page-99"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "children is required" in (response.raw_error or "")

    def test_append_block_api_error(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        handler._client.blocks.children.append.side_effect = APIResponseError(
            code="validation_error",
            status=400,
            message="invalid block",
            headers=Headers(),
            raw_body_text="{}",
        )

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="append_block",
            integration_id="notion",
            params={
                "page_id": "page-99",
                "children": [{"paragraph": {}}],
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "400" in (response.raw_error or "")

    def test_append_block_429_retries(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        handler._client.blocks.children.append.side_effect = [
            rate_limit_error,
            {"results": [{"id": "block-1"}]},
        ]

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="append_block",
            integration_id="notion",
            params={
                "page_id": "page-99",
                "children": [{"paragraph": {"rich_text": [{"text": {"content": "retry"}}]}}],
            },
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        with patch("services.umh.integrations.notion.handlers.time.sleep"):
            response = handler.handle_capability(request)

        assert response.success
        assert response.metadata.get("retried") is True

    # --- query_database tests ---

    def test_query_database_success(self, handler: Any) -> None:
        handler._client.request.return_value = {
            "results": [
                {"id": "p1", "url": "https://notion.so/p1", "properties": {"Name": {}}},
            ],
            "has_more": False,
        }

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={"database_id": "test_tasks"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        assert response.result_data["count"] == 1
        assert response.result_data["results"][0]["page_id"] == "p1"
        assert response.result_data["has_more"] is False

    def test_query_database_with_filter(self, handler: Any) -> None:
        handler._client.request.return_value = {
            "results": [],
            "has_more": False,
        }

        f = {"property": "Status", "select": {"equals": "Active"}}

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={"database_id": "test_tasks", "filter": f, "page_size": 10},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        call_kwargs = handler._client.request.call_args
        assert call_kwargs[1]["path"] == "databases/db-uuid-123/query"
        assert call_kwargs[1]["body"]["page_size"] == 10

    def test_query_database_missing_database_id(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "database_id is required" in (response.raw_error or "")

    def test_query_database_unknown_logical_name(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={"database_id": "nonexistent_db"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "unknown database" in (response.raw_error or "")

    def test_query_database_api_error(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        handler._client.request.side_effect = APIResponseError(
            code="object_not_found",
            status=404,
            message="database not found",
            headers=Headers(),
            raw_body_text="{}",
        )

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={"database_id": "test_tasks"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert not response.success
        assert "404" in (response.raw_error or "")

    def test_query_database_429_retries(self, handler: Any) -> None:
        from notion_client import APIResponseError
        from httpx import Headers

        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        handler._client.request.side_effect = [
            rate_limit_error,
            {"results": [{"id": "p1", "url": "u", "properties": {}}], "has_more": False},
        ]

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="query_database",
            integration_id="notion",
            params={"database_id": "test_tasks"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        with patch("services.umh.integrations.notion.handlers.time.sleep"):
            response = handler.handle_capability(request)

        assert response.success
        assert response.metadata.get("retried") is True

    def test_describe_capabilities_includes_phase2(self, handler: Any) -> None:
        caps = handler.describe_capabilities()
        names = [c.name for c in caps]
        assert "update_page" in names
        assert "append_block" in names
        assert "query_database" in names

    # --- noop tests ---

    def test_noop_success(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="notion",
            params={"page_id": "page-42"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        response = handler.handle_capability(request)
        assert response.success
        assert response.result_data["received"] is True
        assert response.result_data["page_id"] == "page-42"

    def test_noop_no_api_call(self, handler: Any) -> None:
        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="notion",
            params={"page_id": "page-42"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )

        handler.handle_capability(request)
        handler._client.pages.create.assert_not_called()
        handler._client.pages.update.assert_not_called()
        handler._client.blocks.children.append.assert_not_called()
        handler._client.request.assert_not_called()

    def test_describe_capabilities_includes_noop(self, handler: Any) -> None:
        caps = handler.describe_capabilities()
        names = [c.name for c in caps]
        assert "noop" in names


class TestNotionSignalEmitter:
    def test_satisfies_protocol(self) -> None:
        from services.umh.integrations.notion.signals import NotionSignalEmitter

        emitter = NotionSignalEmitter()
        assert isinstance(emitter, SignalEmitter)
        assert emitter.integration_id == "notion"
        assert len(emitter.describe_signals()) > 0


class TestNotionOutcomeReceiver:
    def test_satisfies_protocol(self) -> None:
        from services.umh.integrations.notion.correlation import CorrelationMap
        from services.umh.integrations.notion.outcomes import NotionOutcomeReceiver

        receiver = NotionOutcomeReceiver(MagicMock(), CorrelationMap())
        assert isinstance(receiver, OutcomeReceiver)
        assert receiver.integration_id == "notion"

    def test_accepts_all_outcomes(self) -> None:
        from services.umh.integrations.notion.correlation import CorrelationMap
        from services.umh.integrations.notion.outcomes import NotionOutcomeReceiver

        receiver = NotionOutcomeReceiver(MagicMock(), CorrelationMap())
        assert receiver.accepts_outcomes() == []
