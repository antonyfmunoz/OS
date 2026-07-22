"""Objective-plan decisions — the HUD-only plan-acceptance authority.

Plan §8 (Wave 1). One decision path:

    DECISION_READY plan → AWAITING_APPROVAL → HUD approve/reject/cancel
    (via UnifiedApprovalRuntime, source_type=objective_plan)
    → apply_plan_decision (governed objective_plan_decision mutation)
    → plan status flips; packets are NEVER touched (they stay at most
      PLANNED, non-executable) — authorization_effect=plan_acceptance_only.

Chat NEVER commits a decision: a chat "approve" only surfaces/focuses the
HUD item. Double decisions are safe: a repeat of the same decision on the
same decision_ref is an idempotent no-op; a conflicting decision raises.

The internal Decision object is the canonical ``substrate.types.
ApprovalRequest`` (adapted, §22.3) — no new generic Decision type.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from substrate.execution.planning.records import ObjectivePlanRecord, ObjectivePlanStatus
from substrate.execution.planning.store import PlanningStore, PlanningStoreConflict

logger = logging.getLogger(__name__)

DECISION_MUTATION_NAME = "objective_plan_decision"
PLAN_APPROVED_STATUS_MESSAGE = "PLAN APPROVED — EXECUTION NOT STARTED"

_DECISION_TO_STATUS = {
    "approve": ObjectivePlanStatus.APPROVED.value,
    "reject": ObjectivePlanStatus.REJECTED.value,
    "cancel": ObjectivePlanStatus.CANCELLED.value,
}
_DECIDABLE_FROM = {
    "approve": (ObjectivePlanStatus.AWAITING_APPROVAL.value,),
    "reject": (ObjectivePlanStatus.AWAITING_APPROVAL.value,),
    "cancel": (
        ObjectivePlanStatus.DRAFT.value,
        ObjectivePlanStatus.AWAITING_APPROVAL.value,
        ObjectivePlanStatus.APPROVED.value,
    ),
}


class PlanDecisionConflict(RuntimeError):
    """A conflicting decision already exists for this decision_ref."""


def plan_decision_ref(plan: ObjectivePlanRecord) -> str:
    from substrate.types import build_decision_ref

    return build_decision_ref(
        "objective_plan", plan.plan_record_id, "plan_acceptance", f"v{plan.graph_version}"
    )


def build_plan_approval_request(plan: ObjectivePlanRecord) -> Any:
    """Project one AWAITING_APPROVAL plan into the canonical Decision object."""
    from substrate.types import ApprovalOrigin, ApprovalRequest, RiskClass

    scope = plan.work_scope or {}
    return ApprovalRequest(
        approval_id=plan_decision_ref(plan),  # stable — never minted per poll
        source_origin=ApprovalOrigin.OTHER,
        source_id=plan.plan_record_id,
        source_channel="objective_plan",
        title=f"Accept plan v{plan.graph_version}",
        description=plan.objective_text[:2000],
        operation="plan_acceptance",
        requested_action="approve or reject the objective plan",
        risk_class=RiskClass.LOW,
        org_id=str(scope.get("legacy_org_id", "")),
        decision_ref=plan_decision_ref(plan),
        decision_kind="plan_acceptance",
        subject_type="objective_plan",
        subject_id=plan.plan_record_id,
        subject_version=f"v{plan.graph_version}",
        tenant_id=str(scope.get("tenant_id", "")),
        scope_ref=f"tenant:{scope.get('tenant_id', '')}/conversation:{plan.conversation_id}",
        authorization_effect="plan_acceptance_only",
    )


def derive_decision_fields(approval: Any) -> dict[str, str]:
    """§23.8 legacy adapter: deterministically derive the typed Decision
    fields where possible; unknowns FAIL CLOSED to pending + non-executable."""
    from substrate.types import build_decision_ref

    source_type = getattr(approval, "source_channel", "") or getattr(approval, "source_origin", "")
    source_type = getattr(source_type, "value", source_type) or "unknown"
    source_id = getattr(approval, "source_id", "") or getattr(approval, "approval_id", "")
    kind = getattr(approval, "decision_kind", "") or getattr(approval, "operation", "") or "unknown"
    version = getattr(approval, "subject_version", "") or "v1"
    derived = {
        "decision_ref": getattr(approval, "decision_ref", "")
        or build_decision_ref(str(source_type), str(source_id), str(kind), str(version)),
        "decision_kind": str(kind),
        "subject_type": str(source_type),
        "subject_id": str(source_id),
        "subject_version": str(version),
        "authorization_effect": getattr(approval, "authorization_effect", "") or "none_fail_closed",
    }
    return derived


def apply_plan_decision(
    store: PlanningStore,
    plan_record_id: str,
    decision: str,
    decided_by: str = "operator",
    reason: str = "",
    mutation_runner: Callable[..., Any] | None = None,
    event_emit: Callable[[str, dict[str, Any]], None] | None = None,
    expected_version: int | None = None,
) -> ObjectivePlanRecord:
    """Apply one HUD plan decision under governed mutation.

    Packets are NEVER touched: they remain at most PLANNED with non-empty
    approval gates, and zero ExecutionAttempts exist afterward. Idempotent:
    repeating the SAME decision on an already-decided plan returns it
    unchanged; a CONFLICTING decision raises PlanDecisionConflict.
    """
    decision = (decision or "").strip().lower()
    if decision not in _DECISION_TO_STATUS:
        raise ValueError(f"unknown plan decision {decision!r} (approve|reject|cancel)")

    plan = store.get_plan(plan_record_id)
    if plan is None:
        raise PlanningStoreConflict(f"plan {plan_record_id} not found")

    target_status = _DECISION_TO_STATUS[decision]
    if plan.status == target_status:
        return plan  # double-decision-safe no-op
    if plan.status not in _DECIDABLE_FROM[decision]:
        raise PlanDecisionConflict(
            f"plan {plan_record_id} is {plan.status!r} — cannot {decision} "
            f"(a conflicting decision already resolved this decision_ref)"
        )

    if expected_version is not None and expected_version != plan.graph_version:
        # Optimistic-concurrency: the caller decided against a STALE view
        # (e.g. a revision superseded it) — reject, never silently apply.
        raise PlanDecisionConflict(
            f"plan {plan_record_id}: caller saw v{expected_version}, "
            f"current is v{plan.graph_version}"
        )

    approval = build_plan_approval_request(plan)
    expected_status = plan.status

    def _apply() -> tuple[str, bool]:
        plan.status = target_status
        plan.updated_at = time.time()
        entry = {
            "decision_ref": approval.decision_ref,
            "decision": decision,
            "decided_by": decided_by,
            "reason": reason,
            "authorization_effect": "plan_acceptance_only",
            "decided_at": time.time(),
        }
        if decision == "approve":
            entry["status_message"] = PLAN_APPROVED_STATUS_MESSAGE
        plan.decision_log.append(entry)
        if approval.decision_ref not in plan.approval_request_ids:
            plan.approval_request_ids.append(approval.decision_ref)
        store.update_plan_cas(
            plan,
            expected_current_version=plan.graph_version,
            expected_statuses=(expected_status,),
        )
        return (f"plan {decision}d: {plan.plan_record_id}", True)

    if mutation_runner is None:
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        mutation_runner = _substrate_native_governed_mutation

    response = mutation_runner(
        mutation_name=DECISION_MUTATION_NAME,
        intent=f"{decision} objective plan {plan_record_id} (plan acceptance only)",
        execute_fn=_apply,
        source="objective_plan_decisions",
        metadata={
            "decision_ref": approval.decision_ref,
            "plan_record_id": plan_record_id,
            "objective_id": plan.objective_id,
            "tenant_id": approval.tenant_id,
            "decided_by": decided_by,
        },
    )
    if not bool(getattr(response, "success", False)):
        raise RuntimeError(
            f"plan decision rejected by governance: {getattr(response, 'output', '')}"
        )

    if event_emit is not None:
        try:
            event_emit(
                "planning.decision_recorded",
                {
                    "decision_ref": approval.decision_ref,
                    "decision": decision,
                    "plan_record_id": plan_record_id,
                    "objective_id": plan.objective_id,
                    "tenant_id": approval.tenant_id,
                    "authorization_effect": "plan_acceptance_only",
                },
            )
        except Exception as exc:
            logger.debug("decision event emit failed: %s", exc)
    return plan


class ObjectivePlanDecisionSource:
    """UnifiedApprovalRuntime source adapter (source_type=objective_plan).

    Pending rows carry STABLE ids (the decision_ref — never minted per poll),
    HIGH urgency so plan decisions cannot fall out of the HUD top slice, a
    run-tag-visible description (the objective text), and the plan context
    the ControlPanel row renders.
    """

    def __init__(
        self,
        store: PlanningStore | None = None,
        mutation_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._store = store or PlanningStore()
        self._mutation_runner = mutation_runner

    def pending_decisions(self) -> list[Any]:
        from substrate.workstation.unified_approval_runtime import (
            ApprovalSourceType,
            UnifiedApproval,
        )

        rows: list[Any] = []
        try:
            plans = self._store.load_plans()
        except Exception as exc:
            logger.debug("objective_plan pending read failed: %s", exc)
            return rows
        for plan in plans:
            if plan.status != ObjectivePlanStatus.AWAITING_APPROVAL.value:
                continue
            packet_count = len(plan.workpacket_ids)
            rows.append(
                UnifiedApproval(
                    approval_id=plan_decision_ref(plan),
                    source_type=ApprovalSourceType.OBJECTIVE_PLAN,
                    title=f"Accept plan v{plan.graph_version}",
                    description=plan.objective_text[:300],
                    risk_class="high",  # HUD top-slice guarantee (owner ruling)
                    waiting_since=plan.updated_at or plan.created_at,
                    work_id=plan.plan_record_id,
                    context={
                        "details": {
                            "plan_record_id": plan.plan_record_id,
                            "objective_id": plan.objective_id,
                            "graph_version": plan.graph_version,
                            "packet_count": packet_count,
                            "conversation_id": plan.conversation_id,
                        },
                        "decision_ref": plan_decision_ref(plan),
                        "authorization_effect": "plan_acceptance_only",
                    },
                )
            )
        return rows

    def approve(self, plan_record_id: str, decided_by: str = "operator") -> bool:
        try:
            apply_plan_decision(
                self._store,
                plan_record_id,
                "approve",
                decided_by=decided_by,
                mutation_runner=self._mutation_runner,
            )
            return True
        except Exception as exc:
            logger.error("objective_plan approve failed for %s: %s", plan_record_id, exc)
            return False

    def reject(self, plan_record_id: str, reason: str = "", decided_by: str = "operator") -> bool:
        try:
            apply_plan_decision(
                self._store,
                plan_record_id,
                "reject",
                decided_by=decided_by,
                reason=reason,
                mutation_runner=self._mutation_runner,
            )
            return True
        except Exception as exc:
            logger.error("objective_plan reject failed for %s: %s", plan_record_id, exc)
            return False


__all__ = [
    "DECISION_MUTATION_NAME",
    "PLAN_APPROVED_STATUS_MESSAGE",
    "ObjectivePlanDecisionSource",
    "PlanDecisionConflict",
    "apply_plan_decision",
    "build_plan_approval_request",
    "derive_decision_fields",
    "plan_decision_ref",
]
