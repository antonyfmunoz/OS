"""Integration test: signal → trace lifecycle."""

import sys

sys.path.insert(0, "/opt/OS")

import asyncio
from uuid import UUID

from substrate import Substrate
from substrate.types import SignalEnvelope, SignalSource, ExecutionOutcome


class TestSignalToTrace:
    def test_execute_produces_trace(self):
        s = Substrate()
        signal = SignalEnvelope(
            source=SignalSource.SYSTEM,
            content="test signal for trace",
            user_id="test-user",
            organization_id="test-org",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None
        assert isinstance(result.trace_id, UUID)
        assert result.outcome in list(ExecutionOutcome)

    def test_execute_blocked_still_traced(self):
        s = Substrate()
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all contacts",
            user_id="test-user",
            organization_id="test-org",
        )
        result = asyncio.run(s.execute(signal))
        assert result.trace_id is not None
        assert result.outcome == ExecutionOutcome.BLOCKED

    def test_status_returns_subsystems(self):
        s = Substrate()
        status = s.status()
        assert "identity" in status.subsystems
        assert "governance" in status.subsystems
        assert "spine" in status.subsystems
        assert status.uptime_seconds >= 0.0

    def test_register_component(self):
        from substrate.types import Component, ComponentType

        s = Substrate()
        comp = Component(
            component_type=ComponentType.ADAPTER,
            name="test-adapter",
            capabilities=["llm"],
        )
        result = asyncio.run(s.register(comp))
        assert result.success is True
        assert result.component_id == comp.id

    def test_query_returns_list(self):
        from substrate.types import MemoryQuery

        s = Substrate()
        query = MemoryQuery(query_text="test query", limit=5)
        results = asyncio.run(s.query(query))
        assert isinstance(results, list)
