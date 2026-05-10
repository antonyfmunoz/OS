"""UMH MemoryStore — intelligence-layer memory operations.

This is the semantic/episodic memory subsystem, distinct from
umh.storage (raw key-value persistence). MemoryStore handles
remember/recall/forget with optional tagging and relevance ranking.
"""

from __future__ import annotations

from typing import Any

from umh.core.clock import iso_now


class InMemoryStore:
    """In-memory implementation of the MemoryStore protocol.

    Stores memories as tagged entries with timestamps.
    Recall does substring matching on content and tags.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def remember(self, key: str, content: Any, tags: list[str] | None = None) -> None:
        self._entries[key] = {
            "key": key,
            "content": content,
            "tags": tags or [],
            "created_at": iso_now(),
        }

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_lower = query.lower()
        matches = []
        for entry in self._entries.values():
            content_str = str(entry["content"]).lower()
            tag_str = " ".join(entry["tags"]).lower()
            if query_lower in content_str or query_lower in tag_str:
                matches.append(entry)
        return matches[:limit]

    def forget(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    def keys(self) -> list[str]:
        return list(self._entries.keys())


_STORE: InMemoryStore | None = None


def get_memory_store() -> InMemoryStore:
    """Get the singleton memory store."""
    global _STORE
    if _STORE is None:
        _STORE = InMemoryStore()
    return _STORE


def set_memory_store(store: InMemoryStore) -> None:
    """Override the memory store (for testing or custom backends)."""
    global _STORE
    _STORE = store


def reset_memory_store() -> None:
    """Clear the memory store singleton (for testing)."""
    global _STORE
    _STORE = None
