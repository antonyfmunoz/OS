"""Thread-safe in-memory correlation map for LyfeOS outcome writeback targeting."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LyfeOSWritebackTarget:
    """Where to write back a LyfeOS outcome."""

    user_id: int
    table_name: str
    row_id: str
    integration: str = "lyfeos"


class LyfeOSCorrelationMap:
    """Maps correlation_id -> writeback target. Thread-safe, in-memory only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._map: dict[UUID, LyfeOSWritebackTarget] = {}

    def register(self, correlation_id: UUID, target: LyfeOSWritebackTarget) -> None:
        with self._lock:
            self._map[correlation_id] = target

    def lookup(self, correlation_id: UUID) -> LyfeOSWritebackTarget | None:
        with self._lock:
            return self._map.get(correlation_id)

    def remove(self, correlation_id: UUID) -> None:
        with self._lock:
            self._map.pop(correlation_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)
