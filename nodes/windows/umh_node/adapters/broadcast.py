"""Broadcast adapter — runs FFmpeg engine on the local node.

Exposes start, stop, status, start_composite, switch_scene as mesh
capabilities.  The engine runs locally (remote node or any node with FFmpeg);
the VPS control plane drives it over the mesh WS transport.

Implements execute_async() so the daemon bypasses the 8s sync timeout —
broadcast operations (especially start) need 5-30s for FFmpeg init.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adapters.broadcast.engine import BroadcastEngine  # noqa: E402
from adapters.broadcast.scene_model import (  # noqa: E402
    CompositeConfig,
    Scene,
    SourceEntry,
    SourceLayout,
)

logger = logging.getLogger(__name__)


class BroadcastAdapter:
    """Mesh-capable broadcast adapter wrapping BroadcastEngine.

    Designed for the remote node daemon but works on any node with FFmpeg.
    Uses execute_async() — the daemon detects this and awaits directly
    instead of routing through run_in_executor with a short timeout.
    """

    def __init__(self) -> None:
        self._engine = BroadcastEngine()
        self._engine.set_health_callback(self._on_health)
        self._latest_health: dict[str, Any] = {}

    def _on_health(self, health: dict[str, Any]) -> None:
        self._latest_health = health

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Sync fallback — wraps execute_async for non-async callers."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.execute_async(operation, params))
                    return future.result(timeout=60)
            return loop.run_until_complete(self.execute_async(operation, params))
        except Exception as exc:
            logger.error("[BroadcastAdapter] sync execute failed: %s", exc)
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    async def execute_async(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Async execution — preferred path from the remote node daemon."""
        op = operation.split(".")[-1] if "." in operation else operation

        dispatch = {
            "start": self._start,
            "stop": self._stop,
            "status": self._status,
            "start_composite": self._start_composite,
            "switch_scene": self._switch_scene,
            "health": self._health,
        }

        handler = dispatch.get(op)
        if handler is None:
            return {"success": False, "error": f"unknown broadcast operation: {operation}"}

        try:
            result = await handler(params)
            return {"success": True, **result}
        except Exception as exc:
            logger.error("[BroadcastAdapter] %s failed: %s", operation, exc)
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    async def _start(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._engine.state == "live":
            return {"error": "already broadcasting", "state": "live"}

        config = {
            "source_type": params.get("source_type", "test_pattern"),
            "source_config": params.get("source_config", {}),
            "output_url": params["output_url"],
            "video_codec": params.get("video_codec", "libx264"),
            "video_bitrate": params.get("video_bitrate", "4500k"),
            "audio_codec": params.get("audio_codec", "aac"),
            "audio_bitrate": params.get("audio_bitrate", "128k"),
            "resolution": params.get("resolution", "1920x1080"),
            "fps": params.get("fps", 30),
            "keyframe_interval": params.get("keyframe_interval", 2),
            "preset": params.get("preset", "veryfast"),
            "container_format": params.get("container_format", "flv"),
        }

        ok = await self._engine.start(config)
        if not ok:
            raise RuntimeError("engine start failed")

        return {
            "state": self._engine.state,
            "pid": self._engine._lifecycle.pid if self._engine._lifecycle else None,
        }

    async def _stop(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._engine.state == "idle":
            return {"state": "idle", "already_stopped": True}
        code = await self._engine.stop()
        return {"state": self._engine.state, "exit_code": code}

    async def _status(self, params: dict[str, Any]) -> dict[str, Any]:
        status = self._engine.get_status()
        status["latest_health"] = self._latest_health
        return status

    async def _start_composite(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._engine.state == "live":
            return {"error": "already broadcasting", "state": "live"}

        config = CompositeConfig(
            sources=[SourceEntry(**s) for s in params.get("sources", [])],
            scenes=[
                Scene(
                    scene_id=s["scene_id"],
                    name=s["name"],
                    source_layouts={
                        k: SourceLayout(**v)
                        for k, v in s.get("source_layouts", {}).items()
                    },
                )
                for s in params.get("scenes", [])
            ],
            active_scene_id=params.get("active_scene_id"),
            output_url=params["output_url"],
            canvas_width=params.get("canvas_width", 1920),
            canvas_height=params.get("canvas_height", 1080),
            fps=params.get("fps", 30),
            video_codec=params.get("video_codec", "libx264"),
            video_bitrate=params.get("video_bitrate", "4500k"),
            audio_codec=params.get("audio_codec", "aac"),
            audio_bitrate=params.get("audio_bitrate", "128k"),
            keyframe_interval=params.get("keyframe_interval", 2),
            preset=params.get("preset", "veryfast"),
            container_format=params.get("container_format", "flv"),
        )

        ok = await self._engine.start_composite(config)
        if not ok:
            raise RuntimeError("composite start failed")

        return {
            "state": self._engine.state,
            "pid": self._engine._lifecycle.pid if self._engine._lifecycle else None,
            "active_scene_id": params.get("active_scene_id"),
            "source_count": len(params.get("sources", [])),
            "scene_count": len(params.get("scenes", [])),
        }

    async def _switch_scene(self, params: dict[str, Any]) -> dict[str, Any]:
        scene_id = params.get("scene_id")
        if not scene_id:
            raise ValueError("scene_id is required")
        result = await self._engine.switch_scene(scene_id)
        if not result.get("success"):
            raise RuntimeError(result.get("error", "scene switch failed"))
        return result

    async def _health(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "state": self._engine.state,
            "health": self._latest_health,
        }
