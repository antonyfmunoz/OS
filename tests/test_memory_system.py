"""Tests for ConcreteMemorySystem.

Phase 6 invariant verification.
Exercises the stable fallback path (no Neon DB required).
"""
from __future__ import annotations

import uuid
import pytest

from substrate.control_plane.memory import ConcreteMemorySystem
from substrate.types import MemoryEntry, MemoryQuery, MemoryType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(**kwargs) -> MemoryEntry:
    defaults = dict(
        memory_type=MemoryType.FACT,
        content="test memory content",
        authority_tier=3,
    )
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


def _make_query(**kwargs) -> MemoryQuery:
    defaults = dict(
        query_text="test query",
        limit=5,
    )
    defaults.update(kwargs)
    return MemoryQuery(**defaults)


# ---------------------------------------------------------------------------
# MemorySystem tests
# ---------------------------------------------------------------------------

class TestMemorySystem:
    @pytest.fixture
    def memory(self):
        # ConcreteMemorySystem silently falls back when DB unavailable
        return ConcreteMemorySystem()

    @pytest.mark.asyncio
    async def test_recall_returns_list(self, memory):
        query = _make_query()
        results = await memory.recall(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_stable_without_db(self, memory):
        query = _make_query(query_text="what are my active goals")
        try:
            results = await memory.recall(query)
            assert isinstance(results, list)
        except Exception as exc:
            pytest.fail(f"recall() raised unexpectedly: {exc}")

    @pytest.mark.asyncio
    async def test_store_returns_uuid(self, memory):
        entry = _make_entry()
        result_id = await memory.store(entry)
        assert isinstance(result_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_store_stable_without_db(self, memory):
        entry = _make_entry(content="some new fact")
        try:
            result = await memory.store(entry)
            assert result is not None
        except Exception as exc:
            pytest.fail(f"store() raised unexpectedly: {exc}")

    @pytest.mark.asyncio
    async def test_log_interaction_returns_uuid(self, memory):
        sig_id = uuid.uuid4()
        result = await memory.log_interaction(
            signal_id=sig_id,
            content="user message",
            response="ai response",
            provider="gemini",
        )
        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    async def test_log_interaction_stable_without_db(self, memory):
        try:
            result = await memory.log_interaction(
                signal_id=uuid.uuid4(),
                content="hello",
                response="hi there",
                provider="ollama",
            )
            assert result is not None
        except Exception as exc:
            pytest.fail(f"log_interaction() raised unexpectedly: {exc}")

    def test_memory_entry_pydantic(self):
        entry = _make_entry(content="fact about system")
        data = entry.model_dump()
        assert "content" in data
        assert "memory_type" in data

    def test_memory_query_pydantic(self):
        query = _make_query(limit=10)
        assert query.limit == 10
