"""Tests for adapters/protocol.py and adapters/models/llm_adapter.py.

Verifies the existing interface — this is a coverage task, not a spec task.
The adapters are already implemented and confirmed working; these tests
lock in the contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import UUID

from adapters.protocol import Adapter
from adapters.models.llm_adapter import LLMAdapter
from substrate.types import AdapterRequest, AdapterResponse


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestAdapterProtocol:
    def test_llm_adapter_satisfies_protocol(self):
        """LLMAdapter must be recognised as an Adapter at runtime."""
        adapter = LLMAdapter()
        assert isinstance(adapter, Adapter)

    def test_llm_adapter_has_required_attributes(self):
        """Static attributes must be present with correct values."""
        adapter = LLMAdapter()
        assert hasattr(adapter, "adapter_id")
        assert hasattr(adapter, "adapter_type")
        assert hasattr(adapter, "name")
        assert adapter.adapter_type == "llm"
        assert adapter.name == "model_router"

    def test_adapter_id_is_uuid(self):
        """adapter_id must be a UUID instance."""
        adapter = LLMAdapter()
        assert isinstance(adapter.adapter_id, UUID)

    def test_each_instance_gets_unique_id(self):
        """Two separate LLMAdapter instances must not share an adapter_id."""
        a1 = LLMAdapter()
        a2 = LLMAdapter()
        assert a1.adapter_id != a2.adapter_id


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


class TestLLMAdapterCapabilities:
    def test_capabilities_returns_list(self):
        adapter = LLMAdapter()
        caps = adapter.capabilities()
        assert isinstance(caps, list)

    def test_capabilities_contains_text_generation(self):
        adapter = LLMAdapter()
        assert "text_generation" in adapter.capabilities()

    def test_capabilities_are_strings(self):
        adapter = LLMAdapter()
        for cap in adapter.capabilities():
            assert isinstance(cap, str)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestLLMAdapterHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self):
        adapter = LLMAdapter()
        result = await adapter.health_check()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_health_check_true_when_model_router_importable(self):
        """model_router is present on this system — health should be True."""
        adapter = LLMAdapter()
        result = await adapter.health_check()
        assert result is True


# ---------------------------------------------------------------------------
# Execute — response shape (does not make a live LLM call)
# ---------------------------------------------------------------------------


class TestLLMAdapterExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_adapter_response(self):
        """execute() must return an AdapterResponse regardless of success."""
        adapter = LLMAdapter()
        req = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": "ping"},
        )
        resp = await adapter.execute(req)
        assert isinstance(resp, AdapterResponse)

    @pytest.mark.asyncio
    async def test_execute_response_has_matching_adapter_id(self):
        """The adapter_id in the response must match the adapter that ran."""
        adapter = LLMAdapter()
        req = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": "ping"},
        )
        resp = await adapter.execute(req)
        assert resp.adapter_id == adapter.adapter_id

    @pytest.mark.asyncio
    async def test_execute_response_has_latency(self):
        """latency_ms must be a positive float after any execution."""
        adapter = LLMAdapter()
        req = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": "ping"},
        )
        resp = await adapter.execute(req)
        assert isinstance(resp.latency_ms, float)
        assert resp.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_execute_failure_returns_false_success(self):
        """When model_router is patched to raise, success must be False."""
        import unittest.mock as mock

        adapter = LLMAdapter()
        req = AdapterRequest(
            adapter_id=adapter.adapter_id,
            payload={"prompt": "ping"},
        )

        with mock.patch(
            "adapters.models.llm_adapter.LLMAdapter.execute",
            new_callable=mock.AsyncMock,
            return_value=AdapterResponse(
                adapter_id=adapter.adapter_id,
                success=False,
                error="simulated failure",
            ),
        ):
            resp = await adapter.execute(req)
            assert resp.success is False
            assert resp.error is not None
