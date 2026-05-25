"""Workstation API — workstation mode execution, state, and health."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from substrate.execution.workers.workstation.workstation_contracts_v1 import (
    OperationalMode,
    WorkstationExecutionRequest,
)
from substrate.execution.workers.workstation.workstation_execution_orchestrator_v1 import (
    WorkstationExecutionOrchestrator,
)
from substrate.governance.security import get_audit_log, validate_command
from substrate.workstation.state import (
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationStateManager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/umh/workstation", tags=["workstation"])

_orchestrator = WorkstationExecutionOrchestrator()
_state_manager = WorkstationStateManager()
_profile = WorkstationProfile.detect()
_session = WorkstationSessionState()


class WorkstationExecRequest(BaseModel):
    command: str = Field(max_length=2000)
    adapter_type: str = "shell"
    target_session: str | None = None
    correlation_id: str | None = None


class WorkstationModeRequest(BaseModel):
    mode: str = Field(description="One of: developer, operator, autonomous, restricted, maintenance")


@router.post("/execute")
async def workstation_execute(req: WorkstationExecRequest):
    """Execute a command through the governed workstation orchestrator."""
    cmd_validation = validate_command(req.command)
    if not cmd_validation.valid:
        raise HTTPException(status_code=400, detail=f"Command blocked: {', '.join(cmd_validation.violations)}")

    get_audit_log().record(
        action="workstation_execute",
        target=req.adapter_type,
        detail=req.command[:200],
        risk_level="high",
    )

    ws_request = WorkstationExecutionRequest(
        command=req.command,
        adapter_type=req.adapter_type,
        target_session=req.target_session or "",
        operational_mode=_orchestrator._mode,
        correlation_id=req.correlation_id or "",
    )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _orchestrator.execute, ws_request)

    _session.record_activity(result.request_id, f"workstation_{result.outcome.value}")
    if not result.succeeded:
        _session.record_error()

    return {
        "request_id": result.request_id,
        "command": result.command,
        "outcome": result.outcome.value,
        "succeeded": result.succeeded,
        "adapter_used": result.adapter_used,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "governance_verdict": result.governance_verdict,
        "error_message": result.error_message,
    }


@router.get("/mode")
async def get_mode():
    """Get current operational mode."""
    return {
        "mode": _orchestrator._mode.value,
        "stats": _orchestrator.get_stats(),
    }


@router.patch("/mode")
async def set_mode(req: WorkstationModeRequest):
    """Change operational mode."""
    try:
        mode = OperationalMode(req.mode)
    except ValueError:
        valid = [m.value for m in OperationalMode]
        raise HTTPException(status_code=400, detail=f"Invalid mode. Valid: {valid}")

    _orchestrator.set_mode(mode)
    return {"mode": mode.value, "message": f"Mode changed to {mode.value}"}


@router.get("/state")
async def get_state():
    """Get current workstation state snapshot."""
    snapshot = _state_manager.build_snapshot(_profile, _session)
    return snapshot.to_dict()


@router.get("/health")
async def workstation_health():
    """Get workstation health including pipeline homeostasis."""
    stats = _orchestrator.get_stats()
    return {
        "profile": _profile.to_dict(),
        "session": _session.to_dict(),
        "orchestrator_stats": stats,
    }


@router.get("/stats")
async def workstation_stats():
    """Get workstation execution statistics."""
    return _orchestrator.get_stats()
