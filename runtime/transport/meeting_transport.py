"""
Meeting voice transport — bounded adapter onto the existing voice substrate.

Purpose
-------
This is the FIRST meeting voice transport adapter. It exists so that
text-shaped utterances arriving from a meeting surface (Google Meet, Zoom,
Teams, generic_meeting) — whether captured by an external STT bridge, a
caption pipeline, or a test fixture — can flow into the SAME bounded seam
the local workstation and Discord transports already use:

    inject_transcript(node_id, text, source="meeting_voice", metadata={...})
        → VoiceSessionRuntime.submit_utterance
        → responder (EOS-backed if installed)
        → SPEAK_TEXT bounded output

It does NOT:
  - own a meeting client / browser / Selenium / Playwright session
  - drive Google Meet, Zoom, or Teams DOM
  - parse freeform spoken commands
  - widen any trust boundary
  - run a parallel agent loop

The adapter runs in TRANSCRIPT-ONLY mode by default. An optional bounded
playback/egress sink can be attached via `attach_playback_sink(sink)` —
this is intentionally a thin contract that a future real meeting playback
implementation can plug into without touching the seam.

Modes
-----
- transcript_only (default): no live meeting attachment. The adapter is a
  pure façade over `transcript_inject.inject_transcript`. Safe everywhere.
- attached: a playback sink has been attached AND playback is enabled. The
  adapter renders EOS reply text to the sink via `sink.play_text(text)`.
- attached_degraded: a sink is attached but playback is disabled or the
  sink is not yet capable of real egress. Transcript ingestion still works.

Optional opt-in hook
--------------------
External meeting bridges can call `maybe_mirror_meeting_utterance(...)` —
this is a no-op unless `EOS_MEETING_VOICE_TRANSPORT_ENABLED` is truthy.
Default OFF, so no behavior changes anywhere until an operator opts in.
"""

from __future__ import annotations

import os
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from runtime.transport.meeting_sources import is_meeting_source


def _log(msg: str) -> None:
    print(f"[substrate.meeting_transport] {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Capability probe (best-effort, no side effects) ─────────────────────────


def _probe_meeting_capability() -> dict[str, Any]:
    """Lazy probe: which optional meeting bridges *could* be wired in.

    NEVER imports a meeting client, NEVER opens a browser, NEVER touches the
    network. Just reports what is importable so the operator can see what is
    available without enabling anything.
    """
    out: dict[str, Any] = {
        "playwright_present": False,
        "selenium_present": False,
        "google_meet_lib_present": False,
        "zoom_sdk_present": False,
        "teams_sdk_present": False,
    }
    try:
        import playwright  # type: ignore  # noqa: F401

        out["playwright_present"] = True
    except Exception:
        pass
    try:
        import selenium  # type: ignore  # noqa: F401

        out["selenium_present"] = True
    except Exception:
        pass
    return out


# ─── Models ──────────────────────────────────────────────────────────────────


SUPPORTED_PLATFORMS = frozenset({"google_meet", "zoom", "teams", "generic_meeting"})


def _normalize_platform(platform: Optional[str]) -> str:
    if not platform:
        return "generic_meeting"
    p = str(platform).strip().lower()
    return p if p in SUPPORTED_PLATFORMS else "generic_meeting"


@dataclass
class MeetingTransportEvent:
    """One bounded transcript event flowing through the meeting transport."""

    node_id: str
    text: str
    inject_status: str
    platform: str
    meeting_id: Optional[str] = None
    session_id: Optional[str] = None
    role_slug: Optional[str] = None
    user_id: Optional[str] = None
    participant_name: Optional[str] = None
    occurred_at: str = field(default_factory=_utcnow_iso)
    detail: str = ""
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Bounded transport history ───────────────────────────────────────────────


_HISTORY_CAP = 50


class _MeetingTransportHistory:
    def __init__(self, cap: int = _HISTORY_CAP) -> None:
        self._lock = threading.RLock()
        self._rows: list[MeetingTransportEvent] = []
        self._cap = cap

    def record(self, ev: MeetingTransportEvent) -> MeetingTransportEvent:
        with self._lock:
            self._rows.append(ev)
            if len(self._rows) > self._cap:
                drop = len(self._rows) - self._cap
                self._rows = self._rows[drop:]
        return ev

    def latest(
        self, limit: int = 10, node_id: Optional[str] = None
    ) -> list[MeetingTransportEvent]:
        with self._lock:
            rows = list(self._rows)
        if node_id is not None:
            rows = [r for r in rows if r.node_id == node_id]
        rows.sort(key=lambda r: r.occurred_at or "", reverse=True)
        return rows[: max(0, int(limit))]

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


_history_singleton: Optional[_MeetingTransportHistory] = None
_history_singleton_lock = threading.Lock()


def get_meeting_transport_history() -> _MeetingTransportHistory:
    global _history_singleton
    if _history_singleton is None:
        with _history_singleton_lock:
            if _history_singleton is None:
                _history_singleton = _MeetingTransportHistory()
    return _history_singleton


def reset_meeting_transport_history_for_tests() -> None:
    global _history_singleton
    with _history_singleton_lock:
        _history_singleton = None


# ─── Transport adapter ───────────────────────────────────────────────────────


def _build_node_id(platform: str, meeting_id: Optional[str]) -> str:
    if meeting_id:
        # sanitize meeting id for node id legibility
        clean = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in str(meeting_id)
        )
        return f"meeting_{platform}_{clean}"
    return f"meeting_{platform}_default"


