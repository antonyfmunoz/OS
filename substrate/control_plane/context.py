"""ContextAssembler — builds execution context from signal + identity.

Merges conversation history (last 10 turns), semantic memory recall,
active goals, and business context into a single ExecutionContext.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from substrate.types import (
    ExecutionContext,
    Identity,
    MemoryEntry,
    MemoryQuery,
    SignalEnvelope,
)

if TYPE_CHECKING:
    from substrate.control_plane.memory import MemorySystem


@runtime_checkable
class ContextAssembler(Protocol):
    async def assemble(self, signal: SignalEnvelope, identity: Identity) -> ExecutionContext: ...


class ConcreteContextAssembler:
    """Builds ExecutionContext by querying existing memory and conversation stores."""

    def __init__(self, memory_system: MemorySystem | None = None) -> None:
        self._memory_system = memory_system

    async def assemble(self, signal: SignalEnvelope, identity: Identity) -> ExecutionContext:
        conversation_history = await self._get_conversation_history(
            signal.user_id, signal.metadata.get("channel_id", "")
        )
        relevant_memories = await self._recall_relevant(signal.content)
        business_context = self._get_business_context(identity)

        return ExecutionContext(
            signal_id=signal.id,
            identity=identity,
            session_id=signal.metadata.get("session_id"),
            conversation_history=conversation_history,
            relevant_memories=relevant_memories,
            business_context=business_context,
        )

    async def _get_conversation_history(
        self, user_id: str, channel_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        # Try memory system's conversation store first (if wired)
        if self._memory_system is not None:
            try:
                cm = getattr(self._memory_system, "_conversation_memory", None)
                if cm is not None:
                    return cm.get_session(user_id=user_id, channel_id=channel_id, limit=limit)
            except Exception:
                pass

        # Fallback: attempt direct import of ConversationMemory
        try:
            import sys

            sys.path.insert(0, "/opt/OS")
            from state.memory.memory import ConversationMemory

            cm = ConversationMemory()
            return cm.get_session(user_id=user_id, channel_id=channel_id, limit=limit)
        except Exception:
            return []

    async def _recall_relevant(self, query: str) -> list[MemoryEntry]:
        if self._memory_system is None:
            return []
        try:
            return await self._memory_system.recall(MemoryQuery(query_text=query, limit=5))
        except Exception:
            return []

    def _get_business_context(self, identity: Identity) -> dict[str, Any]:
        return {
            "business_stage": identity.business_stage,
            "ai_name": identity.ai_name,
            "organization_id": identity.organization_id,
            "venture_id": identity.venture_id,
        }
