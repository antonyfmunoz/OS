"""Broadcast capability handler — implements CapabilityHandler Protocol."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from substrate.sockets.envelopes import CapabilityRequest, CapabilityResponse
from substrate.sockets.protocols import CapabilityDescriptor, CapabilityHealth

from adapters.broadcast.engine import BroadcastEngine
from .manifest import CAPABILITY_DESCRIPTORS, INTEGRATION_ID

logger = logging.getLogger(__name__)


class BroadcastCapabilityHandler:
    """Handles capability requests by driving BroadcastEngine in-process.

    Satisfies CapabilityHandler Protocol structurally.
    Supports start, stop, status.

    The engine is async; this handler bridges to sync via a dedicated
    event loop per call. For direct async access, use .engine directly.
    """

    def __init__(self, engine: BroadcastEngine | None = None) -> None:
        self._engine = engine or BroadcastEngine()

    @property
    def engine(self) -> BroadcastEngine:
        return self._engine

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return list(CAPABILITY_DESCRIPTORS)

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        t0 = time.monotonic()
        handler_map = {
            "start": self._start,
            "stop": self._stop,
            "status": self._status,
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
            logger.error(
                "[BroadcastCapabilityHandler] %s failed: %s",
                request.capability_name, exc,
            )
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"{request.capability_name} failed",
                raw_error=f"{type(exc).__name__}: {exc}",
                latency_ms=latency,
            )

    async def handle_capability_async(
        self, request: CapabilityRequest,
    ) -> CapabilityResponse:
        """Async variant for callers already in an event loop."""
        t0 = time.monotonic()
        handler_map = {
            "start": self._start_async,
            "stop": self._stop_async,
            "status": self._status_sync,
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
            if asyncio.iscoroutinefunction(handler):
                result = await handler(request.params)
            else:
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
        status = self._engine.get_status()
        state = status.get("state", "idle")
        if state == "live":
            return CapabilityHealth(
                integration_id=INTEGRATION_ID,
                status="healthy",
                detail=f"broadcasting, pid={status.get('pid')}",
            )
        if state == "error":
            return CapabilityHealth(
                integration_id=INTEGRATION_ID,
                status="unavailable",
                detail="engine in error state",
            )
        return CapabilityHealth(
            integration_id=INTEGRATION_ID,
            status="healthy",
            detail="idle, ready to broadcast",
        )

    def _start(self, params: dict[str, Any]) -> dict[str, Any]:
        config = self._build_config(params)
        ok = asyncio.run(self._engine.start(config))
        if not ok:
            raise RuntimeError("engine start failed (CPU gate or already live)")
        return {"pid": self._engine.get_status().get("pid"), "state": self._engine.state}

    async def _start_async(self, params: dict[str, Any]) -> dict[str, Any]:
        config = self._build_config(params)
        ok = await self._engine.start(config)
        if not ok:
            raise RuntimeError("engine start failed (CPU gate or already live)")
        return {"pid": self._engine.get_status().get("pid"), "state": self._engine.state}

    def _stop(self, params: dict[str, Any]) -> dict[str, Any]:
        code = asyncio.run(self._engine.stop())
        return {"exit_code": code, "state": self._engine.state}

    async def _stop_async(self, params: dict[str, Any]) -> dict[str, Any]:
        code = await self._engine.stop()
        return {"exit_code": code, "state": self._engine.state}

    def _status(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._engine.get_status()

    def _status_sync(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._engine.get_status()

    def _build_config(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": params.get("source_type", "test_pattern"),
            "source_config": params.get("source_config", {}),
            "output_url": params["output_url"],
            "resolution": params.get("resolution", "1920x1080"),
            "video_bitrate": params.get("video_bitrate", "4500k"),
            "fps": params.get("fps", 30),
            "preset": params.get("preset", "veryfast"),
        }
