"""Thread-safe in-memory correlation map for CreatorOS outcome writeback targeting."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreatorOSWritebackTarget:
    """Where to write back a CreatorOS outcome.

    user_id is integer — matches the CreatorOS users.id serial PK.
    """

    user_id: int
    table_name: str
    row_id: str
    integration: str = "creatoros"


class CreatorOSCorrelationMap:
    """Maps correlation_id -> writeback target. Thread-safe, in-memory only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._map: dict[UUID, CreatorOSWritebackTarget] = {}

    def register(self, correlation_id: UUID, target: CreatorOSWritebackTarget) -> None:
        with self._lock:
            self._map[correlation_id] = target

    def lookup(self, correlation_id: UUID) -> CreatorOSWritebackTarget | None:
        with self._lock:
            return self._map.get(correlation_id)

    def remove(self, correlation_id: UUID) -> None:
        with self._lock:
            self._map.pop(correlation_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)
