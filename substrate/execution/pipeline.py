"""ExecutionPipeline — the master success loop.

Signal → Governance → WorkPacket → Adapter Execution → Proof
→ Outcome → Trace → MemoryCandidate → MemoryPromote → ResumeState

Single entry point: submit_signal() processes a signal through every stage
and returns a typed PipelineResult with all generated artifact IDs.
"""

from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from substrate.execution.executor import WorkPacketExecutor
from substrate.governance.policy_engine import PolicyEngine
from substrate.governance.risk_classes import RiskClass
from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler
from substrate.observability.outcome_classifier import OutcomeClassifier
from substrate.observability.trace_store import TraceStore
from substrate.types import (
    ExecutionOutcome,
    GovernanceCondition,
    GovernanceDecision,
    GovernanceRequest,
    PipelineExecutionResult as ExecutionResult,
    PipelineGovernanceVerdict as GovernanceVerdict,
    Proof,
    ProofStatus,
    ProofType,
    RiskLevel,
    Signal,
    SignalSource,
    SignalUrgency,
    Trace,
    TraceEventType,
    WorkPacket,
    WorkPacketStatus,
)
from substrate.workstation.state import (
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationStateManager,
)


class PipelineResult(BaseModel):
    """Typed result from a single pipeline execution."""

    trace_id: UUID
    signal_id: UUID
    governance_approved: bool
    governance_rationale: str
    executed: bool
    success: bool | None
    proof_id: UUID | None
    outcome_type: str | None
    memory_candidate_id: str | None
    memory_promoted: bool


EventListener = Callable[[str, dict[str, Any]], None]


