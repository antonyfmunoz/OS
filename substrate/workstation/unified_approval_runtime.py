"""Unified Approval Runtime — single approval queue across all UMH subsystems.

Answers: "What requires operator intervention, from one place?"

11 active approval systems. 6 persistence models. This runtime unifies them
into a single pending queue with deterministic urgency scoring.

Approvals are owned by the Top HUD (not the Right Rail).
The Right Rail only explains. This runtime is the backend for both.

Campaign 4.2. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ApprovalSourceType(str, Enum):
    GOVERNED_WORK = "governed_work"
    EXECUTION_INTERCEPT = "execution_intercept"
    SANDBOX_GATE = "sandbox_gate"
    STRATEGIC_RECOMMENDATION = "strategic_recommendation"
    KNOWLEDGE_PROMOTION = "knowledge_promotion"
    MEMORY_PROMOTION = "memory_promotion"
    TEMPLATE = "template"
    OVERNIGHT = "overnight"
    AUTOMATION = "automation"
    RECONCILIATION = "reconciliation"
    # Wave 1: objective-plan acceptance decisions (HUD-only; decision_ref ids)
    OBJECTIVE_PLAN = "objective_plan"


@dataclass
class UnifiedApproval:
    approval_id: str = ""
    source_type: ApprovalSourceType = ApprovalSourceType.GOVERNED_WORK
    title: str = ""
    description: str = ""
    risk_class: str = "low"
    waiting_since: float = 0.0
    work_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    urgency_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.approval_id:
            self.approval_id = f"uappr-{uuid4().hex[:8]}"
        if self.waiting_since == 0.0:
            self.waiting_since = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "source_type": self.source_type.value,
            "title": self.title,
            "description": self.description,
            "risk_class": self.risk_class,
            "waiting_since": self.waiting_since,
            "work_id": self.work_id,
            "context": self.context,
            "urgency_score": self.urgency_score,
        }


@dataclass
class ApprovalAction:
    approval_id: str = ""
    source_type: ApprovalSourceType = ApprovalSourceType.GOVERNED_WORK
    action: str = ""
    decided_by: str = "operator"
    reason: str = ""
    routed_to: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "source_type": self.source_type.value,
            "action": self.action,
            "decided_by": self.decided_by,
            "reason": self.reason,
            "routed_to": self.routed_to,
            "timestamp": self.timestamp,
        }


@dataclass
class UnifiedApprovalSnapshot:
    total_pending: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    by_risk: dict[str, int] = field(default_factory=dict)
    oldest_waiting_seconds: float = 0.0
    recent_decisions: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_pending": self.total_pending,
            "by_source": self.by_source,
            "by_risk": self.by_risk,
            "oldest_waiting_seconds": self.oldest_waiting_seconds,
            "recent_decisions": self.recent_decisions,
            "generated_at": self.generated_at,
        }


# ── Urgency Scoring ──────────────────────────────────────────────────────

RISK_WEIGHTS: dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}


def _compute_urgency(risk_class: str, waiting_since: float) -> float:
    weight = RISK_WEIGHTS.get(risk_class, 1.0)
    age_minutes = max(0.0, (time.time() - waiting_since) / 60.0)
    return round(weight * (age_minutes / 60.0), 4)


# ── Helpers ───────────────────────────────────────────────────────────────


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("UnifiedApproval: %s.%s() failed: %s", type(obj).__name__, method, exc)
        return None


def _extract_id(item: Any) -> str:
    for attr in (
        "work_id",
        "packet_id",
        "request_id",
        "candidate_id",
        "item_id",
        "proposal_id",
        "rec_id",
        "id",
    ):
        val = getattr(item, attr, None)
        if val and isinstance(val, str):
            return val
    if isinstance(item, dict):
        for key in (
            "work_id",
            "packet_id",
            "request_id",
            "candidate_id",
            "item_id",
            "proposal_id",
            "rec_id",
            "id",
        ):
            val = item.get(key, "")
            if val:
                return str(val)
    return str(item)[:32]


def _extract_title(item: Any) -> str:
    for attr in ("title", "name", "description", "text", "label"):
        val = getattr(item, attr, None)
        if val and isinstance(val, str):
            return val[:120]
    if isinstance(item, dict):
        for key in ("title", "name", "description", "text", "label"):
            val = item.get(key, "")
            if val:
                return str(val)[:120]
    return str(type(item).__name__)


def _extract_risk(item: Any) -> str:
    for attr in ("risk_class", "risk_level", "risk", "severity"):
        val = getattr(item, attr, None)
        if val and isinstance(val, str):
            return val.lower()
    if isinstance(item, dict):
        for key in ("risk_class", "risk_level", "risk", "severity"):
            val = item.get(key, "")
            if val:
                return str(val).lower()
    return "low"


def _extract_waiting_since(item: Any) -> float:
    for attr in ("created_at", "submitted_at", "waiting_since", "timestamp"):
        val = getattr(item, attr, None)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    if isinstance(item, dict):
        for key in ("created_at", "submitted_at", "waiting_since", "timestamp"):
            val = item.get(key, 0)
            if isinstance(val, (int, float)) and val > 0:
                return float(val)
    return time.time()


def _item_to_unified(
    item: Any,
    source_type: ApprovalSourceType,
) -> UnifiedApproval:
    work_id = _extract_id(item)
    title = _extract_title(item)
    risk = _extract_risk(item)
    waiting = _extract_waiting_since(item)
    ctx = (
        item.to_dict()
        if hasattr(item, "to_dict")
        else (item if isinstance(item, dict) else {"raw": str(item)[:200]})
    )
    return UnifiedApproval(
        source_type=source_type,
        title=title,
        description=f"Pending {source_type.value} approval",
        risk_class=risk,
        waiting_since=waiting,
        work_id=work_id,
        context=ctx,
        urgency_score=_compute_urgency(risk, waiting),
    )


# ── Runtime ───────────────────────────────────────────────────────────────


class UnifiedApprovalRuntime:
    """Unified approval queue composing 10 source systems."""

    def __init__(
        self,
        governed_work: Any | None = None,
        approval_intercept: Any | None = None,
        approval_gate: Any | None = None,
        strategic_gap: Any | None = None,
        compounding: Any | None = None,
        template_registry: Any | None = None,
        memory_promotion: Any | None = None,
        overnight_queue: Any | None = None,
        automation_pipeline: Any | None = None,
        reconciliation: Any | None = None,
        objective_plan: Any | None = None,
    ) -> None:
        self._governed = governed_work
        self._intercept = approval_intercept
        self._gate = approval_gate
        self._strategic = strategic_gap
        self._compounding = compounding
        self._templates = template_registry
        self._memory = memory_promotion
        self._overnight = overnight_queue
        self._automation = automation_pipeline
        self._reconciliation = reconciliation
        if objective_plan is None:
            # Wave 1 default: the objective-plan decision source composes in
            # automatically so plan-acceptance decisions always reach the HUD.
            try:
                from substrate.execution.planning.decisions import (
                    ObjectivePlanDecisionSource,
                )

                objective_plan = ObjectivePlanDecisionSource()
            except Exception as exc:
                logger.debug("objective_plan decision source unavailable: %s", exc)
        self._objective_plan = objective_plan
        self._decisions: list[ApprovalAction] = []

    # ── Query ─────────────────────────────────────────────────────────

    def pending(self, source_type: str = "") -> list[UnifiedApproval]:
        all_pending: list[UnifiedApproval] = []

        collectors: list[tuple[ApprovalSourceType, Any, str, tuple[Any, ...]]] = [
            (ApprovalSourceType.GOVERNED_WORK, self._governed, "blocked", ()),
            (ApprovalSourceType.EXECUTION_INTERCEPT, self._intercept, "pending", ()),
            (ApprovalSourceType.SANDBOX_GATE, self._gate, "pending_packets", ()),
            (
                ApprovalSourceType.STRATEGIC_RECOMMENDATION,
                self._strategic,
                "get_top_recommendations",
                (),
            ),
            (ApprovalSourceType.TEMPLATE, self._templates, "pending_approvals", ()),
            (ApprovalSourceType.MEMORY_PROMOTION, self._memory, "pending_approvals", ()),
            (ApprovalSourceType.OVERNIGHT, self._overnight, "get_pending_approval", ()),
            (ApprovalSourceType.AUTOMATION, self._automation, "pending_proposals", ()),
        ]

        for src_type, obj, method, args in collectors:
            if source_type and source_type != src_type.value:
                continue
            result = _safe_call(obj, method, *args)
            if isinstance(result, list):
                for item in result:
                    all_pending.append(_item_to_unified(item, src_type))

        # Compounding — uses PromotionStatus enum
        if not source_type or source_type == ApprovalSourceType.KNOWLEDGE_PROMOTION.value:
            compounding_pending = self._get_compounding_pending()
            all_pending.extend(compounding_pending)

        # Reconciliation — no simple pending() method, skip for now unless proposals exist
        if not source_type or source_type == ApprovalSourceType.RECONCILIATION.value:
            recon_pending = self._get_reconciliation_pending()
            all_pending.extend(recon_pending)

        # Objective plans — rows arrive as ready UnifiedApprovals with STABLE
        # decision_ref ids (never minted per poll).
        if not source_type or source_type == ApprovalSourceType.OBJECTIVE_PLAN.value:
            result = _safe_call(self._objective_plan, "pending_decisions")
            if isinstance(result, list):
                all_pending.extend(result)

        # Recompute urgency scores with current time
        for appr in all_pending:
            appr.urgency_score = _compute_urgency(appr.risk_class, appr.waiting_since)

        return all_pending

    def _get_compounding_pending(self) -> list[UnifiedApproval]:
        if self._compounding is None:
            return []
        try:
            # PromotionStatus enum — must pass enum, not string
            from substrate.organism.compounding_engine import PromotionStatus

            candidates = self._compounding.list_candidates(
                status=PromotionStatus.PROPOSED,
            )
            if isinstance(candidates, list):
                return [
                    _item_to_unified(c, ApprovalSourceType.KNOWLEDGE_PROMOTION) for c in candidates
                ]
        except ImportError:
            # Fallback if PromotionStatus not importable
            logger.debug("UnifiedApproval: PromotionStatus import failed")
        except Exception as exc:
            logger.debug("UnifiedApproval: compounding.list_candidates failed: %s", exc)
        return []

    def _get_reconciliation_pending(self) -> list[UnifiedApproval]:
        if self._reconciliation is None:
            return []
        # ReconciliationEngine doesn't have a global pending — it's session-based
        # We look for any session with pending proposals
        try:
            sessions = getattr(self._reconciliation, "_sessions", {})
            results: list[UnifiedApproval] = []
            for sid, sess in sessions.items():
                proposals = getattr(sess, "proposals", [])
                if isinstance(proposals, list):
                    for p in proposals:
                        status = (
                            p.get("status", "") if isinstance(p, dict) else getattr(p, "status", "")
                        )
                        if status in ("pending", "proposed", ""):
                            results.append(
                                _item_to_unified(
                                    p,
                                    ApprovalSourceType.RECONCILIATION,
                                )
                            )
            return results
        except Exception as exc:
            logger.debug("UnifiedApproval: reconciliation pending failed: %s", exc)
            return []

    def by_urgency(self, limit: int = 10) -> list[UnifiedApproval]:
        items = self.pending()
        items.sort(key=lambda a: a.urgency_score, reverse=True)
        return items[:limit]

    # ── Act ───────────────────────────────────────────────────────────

    def approve(
        self,
        approval_id: str,
        source_type: str,
        decided_by: str = "operator",
    ) -> ApprovalAction:
        try:
            src = ApprovalSourceType(source_type)
        except ValueError:
            return ApprovalAction(
                approval_id=approval_id,
                action="error",
                reason=f"Unknown source_type: {source_type}",
            )

        # Find the approval to get the work_id
        pending_items = self.pending(source_type=source_type)
        target = None
        for item in pending_items:
            if item.approval_id == approval_id or item.work_id == approval_id:
                target = item
                break

        work_id = target.work_id if target else approval_id
        success = self._route_approve(src, work_id, decided_by)

        action = ApprovalAction(
            approval_id=approval_id,
            source_type=src,
            action="approved" if success else "error",
            decided_by=decided_by,
            routed_to=src.value,
            reason="" if success else "Routing failed",
        )
        self._decisions.append(action)
        return action

    def reject(
        self,
        approval_id: str,
        source_type: str,
        reason: str = "",
        decided_by: str = "operator",
    ) -> ApprovalAction:
        try:
            src = ApprovalSourceType(source_type)
        except ValueError:
            return ApprovalAction(
                approval_id=approval_id,
                action="error",
                reason=f"Unknown source_type: {source_type}",
            )

        pending_items = self.pending(source_type=source_type)
        target = None
        for item in pending_items:
            if item.approval_id == approval_id or item.work_id == approval_id:
                target = item
                break

        work_id = target.work_id if target else approval_id
        success = self._route_reject(src, work_id, reason, decided_by)

        action = ApprovalAction(
            approval_id=approval_id,
            source_type=src,
            action="rejected" if success else "error",
            decided_by=decided_by,
            reason=reason,
            routed_to=src.value,
        )
        self._decisions.append(action)
        return action

    def _route_approve(self, src: ApprovalSourceType, work_id: str, decided_by: str) -> bool:
        routes: dict[ApprovalSourceType, tuple[Any, str, dict[str, Any]]] = {
            ApprovalSourceType.GOVERNED_WORK: (
                self._governed,
                "approve_work",
                {"work_id": work_id},
            ),
            ApprovalSourceType.EXECUTION_INTERCEPT: (
                self._intercept,
                "approve",
                {"approval_id": work_id},
            ),
            ApprovalSourceType.SANDBOX_GATE: (
                self._gate,
                "approve",
                {"packet_id": work_id, "decided_by": decided_by},
            ),
            ApprovalSourceType.STRATEGIC_RECOMMENDATION: (
                self._strategic,
                "approve_recommendation",
                {"recommendation_id": work_id, "reason": "Operator approved"},
            ),
            ApprovalSourceType.KNOWLEDGE_PROMOTION: (
                self._compounding,
                "approve",
                {"candidate_id": work_id},
            ),
            ApprovalSourceType.TEMPLATE: (self._templates, "approve", {"template_id": work_id}),
            ApprovalSourceType.MEMORY_PROMOTION: (
                self._memory,
                "promote",
                {"candidate_id": work_id, "decided_by": decided_by},
            ),
            ApprovalSourceType.OVERNIGHT: (self._overnight, "approve", {"item_id": work_id}),
            ApprovalSourceType.AUTOMATION: (
                self._automation,
                "approve",
                {"proposal_id": work_id, "decided_by": decided_by},
            ),
            ApprovalSourceType.RECONCILIATION: (
                self._reconciliation,
                "approve_proposal",
                {"session_id": "", "proposal_id": work_id},
            ),
            ApprovalSourceType.OBJECTIVE_PLAN: (
                self._objective_plan,
                "approve",
                {"plan_record_id": work_id, "decided_by": decided_by},
            ),
        }
        route = routes.get(src)
        if not route:
            return False
        obj, method, kwargs = route
        result = _safe_call(obj, method, **kwargs)
        return result is not None and result is not False

    def _route_reject(
        self, src: ApprovalSourceType, work_id: str, reason: str, decided_by: str
    ) -> bool:
        routes: dict[ApprovalSourceType, tuple[Any, str, dict[str, Any]]] = {
            ApprovalSourceType.GOVERNED_WORK: (
                self._governed,
                "reject_work",
                {"work_id": work_id, "reason": reason},
            ),
            ApprovalSourceType.EXECUTION_INTERCEPT: (
                self._intercept,
                "reject",
                {"approval_id": work_id, "reason": reason},
            ),
            ApprovalSourceType.SANDBOX_GATE: (
                self._gate,
                "reject",
                {"packet_id": work_id, "reason": reason, "decided_by": decided_by},
            ),
            ApprovalSourceType.STRATEGIC_RECOMMENDATION: (
                self._strategic,
                "reject_recommendation",
                {"recommendation_id": work_id, "reason": reason},
            ),
            ApprovalSourceType.KNOWLEDGE_PROMOTION: (
                self._compounding,
                "reject",
                {"candidate_id": work_id, "reason": reason},
            ),
            ApprovalSourceType.TEMPLATE: (self._templates, "reject", {"template_id": work_id}),
            ApprovalSourceType.MEMORY_PROMOTION: (
                self._memory,
                "reject",
                {"candidate_id": work_id, "reason": reason, "decided_by": decided_by},
            ),
            ApprovalSourceType.OVERNIGHT: (self._overnight, "reject", {"item_id": work_id}),
            ApprovalSourceType.AUTOMATION: (self._automation, "reject", {"proposal_id": work_id}),
            ApprovalSourceType.RECONCILIATION: (
                self._reconciliation,
                "reject_proposal",
                {"session_id": "", "proposal_id": work_id},
            ),
            ApprovalSourceType.OBJECTIVE_PLAN: (
                self._objective_plan,
                "reject",
                {"plan_record_id": work_id, "reason": reason, "decided_by": decided_by},
            ),
        }
        route = routes.get(src)
        if not route:
            return False
        obj, method, kwargs = route
        result = _safe_call(obj, method, **kwargs)
        return result is not None and result is not False

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> UnifiedApprovalSnapshot:
        items = self.pending()
        by_source: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        oldest = 0.0
        now = time.time()

        for item in items:
            by_source[item.source_type.value] = by_source.get(item.source_type.value, 0) + 1
            by_risk[item.risk_class] = by_risk.get(item.risk_class, 0) + 1
            age = now - item.waiting_since
            if age > oldest:
                oldest = age

        recent = [d.to_dict() for d in self._decisions[-10:]]

        return UnifiedApprovalSnapshot(
            total_pending=len(items),
            by_source=by_source,
            by_risk=by_risk,
            oldest_waiting_seconds=round(oldest, 1),
            recent_decisions=recent,
            generated_at=now,
        )

    def recent_decisions(self, limit: int = 20) -> list[ApprovalAction]:
        return list(reversed(self._decisions[-limit:]))
