"""EOS capability handler — implements CapabilityHandler Protocol."""

from __future__ import annotations

import logging
import time
from typing import Any

from services.umh.sockets.envelopes import CapabilityRequest, CapabilityResponse
from services.umh.sockets.protocols import CapabilityDescriptor, CapabilityHealth

from .manifest import CAPABILITY_DESCRIPTORS, INTEGRATION_ID

logger = logging.getLogger(__name__)


class EOSCapabilityHandler:
    """Handles capability requests for the EOS integration.

    Satisfies CapabilityHandler Protocol structurally.
    Phase 1: noop only.
    """

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return list(CAPABILITY_DESCRIPTORS)

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        t0 = time.monotonic()
        handler_map = {
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
        return CapabilityHealth(integration_id=INTEGRATION_ID, status="healthy")

    def _noop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Acknowledge a signal without external action."""
        return {
            "received": True,
            "table_name": params.get("table_name", ""),
            "org_id": params.get("org_id", ""),
            "row_id": params.get("row_id", ""),
        }