class ExecutionPipeline:
    """The master success loop — signal to outcome in one call.

    Composes PolicyEngine, WorkPacketExecutor, OutcomeClassifier,
    TraceStore, MemoryCandidateGenerator, MemoryPromoter, and
    WorkstationStateManager into a single governed flow.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        executor: WorkPacketExecutor | None = None,
        trace_store: TraceStore | None = None,
        outcome_classifier: OutcomeClassifier | None = None,
        candidate_generator: MemoryCandidateGenerator | None = None,
        memory_promoter: MemoryPromoter | None = None,
        state_manager: WorkstationStateManager | None = None,
    ) -> None:
        self._policy = policy_engine or PolicyEngine(safe_roots=["/opt/OS"])
        self._executor = executor or WorkPacketExecutor()
        self._trace_store = trace_store or TraceStore()
        self._classifier = outcome_classifier or OutcomeClassifier()
        self._candidate_gen = candidate_generator or MemoryCandidateGenerator()
        self._promoter = memory_promoter or MemoryPromoter()
        self._reconciler = AutoReconciler()
        self._state_manager = state_manager
        self._session = WorkstationSessionState()
        self._profile = WorkstationProfile.detect()
        self._listeners: list[EventListener] = []

    def on_event(self, listener: EventListener) -> None:
        """Register a sync listener for pipeline stage events."""
        self._listeners.append(listener)

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception:
                pass

    def submit_signal(
        self,
        content: str,
        *,
        source: SignalSource = SignalSource.USER,
        risk_class: RiskClass = RiskClass.READ_ONLY,
        adapter_name: str = "shell",
        operation: str = "generic",
        params: dict[str, Any] | None = None,
        pre_approved: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Process a signal through the full governed pipeline."""
        params = params or {}

        # --- 1. Signal ---
        signal = Signal(
            source=source,
            content_type="text",
            payload={"content": content},
            raw_content=content,
            metadata=metadata or {},
        )
        self._emit("signal", {"signal_id": str(signal.id), "content": content[:120]})

        # --- 2. Protocol Trace (event-sourced) ---
        trace = Trace(signal_id=signal.id)
        trace.add_event(
            TraceEventType.SIGNAL_RECEIVED,
            f"Signal received: text from {source.value}",
            entity_id=signal.id,
        )

        # --- 3. Governance ---
        governance_request = GovernanceRequest(
            decomposition_id=uuid4(),
            component_id=uuid4(),
            proposed_action=content[:300],
            risk_level=risk_class.to_risk_level(),
            reversible=risk_class
            not in (
                RiskClass.IRREVERSIBLE_WRITE,
                RiskClass.FINANCIAL,
                RiskClass.PHYSICAL_WORLD,
            ),
            affects_external=risk_class == RiskClass.EXTERNAL_COMMUNICATION,
        )

        verdict = self._policy.evaluate(risk_class, governance_request)

        if pre_approved and not verdict.is_executable():
            verdict = GovernanceVerdict(
                request_id=governance_request.id,
                decision=GovernanceDecision.APPROVE,
                risk_level=risk_class.to_risk_level(),
                rationale="pre-approved by caller",
                decided_by="pipeline:pre_approved",
            )

        approved = verdict.is_executable()
        trace.add_event(
            TraceEventType.GOVERNANCE_DECIDED,
            f"Governance: {verdict.decision.value} — {verdict.rationale}",
            entity_id=verdict.id,
        )
        self._emit(
            "governance",
            {
                "verdict_id": str(verdict.id),
                "decision": verdict.decision.value,
                "approved": approved,
            },
        )

        executed = False
        success: bool | None = None
        proof_id: UUID | None = None
        outcome_type: str | None = None
        candidate_id: str | None = None
        promoted = False

        if approved:
            # --- 4. Work Packet ---
            packet = WorkPacket(
                governance_verdict_id=verdict.id,
                capability_id=uuid4(),
                trace_id=trace.id,
                description=content[:300],
                input_data=params,
            )
            trace.add_event(
                TraceEventType.WORK_PACKET_CREATED,
                f"Work packet created: {packet.description}",
                entity_id=packet.id,
            )
            self._emit("work_packet", {"packet_id": str(packet.id)})

            # --- 5. Execute ---
            trace.add_event(
                TraceEventType.EXECUTION_STARTED,
                f"Executing via {adapter_name}",
                entity_id=packet.id,
            )

            bundle = self._executor.execute(
                packet,
                verdict,
                adapter_name,
                operation,
                params,
            )
            result = bundle.result
            executed = True
            success = result.is_success()

            trace.add_event(
                TraceEventType.EXECUTION_COMPLETED,
                f"Execution {result.outcome.value}: duration={result.duration_ms:.0f}ms",
                entity_id=result.id,
            )
            self._emit(
                "execution",
                {
                    "result_id": str(result.id),
                    "outcome": result.outcome.value,
                    "success": success,
                    "duration_ms": result.duration_ms,
                },
            )

            # --- 6. Proof ---
            proof = bundle.proof
            proof_id = proof.id
            self._emit("proof", {"proof_id": str(proof.id), "status": proof.status.value})

            # --- 7. Outcome classify ---
            result_dict: dict[str, Any] = {}
            if success:
                result_dict["success"] = True
                result_dict["output"] = result.output_data
            else:
                if result.outcome == ExecutionOutcome.TIMEOUT:
                    result_dict["timeout"] = True
                    result_dict["timeout_detail"] = result.error or ""
                elif result.error:
                    result_dict["error"] = result.error
                else:
                    result_dict["exit_code"] = 1

            classification = self._classifier.classify(result_dict)
            outcome_type = classification.category
            self._emit(
                "outcome",
                {
                    "category": classification.category,
                    "detail": classification.detail,
                    "confidence": classification.confidence,
                },
            )

            # --- 8. JSONL Trace Store (observability projection) ---
            obs_trace = self._trace_store.create_trace(
                input_signal=content,
                governance_decision=verdict.decision.value,
                work_packet={"packet_id": str(packet.id), "adapter": adapter_name},
                adapter_used=adapter_name,
                environment=self._profile.active_environment,
                metadata=metadata,
            )
            self._trace_store.update_trace(
                obs_trace.trace_id,
                status="completed" if success else "failed",
                execution_result=result_dict,
                proof_artifact_id=str(proof_id),
                outcome=classification.category,
                outcome_detail=classification.detail,
                completed_at=str(time.time()),
            )

            # --- 9. Memory candidate ---
            if success:
                candidate = self._candidate_gen.generate_from_trace(
                    trace_id=obs_trace.trace_id,
                    input_signal=content,
                    outcome=classification.category,
                    outcome_detail=classification.detail,
                    execution_result=result_dict,
                )
                if candidate:
                    candidate_id = candidate.candidate_id
                    self._session.candidate_count += 1
                    self._emit(
                        "memory_candidate",
                        {
                            "candidate_id": candidate.candidate_id,
                            "content": candidate.content[:120],
                        },
                    )

                    # --- 10. Memory promote ---
                    if self._promoter and candidate:
                        promotion = self._promoter.evaluate(candidate)
                        promoted = promotion.get("promoted", False)
                        self._emit("memory_promotion", promotion)

                        if promoted:
                            try:
                                recon = self._reconciler.reconcile_promoted(
                                    candidate, promotion
                                )
                                self._emit("memory_reconciliation", recon)
                            except Exception:
                                pass

            self._session.record_activity(obs_trace.trace_id, classification.category)
            if classification.category in ("failure", "error"):
                self._session.record_error()
        else:
            # Blocked by governance — still record trace for auditability
            obs_trace = self._trace_store.create_trace(
                input_signal=content,
                governance_decision=verdict.decision.value,
                metadata=metadata,
            )
            self._trace_store.update_trace(
                obs_trace.trace_id,
                status="blocked",
                outcome="governance_denied",
                outcome_detail=verdict.rationale,
            )
            self._session.record_activity(obs_trace.trace_id, "governance_denied")

        # --- Finalize protocol trace ---
        trace.success = success
        self._emit("trace", {"trace_id": str(trace.id), "success": success})

        return PipelineResult(
            trace_id=trace.id,
            signal_id=signal.id,
            governance_approved=approved,
            governance_rationale=verdict.rationale,
            executed=executed,
            success=success,
            proof_id=proof_id,
            outcome_type=outcome_type,
            memory_candidate_id=candidate_id,
            memory_promoted=promoted,
        )
