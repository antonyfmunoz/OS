"""
Discord text transport — Pseudo-Live Voice Loop v1.

Purpose
-------
This is the **bounded Discord text-channel ingress** for the shared voice
substrate. It exists so the operator can sit in a Discord voice channel,
type a message into the paired text channel (e.g. via a browser STT
plugin), and get an EOS reply sent back as a Discord TTS-flagged text
message — simulating live back-and-forth WITHOUT standing up a real
duplex voice pipeline.

Contract
--------
A Discord text message flows through the SAME bounded seam that the voice
transport already uses:

    Discord text message
      → ingest_text_message(...)
      → inject_transcript(node_id, text, source="discord_text", metadata={...})
      → VoiceSessionRuntime.submit_utterance
      → responder (EOS-backed)
      → AGENT turn
      → build_tts_reply_envelope(...) — Discord text message with tts=True

This module does NOT:
  - import or touch services/discord_bot.py
  - own a Discord client, event loop, or bot lifecycle
  - create a parallel cognition path
  - replace transcript-only or voice-playback modes
  - widen any trust boundary

Default is OFF. Nothing activates unless the operator explicitly enables
the feature flags AND the message passes channel/guild/user gating.

Env flags (all default OFF)
---------------------------
- EOS_DISCORD_TEXT_TRANSPORT_ENABLED      — ingress gate (required for any activity)
- EOS_DISCORD_TEXT_REPLY_TTS_ENABLED      — egress gate (TTS reply allowed)
- EOS_DISCORD_TEXT_ALLOWED_GUILDS         — comma-separated guild IDs; "*" = any
- EOS_DISCORD_TEXT_ALLOWED_CHANNELS       — comma-separated channel IDs; "*" = any
- EOS_DISCORD_TEXT_ALLOWED_USERS          — comma-separated user IDs; "*" = any
- EOS_DISCORD_TEXT_REPLY_MAX_CHARS        — reply truncation cap (default 1800)

Gating is strict: if an allowlist env var is unset OR empty, that dimension
BLOCKS. Operators must explicitly set each dimension. The only exception
is the literal value `*` which means "any".
"""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from substrate.execution.bridge.workload_policy import classify_workload
from substrate.execution.bridge.resource_guard import evaluate_resource_guard
from substrate.execution.bridge.context_lifecycle import (
    detect_context_pressure,
    maybe_clear_and_restore,
)


