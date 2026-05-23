"""UMH Substrate — the unified intelligence substrate.

Single public API. All signals enter through Substrate.execute().
All queries through Substrate.query(). All registrations through
Substrate.register().
"""

from __future__ import annotations

import asyncio
import logging
import time

from substrate.types import (
    Component,
    ComponentType,
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

logger = logging.getLogger(__name__)


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
        self._register_boot_adapters()

    def _register_boot_adapters(self) -> None:
        """Register built-in adapters at boot time.

        Runs synchronously during __init__. Uses run_until_complete when no
        event loop is running; schedules as a task when one is already active.
        """
        try:
            loop = asyncio.get_running_loop()
            # Already inside a running loop — schedule as a background task.
            loop.create_task(self._do_register_boot_adapters())
        except RuntimeError:
            # No running event loop — safe to run synchronously.
            asyncio.run(self._do_register_boot_adapters())

    async def _do_register_boot_adapters(self) -> None:
        """Async implementation: build and register the LLM adapter component."""
        try:
            from adapters.models.llm_adapter import LLMAdapter

            adapter = LLMAdapter()
            component = Component(
                component_type=ComponentType.ADAPTER,
                name=adapter.name,
                capabilities=adapter.capabilities(),
                metadata={
                    "adapter_id": str(adapter.adapter_id),
                    "adapter_type": adapter.adapter_type,
                },
            )
            await self.registry.register(component)
            logger.debug("Boot adapter registered: %s", adapter.name)
        except Exception as exc:
            # Non-fatal — substrate can still operate without LLM at boot.
            logger.warning("Failed to register boot adapter: %s", exc)

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
            "memory": "ok" if self.memory.is_available() else "degraded",
            "registry": "ok",
            "trace": "ok",
            "feedback": "ok",
            "spine": "ok",
        }
        healthy = all(v in ("ok", "degraded") for v in subsystems.values())
        return SubstrateStatus(
            healthy=healthy,
            subsystems=subsystems,
            adapter_count=self.registry.count(),
            trace_count=self.trace.count(),
            uptime_seconds=time.monotonic() - self._started_at,
        )
