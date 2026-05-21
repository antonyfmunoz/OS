"""Session system — temporal lifecycle boundaries for the organism runtime.

Sessions represent bounded periods of operation (DAY/NIGHT cycles).
Only ONE session may be active at a time. Sessions track which cells
are alive within them and persist across individual tasks.

No imports from umh/cells, umh/adapters, or umh/execution.
Session does not execute — it provides structure.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now


@unique
class SessionType(str, Enum):
    DAY = "day"
    NIGHT = "night"


@unique
class SessionState(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class Session:
    session_id: str
    session_type: SessionType
    state: SessionState = SessionState.ACTIVE
    start_time: str = ""
    end_time: str = ""
    active_cells: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.start_time:
            self.start_time = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type.value,
            "state": self.state.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "active_cells": list(self.active_cells),
            "metadata": self.metadata,
        }


class SessionManager:
    """Manages session lifecycle. Enforces single-active-session invariant."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: Session | None = None
        self._history: list[Session] = []

    def start_session(self, session_type: SessionType, **metadata: Any) -> Session:
        with self._lock:
            if self._active is not None:
                raise RuntimeError(
                    f"Cannot start session: '{self._active.session_id}' is still active"
                )
            session = Session(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                session_type=session_type,
                metadata=metadata,
            )
            self._active = session
        return session

    def end_session(self) -> Session | None:
        with self._lock:
            if self._active is None:
                return None
            self._active.state = SessionState.COMPLETED
            self._active.end_time = _iso_now()
            ended = self._active
            self._history.append(ended)
            self._active = None
        return ended

    def abort_session(self) -> Session | None:
        with self._lock:
            if self._active is None:
                return None
            self._active.state = SessionState.ABORTED
            self._active.end_time = _iso_now()
            aborted = self._active
            self._history.append(aborted)
            self._active = None
        return aborted

    def get_active_session(self) -> Session | None:
        with self._lock:
            return self._active

    def attach_cell(self, cell_id: str) -> bool:
        with self._lock:
            if self._active is None:
                return False
            if cell_id not in self._active.active_cells:
                self._active.active_cells.append(cell_id)
            return True

    def detach_cell(self, cell_id: str) -> bool:
        with self._lock:
            if self._active is None:
                return False
            if cell_id in self._active.active_cells:
                self._active.active_cells.remove(cell_id)
                return True
            return False

    def list_history(self) -> list[Session]:
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        with self._lock:
            self._active = None
            self._history.clear()
