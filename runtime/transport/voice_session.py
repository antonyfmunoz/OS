"""
Voice session — bounded live voice-presence layer for the substrate.

Purpose
-------
This module is the first VOICE PRESENCE MVP on top of the existing
station/ritual substrate. It does NOT introduce streaming audio, STT, or any
new ActionKinds. A "voice session" is a small, deterministic, observable
container around an existing capability the substrate already has:

    user utterance (text-in)
        → routed to a substrate-aware agent role
        → response text
        → emitted via the existing SPEAK_TEXT SafeAction path
          (which the StationDaemon executes via `say` / `espeak` / `spd-say`)

That is the entire MVP. Real STT and a real audio loop plug in later as
*producers* of utterances and *consumers* of TTS outputs, exactly the same
way `wake_word_detected` and `clap_detected` will eventually plug into
local_listener.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path (gateway/cognitive_loop/model_router/agent_runtime/
  primitives) is never imported.
- Bounded. Sessions are an explicit lifecycle (PENDING → ACTIVE → IDLE →
  ENDED/ERROR). Turns are an explicit list capped per session. No freeform
  command parsing. No raw shell. No autonomous mic capture.
- Deterministic. Role resolution flows through RoleRegistry/role_resolver.
  Switching roles is an explicit operator/agent action recorded as a
  role_history entry, not an inferred handoff.
- Reuse, don't rebuild. TTS-oriented output goes through `propose_speak_text`
  so the trust gates (control_mode + MVP allow-list) cannot be bypassed.
- Observable. VoiceSessionStore is dual-layer (in-mem + substrate.storage)
  exactly like ResultStore. Bounded retention. Thread-safe. Singleton.
- Best-effort. Runtime methods never raise into the caller; they degrade
  the session into ERROR with a reason and persist.
- Reversible. Removing this file leaves the substrate exactly as it was;
  the runtime is callable directly and the listener bridge is one optional
  additive method.

What this module does NOT do
----------------------------
- No real STT, no microphone capture, no audio streaming.
- No new station ActionKinds. Output rides SPEAK_TEXT.
- No multi-agent simultaneous speech. One active role per session.
- No agent freeform autonomy. The runtime calls a small pluggable
  `responder` callable; the default just echoes a structured stub
  response so the bounded loop is fully exercised end-to-end without
  pulling the LLM stack into the substrate.
- No Pikastream / meeting platform integration. Out of scope.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from runtime.transport.nodes import NodeRegistry
from runtime.transport.roles import AgentRole, RoleRegistry
from runtime.transport.station_helpers import propose_speak_text

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "voice_sessions"
_MAX_SESSIONS = 100  # bounded retention; oldest-by-started_at dropped on overflow
_MAX_TURNS_PER_SESSION = 50  # per-session embedded turns cap


def _log(msg: str) -> None:
    print(f"[substrate.voice_session] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "vs") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Models ───────────────────────────────────────────────────────────────────


class VoiceSessionStatus(str, Enum):
    """Bounded lifecycle of a single voice session.

    PENDING  — created but no turn has happened yet
    ACTIVE   — at least one turn has occurred and the session is open
    IDLE     — open but no recent activity (left for future timeout sweeps)
    ENDED    — explicitly closed by operator/agent; terminal
    ERROR    — failed during start/turn/switch/end; terminal
    """

    PENDING = "pending"
    ACTIVE = "active"
    IDLE = "idle"
    ENDED = "ended"
    ERROR = "error"

    @property
    def is_terminal(self) -> bool:
        return self in (VoiceSessionStatus.ENDED, VoiceSessionStatus.ERROR)


class VoiceTurnSource(str, Enum):
    """Where a turn came from. Bounded; no freeform sources."""

    USER = "user"  # injected utterance from operator/CLI/listener
    AGENT = "agent"  # response produced by the active agent role
    SYSTEM = "system"  # session lifecycle / role switch / error notice


@dataclass
class VoiceTurn:
    """A single bounded turn within a voice session.

    `action_id` is set when the turn produced a SPEAK_TEXT SafeAction so
    the operator can correlate with ResultStore via result_query.by_action_id.
    """

    turn_id: str
    source: VoiceTurnSource
    text: str
    occurred_at: str
    role_slug: Optional[str] = None  # active role at the moment of the turn
    action_id: Optional[str] = None  # populated when output went via SPEAK_TEXT
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "VoiceTurn":
        return cls(
            turn_id=str(d.get("turn_id", _new_id("vt"))),
            source=VoiceTurnSource(d.get("source", "user")),
            text=str(d.get("text", "")),
            occurred_at=str(d.get("occurred_at") or _utcnow()),
            role_slug=d.get("role_slug"),
            action_id=d.get("action_id"),
            metadata=d.get("metadata") or {},
        )


@dataclass
class VoiceSession:
    """A bounded live voice interaction container.

    Embeds turns directly so the row is a single atomic upsert. Capped per
    session by `_MAX_TURNS_PER_SESSION`; oldest turns drop on overflow.
    """

    session_id: str
    node_id: str
    role_slug: str  # currently active role
    status: VoiceSessionStatus = VoiceSessionStatus.PENDING
    started_at: str = field(default_factory=_utcnow)
    ended_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    turns: list[VoiceTurn] = field(default_factory=list)
    role_history: list[dict] = field(default_factory=list)
    error_reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # — derived helpers —————————————————————————————————————————————

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def last_turn(self) -> Optional[VoiceTurn]:
        return self.turns[-1] if self.turns else None

    # — mutation —————————————————————————————————————————————————

    def append_turn(self, turn: VoiceTurn) -> None:
        self.turns.append(turn)
        if len(self.turns) > _MAX_TURNS_PER_SESSION:
            # Drop oldest, keep newest. Bounded, deterministic.
            drop = len(self.turns) - _MAX_TURNS_PER_SESSION
            self.turns = self.turns[drop:]
        self.last_activity_at = turn.occurred_at
        if self.status == VoiceSessionStatus.PENDING:
            self.status = VoiceSessionStatus.ACTIVE

    def record_role_switch(self, from_slug: str, to_slug: str) -> None:
        self.role_history.append(
            {
                "from": from_slug,
                "to": to_slug,
                "at": _utcnow(),
            }
        )
        self.role_slug = to_slug

    # — serialization —————————————————————————————————————————————

    def as_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "node_id": self.node_id,
            "role_slug": self.role_slug,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "last_activity_at": self.last_activity_at,
            "turns": [t.as_dict() for t in self.turns],
            "role_history": list(self.role_history),
            "error_reason": self.error_reason,
            "metadata": dict(self.metadata),
            # convenience denormals for operator reports
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VoiceSession":
        turns_raw = d.get("turns") or []
        turns: list[VoiceTurn] = []
        if isinstance(turns_raw, list):
            for t in turns_raw:
                if isinstance(t, dict):
                    try:
                        turns.append(VoiceTurn.from_dict(t))
                    except Exception:
                        continue
        try:
            status = VoiceSessionStatus(d.get("status", "pending"))
        except Exception:
            status = VoiceSessionStatus.PENDING
        return cls(
            session_id=str(d.get("session_id") or _new_id("vs")),
            node_id=str(d.get("node_id", "")),
            role_slug=str(d.get("role_slug", "ea_orchestrator")),
            status=status,
            started_at=str(d.get("started_at") or _utcnow()),
            ended_at=d.get("ended_at"),
            last_activity_at=d.get("last_activity_at"),
            turns=turns,
            role_history=list(d.get("role_history") or []),
            error_reason=d.get("error_reason"),
            metadata=dict(d.get("metadata") or {}),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class VoiceSessionStore:
    """Durable, bounded, thread-safe index of VoiceSessions.

    Mirrors ResultStore: dual-layer (in-mem + substrate storage), singleton
    via `get_voice_session_store()`. Best-effort persistence — flush failures
    log and the in-memory state remains correct.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[str, VoiceSession] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence —————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from runtime.transport.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default={}) or {}
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = {}
            rows = raw.get("rows") if isinstance(raw, dict) and "rows" in raw else raw
            if isinstance(rows, dict):
                for sid, row in rows.items():
                    if not isinstance(row, dict):
                        continue
                    try:
                        self._by_id[str(sid)] = VoiceSession.from_dict(row)
                    except Exception:
                        continue
            self._loaded = True

    def _flush(self) -> None:
        # Caller holds the lock.
        try:
            from runtime.transport.storage import get_storage

            payload = {
                "rows": {sid: s.as_dict() for sid, s in self._by_id.items()},
                "updated_at": _utcnow(),
            }
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _enforce_retention(self) -> None:
        # Caller holds the lock.
        if len(self._by_id) <= _MAX_SESSIONS:
            return
        ordered = sorted(
            self._by_id.items(),
            key=lambda kv: kv[1].started_at or "",
        )
        drop = len(self._by_id) - _MAX_SESSIONS
        for sid, _ in ordered[:drop]:
            self._by_id.pop(sid, None)

    # — public api —————————————————————————————————————————————

    def put(self, session: VoiceSession) -> None:
        with self._lock:
            self._by_id[session.session_id] = session
            self._enforce_retention()
            self._flush()

    def get(self, session_id: str) -> Optional[VoiceSession]:
        with self._lock:
            return self._by_id.get(session_id)

    def all(self) -> list[VoiceSession]:
        with self._lock:
            return list(self._by_id.values())

    def by_node(self, node_id: str) -> list[VoiceSession]:
        with self._lock:
            return [s for s in self._by_id.values() if s.node_id == node_id]

    def active(self, node_id: Optional[str] = None) -> list[VoiceSession]:
        with self._lock:
            out = [
                s
                for s in self._by_id.values()
                if not s.status.is_terminal
                and (node_id is None or s.node_id == node_id)
            ]
            out.sort(key=lambda s: s.started_at or "", reverse=True)
            return out

    def latest(
        self, limit: int = 10, node_id: Optional[str] = None
    ) -> list[VoiceSession]:
        with self._lock:
            rows = list(self._by_id.values())
            if node_id is not None:
                rows = [s for s in rows if s.node_id == node_id]
            rows.sort(key=lambda s: s.started_at or "", reverse=True)
            return rows[: max(0, int(limit))]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._by_id)
            by_status: dict[str, int] = {}
            by_role: dict[str, int] = {}
            for s in self._by_id.values():
                k = s.status.value
                by_status[k] = by_status.get(k, 0) + 1
                by_role[s.role_slug] = by_role.get(s.role_slug, 0) + 1
            return {
                "total": total,
                "by_status": by_status,
                "by_role": by_role,
                "cap": _MAX_SESSIONS,
                "max_turns_per_session": _MAX_TURNS_PER_SESSION,
            }

    def clear(self) -> None:
        """Test helper. Drops in-memory rows AND the durable payload."""
        with self._lock:
            self._by_id.clear()
            self._flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)


