"""Cockpit Operator Migration routes — exit tracking and closure.

Mounted under /api/umh/ via include_router in cockpit.py.
Tracks operator exits from UMH, classifies them, and drives migration.

W5. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from transports.api.governed import governed_mutation

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
    def record_exit(payload: dict) -> dict:
        description = str(payload.get("description", ""))
        external_tool = str(payload.get("external_tool", ""))

        def _do_exit():
            mig = _get_migration()
            if mig is None:
                return "migration unavailable", False
            exit_id = mig.record_exit(description=description, external_tool=external_tool)
            return f"exit recorded: {exit_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"record operator exit: {description[:100]}",
            execute_fn=_do_exit,
            source="cockpit",
            metadata={"external_tool": external_tool},
        )
        return resp.to_http_dict()

    @r.post("/migration/return")
    def record_return(payload: dict) -> dict:
        exit_id = str(payload.get("exit_id", ""))
        if not exit_id:
            raise HTTPException(status_code=400, detail="exit_id required")

        def _do_return():
            mig = _get_migration()
            if mig is None:
                return "migration unavailable", False
            ok = mig.record_return(exit_id)
            if not ok:
                return "exit not found", False
            return f"returned: {exit_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"record operator return for exit {exit_id}",
            execute_fn=_do_return,
            source="cockpit",
            metadata={"exit_id": exit_id},
        )
        return resp.to_http_dict()

    @r.get("/migration/coverage")
    def coverage_report() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"coverage_pct": 1.0, "total_exits": 0}
        return mig.coverage_report().to_dict()

    @r.get("/migration/priorities")
    def migration_priorities() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"priorities": []}
        return {"priorities": [p.to_dict() for p in mig.migration_priorities()]}

    @r.get("/migration/status")
    def migration_status() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"total_exits": 0, "coverage_pct": 1.0}
        return mig.migration_status().to_dict()

    @r.get("/migration/active")
    def active_migrations() -> dict:
        mig = _get_migration()
        if mig is None:
            return {"migrations": []}
        return {"migrations": [m.to_dict() for m in mig.active_migrations()]}

    @r.post("/migration/propose")
    def propose_migration(payload: dict) -> dict:
        pattern = str(payload.get("exit_pattern", ""))
        tool = str(payload.get("external_tool", ""))
        if not pattern:
            raise HTTPException(status_code=400, detail="exit_pattern required")

        def _do_propose():
            mig = _get_migration()
            if mig is None:
                return "migration unavailable", False
            m = mig.propose_migration(exit_pattern=pattern, external_tool=tool)
            return f"migration proposed: {m.migration_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"propose migration for pattern: {pattern[:100]}",
            execute_fn=_do_propose,
            source="cockpit",
            metadata={"exit_pattern": pattern, "external_tool": tool},
        )
        return resp.to_http_dict()

    @r.post("/migration/complete")
    def complete_migration(payload: dict) -> dict:
        migration_id = str(payload.get("migration_id", ""))
        success = bool(payload.get("success", True))
        if not migration_id:
            raise HTTPException(status_code=400, detail="migration_id required")

        def _do_complete():
            mig = _get_migration()
            if mig is None:
                return "migration unavailable", False
            ok = mig.complete_migration(migration_id, success=success)
            if not ok:
                return "migration not found", False
            return f"migration completed: {migration_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"complete migration {migration_id} (success={success})",
            execute_fn=_do_complete,
            source="cockpit",
            metadata={"migration_id": migration_id, "success": success},
        )
        return resp.to_http_dict()

    @r.get("/migration/suggest/{pattern}")
    def suggest_operationalization(pattern: str) -> dict:
        mig = _get_migration()
        if mig is None:
            raise HTTPException(status_code=503, detail="migration unavailable")
        suggestion = mig.suggest_operationalization(pattern)
        if not suggestion:
            raise HTTPException(status_code=404, detail="no suggestion for pattern")
        return suggestion.to_dict()

    return r
