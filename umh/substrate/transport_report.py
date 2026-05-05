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

    umh.substrate.stt_producer.stt_workstation_readiness
    umh.substrate.ptt_binding.real_capture_report
    umh.substrate.discord_voice_transport.get_default_discord_voice_transport
    umh.substrate.result_query.audio_loop_snapshot
    umh.substrate.result_query.recent_audio_loop_transcripts
    umh.substrate.result_query.recent_voice_sessions
    umh.substrate.result_query.operator_state_snapshot

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
            "umh.substrate.stt_producer", fromlist=["stt_workstation_readiness"]
        ).stt_workstation_readiness(),
        default={"classification": "unknown", "reason": "stt_producer unavailable"},
    )
    workstation["real_capture_report"] = _safe(
        lambda: __import__(
            "umh.substrate.ptt_binding", fromlist=["real_capture_report"]
        ).real_capture_report(node_id=node_id, limit=5),
        default={"history": [], "history_count": 0, "by_classification": {}},
    )

    # ── Discord transport ───────────────────────────────────────────────
    discord_status: dict[str, Any] = {}
    try:
        from umh.substrate.discord_voice_transport import (
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
        from umh.substrate.meeting_transport import (
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
            "umh.substrate.result_query", fromlist=["recent_voice_sessions"]
        ).recent_voice_sessions(limit=5, node_id=node_id),
        default=[],
    )
    audio_loop = _safe(
        lambda: __import__(
            "umh.substrate.result_query", fromlist=["audio_loop_snapshot"]
        ).audio_loop_snapshot(node_id=node_id),
        default={"node_id": node_id, "count": 0, "states": [], "stats": {}},
    )
    operator_state = _safe(
        lambda: __import__(
            "umh.substrate.result_query", fromlist=["operator_state_snapshot"]
        ).operator_state_snapshot(node_id=node_id),
        default={"node_id": node_id, "count": 0, "states": [], "stats": {}},
    )

    # Per-node transcript ring buffer (only meaningful when node_id is set).
    local_transcripts: list[dict] = []
    if node_id:
        local_transcripts = _safe(
            lambda: __import__(
                "umh.substrate.result_query",
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
                "umh.substrate.result_query",
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
                "umh.substrate.result_query",
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

    # ── Meeting intelligence (bounded, never raises) ───────────────────
    meeting_intel: dict[str, Any] = {
        "summary": None,
        "recent_interventions": [],
        "memory_extracted_count": 0,
    }
    try:
        from umh.substrate.meeting_intelligence import (
            intelligence_report_block,
        )

        meeting_intel = intelligence_report_block(
            node_id=meeting_node_id,
            meeting_id=meeting_id,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"meeting_intelligence block failed: {e}")

    report = {
        "node_id": node_id,
        "discord_node_id": discord_node_id,
        "meeting_node_id": meeting_node_id,
        "meeting_intelligence": meeting_intel,
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

    # ── Additive operator-facing augmentations ─────────────────────────
    try:
        report["continuity"] = _continuity_block(report)
        report["ingress"] = _ingress_block(report)
        report["playback_last"] = _playback_last_block(report)
        report["meet_bridges"] = _meet_bridges_block(report)
        report["supervision_hints"] = _supervision_hints_block(report)
        report["pseudo_live"] = _pseudo_live_block()
    except Exception as e:  # noqa: BLE001
        _log(f"augmentation failed: {e}")
        report.setdefault("continuity", _empty_continuity())
        report.setdefault("ingress", _empty_ingress())
        report.setdefault("playback_last", _empty_playback_last())
        report.setdefault("meet_bridges", [])
        report.setdefault("supervision_hints", [])
        report.setdefault("pseudo_live", _empty_pseudo_live())
        report["continuity_error"] = str(e)[:200]

    return report


def _empty_pseudo_live() -> dict:
    return {
        "ingress_enabled": False,
        "tts_reply_enabled": False,
        "allowlists": {"guilds": [], "channels": [], "users": []},
        "reply_max_chars": 0,
        "recent_events": [],
        "transcript_source": "discord_text",
    }


def _pseudo_live_block() -> dict:
    try:
        from umh.substrate.discord_text_transport import pseudo_live_status

        return pseudo_live_status()
    except Exception as e:  # noqa: BLE001
        _log(f"_pseudo_live_block failed: {e}")
        out = _empty_pseudo_live()
        out["error"] = str(e)[:200]
        return out


# ──────────────────────────────────────────────────────────────────────
# Augmentation helpers — all best-effort, never raise to caller
# ──────────────────────────────────────────────────────────────────────


def _empty_continuity() -> dict:
    return {
        "shared_role_slug": None,
        "active_transports": [],
        "transports_seen": [],
        "common_node_role_count": 0,
        "any_active_session": False,
    }


def _empty_ingress() -> dict:
    return {
        "discord": {"last_at": None, "count": 0},
        "meeting": {"last_at": None, "count": 0},
        "local": {"last_at": None, "count": 0},
        "by_source_total": 0,
    }


def _empty_playback_last() -> dict:
    return {
        "discord": {"at": None, "status": None},
        "meeting": {"at": None, "status": None},
    }


def _continuity_block(report: dict) -> dict:
    out = _empty_continuity()
    try:
        dt = report.get("discord_transport") or {}
        mt = report.get("meeting_transport") or {}
        ws = report.get("workstation") or {}
        transports_seen: list[str] = []
        active: list[str] = []
        roles: list[str] = []

        # workstation: "active" if any capture history or classification real_ready
        wsr = ws.get("readiness") or {}
        if wsr:
            transports_seen.append("workstation")
            cls = wsr.get("classification")
            hist_count = (ws.get("real_capture_report") or {}).get("history_count") or 0
            if cls in ("real_ready", "real_capture_ready") or hist_count > 0:
                active.append("workstation")

        if isinstance(dt, dict) and dt.get("mode") != "unavailable":
            transports_seen.append("discord")
            if int(dt.get("active_session_count") or 0) > 0:
                active.append("discord")
            rs = dt.get("role_slug")
            if isinstance(rs, str) and rs:
                roles.append(rs)

        if isinstance(mt, dict) and mt.get("mode") != "unavailable":
            transports_seen.append("meeting")
            if int(mt.get("active_session_count") or 0) > 0:
                active.append("meeting")
            rs = mt.get("role_slug")
            if isinstance(rs, str) and rs:
                roles.append(rs)

        shared_role: Optional[str] = None
        common_count = 0
        if roles:
            counts: dict[str, int] = {}
            for r in roles:
                counts[r] = counts.get(r, 0) + 1
            shared_role, common_count = max(counts.items(), key=lambda kv: kv[1])

        out["shared_role_slug"] = shared_role
        out["active_transports"] = active
        out["transports_seen"] = transports_seen
        out["common_node_role_count"] = common_count
        out["any_active_session"] = bool(active)
    except Exception as e:  # noqa: BLE001
        _log(f"_continuity_block failed: {e}")
    return out


def _latest_occurred_at(entries: list[dict]) -> Optional[str]:
    best: Optional[str] = None
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        ts = e.get("occurred_at") or e.get("ts")
        if isinstance(ts, str) and ts:
            if best is None or ts > best:
                best = ts
    return best


def _ingress_block(report: dict) -> dict:
    out = _empty_ingress()
    try:
        tr = report.get("transcripts") or {}
        local = tr.get("local") or []
        discord = tr.get("discord") or []
        meeting = tr.get("meeting") or []
        out["local"] = {
            "last_at": _latest_occurred_at(local),
            "count": len(local),
        }
        out["discord"] = {
            "last_at": _latest_occurred_at(discord),
            "count": len(discord),
        }
        out["meeting"] = {
            "last_at": _latest_occurred_at(meeting),
            "count": len(meeting),
        }
        by_src = tr.get("by_source") or {}
        try:
            out["by_source_total"] = sum(int(v) for v in by_src.values())
        except Exception:  # noqa: BLE001
            out["by_source_total"] = 0
    except Exception as e:  # noqa: BLE001
        _log(f"_ingress_block failed: {e}")
    return out


def _playback_last_block(report: dict) -> dict:
    out = _empty_playback_last()
    try:
        pa = (report.get("playback_aggregates") or {}).get("by_transport") or {}
        for t in ("discord", "meeting"):
            pb = pa.get(t) or {}
            last = pb.get("last_result") if isinstance(pb, dict) else None
            if isinstance(last, dict):
                out[t] = {
                    "at": last.get("at") or last.get("occurred_at"),
                    "status": last.get("status"),
                }
    except Exception as e:  # noqa: BLE001
        _log(f"_playback_last_block failed: {e}")
    return out


# Average JSONL caption line byte length — used for cheap backlog estimates.
# Tuned against typical caption records {"ts","text","speaker","meeting_code",
# "source","event_id"} which round to ~160-200 bytes. 180 is a conservative
# middle. Skipped entirely for files > 1 MB.
_MEET_BRIDGE_AVG_LINE = 180
_MEET_BRIDGE_BACKLOG_MAX = 1_000_000


def _iso_from_mtime(mtime: float) -> Optional[str]:
    try:
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return None


def _attached_meeting_codes(report: dict) -> set[str]:
    """Best-effort: peek attached meeting sources for their meeting_code.

    Uses the currently-live default meeting transport instance's private
    ``_attached_sources`` dict to reach the live source objects. This is
    intentionally gated behind try/except — if the shape changes we fall
    back to no attached-code info.
    """
    codes: set[str] = set()
    try:
        from umh.substrate.meeting_transport import (
            get_default_meeting_transport,
        )

        t = get_default_meeting_transport()
        live = getattr(t, "_attached_sources", None)
        if not isinstance(live, dict):
            return codes
        for _name, entry in live.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("provider") != "google_meet":
                continue
            src = entry.get("source")
            mc = getattr(src, "meeting_code", None)
            if isinstance(mc, str) and mc:
                # sanitize to match on-disk filename
                try:
                    from umh.substrate.meet_caption_bridge import (
                        sanitize_meeting_code,
                    )

                    codes.add(sanitize_meeting_code(mc))
                except Exception:  # noqa: BLE001
                    codes.add(mc)
    except Exception:  # noqa: BLE001
        pass
    return codes


def _meet_bridges_block(report: dict) -> list[dict]:
    out: list[dict] = []
    try:
        from umh.substrate.meet_caption_bridge import BRIDGE_ROOT

        if not BRIDGE_ROOT.exists():
            return out
        attached_codes = _attached_meeting_codes(report)
        paths = sorted(BRIDGE_ROOT.glob("*.jsonl"))
        for p in paths[:50]:  # bound
            try:
                st = p.stat()
                size = int(st.st_size)
                code = p.stem
                backlog: Optional[int] = None
                if 0 < size <= _MEET_BRIDGE_BACKLOG_MAX:
                    backlog = max(1, size // _MEET_BRIDGE_AVG_LINE)
                out.append(
                    {
                        "meeting_code": code,
                        "path": str(p),
                        "exists": True,
                        "size_bytes": size,
                        "modified_at": _iso_from_mtime(st.st_mtime),
                        "attached_to_transport": code in attached_codes,
                        "backlog_estimate_lines": backlog,
                    }
                )
            except OSError:
                continue
    except Exception as e:  # noqa: BLE001
        _log(f"_meet_bridges_block failed: {e}")
    return out


def _supervision_hints_block(report: dict) -> list[str]:
    hints: list[str] = []
    try:
        dt = report.get("discord_transport") or {}
        mt = report.get("meeting_transport") or {}
        ws = report.get("workstation") or {}
        ingress = report.get("ingress") or {}
        bridges = report.get("meet_bridges") or []

        # discord attachment
        if isinstance(dt, dict) and dt.get("mode") != "unavailable":
            if not dt.get("attached_vc"):
                hints.append("discord: voice client not attached")
            if dt.get("mode") == "transcript_only_no_lib":
                hints.append("discord: voice lib missing — transcript-only")

        # meeting attached sources
        if isinstance(mt, dict) and mt.get("mode") != "unavailable":
            atts = mt.get("attached_sources") or []
            if not atts:
                hints.append("meeting: no caption bridge attached")

        # workstation readiness
        wsr = (ws.get("readiness") or {}) if isinstance(ws, dict) else {}
        cls = wsr.get("classification")
        if cls in ("simulated_only", "unsupported", "degraded"):
            hints.append(f"workstation: ptt classification={cls}")

        # meet bridge backlog
        for b in bridges[:5]:
            try:
                bk = b.get("backlog_estimate_lines")
                if isinstance(bk, int) and bk >= 3:
                    name = b.get("meeting_code") or "?"
                    hints.append(f"meeting: bridge '{name}' backlog ~{bk} lines"[:80])
            except Exception:  # noqa: BLE001
                continue

        # ingress silence: no transcripts at all across transports
        try:
            total = int(ingress.get("by_source_total") or 0)
            if total == 0:
                hints.append("transcripts: no ingress across any transport")
        except Exception:  # noqa: BLE001
            pass

        # playback capability
        pa = report.get("playback_aggregates") or {}
        for t in ("discord", "meeting"):
            pb = (pa.get("by_transport") or {}).get(t) or {}
            if isinstance(pb, dict) and pb.get("mode") == "transcript_only":
                if pb.get("attached") is False and pb.get("enabled") is False:
                    # already implied by earlier hints — skip to stay terse
                    pass
    except Exception as e:  # noqa: BLE001
        _log(f"_supervision_hints_block failed: {e}")

    # Bound + normalize
    normed: list[str] = []
    for h in hints:
        if not isinstance(h, str):
            continue
        s = h.strip()
        if not s:
            continue
        if len(s) > 80:
            s = s[:80]
        normed.append(s)
        if len(normed) >= 10:
            break
    return normed


__all__ = ["unified_transport_report"]
