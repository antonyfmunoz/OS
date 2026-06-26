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


_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _validate_projection_name(name: str) -> str | None:
    if "/" in name or "\\" in name or ".." in name or not name:
        return "invalid projection name"
    base = os.path.realpath(os.path.join(_REPO_ROOT, "projections"))
    target = os.path.realpath(os.path.join(base, name))
    if not target.startswith(base + os.sep):
        return "invalid projection name"
    return None


@projection_router.get("/", dependencies=_get_dep())
def list_projections() -> dict[str, Any]:
    return {"registrations": [r.to_dict() for r in _port().list_registrations()]}


@projection_router.get("/summary", dependencies=_get_dep())
def projection_summary() -> dict[str, Any]:
    return _port().summary()


@projection_router.get("/audit", dependencies=_get_dep())
def audit_all_projections() -> dict[str, Any]:
    return _port().audit_all()


@projection_router.get("/audit/{projection_name}", dependencies=_get_dep())
def audit_projection(projection_name: str) -> dict[str, Any]:
    err = _validate_projection_name(projection_name)
    if err:
        return {"error": err}
    return _port().audit_projection(projection_name)


@projection_router.get("/{projection_id}", dependencies=_get_dep())
def get_projection(projection_id: str) -> dict[str, Any]:
    port = _port()
    reg = port.get(projection_id)
    if reg is None:
        return {"error": "not found"}
    return reg.to_dict()


@projection_router.post("/register", dependencies=_get_dep())
def register_projection(body: dict[str, Any]) -> dict[str, Any]:
    from substrate.sockets.projection_port import ProjectionRegistration

    reg = ProjectionRegistration(
        name=body.get("name", ""),
        capabilities_consumed=body.get("capabilities_consumed", []),
        routes_mounted=body.get("routes_mounted", []),
        substrate_imports=body.get("substrate_imports", []),
    )
    _port().register(reg)
    return {"registered": True, "projection_id": reg.projection_id}
