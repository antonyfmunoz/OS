"""Notion capability handler — implements CapabilityHandler Protocol."""

from __future__ import annotations

import logging
import time
from typing import Any

from notion_client import APIResponseError

from services.umh.sockets.envelopes import CapabilityRequest, CapabilityResponse
from services.umh.sockets.protocols import CapabilityDescriptor, CapabilityHealth

from .auth import discover_database_ids, get_notion_client
from .manifest import CAPABILITY_DESCRIPTORS, INTEGRATION_ID
from .transforms import (
    build_append_block_payload,
    build_create_page_payload,
    build_query_database_payload,
    build_update_page_payload,
    extract_append_block_result,
    extract_create_page_result,
    extract_query_database_result,
    extract_update_page_result,
)

logger = logging.getLogger(__name__)

_RETRY_STATUS = 429
_RETRY_BACKOFF_SECONDS = 2.0


class NotionCapabilityHandler:
    """Handles capability requests by calling the Notion SDK.

    Satisfies CapabilityHandler Protocol structurally.
    Phase 1: create_page. Phase 2: update_page, append_block, query_database.
    Phase 3: noop (signal acknowledgement, no external action).
    """

    def __init__(self) -> None:
        self._client = get_notion_client()
        self._databases = discover_database_ids()
        logger.info(
            "notion handler initialized: %d databases discovered",
            len(self._databases),
        )

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return list(CAPABILITY_DESCRIPTORS)

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        t0 = time.monotonic()
        handler_map = {
            "create_page": self._create_page,
            "update_page": self._update_page,
            "append_block": self._append_block,
            "query_database": self._query_database,
            "noop": self._noop,
        }

        handler = handler_map.get(request.capability_name)
        if handler is None:
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"unsupported capability: {request.capability_name}",
                latency_ms=(time.monotonic() - t0) * 1000,
            )

        try:
            result = handler(request.params)
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=True,
                result_data=result,
                latency_ms=latency,
            )
        except APIResponseError as exc:
            if exc.status == _RETRY_STATUS:
                return self._retry_once(handler, request, t0, exc)
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} failed: {exc.code}",
                raw_error=f"APIResponseError: {exc.status} {exc.code}",
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} failed",
                raw_error=f"{type(exc).__name__}: {exc}",
                latency_ms=latency,
            )

    def health(self) -> CapabilityHealth:
        try:
            self._client.users.me()
            return CapabilityHealth(integration_id=INTEGRATION_ID, status="healthy")
        except Exception as exc:
            return CapabilityHealth(
                integration_id=INTEGRATION_ID,
                status="unavailable",
                detail=str(exc),
            )

    def _resolve_database_id(self, raw_id: str) -> str:
        """Resolve a logical database name to a UUID, or pass through if already a UUID."""
        if "-" in raw_id and len(raw_id) >= 32:
            return raw_id
        resolved = self._databases.get(raw_id)
        if resolved is None:
            raise ValueError(f"unknown database logical name: {raw_id}")
        return resolved

    def _create_page(self, params: dict[str, Any]) -> dict[str, Any]:
        title = params.get("title", "Untitled")
        raw_db_id = params.get("database_id", "")
        if not raw_db_id:
            raise ValueError("database_id is required for create_page")

        database_id = self._resolve_database_id(raw_db_id)
        properties = params.get("properties")

        payload = build_create_page_payload(database_id, title, properties)
        response = self._client.pages.create(**payload)
        return extract_create_page_result(response)

    def _update_page(self, params: dict[str, Any]) -> dict[str, Any]:
        page_id = params.get("page_id", "")
        if not page_id:
            raise ValueError("page_id is required for update_page")
        properties = params.get("properties")
        if not properties:
            raise ValueError("properties is required for update_page")

        payload = build_update_page_payload(page_id, properties)
        response = self._client.pages.update(**payload)
        return extract_update_page_result(response)

    def _append_block(self, params: dict[str, Any]) -> dict[str, Any]:
        page_id = params.get("page_id", "")
        if not page_id:
            raise ValueError("page_id is required for append_block")
        children = params.get("children")
        if not children:
            raise ValueError("children is required for append_block")

        payload = build_append_block_payload(page_id, children)
        response = self._client.blocks.children.append(**payload)
        return extract_append_block_result(response)

    def _query_database(self, params: dict[str, Any]) -> dict[str, Any]:
        raw_db_id = params.get("database_id", "")
        if not raw_db_id:
            raise ValueError("database_id is required for query_database")

        database_id = self._resolve_database_id(raw_db_id)
        filter_obj = params.get("filter")
        sorts = params.get("sorts")
        page_size = params.get("page_size", 100)

        payload = build_query_database_payload(database_id, filter_obj, sorts, page_size)
        body = {k: v for k, v in payload.items() if k != "database_id"}
        response = self._client.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body=body,
        )
        return extract_query_database_result(response)

    def _noop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Acknowledge a signal without making any Notion API call."""
        return {"received": True, "page_id": params.get("page_id", "")}

    def _retry_once(
        self,
        handler_fn: Any,
        request: CapabilityRequest,
        t0: float,
        original_exc: APIResponseError,
    ) -> CapabilityResponse:
        """One retry with backoff on 429."""
        logger.warning("notion 429 — retrying in %.1fs", _RETRY_BACKOFF_SECONDS)
        time.sleep(_RETRY_BACKOFF_SECONDS)
        try:
            result = handler_fn(request.params)
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=True,
                result_data=result,
                latency_ms=latency,
                metadata={"retried": True},
            )
        except Exception as retry_exc:
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} failed after retry",
                raw_error=f"{type(retry_exc).__name__}: {retry_exc}",
                latency_ms=latency,
                metadata={"retried": True},
            )
