"""Command Center MVP Routes — operator landing surface API.

Exposes CommandCenterMVPRuntime: snapshot, situation, attention,
execution pulse, capability pulse, migration pulse, recommendations,
section.

Campaign 3.2 — Command Center MVP Convergence. UMH transport layer.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

command_center_mvp_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    command_center_mvp_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.workstation.command_center_mvp_runtime import (
            CommandCenterMVPRuntime,
        )

        _get_runtime._instance = CommandCenterMVPRuntime()
    return _get_runtime._instance


def _get_governed_execution() -> Any:
    if not hasattr(_get_governed_execution, "_instance"):
        from substrate.organism.governed_execution_runtime import (
            GovernedExecutionRuntime,
        )

        _get_governed_execution._instance = GovernedExecutionRuntime()
    return _get_governed_execution._instance


def _get_organism_state() -> Any:
    if not hasattr(_get_organism_state, "_instance"):
        from substrate.organism.organism_state_runtime import (
            OrganismStateRuntime,
        )

        _get_organism_state._instance = OrganismStateRuntime()
    return _get_organism_state._instance


def _get_execution_lifecycle() -> Any:
    if not hasattr(_get_execution_lifecycle, "_instance"):
        from substrate.organism.execution_lifecycle_runtime import (
            ExecutionLifecycleRuntime,
        )

        _get_execution_lifecycle._instance = ExecutionLifecycleRuntime()
    return _get_execution_lifecycle._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/command-center-mvp/snapshot", dependencies=auth)
    async def snapshot() -> dict[str, Any]:
        return _get_runtime().snapshot().to_dict()

    @r.get("/command-center-mvp/situation", dependencies=auth)
    async def situation() -> dict[str, Any]:
        return _get_runtime().situation()

    @r.get("/command-center-mvp/attention", dependencies=auth)
    async def attention(limit: int = 10) -> list[dict[str, Any]]:
        return _get_runtime().attention(limit=limit)

    @r.get("/command-center-mvp/execution-pulse", dependencies=auth)
    async def execution_pulse() -> dict[str, Any]:
        return _get_runtime().execution_pulse().to_dict()

    @r.get("/command-center-mvp/capability-pulse", dependencies=auth)
    async def capability_pulse() -> dict[str, Any]:
        return _get_runtime().capability_pulse().to_dict()

    @r.get("/command-center-mvp/migration-pulse", dependencies=auth)
    async def migration_pulse() -> dict[str, Any]:
        return _get_runtime().migration_pulse().to_dict()

    @r.get("/command-center-mvp/recommendations", dependencies=auth)
    async def recommendations(limit: int = 5) -> list[dict[str, Any]]:
        return [r.to_dict() for r in _get_runtime().recommendations(limit=limit)]

    @r.get("/command-center-mvp/section/{section_name}", dependencies=auth)
    async def section(section_name: str) -> dict[str, Any]:
        return _get_runtime().section(section_name)

    # ── C16 — Governed Execution Loop endpoints ─────────────────

    @r.get("/command-center-mvp/governed-execution", dependencies=auth)
    async def governed_execution() -> dict[str, Any]:
        return _get_governed_execution().snapshot().to_dict()

    @r.get("/command-center-mvp/execution-summary", dependencies=auth)
    async def execution_summary() -> dict[str, Any]:
        """Unified execution summary — single canonical read for all execution surfaces."""
        return _get_governed_execution().execution_summary()

    @r.get("/command-center-mvp/organism-state", dependencies=auth)
    async def organism_state() -> dict[str, Any]:
        return _get_organism_state().snapshot().to_dict()

    @r.get("/command-center-mvp/execution-lifecycle", dependencies=auth)
    async def execution_lifecycle() -> dict[str, Any]:
        return _get_execution_lifecycle().snapshot().to_dict()

    return r
