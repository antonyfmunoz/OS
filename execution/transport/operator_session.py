"""
Operator session spine — single authoritative source of truth for the
operator's daily lifecycle state.

Purpose
-------
While operator_state.py tracks per-node voice/wake FSM state (OperatorMode),
this module tracks the *daily session lifecycle*: whether the day is open,
which workspace was last active, continuity notes for the next open, and
pointers to the rituals that bookend the day.

OperatorDayMode is intentionally SEPARATE from OperatorMode:
  - OperatorMode (operator_state.py) — per-node, high-frequency, FSM-driven
    by wake/voice events (IDLE → STARTING → ACTIVE → FOCUSED → CLOSING → …)
  - OperatorDayMode (this file) — daily-level, low-frequency, set intentionally
    (INACTIVE → REMOTE_ACTIVE | LOCAL_ACTIVE | DEEP_WORK | OVERNIGHT → INACTIVE)

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path never imported here.
- Bounded. One record, not a collection.
- Best-effort. All public methods catch and log; never raise into callers.
- Deterministic. Storage layout is a single keyed JSON blob.
- Reversible. Removing this file leaves the substrate exactly as it was.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "operator_session"


def _log(msg: str) -> None:
    print(f"[substrate.operator_session] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "ds") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Enum ─────────────────────────────────────────────────────────────────────


class OperatorDayMode(str, Enum):
    """Daily lifecycle posture of the operator.

    Distinct from OperatorMode (voice/wake FSM). Set explicitly at open_day /
    close_day or by the operator via Discord command.

    INACTIVE       — no active day session (default between close and next open)
    REMOTE_ACTIVE  — working away from the primary workstation (mobile, travel)
    LOCAL_ACTIVE   — at the primary workstation, full capability
    DEEP_WORK      — focus block; non-urgent notifications suppressed
    OVERNIGHT      — day is closed; system can run overnight tasks autonomously
    """

    INACTIVE = "inactive"
    REMOTE_ACTIVE = "remote_active"
    LOCAL_ACTIVE = "local_active"
    DEEP_WORK = "deep_work"
    OVERNIGHT = "overnight"


# ─── Dataclass ────────────────────────────────────────────────────────────────


@dataclass
class OperatorSession:
    """Unified bounded operator session state for daily lifecycle management.

    One record exists at a time. Created fresh on open_day; updated throughout
    the day; closed at close_day with continuity fields written for the next open.
    """

    # Identity
    day_session_id: str

    # Lifecycle posture
    day_mode: OperatorDayMode = OperatorDayMode.INACTIVE

    # Session lifecycle
    is_day_open: bool = False

    # Workspace / routing
    active_workspace: str = "builder"  # "product" | "builder"
    node_preference: str = "auto"  # "auto" | "local" | "vps"
    last_active_node: Optional[str] = None
    last_active_discord_channel_id: Optional[str] = None
    active_tmux_session: Optional[str] = None
    active_scene: Optional[str] = None

    # Ritual pointers
    ritual_open_id: Optional[str] = None
    ritual_close_id: Optional[str] = None

    # Timestamps
    created_at: str = field(default_factory=_utcnow)
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    updated_at: str = field(default_factory=_utcnow)

    # Continuity — written at close, read at next open
    last_briefing_summary: Optional[str] = None
    unfinished_priorities: list = field(default_factory=list)
    overnight_tasks: list = field(default_factory=list)
    continuity_notes_for_next_open: Optional[str] = None
    last_resume_context: Optional[str] = None

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(cls) -> "OperatorSession":
        """Create a fresh OperatorSession with a new ID and current timestamps."""
        now = _utcnow()
        return cls(
            day_session_id=_new_id("ds"),
            created_at=now,
            updated_at=now,
        )

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict. Enums serialized as their .value."""
        return {
            "day_session_id": self.day_session_id,
            "day_mode": self.day_mode.value,
            "is_day_open": self.is_day_open,
            "active_workspace": self.active_workspace,
            "node_preference": self.node_preference,
            "last_active_node": self.last_active_node,
            "last_active_discord_channel_id": self.last_active_discord_channel_id,
            "active_tmux_session": self.active_tmux_session,
            "active_scene": self.active_scene,
            "ritual_open_id": self.ritual_open_id,
            "ritual_close_id": self.ritual_close_id,
            "created_at": self.created_at,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "updated_at": self.updated_at,
            "last_briefing_summary": self.last_briefing_summary,
            "unfinished_priorities": list(self.unfinished_priorities),
            "overnight_tasks": list(self.overnight_tasks),
            "continuity_notes_for_next_open": self.continuity_notes_for_next_open,
            "last_resume_context": self.last_resume_context,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OperatorSession":
        """Deserialize from a dict, reconstructing enums and guarding list fields."""
        try:
            day_mode = OperatorDayMode(d.get("day_mode", "inactive"))
        except Exception:
            day_mode = OperatorDayMode.INACTIVE

        raw_priorities = d.get("unfinished_priorities")
        unfinished_priorities: list = (
            list(raw_priorities) if isinstance(raw_priorities, list) else []
        )

        raw_overnight = d.get("overnight_tasks")
        overnight_tasks: list = (
            list(raw_overnight) if isinstance(raw_overnight, list) else []
        )

        return cls(
            day_session_id=str(d.get("day_session_id") or _new_id("ds")),
            day_mode=day_mode,
            is_day_open=bool(d.get("is_day_open", False)),
            active_workspace=str(d.get("active_workspace", "builder")),
            node_preference=str(d.get("node_preference", "auto")),
            last_active_node=d.get("last_active_node"),
            last_active_discord_channel_id=d.get("last_active_discord_channel_id"),
            active_tmux_session=d.get("active_tmux_session"),
            active_scene=d.get("active_scene"),
            ritual_open_id=d.get("ritual_open_id"),
            ritual_close_id=d.get("ritual_close_id"),
            created_at=str(d.get("created_at") or _utcnow()),
            opened_at=d.get("opened_at"),
            closed_at=d.get("closed_at"),
            updated_at=str(d.get("updated_at") or _utcnow()),
            last_briefing_summary=d.get("last_briefing_summary"),
            unfinished_priorities=unfinished_priorities,
            overnight_tasks=overnight_tasks,
            continuity_notes_for_next_open=d.get("continuity_notes_for_next_open"),
            last_resume_context=d.get("last_resume_context"),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class OperatorSessionStore:
    """Durable, thread-safe, singleton store for a single OperatorSession record.

    Dual-layer: in-memory + substrate.storage (Neon-backed, JSON fallback).
    Best-effort persistence — flush failures log and the in-memory state
    remains correct.

    Holds ONE record (not a collection). Calling put() replaces whatever is
    currently stored.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._session: Optional[OperatorSession] = None
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from execution.transport.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                try:
                    self._session = OperatorSession.from_dict(raw)
                except Exception as e:  # noqa: BLE001
                    _log(f"deserialize failed ({e}); starting empty")
                    self._session = None
            self._loaded = True

    def _flush(self) -> None:
        try:
            from execution.transport.storage import get_storage

            payload = self._session.to_dict() if self._session is not None else None
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    # — public api ───────────────────────────────────────────────────────────

    def get(self) -> Optional[OperatorSession]:
        """Return the current session record, or None if none has been stored."""
        with self._lock:
            return self._session

    def put(self, session: OperatorSession) -> None:
        """Persist a session record.

        Sets updated_at on the passed session in place, then flushes to
        storage. Flush failures are caught inside _flush() (best-effort).
        """
        with self._lock:
            session.updated_at = _utcnow()
            self._session = session
            self._flush()

    # — singleton ────────────────────────────────────────────────────────────

    _default: Optional["OperatorSessionStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "OperatorSessionStore":
        """Return the process-level singleton, creating it on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton so the next call to default() creates a fresh instance."""
        with cls._default_lock:
            cls._default = None


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "OperatorDayMode",
    "OperatorSession",
    "OperatorSessionStore",
]