class MeetingTransport:
    """Pure adapter from a meeting voice surface to the bounded voice loop.

    Construction is cheap: no network, no browser, no client. The adapter is
    safe to instantiate from any process (operator CLI, smoke test, future
    meeting bridge service).

    Mirrors the DiscordVoiceTransport shape on purpose so operators learn one
    contract for every transport.
    """

    def __init__(
        self,
        *,
        platform: Optional[str] = None,
        meeting_id: Optional[str] = None,
        node_id: Optional[str] = None,
        role_slug: str = "ea_orchestrator",
        ensure_node: bool = True,
    ) -> None:
        self.platform = _normalize_platform(platform)
        self.meeting_id = str(meeting_id) if meeting_id is not None else None
        self.node_id = node_id or _build_node_id(self.platform, self.meeting_id)
        self.role_slug = role_slug
        self._mode = "transcript_only"
        self._playback_enabled = False
        self._attached_sink: Optional[Any] = None
        self._attached_sources: dict[str, dict] = {}
        self._sources_lock = threading.RLock()
        self._playback_attempts: int = 0
        self._playback_by_status: dict[str, int] = {}
        self._playback_last_result: Optional[dict] = None
        if ensure_node:
            self._ensure_node_registered()

    # ── Optional playback / egress sink (bounded contract) ────────────────

    def attach_playback_sink(
        self, sink: Any, *, enabled: bool = True
    ) -> dict[str, Any]:
        """Attach a bounded playback/egress sink.

        The sink contract is intentionally minimal: an object exposing
        ``play_text(text: str) -> Any``. A future real meeting bridge can
        plug a TTS-into-meeting sink here without touching the seam. Until
        then, transcript-only mode is first class — the sink is optional.

        Never raises. Returns a JSON-friendly dict describing the new state.
        """
        if sink is None:
            return {"status": "no_sink"}
        try:
            self._attached_sink = sink
            self._playback_enabled = bool(enabled)
            self._mode = "attached" if self._playback_enabled else "attached_degraded"
            return {
                "status": "attached",
                "playback_enabled": self._playback_enabled,
                "node_id": self.node_id,
            }
        except Exception as e:  # noqa: BLE001
            _log(f"attach_playback_sink failed: {e}")
            return {"status": "attach_failed", "detail": str(e)}

    def detach_playback_sink(self) -> dict[str, Any]:
        """Drop any attached sink and return to transcript-only mode."""
        self._attached_sink = None
        self._playback_enabled = False
        self._mode = "transcript_only"
        return {"status": "detached", "node_id": self.node_id}

    # ── Attached transcript sources (PULL helpers) ────────────────────────

    def attach_source(
        self, source: Any, *, name: Optional[str] = None
    ) -> dict[str, Any]:
        """Attach a meeting transcript source (duck-typed MeetingSourceProtocol).

        The source is a PULL producer — call ``pump_attached_sources()`` to
        drain it through the bounded inject_utterance seam. Push-style
        bridges may continue to call ``inject_utterance`` directly; this
        attach path exists for identity, status reporting, and pull pumps.

        Never raises. Returns a JSON-friendly dict.
        """
        if not is_meeting_source(source):
            return {"status": "rejected", "reason": "invalid_source"}
        resolved = name or getattr(source, "name", None)
        if not isinstance(resolved, str) or not resolved.strip():
            return {"status": "rejected", "reason": "invalid_source"}
        provider = getattr(source, "provider", "generic_meeting") or "generic_meeting"
        with self._sources_lock:
            if resolved in self._attached_sources:
                return {
                    "status": "rejected",
                    "reason": "duplicate_name",
                    "name": resolved,
                }
            self._attached_sources[resolved] = {
                "source": source,
                "provider": provider,
                "attached_at": _utcnow_iso(),
                "last_pump_at": None,
                "last_status": None,
                "last_error": None,
                "pump_count": 0,
            }
        get_meeting_transport_history().record(
            MeetingTransportEvent(
                node_id=self.node_id,
                text="",
                inject_status="source_attached",
                platform=self.platform,
                meeting_id=self.meeting_id,
                detail=f"source={resolved} provider={provider}",
                metadata={"source_name": resolved, "provider": provider},
            )
        )
        return {
            "status": "attached",
            "name": resolved,
            "provider": provider,
            "node_id": self.node_id,
        }

    def detach_source(self, name: str) -> dict[str, Any]:
        """Detach a previously attached source by name. Never raises."""
        with self._sources_lock:
            entry = self._attached_sources.pop(name, None)
        if entry is None:
            return {"status": "noop", "name": name}
        src = entry.get("source")
        try:
            if src is not None and callable(getattr(src, "close", None)):
                src.close()
        except Exception as e:  # noqa: BLE001
            _log(f"detach_source close() failed for {name}: {e}")
        get_meeting_transport_history().record(
            MeetingTransportEvent(
                node_id=self.node_id,
                text="",
                inject_status="source_detached",
                platform=self.platform,
                meeting_id=self.meeting_id,
                detail=f"source={name}",
                metadata={"source_name": name},
            )
        )
        return {"status": "detached", "name": name}

    def list_attached_sources(self) -> list[dict]:
        """Bounded snapshot of attached sources (excludes the live object)."""
        with self._sources_lock:
            out: list[dict] = []
            for name, entry in self._attached_sources.items():
                out.append(
                    {
                        "name": name,
                        "provider": entry.get("provider"),
                        "attached_at": entry.get("attached_at"),
                        "last_pump_at": entry.get("last_pump_at"),
                        "last_status": entry.get("last_status"),
                        "last_error": entry.get("last_error"),
                        "pump_count": entry.get("pump_count", 0),
                    }
                )
        return out

    def pump_attached_sources(self, *, max_per_source: int = 1) -> dict[str, Any]:
        """Drain up to ``max_per_source`` utterances from each attached source.

        Each utterance is routed through ``self.inject_utterance``, tagged
        with ``meeting_source`` and ``meeting_provider`` metadata. Per-source
        exceptions are caught and recorded — pump never raises.
        """
        try:
            limit = max(1, int(max_per_source))
        except Exception:  # noqa: BLE001
            limit = 1
        per_source: dict[str, dict] = {}
        total = 0
        with self._sources_lock:
            items = list(self._attached_sources.items())
        for name, entry in items:
            src = entry.get("source")
            provider = entry.get("provider", "generic_meeting")
            pumped_here = 0
            last_status = "empty"
            last_error: Optional[str] = None
            for _ in range(limit):
                try:
                    u = src.read_utterance() if src is not None else None
                except Exception as e:  # noqa: BLE001
                    last_status = "error"
                    last_error = str(e)
                    break
                if u is None:
                    last_status = "empty" if pumped_here == 0 else "ok"
                    break
                try:
                    self.inject_utterance(
                        text=u.get("text", ""),
                        user_id=u.get("user_id"),
                        participant_name=u.get("participant_name"),
                        metadata={
                            **(u.get("metadata") or {}),
                            "meeting_source": name,
                            "meeting_provider": provider,
                        },
                    )
                    pumped_here += 1
                    total += 1
                    last_status = "ok"
                    # Meeting Intelligence Layer v1 — bounded, additive,
                    # never raises. Summary/intervention/memory on each
                    # successful inject.
                    try:
                        from runtime.transport.meeting_intelligence import (
                            on_utterance_injected,
                        )

                        on_utterance_injected(
                            self.node_id,
                            self.meeting_id,
                            [u],
                        )
                    except Exception:  # noqa: BLE001
                        pass
                except Exception as e:  # noqa: BLE001
                    last_status = "error"
                    last_error = str(e)
                    break
            with self._sources_lock:
                live = self._attached_sources.get(name)
                if live is not None:
                    live["last_pump_at"] = _utcnow_iso()
                    live["last_status"] = last_status
                    live["last_error"] = last_error
                    live["pump_count"] = int(live.get("pump_count", 0)) + pumped_here
            per_source[name] = {"pumped": pumped_here, "last_status": last_status}
            if last_error:
                per_source[name]["last_error"] = last_error
        return {
            "status": "ok",
            "pumped": total,
            "per_source": per_source,
            "node_id": self.node_id,
        }

    def set_playback_enabled(self, enabled: bool) -> dict[str, Any]:
        """Toggle playback on/off without dropping the attached sink."""
        self._playback_enabled = bool(enabled)
        if self._attached_sink is not None:
            self._mode = "attached" if self._playback_enabled else "attached_degraded"
        return {
            "status": "ok",
            "playback_enabled": self._playback_enabled,
            "attached": self._attached_sink is not None,
        }

    def play_reply(self, text: str) -> dict[str, Any]:
        """Bounded playback entry point for an EOS reply.

        Always returns a JSON-friendly dict. If no sink is attached or
        playback is disabled, returns a structured `disabled` result instead
        of raising.
        """
        # Lazy import to keep hot path clean.
        try:
            from runtime.transport.discord_voice_playback import (
                normalize_playback_result,
            )
        except Exception:  # noqa: BLE001
            normalize_playback_result = None  # type: ignore

        def _wrap(out: dict) -> dict:
            if normalize_playback_result is None:
                return out
            try:
                env = normalize_playback_result(
                    out,
                    transport="meeting",
                    text_preview=(text or "").strip()[:80] or None,
                )
                # Additive merge: existing keys win to preserve backward compat.
                merged = dict(env)
                merged.update(out)
                # Ensure envelope-only keys are present even when out has them missing.
                for k in ("transport", "occurred_at", "reason", "queued_depth"):
                    if k not in merged or merged.get(k) is None and k in env:
                        merged[k] = env[k]
                merged["transport"] = "meeting"
                if "occurred_at" not in merged:
                    merged["occurred_at"] = env["occurred_at"]
                return merged
            except Exception:  # noqa: BLE001
                return out

        if self._attached_sink is None or not self._playback_enabled:
            out = {
                "status": "disabled",
                "detail": "no playback sink attached or playback disabled",
            }
            out = _wrap(out)
            self._record_playback(out)
            return out
        clean = (text or "").strip()
        if not clean:
            out = {"status": "empty_text"}
            out = _wrap(out)
            self._record_playback(out)
            return out
        try:
            result = self._attached_sink.play_text(clean)
            if isinstance(result, dict):
                out = {"status": "ok", **result}
            else:
                out = {
                    "status": "ok",
                    "detail": str(result) if result is not None else "",
                }
            out = _wrap(out)
            self._record_playback(out)
            return out
        except Exception as e:  # noqa: BLE001
            out = {"status": "playback_error", "detail": str(e), "kind": "sink_error"}
            out = _wrap(out)
            self._record_playback(out)
            return out

    def _record_playback(self, result: dict) -> None:
        """Bounded in-memory counter for playback observability. Never raises."""
        try:
            self._playback_attempts += 1
            status = str(result.get("status") or "unknown")
            self._playback_by_status[status] = (
                self._playback_by_status.get(status, 0) + 1
            )
            self._playback_last_result = dict(result)
        except Exception:  # noqa: BLE001
            pass

    def playback_status_snapshot(self) -> dict[str, Any]:
        """Shared PlaybackStatusSnapshot dict for this meeting transport."""
        try:
            from runtime.transport.playback_status import (
                make_playback_status_snapshot,
            )

            attached = bool(self._attached_sink)
            enabled = bool(self._playback_enabled)
            if attached and enabled:
                mode = "attached"
            elif attached:
                mode = "attached_degraded"
            else:
                mode = "transcript_only"
            return make_playback_status_snapshot(
                transport="meeting",
                mode=mode,
                attached=attached,
                enabled=enabled,
                busy=False,
                depth=0,
                max_depth=1,
                attempt_count=int(self._playback_attempts),
                by_status=dict(self._playback_by_status),
                last_result=self._playback_last_result,
                recent=[],
            ).as_dict()
        except Exception as e:  # noqa: BLE001
            _log(f"playback_status_snapshot failed: {e}")
            return {
                "transport": "meeting",
                "mode": "transcript_only",
                "attached": False,
                "enabled": False,
                "busy": False,
                "depth": 0,
                "max_depth": 1,
                "attempt_count": 0,
                "by_status": {},
                "last_result": None,
                "recent": [],
            }

    # ── Node registration (best-effort, never raises) ─────────────────────

    def _ensure_node_registered(self) -> None:
        """Register the meeting-side node so VoiceSessionRuntime accepts it.

        VoiceSessionRuntime.start_session validates `node_id` against the
        NodeRegistry. Without this, every transport call would land in an
        ERROR session. We register a LOCAL_STATION node with capabilities
        describing the bounded transport — same posture Discord uses.
        """
        try:
            from runtime.transport.nodes import (
                Node,
                NodeRegistry,
                NodeStatus,
                NodeType,
            )

            reg = NodeRegistry.default()
            existing = reg.get(self.node_id)
            if existing is not None:
                return
            reg.upsert(
                Node(
                    node_id=self.node_id,
                    node_type=NodeType.LOCAL_STATION,
                    capabilities=["voice_transport", "transcript_inject", "meeting"],
                    status=NodeStatus.ONLINE,
                    availability="on_demand",
                    metadata={
                        "transport": "meeting",
                        "platform": self.platform,
                        "meeting_id": self.meeting_id,
                    },
                )
            )
        except Exception as e:  # noqa: BLE001
            _log(f"node registration failed for {self.node_id}: {e}")

    # ── Lifecycle (thin wrappers — no parallel pipeline) ──────────────────

    def start_session(self, role_slug: Optional[str] = None) -> dict[str, Any]:
        """Start (or resume) a bounded voice session for this meeting node."""
        try:
            from runtime.transport.voice_session import (
                VoiceSessionRuntime,
                get_voice_session_store,
            )
        except Exception as e:  # noqa: BLE001
            return {"status": "import_failed", "detail": str(e)}

        role = role_slug or self.role_slug
        store = get_voice_session_store()
        active = store.active(node_id=self.node_id)
        if active:
            s = active[0]
            return {
                "status": "resumed",
                "session_id": s.session_id,
                "role_slug": s.role_slug,
            }
        runtime = VoiceSessionRuntime()
        try:
            session = runtime.start_session(
                self.node_id,
                role_slug=role,
                metadata={
                    "started_by": "meeting_transport",
                    "transport": "meeting",
                    "platform": self.platform,
                    "meeting_id": self.meeting_id,
                },
            )
        except Exception as e:  # noqa: BLE001
            return {"status": "start_failed", "detail": str(e)}
        return {
            "status": session.status.value,
            "session_id": session.session_id,
            "role_slug": session.role_slug,
            "error_reason": session.error_reason,
        }

    def end_session(self, *, reason: Optional[str] = None) -> dict[str, Any]:
        try:
            from runtime.transport.voice_session import (
                VoiceSessionRuntime,
                get_voice_session_store,
            )
        except Exception as e:  # noqa: BLE001
            return {"status": "import_failed", "detail": str(e)}
        store = get_voice_session_store()
        active = store.active(node_id=self.node_id)
        if not active:
            return {"status": "no_active_session"}
        runtime = VoiceSessionRuntime()
        ended = runtime.end_session(
            active[0].session_id,
            reason=reason or "meeting_transport.end_session",
        )
        if ended is None:
            return {"status": "end_failed"}
        return {
            "status": ended.status.value,
            "session_id": ended.session_id,
            "ended_at": ended.ended_at,
        }

    # ── Core: transcript ingestion ────────────────────────────────────────

    def inject_utterance(
        self,
        text: str,
        *,
        user_id: Optional[str] = None,
        participant_name: Optional[str] = None,
        meeting_id: Optional[str] = None,
        role_slug: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Bounded entry point. Mirrors transcript_inject.inject_transcript()
        with `source="meeting_voice"` and meeting-shaped metadata.

        Never raises. Always returns a JSON-friendly dict.
        """
        clean = (text or "").strip()
        meta = {
            "transport": "meeting",
            "platform": self.platform,
            "meeting_id": meeting_id or self.meeting_id,
            "user_id": str(user_id) if user_id is not None else None,
            "participant_name": participant_name,
            **(metadata or {}),
        }

        if not clean:
            ev = MeetingTransportEvent(
                node_id=self.node_id,
                text="",
                inject_status="empty_text",
                platform=self.platform,
                meeting_id=meta.get("meeting_id"),
                user_id=meta.get("user_id"),
                participant_name=participant_name,
                detail="empty text",
                metadata=meta,
            )
            get_meeting_transport_history().record(ev)
            return {"status": "empty_text", "event": ev.as_dict()}

        try:
            from runtime.transport.transcript_inject import inject_transcript
        except Exception as e:  # noqa: BLE001
            return {"status": "import_failed", "detail": str(e)}

        try:
            result = inject_transcript(
                self.node_id,
                clean,
                source="meeting_voice",
                start_if_missing=True,
                role_slug=role_slug or self.role_slug,
                metadata=meta,
            )
        except Exception as e:  # noqa: BLE001
            ev = MeetingTransportEvent(
                node_id=self.node_id,
                text=clean,
                inject_status="exception",
                platform=self.platform,
                meeting_id=meta.get("meeting_id"),
                user_id=meta.get("user_id"),
                participant_name=participant_name,
                detail=f"inject_transcript raised: {e}",
                metadata=meta,
            )
            get_meeting_transport_history().record(ev)
            return {"status": "exception", "detail": str(e), "event": ev.as_dict()}

        ev = MeetingTransportEvent(
            node_id=self.node_id,
            text=clean,
            inject_status=result.get("status", "unknown"),
            platform=self.platform,
            meeting_id=meta.get("meeting_id"),
            session_id=result.get("session_id"),
            role_slug=result.get("role_slug"),
            user_id=meta.get("user_id"),
            participant_name=participant_name,
            detail=result.get("detail", ""),
            metadata=meta,
        )
        get_meeting_transport_history().record(ev)

        # Bounded auto-playback: if a sink is attached AND playback enabled,
        # render the latest AGENT turn through the sink. Failures NEVER raise
        # — they degrade to a structured `playback` field so callers observe.
        playback_outcome: Optional[dict] = None
        if self._playback_enabled and self._attached_sink is not None:
            try:
                reply_text = self._latest_agent_reply(result.get("session_id"))
                if reply_text:
                    playback_outcome = self.play_reply(reply_text)
                else:
                    playback_outcome = {
                        "status": "no_reply",
                        "detail": "no agent turn produced",
                    }
            except Exception as e:  # noqa: BLE001
                playback_outcome = {"status": "playback_error", "detail": str(e)}

        return {
            "status": result.get("status"),
            "session_id": result.get("session_id"),
            "role_slug": result.get("role_slug"),
            "detail": result.get("detail"),
            "audio_loop": result.get("audio_loop"),
            "event": ev.as_dict(),
            "playback": playback_outcome,
        }

    def _latest_agent_reply(self, session_id: Optional[str]) -> Optional[str]:
        """Best-effort: return the most recent AGENT turn text for `session_id`."""
        if not session_id:
            return None
        try:
            from runtime.transport.voice_session import (
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

    # ── Reporting ─────────────────────────────────────────────────────────

    def status_report(self, *, history_limit: int = 10) -> dict[str, Any]:
        """Bounded snapshot of transport mode + capability + recent events."""
        capability = _probe_meeting_capability()

        active_count = 0
        recent_sessions: list[dict] = []
        try:
            from runtime.transport.voice_session import get_voice_session_store

            store = get_voice_session_store()
            active_count = len(store.active(node_id=self.node_id))
            recent_sessions = [
                s.as_dict() for s in store.latest(limit=5, node_id=self.node_id)
            ]
        except Exception as e:  # noqa: BLE001
            _log(f"voice_session_store lookup failed: {e}")

        audio_loop: Optional[dict] = None
        try:
            from runtime.transport.result_query import audio_loop_snapshot

            audio_loop = audio_loop_snapshot(node_id=self.node_id)
        except Exception as e:  # noqa: BLE001
            _log(f"audio_loop_snapshot failed: {e}")

        recent_events = [
            e.as_dict()
            for e in get_meeting_transport_history().latest(
                limit=history_limit, node_id=self.node_id
            )
        ]

        attached_sources = self.list_attached_sources()

        # Mode classification.
        if self._attached_sink is not None:
            mode = "attached" if self._playback_enabled else "attached_degraded"
        elif attached_sources:
            mode = "attached"
        else:
            mode = "transcript_only"

        return {
            "node_id": self.node_id,
            "platform": self.platform,
            "meeting_id": self.meeting_id,
            "role_slug": self.role_slug,
            "mode": mode,
            "playback_enabled": self._playback_enabled,
            "attached_sink": self._attached_sink is not None,
            "attached_sources": attached_sources,
            "capability": capability,
            "active_session_count": active_count,
            "recent_sessions": recent_sessions,
            "recent_events": recent_events,
            "audio_loop": audio_loop,
            "playback_status": self.playback_status_snapshot(),
            "env_hook_enabled": _env_hook_enabled(),
            "playback_env_enabled": _playback_env_enabled(),
            "supported_platforms": sorted(SUPPORTED_PLATFORMS),
            "generated_at": _utcnow_iso(),
        }


# ─── Default singleton (keyed by platform/meeting_id) ────────────────────────


_default_lock = threading.Lock()
_default_transports: dict[tuple, MeetingTransport] = {}


def get_default_meeting_transport(
    *,
    platform: Optional[str] = None,
    meeting_id: Optional[str] = None,
    role_slug: str = "ea_orchestrator",
) -> MeetingTransport:
    """Return (or lazily create) a default transport for (platform, meeting_id).

    The adapter is intentionally cheap to construct, but operators usually
    want one stable instance per meeting for transport history coherence.
    """
    key = (
        _normalize_platform(platform),
        str(meeting_id) if meeting_id else None,
    )
    with _default_lock:
        existing = _default_transports.get(key)
        if existing is not None:
            return existing
        t = MeetingTransport(
            platform=platform,
            meeting_id=meeting_id,
            role_slug=role_slug,
        )
        _default_transports[key] = t
        return t


def reset_default_meeting_transports_for_tests() -> None:
    with _default_lock:
        for t in list(_default_transports.values()):
            try:
                with t._sources_lock:  # noqa: SLF001
                    for name, entry in list(t._attached_sources.items()):  # noqa: SLF001
                        src = entry.get("source")
                        try:
                            if src is not None and callable(
                                getattr(src, "close", None)
                            ):
                                src.close()
                        except Exception:  # noqa: BLE001
                            pass
                    t._attached_sources.clear()  # noqa: SLF001
            except Exception:  # noqa: BLE001
                pass
        _default_transports.clear()


# ─── Env-gated opt-in hook ───────────────────────────────────────────────────


_ENV_HOOK_VAR = "EOS_MEETING_VOICE_TRANSPORT_ENABLED"
_PLAYBACK_ENV_VAR = "EOS_MEETING_VOICE_PLAYBACK_ENABLED"


def _env_hook_enabled() -> bool:
    val = os.getenv(_ENV_HOOK_VAR, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _playback_env_enabled() -> bool:
    val = os.getenv(_PLAYBACK_ENV_VAR, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def maybe_mirror_meeting_utterance(
    text: str,
    *,
    platform: Optional[str] = None,
    meeting_id: Optional[Any] = None,
    user_id: Optional[Any] = None,
    participant_name: Optional[str] = None,
    role_slug: str = "ea_orchestrator",
    metadata: Optional[dict] = None,
) -> Optional[dict[str, Any]]:
    """Opt-in mirror hook for an external meeting bridge.

    Behavior:
      - Returns ``None`` immediately if EOS_MEETING_VOICE_TRANSPORT_ENABLED
        is not truthy. This is the DEFAULT — no behavior change anywhere
        until an operator explicitly opts in.
      - When enabled, calls ``get_default_meeting_transport(...)`` and
        injects the utterance through the bounded seam.
      - Never raises — failures log and return a status dict.
    """
    if not _env_hook_enabled():
        return None
    try:
        transport = get_default_meeting_transport(
            platform=platform,
            meeting_id=meeting_id,
            role_slug=role_slug,
        )
        return transport.inject_utterance(
            text,
            user_id=user_id,
            participant_name=participant_name,
            meeting_id=meeting_id,
            metadata=metadata,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"maybe_mirror_meeting_utterance failed: {e}")
        return {"status": "mirror_failed", "detail": str(e)}


__all__ = [
    "MeetingTransport",
    "MeetingTransportEvent",
    "SUPPORTED_PLATFORMS",
    "get_default_meeting_transport",
    "reset_default_meeting_transports_for_tests",
    "get_meeting_transport_history",
    "reset_meeting_transport_history_for_tests",
    "maybe_mirror_meeting_utterance",
]
