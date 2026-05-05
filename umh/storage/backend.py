"""StorageBackend — minimal key-value persistence contract.

Any object with get/put/all_keys methods satisfies the StorageBackend
protocol. InMemoryStorage provides a zero-dependency default.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Minimal key-value storage contract for UMH modules."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def put(self, key: str, value: Any) -> None: ...

    def all_keys(self) -> list[str]: ...


class InMemoryStorage:
    """In-memory storage for testing and bootstrapping."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all_keys(self) -> list[str]:
        return list(self._data.keys())
