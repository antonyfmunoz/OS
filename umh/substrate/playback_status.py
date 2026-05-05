"""Shared playback status snapshot shape for voice transports.

This module defines a single JSON-friendly shape that both the Discord
voice transport and the meeting voice transport emit via their
``status_report()`` methods. Operators get one contract per transport
for bounded playback observability.

Never raises. Additive only. ``max_depth`` is always 1 by design.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

PLAYBACK_REASONS = (
    "another_utterance_playing",
    "tts_unavailable",
    "vc_unavailable",
    "ffmpeg_missing",
    "disabled_by_env",
    "empty_text",
    "playback_error",
    "no_sink_attached",
    "ok",
)


@dataclass
class PlaybackStatusSnapshot:
    transport: str  # "discord" | "meeting"
    mode: str  # "transcript_only" | "attached" | "attached_degraded"
    attached: bool
    enabled: bool
    busy: bool
    depth: int  # current outstanding (0 or 1)
    max_depth: int  # always 1 for now (bounded)
    attempt_count: int
    by_status: dict[str, int] = field(default_factory=dict)
    last_result: Optional[dict] = None
    recent: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_playback_status_snapshot(
    *,
    transport: str,
    mode: str,
    attached: bool,
    enabled: bool,
    busy: bool = False,
    depth: int = 0,
    max_depth: int = 1,
    attempt_count: int = 0,
    by_status: Optional[dict[str, int]] = None,
    last_result: Optional[dict] = None,
    recent: Optional[list[dict]] = None,
) -> PlaybackStatusSnapshot:
    return PlaybackStatusSnapshot(
        transport=transport,
        mode=mode,
        attached=attached,
        enabled=enabled,
        busy=busy,
        depth=depth,
        max_depth=max_depth,
        attempt_count=attempt_count,
        by_status=dict(by_status or {}),
        last_result=last_result,
        recent=list(recent or []),
    )


def aggregate_by_status(history_rows: list[dict]) -> dict[str, int]:
    """Count occurrences of the 'status' field across history rows."""
    out: dict[str, int] = {}
    for row in history_rows or []:
        status = (row or {}).get("status") if isinstance(row, dict) else None
        if not status:
            continue
        out[status] = out.get(status, 0) + 1
    return out


__all__ = [
    "PLAYBACK_REASONS",
    "PlaybackStatusSnapshot",
    "make_playback_status_snapshot",
    "aggregate_by_status",
]
