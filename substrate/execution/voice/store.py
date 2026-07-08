"""Canonical voice record store — the ONE durable home for voice sessions.

P4S31 Voice Convergence. This module is the single durable store for voice
sessions across every surface (web, mobile web, Electron, Capacitor, CLI,
Discord). It is the fold target for the record + turn store that previously
lived in ``substrate/execution/bridge/voice_session.py`` (that module becomes a
compat re-export shim).

Renames on the way in (to end the name collision with the *runtime*
``substrate.execution.voice.session.VoiceSession``):

- ``VoiceSession``        (bridge dataclass row) → ``VoiceSessionRecord``
- ``VoiceSessionStatus``  (bridge lifecycle enum) → ``VoiceSessionRecordStatus``

``VoiceTurn`` / ``VoiceTurnSource`` fold in unchanged (names already distinct).

Preserved exactly (so already-persisted rows keep loading):
- storage key ``voice_sessions``
- dual-layer persistence (in-mem + ``substrate.execution.bridge.storage``)
- bounded retention (oldest-by-started_at dropped), thread-safety, singleton.

Added by convergence:
- ``STATUS_MAP`` / ``RECORD_TO_RUNTIME_STATUS`` — TOTAL bidirectional map between
  the runtime's operational status (``VoiceSessionStatus`` in ``session.py``:
  idle/listening/processing/speaking/error) and the record's lifecycle status
  (pending/active/idle/ended/error). Total in both directions — every member
  maps, no ``KeyError`` possible.
- ``exchange_to_turns`` / ``turn_to_exchange`` — map the runtime's
  ``VoiceExchange`` (utterance→response) to persisted ``VoiceTurn`` rows and back
  so the one runtime can emit records into this store.

UMH substrate subsystem. Instance-agnostic. Transcript/audio content is never
logged here (logging law: only ids/energy/status/counts are non-secret).
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "voice_sessions"  # UNCHANGED — existing persisted rows keep loading
_MAX_SESSIONS = 100  # bounded retention; oldest-by-started_at dropped on overflow
_MAX_TURNS_PER_SESSION = 50  # per-session embedded turns cap


def _log(msg: str) -> None:
    print(f"[substrate.voice.store] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "vs") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Record status (formerly bridge VoiceSessionStatus) ───────────────────────


class VoiceSessionRecordStatus(str, Enum):
    """Bounded lifecycle of a persisted voice-session record.

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
        return self in (VoiceSessionRecordStatus.ENDED, VoiceSessionRecordStatus.ERROR)


class VoiceTurnSource(str, Enum):
    """Where a turn came from. Bounded; no freeform sources."""

    USER = "user"  # injected utterance from operator/CLI/listener/capture edge
    AGENT = "agent"  # response produced by the active agent role / runtime
    SYSTEM = "system"  # session lifecycle / role switch / error notice


