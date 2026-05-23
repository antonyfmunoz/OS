"""LyfeOS capability handler — implements CapabilityHandler Protocol."""

from __future__ import annotations

import logging
import time
from typing import Any

import psycopg2

from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
from substrate.sockets.protocols import CapabilityDescriptor, CapabilityHealth

from .manifest import CAPABILITY_DESCRIPTORS, INTEGRATION_ID
from .tables import insert_daily_log, insert_quest, update_quest

logger = logging.getLogger(__name__)


class LyfeOSCapabilityHandler:
    """Handles capability requests for the LyfeOS integration.

    Satisfies CapabilityHandler Protocol structurally.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url
        self._conn: Any = None

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return list(CAPABILITY_DESCRIPTORS)

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        t0 = time.monotonic()
        handler_map: dict[str, Any] = {
            "noop": self._noop,
            "create_quest": self._create_quest,
            "complete_quest": self._complete_quest,
            "log_daily_reflection": self._log_daily_reflection,
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
        except ValueError as exc:
            latency = (time.monotonic() - t0) * 1000
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} validation failed: {exc}",
                raw_error=f"ValueError: {exc}",
                latency_ms=latency,
            )
        except psycopg2.Error as exc:
            latency = (time.monotonic() - t0) * 1000
            self._conn = None
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} failed: database error",
                raw_error=f"{type(exc).__name__}: {exc}",
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
        if not self._database_url:
            return CapabilityHealth(integration_id=INTEGRATION_ID, status="healthy")
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return CapabilityHealth(integration_id=INTEGRATION_ID, status="healthy")
        except Exception as exc:
            self._conn = None
            return CapabilityHealth(
                integration_id=INTEGRATION_ID,
                status="unavailable",
                detail=str(exc),
            )

    def _get_connection(self) -> Any:
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._conn
            except Exception:
                self._conn = None

        if not self._database_url:
            raise RuntimeError("no LYFEOS_DATABASE_URL configured for capability handler")

        self._conn = psycopg2.connect(self._database_url)
        self._conn.autocommit = False
        return self._conn

    def _noop(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "received": True,
            "table_name": params.get("table_name", ""),
            "user_id": params.get("user_id", 0),
            "row_id": params.get("row_id", ""),
        }

    def _create_quest(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        quest_id = insert_quest(conn, params)
        return {"quest_id": quest_id}

    def _complete_quest(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        if "completed" not in params:
            params["completed"] = True
        return update_quest(conn, params)

    def _log_daily_reflection(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        log_id = insert_daily_log(conn, params)
        return {"log_id": log_id}
