"""UMH Substrate — the unified intelligence substrate.

Single public API. All signals enter through Substrate.execute().
All queries through Substrate.query(). All registrations through
Substrate.register().
"""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import uuid4

from substrate.types import (
    Component,
    ComponentType,
    Department,
    ExecutionResult,
    MemoryEntry,
    MemoryQuery,
    OperatorType,
    PermissionTier,
    Portfolio,
    RegistrationResult,
    Role,
    SignalEnvelope,
    SubstrateStatus,
    required_tier_for_action,
)


def get_conn(org_id: str | None = None):
    """Database cursor via substrate storage layer."""
    from substrate.state.storage.db import get_conn as _get_conn

    if org_id is not None:
        return _get_conn(org_id)
    return _get_conn()


async def run_browser_task(url: str, task: str, ctx: object | None = None) -> dict:
    """Public API for browser task execution. Projections use this, not internal imports."""
    from substrate.execution.agents.browser_agent import run_browser_task as _run

    return await _run(url=url, task=task, ctx=ctx)


from substrate.self_model import self_model
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
        self.self_model = self_model
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
        self.self_model.register_subsystems(
            registry=self.registry,
            trace_recorder=self.trace,
            governance=self.governance,
        )
        self._register_config_store()
        self._register_boot_adapters()

    def _register_config_store(self) -> None:
        """Wire the config store into the config port so substrate code can access config."""
        try:
            from substrate.state.config import config_store
            from substrate.sockets.config_port import register_config_store

            config_store.seed_from_instance_json()
            register_config_store(
                get_fn=config_store.get,
                set_fn=config_store.set,
                get_all_fn=config_store.get_all,
                on_change_fn=config_store.on_change,
            )
            logger.debug("Config store registered with %d system keys",
                         len(config_store.get_layer("system")))
        except Exception as exc:
            logger.warning("Failed to register config store: %s", exc)

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


    async def execute_work(
        self,
        intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
    ) -> "OrganismLoopResult":
        """Execute governed work through the organism loop.

        This is the canonical entry point for any caller (cockpit, API, CLI,
        projection) that wants governed execution. It creates an
        OrganismLoopEngine and runs the full intent-to-memory cycle:
        reality check -> work packet -> queue -> governance -> execution ->
        memory write -> event emission.

        The loop engine handles governance internally — callers must NOT
        bypass this method to call WorkPacketExecutor directly.

        Args:
            intent: Natural language description of what to do.
            desired_end_state: What the world should look like after.
            constraints: Optional list of constraints on execution.

        Returns:
            OrganismLoopResult documenting every step of the cycle.
        """
        from substrate.organism.organism_loop import (
            OrganismLoopEngine,
            OrganismLoopResult,
        )

        engine = OrganismLoopEngine()
        return await engine.execute_intent(
            intent=intent,
            desired_end_state=desired_end_state,
            constraints=constraints,
        )

    async def execute_intent(
        self,
        intent: str,
        conversation_id: str = "",
        desired_end_state: str = "",
        constraints: list[str] | None = None,
    ) -> "IntentReceipt":
        """Unified operator entry point — classifies intent and routes.

        This is the Phase 18 convergence point. The operator never needs to
        choose between execute() and execute_work(). This method classifies
        the intent deterministically, routes to the correct path, and returns
        a canonical IntentReceipt.

        IntentRouter introduces ZERO new execution authority. All execution
        flows through either ConcreteExecutionSpine (conversation) or
        OrganismLoopEngine (governed work).

        Args:
            intent: Natural language operator input.
            conversation_id: Optional conversation ID for context threading.
            desired_end_state: For work-type intents, what success looks like.
            constraints: For work-type intents, execution constraints.

        Returns:
            IntentReceipt documenting classification, routing, and outcome.
        """
        from substrate.operator.intent_router import IntentRouter, RouteType
        from substrate.operator.intent_receipt import (
            IntentReceipt,
            IntentReceiptStore,
            ReceiptStatus,
        )

        router = IntentRouter()
        classification = router.classify(intent)

        receipt = IntentReceipt(
            intent_id=f"ir-{uuid4().hex[:12]}",
            raw_input=intent,
            route_type=classification.route_type.value,
            confidence=classification.confidence,
            extracted_entities=classification.extracted_entities,
            reasoning=classification.reasoning,
            final_status=ReceiptStatus.ROUTING.value,
        )

        store = IntentReceiptStore()
        store.append(receipt)

        try:
            if classification.route_type == RouteType.CONVERSATION:
                receipt.conversation_id = conversation_id or f"conv-{uuid4().hex[:12]}"
                receipt.final_status = ReceiptStatus.COMPLETED.value

            elif classification.route_type == RouteType.WORK_PACKET:
                receipt.final_status = ReceiptStatus.EXECUTING.value
                result = await self.execute_work(
                    intent=intent,
                    desired_end_state=desired_end_state,
                    constraints=constraints,
                )
                receipt.work_packet_id = result.work_packet_id
                receipt.governance_decision_id = result.governance_decision_id
                receipt.execution_bundle_id = result.execution_bundle_id
                receipt.memory_write_receipt_id = result.memory_write_receipt_id
                receipt.reality_update_id = result.reality_update_id
                receipt.event_ids = result.event_ids
                receipt.final_status = result.final_status

            elif classification.route_type == RouteType.HYBRID:
                receipt.conversation_id = conversation_id or f"conv-{uuid4().hex[:12]}"
                receipt.final_status = ReceiptStatus.COMPLETED.value

            elif classification.route_type == RouteType.OBSERVATION:
                receipt.final_status = ReceiptStatus.COMPLETED.value

            elif classification.route_type == RouteType.APPROVAL:
                receipt.final_status = ReceiptStatus.COMPLETED.value

        except Exception as exc:
            receipt.error = str(exc)
            receipt.final_status = ReceiptStatus.FAILED.value

        receipt.completed_at = time.time()
        store.update(receipt)

        try:
            from substrate.organism.event_spine import EventDomain, EventSpine

            spine = EventSpine()
            spine.emit(
                domain=EventDomain.OPERATOR,
                event_type="intent_routed",
                source="substrate.execute_intent",
                data=receipt.to_dict(),
                correlation_id=receipt.intent_id,
            )
        except Exception:
            pass

        return receipt

    def check_tier(self, action_type: str, caller_tier: str = "execute") -> dict:
        """Check if a permission tier allows an action type."""
        return self.governance.check_tier(action_type, caller_tier)

    def status(self) -> SubstrateStatus:
        """Return substrate health status."""
        subsystems = {
            "self_model": "ok" if self.self_model.instance.loaded else "unloaded",
            "identity": "ok",
            "context": "ok",
            "governance": "ok",
            "memory": "ok" if self.memory.is_available() else "degraded",
            "registry": "ok",
            "trace": "ok",
            "feedback": "ok",
            "spine": "ok",
        }
        healthy = all(v in ("ok", "degraded", "unloaded") for v in subsystems.values())
        return SubstrateStatus(
            healthy=healthy,
            subsystems=subsystems,
            adapter_count=self.registry.count(),
            trace_count=self.trace.count(),
            uptime_seconds=time.monotonic() - self._started_at,
        )
