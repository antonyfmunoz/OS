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


def _get_executor() -> Any:
    """Try to construct an executor. Returns None if unavailable."""
    try:
        from substrate.organism.executor_runtime import (
            AgentExecutor,
        )

        return AgentExecutor()
    except Exception:
        pass
    try:
        from substrate.organism.executor_runtime import (
            WorkstationExecutor,
        )

        return WorkstationExecutor()
    except Exception:
        pass
    return None


def _get_coordinator() -> Any:
    global _coordinator_instance
    if _coordinator_instance is not None:
        return _coordinator_instance
    try:
        from substrate.meta_ide.engineering_session_coordinator import (
            EngineeringSessionCoordinator,
        )

        executor = _get_executor()
        _coordinator_instance = EngineeringSessionCoordinator(executor=executor)
        if executor is not None:
            logger.info("engineering coordinator wired with executor: %s", type(executor).__name__)
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


_ALLOWED_WORKSPACE_TARGETS = frozenset(
    {
        "OS",
        "CreatorOS",
        "EntrepreneurOS",
        "LyfeOS",
        "cockpit",
        "saas",
    }
)

_MAX_WORKSPACE_TARGETS = 10


def _validate_workspace_targets(targets: Any) -> list[str]:
    """Validate workspace_targets against allowlist."""
    if not isinstance(targets, list):
        raise HTTPException(400, "workspace_targets must be a list")
    if len(targets) > _MAX_WORKSPACE_TARGETS:
        raise HTTPException(400, f"workspace_targets exceeds maximum of {_MAX_WORKSPACE_TARGETS}")
    validated: list[str] = []
    for t in targets:
        if not isinstance(t, str):
            raise HTTPException(400, "workspace_targets entries must be strings")
        if t not in _ALLOWED_WORKSPACE_TARGETS:
            raise HTTPException(400, f"unknown workspace target: {t}")
        validated.append(t)
    return validated


def _get_shared_planner() -> Any:
    from substrate.meta_ide.shared_planner import get_shared_planner

    return get_shared_planner()


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/engineering/sessions", dependencies=[Depends(require_operator_dep)])
    def list_sessions() -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            return {"sessions": [], "error": "coordinator unavailable"}
        sessions = coordinator.list_sessions()
        return {
            "sessions": [s.to_dict() for s in sessions],
            "total": len(sessions),
        }

    @router.get("/engineering/sessions/{session_id}", dependencies=[Depends(require_operator_dep)])
    def get_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        session = coordinator.get_session(session_id)
        if session is None:
            raise HTTPException(404, f"session {session_id} not found")
        return session.to_dict()

    @router.post("/engineering/sessions")
    def create_session(
        body: dict[str, Any],
        principal: str = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")

        plan_id = body.get("plan_id", "")
        if not plan_id:
            raise HTTPException(400, "plan_id required")

        workspace_targets = _validate_workspace_targets(body.get("workspace_targets", []))

        planner = _get_shared_planner()
        if planner is not None:
            plans = getattr(planner, "_plans", {})
            if plan_id in plans:
                coordinator.register_plan(plans[plan_id])

        try:
            session = coordinator.create_session(
                plan_id=plan_id,
                workspace_targets=workspace_targets,
                operator_id=principal,
            )
            return session.to_dict()
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @router.post(
        "/engineering/sessions/{session_id}/execute", dependencies=[Depends(require_operator_dep)]
    )
    def execute_session(session_id: str) -> dict[str, Any]:
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

    @router.post(
        "/engineering/sessions/{session_id}/pause", dependencies=[Depends(require_operator_dep)]
    )
    def pause_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        ok = coordinator.pause_session(session_id)
        if not ok:
            raise HTTPException(400, "cannot pause session")
        session = coordinator.get_session(session_id)
        return session.to_dict() if session else {"status": "paused"}

    @router.post(
        "/engineering/sessions/{session_id}/cancel", dependencies=[Depends(require_operator_dep)]
    )
    def cancel_session(session_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        ok = coordinator.cancel_session(session_id)
        if not ok:
            raise HTTPException(400, "cannot cancel session")
        session = coordinator.get_session(session_id)
        return session.to_dict() if session else {"status": "cancelled"}

    @router.get("/engineering/reviews", dependencies=[Depends(require_operator_dep)])
    async def list_reviews() -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            return {"reviews": [], "error": "coordinator unavailable"}
        packages = coordinator.list_proof_packages()
        return {
            "reviews": [p.to_dict() for p in packages],
            "total": len(packages),
        }

    @router.get("/engineering/reviews/{proof_id}", dependencies=[Depends(require_operator_dep)])
    def get_review(proof_id: str) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        package = coordinator.get_proof_package(proof_id)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")
        return package.to_dict()

    @router.post("/engineering/reviews/{proof_id}/approve")
    def approve_review(
        proof_id: str,
        principal: str = Depends(require_operator_dep),
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        package = coordinator.approve_review(proof_id, reviewed_by=principal)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")

        integration = coordinator.integrate_session(package.session_id)
        result = package.to_dict()
        result["integration"] = integration
        return result

    @router.post("/engineering/reviews/{proof_id}/reject")
    def reject_review(
        proof_id: str,
        principal: str = Depends(require_operator_dep),
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        coordinator = _get_coordinator()
        if coordinator is None:
            raise HTTPException(503, "coordinator unavailable")
        reason = (body or {}).get("reason", "")
        package = coordinator.reject_review(proof_id, reason=reason, reviewed_by=principal)
        if package is None:
            raise HTTPException(404, f"review {proof_id} not found")
        return package.to_dict()

    return router
