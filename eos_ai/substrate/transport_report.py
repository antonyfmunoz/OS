"""
Unified transport report — bounded read-only join across the local PTT,
the Discord voice transport, and the shared voice/audio/operator state.

Purpose
-------
Both new transport fronts (workstation push-to-talk and Discord voice
adapter) reuse the SAME bounded seam (`inject_transcript → voice_session
→ responder → SPEAK_TEXT`). This module exists so an operator can ask one
question and get one answer:

    "What is the current state of every transport feeding the voice loop?"

It is intentionally NOT a new abstraction. It just joins existing read-only
views from:

    eos_ai.substrate.stt_producer.stt_workstation_readiness
    eos_ai.substrate.ptt_binding.real_capture_report
    eos_ai.substrate.discord_voice_transport.get_default_discord_voice_transport
    eos_ai.substrate.result_query.audio_loop_snapshot
    eos_ai.substrate.result_query.recent_audio_loop_transcripts
    eos_ai.substrate.result_query.recent_voice_sessions
    eos_ai.substrate.result_query.operator_state_snapshot

Best-effort. Never raises. JSON-friendly.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, Optional


def _log(msg: str) -> None:
    print(f"[substrate.transport_report] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(call, default):
    try:
        return call()
    except Exception as e:  # noqa: BLE001
        _log(f"safe call failed: {e}")
        return default


def _group_transcripts_by_source(transcripts: list[dict]) -> dict[str, int]:
    """Count audio_loop transcripts by their source tag.

    The source tag distinguishes transports that all flow through the same
    seam: `local_stt`, `push_to_talk`, `discord_voice`, `manual`, etc.
    """
    out: dict[str, int] = {}
    for entry in transcripts or []:
        src = (entry.get("source") if isinstance(entry, dict) else None) or "unknown"
        out[src] = out.get(src, 0) + 1
    return out


def unified_transport_report(
    node_id: Optional[str] = None,
    *,
    transcript_limit: int = 10,
    discord_guild_id: Optional[str] = None,
    discord_channel_id: Optional[str] = None,
    meeting_platform: Optional[str] = None,
    meeting_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build the cross-transport report.

    Parameters
    ----------
    node_id:
        The local workstation node to focus on (e.g. ``antony-workstation``).
        Pass ``None`` to get a global view (no per-node audio loop / operator
        state filter; PTT readiness is still global).
    transcript_limit:
        Newest-first transcript ring-buffer rows to include for ``node_id``.
    discord_guild_id, discord_channel_id:
        Optional discord context. When set, the report includes the
        corresponding `DiscordVoiceTransport.status_report()`. When neither
        is set, the report uses the default transport instance.
    """
    # ── Local workstation PTT ───────────────────────────────────────────
    workstation: dict[str, Any] = {}
    workstation["readiness"] = _safe(
        lambda: __import__(
            "eos_ai.substrate.stt_producer", fromlist=["stt_workstation_readiness"]
        ).stt_workstation_readiness(),
        default={"classification": "unknown", "reason": "stt_producer unavailable"},
    )
    workstation["real_capture_report"] = _safe(
        lambda: __import__(
            "eos_ai.substrate.ptt_binding", fromlist=["real_capture_report"]
        ).real_capture_report(node_id=node_id, limit=5),
        default={"history": [], "history_count": 0, "by_classification": {}},
    )

    # ── Discord transport ───────────────────────────────────────────────
    discord_status: dict[str, Any] = {}
    try:
        from eos_ai.substrate.discord_voice_transport import (
            get_default_discord_voice_transport,
        )

        transport = get_default_discord_voice_transport(
            guild_id=discord_guild_id,
            channel_id=discord_channel_id,
        )
        discord_status = transport.status_report(history_limit=transcript_limit)
    except Exception as e:  # noqa: BLE001
        discord_status = {
            "node_id": None,
            "mode": "unavailable",
            "detail": f"discord_voice_transport unavailable: {e}",
        }

    # ── Meeting transport ───────────────────────────────────────────────
    meeting_status: dict[str, Any] = {}
    try:
        from eos_ai.substrate.meeting_transport import (
            get_default_meeting_transport,
        )

        meeting_transport = get_default_meeting_transport(
            platform=meeting_platform,
            meeting_id=meeting_id,
        )
        meeting_status = meeting_transport.status_report(history_limit=transcript_limit)
    except Exception as e:  # noqa: BLE001
        meeting_status = {
            "node_id": None,
            "mode": "unavailable",
            "detail": f"meeting_transport unavailable: {e}",
        }

    # ── Shared voice substrate (read-only joins) ────────────────────────
    voice_sessions = _safe(
        lambda: __import__(
            "eos_ai.substrate.result_query", fromlist=["recent_voice_sessions"]
        ).recent_voice_sessions(limit=5, node_id=node_id),
        default=[],
    )
    audio_loop = _safe(
        lambda: __import__(
            "eos_ai.substrate.result_query", fromlist=["audio_loop_snapshot"]
        ).audio_loop_snapshot(node_id=node_id),
        default={"node_id": node_id, "count": 0, "states": [], "stats": {}},
    )
    operator_state = _safe(
        lambda: __import__(
            "eos_ai.substrate.result_query", fromlist=["operator_state_snapshot"]
        ).operator_state_snapshot(node_id=node_id),
        default={"node_id": node_id, "count": 0, "states": [], "stats": {}},
    )

    # Per-node transcript ring buffer (only meaningful when node_id is set).
    local_transcripts: list[dict] = []
    if node_id:
        local_transcripts = _safe(
            lambda: __import__(
                "eos_ai.substrate.result_query",
                fromlist=["recent_audio_loop_transcripts"],
            ).recent_audio_loop_transcripts(node_id, limit=transcript_limit),
            default=[],
        )

    # Discord transport runs on its own discord_vc_* node — pull its
    # transcript ring buffer too so the unified view shows both feeds.
    discord_transcripts: list[dict] = []
    discord_node_id = (
        discord_status.get("node_id") if isinstance(discord_status, dict) else None
    )
    if discord_node_id:
        discord_transcripts = _safe(
            lambda: __import__(
                "eos_ai.substrate.result_query",
                fromlist=["recent_audio_loop_transcripts"],
            ).recent_audio_loop_transcripts(discord_node_id, limit=transcript_limit),
            default=[],
        )

    # Meeting transport runs on its own meeting_<platform>_* node — pull
    # its transcript ring buffer too so the unified view shows all feeds.
    meeting_transcripts: list[dict] = []
    meeting_node_id = (
        meeting_status.get("node_id") if isinstance(meeting_status, dict) else None
    )
    if meeting_node_id:
        meeting_transcripts = _safe(
            lambda: __import__(
                "eos_ai.substrate.result_query",
                fromlist=["recent_audio_loop_transcripts"],
            ).recent_audio_loop_transcripts(meeting_node_id, limit=transcript_limit),
            default=[],
        )

    # Aggregate transcript-by-source counts across all nodes so the
    # operator can see at a glance how many entries came from each
    # transport in the bounded seam.
    by_source: dict[str, int] = {}
    for src, n in _group_transcripts_by_source(local_transcripts).items():
        by_source[src] = by_source.get(src, 0) + n
    for src, n in _group_transcripts_by_source(discord_transcripts).items():
        by_source[src] = by_source.get(src, 0) + n
    for src, n in _group_transcripts_by_source(meeting_transcripts).items():
        by_source[src] = by_source.get(src, 0) + n

    # ── Playback aggregates across transports ──────────────────────────
    discord_pb: Optional[dict] = None
    meeting_pb: Optional[dict] = None
    try:
        if isinstance(discord_status, dict):
            discord_pb = discord_status.get("playback_status")
    except Exception:  # noqa: BLE001
        discord_pb = None
    try:
        if isinstance(meeting_status, dict):
            meeting_pb = meeting_status.get("playback_status")
    except Exception:  # noqa: BLE001
        meeting_pb = None

    merged_by_status: dict[str, int] = {}
    for pb in (discord_pb, meeting_pb):
        try:
            if isinstance(pb, dict):
                bs = pb.get("by_status") or {}
                if isinstance(bs, dict):
                    for k, v in bs.items():
                        try:
                            merged_by_status[k] = merged_by_status.get(k, 0) + int(v)
                        except Exception:  # noqa: BLE001
                            continue
        except Exception:  # noqa: BLE001
            continue

    playback_aggregates = {
        "by_transport": {
            "discord": discord_pb or None,
            "meeting": meeting_pb or None,
        },
        "by_status": merged_by_status,
    }

    return {
        "node_id": node_id,
        "discord_node_id": discord_node_id,
        "meeting_node_id": meeting_node_id,
        "generated_at": _utcnow_iso(),
        "workstation": workstation,
        "discord_transport": discord_status,
        "meeting_transport": meeting_status,
        "voice_sessions_recent": voice_sessions,
        "audio_loop_snapshot": audio_loop,
        "operator_state_snapshot": operator_state,
        "transcripts": {
            "local": local_transcripts,
            "discord": discord_transcripts,
            "meeting": meeting_transcripts,
            "by_source": by_source,
        },
        "playback_aggregates": playback_aggregates,
    }


__all__ = ["unified_transport_report"]
