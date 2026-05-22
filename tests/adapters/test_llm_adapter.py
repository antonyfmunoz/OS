"""Tests for the LLM adapter wrapping model_router."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/substrate-unification")

import asyncio
from uuid import UUID

from adapters.models.llm_adapter import LLMAdapter
from adapters.protocol import Adapter
from substrate.types import AdapterRequest, AdapterResponse


class TestLLMAdapter:
    def test_satisfies_adapter_protocol(self):
        adapter = LLMAdapter()
        assert isinstance(adapter, Adapter)

    def test_has_required_attributes(self):
        adapter = LLMAdapter()
        assert isinstance(adapter.adapter_id, UUID)
        assert adapter.adapter_type == "llm"
        assert adapter.name == "model_router"

    def test_capabilities(self):
        adapter = LLMAdapter()
        caps = adapter.capabilities()
        assert "text_generation" in caps
        assert "conversation" in caps
        assert "analysis" in caps
        assert "summarization" in caps

    def test_health_check(self):
        adapter = LLMAdapter()
        result = asyncio.run(adapter.health_check())
        assert result is True

    def test_execute_empty_prompt_returns_response(self):
        """Execute with empty prompt — model_router may fail, adapter must not crash."""
        adapter = LLMAdapter()
        request = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": ""},
        )
        result = asyncio.run(adapter.execute(request))
        assert isinstance(result, AdapterResponse)
        assert result.adapter_id == adapter.adapter_id
        # Either success or graceful failure, never an exception
        assert isinstance(result.success, bool)

    def test_execute_returns_adapter_response_type(self):
        """Verify execute always returns an AdapterResponse."""
        adapter = LLMAdapter()
        request = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": "say hello"},
        )
        result = asyncio.run(adapter.execute(request))
        assert isinstance(result, AdapterResponse)
        assert result.latency_ms >= 0
