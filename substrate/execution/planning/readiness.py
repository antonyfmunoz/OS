"""Decision readiness — when a Plan may request its acceptance Decision.

Plan §8 (Wave 1). A Plan surfaces a HUD DecisionRequest ONLY at
DECISION_READY. The assessment distinguishes:

  - planning evidence needed TO JUDGE the Plan → blocks readiness
    (unresolved clarification, missing grounding, unbound objective,
    empty graph, unresolved requirement gaps);
  - artifacts/Tasks the Plan proposes TO CREATE → NEVER block acceptance
    (they become Tasks — that is what approving the plan schedules).

Plan acceptance ≠ execution authorization: the emitted decision package says
exactly what approval does and does not authorize.

UMH substrate subsystem. Instance-agnostic. Deterministic.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from substrate.execution.planning.records import (
    GapAssessmentSnapshot,
    ObjectivePlanRecord,
    PlanningSession,
)


class DecisionReadiness(str, Enum):
    INVESTIGATING = "investigating"
    CLARIFICATION_REQUIRED = "clarification_required"
    TECHNICAL_WORK_REMAINING = "technical_work_remaining"
    DECISION_READY = "decision_ready"
    PROHIBITED = "prohibited"
    FAILED = "failed"


@dataclass
class DecisionReadinessAssessment:
    """The readiness verdict + the decision package it emits when ready."""

    state: str = DecisionReadiness.INVESTIGATING.value
    blocking_items: list[str] = field(default_factory=list)
    non_blocking_notes: list[str] = field(default_factory=list)
    decision_package: dict[str, Any] = field(default_factory=dict)
    assessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionReadinessAssessment:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def evaluate_decision_readiness(
    plan: ObjectivePlanRecord,
    session: PlanningSession,
    gap_snapshot: GapAssessmentSnapshot | None = None,
    requirement_gaps: list[str] | None = None,
) -> DecisionReadinessAssessment:
    """Deterministically evaluate whether the Plan may request acceptance."""
    assessment = DecisionReadinessAssessment()
    blocking = assessment.blocking_items
    notes = assessment.non_blocking_notes

    state = (session.assessment or {}).get("state", "")
    if state == "prohibited":
        assessment.state = DecisionReadiness.PROHIBITED.value
        blocking.append("objective assessed PROHIBITED")
        return assessment
    if state == "failed" or session.operation_stage == "failed":
        assessment.state = DecisionReadiness.FAILED.value
        blocking.append("planning operation failed — recover before deciding")
        return assessment
    if session.stage == "awaiting_clarification":
        assessment.state = DecisionReadiness.CLARIFICATION_REQUIRED.value
        blocking.append("material clarification outstanding")
        return assessment

    # Evidence needed TO JUDGE the plan (blocks readiness).
    if not plan.objective_id:
        blocking.append("plan is not bound to a canonical Objective")
    if not plan.grounding_snapshot_id:
        blocking.append("no grounding snapshot — current reality not evidenced")
    if not plan.current_state_id or not plan.desired_state_id:
        blocking.append("current/desired state records missing")
    packet_nodes = [
        n for n in plan.nodes if n.get("kind") == "packet" and n.get("status") == "active"
    ]
    if not packet_nodes:
        blocking.append("plan graph contains no active work nodes")
    for gap in requirement_gaps or []:
        blocking.append(f"requirement gap: {gap}")
    if gap_snapshot is not None and gap_snapshot.contradictions:
        blocking.append(
            f"{len(gap_snapshot.contradictions)} unresolved contradiction(s) in gap assessment"
        )

    # Things the plan proposes TO CREATE — never blocking (test AD).
    if gap_snapshot is not None and gap_snapshot.unknowns:
        notes.append(
            f"{len(gap_snapshot.unknowns)} unknown(s) become investigation Tasks — not blocking"
        )
    notes.append(f"{len(plan.workpacket_ids)} Task(s) will be scheduled by acceptance")

    if blocking:
        assessment.state = DecisionReadiness.TECHNICAL_WORK_REMAINING.value
        return assessment

    assessment.state = DecisionReadiness.DECISION_READY.value
    assessment.decision_package = {
        "exact_decision": "Accept plan "
        f"{plan.plan_record_id} v{plan.graph_version} for objective {plan.objective_id}",
        "objective_id": plan.objective_id,
        "objective_text": plan.objective_text[:300],
        "scope": {"tenant_id": session.tenant_id, "conversation_id": plan.conversation_id},
        "recommendation": "accept",
        "alternatives": ["reject the plan", "request a revision in chat"],
        "expected_effect": (
            f"plan status → approved; {len(plan.workpacket_ids)} Task(s) remain at most "
            "PLANNED on the Work board"
        ),
        "risk": "low — planning artifacts only, no execution authority conveyed",
        "unresolved_uncertainty": list((gap_snapshot.unknowns if gap_snapshot else [])),
        "proof_collected": {
            "grounding_snapshot_id": plan.grounding_snapshot_id,
            "current_state_id": plan.current_state_id,
            "desired_state_id": plan.desired_state_id,
            "gap_model_id": plan.gap_model_id,
        },
        "authorizes": "plan acceptance ONLY",
        "does_not_authorize": (
            "execution — starting any Task requires a distinct future "
            "execution-authorization decision (Wave 2); zero ExecutionAttempts exist"
        ),
    }
    return assessment


__all__ = [
    "DecisionReadiness",
    "DecisionReadinessAssessment",
    "evaluate_decision_readiness",
]
