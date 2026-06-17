"""Cockpit routes for Gate 10 — Projection Consumption Layer.

Read-only audit and registration endpoints for projection drift detection.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable

from fastapi import APIRouter, Depends

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

projection_router = APIRouter(prefix="/projections", tags=["projections"])

_require_operator: Callable[..., Any] | None = None


def configure(require_operator_dep: Callable[..., Any] | None = None) -> None:
    global _require_operator
    _require_operator = require_operator_dep


def _get_dep() -> list[Any]:
    return [Depends(_require_operator)] if _require_operator else []


def _port() -> "ProjectionPort":
    from substrate.sockets.projection_port import ProjectionPort

    return ProjectionPort()


@projection_router.get("/")
async def list_projections() -> dict[str, Any]:
    return {"registrations": [r.to_dict() for r in _port().list_registrations()]}


@projection_router.get("/summary")
async def projection_summary() -> dict[str, Any]:
    return _port().summary()


@projection_router.get("/audit")
async def audit_all_projections() -> dict[str, Any]:
    return _port().audit_all()


@projection_router.get("/audit/{projection_name}")
async def audit_projection(projection_name: str) -> dict[str, Any]:
    return _port().audit_projection(projection_name)


@projection_router.get("/{projection_id}")
async def get_projection(projection_id: str) -> dict[str, Any]:
    port = _port()
    reg = port.get(projection_id)
    if reg is None:
        return {"error": "not found"}
    return reg.to_dict()


@projection_router.post("/register")
async def register_projection(body: dict[str, Any]) -> dict[str, Any]:
    from substrate.sockets.projection_port import ProjectionRegistration

    reg = ProjectionRegistration(
        name=body.get("name", ""),
        capabilities_consumed=body.get("capabilities_consumed", []),
        routes_mounted=body.get("routes_mounted", []),
        substrate_imports=body.get("substrate_imports", []),
    )
    _port().register(reg)
    return {"registered": True, "projection_id": reg.projection_id}
