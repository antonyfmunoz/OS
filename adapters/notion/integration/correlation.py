"""Thread-safe in-memory correlation map for outcome writeback targeting."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class WritebackTarget:
    """Where to write back an outcome."""

    page_id: str
    integration: str = "notion"


class CorrelationMap:
    """Maps correlation_id → writeback target. Thread-safe, in-memory only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._map: dict[UUID, WritebackTarget] = {}

    def register(self, correlation_id: UUID, target: WritebackTarget) -> None:
        with self._lock:
            self._map[correlation_id] = target

    def lookup(self, correlation_id: UUID) -> WritebackTarget | None:
        with self._lock:
            return self._map.get(correlation_id)

    def remove(self, correlation_id: UUID) -> None:
        with self._lock:
            self._map.pop(correlation_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)
