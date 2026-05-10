"""Phase 77 session state — tracks the active operator session.

Sessions are identity-scoped and track active mode, traces, tasks,
and continuity notes.  No direct execution, no adapter calls.
Persistence-capable with in-memory fallback.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class SessionState:
    session_id: str
    user_id: str
    workstation_id: str = ""
    active_mode: str = "command_center"
    started_at: str = ""
    updated_at: str = ""
    active_environment: str = "local"
    active_device: str = "default_vps"
    active_trace_ids: list[str] = field(default_factory=list)
    active_task_ids: list[str] = field(default_factory=list)
    pending_approval_ids: list[str] = field(default_factory=list)
    last_input_summary: str = ""
    last_result_summary: str = ""
    continuity_notes: list[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workstation_id": self.workstation_id,
            "active_mode": self.active_mode,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "active_environment": self.active_environment,
            "active_device": self.active_device,
            "active_trace_ids": self.active_trace_ids,
            "active_task_ids": self.active_task_ids,
            "pending_approval_ids": self.pending_approval_ids,
            "last_input_summary": self.last_input_summary,
            "last_result_summary": self.last_result_summary,
            "continuity_notes": self.continuity_notes,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionState:
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id", ""),
            workstation_id=data.get("workstation_id", ""),
            active_mode=data.get("active_mode", "command_center"),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
            active_environment=data.get("active_environment", "local"),
            active_device=data.get("active_device", "default_vps"),
            active_trace_ids=data.get("active_trace_ids", []),
            active_task_ids=data.get("active_task_ids", []),
            pending_approval_ids=data.get("pending_approval_ids", []),
            last_input_summary=data.get("last_input_summary", ""),
            last_result_summary=data.get("last_result_summary", ""),
            continuity_notes=data.get("continuity_notes", []),
            status=SessionStatus(data.get("status", "active")),
            metadata=data.get("metadata", {}),
        )


class SessionStore:
    """In-memory session store. Thread-safe."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._active_by_user: dict[str, str] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        user_id: str,
        workstation_id: str = "",
        mode: str = "command_center",
    ) -> SessionState:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = _iso_now()
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            workstation_id=workstation_id,
            active_mode=mode,
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            self._sessions[session_id] = session
            self._active_by_user[user_id] = session_id
        return session

    def load_session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def update_session(self, session: SessionState, **updates: Any) -> SessionState:
        with self._lock:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = _iso_now()
        return session

    def pause_session(self, session_id: str) -> SessionState | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = SessionStatus.PAUSED
            session.updated_at = _iso_now()
            return session

    def close_session(self, session_id: str) -> SessionState | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = SessionStatus.CLOSED
            session.updated_at = _iso_now()
            if self._active_by_user.get(session.user_id) == session_id:
                del self._active_by_user[session.user_id]
            return session

    def get_active_session(self, user_id: str) -> SessionState | None:
        session_id = self._active_by_user.get(user_id)
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            return session
        return None

    def list_sessions(self, user_id: str | None = None) -> list[SessionState]:
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sessions


_session_store: SessionStore | None = None
_store_lock = threading.Lock()


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        with _store_lock:
            if _session_store is None:
                _session_store = SessionStore()
    return _session_store


def reset_session_store(store: SessionStore | None = None) -> None:
    global _session_store
    with _store_lock:
        _session_store = store


def export_storage_descriptors(
    store: SessionStore | None = None,
) -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    if store is None:
        store = get_session_store()

    descriptors: list[StorageRecordDescriptor] = []
    for s in store.list_sessions():
        descriptors.append(
            StorageRecordDescriptor(
                record_id=s.session_id,
                record_type=StorageRecordType.SESSION_STATE,
                scope=StorageScope.SESSION,
                mutability=StorageMutability.MUTABLE,
                source=StorageSource.WORKSTATION,
                backend_type=StorageBackendType.MEMORY,
                owner_id=s.user_id,
                created_at=s.started_at,
                updated_at=s.updated_at,
            )
        )

    return descriptors
