"""Broadcast engine — owns FFmpeg subprocess lifecycle, config->args, health.

Runs FFmpeg with ``-progress pipe:1`` for structured progress parsing.
The muxed output goes to the RTMP/file URL.  Stdout carries key=value
progress lines (frame, fps, bitrate, drop_frames, out_time_ms).
Stderr is logged but NOT scraped for metrics.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from adapters.broadcast.ffmpeg_args import build_args
from adapters.broadcast.process_lifecycle import ProcessLifecycle

logger = logging.getLogger(__name__)


class BroadcastHealth:
    """Parsed health metrics from FFmpeg progress output."""

    def __init__(self) -> None:
        self.frame: int = 0
        self.fps: float = 0.0
        self.bitrate_kbps: float = 0.0
        self.drop_frames: int = 0
        self.out_time_ms: int = 0
        self.speed: str = "0x"
        self.total_size_bytes: int = 0
        self.started_at: float = 0.0

    @property
    def uptime_s(self) -> float:
        if self.started_at <= 0:
            return 0.0
        return time.time() - self.started_at

    @property
    def drop_percentage(self) -> float:
        if self.frame <= 0:
            return 0.0
        return (self.drop_frames / self.frame) * 100.0

    @property
    def status_tier(self) -> str:
        if self.drop_percentage > 5.0:
            return "CRITICAL"
        if self.drop_percentage > 1.0:
            return "WARNING"
        return "HEALTHY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "fps": self.fps,
            "bitrate_kbps": self.bitrate_kbps,
            "drop_frames": self.drop_frames,
            "out_time_ms": self.out_time_ms,
            "speed": self.speed,
            "total_size_bytes": self.total_size_bytes,
            "uptime_s": round(self.uptime_s, 1),
            "drop_percentage": round(self.drop_percentage, 2),
            "status_tier": self.status_tier,
        }

    def parse_progress_line(self, line: str) -> None:
        """Parse a single key=value line from FFmpeg -progress pipe:1."""
        if "=" not in line:
            return
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        try:
            if key == "frame":
                self.frame = int(value)
            elif key == "fps":
                self.fps = float(value)
            elif key == "bitrate":
                if value.endswith("kbits/s"):
                    self.bitrate_kbps = float(value.replace("kbits/s", "").strip())
            elif key == "drop_frames":
                self.drop_frames = int(value)
            elif key == "out_time_ms":
                self.out_time_ms = int(value)
            elif key == "speed":
                self.speed = value
            elif key == "total_size":
                self.total_size_bytes = int(value)
        except (ValueError, TypeError):
            pass


class BroadcastEngine:
    """High-level broadcast engine wrapping FFmpeg as a subprocess."""

    def __init__(self) -> None:
        self._lifecycle: ProcessLifecycle | None = None
        self._health = BroadcastHealth()
        self._config: dict[str, Any] = {}
        self._on_health: Callable[[dict[str, Any]], None] | None = None
        self._state: str = "idle"

    @property
    def state(self) -> str:
        return self._state

    @property
    def health(self) -> BroadcastHealth:
        return self._health

    def set_health_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        self._on_health = cb

    async def start(self, config: dict[str, Any]) -> bool:
        """Start broadcasting with the given config.  Returns False on failure."""
        if self._state == "live":
            logger.warning("[BroadcastEngine] already live, stop first")
            return False

        self._config = config
        self._health = BroadcastHealth()

        try:
            cmd = build_args(
                source_type=config.get("source_type", "test_pattern"),
                source_config=config.get("source_config", {}),
                output_url=config["output_url"],
                video_codec=config.get("video_codec", "libx264"),
                video_bitrate=config.get("video_bitrate", "4500k"),
                audio_codec=config.get("audio_codec", "aac"),
                audio_bitrate=config.get("audio_bitrate", "128k"),
                resolution=config.get("resolution", "1920x1080"),
                fps=config.get("fps", 30),
                keyframe_interval=config.get("keyframe_interval", 2),
                preset=config.get("preset", "veryfast"),
                container_format=config.get("container_format", "flv"),
            )
        except (KeyError, ValueError) as exc:
            logger.error("[BroadcastEngine] bad config: %s", exc)
            self._state = "error"
            return False

        logger.info("[BroadcastEngine] ffmpeg cmd: %s", " ".join(cmd))

        self._lifecycle = ProcessLifecycle(
            cmd,
            caller="broadcast_engine",
            on_stdout=self._handle_stdout,
            on_stderr=self._handle_stderr,
            on_exit=self._handle_exit,
            teardown_timeout=5.0,
        )

        self._state = "starting"
        ok = await self._lifecycle.start()
        if not ok:
            self._state = "error"
            return False

        self._health.started_at = time.time()
        self._state = "live"
        return True

    async def stop(self) -> int | None:
        """Idempotent stop.  Returns exit code."""
        if self._state == "idle":
            return None

        self._state = "stopping"
        code = None
        if self._lifecycle:
            code = await self._lifecycle.stop()
            self._lifecycle = None

        self._state = "idle"
        return code

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "health": self._health.to_dict() if self._state == "live" else None,
            "config": self._config if self._state == "live" else None,
            "pid": self._lifecycle.pid if self._lifecycle else None,
        }

    def _handle_stdout(self, line: str) -> None:
        """Parse structured -progress output from FFmpeg."""
        self._health.parse_progress_line(line)
        if self._on_health and line.startswith("progress="):
            try:
                self._on_health(self._health.to_dict())
            except Exception:
                logger.debug("[BroadcastEngine] health callback error")

    def _handle_stderr(self, line: str) -> None:
        if "error" in line.lower() or "fatal" in line.lower():
            logger.error("[BroadcastEngine:stderr] %s", line)
        else:
            logger.debug("[BroadcastEngine:stderr] %s", line)

    def _handle_exit(self, code: int | None) -> None:
        logger.info("[BroadcastEngine] FFmpeg exited code=%s", code)
        if self._state != "stopping":
            self._state = "error"
