"""ExecutionPipeline — the master success loop.

Signal → Understanding (interpret/decompose/domain/laws/reality)
→ Mastery Gate → Governance → WorkPacket → Adapter Execution → Proof
→ Outcome → Trace → MemoryCandidate → MemoryPromote → Reality Model Update

Single entry point: submit_signal() processes a signal through every stage
and returns a typed PipelineResult with all generated artifact IDs.
"""

from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from substrate.execution.executor import WorkPacketExecutor
from substrate.execution.mastery_gate import MasteryGate
from substrate.execution.understanding_bridge import UnderstandingBridge
from substrate.governance.policy_engine import PolicyEngine
from substrate.governance.risk_classes import RiskClass
from substrate.governance.validation.completeness_engine import CompletenessEngine
from substrate.organism.homeostasis import HomeostasisEngine
from substrate.understanding.deliberation.council import DeliberationCouncil, Verdict
from substrate.intelligence.runtime import IntelligenceRuntime
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
    understanding_confidence: float = 0.0
    law_violations: list[str] = Field(default_factory=list)
    mastery_assured: bool = True
    mastery_blocked_tools: list[str] = Field(default_factory=list)
    deliberation_verdict: str | None = None
    completeness_score: float | None = None


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
        self._mastery_gate = MasteryGate()
        self._understanding = UnderstandingBridge()
        self._homeostasis = HomeostasisEngine()
        self._council = DeliberationCouncil()
        self._completeness = CompletenessEngine()
        self._intelligence = IntelligenceRuntime()
        self._state_manager = state_manager
        self._session = WorkstationSessionState()
        self._profile = WorkstationProfile.detect()
        self._listeners: list[EventListener] = []

    def health_check(self) -> dict[str, Any]:
        """Run homeostasis check and return system health report."""
        report = self._homeostasis.check()
        return report.to_dict()

    def intelligence_health(self) -> dict[str, Any]:
        """Return pattern + decision intelligence stats."""
        return self._intelligence.health()

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

        # --- 3-7. Understanding (interpret → decompose → domain → laws → reality) ---
        understanding = self._understanding.process(
            content=content,
            signal_id=str(signal.id),
            trace_id=str(trace.id),
        )
        trace.add_event(
            TraceEventType.SIGNAL_RECEIVED,
            (
                f"Understanding: confidence={understanding.confidence:.2f}, "
                f"projections={len(understanding.domain_projections)}, "
                f"violations={len(understanding.law_violations)}"
            ),
            entity_id=signal.id,
        )
        self._emit("understanding", understanding.to_dict())

        # --- 8. Mastery Gate (step 16) ---
        mastery = self._mastery_gate.check(
            content,
            founder_waiver=pre_approved,
            adapter_name=adapter_name,
        )
        if mastery.tools_detected:
            trace.add_event(
                TraceEventType.SIGNAL_RECEIVED,
                (
                    f"Mastery: {len(mastery.tools_assured)} assured, "
                    f"{len(mastery.tools_blocked)} blocked"
                ),
                entity_id=signal.id,
            )
            self._emit("mastery", mastery.to_dict())

        if not mastery.can_proceed:
            blocked_str = ", ".join(mastery.tools_blocked)
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Mastery gate blocked: {blocked_str}",
                entity_id=signal.id,
            )
            obs_trace = self._trace_store.create_trace(
                input_signal=content,
                governance_decision="mastery_blocked",
                metadata=metadata,
            )
            self._trace_store.update_trace(
                obs_trace.trace_id,
                status="blocked",
                outcome="mastery_blocked",
                outcome_detail=f"tools without mastery: {blocked_str}",
            )
            self._session.record_activity(obs_trace.trace_id, "mastery_blocked")
            trace.success = False
            self._emit("trace", {"trace_id": str(trace.id), "success": False})
            return PipelineResult(
                trace_id=trace.id,
                signal_id=signal.id,
                governance_approved=False,
                governance_rationale=f"mastery not assured: {blocked_str}",
                executed=False,
                success=None,
                proof_id=None,
                outcome_type="mastery_blocked",
                memory_candidate_id=None,
                memory_promoted=False,
                understanding_confidence=understanding.confidence,
                law_violations=understanding.law_violations,
                mastery_assured=False,
                mastery_blocked_tools=mastery.tools_blocked,
            )

        # --- 8b. Deliberation Council (high-risk signals only) ---
        deliberation_verdict: str | None = None
        if risk_class not in (RiskClass.READ_ONLY, RiskClass.REVERSIBLE_WRITE):
            delib = self._council.deliberate(content, context={"domain": "execution"})
            deliberation_verdict = delib.final_verdict.value
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Council: {delib.final_verdict.value} (confidence={delib.overall_confidence:.2f})",
                entity_id=signal.id,
            )
            self._emit("deliberation", delib.to_dict())
            if delib.final_verdict == Verdict.REJECT and not pre_approved:
                obs_trace = self._trace_store.create_trace(
                    input_signal=content,
                    governance_decision="council_rejected",
                    metadata=metadata,
                )
                self._trace_store.update_trace(
                    obs_trace.trace_id,
                    status="blocked",
                    outcome="council_rejected",
                    outcome_detail=f"dissenting: {', '.join(delib.dissenting_roles)}",
                )
                self._session.record_activity(obs_trace.trace_id, "council_rejected")
                trace.success = False
                self._emit("trace", {"trace_id": str(trace.id), "success": False})
                return PipelineResult(
                    trace_id=trace.id,
                    signal_id=signal.id,
                    governance_approved=False,
                    governance_rationale=f"council rejected: {delib.synthesis.rationale if delib.synthesis else 'no synthesis'}",
                    executed=False,
                    success=None,
                    proof_id=None,
                    outcome_type="council_rejected",
                    memory_candidate_id=None,
                    memory_promoted=False,
                    understanding_confidence=understanding.confidence,
                    law_violations=understanding.law_violations,
                    mastery_assured=mastery.can_proceed,
                    mastery_blocked_tools=mastery.tools_blocked,
                    deliberation_verdict=deliberation_verdict,
                )

        # --- 9. Governance ---
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

            # --- Intelligence learning (pattern + decision from execution) ---
            try:
                self._intelligence.learn_from_execution(
                    content=content,
                    action=f"{adapter_name}:{operation}",
                    outcome=classification.category,
                    success=bool(success),
                    domain=classification.detail or "general",
                )
            except Exception:
                pass

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

            # --- 11. Reality Model update (step 27) ---
            self._understanding.record_outcome(
                content=content,
                outcome_type=classification.category,
                signal_id=str(signal.id),
                trace_id=str(trace.id),
            )

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

        # --- Homeostasis: record execution for health monitoring ---
        self._homeostasis.record_execution(success=bool(success))

        # --- Completeness check on pipeline result ---
        completeness_score: float | None = None
        try:
            pipeline_dict = {
                "signal_id": str(signal.id),
                "executed": executed,
                "outcome_type": outcome_type,
                "memory_promoted": promoted,
                "memory_candidate_id": candidate_id,
                "governance_approved": approved,
                "governance_rationale": verdict.rationale,
                "proof_id": str(proof_id) if proof_id else None,
                "trace_id": str(trace.id),
                "mastery_assured": mastery.can_proceed,
                "understanding_confidence": understanding.confidence,
                "success": success,
            }
            comp_result = self._completeness.evaluate_pipeline_result(pipeline_dict)
            completeness_score = comp_result.score
            self._emit("completeness", comp_result.to_dict())
        except Exception:
            pass

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
            understanding_confidence=understanding.confidence,
            law_violations=understanding.law_violations,
            mastery_assured=mastery.can_proceed,
            mastery_blocked_tools=mastery.tools_blocked,
            deliberation_verdict=deliberation_verdict,
            completeness_score=completeness_score,
        )
