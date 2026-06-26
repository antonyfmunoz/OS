"""Meta IDE critical path routes — planning, work packets, proof packages, trust.

These endpoints expose the engineering planning pipeline and trust scoring
through the cockpit API. They wire existing substrate modules
(engineering_planner, engineering_work_generator, review_package_builder,
trust_score) into API routes.

All routes are mounted under /api/umh/ via include_router in cockpit.py.
UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

meta_ide_critical_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    require_operator_dep: Any,
) -> None:
    global _get_organism, _configured, meta_ide_critical_router

    _get_organism = get_organism_fn
    _configured = True

    meta_ide_critical_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Planning ─────────────────────────────────────────────────────────

    r.add_api_route("/compose", _compose, methods=["POST"], dependencies=auth)
    r.add_api_route("/plans", _list_plans, methods=["GET"])
    r.add_api_route("/plans/{plan_id}", _get_plan, methods=["GET"])
    r.add_api_route(
        "/plans/{plan_id}/approve", _approve_plan, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/plans/{plan_id}/reject", _reject_plan, methods=["POST"], dependencies=auth
    )

    # ── Work Packets ─────────────────────────────────────────────────────

    r.add_api_route(
        "/execute-plan", _execute_plan, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/execute-plan/{plan_id}/pending",
        _pending_steps,
        methods=["GET"],
    )

    # ── Proof Packages ───────────────────────────────────────────────────

    r.add_api_route("/deliverables", _list_deliverables, methods=["GET"])

    # ── Trust Scores ─────────────────────────────────────────────────────

    r.add_api_route("/trust/scores", _trust_scores, methods=["GET"])
    r.add_api_route("/trust/scores/{work_id}", _trust_score_detail, methods=["GET"])

    return r


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_planner() -> Any:
    try:
        from substrate.meta_ide.shared_planner import get_shared_planner

        return get_shared_planner()
    except Exception as exc:
        logger.debug("failed to get shared planner: %s", exc)
        return None


def _get_trust_engine() -> Any:
    organism = _get_organism()
    if organism is None:
        return None
    engine = getattr(organism, "_trust_engine", None)
    if engine is None:
        try:
            from substrate.organism.trust_score import TrustScoreEngine

            engine = TrustScoreEngine()
            organism._trust_engine = engine
        except Exception as exc:
            logger.debug("failed to create trust engine: %s", exc)
    return engine


# ── Planning endpoints ───────────────────────────────────────────────────


def _compose(payload: dict) -> dict[str, Any]:
    """Create an engineering plan from natural language intent."""
    planner = _get_planner()
    if planner is None:
        return {"error": "engineering planner not available"}

    raw_input = payload.get("input", payload.get("content", ""))
    if not raw_input:
        return {"error": "input required"}

    try:
        plan = planner.create_plan(
            raw_input=raw_input,
            desired_end_state=payload.get("desired_end_state", ""),
            constraints=payload.get("constraints"),
        )
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "intent": {
                "type": plan.intent.intent_type,
                "goal": plan.intent.goal,
                "scope": plan.intent.scope,
                "risk": plan.intent.estimated_risk,
            },
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "task_type": t.task_type,
                    "risk": t.risk,
                    "status": t.status,
                }
                for t in plan.tasks
            ],
            "estimated_risk": plan.estimated_total_risk,
        }
    except Exception as exc:
        logger.exception("compose failed: %s", exc)
        return {"error": str(exc)}


def _list_plans() -> list[dict[str, Any]]:
    """List all in-memory plans."""
    planner = _get_planner()
    if planner is None:
        return []
    try:
        return [
            {
                "plan_id": p.plan_id,
                "status": p.status,
                "goal": p.intent.goal,
                "task_count": len(p.tasks),
                "risk": p.estimated_total_risk,
                "created_at": p.created_at,
            }
            for p in planner.list_plans()
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


def _get_plan(plan_id: str) -> dict[str, Any]:
    """Get full plan detail."""
    planner = _get_planner()
    if planner is None:
        return {"error": "planner not available"}
    plan = planner.get_plan(plan_id)
    if plan is None:
        return {"error": f"plan {plan_id} not found"}
    try:
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "intent": {
                "type": plan.intent.intent_type,
                "goal": plan.intent.goal,
                "scope": plan.intent.scope,
                "constraints": plan.intent.constraints,
                "success_criteria": plan.intent.success_criteria,
                "risk": plan.intent.estimated_risk,
            },
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "task_type": t.task_type,
                    "risk": t.risk,
                    "status": t.status,
                    "validation": t.validation,
                }
                for t in plan.tasks
            ],
            "dependency_graph": plan.dependency_graph,
            "estimated_risk": plan.estimated_total_risk,
            "roadmap_context": plan.roadmap_context,
            "workspace_health": plan.workspace_health,
            "engineering_risks": plan.engineering_risks,
            "created_at": plan.created_at,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _approve_plan(plan_id: str) -> dict[str, Any]:
    """Approve a plan for execution."""
    planner = _get_planner()
    if planner is None:
        return {"error": "planner not available"}
    ok = planner.update_plan_status(plan_id, "approved")
    if not ok:
        return {"error": f"plan {plan_id} not found"}
    return {"plan_id": plan_id, "status": "approved"}


def _reject_plan(plan_id: str) -> dict[str, Any]:
    """Reject a plan."""
    planner = _get_planner()
    if planner is None:
        return {"error": "planner not available"}
    ok = planner.update_plan_status(plan_id, "rejected")
    if not ok:
        return {"error": f"plan {plan_id} not found"}
    return {"plan_id": plan_id, "status": "rejected"}


# ── Work Packet endpoints ────────────────────────────────────────────────


def _execute_plan(payload: dict) -> dict[str, Any]:
    """Generate work packets from an approved plan."""
    plan_id = payload.get("plan_id", "")
    if not plan_id:
        return {"error": "plan_id required"}

    planner = _get_planner()
    if planner is None:
        return {"error": "planner not available"}

    plan = planner.get_plan(plan_id)
    if plan is None:
        return {"error": f"plan {plan_id} not found"}

    if plan.status != "approved":
        return {"error": f"plan must be approved first (current: {plan.status})"}

    try:
        from substrate.meta_ide.engineering_work_generator import (
            EngineeringWorkGenerator,
        )

        generator = EngineeringWorkGenerator()
        receipt = generator.generate_packets(plan)
        planner.update_plan_status(plan_id, "executing")
        return {
            "plan_id": plan_id,
            "receipt_id": receipt.receipt_id,
            "packets_generated": len(receipt.packets),
            "packets": [
                {
                    "packet_id": p.packet_id,
                    "title": p.title,
                    "risk_level": p.risk_level,
                    "status": p.status,
                }
                for p in receipt.packets
            ],
        }
    except Exception as exc:
        logger.exception("execute-plan failed: %s", exc)
        return {"error": str(exc)}


def _pending_steps(plan_id: str) -> dict[str, Any]:
    """List pending approval steps for a plan."""
    planner = _get_planner()
    if planner is None:
        return {"error": "planner not available"}
    plan = planner.get_plan(plan_id)
    if plan is None:
        return {"error": f"plan {plan_id} not found"}
    pending = [
        {"task_id": t.task_id, "title": t.title, "status": t.status}
        for t in plan.tasks
        if t.status in ("pending", "awaiting_approval")
    ]
    return {"plan_id": plan_id, "pending": pending}


# ── Proof Package endpoints ──────────────────────────────────────────────


def _list_deliverables() -> list[dict[str, Any]]:
    """List available proof packages / deliverables."""
    organism = _get_organism()
    if organism is None:
        return []
    try:
        store = getattr(organism, "store", None)
        if store is None:
            return []
        reports = store.list_reports(limit=50)
        return [
            {
                "id": r.get("id", ""),
                "title": r.get("title", "Deliverable"),
                "summary": (r.get("summary", "") or "")[:300],
                "status": r.get("status", "complete"),
                "created_at": r.get("created_at", ""),
            }
            for r in reports
        ]
    except Exception as exc:
        logger.debug("deliverables fetch failed: %s", exc)
        return []


# ── Trust Score endpoints ────────────────────────────────────────────────


def _trust_scores() -> dict[str, Any]:
    """Trust score summary across all tracked work items."""
    engine = _get_trust_engine()
    if engine is None:
        return {"error": "trust engine not available", "total": 0, "by_level": {}}
    try:
        return engine.summary()
    except Exception as exc:
        return {"error": str(exc)}


def _trust_score_detail(work_id: str) -> dict[str, Any]:
    """Trust score for a specific work item."""
    engine = _get_trust_engine()
    if engine is None:
        return {"error": "trust engine not available"}
    score = engine.get_score(work_id)
    if score is None:
        return {"error": f"no trust score for {work_id}"}
    try:
        return score.to_dict()
    except Exception as exc:
        return {"error": str(exc)}
