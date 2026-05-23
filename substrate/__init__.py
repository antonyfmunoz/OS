"""UMH Substrate — the unified intelligence substrate.

Single public API. All signals enter through Substrate.execute().
All queries through Substrate.query(). All registrations through
Substrate.register().
"""

from __future__ import annotations

import time

from substrate.types import (
    Component,
    ExecutionResult,
    MemoryEntry,
    MemoryQuery,
    RegistrationResult,
    SignalEnvelope,
    SubstrateStatus,
)

from substrate.control_plane.identity import ConcreteIdentityResolver
from substrate.control_plane.context import ConcreteContextAssembler
from substrate.control_plane.governance import ConcreteGovernanceEngine
from substrate.control_plane.memory import ConcreteMemorySystem
from substrate.control_plane.registry import ConcreteComponentRegistry
from substrate.control_plane.router import ConcreteSignalRouter
from substrate.execution.trace import ConcreteTraceRecorder
from substrate.execution.feedback import ConcreteFeedbackCapture
from substrate.execution.spine import ConcreteExecutionSpine


class Substrate:
    """The unified UMH substrate — single entry point for all operations."""

    def __init__(self) -> None:
        self._started_at = time.monotonic()
        self.identity = ConcreteIdentityResolver()
        self.governance = ConcreteGovernanceEngine()
        self.memory = ConcreteMemorySystem()
        self.context = ConcreteContextAssembler(memory_system=self.memory)
        self.registry = ConcreteComponentRegistry()
        self.trace = ConcreteTraceRecorder()
        self.feedback = ConcreteFeedbackCapture()
        self.spine = ConcreteExecutionSpine(
            memory=self.memory,
            registry=self.registry,
            trace_recorder=self.trace,
            feedback_capture=self.feedback,
        )
        self.router = ConcreteSignalRouter(
            identity_resolver=self.identity,
            context_assembler=self.context,
            governance_engine=self.governance,
            memory_system=self.memory,
            registry=self.registry,
            execution_spine=self.spine,
            trace_recorder=self.trace,
            feedback_capture=self.feedback,
        )

    async def execute(self, signal: SignalEnvelope) -> ExecutionResult:
        """Route a signal through the full substrate lifecycle."""
        return await self.router.route(signal)

    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Query the memory system."""
        return await self.memory.recall(query)

    async def register(self, component: Component) -> RegistrationResult:
        """Register a component in the registry."""
        return await self.registry.register(component)

    def status(self) -> SubstrateStatus:
        """Return substrate health status."""
        subsystems = {
            "identity": "ok",
            "context": "ok",
            "governance": "ok",
            "memory": "ok" if self.memory._agent_memory is not None else "degraded",
            "registry": "ok",
            "trace": "ok",
            "feedback": "ok",
            "spine": "ok",
        }
        healthy = all(v == "ok" for v in subsystems.values())
        return SubstrateStatus(
            healthy=healthy,
            subsystems=subsystems,
            adapter_count=len(self.registry._components),
            trace_count=len(self.trace._traces),
            uptime_seconds=time.monotonic() - self._started_at,
        )