@dataclass
class VoiceTurn:
    """A single bounded turn within a voice-session record.

    ``action_id`` is set when the turn produced a SPEAK_TEXT SafeAction so the
    operator can correlate with ResultStore via ``result_query.by_action_id``.
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
class VoiceSessionRecord:
    """A bounded, persisted voice-session record (formerly bridge VoiceSession).

    Embeds turns directly so the row is a single atomic upsert. Capped per
    session by ``_MAX_TURNS_PER_SESSION``; oldest turns drop on overflow.
    """

    session_id: str
    node_id: str
    role_slug: str  # currently active role
    status: VoiceSessionRecordStatus = VoiceSessionRecordStatus.PENDING
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
        if self.status == VoiceSessionRecordStatus.PENDING:
            self.status = VoiceSessionRecordStatus.ACTIVE

    def record_role_switch(self, from_slug: str, to_slug: str) -> None:
        self.role_history.append({"from": from_slug, "to": to_slug, "at": _utcnow()})
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
    def from_dict(cls, d: dict) -> "VoiceSessionRecord":
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
            status = VoiceSessionRecordStatus(d.get("status", "pending"))
        except Exception:
            status = VoiceSessionRecordStatus.PENDING
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


# ─── Status bridge: runtime operational status <-> record lifecycle status ─────
#
# The runtime (session.py) tracks an OPERATIONAL status while a turn is in
# flight (idle/listening/processing/speaking/error). The record tracks a
# LIFECYCLE status (pending/active/idle/ended/error). These maps are TOTAL in
# both directions — every member has an image, so no KeyError is ever possible.
# String keys/values are used so callers need not import the runtime enum here
# (keeps this module import-light and avoids a cycle with session.py).

# runtime operational status value -> record lifecycle status
STATUS_MAP: dict[str, VoiceSessionRecordStatus] = {
    "idle": VoiceSessionRecordStatus.IDLE,
    "listening": VoiceSessionRecordStatus.ACTIVE,
    "processing": VoiceSessionRecordStatus.ACTIVE,
    "speaking": VoiceSessionRecordStatus.ACTIVE,
    "error": VoiceSessionRecordStatus.ERROR,
}

# record lifecycle status -> runtime operational status value
RECORD_TO_RUNTIME_STATUS: dict[VoiceSessionRecordStatus, str] = {
    VoiceSessionRecordStatus.PENDING: "idle",
    VoiceSessionRecordStatus.ACTIVE: "listening",
    VoiceSessionRecordStatus.IDLE: "idle",
    VoiceSessionRecordStatus.ENDED: "idle",
    VoiceSessionRecordStatus.ERROR: "error",
}


def runtime_status_to_record(runtime_status: str) -> VoiceSessionRecordStatus:
    """Map a runtime operational status value to a record lifecycle status.

    Total: an unknown status falls back to ACTIVE (a live turn), never raises.
    """
    return STATUS_MAP.get(runtime_status, VoiceSessionRecordStatus.ACTIVE)


def record_status_to_runtime(status: VoiceSessionRecordStatus) -> str:
    """Map a record lifecycle status to a runtime operational status value.

    Total: an unknown status falls back to ``idle``, never raises.
    """
    return RECORD_TO_RUNTIME_STATUS.get(status, "idle")


# ─── Exchange <-> turn mappers ─────────────────────────────────────────────────
#
# The runtime emits ``VoiceExchange`` (one utterance + its response). A single
# exchange persists as up to two ``VoiceTurn`` rows: a USER turn (the utterance)
# and, when the runtime responded, an AGENT turn (the response text). These
# mappers let the one runtime write into this store without importing the store's
# internals into its hot loop.


def exchange_to_turns(
    utterance: str,
    response_text: str,
    responded: bool,
    *,
    role_slug: Optional[str] = None,
    action_id: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> list[VoiceTurn]:
    """Build the persisted turn rows for one runtime exchange.

    Always emits a USER turn for a non-empty utterance; emits an AGENT turn only
    when the runtime actually responded with text. Empty-utterance/no-response
    exchanges (silence classifications) yield an empty list — nothing to persist.
    """
    ts = occurred_at or _utcnow()
    turns: list[VoiceTurn] = []
    if utterance and utterance.strip():
        turns.append(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=VoiceTurnSource.USER,
                text=utterance,
                occurred_at=ts,
                role_slug=role_slug,
            )
        )
    if responded and response_text and response_text.strip():
        turns.append(
            VoiceTurn(
                turn_id=_new_id("vt"),
                source=VoiceTurnSource.AGENT,
                text=response_text,
                occurred_at=ts,
                role_slug=role_slug,
                action_id=action_id,
            )
        )
    return turns


def turn_to_exchange(turns: list[VoiceTurn]) -> dict[str, Any]:
    """Collapse a USER(+AGENT) turn pair back into an exchange-shaped dict.

    Inverse of ``exchange_to_turns`` for read paths (reports, replay). Returns a
    flat dict rather than importing the runtime's ``VoiceExchange`` dataclass, to
    keep this module free of a cycle with ``session.py``.
    """
    utterance = ""
    response_text = ""
    responded = False
    action_id: Optional[str] = None
    occurred_at = ""
    for t in turns:
        if t.source == VoiceTurnSource.USER and not utterance:
            utterance = t.text
            occurred_at = occurred_at or t.occurred_at
        elif t.source == VoiceTurnSource.AGENT:
            response_text = t.text
            responded = True
            action_id = t.action_id
            occurred_at = occurred_at or t.occurred_at
    return {
        "utterance": utterance,
        "response_text": response_text,
        "responded": responded,
        "action_id": action_id,
        "occurred_at": occurred_at,
    }


# ─── Store ────────────────────────────────────────────────────────────────────


class VoiceSessionStore:
    """Durable, bounded, thread-safe index of ``VoiceSessionRecord`` rows.

    Mirrors ResultStore: dual-layer (in-mem + substrate storage), singleton via
    ``get_voice_session_store()``. Best-effort persistence — flush failures log
    and the in-memory state remains correct.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[str, VoiceSessionRecord] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence —————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from substrate.execution.bridge.storage import get_storage

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
                        self._by_id[str(sid)] = VoiceSessionRecord.from_dict(row)
                    except Exception:
                        continue
            self._loaded = True

    def _flush(self) -> None:
        # Caller holds the lock.
        try:
            from substrate.execution.bridge.storage import get_storage

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
        ordered = sorted(self._by_id.items(), key=lambda kv: kv[1].started_at or "")
        drop = len(self._by_id) - _MAX_SESSIONS
        for sid, _ in ordered[:drop]:
            self._by_id.pop(sid, None)

    # — public api —————————————————————————————————————————————

    def put(self, session: VoiceSessionRecord) -> None:
        with self._lock:
            self._by_id[session.session_id] = session
            self._enforce_retention()
            self._flush()

    def get(self, session_id: str) -> Optional[VoiceSessionRecord]:
        with self._lock:
            return self._by_id.get(session_id)

    def all(self) -> list[VoiceSessionRecord]:
        with self._lock:
            return list(self._by_id.values())

    def by_node(self, node_id: str) -> list[VoiceSessionRecord]:
        with self._lock:
            return [s for s in self._by_id.values() if s.node_id == node_id]

    def active(self, node_id: Optional[str] = None) -> list[VoiceSessionRecord]:
        with self._lock:
            out = [
                s
                for s in self._by_id.values()
                if not s.status.is_terminal and (node_id is None or s.node_id == node_id)
            ]
            out.sort(key=lambda s: s.started_at or "", reverse=True)
            return out

    def latest(self, limit: int = 10, node_id: Optional[str] = None) -> list[VoiceSessionRecord]:
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
