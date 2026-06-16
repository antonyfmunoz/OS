"""Cockpit routes for the Governed Action Bridge (Phase 26).

Exposes the ActionBridge API: catalog, execute, approve, status, history.
Follows the standard configure() + router pattern.

UMH transport layer.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

action_bridge_router: APIRouter = APIRouter()

_configured = False


class ExecuteActionBody(BaseModel):
    action_id: str = Field(..., min_length=1)
    parameters: dict[str, str] = Field(default_factory=dict)
    source: str = "cockpit"


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    _router = _build_router(require_operator_dep)
    action_bridge_router.include_router(_router)


def _get_bridge() -> Any:
    from substrate.organism.action_bridge import ActionBridge

    if not hasattr(_get_bridge, "_instance"):
        _get_bridge._instance = ActionBridge()
    return _get_bridge._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/actions",
        tags=["actions"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("/catalog")
    async def list_catalog(category: str | None = None) -> dict[str, Any]:
        bridge = _get_bridge()
        actions = bridge.list_available_actions(category=category)
        return {"actions": actions, "count": len(actions)}

    @router.get("/catalog/{action_id}")
    async def get_action(action_id: str) -> dict[str, Any]:
        bridge = _get_bridge()
        from substrate.organism.action_catalog import ActionCatalog

        catalog = bridge._catalog
        action = catalog.resolve_by_id(action_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
        entry = action.to_dict()
        entry["precondition_state"] = bridge.check_preconditions(action, {})
        return entry

    @router.post("/execute")
    async def execute_action(body: ExecuteActionBody) -> dict[str, Any]:
        bridge = _get_bridge()
        from substrate.organism.action_bridge import ActionRequest

        request = ActionRequest(
            action_id=body.action_id,
            parameters=body.parameters,
            source=body.source,
        )
        result = bridge.execute_action(request)
        return result.to_dict()

    @router.post("/{execution_plan_id}/approve")
    async def approve_action(execution_plan_id: str) -> dict[str, Any]:
        bridge = _get_bridge()
        result = bridge.approve_and_dispatch(execution_plan_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No pending action for plan: {execution_plan_id}",
            )
        return result.to_dict()

    @router.get("/status/{request_id}")
    async def action_status(request_id: str) -> dict[str, Any]:
        bridge = _get_bridge()
        result = bridge.get_action_status(request_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"No result for request: {request_id}")
        return result.to_dict()

    @router.get("/history")
    async def action_history(limit: int = 20) -> dict[str, Any]:
        bridge = _get_bridge()
        clamped = max(1, min(limit, 100))
        items = bridge.history(limit=clamped)
        return {"history": items, "count": len(items)}

    return router
