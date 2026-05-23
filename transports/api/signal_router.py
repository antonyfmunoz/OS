"""Signal router — enforces the legal processing pathway for all signals."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from substrate.types import (
    Decomposition,
    GovernanceDecision,
    GovernanceRequest,
    GovernanceVerdict,
    RiskLevel,
    Interpretation,
    Outcome,
    OutcomeType,
    Signal,
    Trace,
    TraceEventType,
    WorkPacket,
    WorkPacketPriority,
    WorkPacketStatus,
)
from transports.api.event_bus import Event, EventBus
from transports.api.invariants import InvariantChecker

logger = logging.getLogger(__name__)


class SignalRouter:
    """Routes signals through the mandatory processing pipeline.

    Legal path: signal → interpret → decompose → govern → execute → trace → outcome
    No shortcuts. No direct execution.
    """

    def __init__(self, event_bus: EventBus, invariant_checker: InvariantChecker) -> None:
        self._event_bus = event_bus
        self._invariant_checker = invariant_checker
        self._traces: dict[str, Trace] = {}

    async def intake(self, signal: Signal) -> Trace:
        """Entry point — all signals MUST enter here."""
        violation = self._invariant_checker.check_signal_intake(signal)
        if violation:
            raise ValueError(f"Signal intake violation: {violation}")

        trace = Trace(signal_id=signal.id)
        trace.add_event(
            TraceEventType.SIGNAL_RECEIVED,
            f"Signal received: {signal.content_type} from {signal.source.value}",
            entity_id=signal.id,
        )
        self._traces[str(trace.id)] = trace

        await self._event_bus.publish(
            Event(
                event_type="signal.received",
                source="router",
                payload={"signal_id": str(signal.id), "trace_id": str(trace.id)},
                correlation_id=signal.correlation_id,
            )
        )

        return trace

    async def submit_interpretation(self, interpretation: Interpretation, trace: Trace) -> None:
        """Record that interpretation is complete."""
        trace.add_event(
            TraceEventType.INTERPRETATION_COMPLETE,
            f"Interpreted as: {interpretation.interpretation_type.value}",
            entity_id=interpretation.id,
        )

        await self._event_bus.publish(
            Event(
                event_type="interpretation.complete",
                source="router",
                payload={
                    "interpretation_id": str(interpretation.id),
                    "trace_id": str(trace.id),
                },
            )
        )

    async def submit_decomposition(self, decomposition: Decomposition, trace: Trace) -> None:
        """Record that decomposition is complete."""
        trace.add_event(
            TraceEventType.DECOMPOSITION_COMPLETE,
            f"Decomposed into {len(decomposition.components)} components",
            entity_id=decomposition.id,
        )

        await self._event_bus.publish(
            Event(
                event_type="decomposition.complete",
                source="router",
                payload={
                    "decomposition_id": str(decomposition.id),
                    "trace_id": str(trace.id),
                    "component_count": len(decomposition.components),
                },
            )
        )

    async def request_governance(
        self, request: GovernanceRequest, trace: Trace
    ) -> GovernanceVerdict:
        """Submit a governance request — blocks until decided."""
        trace.add_event(
            TraceEventType.GOVERNANCE_REQUESTED,
            f"Governance requested for: {request.proposed_action}",
            entity_id=request.id,
        )

        await self._event_bus.publish(
            Event(
                event_type="governance.requested",
                source="router",
                payload={
                    "request_id": str(request.id),
                    "trace_id": str(trace.id),
                    "risk_level": request.risk_level.value,
                },
            )
        )

        verdict = GovernanceVerdict(
            request_id=request.id,
            decision=GovernanceDecision.APPROVE
            if request.risk_level in (RiskLevel.NEGLIGIBLE, RiskLevel.LOW)
            else GovernanceDecision.DEFER,
            risk_level=request.risk_level,
            rationale=f"Auto-decision based on risk level: {request.risk_level.value}",
        )

        trace.add_event(
            TraceEventType.GOVERNANCE_DECIDED,
            f"Governance decision: {verdict.decision.value}",
            entity_id=verdict.id,
        )

        return verdict

    async def create_work_packet(
        self,
        verdict: GovernanceVerdict,
        capability_id: str,
        trace: Trace,
        description: str,
        input_data: dict | None = None,
    ) -> WorkPacket | None:
        """Create a work packet only if governance approves."""
        if not verdict.is_executable():
            logger.warning(
                f"Cannot create work packet — governance not executable: {verdict.decision.value}"
            )
            return None

        from uuid import UUID

        work_packet = WorkPacket(
            governance_verdict_id=verdict.id,
            capability_id=UUID(capability_id) if isinstance(capability_id, str) else capability_id,
            trace_id=trace.id,
            description=description,
            input_data=input_data or {},
        )

        violations = self._invariant_checker.validate_work_packet(work_packet)
        if self._invariant_checker.has_hard_violations(violations):
            logger.error(f"Work packet blocked by invariants: {violations}")
            return None

        trace.add_event(
            TraceEventType.WORK_PACKET_CREATED,
            f"Work packet created: {description}",
            entity_id=work_packet.id,
        )

        await self._event_bus.publish(
            Event(
                event_type="work_packet.created",
                source="router",
                payload={"work_packet_id": str(work_packet.id), "trace_id": str(trace.id)},
            )
        )

        return work_packet

    async def complete_trace(self, trace: Trace, outcome: Outcome) -> None:
        """Finalize a trace with its outcome."""
        trace.completed_at = datetime.now(timezone.utc)
        trace.success = outcome.is_successful()

        await self._event_bus.publish(
            Event(
                event_type="trace.completed",
                source="router",
                payload={
                    "trace_id": str(trace.id),
                    "signal_id": str(trace.signal_id),
                    "success": trace.success,
                    "outcome_type": outcome.outcome_type.value,
                },
            )
        )
