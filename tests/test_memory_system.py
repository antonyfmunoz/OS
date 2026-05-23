import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import uuid4, UUID
from substrate.types import MemoryEntry, MemoryQuery, MemoryType
from substrate.control_plane.memory import ConcreteMemorySystem


class TestMemorySystem:
    @pytest.fixture
    def memory(self):
        return ConcreteMemorySystem()

    @pytest.mark.asyncio
    async def test_store_returns_uuid(self, memory):
        entry = MemoryEntry(
            memory_type=MemoryType.OBSERVATION,
            content="test observation",
        )
        result = await memory.store(entry)
        assert result is not None
        assert isinstance(result, UUID)

    @pytest.mark.asyncio
    async def test_store_returns_entry_id(self, memory):
        """store() returns the entry's own id, not a new one."""
        entry = MemoryEntry(
            memory_type=MemoryType.FACT,
            content="idempotency check",
        )
        result = await memory.store(entry)
        assert result == entry.id

    @pytest.mark.asyncio
    async def test_recall_returns_list(self, memory):
        query = MemoryQuery(query_text="test", limit=5)
        results = await memory.recall(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_items_are_memory_entries(self, memory):
        """If recall returns anything, each item must be a MemoryEntry."""
        query = MemoryQuery(query_text="test", limit=5)
        results = await memory.recall(query)
        for item in results:
            assert isinstance(item, MemoryEntry)

    @pytest.mark.asyncio
    async def test_recall_respects_limit(self, memory):
        """recall() never returns more items than the requested limit."""
        query = MemoryQuery(query_text="anything", limit=3)
        results = await memory.recall(query)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_log_interaction_returns_uuid(self, memory):
        result = await memory.log_interaction(
            signal_id=uuid4(),
            content="user said hello",
            response="hello back",
            provider="test",
        )
        assert result is not None
        assert isinstance(result, UUID)

    @pytest.mark.asyncio
    async def test_log_interaction_each_call_returns_unique_uuid(self, memory):
        """log_interaction generates a fresh uuid on every call."""
        r1 = await memory.log_interaction(
            signal_id=uuid4(),
            content="msg a",
            response="resp a",
            provider="test",
        )
        r2 = await memory.log_interaction(
            signal_id=uuid4(),
            content="msg b",
            response="resp b",
            provider="test",
        )
        assert r1 != r2

    @pytest.mark.asyncio
    async def test_store_multiple_entries_distinct_ids(self, memory):
        """Two separate MemoryEntry objects get distinct UUIDs."""
        e1 = MemoryEntry(memory_type=MemoryType.DECISION, content="first")
        e2 = MemoryEntry(memory_type=MemoryType.BELIEF, content="second")
        r1 = await memory.store(e1)
        r2 = await memory.store(e2)
        assert r1 != r2

    @pytest.mark.asyncio
    async def test_concrete_memory_system_satisfies_protocol(self, memory):
        """ConcreteMemorySystem must satisfy the MemorySystem protocol."""
        from substrate.control_plane.memory import MemorySystem

        assert isinstance(memory, MemorySystem)
