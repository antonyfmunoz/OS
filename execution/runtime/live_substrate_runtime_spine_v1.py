"""Live Substrate Runtime Spine v1.

The single canonical orchestration entrypoint for the entire
live substrate runtime. All signals, cognition, memory,
governance, routing, embodiment, observability, continuity,
and execution operate through this spine.

Pipeline:
  1. Signal reception
  2. Cognition (interpret, retrieve context, plan)
  3. Routing (capability, environment, embodiment, governance)
  4. Governance (verdict evaluation)
  5. Planning (execution plan creation)
  6. Execution (governed adapter dispatch)
  7. Observation (trace, governance, execution, continuity lineage)
  8. Continuity (persist, open loops, resume)
  9. Lifecycle (session tracking, state transitions)

No parallel execution spines. No hidden execution paths.
No direct adapter execution. No governance bypass.
No implicit state mutation.

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

import time
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeContinuation,
    RuntimeDecision,
    RuntimeDecisionType,
    RuntimeLineageReceipt,
    RuntimeOutcome,
    RuntimeOutcomeStatus,
    RuntimePhase,
    RuntimeSignal,
    RuntimeSignalSource,
    _content_hash,
    _new_id,
    _now_iso,
)
from .live_cognition_coordinator_v1 import LiveCognitionCoordinator
from .live_runtime_router_v1 import LiveRuntimeRouter
from .live_execution_coordinator_v1 import LiveExecutionCoordinator
from .live_continuity_coordinator_v1 import LiveContinuityCoordinator
from .live_observability_coordinator_v1 import LiveObservabilityCoordinator
from .live_replay_coordinator_v1 import LiveReplayCoordinator
from .runtime_lifecycle_engine_v1 import (
    LifecycleState,
    RuntimeLifecycleEngine,
)


RUNTIME_COMMANDS: dict[str, str] = {
    "runtime-status": "Full live runtime status",
    "runtime-lineage": "Recent runtime lineage traces",
    "runtime-open-loops": "Open loops and unresolved items",
    "runtime-resume": "Generate runtime resume packet",
    "runtime-observe": "Recent observability traces",
    "runtime-replay": "Replay recent traces for determinism",
    "runtime-governance": "Recent governance decisions",
    "runtime-context": "Current runtime context state",
}


class LiveSubstrateRuntimeSpine:
    """The single canonical orchestration entrypoint.

    Composes:
      - LiveCognitionCoordinator (interpret, plan)
      - LiveRuntimeRouter (capability, environment, embodiment)
      - LiveExecutionCoordinator (governed adapter dispatch)
      - LiveContinuityCoordinator (persist, resume)
      - LiveObservabilityCoordinator (traces, lineage)
      - LiveReplayCoordinator (determinism verification)
      - RuntimeLifecycleEngine (session tracking)
    """

    VERSION = "v1"

    def __init__(
        self,
        cognition: LiveCognitionCoordinator | None = None,
        router: LiveRuntimeRouter | None = None,
        executor: LiveExecutionCoordinator | None = None,
        continuity: LiveContinuityCoordinator | None = None,
        observability: LiveObservabilityCoordinator | None = None,
        replay: LiveReplayCoordinator | None = None,
        lifecycle: RuntimeLifecycleEngine | None = None,
    ) -> None:
        self._cognition = cognition or LiveCognitionCoordinator()
        self._router = router or LiveRuntimeRouter()
        self._executor = executor or LiveExecutionCoordinator()
        self._continuity = continuity or LiveContinuityCoordinator()
        self._observability = observability or LiveObservabilityCoordinator()
        self._replay = replay or LiveReplayCoordinator()
        self._lifecycle = lifecycle or RuntimeLifecycleEngine()
        self._session_id = ""
        self._total_processed: int = 0
        self._total_successes: int = 0
        self._total_denials: int = 0
        self._total_failures: int = 0

    def initialize(self, session_id: str = "") -> dict[str, Any]:
        """Initialize the live runtime spine and all subsystems."""
        self._session_id = session_id or _new_id("lspine")

        runtime_session = self._lifecycle.initialize(self._session_id)
        self._continuity.start_session(self._session_id)

        self._lifecycle.register_session("continuity", f"{self._session_id}-cont")
        self._lifecycle.register_session("observability", f"{self._session_id}-obs")
        self._lifecycle.register_session("workstation", f"{self._session_id}-ws")
        self._lifecycle.register_session("browser", f"{self._session_id}-br")

        return {
            "session_id": self._session_id,
            "lifecycle_state": self._lifecycle.state.value,
            "active_sessions": len(self._lifecycle.get_active_sessions()),
            "initialized_at": _now_iso(),
        }

    def process(
        self,
        raw_input: str,
        source: RuntimeSignalSource = RuntimeSignalSource.MANUAL,
        user_id: str = "",
        channel_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> RuntimeOutcome:
        """Process a signal through the full live runtime pipeline.

        This is the ONLY allowed entrypoint for runtime operations.
        """
        start = time.monotonic()

        # Step 1: Signal reception
        signal = RuntimeSignal(
            source=source,
            raw_input=raw_input,
            payload=payload or {},
            user_id=user_id,
            channel_id=channel_id,
            session_id=self._session_id,
        )

        context = RuntimeContext(
            signal_id=signal.signal_id,
            correlation_id=signal.correlation_id,
            session_id=self._session_id,
            current_phase=RuntimePhase.SIGNAL_RECEIVED,
        )

        # Step 2: Cognition
        context = self._cognition.interpret(signal, context)

        # Check for runtime commands (dispatched internally)
        if context.command_name in RUNTIME_COMMANDS:
            return self._dispatch_runtime_command(signal, context, start)

        # Step 3: Routing
        context = self._router.resolve(signal, context)

        # Step 4: Governance
        context = self._evaluate_governance(signal, context)
        if context.governance_verdict == "denied":
            return self._make_denied_outcome(signal, context, start)

        # Step 5: Planning
        plan = self._cognition.create_plan(signal, context)
        plan.governance_approved = True

        # Step 6: Execution
        outcome = self._executor.execute_plan(signal, context, plan)

        # Step 7: Observation
        self._observability.record_trace(signal, context, outcome)
        self._observability.record_governance_event(signal, context)
        self._observability.record_execution_event(signal, context, outcome)
        self._observability.persist_lineage_receipts(context)

        # Step 8: Continuity
        continuation = self._continuity.persist_event(signal, context, outcome)
        self._observability.record_continuity_event(
            signal, context, continuation.continuation_type.value
        )

        # Step 9: Lifecycle
        self._lifecycle.record_activity(self._session_id)

        # Finalize
        outcome.duration_ms = (time.monotonic() - start) * 1000
        self._total_processed += 1
        if outcome.succeeded:
            self._total_successes += 1
        elif outcome.status == RuntimeOutcomeStatus.DENIED:
            self._total_denials += 1
        else:
            self._total_failures += 1

        return outcome

    def dispatch_command(self, command_name: str) -> dict[str, Any]:
        """Dispatch a runtime command by name."""
        handlers: dict[str, Any] = {
            "runtime-status": self._cmd_runtime_status,
            "runtime-lineage": self._cmd_runtime_lineage,
            "runtime-open-loops": self._cmd_runtime_open_loops,
            "runtime-resume": self._cmd_runtime_resume,
            "runtime-observe": self._cmd_runtime_observe,
            "runtime-replay": self._cmd_runtime_replay,
            "runtime-governance": self._cmd_runtime_governance,
            "runtime-context": self._cmd_runtime_context,
        }

        handler = handlers.get(command_name)
        if not handler:
            return {
                "error": f"Unknown runtime command: {command_name}",
                "available_commands": list(RUNTIME_COMMANDS.keys()),
            }
        return handler()

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "total_processed": self._total_processed,
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "total_failures": self._total_failures,
            "lifecycle": self._lifecycle.get_stats(),
            "cognition": self._cognition.get_stats(),
            "router": self._router.get_stats(),
            "executor": self._executor.get_stats(),
            "continuity": self._continuity.get_stats(),
            "observability": self._observability.get_stats(),
            "replay": self._replay.get_stats(),
        }

    # ------------------------------------------------------------------
    # Internal pipeline steps
    # ------------------------------------------------------------------

    def _evaluate_governance(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
    ) -> RuntimeContext:
        """Evaluate governance for the current context."""
        context.current_phase = RuntimePhase.GOVERNANCE

        verdict = "approved"
        rules = list(context.governance_rules)

        if context.risk_class in ("high", "critical", "forbidden"):
            if context.risk_class == "forbidden":
                verdict = "denied"
                rules.append("STRUCTURALLY_FORBIDDEN")
            else:
                rules.append("ELEVATED_RISK_APPROVED")

        context.governance_verdict = verdict

        decision = RuntimeDecision(
            decision_type=RuntimeDecisionType.GOVERN,
            phase=RuntimePhase.GOVERNANCE,
            input_summary=f"command:{context.command_name} risk:{context.risk_class}",
            output_summary=f"verdict:{verdict}",
            rules_applied=rules,
            approved=(verdict == "approved"),
            denial_reason="" if verdict == "approved" else "Governance denied",
            correlation_id=context.correlation_id,
        )
        context.add_decision(decision)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.GOVERNANCE,
            action="evaluate_governance",
            component="runtime_spine",
            input_hash=_content_hash({"command": context.command_name, "risk": context.risk_class}),
            output_hash=_content_hash({"verdict": verdict}),
            approved=(verdict == "approved"),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        return context

    def _dispatch_runtime_command(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        start: float,
    ) -> RuntimeOutcome:
        """Dispatch a runtime command internally."""
        result = self.dispatch_command(context.command_name)
        succeeded = "error" not in result
        duration_ms = (time.monotonic() - start) * 1000

        self._total_processed += 1
        if succeeded:
            self._total_successes += 1
        else:
            self._total_failures += 1

        outcome = RuntimeOutcome(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            session_id=self._session_id,
            status=RuntimeOutcomeStatus.SUCCESS if succeeded else RuntimeOutcomeStatus.FAILED,
            command_name=context.command_name,
            embodiment_path="runtime",
            steps_completed=1 if succeeded else 0,
            steps_total=1,
            governance_verdict="approved",
            result_data=result,
            duration_ms=duration_ms,
        )

        self._observability.record_trace(signal, context, outcome)
        self._lifecycle.record_activity(self._session_id)

        return outcome

    def _make_denied_outcome(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        start: float,
    ) -> RuntimeOutcome:
        """Create a denied outcome."""
        duration_ms = (time.monotonic() - start) * 1000
        self._total_processed += 1
        self._total_denials += 1

        outcome = RuntimeOutcome(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            session_id=self._session_id,
            status=RuntimeOutcomeStatus.DENIED,
            command_name=context.command_name,
            embodiment_path=context.embodiment_path,
            governance_verdict="denied",
            governance_rules=context.governance_rules,
            error_message="Governance denied",
            duration_ms=duration_ms,
        )

        self._observability.record_trace(signal, context, outcome)
        self._observability.record_governance_event(signal, context)

        return outcome

    # ------------------------------------------------------------------
    # Runtime command handlers
    # ------------------------------------------------------------------

    def _cmd_runtime_status(self) -> dict[str, Any]:
        return {
            "command": "runtime-status",
            "session_id": self._session_id,
            "lifecycle_state": self._lifecycle.state.value,
            "stats": self.get_stats(),
            "active_sessions": [s.to_dict() for s in self._lifecycle.get_active_sessions()],
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_lineage(self) -> dict[str, Any]:
        return {
            "command": "runtime-lineage",
            "recent_traces": self._observability.get_recent_traces(10),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_open_loops(self) -> dict[str, Any]:
        return {
            "command": "runtime-open-loops",
            "open_loops": self._continuity.get_open_loops(),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_resume(self) -> dict[str, Any]:
        packet = self._continuity.create_resume_packet()
        return {
            "command": "runtime-resume",
            "resume_packet": packet,
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_observe(self) -> dict[str, Any]:
        return {
            "command": "runtime-observe",
            "recent_traces": self._observability.get_recent_traces(20),
            "recent_governance": self._observability.get_recent_governance(10),
            "recent_execution": self._observability.get_recent_execution(10),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_replay(self) -> dict[str, Any]:
        traces = self._observability.get_recent_traces(10)
        if not traces:
            return {
                "command": "runtime-replay",
                "message": "No traces to replay",
                "timestamp": _now_iso(),
            }
        result = self._replay.replay_session(traces, session_id=self._session_id)
        return {
            "command": "runtime-replay",
            "replay_result": result.to_dict(),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_governance(self) -> dict[str, Any]:
        return {
            "command": "runtime-governance",
            "recent_governance": self._observability.get_recent_governance(20),
            "timestamp": _now_iso(),
        }

    def _cmd_runtime_context(self) -> dict[str, Any]:
        return {
            "command": "runtime-context",
            "session_id": self._session_id,
            "lifecycle_state": self._lifecycle.state.value,
            "continuity_state": self._continuity.retrieve_state(),
            "state_map": self._lifecycle.get_state_map(),
            "timestamp": _now_iso(),
        }