_store_singleton: Optional[VoiceSessionStore] = None
_store_singleton_lock = threading.Lock()


def get_voice_session_store() -> VoiceSessionStore:
    global _store_singleton
    if _store_singleton is None:
        with _store_singleton_lock:
            if _store_singleton is None:
                _store_singleton = VoiceSessionStore()
    return _store_singleton


def reset_voice_session_store_for_tests() -> None:
    global _store_singleton
    with _store_singleton_lock:
        _store_singleton = None


# ─── Responder hook ───────────────────────────────────────────────────────────

# A responder is the seam where richer agents plug in later. The default
# responder is intentionally a structured stub: it proves the bounded loop
# end-to-end without pulling the LLM stack into the substrate. The hot path
# can later register a real responder via `set_voice_responder(...)`.

VoiceResponder = Callable[["VoiceSession", str], str]


def _default_responder(session: VoiceSession, utterance: str) -> str:
    role_title = session.role_slug
    truncated = utterance.strip()
    if len(truncated) > 160:
        truncated = truncated[:157] + "…"
    return f"[{role_title}] heard: {truncated}"


_responder: VoiceResponder = _default_responder
_responder_lock = threading.Lock()


def set_voice_responder(responder: Optional[VoiceResponder]) -> None:
    """Replace the default echo responder with a real implementation.

    Pass `None` to reset back to the default. Callers (e.g. an EA-aware
    bridge) own all LLM/intelligence concerns; the substrate stays clean.
    """
    global _responder
    with _responder_lock:
        _responder = responder or _default_responder


