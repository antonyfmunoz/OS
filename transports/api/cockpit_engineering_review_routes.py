"""Cockpit engineering review routes — execution sessions and proof review.

Mounted under /api/umh/ via include_router in cockpit.py.
Manages engineering execution sessions, dispatches to existing executors,
and surfaces proof packages for operator review. No auto-merge/push/deploy.

Phase 23. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

engineering_review_router: APIRouter = APIRouter()

_configured: bool = False

_coordinator_instance: Any = None


def configure(require_operator_dep: Any) -> None:
    global _configured, engineering_review_router
    _configured = True
    engineering_review_router = _build_router(require_operator_dep)


def _get_coordinator() -> Any:
    global _coordinator_instance
    if _coordinator_instance is not None:
        return _coordinator_instance
    try:
        from substrate.meta_ide.engineering_session_coordinator import (
            EngineeringSessionCoordinator,
        )

        _coordinator_instance = EngineeringSessionCoordinator()
        return _coordinator_instance
    except Exception as exc:
        logger.debug("engineering review routes: failed to create coordinator: %s", exc)
        return None


def _get_builder() -> Any:
    try:
        from substrate.meta_ide.review_package_builder import (
            ReviewPackageBuilder,
        )

        return ReviewPackageBuilder()
    except Exception as exc:
        logger.debug("engineering review routes: failed to create builder: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter()
    auth = [Depends(require_operator_dep)]

    @router.get("/engineering/sessions", dependencies=auth)
    async def list_sessions() -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            return {"sessions": [], "error": "coordinator unavailable"}
        sessions = coordinator.list_sessions()
        return {
            "sessions": [s.to_dict() for s in sessions],
            "total": len(sessions),
        }

    @router.get("/engineering/sessions/{session_id}", dependencies=auth)
    async def get_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        session = coordinator.get_session(session_id)
        if session is None:
            raise HTTPException(404, f"session {session_id} not found")
        return session.to_dict()

    @router.post("/engineering/sessions", dependencies=auth)
    async def create_session(body: dict[str, Any]) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")

        plan_id = body.get("plan_id", "")
        if not plan_id:
            raise HTTPException(400, "plan_id required")

        workspace_targets = body.get("workspace_targets", [])
        operator_id = body.get("operator_id", "")

        try:
            from substrate.meta_ide.engineering_planner import (
                EngineeringPlanner,
            )

            planner = EngineeringPlanner()
            plans = getattr(planner, "_plans", {})
            if plan_id in plans:
                coordinator.register_plan(plans[plan_id])
        except Exception:
            pass

        try:
            session = coordinator.create_session(
                plan_id=plan_id,
                workspace_targets=workspace_targets,
                operator_id=operator_id,
            )
            return session.to_dict()
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @router.post("/engineering/sessions/{session_id}/execute", dependencies=auth)
    async def execute_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        try:
            session = coordinator.execute_session(session_id)
            builder = _get_builder()
            if builder is not None:
                package = builder.build_package(session)
                coordinator.store_proof_package(package)
                return {
                    "session": session.to_dict(),
                    "proof_package": package.to_dict(),
                }
            return {"session": session.to_dict()}
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @router.post("/engineering/sessions/{session_id}/pause", dependencies=auth)
    async def pause_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        ok = coordinator.pause_session(session_id)
        if not ok:
            raise HTTPException(400, "cannot pause session")
        session = coordinator.get_session(session_id)
        return session.to_dict() if session else {"status": "paused"}

    @router.post("/engineering/sessions/{session_id}/cancel", dependencies=auth)
    async def cancel_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        ok = coordinator.cancel_session(session_id)
        if not ok:
            raise HTTPException(400, "cannot cancel session")
        session = coordinator.get_session(session_id)
        return session.to_dict() if session else {"status": "cancelled"}

    @router.get("/engineering/reviews", dependencies=auth)
    async def list_reviews() -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            return {"reviews": [], "error": "coordinator unavailable"}
        packages = coordinator.list_proof_packages()
        return {
            "reviews": [p.to_dict() for p in packages],
            "total": len(packages),
        }

    @router.get("/engineering/reviews/{proof_id}", dependencies=auth)
    async def get_review(proof_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        package = coordinator.get_proof_package(proof_id)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")
        return package.to_dict()

    @router.post("/engineering/reviews/{proof_id}/approve", dependencies=auth)
    async def approve_review(proof_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        reviewed_by = (body or {}).get("reviewed_by", "")
        package = coordinator.approve_review(proof_id, reviewed_by=reviewed_by)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")
        return package.to_dict()

    @router.post("/engineering/reviews/{proof_id}/reject", dependencies=auth)
    async def reject_review(proof_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        b = body or {}
        reason = b.get("reason", "")
        reviewed_by = b.get("reviewed_by", "")
        package = coordinator.reject_review(proof_id, reason=reason, reviewed_by=reviewed_by)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")
        return package.to_dict()

    return router
