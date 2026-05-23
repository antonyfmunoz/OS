"""Capability socket — bidirectional execution for integration capabilities."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
from substrate.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHandler,
    CapabilityHealth,
)

logger = logging.getLogger(__name__)


class CapabilitySocket:
    """Routes capability requests to registered integration handlers.

    When the pipeline's WorkPacketExecutor dispatches to an integration
    adapter, the adapter calls this socket's request() method. The socket
    looks up the handler, calls handle_capability(), and normalizes
    errors at the boundary (raw exception preserved in raw_error).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, CapabilityHandler] = {}
        self._catalogs: dict[str, list[CapabilityDescriptor]] = {}

    def register_handler(self, handler: CapabilityHandler) -> None:
        """Register an integration's capability handler.

        Raises ValueError if integration_id is already registered.
        """
        iid = handler.integration_id
        if iid in self._handlers:
            raise ValueError(f"integration '{iid}' already registered as capability handler")
        self._handlers[iid] = handler
        self._catalogs[iid] = handler.describe_capabilities()
        logger.info(
            "capability handler registered: %s (%d capabilities)",
            iid,
            len(self._catalogs[iid]),
        )

    def request(self, req: CapabilityRequest) -> CapabilityResponse:
        """Send a capability request to the registered handler.

        Normalizes all handler exceptions into CapabilityResponse with
        success=False. The raw exception is preserved in raw_error for
        integration-side debugging (e.g., "NotionAPIError: 429").
        """
        handler = self._handlers.get(req.integration_id)
        if handler is None:
            return CapabilityResponse(
                request_id=req.request_id,
                success=False,
                error=f"no handler registered for '{req.integration_id}'",
            )

        t0 = time.monotonic()
        try:
            response = handler.handle_capability(req)
            return response
        except Exception as exc:
            duration = (time.monotonic() - t0) * 1000
            logger.error(
                "capability handler '%s' raised %s: %s",
                req.integration_id,
                type(exc).__name__,
                exc,
            )
            return CapabilityResponse(
                request_id=req.request_id,
                success=False,
                error=f"capability failed: {req.capability_name}",
                raw_error=f"{type(exc).__name__}: {exc}",
                latency_ms=duration,
            )

    def unregister_handler(self, integration_id: str) -> None:
        """Remove an integration's capability handler. Idempotent."""
        if integration_id in self._handlers:
            del self._handlers[integration_id]
            del self._catalogs[integration_id]
            logger.info("capability handler unregistered: %s", integration_id)

    def capability_catalog(self) -> dict[str, list[CapabilityDescriptor]]:
        return dict(self._catalogs)

    def health_check(self, integration_id: str) -> CapabilityHealth:
        handler = self._handlers.get(integration_id)
        if handler is None:
            return CapabilityHealth(
                integration_id=integration_id,
                status="unavailable",
                detail="not registered",
            )
        try:
            return handler.health()
        except Exception as exc:
            return CapabilityHealth(
                integration_id=integration_id,
                status="unavailable",
                detail=f"health check failed: {exc}",
            )
