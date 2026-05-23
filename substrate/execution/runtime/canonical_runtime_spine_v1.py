"""Canonical Runtime Spine v1.

The single approved execution flow for all governed runtime operations.

14-step pipeline:
  1. Signal reception
  2. Interpretation (signal → intent)
  3. Capability resolution (intent → required capabilities)
  4. Adapter selection (capabilities → adapter)
  5. Environment selection (adapter → environment)
  6. Governance evaluation (intent + risk → verdict)
  7. Execution queueing (envelope → queue)
  8. Execution orchestration (queue → execute → result)
  9. Result capture (execution result → spine result)
  10. Observability persistence (result → telemetry)
  11. Continuity update (result → continuity engine)
  12. Memory governance bridge (result → memory promotion)
  13. Open loop management (result → loop registry)
  14. Runtime summary

No parallel execution spines. No hidden execution paths.
No direct adapter execution. No governance bypass.

UMH substrate subsystem. Phase 96.8BO.
"""

from __future__ import annotations

import time
from typing import Any

from .execution_contracts_v1 import (
    AdapterSelection,
    CapabilityResolution,
    EnvironmentSelection,
    ExecutionEnvelope,
    ExecutionMode,
    ExecutionSignal,
    GovernanceEvaluation,
    GovernanceVerdict,
    IntentType,
    InterpretedIntent,
    ObservabilityRecord,
    RiskClass,
    SignalSource,
    SpineExecutionResult,
    SpineOutcome,
    _new_id,
    _now_iso,
)
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import AdapterLifecycleManager
from .capability_router_v1 import CapabilityRouter
from .environment_registry_v1 import EnvironmentRegistry
from .execution_orchestrator_v1 import ExecutionOrchestrator
from .governance_execution_bridge_v1 import GovernanceExecutionBridge
from .runtime_execution_queue_v1 import RuntimeExecutionQueue
from .runtime_observability_pipeline_v1 import RuntimeObservabilityPipeline
from .substrate_continuity_engine_v1 import SubstrateContinuityEngine
from .runtime_memory_governance_bridge_v1 import RuntimeMemoryGovernanceBridge


