"""Cockpit engineering routes — autonomous planning and packetization.

Mounted under /api/umh/ via include_router in cockpit.py.
Creates engineering plans from intent, supports operator review,
generates governed work packets on approval. No direct execution.

Phase 22. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

engineering_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, engineering_router
    _configured = True
    engineering_router = _build_router(require_operator_dep)


def _get_planner() -> Any:
    from substrate.meta_ide.shared_planner import get_shared_planner

    return get_shared_planner()


def _get_generator() -> Any:
    try:
        from substrate.meta_ide.engineering_work_generator import (
            EngineeringWorkGenerator,
        )

        return EngineeringWorkGenerator()
    except Exception as exc:
        logger.debug("engineering routes: failed to create generator: %s", exc)
        return None


def _get_gap_engine() -> Any:
    try:
        from substrate.meta_ide.roadmap_gap_engine import RoadmapGapEngine

        return RoadmapGapEngine()
    except Exception as exc:
        logger.debug("engineering routes: failed to create gap engine: %s", exc)
        return None


_planners: dict[str, Any] = {}


def _get_or_create_planner() -> Any:
    if "default" not in _planners:
        planner = _get_planner()
        if planner:
            _planners["default"] = planner
    return _planners.get("default")


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter()
    auth = [Depends(require_operator_dep)]

    @router.post("/engineering/plan", dependencies=auth)
    async def create_plan(body: dict[str, Any]) -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        intent = body.get("intent", "")
        if not intent:
            raise HTTPException(status_code=400, detail="intent is required")

        desired_end_state = body.get("desired_end_state", "")
        constraints = body.get("constraints", [])

        plan = planner.create_plan(intent, desired_end_state, constraints)
        return plan.to_dict()

    @router.get("/engineering/plans", dependencies=auth)
    async def list_plans() -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            return {"plans": [], "count": 0}

        plans = planner.list_plans()
        return {
            "plans": [p.to_dict() for p in plans],
            "count": len(plans),
        }

    @router.get("/engineering/plans/{plan_id}", dependencies=auth)
    async def get_plan(plan_id: str) -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        plan = planner.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        return plan.to_dict()

    @router.post("/engineering/plans/{plan_id}/approve", dependencies=auth)
    async def approve_plan(plan_id: str) -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        plan = planner.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        if plan.status not in ("draft", "approved"):
            raise HTTPException(
                status_code=409,
                detail=f"Plan status is '{plan.status}', cannot approve",
            )

        generator = _get_generator()
        if not generator:
            raise HTTPException(status_code=503, detail="Generator unavailable")

        receipt = generator.generate_packets(plan)
        return receipt.to_dict()

    @router.post("/engineering/plans/{plan_id}/dispatch", dependencies=auth)
    async def dispatch_plan(plan_id: str, body: dict[str, Any] = {}) -> dict[str, Any]:
        """Dispatch approved plan's work packets to a connected node for execution.

        Starts dispatch as a background asyncio task and returns 202 immediately.
        The Fly.io→Tailscale tunnel has a 60s proxy timeout — long dispatches
        would get cancelled if awaited in the handler.
        """
        import asyncio

        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        plan = planner.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        node_id = body.get("node_id", "windows-desktop")
        cwd = body.get("cwd", r"C:\dev\dev\LYFEOS")

        from transports.api._mesh_dispatch import (
            _validate_cwd,
            _validate_node_id,
            dispatch_plan_to_node,
        )

        try:
            _validate_node_id(node_id)
            _validate_cwd(cwd)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        async def _run_dispatch() -> None:
            try:
                result = await dispatch_plan_to_node(plan, node_id=node_id, cwd=cwd)
                logger.info("dispatch %s completed: %d dispatched", plan_id, result.get("dispatched", 0))
            except Exception as exc:
                logger.error("dispatch %s background failed: %s", plan_id, exc)

        asyncio.create_task(_run_dispatch())
        return {"ok": True, "status": "dispatching", "plan_id": plan_id, "node_id": node_id}

    @router.post("/engineering/plans/{plan_id}/reject", dependencies=auth)
    async def reject_plan(plan_id: str) -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        plan = planner.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        planner.update_plan_status(plan_id, "rejected")
        return {"plan_id": plan_id, "status": "rejected"}

    @router.get("/engineering/plans/{plan_id}/packets", dependencies=auth)
    async def get_plan_packets(plan_id: str) -> dict[str, Any]:
        planner = _get_or_create_planner()
        if not planner:
            raise HTTPException(status_code=503, detail="Planner unavailable")

        plan = planner.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

        try:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            queue = UniversalWorkQueue()
            packets = [
                p
                for p in queue._packets.values()
                if p.source_id == plan_id and p.source_type == "engineering_plan"
            ]
            return {
                "plan_id": plan_id,
                "packets": [p.to_safe_dict() for p in packets],
                "count": len(packets),
            }
        except Exception:
            return {"plan_id": plan_id, "packets": [], "count": 0}

    @router.get("/engineering/queue", dependencies=auth)
    async def engineering_queue() -> dict[str, Any]:
        try:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            queue = UniversalWorkQueue()
            eng_packets = [
                p for p in queue._packets.values() if p.source_type == "engineering_plan"
            ]
            by_status: dict[str, int] = {}
            for p in eng_packets:
                s = p.status.value if hasattr(p.status, "value") else str(p.status)
                by_status[s] = by_status.get(s, 0) + 1
            return {
                "total_engineering_packets": len(eng_packets),
                "by_status": by_status,
                "packets": [p.to_safe_dict() for p in eng_packets[:50]],
            }
        except Exception:
            return {"total_engineering_packets": 0, "by_status": {}, "packets": []}

    @router.get("/engineering/gaps", dependencies=auth)
    async def roadmap_gaps() -> dict[str, Any]:
        gap_engine = _get_gap_engine()
        if not gap_engine:
            return {"analysis": None, "recommendations": []}

        analysis = gap_engine.analyze_gaps()
        recommendations = gap_engine.recommend_work(max_items=10)
        return {
            "analysis": analysis.to_dict(),
            "recommendations": [r.to_dict() for r in recommendations],
        }

    return router
