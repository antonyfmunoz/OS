"""EOS capability handler — implements CapabilityHandler Protocol."""

from __future__ import annotations

import logging
import time
from typing import Any

import psycopg2

from services.umh.sockets.envelopes import CapabilityRequest, CapabilityResponse
from services.umh.sockets.protocols import CapabilityDescriptor, CapabilityHealth

from .manifest import CAPABILITY_DESCRIPTORS, INTEGRATION_ID
from .tables import insert_activity, insert_contact, insert_deal, update_deal_stage

logger = logging.getLogger(__name__)


class EOSCapabilityHandler:
    """Handles capability requests for the EOS integration.

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
            "create_contact": self._create_contact,
            "create_deal": self._create_deal,
            "update_deal_stage": self._update_deal_stage,
            "log_activity": self._log_activity,
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
        """Get or create a Postgres connection with one reconnect attempt."""
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._conn
            except Exception:
                self._conn = None

        if not self._database_url:
            raise RuntimeError("no EOS_DATABASE_URL configured for capability handler")

        self._conn = psycopg2.connect(self._database_url)
        self._conn.autocommit = False
        return self._conn

    def _noop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Acknowledge a signal without external action."""
        return {
            "received": True,
            "table_name": params.get("table_name", ""),
            "user_id": params.get("user_id", ""),
            "row_id": params.get("row_id", ""),
        }

    def _create_contact(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        contact_id = insert_contact(conn, params)
        return {"contact_id": contact_id}

    def _create_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        deal_id = insert_deal(conn, params)
        return {"deal_id": deal_id}

    def _update_deal_stage(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        return update_deal_stage(conn, params)

    def _log_activity(self, params: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        activity_id = insert_activity(conn, params)
        return {"activity_id": activity_id}
