"""Cockpit Operator Migration routes — exit tracking and closure.

Mounted under /api/umh/ via include_router in cockpit.py.
Tracks operator exits from UMH, classifies them, and drives migration.

W5. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

migration_router: APIRouter = APIRouter()

_configured: bool = False
_migration_instance: Any = None


def configure(*, require_operator_dep: Any) -> None:
    global _configured, migration_router
    if _configured:
        return
    _configured = True
    migration_router = _build_router(require_operator_dep)


def _get_migration() -> Any:
    global _migration_instance
    if _migration_instance is not None:
        return _migration_instance
    try:
        from substrate.organism.operator_migration_runtime import OperatorMigrationRuntime

        _migration_instance = OperatorMigrationRuntime()
        return _migration_instance
    except Exception as exc:
        logger.debug("migration routes: failed to create runtime: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.post("/migration/exit")
    async def record_exit(payload: dict) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        description = str(payload.get("description", ""))
        external_tool = str(payload.get("external_tool", ""))
        exit_id = mig.record_exit(description=description, external_tool=external_tool)
        return {"exit_id": exit_id}

    @r.post("/migration/return")
    async def record_return(payload: dict) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        exit_id = str(payload.get("exit_id", ""))
        if not exit_id:
            raise HTTPException(status_code=400, detail="exit_id required")
        ok = mig.record_return(exit_id)
        if not ok:
            raise HTTPException(status_code=404, detail="exit not found")
        return {"status": "returned", "exit_id": exit_id}

    @r.get("/migration/coverage")
    async def coverage_report() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"coverage_pct": 1.0, "total_exits": 0}
        return mig.coverage_report().to_dict()

    @r.get("/migration/priorities")
    async def migration_priorities() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"priorities": []}
        return {"priorities": [p.to_dict() for p in mig.migration_priorities()]}

    @r.get("/migration/status")
    async def migration_status() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"total_exits": 0, "coverage_pct": 1.0}
        return mig.migration_status().to_dict()

    @r.get("/migration/active")
    async def active_migrations() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"migrations": []}
        return {"migrations": [m.to_dict() for m in mig.active_migrations()]}

    @r.post("/migration/propose")
    async def propose_migration(payload: dict) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        pattern = str(payload.get("exit_pattern", ""))
        tool = str(payload.get("external_tool", ""))
        if not pattern:
            raise HTTPException(status_code=400, detail="exit_pattern required")
        m = mig.propose_migration(exit_pattern=pattern, external_tool=tool)
        return m.to_dict()

    @r.post("/migration/complete")
    async def complete_migration(payload: dict) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        migration_id = str(payload.get("migration_id", ""))
        success = bool(payload.get("success", True))
        if not migration_id:
            raise HTTPException(status_code=400, detail="migration_id required")
        ok = mig.complete_migration(migration_id, success=success)
        if not ok:
            raise HTTPException(status_code=404, detail="migration not found")
        return {"status": "completed", "migration_id": migration_id}

    @r.get("/migration/suggest/{pattern}")
    async def suggest_operationalization(pattern: str) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        suggestion = mig.suggest_operationalization(pattern)
        if not suggestion:
            raise HTTPException(status_code=404, detail="no suggestion for pattern")
        return suggestion.to_dict()

    return r