def _apply_operator_state(session: "VoiceSession", lifecycle: str) -> None:
    """Best-effort hook into the operator state engine. Never raises.

    Lazy import keeps voice_session free of any operator_state import-time
    dependency, and the try/except keeps the substrate fully reversible.
    """
    try:
        from runtime.transport.operator_transitions import apply_voice_session

        apply_voice_session(session, lifecycle=lifecycle)
    except Exception as e:  # noqa: BLE001
        _log(f"operator_state apply_voice_session failed: {e}")


def _call_responder(session: VoiceSession, utterance: str) -> str:
    try:
        return _responder(session, utterance)
    except Exception as e:  # noqa: BLE001
        _log(f"responder failed for session {session.session_id}: {e}")
        return f"[{session.role_slug}] (responder error: {e})"


# ─── Runtime ──────────────────────────────────────────────────────────────────


class VoiceSessionRuntime:
    """Bounded, deterministic voice session runtime.

    All public methods are best-effort: they never raise into the caller.
    On failure they mark the session ERROR with a reason and persist it,
    matching the local_listener emit() pattern.
    """

    def __init__(self, store: Optional[VoiceSessionStore] = None) -> None:
        self._store = store or get_voice_session_store()

    # — lifecycle —————————————————————————————————————————————————

    def start_session(
        self,
        node_id: str,
        role_slug: str = "ea_orchestrator",
        *,
        metadata: Optional[dict] = None,
    ) -> VoiceSession:
        """Start a new voice session targeting `node_id` with `role_slug`.

        Validates: node exists in the registry, role exists in the role
        registry. Either failure produces an ERROR session that is still
        persisted so the operator can see what happened.
        """
        session = VoiceSession(
            session_id=_new_id("vs"),
            node_id=node_id,
            role_slug=role_slug,
            metadata=dict(metadata or {}),
        )

        # Node existence check (no auto-create — same posture as listener).
        try:
            node = NodeRegistry.default().get(node_id)
        except Exception as e:  # noqa: BLE001
            session.status = VoiceSessionStatus.ERROR
            session.error_reason = f"node lookup failed: {e}"
            session.ended_at = _utcnow()
            self._store.put(session)
            return session
        if node is None:
            session.status = VoiceSessionStatus.ERROR
            session.error_reason = f"node {node_id!r} not registered"
            session.ended_at = _utcnow()
            self._store.put(session)
            return session

        # Role validation against the substrate role registry.
        role = self._resolve_role(role_slug)
        if role is None:
            session.status = VoiceSessionStatus.ERROR
            session.error_reason = f"unknown role slug {role_slug!r}"
            session.ended_at = _utcnow()
            self._store.put(session)
            return session

        # Record a system turn so role/start is part of the transcript.
        session.append_turn(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=VoiceTurnSource.SYSTEM,
                text=f"session started with role={role.slug} ({role.title})",
                occurred_at=_utcnow(),
                role_slug=role.slug,
            )
        )
        # append_turn flips PENDING → ACTIVE; that is the desired post-state.
        self._store.put(session)
        _apply_operator_state(session, "started")
        return session

    def end_session(
        self,
        session_id: str,
        *,
        reason: Optional[str] = None,
    ) -> Optional[VoiceSession]:
        session = self._store.get(session_id)
        if session is None:
            return None
        if session.status.is_terminal:
            return session
        session.status = VoiceSessionStatus.ENDED
        session.ended_at = _utcnow()
        session.append_turn(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=VoiceTurnSource.SYSTEM,
                text=f"session ended{f': {reason}' if reason else ''}",
                occurred_at=_utcnow(),
                role_slug=session.role_slug,
            )
        )
        # append_turn would flip status back to ACTIVE — restore terminal state.
        session.status = VoiceSessionStatus.ENDED
        self._store.put(session)
        _apply_operator_state(session, "ended")

        # Audio loop: close the interaction window. Best-effort.
        try:
            from runtime.transport.audio_loop import mark_inactive

            mark_inactive(session.node_id)
        except Exception as e:  # noqa: BLE001
            _log(f"audio_loop mark_inactive failed: {e}")

        return session

    # — turns —————————————————————————————————————————————————————

    def submit_utterance(
        self,
        session_id: str,
        text: str,
        *,
        source: VoiceTurnSource = VoiceTurnSource.USER,
        emit_tts: bool = True,
    ) -> Optional[VoiceSession]:
        """Submit a bounded utterance to the active session.

        Records the user turn, calls the responder for an agent reply, and
        (by default) emits the reply through SPEAK_TEXT so the daemon will
        speak it.
        """
        session = self._store.get(session_id)
        if session is None:
            return None
        if session.status.is_terminal:
            return session

        clean = (text or "").strip()
        if not clean:
            session.append_turn(
                VoiceTurn(
                    turn_id=_new_id("vt"),
                    source=VoiceTurnSource.SYSTEM,
                    text="empty utterance ignored",
                    occurred_at=_utcnow(),
                    role_slug=session.role_slug,
                )
            )
            self._store.put(session)
            return session

        # 1. Record user turn
        session.append_turn(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=source,
                text=clean,
                occurred_at=_utcnow(),
                role_slug=session.role_slug,
            )
        )

        # Audio loop: enter LISTENING_WINDOW + append transcript entry.
        # Best-effort, never raises.
        try:
            from runtime.transport.audio_loop import (
                mark_listening,
                record_transcript,
            )

            mark_listening(session.node_id, voice_session_id=session.session_id)
            record_transcript(
                session.node_id,
                clean,
                source="voice_turn",
                session_id=session.session_id,
                metadata={"role": session.role_slug},
            )
        except Exception as e:  # noqa: BLE001
            _log(f"audio_loop mark_listening failed: {e}")

        # 2. Produce agent response via responder hook
        try:
            response_text = _call_responder(session, clean)
        except Exception as e:  # noqa: BLE001
            response_text = f"[{session.role_slug}] (responder crash: {e})"

        # Audio loop: enter RESPONDING window. Best-effort.
        try:
            from runtime.transport.audio_loop import mark_responding

            mark_responding(session.node_id, voice_session_id=session.session_id)
        except Exception as e:  # noqa: BLE001
            _log(f"audio_loop mark_responding failed: {e}")

        # 3. Emit response — agent turn first so transcript is in order even if TTS fails
        agent_turn = VoiceTurn(
            turn_id=_new_id("vt"),
            source=VoiceTurnSource.AGENT,
            text=response_text,
            occurred_at=_utcnow(),
            role_slug=session.role_slug,
        )

        if emit_tts and response_text:
            try:
                action = propose_speak_text(
                    session.node_id,
                    response_text,
                    issued_by=f"voice_session:{session.role_slug}",
                )
                # SafeAction has an action_id field per actions.py
                agent_turn.action_id = getattr(action, "action_id", None)
            except Exception as e:  # noqa: BLE001
                _log(f"propose_speak_text failed for session {session.session_id}: {e}")
                agent_turn.metadata["tts_error"] = str(e)

        session.append_turn(agent_turn)
        self._store.put(session)
        _apply_operator_state(session, "turn")

        # Audio loop: response emitted — enter COOLING_DOWN. Best-effort.
        try:
            from runtime.transport.audio_loop import mark_cooling_down

            mark_cooling_down(session.node_id)
        except Exception as e:  # noqa: BLE001
            _log(f"audio_loop mark_cooling_down failed: {e}")

        return session

    # — role switching ——————————————————————————————————————————————

    def switch_role(
        self,
        session_id: str,
        new_role_slug: str,
    ) -> Optional[VoiceSession]:
        session = self._store.get(session_id)
        if session is None:
            return None
        if session.status.is_terminal:
            return session

        new_role = self._resolve_role(new_role_slug)
        if new_role is None:
            session.append_turn(
                VoiceTurn(
                    turn_id=_new_id("vt"),
                    source=VoiceTurnSource.SYSTEM,
                    text=f"role switch rejected: unknown slug {new_role_slug!r}",
                    occurred_at=_utcnow(),
                    role_slug=session.role_slug,
                )
            )
            self._store.put(session)
            return session

        if new_role.slug == session.role_slug:
            session.append_turn(
                VoiceTurn(
                    turn_id=_new_id("vt"),
                    source=VoiceTurnSource.SYSTEM,
                    text=f"role switch noop: already {new_role.slug}",
                    occurred_at=_utcnow(),
                    role_slug=session.role_slug,
                )
            )
            self._store.put(session)
            return session

        previous = session.role_slug
        session.record_role_switch(previous, new_role.slug)
        session.append_turn(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=VoiceTurnSource.SYSTEM,
                text=f"role switched: {previous} → {new_role.slug}",
                occurred_at=_utcnow(),
                role_slug=new_role.slug,
            )
        )
        self._store.put(session)
        return session

    # — internals —————————————————————————————————————————————————

    @staticmethod
    def _resolve_role(role_slug: str) -> Optional[AgentRole]:
        if not role_slug:
            return None
        try:
            return RoleRegistry.default().get(role_slug)
        except Exception:
            return None


# ─── Reporting ────────────────────────────────────────────────────────────────


def voice_session_report(
    node_id: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """Compact, JSON-friendly operator report on voice presence activity."""
    store = get_voice_session_store()
    active = [s.as_dict() for s in store.active(node_id=node_id)]
    recent = [s.as_dict() for s in store.latest(limit=limit, node_id=node_id)]

    last = recent[0] if recent else None
    last_turn = None
    last_role = None
    if last:
        turns = last.get("turns") or []
        if turns:
            last_turn = turns[-1]
        last_role = last.get("role_slug")

    return {
        "node_id": node_id,
        "active_count": len(active),
        "active_sessions": active,
        "recent_sessions": recent,
        "last_session_id": last.get("session_id") if last else None,
        "last_role": last_role,
        "last_turn": last_turn,
        "stats": store.stats(),
    }
