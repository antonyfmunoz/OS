"""Runtime session registry — in-memory source of truth for session identity.

Decouples session identity from execution node and tmux session name.
A session persists across node failover, transport switches, and reconnects.

Design rules:
- In-memory only — no persistence yet
- Thread-safe via threading.Lock
- No substrate imports — this is runtime-layer
- No IO — pure state management
- Aligns with RuntimeContext.runtime_session_id
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class SessionRecord:
    """Immutable snapshot of a session's state."""

    session_id: str
    session_name: str
    mode: str
    node: str
    channel_id: str
    transport: str
    status: str
    last_activity_ts: float
    created_ts: float
    last_opened_ts: float = 0.0
    last_closed_ts: float = 0.0
    objective: str | None = None
    progress: dict | None = None

    def with_updates(self, **kwargs: Any) -> SessionRecord:
        return replace(self, **kwargs)

    @property
    def tmux_name(self) -> str:
        """Derived tmux session name. Never hardcoded — always computed."""
        return derive_tmux_name(self)


def derive_tmux_name(session: SessionRecord) -> str:
    """Single source of tmux session name derivation.

    Format: dex_{mode}_{session_id_prefix}
    Deterministic for the same session_id.
    """
    prefix = (
        session.session_id[:12] if len(session.session_id) >= 12 else session.session_id
    )
    raw = f"dex_{session.mode}_{prefix}"
    return _sanitize_tmux_name(raw)


def _sanitize_tmux_name(name: str) -> str:
    for ch in (":", ".", "\n", "\r", "\t"):
        name = name.replace(ch, "_")
    return name[:120]


def _fire_lifecycle(hook_name: str, session: SessionRecord) -> None:
    """Fire a lifecycle hook outside the registry lock. Never raises."""
    try:
        from umh.runtime_loop.lifecycle_hooks import fire_hook

        fire_hook(hook_name, session)
    except Exception:
        pass


_VALID_STATUSES = frozenset({"active", "idle", "closed"})
_VALID_MODES = frozenset({"builder", "product", "unknown"})
_VALID_TRANSPORTS = frozenset({"discord", "voice", "api"})