class CanonicalRuntimeSpine:
    """The single approved execution flow for all governed operations.

    Composes:
      - CapabilityRouter (command → capability → environment)
      - AdapterLifecycleManager (adapter health + selection)
      - EnvironmentRegistry (environment capabilities + health)
      - GovernanceExecutionBridge (pre-execution governance gate)
      - RuntimeExecutionQueue (ordered execution queue)
      - ExecutionOrchestrator (execute within approved envelope)
      - RuntimeObservabilityPipeline (telemetry capture)
      - SubstrateContinuityEngine (continuity state updates)
      - RuntimeMemoryGovernanceBridge (memory promotion decisions)
    """

    VERSION = "v1"

    def __init__(
        self,
        capability_router: CapabilityRouter,
        adapter_manager: AdapterLifecycleManager,
        environment_registry: EnvironmentRegistry,
        governance_bridge: GovernanceExecutionBridge,
        execution_queue: RuntimeExecutionQueue,
        orchestrator: ExecutionOrchestrator,
        observability: RuntimeObservabilityPipeline,
        continuity_engine: SubstrateContinuityEngine | None = None,
        memory_bridge: RuntimeMemoryGovernanceBridge | None = None,
    ) -> None:
        self._router = capability_router
        self._adapter_manager = adapter_manager
        self._env_registry = environment_registry
        self._governance = governance_bridge
        self._queue = execution_queue
        self._orchestrator = orchestrator
        self._observability = observability
        self._continuity = continuity_engine
        self._memory_bridge = memory_bridge
        self._session_id = ""
        self._executions_count = 0

    def start_session(self, session_id: str) -> None:
        self._session_id = session_id
        if self._continuity:
            self._continuity.start_session(session_id)

    # ------------------------------------------------------------------
    # The 14-step pipeline
    # ------------------------------------------------------------------

    def execute(
        self,
        raw_command: str,
        source: SignalSource = SignalSource.DISCORD,
        payload: dict[str, Any] | None = None,
        user_id: str = "",
        channel_id: str = "",
    ) -> SpineExecutionResult:
        """Execute a command through the full 14-step governed pipeline."""
        start_time = time.monotonic()

        # Step 1: Signal reception
        signal = ExecutionSignal(
            source=source,
            raw_command=raw_command,
            payload=payload or {},
            user_id=user_id,
            channel_id=channel_id,
        )

        # Step 2: Interpretation
        intent = self._interpret_signal(signal)

        # Step 3: Capability resolution
        route = self._router.resolve(intent.command_name)
        if route.is_forbidden:
            return self._make_failure(
                signal,
                intent,
                SpineOutcome.STRUCTURALLY_FORBIDDEN,
                f"Command {intent.command_name} is structurally forbidden",
                start_time,
            )
        if route.capability is None:
            return self._make_failure(
                signal,
                intent,
                SpineOutcome.CAPABILITY_UNAVAILABLE,
                f"No capability mapping for command {intent.command_name}",
                start_time,
            )
        cap_resolution = self._router.resolve_intent(intent)
        if not cap_resolution.resolved:
            return self._make_failure(
                signal,
                intent,
                SpineOutcome.CAPABILITY_UNAVAILABLE,
                f"Missing capabilities: {cap_resolution.missing_capabilities}",
                start_time,
            )

        # Step 4: Adapter selection
        adapter_selection = self._adapter_manager.select_adapter(
            intent.command_name, intent.intent_id
        )

        # Step 5: Environment selection
        env_selection = self._select_environment(intent)

        # Step 6: Governance evaluation
        gov_evaluation = self._governance.evaluate(intent)
        if not gov_evaluation.approved:
            return self._make_governance_denied(
                signal,
                intent,
                cap_resolution,
                adapter_selection,
                env_selection,
                gov_evaluation,
                start_time,
            )

        # Step 7: Build execution envelope and queue
        envelope = ExecutionEnvelope(
            signal=signal,
            intent=intent,
            capability_resolution=cap_resolution,
            adapter_selection=adapter_selection,
            environment_selection=env_selection,
            governance_evaluation=gov_evaluation,
            execution_mode=ExecutionMode.SYNCHRONOUS,
            session_id=self._session_id,
        )

        queue_entry = self._queue.enqueue(envelope)

        # Step 8: Execute
        if queue_entry:
            self._queue.dequeue()

        result = self._orchestrator.execute(envelope)
        self._executions_count += 1

        # Step 9: Update queue status
        if queue_entry:
            if result.succeeded:
                self._queue.complete(queue_entry.entry_id)
            else:
                self._queue.fail(queue_entry.entry_id, result.error_message)

        # Step 10: Observability (already captured by orchestrator)

        # Step 11: Continuity update
        if self._continuity:
            self._update_continuity(signal, intent, result)

        # Step 12: Memory governance bridge
        if self._memory_bridge and result.succeeded:
            promotion = self._memory_bridge.evaluate_outcome(
                {
                    "outcome_id": result.result_id,
                    "trace_id": result.correlation_id,
                    "command": result.command_name,
                    "result": "success" if result.succeeded else "failure",
                    "duration_ms": result.duration_ms,
                    "artifacts_produced": result.artifacts_produced,
                }
            )
            if promotion.should_promote:
                result.memory_promotions.append(promotion.rule.value)

        # Step 13: Open loop management (handled by continuity engine)

        # Step 14: Duration capture
        result.duration_ms = (time.monotonic() - start_time) * 1000

        return result

    # ------------------------------------------------------------------
    # Pipeline step implementations
    # ------------------------------------------------------------------

    def _interpret_signal(self, signal: ExecutionSignal) -> InterpretedIntent:
        """Step 2: Interpret signal into intent."""
        command = signal.raw_command.lstrip("!").strip()
        parts = command.split(maxsplit=1)
        command_name = parts[0] if parts else command
        args_str = parts[1] if len(parts) > 1 else ""

        route = self._router.resolve(command_name)

        intent_type = IntentType.COMMAND
        if route.capability and route.capability.value == "report_generation":
            intent_type = IntentType.REPORT
        elif route.capability and route.capability.value == "memory_query":
            intent_type = IntentType.QUERY
        elif route.capability and route.capability.value == "document_ingestion":
            intent_type = IntentType.INGESTION

        required_caps = [route.capability.value] if route.capability else []

        return InterpretedIntent(
            signal_id=signal.signal_id,
            intent_type=intent_type,
            command_name=command_name,
            arguments={"raw_args": args_str} if args_str else {},
            required_capabilities=required_caps,
            risk_class=route.risk_class,
        )

    def _select_environment(self, intent: InterpretedIntent) -> EnvironmentSelection:
        """Step 5: Select execution environment."""
        route = self._router.resolve(intent.command_name)
        if route.selected_environment:
            env = route.selected_environment
            return EnvironmentSelection(
                intent_id=intent.intent_id,
                environment_id=env.environment_id,
                environment_type=env.environment_type,
                authority_domains=env.authority_domains,
                health_status=env.status.value,
                selected=True,
            )
        return EnvironmentSelection(
            intent_id=intent.intent_id,
            selected=False,
            rejection_reason="No suitable environment found",
        )

    def _update_continuity(
        self,
        signal: ExecutionSignal,
        intent: InterpretedIntent,
        result: SpineExecutionResult,
    ) -> None:
        """Step 11: Update continuity engine with execution outcome."""
        if not self._continuity:
            return

        event_type = "execution_completed" if result.succeeded else "execution_failed"
        self._continuity.ingest_event(
            {
                "event_id": result.result_id,
                "event_type": event_type,
                "source": "canonical_spine",
                "severity": "info" if result.succeeded else "error",
                "payload": {
                    "command": result.command_name,
                    "summary": f"Spine execution: {result.command_name} → {result.outcome.value}",
                },
                "correlation_id": result.correlation_id,
            }
        )

        self._continuity.record_outcome(
            {
                "outcome_id": f"spine-{result.result_id}",
                "trace_id": result.correlation_id,
                "command": result.command_name,
                "result": "success" if result.succeeded else "failure",
                "duration_ms": result.duration_ms,
                "error_message": result.error_message,
                "artifacts_produced": result.artifacts_produced,
            }
        )

    def _make_failure(
        self,
        signal: ExecutionSignal,
        intent: InterpretedIntent,
        outcome: SpineOutcome,
        error: str,
        start_time: float,
    ) -> SpineExecutionResult:
        duration_ms = (time.monotonic() - start_time) * 1000
        return SpineExecutionResult(
            envelope_id="",
            correlation_id=signal.correlation_id,
            command_name=intent.command_name,
            outcome=outcome,
            error_message=error,
            duration_ms=duration_ms,
        )

    def _make_governance_denied(
        self,
        signal: ExecutionSignal,
        intent: InterpretedIntent,
        cap_resolution: CapabilityResolution,
        adapter_selection: AdapterSelection,
        env_selection: EnvironmentSelection,
        gov_evaluation: GovernanceEvaluation,
        start_time: float,
    ) -> SpineExecutionResult:
        duration_ms = (time.monotonic() - start_time) * 1000
        envelope = ExecutionEnvelope(
            signal=signal,
            intent=intent,
            capability_resolution=cap_resolution,
            adapter_selection=adapter_selection,
            environment_selection=env_selection,
            governance_evaluation=gov_evaluation,
            session_id=self._session_id,
        )
        return SpineExecutionResult(
            envelope_id=envelope.envelope_id,
            correlation_id=signal.correlation_id,
            command_name=intent.command_name,
            outcome=SpineOutcome.GOVERNANCE_DENIED,
            execution_envelope=envelope,
            error_message=f"Governance: {gov_evaluation.verdict.value} — {', '.join(gov_evaluation.denial_reasons)}",
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "executions_count": self._executions_count,
            "router": self._router.get_stats(),
            "adapters": self._adapter_manager.get_stats(),
            "environments": self._env_registry.get_stats(),
            "governance": self._governance.get_stats(),
            "queue": self._queue.get_stats(),
            "observability": self._observability.get_stats(),
        }

    def get_safe_commands(self) -> list[str]:
        return self._router.get_safe_commands()

    def get_all_commands(self) -> list[str]:
        return self._router.get_all_commands()