def _log(msg: str) -> None:
    print(f"[substrate.discord_text_transport] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Env flag helpers ────────────────────────────────────────────────────────


_ENV_INGRESS = "EOS_DISCORD_TEXT_TRANSPORT_ENABLED"
_ENV_TTS = "EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"
_ENV_GUILDS = "EOS_DISCORD_TEXT_ALLOWED_GUILDS"
_ENV_CHANNELS = "EOS_DISCORD_TEXT_ALLOWED_CHANNELS"
_ENV_USERS = "EOS_DISCORD_TEXT_ALLOWED_USERS"
_ENV_MAX_CHARS = "EOS_DISCORD_TEXT_REPLY_MAX_CHARS"
# Claude Responder v1: when truthy, route replies through a persistent
# Claude Code tmux session instead of the voice-substrate responder.
_ENV_CLAUDE_RESPONDER = "EOS_DISCORD_CLAUDE_RESPONDER_ENABLED"
_ENV_CLAUDE_TARGET = "EOS_DISCORD_CLAUDE_RESPONDER_TARGET"
_ENV_CLAUDE_SESSION = "EOS_DISCORD_CLAUDE_RESPONDER_SESSION"
_ENV_CLAUDE_PER_CHANNEL = "EOS_DISCORD_CLAUDE_RESPONDER_PER_CHANNEL"

_DEFAULT_MAX_CHARS = 1800
_TRANSCRIPT_SOURCE = "discord_text"


def _flag_truthy(name: str) -> bool:
    val = os.getenv(name, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _ingress_enabled() -> bool:
    return _flag_truthy(_ENV_INGRESS)


def _tts_enabled() -> bool:
    return _flag_truthy(_ENV_TTS)


def _parse_allowlist(name: str) -> set[str]:
    raw = os.getenv(name, "") or ""
    return {tok.strip() for tok in raw.split(",") if tok.strip()}


def _allowlist_permits(name: str, value: Optional[str]) -> bool:
    allow = _parse_allowlist(name)
    if not allow:
        return False  # strict: empty = block
    if "*" in allow:
        return True
    if value is None:
        return False
    return str(value) in allow


def _reply_max_chars() -> int:
    raw = os.getenv(_ENV_MAX_CHARS, "").strip()
    if not raw:
        return _DEFAULT_MAX_CHARS
    try:
        n = int(raw)
        return max(50, min(4000, n))
    except ValueError:
        return _DEFAULT_MAX_CHARS


def truncate_reply(text: str, *, max_chars: Optional[int] = None) -> str:
    """Bounded reply truncation with ellipsis. Never raises."""
    cap = (
        max_chars
        if isinstance(max_chars, int) and max_chars > 0
        else _reply_max_chars()
    )
    clean = (text or "").strip()
    if len(clean) <= cap:
        return clean
    # Leave room for the ellipsis marker.
    return clean[: max(1, cap - 1)].rstrip() + "…"


# ─── Event history ring ──────────────────────────────────────────────────────


@dataclass
class DiscordTextEvent:
    kind: str  # "ingress" | "reply" | "gate_denied" | "disabled" | "error"
    occurred_at: str = field(default_factory=_utcnow_iso)
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    text_preview: Optional[str] = None
    session_id: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
    tts: Optional[bool] = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class _TextHistory:
    def __init__(self, capacity: int = 64) -> None:
        self._cap = max(8, int(capacity))
        self._items: list[DiscordTextEvent] = []
        self._lock = threading.Lock()

    def record(self, ev: DiscordTextEvent) -> None:
        with self._lock:
            self._items.append(ev)
            if len(self._items) > self._cap:
                self._items = self._items[-self._cap :]

    def latest(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [e.as_dict() for e in self._items[-int(max(1, limit)) :]]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


_history = _TextHistory()


# ─── Responder-backend observability state ──────────────────────────────────
# Tracks which backend served the most recent pseudo-live reply and whether
# TTS sanitization stripped any footer/meta content. Read by
# pseudo_live_status() so the operator can confirm the hard-switch is live.
_backend_state_lock = threading.Lock()
_backend_state: dict[str, Any] = {
    "responder_backend": None,  # "claude_session" | "substrate" | None
    "provider_fallback_used": False,  # True if provider path ever served
    "last_tts_sanitized": None,  # True if last reply had footer stripped
    "last_tts_reply_length": None,  # int chars of spoken_text
    "last_display_length": None,  # int chars of display_text (visible)
    "last_spoken_length": None,  # int chars of spoken_text (TTS)
    "last_reply_at": None,  # iso timestamp
}


def _record_backend(
    *,
    backend: str,
    provider_fallback: bool,
    sanitized: Optional[bool],
    spoken_length: Optional[int],
    display_length: Optional[int] = None,
) -> None:
    with _backend_state_lock:
        _backend_state["responder_backend"] = backend
        if provider_fallback:
            _backend_state["provider_fallback_used"] = True
        _backend_state["last_tts_sanitized"] = sanitized
        _backend_state["last_tts_reply_length"] = spoken_length
        _backend_state["last_spoken_length"] = spoken_length
        if display_length is not None:
            _backend_state["last_display_length"] = display_length
        _backend_state["last_reply_at"] = _utcnow_iso()


def _backend_snapshot() -> dict[str, Any]:
    with _backend_state_lock:
        return dict(_backend_state)


def reset_backend_state_for_tests() -> None:
    with _backend_state_lock:
        _backend_state.update(
            {
                "responder_backend": None,
                "provider_fallback_used": False,
                "last_tts_sanitized": None,
                "last_tts_reply_length": None,
                "last_display_length": None,
                "last_spoken_length": None,
                "last_reply_at": None,
            }
        )


def get_text_history() -> _TextHistory:
    return _history


def reset_text_history_for_tests() -> None:
    _history.clear()


# ─── Core: ingest + reply envelope ───────────────────────────────────────────


def _short_preview(text: str, n: int = 80) -> str:
    clean = (text or "").strip().replace("\n", " ")
    if len(clean) <= n:
        return clean
    return clean[: n - 1] + "…"


def _check_gating(
    *,
    guild_id: Optional[str],
    channel_id: Optional[str],
    user_id: Optional[str],
) -> Optional[str]:
    """Return None if permitted; otherwise a short denial reason."""
    if not _allowlist_permits(_ENV_GUILDS, guild_id):
        return "guild_not_allowed"
    if not _allowlist_permits(_ENV_CHANNELS, channel_id):
        return "channel_not_allowed"
    if not _allowlist_permits(_ENV_USERS, user_id):
        return "user_not_allowed"
    return None


def ingest_text_message(
    text: str,
    *,
    guild_id: Optional[Any] = None,
    channel_id: Optional[Any] = None,
    user_id: Optional[Any] = None,
    role_slug: str = "ea_orchestrator",
    extra_metadata: Optional[dict] = None,
    emit_tts: bool = True,
) -> dict[str, Any]:
    """Pseudo-live text ingress into the shared voice substrate.

    Behavior:
      1. Returns {status: "disabled"} immediately if ingress flag is off.
      2. Returns {status: "gate_denied", detail: <reason>} if any allowlist
         dimension blocks this (guild/channel/user).
      3. Otherwise routes through the SAME DiscordVoiceTransport instance
         for this (guild, channel) — so there is exactly one voice session
         shared between voice and text ingress — and tags the transcript
         with source="discord_text".
      4. Returns a JSON-friendly dict with session_id, reply_text (latest
         AGENT turn on that session, if any), and the ingress status.

    Never raises. All failures degrade to a status dict.
    """
    gid = str(guild_id) if guild_id is not None else None
    cid = str(channel_id) if channel_id is not None else None
    uid = str(user_id) if user_id is not None else None

    preview = _short_preview(text or "")

    if not _ingress_enabled():
        ev = DiscordTextEvent(
            kind="disabled",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=preview,
            status="disabled",
            detail=f"{_ENV_INGRESS} not truthy",
        )
        _history.record(ev)
        return {"status": "disabled", "event": ev.as_dict()}

    denial = _check_gating(guild_id=gid, channel_id=cid, user_id=uid)
    if denial is not None:
        ev = DiscordTextEvent(
            kind="gate_denied",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=preview,
            status="gate_denied",
            detail=denial,
        )
        _history.record(ev)
        return {"status": "gate_denied", "detail": denial, "event": ev.as_dict()}

    clean = (text or "").strip()
    if not clean:
        ev = DiscordTextEvent(
            kind="ingress",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview="",
            status="empty_text",
            detail="empty text",
        )
        _history.record(ev)
        return {"status": "empty_text", "event": ev.as_dict()}

    # Reuse the SAME DiscordVoiceTransport for this (guild, channel), so a
    # single shared voice session carries both voice and text turns.
    try:
        from substrate.execution.bridge.discord_voice_transport import (
            get_default_discord_voice_transport,
        )
    except Exception as e:  # noqa: BLE001
        ev = DiscordTextEvent(
            kind="error",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=preview,
            status="import_failed",
            detail=str(e),
        )
        _history.record(ev)
        return {"status": "import_failed", "detail": str(e), "event": ev.as_dict()}

    try:
        transport = get_default_discord_voice_transport(
            guild_id=gid,
            channel_id=cid,
            role_slug=role_slug,
        )
    except Exception as e:  # noqa: BLE001
        ev = DiscordTextEvent(
            kind="error",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=preview,
            status="transport_init_failed",
            detail=str(e),
        )
        _history.record(ev)
        return {
            "status": "transport_init_failed",
            "detail": str(e),
            "event": ev.as_dict(),
        }

    # ── Discord Channel Mode Routing v1 ─────────────────────────────────────
    # Classify the channel into a substrate mode (builder|product|unknown) and
    # resolve the corresponding Claude session target/name. Mode is metadata
    # that rides the existing shared substrate/router path — it never forks
    # the pipeline. Unknown mode is a no-op (router uses its env defaults).
    try:
        from substrate.execution.bridge.discord_mode_routing import (
            MODE_UNKNOWN,
            mode_context,
            resolve_discord_mode,
            resolve_mode_session,
        )
    except Exception as e:  # noqa: BLE001 — bounded, never raise
        _log(f"discord_mode_routing import failed: {e}")
        MODE_UNKNOWN = "unknown"  # type: ignore[assignment]

        def resolve_discord_mode(_g, _c):  # type: ignore[no-redef]
            return "unknown"

        def resolve_mode_session(_m, guild_id=None, channel_id=None):  # type: ignore[no-redef]
            return {"mode": "unknown", "target": None, "session_name": None}

        from contextlib import contextmanager as _cm

        @_cm  # type: ignore[no-redef]
        def mode_context(*_a, **_k):  # type: ignore[no-redef]
            yield None

    discord_mode = resolve_discord_mode(gid, cid)
    mode_session = resolve_mode_session(discord_mode, guild_id=gid, channel_id=cid)

    # ── Execution Trace v1 — create per-request trace ─────────────────
    try:
        from substrate.execution.bridge.execution_trace import (
            new_trace,
            update_trace as _ut,
            finalize_trace as _ft,
            trace_context,
            get_trace_history,
        )

        _trace = new_trace(
            source="discord_text",
            mode=discord_mode,
            session_name=mode_session.get("session_name") or "",
            target_initial=mode_session.get("target"),
        )
    except Exception:  # noqa: BLE001
        _trace = None
        trace_context = None  # type: ignore[assignment]
    # ──────────────────────────────────────────────────────────────────

    meta = {
        "transport": "discord",
        "source_context": "text_message",
        "guild_id": gid,
        "channel_id": cid,
        "user_id": uid,
        "discord_mode": discord_mode,
        "responder_target": mode_session.get("target"),
        "responder_session": mode_session.get("session_name"),
        "execution_policy_source": mode_session.get("source", "default"),
        "delegated_local": mode_session.get("delegated_local", False),
        "delegation_reason": mode_session.get("delegation_reason"),
        "policy_version": mode_session.get("policy_version"),
        **(extra_metadata or {}),
    }

    # ── workflow delegation (classification + policy) ────────────────────
    try:
        from substrate.execution.bridge.workflow_delegation import enrich_metadata

        enrich_metadata(meta, clean, discord_mode)
    except Exception:  # noqa: BLE001
        pass  # classification failure must never block the request path
    if _trace is not None:
        try:
            _ut(
                _trace,
                workflow_intent=meta.get("workflow_intent"),
                workflow_kind=meta.get("workflow_kind"),
                workflow_allowed=meta.get("workflow_allowed"),
            )
        except Exception:  # noqa: BLE001
            pass
    # ────────────────────────────────────────────────────────────────────

    # ── workload classification ────────────────────────────────────────
    try:
        wl = classify_workload(
            clean,
            discord_mode,
            workflow_kind=meta.get("workflow_kind"),
            metadata=meta,
        )
        meta["workload_class"] = wl.get("workload_class", "standard")
        meta["workload_reason"] = wl.get("reason", "")
    except Exception:  # noqa: BLE001
        meta["workload_class"] = "standard"
        meta["workload_reason"] = "classify_error"
    if _trace is not None:
        try:
            _ut(_trace, workload_class=meta.get("workload_class", "standard"))
        except Exception:  # noqa: BLE001
            pass
    # ────────────────────────────────────────────────────────────────────

    # ── resource guard ─────────────────────────────────────────────────
    try:
        rg = evaluate_resource_guard(
            mode=discord_mode,
            target=mode_session.get("target") or "vps",
            workload_class=meta["workload_class"],
        )
        meta["pressure_level"] = rg.get("pressure_level", "low")
        meta["resource_guard_allowed"] = rg.get("allowed", True)
        meta["resource_recommended_target"] = rg.get("recommended_target", "vps")

        # If resource guard says blocked AND mode is builder, override target
        if not rg.get("allowed", True) and discord_mode == "builder":
            mode_session["target"] = "local"
            meta["responder_target"] = "local"
            meta["resource_guard_override"] = True
    except Exception:  # noqa: BLE001
        meta["pressure_level"] = "low"
        meta["resource_guard_allowed"] = True
        meta["resource_recommended_target"] = mode_session.get("target") or "vps"
    if _trace is not None:
        try:
            _ut(
                _trace,
                resource_pressure=meta.get("pressure_level", "low"),
                resource_guard_allowed=meta.get("resource_guard_allowed", True),
                resource_guard_reason=meta.get("resource_recommended_target"),
                target_final=meta.get("responder_target"),
            )
        except Exception:  # noqa: BLE001
            pass
    # ────────────────────────────────────────────────────────────────────

    # ── workflow execution (v1: bounded handler dispatch) ──────────────
    # If the request is a classified, allowed workflow AND the handler
    # is not deferred, execute it here and short-circuit inject_transcript.
    # Deferred handlers (no session bound) fall through to the normal path.
    wf_exec_result: Optional[dict] = None
    # ── DEBUG: trace workflow gate decision (remove after fix confirmed) ──
    _log(
        f"workflow gate: exec_class={meta.get('workflow_execution_class')!r} "
        f"allowed={meta.get('workflow_allowed')!r} "
        f"kind={meta.get('workflow_kind')!r} "
        f"reason={meta.get('workflow_policy_reason')!r}"
    )
    if (
        meta.get("workflow_execution_class") == "workflow"
        and meta.get("workflow_allowed") is True
    ):
        try:
            from substrate.execution.bridge.workflow_execution import (
                execute_workflow_if_allowed,
            )

            wf_exec_result = execute_workflow_if_allowed(
                clean,
                discord_mode,
                target=mode_session.get("target"),
                session_name=mode_session.get("session_name"),
                metadata=meta,
            )
        except Exception:  # noqa: BLE001
            wf_exec_result = None  # execution failure falls through

        # If workflow executed and not deferred, return early
        if (
            wf_exec_result is not None
            and wf_exec_result.get("workflow_executed") is True
            and not wf_exec_result.get("details", {}).get("deferred", False)
        ):
            # Stamp trace for workflow short-circuit path
            if _trace is not None:
                try:
                    _ut(
                        _trace,
                        workflow_executed=True,
                        workflow_handler=wf_exec_result.get("handler"),
                        execution_path="workflow",
                    )
                    _ft(_trace, result="success")
                    get_trace_history().record(_trace)
                except Exception:  # noqa: BLE001
                    pass
            reply_text = wf_exec_result.get("result_summary", "")
            ev = DiscordTextEvent(
                kind="ingress",
                guild_id=gid,
                channel_id=cid,
                user_id=uid,
                text_preview=preview,
                status="workflow_executed",
                detail=wf_exec_result.get("handler", ""),
            )
            _history.record(ev)
            return {
                "status": "workflow_executed",
                "session_id": None,
                "role_slug": role_slug,
                "detail": wf_exec_result.get("handler", ""),
                "audio_loop": False,
                "reply_text": reply_text,
                "event": ev.as_dict(),
                "workflow_intent": meta.get("workflow_intent"),
                "workflow_kind": meta.get("workflow_kind"),
                "workflow_allowed": meta.get("workflow_allowed"),
                "workflow_execution_class": meta.get("workflow_execution_class"),
                "workflow_executed": True,
                "workflow_result": wf_exec_result,
                # substrate metadata
                "workload_class": meta.get("workload_class"),
                "workload_reason": meta.get("workload_reason"),
                "pressure_level": meta.get("pressure_level"),
                "resource_guard_allowed": meta.get("resource_guard_allowed"),
                "resource_recommended_target": meta.get("resource_recommended_target"),
                "context_pressure_score": None,
                "context_pressure_level": None,
                "context_cleared": False,
                "context_checkpoint_used": False,
                "execution_target_final": mode_session.get("target"),
                "_trace": _trace,
            }
    # ────────────────────────────────────────────────────────────────────

    # Route conversation through mode context so downstream sees the right target.
    try:
        with mode_context(
            discord_mode,
            target=mode_session.get("target"),
            session_name=mode_session.get("session_name"),
            guild_id=gid,
            channel_id=cid,
            source=mode_session.get("source"),
            delegated_local=mode_session.get("delegated_local", False),
            delegation_reason=mode_session.get("delegation_reason"),
            policy_version=mode_session.get("policy_version"),
        ):
            if _trace is not None:
                _ut(
                    _trace,
                    execution_path="conversation",
                    workflow_executed=False,
                )
    except Exception as e:  # noqa: BLE001
        ev = DiscordTextEvent(
            kind="error",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=preview,
            status="conversation_exception",
            detail=str(e),
        )
        _history.record(ev)
        return {"status": "conversation_exception", "detail": str(e), "event": ev.as_dict()}

    # Finalize substrate trace
    if _trace is not None:
        try:
            _ft(
                _trace,
                provider=None,
                result="success",
                latency_ms=None,
            )
            get_trace_history().record(_trace)
        except Exception:  # noqa: BLE001
            pass

    ev = DiscordTextEvent(
        kind="ingress",
        guild_id=gid,
        channel_id=cid,
        user_id=uid,
        text_preview=preview,
        session_id=None,
        status="ok",
        detail="",
    )
    _history.record(ev)

    return {
        "status": "ok",
        "session_id": None,
        "node_id": transport.node_id,
        "role_slug": role_slug,
        "detail": "",
        "audio_loop": None,
        "reply_text": None,
        "event": ev.as_dict(),
        # workflow metadata
        "workflow_intent": meta.get("workflow_intent"),
        "workflow_kind": meta.get("workflow_kind"),
        "workflow_allowed": meta.get("workflow_allowed"),
        "workflow_execution_class": meta.get("workflow_execution_class"),
        "workflow_executed": False,
        "workflow_result": wf_exec_result,
        # substrate metadata
        "workload_class": meta.get("workload_class"),
        "workload_reason": meta.get("workload_reason"),
        "pressure_level": meta.get("pressure_level"),
        "resource_guard_allowed": meta.get("resource_guard_allowed"),
        "resource_recommended_target": meta.get("resource_recommended_target"),
        "context_pressure_score": None,
        "context_pressure_level": None,
        "context_cleared": False,
        "context_checkpoint_used": False,
        "execution_target_final": mode_session.get("target"),
        "_trace": _trace,
    }


def _latest_agent_reply(session_id: Optional[str]) -> Optional[str]:
    if not session_id:
        return None
    try:
        from substrate.execution.bridge.voice_session import (
            VoiceTurnSource,
            get_voice_session_store,
        )

        session = get_voice_session_store().get(session_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.source == VoiceTurnSource.AGENT and (turn.text or "").strip():
                return turn.text
    except Exception as e:  # noqa: BLE001
        _log(f"_latest_agent_reply failed: {e}")
    return None


def build_tts_reply_envelope(
    reply_text: Optional[str],
    *,
    guild_id: Optional[Any] = None,
    channel_id: Optional[Any] = None,
    max_chars: Optional[int] = None,
) -> dict[str, Any]:
    """Produce a Discord-send envelope for a pseudo-live TTS reply.

    Returns a dict with a stable shape:

        {
          "status": "ok" | "no_reply" | "tts_disabled" | "ingress_disabled",
          "content": <truncated text>,
          "tts":     <bool — True only when TTS egress is env-enabled>,
          "max_chars": <int>,
          "guild_id": <str|None>,
          "channel_id": <str|None>,
          "detail":  <short reason>,
        }

    The bot layer calls this and then emits:

        env = build_tts_reply_envelope(reply, ...)
        if env["status"] == "ok":
            await channel.send(env["content"], tts=env["tts"])

    When TTS is disabled, the envelope still degrades safely to a plain
    text reply (tts=False) so the operator still sees the answer.
    """
    gid = str(guild_id) if guild_id is not None else None
    cid = str(channel_id) if channel_id is not None else None
    cap = _reply_max_chars() if max_chars is None else max_chars

    if not _ingress_enabled():
        return {
            "status": "ingress_disabled",
            "content": "",
            "tts": False,
            "max_chars": cap,
            "guild_id": gid,
            "channel_id": cid,
            "detail": f"{_ENV_INGRESS} not truthy",
        }

    clean = (reply_text or "").strip()
    if not clean:
        return {
            "status": "no_reply",
            "content": "",
            "tts": False,
            "max_chars": cap,
            "guild_id": gid,
            "channel_id": cid,
            "detail": "no agent reply available",
        }

    # Display text preserves the FULL (truncated) reply for chat rendering —
    # footer, skill block, provider badge, and all. This is what the visible
    # Discord message shows the operator.
    display_text = truncate_reply(clean, max_chars=cap)

    # Spoken text is the sanitized body — footer/meta/skill/provider lines
    # are stripped so TTS NEVER reads them aloud. Bounded length.
    try:
        from substrate.execution.bridge.tts_sanitize import sanitize_tts_reply

        spoken_raw = sanitize_tts_reply(clean, max_chars=cap)
    except Exception as e:  # noqa: BLE001 — never raise from envelope build
        _log(f"sanitize_tts_reply failed: {e}")
        spoken_raw = ""
    spoken_text = truncate_reply(spoken_raw, max_chars=cap) if spoken_raw else ""
    sanitized = bool(spoken_text) and spoken_text != display_text

    tts = _tts_enabled()

    # `content` keeps backward-compat shape = the VISIBLE message (full
    # display_text with footer). The bot should prefer `emit_plan` to get
    # the split behavior, but any legacy reader that pulls `content` now
    # correctly sees the footer-preserving visible message.
    content = display_text

    # tts_content is the spoken-only payload. Empty when sanitizer produced
    # nothing useful — in that case the spoken send is skipped.
    tts_content = spoken_text

    # emit_plan: ordered list of (content, tts) pairs the bot should send.
    #   - If TTS is off entirely → one visible send, tts=False.
    #   - If sanitizer stripped footer AND produced a distinct body →
    #     TWO sends: visible (display, tts=False) + spoken (tts_content, tts=True).
    #   - If sanitizer produced nothing distinct (body == display, no footer)
    #     → ONE send with tts=True, speaking the whole thing (safe, no footer).
    #   - If sanitizer produced ONLY footer (empty spoken) → ONE visible send,
    #     tts=False (nothing clean to speak).
    emit_plan: list[dict[str, Any]] = []
    if not tts:
        emit_plan.append({"content": display_text, "tts": False, "role": "visible"})
    elif sanitized and tts_content:
        emit_plan.append({"content": display_text, "tts": False, "role": "visible"})
        emit_plan.append({"content": tts_content, "tts": True, "role": "spoken"})
    elif tts_content and tts_content == display_text:
        emit_plan.append({"content": display_text, "tts": True, "role": "combined"})
    else:
        # spoken_text was empty (footer-only input) — don't speak gibberish.
        emit_plan.append({"content": display_text, "tts": False, "role": "visible"})

    _record_backend(
        backend=_backend_snapshot().get("responder_backend") or "unknown",
        provider_fallback=False,
        sanitized=sanitized,
        spoken_length=len(tts_content) if tts_content else 0,
        display_length=len(display_text),
    )

    ev = DiscordTextEvent(
        kind="reply",
        guild_id=gid,
        channel_id=cid,
        text_preview=_short_preview(display_text),
        status="ok",
        tts=tts,
        detail=(
            "split_visible_plus_spoken"
            if sanitized and tts_content and tts
            else ("tts_enabled" if tts else "tts_disabled_plain_fallback")
        ),
    )
    _history.record(ev)

    return {
        "status": "ok",
        "content": content,
        "tts_content": tts_content,
        "spoken_text": spoken_text,
        "display_text": display_text,
        "sanitized": sanitized,
        "tts": tts,
        "emit_plan": emit_plan,
        "max_chars": cap,
        "guild_id": gid,
        "channel_id": cid,
        "detail": (
            "split_visible_plus_spoken"
            if sanitized and tts_content and tts
            else ("tts_enabled" if tts else "tts_disabled_plain_fallback")
        ),
    }


# ─── Session command handler ─────────────────────────────────────────────────


def _handle_session_command(
    command: str,
    *,
    guild_id: Optional[str],
    channel_id: Optional[str],
    user_id: Optional[str],
) -> dict[str, Any]:
    """Handle /clear and /reset session commands.

    Executes directly via claude_session_bridge — does NOT route through the
    voice substrate or model_router. Returns a combined {ingress, envelope}
    dict with tts=False (no TTS for control commands).
    """
    preview = command
    try:
        from substrate.execution.bridge.discord_mode_routing import (
            resolve_discord_mode,
            resolve_mode_session,
        )

        mode = resolve_discord_mode(guild_id, channel_id)
        mode_session = resolve_mode_session(
            mode, guild_id=guild_id, channel_id=channel_id
        )
        session_name = mode_session.get("session_name")
        target = mode_session.get("target") or "vps"
    except Exception as e:  # noqa: BLE001
        _log(f"session command mode resolution failed: {e}")
        session_name = None
        target = "vps"

    if not session_name:
        reply = "[session] No session mapped for this channel."
        ev = DiscordTextEvent(
            kind="ingress",
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            text_preview=preview,
            status="no_session",
            detail="no session for channel",
        )
        _history.record(ev)
        return {
            "ingress": {
                "status": "no_session",
                "detail": "no session mapped",
                "event": ev.as_dict(),
            },
            "envelope": {
                "status": "ok",
                "content": reply,
                "tts": False,
                "tts_content": "",
                "spoken_text": "",
                "display_text": reply,
                "sanitized": False,
                "emit_plan": [{"content": reply, "tts": False, "role": "visible"}],
                "max_chars": _reply_max_chars(),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "detail": "session_command_no_session",
            },
        }

    try:
        from substrate.execution.bridge.session_control import clear_session, reset_session

        if command == "/clear":
            result = clear_session(target, session_name)
        else:  # /reset
            result = reset_session(target, session_name)
    except Exception as e:  # noqa: BLE001
        _log(f"session command execution failed: {e}")
        result = {"ok": False, "reason": str(e)}

    if result.get("ok"):
        reply = f"[session] {command.lstrip('/')} completed for `{session_name}`."
    else:
        reason = result.get("reason", "unknown")
        reply = f"[session] {command.lstrip('/')} failed: {reason}"

    ev = DiscordTextEvent(
        kind="ingress",
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
        text_preview=preview,
        status="ok" if result.get("ok") else "error",
        detail=f"session_command:{command}",
    )
    _history.record(ev)
    return {
        "ingress": {
            "status": "ok" if result.get("ok") else "error",
            "detail": f"session_command:{command}",
            "session_name": session_name,
            "event": ev.as_dict(),
        },
        "envelope": {
            "status": "ok",
            "content": reply,
            "tts": False,
            "tts_content": "",
            "spoken_text": "",
            "display_text": reply,
            "sanitized": False,
            "emit_plan": [{"content": reply, "tts": False, "role": "visible"}],
            "max_chars": _reply_max_chars(),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "detail": f"session_command:{command}",
        },
    }


def _handle_trace_command(
    text: str,
    *,
    guild_id: Optional[str],
    channel_id: Optional[str],
    user_id: Optional[str],
) -> dict[str, Any]:
    """Handle /trace operator command.

    Returns recent execution traces in compact format. Builder mode only —
    product mode gets a denial message. No TTS for trace output.
    """
    try:
        from substrate.execution.bridge.discord_mode_routing import resolve_discord_mode

        mode = resolve_discord_mode(guild_id, channel_id)
    except Exception:  # noqa: BLE001
        mode = "unknown"

    if mode == "product":
        reply = "[trace] Trace output is not available in product mode."
        return {
            "ingress": {"status": "denied", "detail": "product_mode_trace_denied"},
            "envelope": {
                "status": "ok",
                "content": reply,
                "tts": False,
                "tts_content": "",
                "spoken_text": "",
                "display_text": reply,
                "sanitized": False,
                "emit_plan": [{"content": reply, "tts": False, "role": "visible"}],
                "max_chars": _reply_max_chars(),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "detail": "trace_denied_product",
            },
        }

    # Parse optional limit: "/trace 10" or "/trace" (default 5)
    parts = (text or "").strip().split()
    limit = 5
    if len(parts) > 1:
        try:
            limit = max(1, min(int(parts[1]), 20))
        except ValueError:
            pass

    try:
        from substrate.execution.bridge.execution_trace import (
            format_trace_compact,
            get_trace_history,
        )

        traces = get_trace_history().latest(limit=limit)
        if not traces:
            reply = "[trace] No traces recorded yet."
        else:
            lines = [f"**Execution Traces** (last {len(traces)}):"]
            lines.append("```")
            for t in traces:
                lines.append(format_trace_compact(t))
            lines.append("```")
            reply = "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        reply = f"[trace] Error: {e}"

    ev = DiscordTextEvent(
        kind="ingress",
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
        text_preview="/trace",
        status="ok",
        detail="trace_command",
    )
    _history.record(ev)
    return {
        "ingress": {"status": "ok", "detail": "trace_command", "event": ev.as_dict()},
        "envelope": {
            "status": "ok",
            "content": reply[:1800],
            "tts": False,
            "tts_content": "",
            "spoken_text": "",
            "display_text": reply[:1800],
            "sanitized": False,
            "emit_plan": [{"content": reply[:1800], "tts": False, "role": "visible"}],
            "max_chars": _reply_max_chars(),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "detail": "trace_command",
        },
    }


# ─── Opt-in one-shot helper for services/discord_bot.py ──────────────────────


def maybe_mirror_discord_text_message(
    text: str,
    *,
    guild_id: Optional[Any] = None,
    channel_id: Optional[Any] = None,
    user_id: Optional[Any] = None,
    role_slug: str = "ea_orchestrator",
) -> Optional[dict[str, Any]]:
    """Opt-in hook for discord_bot.on_message.

    - Returns None immediately if EOS_DISCORD_TEXT_TRANSPORT_ENABLED is not
      truthy. This is the DEFAULT; bot behavior is unchanged.
    - Otherwise performs gating + ingress + envelope build, and returns a
      combined dict:

        {
          "ingress": {...},         # result of ingest_text_message(...)
          "envelope": {...},        # result of build_tts_reply_envelope(...)
        }

    The bot is expected to:
      1. Call this from on_message.
      2. If the return is None → do nothing (feature off).
      3. If ingress.status is "gate_denied" → do nothing.
      4. If envelope.status == "ok" → await channel.send(envelope["content"],
         tts=envelope["tts"]).

    Never raises. All failures degrade to a status dict inside `ingress`.
    """
    if not _ingress_enabled():
        return None

    # Gate check first — respect allowlists regardless of responder backend.
    gid = str(guild_id) if guild_id is not None else None
    cid = str(channel_id) if channel_id is not None else None
    uid = str(user_id) if user_id is not None else None
    denial = _check_gating(guild_id=gid, channel_id=cid, user_id=uid)
    if denial is not None:
        ev = DiscordTextEvent(
            kind="gate_denied",
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
            text_preview=_short_preview(text or ""),
            status="gate_denied",
            detail=denial,
        )
        _history.record(ev)
        return {
            "ingress": {
                "status": "gate_denied",
                "detail": denial,
                "event": ev.as_dict(),
            },
            "envelope": build_tts_reply_envelope(
                None, guild_id=guild_id, channel_id=channel_id
            ),
        }

    # Router-backed path (v2). There is no longer a Discord-only hard switch.
    # All Discord pseudo-live replies now flow through the shared voice
    # substrate → broader router (runtime.model_router.call_with_fallback),
    # where Claude CLI tmux is registered as backend #0. If Claude CLI is
    # unavailable the router falls through to the existing provider chain.
    # The legacy EOS_DISCORD_CLAUDE_RESPONDER_ENABLED flag is accepted for
    # backwards compatibility with existing env files but is now purely
    # observational — it no longer bypasses the router.
    _record_backend(
        backend="shared_router",
        provider_fallback=False,
        sanitized=None,
        spoken_length=None,
    )

    # ── Session / operator command interception ────────────────────────────
    # /clear, /reset, and /trace are control commands — they must NOT flow
    # through the router. Execute directly and return.
    clean_text = (text or "").strip()
    if clean_text.lower() in ("/clear", "/reset"):
        return _handle_session_command(
            clean_text.lower(),
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
        )
    if clean_text.lower().startswith("/trace"):
        return _handle_trace_command(
            clean_text,
            guild_id=gid,
            channel_id=cid,
            user_id=uid,
        )

    ingress = ingest_text_message(
        text,
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
        role_slug=role_slug,
        emit_tts=False,
    )

    # ── Mode behavior shaping ────────────────────────────────────────────
    # Resolve the channel mode and apply output shaping AFTER the router
    # returns but BEFORE the reply reaches Discord. This is a presentation
    # layer — it never changes routing or capability.
    reply_text = ingress.get("reply_text")
    try:
        from substrate.execution.bridge.discord_mode_routing import resolve_discord_mode
        from substrate.execution.bridge.mode_behavior import shape_reply

        discord_mode = resolve_discord_mode(gid, cid)
        if reply_text and discord_mode in ("builder", "product"):
            reply_text = shape_reply(reply_text, mode=discord_mode)
    except Exception as e:  # noqa: BLE001
        _log(f"mode shaping failed: {e}")

    # ── Context pressure + auto-clear ────────────────────────────────────
    # Detect context pressure using multi-signal analysis. If pressure
    # exceeds threshold, clear-and-restore via context_lifecycle. Otherwise
    # fall back to the original message-count auto-clear for backward compat.
    auto_clear_result: dict[str, Any] = {}
    ctx_pressure_score: float | None = None
    ctx_pressure_level: str | None = None
    ctx_cleared = False
    ctx_checkpoint_used = False
    try:
        from substrate.execution.bridge.discord_mode_routing import resolve_discord_mode as _rdm
        from substrate.execution.bridge.discord_mode_routing import resolve_mode_session as _rms

        _ac_mode = _rdm(gid, cid)
        _ac_session = _rms(_ac_mode, guild_id=gid, channel_id=cid)
        _ac_session_name = _ac_session.get("session_name")
        _ac_target = _ac_session.get("target") or "vps"

        if _ac_session_name:
            # Get message count for pressure signal
            from substrate.execution.bridge.session_control import (
                get_message_count,
                maybe_auto_clear as _maybe_auto_clear,
            )

            _msg_count = get_message_count(_ac_session_name)

            # Detect context pressure
            cp = detect_context_pressure(
                _ac_session_name,
                message_count=_msg_count,
                reply_text=reply_text,
                metadata=ingress,
            )
            ctx_pressure_score = cp.get("pressure_score")
            ctx_pressure_level = cp.get("pressure_level")

            if cp.get("should_clear"):
                # Use context lifecycle clear-and-restore
                cl_result = maybe_clear_and_restore(
                    _ac_session_name,
                    _ac_target,
                    _ac_mode,
                    message_count=_msg_count,
                    reply_text=reply_text,
                    workflow_kind=ingress.get("workflow_kind"),
                    metadata=ingress,
                )
                ctx_cleared = cl_result.get("cleared", False)
                ctx_checkpoint_used = "checkpoint" in cl_result
                auto_clear_result = cl_result
            else:
                # Fallback: original message-count auto-clear (backward compat)
                auto_clear_result = _maybe_auto_clear(
                    _ac_session_name, target=_ac_target
                )
    except Exception as e:  # noqa: BLE001
        _log(f"context-pressure/auto-clear check failed: {e}")

    # Surface context lifecycle metadata into ingress result
    ingress["context_pressure_score"] = ctx_pressure_score
    ingress["context_pressure_level"] = ctx_pressure_level
    ingress["context_cleared"] = ctx_cleared
    ingress["context_checkpoint_used"] = ctx_checkpoint_used
    ingress["auto_clear_result"] = auto_clear_result
    ingress["execution_target_final"] = ingress.get(
        "resource_recommended_target", ingress.get("responder_target")
    )

    # ── Execution Trace finalization ──────────────────────────────────
    # The trace was created inside ingest_text_message and stamped by
    # model_router._stamp_trace (provider/model). Here we add context
    # pressure data and record it into history.
    _ingress_trace = ingress.get("_trace")
    if _ingress_trace is not None:
        try:
            from substrate.execution.bridge.execution_trace import (
                update_trace as _ut_final,
                finalize_trace as _ft_final,
                get_trace_history as _gth,
            )

            _ut_final(
                _ingress_trace,
                context_pressure_score=ctx_pressure_score,
                context_checkpoint_used=ctx_checkpoint_used,
                context_restore_used=ctx_cleared,
            )
            # If model_router already set provider/model, finalize_trace
            # will not overwrite (only sets non-None args).
            _result_tag = (
                "success"
                if ingress.get("status") == "ok"
                else (
                    "blocked"
                    if ingress.get("status") in ("gate_denied", "disabled")
                    else "fallback"
                )
            )
            if _ingress_trace.get("result") is None:
                _ft_final(_ingress_trace, result=_result_tag)
            elif "finalized_at" not in _ingress_trace:
                _ft_final(_ingress_trace)
            _gth().record(_ingress_trace)
        except Exception:  # noqa: BLE001
            pass
    # ──────────────────────────────────────────────────────────────────

    envelope = build_tts_reply_envelope(
        reply_text,
        guild_id=guild_id,
        channel_id=channel_id,
    )

    # Include node_id + spoken_text so the bot can dispatch TTS AFTER
    # sending the Discord message (emit_tts=False above defers TTS).
    spoken_text = ""
    for _ep in envelope.get("emit_plan", []):
        if _ep.get("role") == "spoken":
            spoken_text = (_ep.get("content") or "").strip()
            break
    # If no separate spoken entry, use the combined/visible content
    if not spoken_text:
        for _ep in envelope.get("emit_plan", []):
            if _ep.get("tts") and _ep.get("content", "").strip():
                spoken_text = _ep["content"].strip()
                break

    return {
        "ingress": ingress,
        "envelope": envelope,
        "deferred_tts": {
            "node_id": ingress.get("node_id"),
            "spoken_text": spoken_text,
            "role_slug": ingress.get("role_slug") or role_slug,
        },
    }


_CLAUDE_UNAVAILABLE_REPLY = "[DEX] Claude session unavailable."


# NOTE: the _claude_failure_envelope / _claude_responder_ingest helpers below
# are no longer reachable — the former Discord-only hard switch in
# maybe_mirror_discord_text_message has been removed. Discord text now flows
# through the shared `ingest_text_message` → broader router path, where
# Claude CLI is registered as backend #0 in model_router.PROVIDER_PRIORITY.
# These helpers are retained only so legacy smoke tests can still import the
# module without error while being migrated; they are dead code.


def _claude_failure_envelope(
    *,
    guild_id: Optional[str],
    channel_id: Optional[str],
    reason: str,
    detail: str = "",
) -> dict[str, Any]:
    """Bounded clean failure envelope — NEVER touches provider path.

    Used when the Claude responder backend is enabled but unreachable
    (tmux missing, claude CLI missing, import failure, etc.). Returns a
    short deterministic reply so the operator sees a clear failure, and
    explicitly does not fall back to model_router / provider APIs.
    """
    cap = _reply_max_chars()
    tts_on = _tts_enabled()
    content = _CLAUDE_UNAVAILABLE_REPLY
    _record_backend(
        backend="claude_session",
        provider_fallback=False,
        sanitized=False,
        spoken_length=len(content),
        display_length=len(content),
    )
    emit_plan = [{"content": content, "tts": bool(tts_on), "role": "combined"}]
    envelope = {
        "status": "ok",
        "content": content,
        "tts_content": content,
        "spoken_text": content,
        "display_text": content,
        "sanitized": False,
        "tts": tts_on,
        "emit_plan": emit_plan,
        "max_chars": cap,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "detail": f"claude_responder_unavailable:{reason}",
    }
    ingress = {
        "status": "claude_responder_unavailable",
        "session_id": None,
        "role_slug": None,
        "detail": detail or reason,
        "audio_loop": None,
        "reply_text": content,
        "source": "claude_session",
        "provider_fallback_used": False,
    }
    return {"ingress": ingress, "envelope": envelope}


def _claude_responder_ingest(
    text: str,
    *,
    guild_id: Optional[str],
    channel_id: Optional[str],
    user_id: Optional[str],
) -> dict[str, Any]:
    """Route a Discord text message through Claude Session Bridge.

    HARD SWITCH — when the Claude responder flag is enabled, this is the
    ONLY path. On any failure it returns a bounded clean failure envelope;
    it NEVER returns None (which would cause the caller to silently fall
    back to the provider / substrate path). Never raises.
    """
    preview = _short_preview(text or "")
    clean = (text or "").strip()

    # Mark backend up-front so envelope build attributes correctly even on
    # early-return paths.
    _record_backend(
        backend="claude_session",
        provider_fallback=False,
        sanitized=None,
        spoken_length=None,
    )

    if not clean:
        ev = DiscordTextEvent(
            kind="ingress",
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            text_preview="",
            status="empty_text",
            detail="empty text",
        )
        _history.record(ev)
        return {
            "ingress": {
                "status": "empty_text",
                "session_id": None,
                "role_slug": None,
                "detail": "empty text",
                "audio_loop": None,
                "reply_text": "",
                "source": "claude_session",
                "provider_fallback_used": False,
                "event": ev.as_dict(),
            },
            "envelope": build_tts_reply_envelope(
                None, guild_id=guild_id, channel_id=channel_id
            ),
        }

    try:
        from substrate.execution.bridge.claude_responder import (
            DEFAULT_SESSION_NAME,
            DEFAULT_TARGET,
            respond_via_claude_session,
            session_name_for_discord_channel,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"claude_responder import failed: {e}")
        ev = DiscordTextEvent(
            kind="error",
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            text_preview=preview,
            status="claude_responder_unavailable",
            detail=f"import_failed: {e}",
        )
        _history.record(ev)
        # HARD SWITCH — NO fallback to provider/substrate path.
        return _claude_failure_envelope(
            guild_id=guild_id,
            channel_id=channel_id,
            reason="import_failed",
            detail=str(e),
        )

    target = (
        os.getenv(_ENV_CLAUDE_TARGET) or DEFAULT_TARGET
    ).strip().lower() or DEFAULT_TARGET
    per_channel = _flag_truthy(_ENV_CLAUDE_PER_CHANNEL)
    if per_channel and channel_id:
        session_name = session_name_for_discord_channel(channel_id)
    else:
        session_name = (
            os.getenv(_ENV_CLAUDE_SESSION) or DEFAULT_SESSION_NAME
        ).strip() or DEFAULT_SESSION_NAME

    try:
        result = respond_via_claude_session(
            clean,
            target=target,
            session_name=session_name,
        )
    except Exception as e:  # noqa: BLE001 — boundary, never raise
        _log(f"respond_via_claude_session raised: {e}")
        ev = DiscordTextEvent(
            kind="error",
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            text_preview=preview,
            status="claude_responder_unavailable",
            detail=f"exception: {e}",
        )
        _history.record(ev)
        return _claude_failure_envelope(
            guild_id=guild_id,
            channel_id=channel_id,
            reason="exception",
            detail=str(e),
        )

    if not result.get("ok"):
        reason = result.get("reason") or "claude_responder_failed"
        ev = DiscordTextEvent(
            kind="error",
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            text_preview=preview,
            status="claude_responder_unavailable",
            detail=f"{reason}: {result.get('detail') or ''}",
        )
        _history.record(ev)
        return _claude_failure_envelope(
            guild_id=guild_id,
            channel_id=channel_id,
            reason=reason,
            detail=str(result.get("detail") or ""),
        )

    reply_text = result.get("reply") or ""
    ev = DiscordTextEvent(
        kind="ingress",
        guild_id=guild_id,
        channel_id=channel_id,
        user_id=user_id,
        text_preview=preview,
        session_id=session_name,
        status="ok",
        detail=f"source=claude_session target={target}",
    )
    _history.record(ev)

    ingress = {
        "status": "ok",
        "session_id": session_name,
        "role_slug": None,
        "detail": result.get("detail") or result.get("reason"),
        "audio_loop": None,
        "reply_text": reply_text,
        "source": "claude_session",
        "target": target,
        "provider_fallback_used": False,
        "event": ev.as_dict(),
    }
    envelope = build_tts_reply_envelope(
        reply_text,
        guild_id=guild_id,
        channel_id=channel_id,
    )
    return {"ingress": ingress, "envelope": envelope}


# ─── Reporting block ─────────────────────────────────────────────────────────


def pseudo_live_status() -> dict[str, Any]:
    """Observability snapshot for the pseudo-live Discord text loop."""
    snap = _backend_snapshot()
    return {
        "ingress_enabled": _ingress_enabled(),
        "tts_reply_enabled": _tts_enabled(),
        "responder_backend": snap.get("responder_backend"),
        "provider_fallback_used": snap.get("provider_fallback_used"),
        "last_tts_sanitized": snap.get("last_tts_sanitized"),
        "last_tts_reply_length": snap.get("last_tts_reply_length"),
        "last_display_length": snap.get("last_display_length"),
        "last_spoken_length": snap.get("last_spoken_length"),
        "last_reply_at": snap.get("last_reply_at"),
        "claude_responder_enabled": _flag_truthy(_ENV_CLAUDE_RESPONDER),
        "claude_responder_target": os.getenv(_ENV_CLAUDE_TARGET) or "vps",
        "claude_responder_session": os.getenv(_ENV_CLAUDE_SESSION) or "dex_main",
        "claude_responder_per_channel": _flag_truthy(_ENV_CLAUDE_PER_CHANNEL),
        "allowlists": {
            "guilds": sorted(_parse_allowlist(_ENV_GUILDS)),
            "channels": sorted(_parse_allowlist(_ENV_CHANNELS)),
            "users": sorted(_parse_allowlist(_ENV_USERS)),
        },
        "reply_max_chars": _reply_max_chars(),
        "recent_events": _history.latest(limit=20),
        "transcript_source": _TRANSCRIPT_SOURCE,
        "hybrid_execution": _hybrid_execution_status(),
        "generated_at": _utcnow_iso(),
    }


def _hybrid_execution_status() -> dict[str, Any]:
    """Snapshot of the hybrid execution target policy layer."""
    try:
        from substrate.execution.bridge.target_policy import (
            POLICY_VERSION,
            resolve_execution_policy,
        )

        return {
            "policy_version": POLICY_VERSION,
            "builder_policy": resolve_execution_policy("builder"),
            "product_policy": resolve_execution_policy("product"),
        }
    except Exception:  # noqa: BLE001
        return {"policy_version": None, "error": "target_policy import failed"}


__all__ = [
    "DiscordTextEvent",
    "ingest_text_message",
    "build_tts_reply_envelope",
    "maybe_mirror_discord_text_message",
    "pseudo_live_status",
    "truncate_reply",
    "get_text_history",
    "reset_text_history_for_tests",
    "reset_backend_state_for_tests",
]
