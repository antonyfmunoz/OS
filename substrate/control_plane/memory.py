"""MemorySystem — unified protocol over existing memory stores.

Wraps AgentMemory + ConversationMemory behind a single protocol.
Does NOT rewrite the memory layer — wraps it.

Source mapping:
- state/memory/memory.py → AgentMemory.log(), semantic_search(), embed_and_store()
- state/memory/memory.py → ConversationMemory.store(), get_session()
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from substrate.types import MemoryQuery, MemoryEntry, MemoryType


@runtime_checkable
class MemorySystem(Protocol):
    async def recall(self, query: MemoryQuery) -> list[MemoryEntry]: ...
    async def store(self, entry: MemoryEntry) -> UUID: ...
    async def log_interaction(
        self, signal_id: UUID, content: str, response: str, provider: str, **kwargs: Any
    ) -> UUID: ...


class ConcreteMemorySystem:
    """Wraps existing AgentMemory + ConversationMemory."""

    def is_available(self) -> bool:
        return self._agent_memory is not None

    def __init__(self, ctx: object | None = None) -> None:
        try:
            from substrate.state.memory.memory import AgentMemory, ConversationMemory

            self._agent_memory = AgentMemory()
            if ctx and hasattr(ctx, "org_id"):
                self._conversation_memory = ConversationMemory(ctx)
            else:
                self._conversation_memory = None
        except Exception:
            self._agent_memory = None
            self._conversation_memory = None

    async def recall(self, query: MemoryQuery) -> list[MemoryEntry]:
        if not self._agent_memory:
            return []
        try:
            results = self._agent_memory.semantic_search(query.query_text, limit=query.limit)
            return [
                MemoryEntry(
                    memory_type=query.memory_types[0]
                    if query.memory_types
                    else MemoryType.OBSERVATION,
                    content=r.get("content", ""),
                    authority_tier=r.get("authority_tier", 5),
                )
                for r in results
            ]
        except Exception:
            return []

    async def store(self, entry: MemoryEntry) -> UUID:
        if self._agent_memory:
            try:
                self._agent_memory.log_event(
                    org_id=entry.metadata.get("org_id", "") if entry.metadata else "",
                    event_type=entry.memory_type.value,
                    payload={"content": entry.content, **(entry.metadata or {})},
                )
            except Exception:
                pass
        return entry.id

    async def log_interaction(
        self, signal_id: UUID, content: str, response: str, provider: str, **kwargs: Any
    ) -> UUID:
        if self._agent_memory:
            try:
                from types import SimpleNamespace

                agent_result = SimpleNamespace(
                    content=response,
                    provider=provider,
                    agent_type=kwargs.get("agent_type", "substrate"),
                    task_type=kwargs.get("task_type", "chat"),
                )
                self._agent_memory.log(
                    agent_result=agent_result,
                    venture_id=kwargs.get("venture_id"),
                    input_summary=content,
                )
            except Exception:
                pass
        from uuid import uuid4

        return uuid4()
