"""OrganismLoopEngine -- convergence coordinator for organism execution.

Connects existing subsystems into a single intent-to-memory loop:
  EmpireRouter -> WorkPacketEngine -> UniversalWorkQueue ->
  PolicyEngine -> WorkPacketExecutor -> CanonicalWritePath -> EventSpine

This is NOT a new execution authority. It is a convergence coordinator
that wires existing subsystems together without replacing or duplicating
any of their logic.

Phase 17C. UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4, UUID

from substrate.governance.policy_engine import PolicyEngine
from substrate.governance.risk_classes import ActionRiskCategory
from substrate.execution.executor import (
    ExecutionBundle,
    WorkPacketExecutor,
    build_default_executor,
)
from substrate.memory.canonical_write import CanonicalWritePath, MemoryWriteReceipt
from substrate.organism.canonical_runtime import canonical_runtime_routing_enabled
from substrate.organism.empire_router import EmpireRouter, RealitySnapshot
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import (
    PacketLifecycleStatus,
    WorkPacket as OrganismWorkPacket,
)
from substrate.organism.work_packet_engine import WorkPacketEngine
from substrate.types import (
    GovernanceDecision,
    GovernanceRequest,
    PipelineGovernanceVerdict,
    PipelineExecutionResult as ExecutionResult,
    WorkPacket as ExecutorWorkPacket,
    WorkPacketStatus,
)

logger = logging.getLogger(__name__)

# ── Risk string → ActionRiskCategory mapping ─────────────────────────────
_RISK_STRING_MAP: dict[str, ActionRiskCategory] = {
    "low": ActionRiskCategory.SAFE_WRITE,
    "medium": ActionRiskCategory.REVERSIBLE_WRITE,
    "high": ActionRiskCategory.IRREVERSIBLE_WRITE,
    "critical": ActionRiskCategory.FINANCIAL,
}


@dataclass
class OrganismLoopResult:
    """Complete result of an organism loop cycle."""

    result_id: str = field(default_factory=lambda: f"olr-{uuid4().hex[:12]}")
    reality_snapshot_id: str = ""
    work_packet_id: str = ""
    governance_decision_id: str = ""
    execution_bundle_id: str | None = None
    proof_artifact_ids: list[str] = field(default_factory=list)
    memory_write_receipt_id: str | None = None
    reality_update_id: str | None = None
    event_ids: list[str] = field(default_factory=list)
    steps_completed: list[str] = field(default_factory=list)
    total_duration_ms: int = 0
    final_status: str = "created"
    error: str | None = None


class OrganismLoopEngine:
    """Convergence coordinator -- wires existing subsystems into the organism loop.

    NOT a new execution authority. Every step delegates to the canonical
    subsystem that owns that concern:
      - EmpireRouter for reality awareness
      - WorkPacketEngine for packet creation
      - UniversalWorkQueue for queue management
      - PolicyEngine for governance
      - WorkPacketExecutor for execution
      - CanonicalWritePath for memory writes
      - EventSpine for event transport
    """

    def __init__(
        self,
        empire_router: EmpireRouter | None = None,
        work_queue: UniversalWorkQueue | None = None,
        policy_engine: PolicyEngine | None = None,
        executor: WorkPacketExecutor | None = None,
        event_spine: EventSpine | None = None,
        canonical_write: CanonicalWritePath | None = None,
        canonical_reality_write: Any | None = None,
        mutation_router: Any | None = None,
    ) -> None:
        self._empire_router = empire_router or EmpireRouter()
        self._work_queue = work_queue or UniversalWorkQueue()
        self._policy_engine = policy_engine or PolicyEngine()
        self._executor = executor or build_default_executor()
        self._event_spine = event_spine or EventSpine()
        self._canonical_write = canonical_write or CanonicalWritePath()
        self._canonical_reality_write = canonical_reality_write
        # WP-P1-001: optional injected canonical MutationRouter. When canonical
        # routing is enabled and a router is wired, Step 5's execution is
        # submitted through the canonical runtime so the organism loop is not a
        # second, independent governance choke point. None / flag-off preserves
        # the prior PolicyEngine-gated direct-executor behavior exactly.
        self._mutation_router = mutation_router

    async def execute_intent(
        self,
        intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
    ) -> OrganismLoopResult:
        """Execute a full organism loop cycle from intent to memory.

        Steps:
        1. Reality check (EmpireRouter)
        2. WorkPacket creation (WorkPacketEngine)
        3. Queue ingest (UniversalWorkQueue)
        4. Governance gate (PolicyEngine)
        5. Execution (WorkPacketExecutor) -- if approved
        6. Canonical memory write (CanonicalWritePath)
        7. Status update on organism packet
        8. Event emission (EventSpine)

        Args:
            intent: Natural language description of what to do.
            desired_end_state: What the world should look like after.
            constraints: Optional list of constraints on execution.

        Returns:
            OrganismLoopResult documenting everything that happened.
        """
        t0 = time.monotonic()
        result = OrganismLoopResult()

        # ── Step 1: Reality check ────────────────────────────────────────
        try:
            snapshot: RealitySnapshot = self._empire_router.get_reality_snapshot()
            result.reality_snapshot_id = f"snap-{uuid4().hex[:12]}"
            result.steps_completed.append("reality_check")
            result.final_status = "created"
        except Exception as exc:
            logger.debug("organism_loop: reality check failed: %s", exc)
            result.error = f"reality_check failed: {exc}"
            result.final_status = "failed"
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        # ── Step 2: WorkPacket creation ──────────────────────────────────
        try:
            engine = self._empire_router._engine  # noqa: SLF001
            organism_packet: OrganismWorkPacket = engine.create_packet_from_intent(
                user_intent=intent,
                desired_end_state=desired_end_state,
                constraints=constraints,
            )
            result.work_packet_id = organism_packet.packet_id
            result.steps_completed.append("work_packet_created")
            result.final_status = "created"
        except Exception as exc:
            logger.debug("organism_loop: packet creation failed: %s", exc)
            result.error = f"work_packet_creation failed: {exc}"
            result.final_status = "failed"
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        # ── Step 3: Queue ingest ─────────────────────────────────────────
        try:
            self._work_queue.ingest_work_packet(organism_packet)
            result.steps_completed.append("queue_ingested")
            result.final_status = "queued"
        except Exception as exc:
            logger.debug("organism_loop: queue ingest failed: %s", exc)
            result.error = f"queue_ingest failed: {exc}"
            result.final_status = "failed"
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        # ── Step 4: Governance gate ──────────────────────────────────────
        try:
            action_risk = _RISK_STRING_MAP.get(
                organism_packet.risk_class,
                ActionRiskCategory.REVERSIBLE_WRITE,
            )
            governance_request = GovernanceRequest(
                decomposition_id=uuid4(),
                component_id=uuid4(),
                proposed_action=intent[:300],
            )
            verdict: PipelineGovernanceVerdict = self._policy_engine.evaluate(
                risk_class=action_risk,
                request=governance_request,
                context={
                    "intent": intent,
                    "work_packet_id": organism_packet.packet_id,
                    "risk_class": organism_packet.risk_class,
                    "snapshot_id": result.reality_snapshot_id,
                },
            )
            result.governance_decision_id = str(verdict.id)
            result.steps_completed.append("governance_evaluated")
            result.final_status = "governance_pending"
        except Exception as exc:
            logger.debug("organism_loop: governance evaluation failed: %s", exc)
            result.error = f"governance_evaluation failed: {exc}"
            result.final_status = "failed"
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        # Record governance decision as reality observation
        self._record_governance_decision(verdict, result, organism_packet, intent)

        # Check governance decision
        if not verdict.is_executable():
            result.final_status = (
                "denied" if verdict.decision == GovernanceDecision.DENY else "blocked"
            )
            result.steps_completed.append("governance_denied")
            self._update_organism_packet_status(
                organism_packet,
                PacketLifecycleStatus.REJECTED,
                f"governance {verdict.decision.value}: {verdict.rationale}",
            )
            self._emit_cycle_event(result, organism_packet, snapshot)
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        result.final_status = "approved"
        result.steps_completed.append("governance_approved")

        # ── Step 5: Execution ────────────────────────────────────────────
        execution_bundle: ExecutionBundle | None = None
        executor_packet: ExecutorWorkPacket | None = None
        try:
            executor_packet = self._to_executor_packet(organism_packet, verdict)

            adapter_name = self._select_adapter(organism_packet)

            # WP-P1-001 convergence point: when canonical routing is enabled and
            # a MutationRouter is wired, the execution is submitted through the
            # canonical governed runtime so this loop shares the one choke point
            # instead of being a second one. Otherwise the prior PolicyEngine-
            # gated direct-executor call runs unchanged.
            _executor_call = lambda: self._executor.execute(  # noqa: E731
                executor_packet,
                verdict,
                adapter_name,
                "execute_intent",
                {
                    "intent": intent,
                    "desired_end_state": desired_end_state,
                    "_risk_class": organism_packet.risk_class,
                },
            )

            if canonical_runtime_routing_enabled() and self._mutation_router is not None:
                execution_bundle = await asyncio.to_thread(
                    self._execute_via_canonical_runtime,
                    _executor_call,
                    organism_packet,
                    intent,
                )
            else:
                # WorkPacketExecutor.execute is synchronous -- wrap in thread
                execution_bundle = await asyncio.to_thread(_executor_call)
            result.execution_bundle_id = str(execution_bundle.result.id)
            result.proof_artifact_ids.append(str(execution_bundle.proof.id))
            result.proof_artifact_ids.append(str(execution_bundle.governance_proof.id))
            result.steps_completed.append("execution_completed")
            result.final_status = "executing"

            if execution_bundle.result.outcome.value == "success":
                result.final_status = "completed"
            else:
                result.final_status = "failed"

        except Exception as exc:
            logger.debug("organism_loop: execution failed: %s", exc)
            result.error = f"execution failed: {exc}"
            result.final_status = "failed"
            self._update_organism_packet_status(
                organism_packet,
                PacketLifecycleStatus.FAILED,
                f"execution error: {exc}",
            )
            self._emit_cycle_event(result, organism_packet, snapshot)
            result.total_duration_ms = int((time.monotonic() - t0) * 1000)
            return result

        # ── Step 6: Canonical memory write ───────────────────────────────
        if execution_bundle is not None and executor_packet is not None:
            try:
                trace_id = str(executor_packet.trace_id)
                receipt: MemoryWriteReceipt = self._canonical_write.write_from_execution(
                    execution_bundle=execution_bundle,
                    trace_id=trace_id,
                    input_signal=intent,
                    work_packet_id=organism_packet.packet_id,
                )
                result.memory_write_receipt_id = receipt.receipt_id
                result.reality_update_id = receipt.observation_id
                result.steps_completed.append("memory_written")
            except Exception as exc:
                logger.debug("organism_loop: memory write failed: %s", exc)
                # Memory write failure is non-fatal -- execution still succeeded
                result.steps_completed.append("memory_write_failed")

        # ── Step 7: Status update on organism packet ─────────────────────
        if result.final_status == "completed":
            self._update_organism_packet_status(
                organism_packet,
                PacketLifecycleStatus.COMPLETED,
                "organism loop cycle completed successfully",
            )
        else:
            self._update_organism_packet_status(
                organism_packet,
                PacketLifecycleStatus.FAILED,
                result.error or "execution did not succeed",
            )

        # ── Step 8: Event emission ───────────────────────────────────────
        self._emit_cycle_event(result, organism_packet, snapshot)

        result.total_duration_ms = int((time.monotonic() - t0) * 1000)
        return result

    def _execute_via_canonical_runtime(
        self,
        executor_call: Any,
        organism_packet: OrganismWorkPacket,
        intent: str,
    ) -> ExecutionBundle | None:
        """Run the executor step through the canonical governed runtime.

        Wraps the (already PolicyEngine-approved) WorkPacketExecutor call in a
        MutationRequest and submits it through the injected MutationRouter, so the
        organism loop's execution shares the one canonical choke point. Returns
        the ExecutionBundle produced by the executor, or None if the canonical
        runtime rejected/held the submission (fail-closed — no direct fallback).
        """
        from substrate.organism.mutation_router import MutationRequest

        bundle_holder: dict[str, Any] = {}

        def _do_execute() -> tuple[str, bool]:
            bundle = executor_call()
            bundle_holder["bundle"] = bundle
            success = bundle.result.outcome.value == "success"
            return (str(bundle.result.id), success)

        request = MutationRequest(
            mutation_name="work_packet_execute",
            intent=f"organism loop execute: {intent[:200]}",
            execute_fn=_do_execute,
            source="organism_loop",
            risk_level=organism_packet.risk_class,
            metadata={"work_packet_id": organism_packet.packet_id},
        )
        response = self._mutation_router.execute(request)
        if not response.success:
            logger.warning(
                "organism_loop canonical routing did not execute %s: %s",
                organism_packet.packet_id,
                response.rejected_reason or response.status,
            )
            return None
        return bundle_holder.get("bundle")

    def _select_adapter(self, packet: OrganismWorkPacket) -> str:
        """Select an appropriate adapter for the work packet.

        Falls back to 'shell' (always registered by build_default_executor).
        """
        registered = self._executor.registered_adapters
        if not registered:
            return "shell"
        domain = (packet.domain or "").lower()
        if "git" in domain and "git" in registered:
            return "git"
        if "file" in domain and "filesystem" in registered:
            return "filesystem"
        return registered[0]

    # ── Bridge: organism WorkPacket → executor WorkPacket ─────────────────

    @staticmethod
    def _to_executor_packet(
        organism_packet: OrganismWorkPacket,
        verdict: PipelineGovernanceVerdict,
    ) -> ExecutorWorkPacket:
        """Convert an organism WorkPacket (dataclass) to an executor WorkPacket (Pydantic).

        The organism packet is rich (67+ fields, lifecycle-aware).
        The executor packet is lean (governance-linked, trace-aware).
        This bridge maps the essential fields needed for execution.
        """
        return ExecutorWorkPacket(
            governance_verdict_id=verdict.id,
            capability_id=uuid4(),  # placeholder -- organism loop is the capability
            trace_id=uuid4(),
            description=organism_packet.user_intent[:300] or organism_packet.title[:300],
            status=WorkPacketStatus.PENDING,
            input_data={
                "organism_packet_id": organism_packet.packet_id,
                "domain": organism_packet.domain,
                "risk_class": organism_packet.risk_class,
                "desired_end_state": organism_packet.desired_end_state,
                "constraints": organism_packet.constraints,
            },
            metadata={
                "source": "organism_loop",
                "organism_packet_id": organism_packet.packet_id,
            },
        )

    def _record_governance_decision(
        self,
        verdict: Any,
        result: OrganismLoopResult,
        organism_packet: OrganismWorkPacket,
        intent: str,
    ) -> None:
        try:
            from substrate.reality_model.reality_mutation import (
                RealityMutation,
                MutationSource,
                MutationType,
            )
            from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath

            gov_mutation = RealityMutation(
                mutation_id=f"rm-gov-{uuid4().hex[:12]}",
                source_system=MutationSource.GOVERNANCE,
                source_id=result.governance_decision_id or "",
                mutation_type=MutationType.DECISION_RECORDED,
                content=f"Governance {verdict.decision.value}: {verdict.rationale[:500]}",
                confidence=0.95,
                domain="governance",
                evidence={
                    "risk_class": organism_packet.risk_class,
                    "decision": verdict.decision.value,
                    "work_packet_id": organism_packet.packet_id,
                },
                tags=["governance-decision", verdict.decision.value],
                metadata={"intent": intent[:200]},
                governance_context={"verdict_id": result.governance_decision_id or ""},
            )
            writer = self._canonical_reality_write or CanonicalRealityWritePath(
                reality_model=getattr(self._canonical_write, "_reality_model", None),
                event_spine=self._event_spine,
            )
            writer.apply_mutation(gov_mutation)
        except Exception as exc:
            logger.debug("organism_loop: governance reality write failed: %s", exc)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _update_organism_packet_status(
        self,
        packet: OrganismWorkPacket,
        target_status: PacketLifecycleStatus,
        reason: str,
    ) -> None:
        """Attempt to transition the organism packet to a target status.

        Navigates through required intermediate states if a direct
        transition is not valid. Non-fatal on failure.
        """
        # Define transition paths to reach terminal states
        _paths_to_completed: list[PacketLifecycleStatus] = [
            PacketLifecycleStatus.PLANNED,
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
            PacketLifecycleStatus.DELEGATED,
            PacketLifecycleStatus.EXECUTING,
            PacketLifecycleStatus.VALIDATING,
            PacketLifecycleStatus.COMPLETED,
        ]
        _paths_to_rejected: list[PacketLifecycleStatus] = [
            PacketLifecycleStatus.PLANNED,
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.REJECTED,
        ]
        _paths_to_failed: list[PacketLifecycleStatus] = [
            PacketLifecycleStatus.PLANNED,
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
            PacketLifecycleStatus.DELEGATED,
            PacketLifecycleStatus.EXECUTING,
            PacketLifecycleStatus.FAILED,
        ]

        if target_status == PacketLifecycleStatus.COMPLETED:
            path = _paths_to_completed
        elif target_status == PacketLifecycleStatus.REJECTED:
            path = _paths_to_rejected
        elif target_status == PacketLifecycleStatus.FAILED:
            path = _paths_to_failed
        else:
            path = [target_status]

        try:
            from substrate.organism.work_packet import _VALID_TRANSITIONS

            for step in path:
                if packet.status == target_status:
                    break
                allowed = _VALID_TRANSITIONS.get(packet.status, frozenset())
                if step in allowed:
                    packet.status = step
                    packet.status_reason = reason
                    packet.updated_at = time.time()
        except Exception as exc:
            logger.debug(
                "organism_loop: status update to %s failed: %s",
                target_status.value,
                exc,
            )

    def _emit_cycle_event(
        self,
        result: OrganismLoopResult,
        packet: OrganismWorkPacket,
        snapshot: RealitySnapshot,
    ) -> None:
        """Emit an organism_loop_cycle event via the EventSpine."""
        try:
            event = self._event_spine.emit(
                domain=EventDomain.EXECUTION,
                event_type="organism_loop_cycle",
                source="organism_loop",
                data={
                    "result_id": result.result_id,
                    "work_packet_id": result.work_packet_id,
                    "governance_decision_id": result.governance_decision_id,
                    "execution_bundle_id": result.execution_bundle_id,
                    "memory_write_receipt_id": result.memory_write_receipt_id,
                    "reality_update_id": result.reality_update_id,
                    "final_status": result.final_status,
                    "steps_completed": result.steps_completed,
                    "total_duration_ms": result.total_duration_ms,
                    "active_domains": snapshot.active_domains,
                    "error": result.error,
                },
                correlation_id=result.work_packet_id,
            )
            result.event_ids.append(event.event_id)
        except Exception as exc:
            logger.debug("organism_loop: event emission failed: %s", exc)
