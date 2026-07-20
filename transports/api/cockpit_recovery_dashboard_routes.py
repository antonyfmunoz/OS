"""Cockpit Recovery Dashboard routes — G11 MVP gate.

Surfaces failed/blocked/interrupted work items with recovery actions.
All recovery executions route through governed_mutation().

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

recovery_dashboard_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, recovery_dashboard_router
    _configured = True
    recovery_dashboard_router = _build_router(require_operator_dep)


def _get_recovery_runtime() -> Any:
    try:
        from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime

        return WorkRecoveryRuntime()
    except Exception:
        return None


def _get_failure_engine() -> Any:
    try:
        from substrate.execution.runtime.runtime_recovery_v1 import RuntimeRecoveryManager

        return RuntimeRecoveryManager()
    except Exception:
        return None


def _get_journal() -> Any:
    try:
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.state.runtime_paths import runtime_state_path

        j_path = runtime_state_path("organism", "execution_journal.jsonl", create_parent=False)
        journal = ExecutionJournal(persist_path=str(j_path))
        journal.recover()
        return journal
    except Exception:
        return None


_recovery_history: list[dict[str, Any]] = []


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/recovery/summary", _summary, methods=["GET"])
    r.add_api_route("/recovery/queue", _queue, methods=["GET"])
    r.add_api_route("/recovery/queue/{work_id}", _queue_detail, methods=["GET"])
    r.add_api_route("/recovery/failures", _failures, methods=["GET"])
    r.add_api_route("/recovery/failures/{work_id}/history", _failure_history, methods=["GET"])
    r.add_api_route("/recovery/actions/{work_id}", _actions, methods=["GET"])
    r.add_api_route("/recovery/execute", _execute, methods=["POST"], dependencies=auth)
    r.add_api_route("/recovery/history", _history, methods=["GET"])

    return r


async def _summary(request: Request) -> dict[str, Any]:
    runtime = _get_recovery_runtime()
    if runtime is None:
        return {
            "total_recoverable": 0,
            "failed": 0,
            "blocked": 0,
            "interrupted": 0,
            "runtime_available": False,
        }

    failed = runtime.failed_work()
    blocked = runtime.blocked_work()
    interrupted = runtime.interrupted_work()
    recoverable = runtime.recoverable_work()

    return {
        "total_recoverable": len(recoverable),
        "failed": len(failed),
        "blocked": len(blocked),
        "interrupted": len(interrupted),
        "runtime_available": True,
    }


async def _queue(request: Request) -> dict[str, Any]:
    runtime = _get_recovery_runtime()
    if runtime is None:
        return {"items": [], "runtime_available": False}

    assessments = runtime.recoverable_work()
    items = [a.to_dict() for a in assessments]
    return {"items": items, "total": len(items), "runtime_available": True}


async def _queue_detail(request: Request) -> dict[str, Any]:
    work_id = request.path_params["work_id"]
    runtime = _get_recovery_runtime()
    if runtime is None:
        raise HTTPException(status_code=503, detail="Recovery runtime unavailable")

    assessment = runtime.assess(work_id)
    result = assessment.to_dict()

    journal = _get_journal()
    if journal:
        try:
            entries = journal.entries_for(work_id)
            result["journal_entries"] = [
                {
                    "phase": getattr(e, "phase", "unknown"),
                    "source": getattr(e, "source", ""),
                    "details": getattr(e, "details", ""),
                    "timestamp": getattr(e, "timestamp", 0),
                }
                for e in entries
            ]
        except Exception:
            result["journal_entries"] = []

    return result


async def _failures(request: Request) -> dict[str, Any]:
    runtime = _get_recovery_runtime()
    if runtime is None:
        return {"failures": [], "runtime_available": False}

    failed = runtime.failed_work()
    items = []
    for node in failed:
        items.append(
            {
                "work_id": getattr(node, "node_id", str(node)),
                "status": getattr(node, "status", "failed"),
                "description": getattr(node, "description", ""),
                "risk_class": getattr(node, "risk_class", "unknown"),
                "created_at": getattr(node, "created_at", 0),
            }
        )
    return {"failures": items, "total": len(items), "runtime_available": True}


async def _failure_history(request: Request) -> dict[str, Any]:
    work_id = request.path_params["work_id"]
    engine = _get_failure_engine()
    if engine is None:
        return {"work_id": work_id, "history": [], "engine_available": False}

    try:
        history = engine.get_failure_history(work_id)
        records = []
        for rec in history:
            records.append(
                {
                    "failure_type": getattr(rec, "failure_type", "unknown"),
                    "message": getattr(rec, "message", ""),
                    "timestamp": getattr(rec, "timestamp", 0),
                    "recovery_attempted": getattr(rec, "recovery_attempted", False),
                }
            )
        return {"work_id": work_id, "history": records, "engine_available": True}
    except Exception as exc:
        logger.debug("Failure history lookup failed for %s: %s", work_id, exc)
        return {"work_id": work_id, "history": [], "engine_available": True, "error": str(exc)}


async def _actions(request: Request) -> dict[str, Any]:
    work_id = request.path_params["work_id"]
    runtime = _get_recovery_runtime()
    if runtime is None:
        raise HTTPException(status_code=503, detail="Recovery runtime unavailable")

    actions = runtime.recovery_actions(work_id)
    return {
        "work_id": work_id,
        "actions": [a.to_dict() for a in actions],
    }


async def _execute(request: Request) -> dict[str, Any]:
    body = await request.json()
    work_id = body.get("work_id", "")
    action_type = body.get("action_type", "")
    reason = body.get("reason", "")

    if not work_id or not action_type:
        raise HTTPException(status_code=400, detail="work_id and action_type required")

    valid_actions = {"retry", "resume", "unblock", "escalate", "abandon"}
    if action_type not in valid_actions:
        raise HTTPException(
            status_code=400, detail=f"Invalid action_type. Must be one of: {valid_actions}"
        )

    def _do_recovery() -> tuple[str, bool]:
        runtime = _get_recovery_runtime()
        if runtime is None:
            return "Recovery runtime unavailable", False

        assessment = runtime.assess(work_id)
        available = {
            a.action.value if hasattr(a.action, "value") else a.action for a in assessment.actions
        }

        if action_type not in available:
            return (
                f"Action {action_type} not available for work {work_id}. Available: {available}",
                False,
            )

        _recovery_history.append(
            {
                "work_id": work_id,
                "action_type": action_type,
                "reason": reason,
                "timestamp": time.time(),
                "state_before": assessment.state.value
                if hasattr(assessment.state, "value")
                else str(assessment.state),
            }
        )

        return f"Recovery action {action_type} queued for {work_id}", True

    result = governed_mutation(
        mutation_name="recovery_action",
        intent=f"{action_type} work {work_id}",
        execute_fn=_do_recovery,
        source="cockpit",
        metadata={"work_id": work_id, "action_type": action_type, "reason": reason},
    )
    if not result.success:
        raise HTTPException(status_code=422, detail=result.to_http_dict())
    return result.to_http_dict()


async def _history(request: Request) -> dict[str, Any]:
    limit = int(request.query_params.get("limit", "50"))
    recent = _recovery_history[-limit:]
    recent.reverse()
    return {"history": recent, "total": len(_recovery_history)}
