"""Memory protocols — contracts for intelligence-layer memory operations.

Memory in UMH is the intelligence subsystem: semantic recall, episodic
retrieval, working memory. This is distinct from storage (raw key-value).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryStore(Protocol):
    """Contract for UMH intelligence memory operations."""

    def remember(
        self, key: str, content: Any, tags: list[str] | None = None
    ) -> None: ...

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

    def forget(self, key: str) -> bool: ...


@runtime_checkable
class EpisodicMemory(Protocol):
    """Contract for episode-based memory retrieval."""

    def record_episode(self, episode_id: str, events: list[dict[str, Any]]) -> None: ...

    def retrieve_episodes(self, query: str, limit: int = 3) -> list[dict[str, Any]]: ...
