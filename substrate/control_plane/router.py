"""SignalRouter — the integration point that wires all subsystems together.

Single entry point from transports. route() orchestrates the full lifecycle:
identity → context → governance → spine.

Source mapping:
- gateway.py (2,063 lines) → signal routing, deterministic intent, fix-forever
- intent_handler.py (410 lines) → deterministic intent classification
- capability_router.py (610 lines) → intent-driven tool selection
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.types import (
    SignalEnvelope,
    ExecutionResult,
    ExecutionOutcome,
    TraceRecord,
    TraceEventType,
    RiskClass,
    GovernanceDecision,
)


@runtime_checkable
class SignalRouter(Protocol):
    async def route(self, signal: SignalEnvelope) -> ExecutionResult: ...


class ConcreteSignalRouter:
    """Routes signals through the full substrate lifecycle."""

    def __init__(
        self,
        identity_resolver=None,
        context_assembler=None,
        governance_engine=None,
        memory_system=None,
        registry=None,
        execution_spine=None,
        trace_recorder=None,
        feedback_capture=None,
    ):
        self._identity = identity_resolver
        self._context = context_assembler
        self._governance = governance_engine
        self._memory = memory_system
        self._registry = registry
        self._spine = execution_spine
        self._trace = trace_recorder
        self._feedback = feedback_capture

    async def route(self, signal: SignalEnvelope) -> ExecutionResult:
        trace = TraceRecord(signal_id=signal.id)
        trace.add_event(TraceEventType.SIGNAL_RECEIVED, f"Signal from {signal.source.value}")

        try:
            identity = await self._identity.resolve(signal)
            trace.add_event(TraceEventType.IDENTITY_RESOLVED, f"Identity: {identity.ai_name}")

            context = await self._context.assemble(signal, identity)
            trace.add_event(TraceEventType.CONTEXT_ASSEMBLED, "Context assembled")

            verdict = await self._governance.classify(signal, context)
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Risk: {verdict.risk_class.value}, Decision: {verdict.decision.value}",
            )

            if not verdict.is_executable():
                trace.complete(success=True)
                if self._trace:
                    await self._trace.persist(trace)
                result = ExecutionResult(
                    signal_id=signal.id,
                    trace_id=trace.id,
                    outcome=ExecutionOutcome.BLOCKED,
                    risk_class=verdict.risk_class,
                    governance_decision=verdict.decision,
                    output=verdict.rationale,
                )
                if self._feedback:
                    fb = await self._feedback.capture(trace, result)
                    await self._feedback.persist(fb)
                return result

            result = await self._spine.execute(signal, context, verdict, trace=trace)

            trace.complete(success=result.is_success())
            if self._trace:
                await self._trace.persist(trace)

            if self._feedback:
                feedback = await self._feedback.capture(trace, result)
                await self._feedback.persist(feedback)

            return result

        except Exception as e:
            trace.add_event(TraceEventType.ERROR, str(e)[:300])
            trace.complete(success=False)
            if self._trace:
                await self._trace.persist(trace)
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.FAILURE,
                error=str(e)[:300],
            )
