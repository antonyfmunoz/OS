"""Cell control bridge — connects cells to the existing execution spine.

The bridge accepts CellExecutionRequests and routes them to the
existing planning/execution infrastructure. It does NOT contain
execution logic itself — it translates cell requests into the
shapes the control plane already understands.

CellExecutionRequest → PlanObjective → create_plan() → execution spine.

If the planning layer is unavailable, the bridge returns a PENDING
result and emits a signal. No execution is ever bypassed or duplicated.

No imports from adapters, tools, subprocess, or shell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from umh.cells.models import (
    CellExecutionRequest,
    CellResult,
    RequestStatus,
    _gen_id,
)
from umh.core.clock import iso_now as _iso_now

if TYPE_CHECKING:
    from umh.planning.models import ExecutionPlan


def _emit(signal_type: str, payload: dict[str, Any]) -> None:
    """Best-effort signal emission."""
    try:
        from umh.brains.signals import emit_signal

        emit_signal("cell_bridge", signal_type, payload)
    except Exception:
        pass


def _publish_event(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort event publishing."""
    try:
        from umh.events.stream import publish

        publish(event_type, payload=payload, actor_id="cell_bridge")
    except Exception:
        pass


def submit_request(request: CellExecutionRequest) -> CellResult:
    """Submit a cell execution request to the control plane.

    Attempts to create a plan via the existing planning layer.
    If the planning layer returns a validated plan, the result is DELEGATED
    (meaning the control plane accepted it — actual execution follows
    the normal plan lifecycle).

    If planning fails or is unavailable, returns PENDING with the request
    queued for later processing.
    """
    try:
        return _delegate_to_planner(request)
    except Exception as exc:
        _emit(
            "cell.bridge_fallback",
            {
                "request_id": request.request_id,
                "cell_id": request.cell_id,
                "reason": str(exc),
            },
        )
        return _pending_result(request, reason=f"Planning unavailable: {exc}")


def _delegate_to_planner(request: CellExecutionRequest) -> CellResult:
    """Convert CellExecutionRequest → PlanObjective → create_plan."""
    from umh.planning.models import PlanObjective
    from umh.planning.planner import create_plan

    objective = PlanObjective(
        title=request.objective,
        description=f"Cell {request.cell_id} requests: {request.operation}",
        constraints=list(request.constraints),
        context={
            "cell_id": request.cell_id,
            "request_id": request.request_id,
            "operation": request.operation,
            "inputs": request.inputs,
            "required_capabilities": list(request.required_capabilities),
            "environment": request.environment,
            "source": "cell_bridge",
        },
        requested_by=f"cell:{request.cell_id}",
        allowed_capabilities=list(request.required_capabilities) or None,
    )

    plan = create_plan(objective)

    plan_status = plan.status.value
    plan_id = plan.plan_id

    _publish_event(
        "cell.request_delegated",
        {
            "request_id": request.request_id,
            "cell_id": request.cell_id,
            "plan_id": plan_id,
            "plan_status": plan_status,
        },
    )

    if plan_status in ("validated", "executing", "completed"):
        return CellResult(
            request_id=request.request_id,
            cell_id=request.cell_id,
            status=RequestStatus.DELEGATED,
            plan_id=plan_id,
            outputs={"plan_status": plan_status},
            metadata={"objective": request.objective},
        )

    return CellResult(
        request_id=request.request_id,
        cell_id=request.cell_id,
        status=RequestStatus.REJECTED,
        plan_id=plan_id,
        error=f"Plan {plan_status}: {'; '.join(plan.validation_errors) if plan.validation_errors else 'no details'}",
        metadata={"objective": request.objective},
    )


def _pending_result(request: CellExecutionRequest, reason: str = "") -> CellResult:
    """Return a PENDING result when the bridge cannot delegate immediately."""
    _emit(
        "cell.request_pending",
        {
            "request_id": request.request_id,
            "cell_id": request.cell_id,
            "reason": reason,
        },
    )

    return CellResult(
        request_id=request.request_id,
        cell_id=request.cell_id,
        status=RequestStatus.PENDING,
        error=reason,
        metadata={"objective": request.objective, "queued": True},
    )