class SessionRegistry:
    """In-memory registry of active sessions.

    Thread-safe. Singleton access via get_registry().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionRecord] = {}
        self._channel_index: dict[str, str] = {}

    def register_session(
        self,
        session_name: str,
        mode: str,
        node: str,
        channel_id: str,
        transport: str = "discord",
        session_id: str | None = None,
    ) -> SessionRecord:
        """Register a new session or return existing if already registered.

        Idempotent: if a session with the same session_name + channel_id
        exists and is not closed, returns the existing record.
        """
        with self._lock:
            existing_id = self._channel_index.get(channel_id)
            if existing_id and existing_id in self._sessions:
                existing = self._sessions[existing_id]
                if existing.status != "closed":
                    updated = existing.with_updates(
                        last_activity_ts=time.time(),
                        node=node,
                    )
                    self._sessions[existing_id] = updated
                    return updated

            now = time.time()
            sid = session_id or f"ses_{uuid.uuid4().hex[:12]}"
            record = SessionRecord(
                session_id=sid,
                session_name=session_name,
                mode=mode,
                node=node,
                channel_id=channel_id,
                transport=transport,
                status="active",
                last_activity_ts=now,
                created_ts=now,
                last_opened_ts=now,
            )
            self._sessions[sid] = record
            self._channel_index[channel_id] = sid
            _fire_lifecycle("on_open", record)
            return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[SessionRecord]:
        with self._lock:
            return [s for s in self._sessions.values() if s.status == "active"]

    def update_activity(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec:
                return None
            updated = rec.with_updates(last_activity_ts=time.time())
            self._sessions[session_id] = updated
            return updated

    def set_status(self, session_id: str, status: str) -> SessionRecord | None:
        if status not in _VALID_STATUSES:
            return None
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec:
                return None
            now = time.time()
            updates: dict[str, Any] = {
                "status": status,
                "last_activity_ts": now,
            }
            if status == "active" and rec.status in ("idle", "closed"):
                updates["last_opened_ts"] = now
            elif status == "closed":
                updates["last_closed_ts"] = now
            previous_status = rec.status
            updated = rec.with_updates(**updates)
            self._sessions[session_id] = updated
            if status == "closed":
                self._channel_index.pop(rec.channel_id, None)
        if status != previous_status:
            if status == "active":
                _fire_lifecycle("on_active", updated)
            elif status == "idle":
                _fire_lifecycle("on_idle", updated)
            elif status == "closed":
                _fire_lifecycle("on_close", updated)
        return updated

    def resolve_by_channel(self, channel_id: str) -> SessionRecord | None:
        with self._lock:
            sid = self._channel_index.get(channel_id)
            if sid and sid in self._sessions:
                rec = self._sessions[sid]
                if rec.status != "closed":
                    return rec
            return None

    def resolve_or_create(
        self,
        session_name: str,
        mode: str,
        node: str,
        channel_id: str,
        transport: str = "discord",
    ) -> SessionRecord:
        """Main entry point: find existing session or create new one.

        Lifecycle transitions:
        - Existing active → update activity (stay ACTIVE)
        - Existing idle → re-activate (IDLE → ACTIVE, update last_opened_ts)
        - Existing closed → ignored, create new session
        - None → create new session (OPEN → ACTIVE)
        """
        existing = self.resolve_by_channel(channel_id)
        if existing:
            now = time.time()
            with self._lock:
                updates: dict[str, Any] = {
                    "last_activity_ts": now,
                    "node": node,
                    "session_name": session_name,
                }
                was_idle = existing.status == "idle"
                if was_idle:
                    updates["status"] = "active"
                    updates["last_opened_ts"] = now
                updated = existing.with_updates(**updates)
                self._sessions[existing.session_id] = updated
            if was_idle:
                _fire_lifecycle("on_active", updated)
            return updated
        return self.register_session(
            session_name=session_name,
            mode=mode,
            node=node,
            channel_id=channel_id,
            transport=transport,
        )

    def set_objective(
        self, session_id: str, objective: str | None
    ) -> SessionRecord | None:
        """Set or clear the session objective."""
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec or rec.status == "closed":
                return None
            updated = rec.with_updates(
                objective=objective,
                last_activity_ts=time.time(),
            )
            self._sessions[session_id] = updated
            return updated

    def get_objective(self, session_id: str) -> str | None:
        """Return the current objective for a session, or None."""
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec:
                return None
            return rec.objective

    def update_progress(
        self,
        session_id: str,
        events: list,
    ) -> SessionRecord | None:
        """Update objective progress based on emitted events.

        Counts ritual_step_executed and action_completed as steps.
        Sets status to "complete" on ritual_completed.
        """
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec or rec.status == "closed" or rec.objective is None:
                return None

            current = rec.progress or {
                "steps_completed": 0,
                "last_event": "",
                "status": "active",
            }
            if current["status"] == "complete":
                return rec

            steps = current["steps_completed"]
            last_event = current["last_event"]
            status = current["status"]

            for ev in events:
                et = getattr(ev, "event_type", None) or ""
                if et in ("ritual_step_executed", "action_completed"):
                    steps += 1
                    last_event = et
                if et == "ritual_completed":
                    status = "complete"
                    last_event = et

            new_progress = {
                "steps_completed": steps,
                "last_event": last_event,
                "status": status,
            }
            updated = rec.with_updates(
                progress=new_progress,
                last_activity_ts=time.time(),
            )
            self._sessions[session_id] = updated
            return updated

    def get_progress(self, session_id: str) -> dict | None:
        """Return the current progress dict for a session, or None."""
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec:
                return None
            return rec.progress

    def update_node(self, session_id: str, node: str) -> SessionRecord | None:
        """Update the execution node for a session (e.g. on failover)."""
        with self._lock:
            rec = self._sessions.get(session_id)
            if not rec:
                return None
            updated = rec.with_updates(node=node, last_activity_ts=time.time())
            self._sessions[session_id] = updated
            return updated

    def close_session(self, session_id: str) -> SessionRecord | None:
        """Full CLOSED transition: set status, clear objective, detach all surfaces.

        Returns the updated record, or None if session_id not found.
        """
        self.set_objective(session_id, None)
        with self._lock:
            r = self._sessions.get(session_id)
            if r:
                self._sessions[session_id] = r.with_updates(progress=None)
        rec = self.set_status(session_id, "closed")
        if rec is None:
            return None
        try:
            from umh.runtime_loop.surface_registry import get_surface_registry

            detached = get_surface_registry().detach_all(session_id)
            if detached:
                import sys

                print(
                    f"[session_registry] closed {session_id}: "
                    f"detached {len(detached)} surface(s)",
                    file=sys.stderr,
                )
        except Exception:
            pass
        return rec

    def get_idle_sessions(self) -> list[SessionRecord]:
        """Return all sessions with status 'idle'."""
        with self._lock:
            return [s for s in self._sessions.values() if s.status == "idle"]

    def resolve_by_session_name(self, session_name: str) -> SessionRecord | None:
        """Find active session by tmux session name (for webhook receiver).

        Checks both the derived tmux_name and the stored session_name field
        for backward compatibility with legacy session names.
        """
        with self._lock:
            for rec in self._sessions.values():
                if rec.status == "closed":
                    continue
                if rec.tmux_name == session_name or rec.session_name == session_name:
                    return rec
            return None

    def snapshot(self) -> dict[str, Any]:
        """Observability: return full registry state."""
        with self._lock:
            return {
                "session_count": len(self._sessions),
                "active_count": sum(
                    1 for s in self._sessions.values() if s.status == "active"
                ),
                "sessions": {
                    sid: {
                        "session_name": r.session_name,
                        "mode": r.mode,
                        "node": r.node,
                        "channel_id": r.channel_id,
                        "transport": r.transport,
                        "status": r.status,
                        "last_activity_ts": r.last_activity_ts,
                        "created_ts": r.created_ts,
                        "last_opened_ts": r.last_opened_ts,
                        "last_closed_ts": r.last_closed_ts,
                        "objective": r.objective,
                        "progress": r.progress,
                    }
                    for sid, r in self._sessions.items()
                },
            }


_SINGLETON: SessionRegistry | None = None
_SINGLETON_LOCK = threading.Lock()


def get_registry() -> SessionRegistry:
    """Return the process-wide session registry singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = SessionRegistry()
    return _SINGLETON
