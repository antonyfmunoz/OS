"""UMH Control Plane API — single authenticated HTTP interface.

All external interaction (CLI, UI, agents, automation) routes through
this API. It delegates to the execution engine, approval store, and
metrics module without duplicating logic.

Authentication is identity-based with scoped permissions. Every action
is attributable to an authenticated identity.

Usage:
    python3 -m umh.control.api
    uvicorn umh.control.api:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, "/opt/OS")

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from umh.control.identity import Identity, get_identity_store
from umh.core.clock import iso_now as _iso_now
from umh.execution.approval import ApprovalStatus, get_approval_store
from umh.execution.contract import (
    ExecutionClass,
    ExecutionConstraints,
    ExecutionContext,
    ExecutionRequest,
    ExecutionTarget,
)
from umh.events.stream import get_event_stream
from umh.execution.engine import execute
from umh.execution.metrics import get_metrics

app = FastAPI(
    title="UMH Control Plane",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)


# ── Global Exception Handler ───────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging

    logging.getLogger("umh.control.api").error(
        "Unhandled error: %s %s — %s", request.method, request.url.path, exc
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)},
    )


# ── Error Helper ───────────────────────────────────────────────────


def _error_response(status_code: int, error_type: str, message: str) -> JSONResponse:
    """Return a consistent JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": error_type, "message": message},
    )


# ── Startup Event ──────────────────────────────────────────────────


@app.on_event("startup")
async def startup_event():
    import logging

    _log = logging.getLogger("umh.control.api")

    # Auto-start worker if configured
    try:
        from umh.core.config import WORKER_AUTO_START, WORKER_POLL_INTERVAL
    except ImportError:
        WORKER_AUTO_START = True
        WORKER_POLL_INTERVAL = 2.0

    if WORKER_AUTO_START:
        from umh.orchestrator.worker import start_worker
        from umh.orchestrator.engine import start_orchestrator

        start_orchestrator()
        start_worker(poll_interval=WORKER_POLL_INTERVAL)
        _log.info("Worker auto-started (poll_interval=%.1f)", WORKER_POLL_INTERVAL)

    try:
        from umh.adapters.adapter_pack import initialize_adapter_pack

        initialize_adapter_pack()
        _log.info("Adapter pack initialized")
    except Exception as e:
        _log.warning("Adapter pack init failed (non-fatal): %s", e)


# ── Auth Middleware ──────────────────────────────────────────────────


def _legacy_key_check(provided: str) -> bool:
    """Fallback: check against UMH_API_KEY env var for backwards compat."""
    legacy = os.environ.get("UMH_API_KEY")
    return legacy is not None and provided == legacy


def _build_legacy_identity(api_key: str) -> Identity:
    """Build a synthetic identity for legacy API key auth."""
    from umh.control.identity import hash_key

    return Identity(
        id="legacy_api_key",
        name="legacy",
        api_key_hash=hash_key(api_key),
        scopes=["admin"],
        created_at="",
        status="active",
    )


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/ui"):
        return await call_next(request)

    provided = request.headers.get("X-API-Key", "")
    if not provided:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key"},
        )

    # Try identity store first
    store = get_identity_store()
    identity = store.authenticate(provided)

    # Fallback to legacy UMH_API_KEY
    if identity is None and _legacy_key_check(provided):
        identity = _build_legacy_identity(provided)

    if identity is None:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key"},
        )

    request.state.identity = identity
    return await call_next(request)


def _require_scope(request: Request, scope: str) -> Identity:
    """Extract identity and enforce scope. Raises HTTPException on failure."""
    identity: Identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not identity.has_scope(scope):
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient scope: requires '{scope}'",
        )
    return identity


# ── Health ───────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/ui/")


# ── Worker Health ──────────────────────────────────────────────────


@app.get("/worker/health")
async def worker_health(request: Request):
    _require_scope(request, "metrics:read")
    from umh.orchestrator.worker import get_worker

    worker = get_worker()
    return worker.heartbeat()


# ── Run (primary operator entry point) ──────────────────────────────


class RunBody(BaseModel):
    objective: str
    async_exec: bool = True
    dry_run: bool = False
    use_memory: bool = False


@app.post("/run")
async def run_endpoint(request: Request, body: RunBody):
    identity = _require_scope(request, "execute")

    from umh.planning.planner import create_plan_from_raw, execute_plan
    from umh.planning.models import PlanStatus

    plan = create_plan_from_raw(body.objective, requested_by=identity.id)

    # Memory context — informational for the operator, NOT injected into planner
    memory_context: list = []
    memory_count: int = 0
    if body.use_memory:
        try:
            from umh.memory.context import get_relevant_context, format_context_for_planner

            memories = get_relevant_context(body.objective)
            if memories:
                memory_context = memories
                memory_count = len(memories)
        except Exception:
            pass  # Memory is optional — never block execution

    quality_verdict = ""
    if plan.quality_score:
        quality_verdict = plan.quality_score.get("verdict", "")

    executable = plan.status == PlanStatus.VALIDATED and quality_verdict != "fail"

    if not executable or body.dry_run:
        resp = _enrich_plan_response(plan)
        resp["memory_context"] = memory_context
        resp["memory_count"] = memory_count
        return resp

    from umh.orchestrator.task import TaskStatus
    from umh.orchestrator.summary import summarize_task

    try:
        result = execute_plan(plan)
        if result is None:
            resp = _enrich_plan_response(plan)
            resp["memory_context"] = memory_context
            resp["memory_count"] = memory_count
            return resp

        summary = summarize_task(result)
        resp = _enrich_plan_response(plan)
        resp["task_id"] = result.id
        resp["task_status"] = result.status.value
        resp["task_summary"] = summary
        resp["next_actions"] = _build_next_actions(result, plan)
        resp["memory_context"] = memory_context
        resp["memory_count"] = memory_count
        return resp

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _build_next_actions(task, plan=None) -> list[str]:
    """Build contextual next-action hints based on task state."""
    from umh.orchestrator.task import TaskStatus

    actions: list[str] = []
    if task.status == TaskStatus.PAUSED:
        actions.append(f"Approve: POST /approvals/{task.paused_approval_id}/approve")
        actions.append(f"Deny: POST /approvals/{task.paused_approval_id}/deny")
        actions.append(f"Cancel: POST /tasks/{task.id}/cancel")
    elif task.status == TaskStatus.FAILED:
        actions.append(f"Retry: POST /tasks/{task.id}/retry")
        actions.append(f"Timeline: GET /tasks/{task.id}/timeline")
    elif task.status == TaskStatus.COMPLETED:
        actions.append(f"Summary: GET /tasks/{task.id}/summary")
        actions.append(f"Timeline: GET /tasks/{task.id}/timeline")
    elif task.status == TaskStatus.PENDING:
        actions.append(f"Watch: GET /tasks/{task.id}")
        actions.append(f"Cancel: POST /tasks/{task.id}/cancel")
    return actions


# ── Execute ──────────────────────────────────────────────────────────


class ExecuteBody(BaseModel):
    operation: str
    inputs: dict = Field(default_factory=dict)
    execution_class: str = "side_effect"
    timeout_s: int = 30
    sandbox: bool = False


@app.post("/execute")
async def execute_endpoint(request: Request, body: ExecuteBody):
    identity = _require_scope(request, "execute")
    exec_id = f"exec_{uuid.uuid4().hex[:16]}"
    exec_request = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=exec_id,
        causal_event_id="",
        session_id="",
        operation=body.operation,
        inputs=body.inputs,
        execution_class=ExecutionClass(body.execution_class),
        constraints=ExecutionConstraints(
            timeout_s=body.timeout_s,
            sandbox=body.sandbox,
        ),
        target=ExecutionTarget(node_id="local", transport="api"),
        context=ExecutionContext(metadata={"actor_id": identity.id}),
        issued_at=_iso_now(),
        issued_by=identity.id,
        idempotency_key="",
    )
    result = execute(exec_request)
    return result.to_dict()


# ── Run Direct (governed, non-planner) ────────────────────────────────


class RunDirectBody(BaseModel):
    operation: str
    inputs: dict = Field(default_factory=dict)
    environment: str = "local"
    capability: str = ""
    authority: str = "analyze"
    constraints: dict = Field(default_factory=dict)


@app.post("/run/direct")
async def run_direct_endpoint(request: Request, body: RunDirectBody):
    identity = _require_scope(request, "execute")
    from umh.execution.governance_gate import ExecutionDirective, execute_governed
    from umh.governance.authority import AuthorityLevel

    authority_map = {level.name.lower(): level for level in AuthorityLevel}
    authority = authority_map.get(body.authority.lower())
    if authority is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid authority '{body.authority}'. Must be one of: {', '.join(authority_map.keys())}",
        )

    directive = ExecutionDirective(
        operation=body.operation,
        inputs=body.inputs,
        environment=body.environment,
        capability=body.capability,
        authority=authority,
        constraints=body.constraints,
    )

    result = execute_governed(directive, user_id=identity.id)
    status_code = 200 if result["success"] else 422
    return JSONResponse(status_code=status_code, content=result)


# ── Adapter Pack Introspection ────────────────────────────────────────


@app.get("/adapters/capabilities")
async def list_adapter_capabilities(request: Request):
    _require_scope(request, "metrics:read")
    from umh.capabilities.definitions import list_capabilities

    return [c.to_dict() for c in list_capabilities()]


@app.get("/adapters/environments")
async def list_adapter_environments(request: Request):
    _require_scope(request, "metrics:read")
    from umh.environments.definitions import list_environments

    return [e.to_dict() for e in list_environments()]


@app.get("/adapters/status")
async def adapter_pack_status(request: Request):
    _require_scope(request, "metrics:read")
    from umh.adapters.adapter_pack import get_adapter_pack_status

    return get_adapter_pack_status()


# ── Workstation ────────────────────────────────────────────────────────


class WorkstationBootBody(BaseModel):
    mode: str = "command_center"


@app.get("/workstation/status")
async def workstation_status(request: Request):
    identity = _require_scope(request, "metrics:read")
    from umh.workstation.operator_profile import load_or_create_profile
    from umh.workstation.session_state import get_session_store

    profile = load_or_create_profile(identity.id)
    session_store = get_session_store()
    session = session_store.get_active_session(identity.id)

    return {
        "user_id": identity.id,
        "workstation_id": profile.workstation_id,
        "active_mode": profile.active_mode,
        "active_session_id": session.session_id if session else None,
        "current_environment": profile.execution_preference.preferred_environment,
        "execution_preference": profile.execution_preference.to_dict(),
        "session_status": session.status.value if session else "none",
    }


@app.post("/workstation/boot")
async def workstation_boot(request: Request, body: WorkstationBootBody):
    identity = _require_scope(request, "execute")
    from umh.control.trace_store import get_trace_store
    from umh.workstation.boot_sequence import run_boot_sequence

    result = run_boot_sequence(
        user_id=identity.id,
        mode=body.mode,
        trace_store=get_trace_store(),
    )
    return result.to_dict()


@app.get("/workstation/resume")
async def workstation_resume(request: Request):
    identity = _require_scope(request, "metrics:read")
    from umh.control.trace_store import get_trace_store
    from umh.workstation.operator_profile import load_or_create_profile
    from umh.workstation.resume import build_resume_summary
    from umh.workstation.session_state import get_session_store

    profile = load_or_create_profile(identity.id)
    session_store = get_session_store()
    session = session_store.get_active_session(identity.id)
    summary = build_resume_summary(
        profile=profile,
        session=session,
        trace_store=get_trace_store(),
    )
    return summary.to_dict()


@app.get("/workstation/modes")
async def workstation_modes(request: Request):
    _require_scope(request, "metrics:read")
    from umh.workstation.modes import ModeRegistry

    registry = ModeRegistry()
    return [m.to_dict() for m in registry.list_modes()]


@app.get("/workstation/devices")
async def workstation_devices(request: Request):
    _require_scope(request, "metrics:read")
    from umh.workstation.device_registry import DeviceRegistry, create_default_devices

    registry = DeviceRegistry()
    for d in create_default_devices():
        registry.register_device(d)
    return registry.to_dict()


@app.get("/workstation/environments")
async def workstation_environments(request: Request):
    _require_scope(request, "metrics:read")
    from umh.workstation.environment_registry import (
        WorkstationEnvironmentRegistry,
        create_default_environments,
    )

    registry = WorkstationEnvironmentRegistry()
    for e in create_default_environments():
        registry.register_environment(e)
    return registry.to_dict()


@app.get("/workstation/pending-approvals")
async def workstation_pending_approvals(request: Request):
    identity = _require_scope(request, "approvals:read")
    from umh.workstation.resume import list_pending_approvals

    approvals = list_pending_approvals(identity.id)
    return [a.to_dict() for a in approvals]


# ── Feedback (Phase 78) ────────────────────────────────────────────────


class UserFeedbackBody(BaseModel):
    trace_id: str
    outcome_id: str = ""
    score: float = 0.5
    signal: str = "user_positive"
    notes: str = ""


@app.get("/feedback/outcomes")
async def list_feedback_outcomes(
    request: Request, user_id: str | None = None, trace_id: str | None = None, limit: int = 50
):
    _require_scope(request, "metrics:read")
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    outcomes = store.list_outcomes(user_id=user_id, trace_id=trace_id, limit=limit)
    return [o.to_dict() for o in outcomes]


@app.get("/feedback/outcomes/{outcome_id}")
async def get_feedback_outcome(request: Request, outcome_id: str):
    _require_scope(request, "metrics:read")
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    outcome = store.get_outcome(outcome_id)
    if outcome is None:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome.to_dict()


@app.get("/feedback/records")
async def list_feedback_records(
    request: Request, user_id: str | None = None, trace_id: str | None = None, limit: int = 50
):
    _require_scope(request, "metrics:read")
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    records = store.list_feedback(user_id=user_id, trace_id=trace_id, limit=limit)
    return [r.to_dict() for r in records]


@app.get("/feedback/memory-candidates")
async def list_feedback_memory_candidates(
    request: Request, user_id: str | None = None, limit: int = 50
):
    _require_scope(request, "metrics:read")
    from umh.feedback.store import get_feedback_store

    store = get_feedback_store()
    candidates = store.list_memory_candidates(user_id=user_id, limit=limit)
    return [c.to_dict() for c in candidates]


@app.post("/feedback/user")
async def post_user_feedback(request: Request, body: UserFeedbackBody):
    identity = _require_scope(request, "execute")
    from umh.feedback.outcome import clamp_score
    from umh.feedback.records import (
        FeedbackRecord,
        FeedbackSource,
        create_feedback_id,
        normalize_feedback_signal,
    )
    from umh.feedback.store import get_feedback_store
    from umh.core.clock import iso_now

    signal_type = normalize_feedback_signal(body.signal)
    feedback = FeedbackRecord(
        feedback_id=create_feedback_id(body.trace_id, signal_type.value, "user"),
        trace_id=body.trace_id,
        outcome_id=body.outcome_id,
        user_id=identity.id,
        signal_type=signal_type,
        score=clamp_score(body.score),
        confidence=0.9,
        source=FeedbackSource.USER,
        notes=body.notes,
        timestamp=iso_now(),
    )
    store = get_feedback_store()
    store.append_feedback(feedback)
    return feedback.to_dict()


# ── Traces ────────────────────────────────────────────────────────────


@app.get("/traces/{trace_id}")
async def get_trace_endpoint(request: Request, trace_id: str):
    _require_scope(request, "metrics:read")
    from umh.control.trace_store import get_trace_store

    store = get_trace_store()
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
    return trace.to_dict()


@app.get("/traces")
async def list_traces_endpoint(request: Request, limit: int = 50):
    _require_scope(request, "metrics:read")
    from umh.control.trace_store import get_trace_store

    store = get_trace_store()
    traces = store.list_traces(limit=min(limit, 200))
    return [t.to_dict() for t in traces]


# ── Approvals ────────────────────────────────────────────────────────


@app.get("/approvals")
async def list_approvals(request: Request, status: str | None = None):
    _require_scope(request, "approvals:read")
    store = get_approval_store()
    if status == "pending":
        reqs = store.list_pending()
    else:
        reqs = store.list_all()
    return [r.to_dict() for r in reqs]


@app.get("/approvals/{approval_id}")
async def get_approval(request: Request, approval_id: str):
    _require_scope(request, "approvals:read")
    store = get_approval_store()
    req = store.get(approval_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    return req.to_dict()


@app.post("/approvals/{approval_id}/approve")
async def approve_approval(request: Request, approval_id: str):
    identity = _require_scope(request, "approvals:write")
    store = get_approval_store()
    req = store.get(approval_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    if req.is_expired():
        raise HTTPException(status_code=409, detail=f"Approval {approval_id} has expired")
    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: status is {req.status.value}",
        )
    result = store.approve(approval_id, approved_by=identity.id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    if result.status == ApprovalStatus.EXPIRED:
        raise HTTPException(
            status_code=409, detail=f"Approval {approval_id} expired during approval"
        )
    return {"approved": approval_id, "status": "approved", "approved_by": identity.id}


@app.post("/approvals/{approval_id}/deny")
async def deny_approval(request: Request, approval_id: str):
    identity = _require_scope(request, "approvals:write")
    store = get_approval_store()
    req = store.get(approval_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    if req.status == ApprovalStatus.CONSUMED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot deny: {approval_id} already consumed",
        )
    result = store.deny(approval_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    return {"denied": approval_id, "status": "denied", "denied_by": identity.id}


# ── Attention Queue ──────────────────────────────────────────────────


def _resolve_goal_for_task(task):
    """Resolve the goal associated with a task, if any."""
    goal_id = task.context.get("goal_id", "")
    if not goal_id:
        return None
    from umh.goals.store import get_goal_store

    return get_goal_store().get(goal_id)


def _compute_task_age(task) -> float:
    """Compute task age in seconds from creation time."""
    from datetime import datetime, timezone

    try:
        created = datetime.fromisoformat(task.created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - created).total_seconds())
    except (ValueError, TypeError):
        return 0.0


@app.get("/system/controls")
async def get_controls(request: Request):
    _require_scope(request, "metrics:read")
    from umh.attention.controls import get_system_controls

    controls = get_system_controls()
    return controls.to_dict()


@app.post("/system/controls")
async def update_controls(request: Request):
    _require_scope(request, "admin")
    from umh.attention.controls import get_system_controls, update_system_control
    from umh.events.stream import publish as _publish_event

    body = await request.json()

    errors = []
    for key, value in body.items():
        try:
            update_system_control(key, value)
        except (ValueError, KeyError) as e:
            errors.append(f"{key}: {str(e)}")

    controls = get_system_controls()

    _publish_event(
        "system.controls_updated",
        payload={"controls": controls.to_dict(), "errors": errors},
        actor_id="operator",
    )

    result = controls.to_dict()
    if errors:
        result["errors"] = errors
    return result


@app.get("/queue")
async def get_execution_queue(request: Request):
    _require_scope(request, "metrics:read")
    from umh.attention.queue import get_attention_queue

    queue = get_attention_queue()
    entries = queue.list_ordered()
    return {"queue": [e.to_dict() for e in entries], "size": queue.size()}


@app.get("/tasks/{task_id}/priority")
async def get_task_priority(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.attention.controls import compute_control_influence, get_system_controls
    from umh.attention.queue import get_attention_queue

    queue = get_attention_queue()
    for entry in queue.list_ordered():
        if entry.task_id == task_id:
            controls = get_system_controls()
            influence = compute_control_influence(
                controls, entry.priority_score, entry.priority_score
            )
            result = entry.to_dict()
            result["control_influence"] = influence.to_dict()
            return result

    # Not in queue — compute on the fly with controls
    from umh.attention.controls import score_task_with_controls
    from umh.goals.models import GoalPriority
    from umh.orchestrator.task import get_task

    task = get_task(task_id)
    if task is None:
        return JSONResponse({"error": "task not found"}, status_code=404)
    goal = _resolve_goal_for_task(task)
    goal_priority = goal.priority if goal is not None else GoalPriority.MEDIUM
    age = _compute_task_age(task)
    entry, influence = score_task_with_controls(task, goal_priority, age)
    result = entry.to_dict()
    result["control_influence"] = influence.to_dict()
    return result


# ── Metrics ──────────────────────────────────────────────────────────


def _task_metrics() -> dict:
    """Build task-level metrics from the in-memory task store."""
    from umh.orchestrator.task import TaskStatus, list_tasks

    tasks = list_tasks()

    by_status: dict[str, int] = {s.value: 0 for s in TaskStatus}
    recent: list[dict] = []

    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

    sorted_tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)
    for t in sorted_tasks[:5]:
        recent.append(
            {
                "id": t.id,
                "status": t.status.value,
                "step_count": len(t.steps),
                "created_at": t.created_at,
            }
        )

    return {
        "total_tasks": len(tasks),
        "tasks_by_status": by_status,
        "paused_tasks": by_status.get("paused", 0),
        "recent_tasks": recent,
    }


def _plan_metrics() -> dict:
    """Build plan-level metrics from the in-memory plan store."""
    from umh.planning.models import PlanStatus
    from umh.planning.planner import list_plans

    plans = list_plans()
    by_status: dict[str, int] = {s.value: 0 for s in PlanStatus}
    for p in plans:
        by_status[p.status.value] = by_status.get(p.status.value, 0) + 1

    validation_failures = by_status.get("rejected", 0)

    by_verdict: dict[str, int] = {"pass": 0, "warn": 0, "fail": 0}
    quality_scores: list[float] = []
    quality_failures = 0
    for p in plans:
        if p.quality_score:
            v = p.quality_score.get("verdict", "")
            if v in by_verdict:
                by_verdict[v] += 1
            s = p.quality_score.get("score", 0)
            quality_scores.append(s)
            if v == "fail":
                quality_failures += 1

    avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0

    recent: list[dict] = []
    sorted_plans = sorted(plans, key=lambda p: p.created_at, reverse=True)
    for p in sorted_plans[:5]:
        entry: dict = {
            "plan_id": p.plan_id,
            "status": p.status.value,
            "source": p.source.value,
            "step_count": len(p.steps),
            "created_at": p.created_at,
        }
        if p.quality_score:
            entry["quality_verdict"] = p.quality_score.get("verdict", "")
            entry["quality_score"] = p.quality_score.get("score", 0)
        recent.append(entry)

    return {
        "total_plans": len(plans),
        "plans_by_status": by_status,
        "plans_by_quality_verdict": by_verdict,
        "avg_plan_quality": avg_quality,
        "validation_failures": validation_failures,
        "quality_failures": quality_failures,
        "recent_plans": recent,
    }


@app.get("/metrics")
async def metrics_endpoint(request: Request):
    _require_scope(request, "metrics:read")
    base = get_metrics()
    base["tasks"] = _task_metrics()
    base["plans"] = _plan_metrics()

    # Extended metrics — worker health
    try:
        from umh.execution.metrics import get_worker_metrics

        base["worker"] = get_worker_metrics()
    except Exception:
        base["worker"] = {"is_running": False}

    # System controls
    try:
        from umh.attention.controls import get_system_controls as _get_sys_controls

        _sys_controls = _get_sys_controls()
        base["controls"] = {
            "execution_mode": _sys_controls.execution_mode.value,
            "retry_policy": _sys_controls.retry_policy.value,
            "max_concurrent_tasks": _sys_controls.max_concurrent_tasks,
        }
    except Exception:
        base["controls"] = {
            "execution_mode": "balanced",
            "retry_policy": "normal",
            "max_concurrent_tasks": 5,
        }

    # Attention queue metrics
    try:
        from umh.attention.priority import AttentionState
        from umh.attention.queue import get_attention_queue as _get_attn_queue

        attn_queue = _get_attn_queue()
        base["attention"] = {
            "queue_size": attn_queue.size(),
            "starved_count": len(attn_queue.list_by_state(AttentionState.STARVED)),
        }
    except Exception:
        base["attention"] = {"queue_size": 0, "starved_count": 0}

    # Memory stats
    try:
        from umh.memory.persistent_store import get_memory_store

        store = get_memory_store()
        total = store.count_memories()
        base["memory"] = {"total_memories": total}
    except Exception:
        base["memory"] = {"total_memories": 0}

    # Agent metrics
    try:
        from umh.planning.planner import list_plans as _list_plans_for_metrics

        all_plans = _list_plans_for_metrics()
        reviewed = sum(1 for p in all_plans if getattr(p, "review", None))
        debugged = sum(1 for p in all_plans if getattr(p, "debug_analysis", None))
        base["agents"] = {
            "plans_reviewed": reviewed,
            "plans_debugged": debugged,
        }
    except Exception:
        base["agents"] = {"plans_reviewed": 0, "plans_debugged": 0}

    # Schedule metrics
    try:
        from umh.scheduler.store import get_schedule_store as _get_sched_store

        sched_store = _get_sched_store()
        all_scheds = sched_store.list_all()
        enabled_count = sum(1 for s in all_scheds if s.enabled)
        disabled_count = len(all_scheds) - enabled_count
        runs_today = sum(s.run_count for s in all_scheds)
        failed_runs = sum(1 for s in all_scheds if s.last_run_status == "failed")
        skipped_runs = sum(1 for s in all_scheds if s.last_run_status == "skipped")

        next_due = ""
        enabled_scheds = [s for s in all_scheds if s.enabled and s.next_run_at]
        if enabled_scheds:
            next_due = min(s.next_run_at for s in enabled_scheds)

        base["schedules"] = {
            "total": len(all_scheds),
            "enabled": enabled_count,
            "disabled": disabled_count,
            "runs_today": runs_today,
            "failed_runs": failed_runs,
            "skipped_runs": skipped_runs,
            "next_due": next_due,
        }
    except Exception:
        base["schedules"] = {
            "total": 0,
            "enabled": 0,
            "disabled": 0,
            "runs_today": 0,
            "failed_runs": 0,
            "skipped_runs": 0,
            "next_due": "",
        }

    # Goal metrics
    try:
        from umh.goals.store import get_goal_store as _get_goal_store

        goal_store = _get_goal_store()
        all_goals = goal_store.list_all()
        active_goals = sum(1 for g in all_goals if g.status.value == "active")
        completed_goals = sum(1 for g in all_goals if g.status.value == "completed")
        total_tasks_from_goals = sum(g.tasks_created for g in all_goals)
        total_completed_from_goals = sum(g.tasks_completed for g in all_goals)
        base["goals"] = {
            "total": len(all_goals),
            "active": active_goals,
            "completed": completed_goals,
            "tasks_generated": total_tasks_from_goals,
            "tasks_completed_from_goals": total_completed_from_goals,
        }

        from umh.strategy.decomposer import get_cached_strategy as _get_strat

        strategies_computed = sum(1 for g in all_goals if _get_strat(g.id) is not None)
        base["strategies"] = {
            "computed": strategies_computed,
        }

        from umh.strategy.refiner import get_proposal as _get_prop

        proposals_pending = sum(1 for g in all_goals if _get_prop(g.id) is not None)
        base["refinements"] = {
            "proposals_pending": proposals_pending,
        }
    except Exception:
        base["goals"] = {
            "total": 0,
            "active": 0,
            "completed": 0,
            "tasks_generated": 0,
            "tasks_completed_from_goals": 0,
        }
        base["strategies"] = {
            "computed": 0,
        }
        base["refinements"] = {
            "proposals_pending": 0,
        }

    return base


# ── Identity Management ─────────────────────────────────────────────


class CreateIdentityBody(BaseModel):
    name: str
    scopes: list[str]


@app.post("/identities")
async def create_identity_endpoint(request: Request, body: CreateIdentityBody):
    _require_scope(request, "admin")
    store = get_identity_store()
    try:
        identity, raw_key = store.create_identity(body.name, body.scopes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = identity.to_dict()
    result["api_key"] = raw_key
    return result


@app.get("/identities")
async def list_identities(request: Request):
    _require_scope(request, "admin")
    store = get_identity_store()
    return [i.to_dict() for i in store.list_identities()]


@app.post("/identities/{identity_id}/disable")
async def disable_identity_endpoint(request: Request, identity_id: str):
    _require_scope(request, "admin")
    store = get_identity_store()
    if not store.disable_identity(identity_id):
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return {"disabled": identity_id}


# ── Orchestrator ───────────────────────────────────────────���────────


@app.get("/orchestrator/rules")
async def list_orchestrator_rules(request: Request):
    _require_scope(request, "admin")
    from umh.orchestrator.engine import get_orchestrator

    rules = get_orchestrator().list_rules()
    return [r.to_dict() for r in rules]


# ── Tasks ───────────────────────────────────────────────────────────


class TaskStepBody(BaseModel):
    operation: str
    inputs_template: dict = Field(default_factory=dict)
    output_key: str = ""
    execution_class: str = "llm_call"


class CreateTaskBody(BaseModel):
    steps: list[TaskStepBody]
    context: dict = Field(default_factory=dict)
    async_exec: bool = False


@app.get("/tasks")
async def list_tasks_endpoint(request: Request):
    _require_scope(request, "execute")
    from umh.orchestrator.task import list_tasks

    tasks = list_tasks()

    # Enrich with priority scores from the attention queue
    try:
        from umh.attention.queue import get_attention_queue as _get_attn_q

        attn_q = _get_attn_q()
        score_map: dict[str, float] = {}
        for entry in attn_q.list_ordered():
            score_map[entry.task_id] = entry.priority_score
    except Exception:
        score_map = {}

    result = []
    for t in tasks:
        d = t.to_dict()
        if t.id in score_map:
            d["priority_score"] = round(score_map[t.id], 3)
        result.append(d)
    return result


@app.post("/tasks")
async def create_task_endpoint(request: Request, body: CreateTaskBody):
    identity = _require_scope(request, "execute")
    from umh.execution.contract import ExecutionClass
    from umh.orchestrator.task import Task, TaskStep, enqueue_task, execute_task

    if len(body.steps) == 0:
        raise HTTPException(status_code=400, detail="Steps list cannot be empty")

    if len(body.steps) > 10:
        raise HTTPException(status_code=400, detail="Max 10 steps per task")

    for i, s in enumerate(body.steps):
        if not s.operation or not s.operation.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Step {i}: operation cannot be empty",
            )
        try:
            ExecutionClass(s.execution_class)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Step {i}: invalid execution_class '{s.execution_class}'",
            )

    steps = [
        TaskStep(
            operation=s.operation,
            inputs_template=s.inputs_template,
            output_key=s.output_key,
            execution_class=s.execution_class,
        )
        for s in body.steps
    ]
    task = Task(steps=steps, context=dict(body.context), issued_by=identity.id)

    if body.async_exec:
        result = enqueue_task(task)
        return JSONResponse(
            status_code=202,
            content={
                "task_id": result.id,
                "status": result.status.value,
                "step_count": len(result.steps),
                "message": "Task enqueued for background execution",
            },
        )

    result = execute_task(task)
    return result.to_dict()


@app.get("/tasks/{task_id}")
async def get_task_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import TaskStatus, get_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    resp = task.to_dict()
    resp["step_statuses"] = [s.status.value for s in task.steps]
    resp["current_step"] = task.current_step_index
    resp["pending_approval"] = task.paused_approval_id if task.status == TaskStatus.PAUSED else None

    # Attach plan review/debug data if available
    if task.context and task.context.get("plan_id"):
        try:
            from umh.planning.planner import get_plan

            related_plan = get_plan(task.context["plan_id"])
            if related_plan:
                review = getattr(related_plan, "review", None)
                if review:
                    resp["review"] = review
                debug_analysis = getattr(related_plan, "debug_analysis", None)
                if debug_analysis:
                    resp["debug_analysis"] = debug_analysis
                decision_trace = getattr(related_plan, "decision_trace", None)
                if decision_trace:
                    resp["decision_trace"] = decision_trace
        except Exception:
            pass

    return resp


@app.post("/tasks/{task_id}/resume")
async def resume_task_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import TaskStatus, get_task, resume_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=f"Task status is '{task.status.value}', must be 'paused'",
        )
    if not task.paused_approval_id:
        raise HTTPException(status_code=409, detail="Task has no pending approval")

    result = resume_task(task_id, task.paused_approval_id)
    if result is None:
        raise HTTPException(
            status_code=409, detail="Resume failed — task may have already been resumed"
        )
    return result.to_dict()


@app.post("/tasks/{task_id}/cancel")
async def cancel_task_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import TaskStatus, cancel_task, get_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if task.status not in (TaskStatus.PENDING, TaskStatus.PAUSED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel: task status is '{task.status.value}'",
        )

    result = cancel_task(task_id)
    if result is None:
        raise HTTPException(status_code=409, detail="Cancel failed")
    return result.to_dict()


@app.post("/tasks/{task_id}/retry")
async def retry_task_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import TaskStatus, get_task, retry_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry: task status is '{task.status.value}', must be 'failed'",
        )

    new_task = retry_task(task_id)
    if new_task is None:
        raise HTTPException(status_code=409, detail="Retry failed")
    resp = new_task.to_dict()
    resp["retried_from"] = task_id
    return resp


@app.get("/tasks/{task_id}/timeline")
async def task_timeline_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import get_task
    from umh.orchestrator.timeline import build_task_timeline

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    entries = build_task_timeline(task_id)
    return [e.to_dict() for e in entries]


@app.get("/tasks/{task_id}/summary")
async def task_summary_endpoint(request: Request, task_id: str):
    _require_scope(request, "execute")
    from umh.orchestrator.task import get_task
    from umh.orchestrator.summary import summarize_task

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return summarize_task(task)


# ── Plans ───────────────────────────────────────────────────────────


def _enrich_plan_response(plan) -> dict:
    """Add executable, blocked_reason, and warnings to a plan response."""
    from umh.planning.models import PlanStatus

    d = plan.to_dict()

    quality_verdict = ""
    if plan.quality_score:
        quality_verdict = plan.quality_score.get("verdict", "")

    executable = plan.status == PlanStatus.VALIDATED and quality_verdict != "fail"

    blocked_reason = ""
    if not executable:
        if plan.status != PlanStatus.VALIDATED:
            reasons = plan.validation_errors or []
            blocked_reason = f"Plan status is '{plan.status.value}'" + (
                f": {'; '.join(reasons)}" if reasons else ""
            )
        elif quality_verdict == "fail":
            blocked_reason = "Quality verdict is 'fail'"

    warnings: list[str] = []
    if quality_verdict == "warn" and plan.quality_score:
        warnings = plan.quality_score.get("reasons", [])

    d["executable"] = executable
    d["blocked_reason"] = blocked_reason
    d["warnings"] = warnings

    # Agent review / debug data (fields added by multi-agent layer)
    review = getattr(plan, "review", None)
    if review:
        d["review"] = review
    debug_analysis = getattr(plan, "debug_analysis", None)
    if debug_analysis:
        d["debug_analysis"] = debug_analysis
    decision_trace = getattr(plan, "decision_trace", None)
    if decision_trace:
        d["decision_trace"] = decision_trace

    return d


class PlanObjectiveBody(BaseModel):
    title: str = ""
    raw_input: str = ""
    description: str = ""
    constraints: list[str] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    max_steps: int = 10
    allowed_capabilities: list[str] = Field(default_factory=list)
    dry_run: bool = False


@app.post("/plans")
async def create_plan_endpoint(request: Request, body: PlanObjectiveBody):
    identity = _require_scope(request, "execute")
    from umh.planning.models import PlanObjective, PlanStatus
    from umh.planning.planner import create_plan, create_plan_from_raw

    if body.raw_input and body.raw_input.strip():
        plan = create_plan_from_raw(body.raw_input, requested_by=identity.id)
        status_code = 200 if plan.status == PlanStatus.VALIDATED else 422
        return JSONResponse(status_code=status_code, content=_enrich_plan_response(plan))

    if not body.title or not body.title.strip():
        raise HTTPException(status_code=400, detail="title or raw_input required")
    if body.max_steps < 1 or body.max_steps > 10:
        raise HTTPException(status_code=400, detail="max_steps must be 1-10")

    objective = PlanObjective(
        title=body.title,
        description=body.description,
        constraints=body.constraints,
        context=body.context,
        requested_by=identity.id,
        max_steps=body.max_steps,
        allowed_capabilities=body.allowed_capabilities,
        dry_run=body.dry_run,
    )

    plan = create_plan(objective)
    status_code = 200 if plan.status == PlanStatus.VALIDATED else 422
    return JSONResponse(status_code=status_code, content=_enrich_plan_response(plan))


@app.get("/plans")
async def list_plans_endpoint(request: Request):
    _require_scope(request, "execute")
    from umh.planning.planner import list_plans

    plans = []
    for p in list_plans():
        d = p.to_dict()
        if p.quality_score:
            d["quality_verdict"] = p.quality_score.get("verdict", "")
            d["quality_score_value"] = p.quality_score.get("score", 0)
        plans.append(d)
    return plans


@app.get("/plans/{plan_id}")
async def get_plan_endpoint(request: Request, plan_id: str):
    _require_scope(request, "execute")
    from umh.planning.planner import get_plan

    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return plan.to_dict()


@app.post("/plans/{plan_id}/execute")
async def execute_plan_endpoint(request: Request, plan_id: str):
    identity = _require_scope(request, "execute")
    from umh.planning.models import PlanStatus
    from umh.planning.planner import execute_plan, get_plan

    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    if plan.status != PlanStatus.VALIDATED:
        raise HTTPException(
            status_code=409,
            detail=f"Plan status is '{plan.status.value}', must be 'validated'",
        )

    if plan.quality_score and plan.quality_score.get("verdict") == "fail":
        raise HTTPException(
            status_code=422,
            detail=f"Plan quality verdict is 'fail' — execution blocked",
        )

    try:
        result = execute_plan(plan)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if result is None:
        return {
            "plan_id": plan_id,
            "status": "dry_run",
            "task_id": None,
            "objective_summary": f"{plan.objective.title}: {plan.objective.description}".rstrip(
                ": "
            ),
            "step_count": len(plan.steps),
            "approval_required": False,
            "approval_id": "",
        }

    from umh.orchestrator.task import TaskStatus

    resp = result.to_dict()
    resp["plan_id"] = plan_id
    resp["objective_summary"] = f"{plan.objective.title}: {plan.objective.description}".rstrip(": ")
    resp["step_count"] = len(plan.steps)
    resp["approval_required"] = result.status == TaskStatus.PAUSED
    resp["approval_id"] = result.paused_approval_id if result.status == TaskStatus.PAUSED else ""
    if plan.quality_score and plan.quality_score.get("verdict") == "warn":
        resp["quality_warnings"] = plan.quality_score.get("reasons", [])
    resp["next_actions"] = _build_next_actions(result, plan)

    # Agent review / debug data
    review = getattr(plan, "review", None)
    if review:
        resp["review"] = review
    debug_analysis = getattr(plan, "debug_analysis", None)
    if debug_analysis:
        resp["debug_analysis"] = debug_analysis
    decision_trace = getattr(plan, "decision_trace", None)
    if decision_trace:
        resp["decision_trace"] = decision_trace

    return resp


@app.post("/plans/{plan_id}/validate")
async def validate_plan_endpoint(request: Request, plan_id: str):
    _require_scope(request, "execute")
    from umh.planning.planner import get_plan
    from umh.planning.validator import validate_plan

    plan = get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    result = validate_plan(plan)
    return result.to_dict()


# ── Events ──────────────────────────────────────────────────────────


@app.get("/events")
async def list_events(request: Request, limit: int = 100):
    _require_scope(request, "metrics:read")
    stream = get_event_stream()
    events = stream.list_events(limit=min(limit, 1000))
    return [e.to_dict() for e in events]


@app.get("/events/stream")
async def stream_events(request: Request):
    _require_scope(request, "metrics:read")

    import asyncio
    import json
    import queue

    q: queue.Queue = queue.Queue()

    def on_event(event):
        q.put(event)

    stream = get_event_stream()
    stream.subscribe(on_event)

    async def event_generator():
        try:
            idle_ticks = 0
            while True:
                try:
                    event = q.get_nowait()
                    idle_ticks = 0
                    yield f"data: {json.dumps(event.to_dict())}\n\n"
                except queue.Empty:
                    idle_ticks += 1
                    if idle_ticks % 50 == 0:
                        yield ": keepalive\n\n"
                    await asyncio.sleep(0.1)
        finally:
            stream.unsubscribe(on_event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── Tools ──────────────────────────────────────────────────────────


@app.get("/tools")
async def list_tools_endpoint(request: Request):
    """List all registered tools."""
    _require_scope(request, "execute")
    from umh.tools.registry import list_tools

    return [
        {
            "name": t.name,
            "operation": t.operation,
            "description": t.description,
            "required_inputs": list(t.required_inputs),
            "optional_inputs": list(t.optional_inputs),
            "mutating": t.mutating,
            "timeout_s": t.timeout_s,
        }
        for t in list_tools()
    ]


@app.get("/tools/{tool_name}")
async def get_tool_endpoint(request: Request, tool_name: str):
    """Get a single tool definition by name."""
    _require_scope(request, "execute")
    from umh.tools.registry import get_tool

    tool = get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return {
        "name": tool.name,
        "operation": tool.operation,
        "description": tool.description,
        "required_inputs": list(tool.required_inputs),
        "optional_inputs": list(tool.optional_inputs),
        "mutating": tool.mutating,
        "timeout_s": tool.timeout_s,
        "execution_class": tool.execution_class,
    }


class ToolExecuteBody(BaseModel):
    inputs: dict = Field(default_factory=dict)


@app.post("/tools/{tool_name}/execute")
async def execute_tool_endpoint(request: Request, tool_name: str, body: ToolExecuteBody):
    """Execute a tool by name, routing through the full execution engine."""
    identity = _require_scope(request, "execute")
    from umh.tools.registry import get_tool

    tool = get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    exec_id = f"tool_{uuid.uuid4().hex[:16]}"
    tool_inputs = {
        **body.inputs,
        "tool_name": tool_name,
        "method": body.inputs.get("method", "GET"),
    }

    exec_request = ExecutionRequest(
        execution_id=exec_id,
        correlation_id=exec_id,
        causal_event_id="",
        session_id="",
        operation=tool.operation,
        inputs=tool_inputs,
        execution_class=ExecutionClass(tool.execution_class),
        constraints=ExecutionConstraints(timeout_s=tool.timeout_s),
        target=ExecutionTarget(node_id="local", transport="api"),
        context=ExecutionContext(metadata={"actor_id": identity.id, "tool_name": tool_name}),
        issued_at=_iso_now(),
        issued_by=identity.id,
        idempotency_key="",
    )
    result = execute(exec_request)
    return result.to_dict()


# ── Memory ─────────────────────────────────────────────────────────


class CreateMemoryBody(BaseModel):
    type: str
    content: str
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


@app.post("/memory")
async def create_memory_endpoint(request: Request, body: CreateMemoryBody):
    _require_scope(request, "memory:write")
    from umh.memory.persistent_store import VALID_MEMORY_TYPES, get_memory_store

    if not body.content or not body.content.strip():
        return _error_response(400, "validation_error", "content is required")
    if body.type not in VALID_MEMORY_TYPES:
        return _error_response(
            400,
            "validation_error",
            f"Invalid memory type '{body.type}'. Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}",
        )

    store = get_memory_store()
    memory = store.save_memory(
        type=body.type,
        content=body.content.strip(),
        metadata=body.metadata or None,
        tags=body.tags,
    )
    return {
        "id": memory.id,
        "type": memory.type,
        "content": memory.content,
        "metadata": memory.metadata,
        "tags": memory.tags,
        "created_at": memory.created_at,
    }


@app.get("/memory")
async def list_memories_endpoint(request: Request, type: str | None = None, limit: int = 50):
    _require_scope(request, "memory:read")
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    memories = store.list_memories(type=type, limit=min(limit, 500))
    return [
        {
            "id": m.id,
            "type": m.type,
            "content": m.content,
            "metadata": m.metadata,
            "tags": m.tags,
            "created_at": m.created_at,
        }
        for m in memories
    ]


@app.get("/memory/search")
async def search_memories_endpoint(request: Request, q: str | None = None, limit: int = 10):
    _require_scope(request, "memory:read")
    if not q or not q.strip():
        return _error_response(400, "validation_error", "Query parameter 'q' is required")

    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    memories = store.search_memories(q.strip(), limit=min(limit, 100))
    return [
        {
            "id": m.id,
            "type": m.type,
            "content": m.content,
            "metadata": m.metadata,
            "tags": m.tags,
            "created_at": m.created_at,
        }
        for m in memories
    ]


@app.delete("/memory/{memory_id}")
async def delete_memory_endpoint(request: Request, memory_id: str):
    _require_scope(request, "memory:write")
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    deleted = store.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory not found: {memory_id}")
    return {"deleted": memory_id}


@app.get("/memory/stats")
async def memory_stats_endpoint(request: Request):
    _require_scope(request, "memory:read")
    from umh.memory.persistent_store import get_memory_store

    store = get_memory_store()
    total = store.count_memories()

    # Count by type
    by_type: dict[str, int] = {}
    all_memories = store.list_memories(limit=10000)
    for m in all_memories:
        by_type[m.type] = by_type.get(m.type, 0) + 1

    return {"total_memories": total, "by_type": by_type}


# ── Schedules ─────────────────────────────────────────────────────


class CreateScheduleBody(BaseModel):
    name: str
    objective: str
    schedule_type: str = "interval"  # interval, daily, weekly, cron_like
    schedule_value: str = "60"  # minutes for interval, "09:00" for daily, etc.
    policy: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


@app.get("/schedules")
async def list_schedules_endpoint(request: Request):
    _require_scope(request, "execute")
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    return [w.to_dict() for w in store.list_all()]


@app.post("/schedules")
async def create_schedule_endpoint(request: Request, body: CreateScheduleBody):
    identity = _require_scope(request, "execute")
    from umh.scheduler.models import SchedulePolicy, ScheduleType, ScheduledWorkflow
    from umh.scheduler.store import get_schedule_store

    try:
        stype = ScheduleType(body.schedule_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid schedule_type: {body.schedule_type}")

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if not body.objective or not body.objective.strip():
        raise HTTPException(status_code=400, detail="objective is required")

    policy = SchedulePolicy()
    if body.policy:
        for key in [
            "require_approval_before_run",
            "allowed_capabilities",
            "max_runs_per_day",
            "max_cost_usd",
            "dry_run_only",
            "auto_execute_safe_tasks_only",
        ]:
            if key in body.policy:
                setattr(policy, key, body.policy[key])

    workflow = ScheduledWorkflow(
        name=body.name.strip(),
        objective=body.objective.strip(),
        schedule_type=stype,
        schedule_value=body.schedule_value,
        policy=policy,
        metadata=body.metadata,
        created_by=identity.id,
    )

    store = get_schedule_store()
    store.create(workflow)

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "schedule.created",
        payload={
            "schedule_id": workflow.id,
            "name": workflow.name,
            "schedule_type": stype.value,
        },
        actor_id=identity.id,
    )

    return JSONResponse(status_code=201, content=workflow.to_dict())


@app.get("/schedules/{schedule_id}")
async def get_schedule_endpoint(request: Request, schedule_id: str):
    _require_scope(request, "execute")
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflow = store.get(schedule_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return workflow.to_dict()


@app.post("/schedules/{schedule_id}/enable")
async def enable_schedule_endpoint(request: Request, schedule_id: str):
    identity = _require_scope(request, "execute")
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflow = store.enable(schedule_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "schedule.enabled",
        payload={
            "schedule_id": schedule_id,
        },
        actor_id=identity.id,
    )

    return workflow.to_dict()


@app.post("/schedules/{schedule_id}/disable")
async def disable_schedule_endpoint(request: Request, schedule_id: str):
    identity = _require_scope(request, "execute")
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()
    workflow = store.disable(schedule_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "schedule.disabled",
        payload={
            "schedule_id": schedule_id,
        },
        actor_id=identity.id,
    )

    return workflow.to_dict()


@app.post("/schedules/{schedule_id}/run-now")
async def run_now_endpoint(request: Request, schedule_id: str):
    identity = _require_scope(request, "execute")
    from umh.scheduler.runner import get_scheduler_runner

    runner = get_scheduler_runner()

    try:
        result = runner.run_now(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.delete("/schedules/{schedule_id}")
async def delete_schedule_endpoint(request: Request, schedule_id: str):
    identity = _require_scope(request, "execute")
    from umh.scheduler.store import get_schedule_store

    store = get_schedule_store()

    if not store.delete(schedule_id):
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "schedule.deleted",
        payload={
            "schedule_id": schedule_id,
        },
        actor_id=identity.id,
    )

    return {"deleted": schedule_id}


# ── Goals ─────────────────────────────────────────────────────────


class CreateGoalBody(BaseModel):
    name: str
    objective: str
    priority: str = "medium"
    success_criteria: list[str] = Field(default_factory=list)
    constraints: dict = Field(default_factory=dict)
    policy: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


@app.get("/goals")
async def list_goals_endpoint(request: Request):
    _require_scope(request, "execute")
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    return [g.to_dict() for g in store.list_all()]


@app.post("/goals")
async def create_goal_endpoint(request: Request, body: CreateGoalBody):
    identity = _require_scope(request, "execute")
    from umh.goals.models import Goal, GoalPolicy, GoalPriority

    try:
        priority = GoalPriority(body.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {body.priority}")

    policy = GoalPolicy()
    if body.policy:
        for key in vars(policy):
            if key in body.policy:
                setattr(policy, key, body.policy[key])

    goal = Goal(
        name=body.name,
        objective=body.objective,
        priority=priority,
        success_criteria=body.success_criteria,
        constraints=body.constraints,
        policy=policy,
        metadata=body.metadata,
        created_by=identity.id,
    )

    from umh.goals.store import get_goal_store

    store = get_goal_store()
    store.create(goal)

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "goal.created",
        payload={
            "goal_id": goal.id,
            "name": goal.name,
            "priority": priority.value,
        },
        actor_id=identity.id,
    )

    return JSONResponse(status_code=201, content=goal.to_dict())


@app.get("/goals/{goal_id}")
async def get_goal_endpoint(request: Request, goal_id: str):
    _require_scope(request, "read")
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    data = goal.to_dict()

    from umh.strategy.decomposer import get_cached_strategy

    strategy = get_cached_strategy(goal_id)
    if strategy is not None:
        data["strategy"] = strategy.to_dict()

    from umh.strategy.history import get_strategy_history
    from umh.strategy.refiner import get_proposal

    hist = get_strategy_history(goal_id)
    if hist.version_count() > 0:
        data["strategy_history"] = hist.to_dict()

    proposal = get_proposal(goal_id)
    if proposal is not None:
        data["refinement_proposal"] = proposal.to_dict()

    return data


@app.post("/goals/{goal_id}/pause")
async def pause_goal_endpoint(request: Request, goal_id: str):
    identity = _require_scope(request, "execute")
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.pause(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "goal.paused",
        payload={"goal_id": goal_id},
        actor_id=identity.id,
    )

    return goal.to_dict()


@app.post("/goals/{goal_id}/resume")
async def resume_goal_endpoint(request: Request, goal_id: str):
    identity = _require_scope(request, "execute")
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.resume(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "goal.resumed",
        payload={"goal_id": goal_id},
        actor_id=identity.id,
    )

    return goal.to_dict()


@app.post("/goals/{goal_id}/evaluate")
async def evaluate_goal_endpoint(request: Request, goal_id: str):
    _require_scope(request, "execute")
    from umh.goals.goal_engine import get_goal_engine

    engine = get_goal_engine()
    result = engine.evaluate_now(goal_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")
    return result


@app.post("/goals/{goal_id}/strategy")
async def goal_strategy_endpoint(request: Request, goal_id: str):
    _require_scope(request, "execute")
    from umh.goals.store import get_goal_store
    from umh.strategy.decomposer import (
        cache_strategy,
        decompose_goal,
        get_cached_strategy,
        invalidate_strategy,
    )

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    # Force recompute
    invalidate_strategy(goal_id)
    strategy = decompose_goal(goal)
    cache_strategy(strategy)

    return strategy.to_dict()


@app.get("/goals/{goal_id}/strategy")
async def get_goal_strategy_endpoint(request: Request, goal_id: str):
    _require_scope(request, "read")
    from umh.goals.store import get_goal_store
    from umh.strategy.decomposer import get_cached_strategy

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    strategy = get_cached_strategy(goal_id)
    if strategy is None:
        return {
            "strategy": None,
            "message": "No strategy computed yet. POST to /goals/{id}/strategy to generate.",
        }

    return strategy.to_dict()


@app.post("/goals/{goal_id}/priority")
async def set_goal_priority(request: Request, goal_id: str):
    identity = _require_scope(request, "execute")
    body = await request.json()
    priority_value = body.get("priority", "medium")
    from umh.goals.models import GoalPriority
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        return JSONResponse({"error": "goal not found"}, status_code=404)
    try:
        goal.priority = GoalPriority(priority_value)
        goal.updated_at = _iso_now()
    except ValueError:
        return JSONResponse({"error": f"invalid priority: {priority_value}"}, status_code=400)
    return {"goal_id": goal_id, "priority": goal.priority.value}


@app.post("/goals/{goal_id}/refine")
async def refine_goal_strategy_endpoint(request: Request, goal_id: str):
    _require_scope(request, "execute")
    from umh.goals.store import get_goal_store
    from umh.strategy.refiner import refine_strategy, store_proposal

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    proposal = refine_strategy(goal_id)
    if proposal is None:
        return {"message": "No refinement needed or insufficient data", "goal_id": goal_id}

    store_proposal(proposal)
    return proposal.to_dict()


@app.post("/goals/{goal_id}/apply_refinement")
async def apply_refinement_endpoint(request: Request, goal_id: str):
    identity = _require_scope(request, "execute")
    from umh.goals.store import get_goal_store
    from umh.strategy.decomposer import cache_strategy, invalidate_strategy
    from umh.strategy.history import record_strategy_version
    from umh.strategy.refiner import clear_proposal, get_proposal

    store = get_goal_store()
    goal = store.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    proposal = get_proposal(goal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="No refinement proposal available")

    if proposal.new_strategy is None:
        raise HTTPException(status_code=400, detail="Proposal has no new strategy")

    new_strategy = proposal.new_strategy
    invalidate_strategy(goal_id)
    cache_strategy(new_strategy)
    record_strategy_version(goal_id, new_strategy)
    clear_proposal(goal_id)

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "strategy.refinement_applied",
        payload={
            "goal_id": goal_id,
            "proposal_id": proposal.id,
            "new_strategy_id": new_strategy.id,
        },
        actor_id=identity.id,
    )

    return {
        "applied": True,
        "goal_id": goal_id,
        "new_strategy": new_strategy.to_dict(),
    }


@app.delete("/goals/{goal_id}")
async def delete_goal_endpoint(request: Request, goal_id: str):
    identity = _require_scope(request, "execute")
    from umh.goals.store import get_goal_store

    store = get_goal_store()
    if not store.delete(goal_id):
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}")

    from umh.events.stream import publish as _publish_event

    _publish_event(
        "goal.deleted",
        payload={"goal_id": goal_id},
        actor_id=identity.id,
    )

    return {"deleted": goal_id}


# ── Brains ─────────────────────────────────────────────────────────


@app.get("/brains")
def api_list_brains():
    from umh.brains.registry import list_all

    profiles = list_all()
    return {"brains": [p.to_dict() for p in profiles], "count": len(profiles)}


@app.get("/brains/{brain_id}")
def api_get_brain(brain_id: str):
    from umh.brains.registry import get, resolve_with_inheritance

    profile = get(brain_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found")

    resolved = resolve_with_inheritance(brain_id)
    return {
        "profile": profile.to_dict(),
        "resolved": resolved.to_dict() if resolved else None,
    }


@app.get("/brains/{brain_id}/expression")
def api_get_brain_expression(brain_id: str):
    from umh.brains.registry import get, get_expression

    if get(brain_id) is None:
        raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found")

    state = get_expression(brain_id)
    return {"expression": state.to_dict() if state else None}


@app.get("/brains/{brain_id}/children")
def api_get_brain_children(brain_id: str):
    from umh.brains.registry import children

    kids = children(brain_id)
    return {"children": [p.to_dict() for p in kids], "count": len(kids)}


@app.get("/brain-signals")
def api_list_brain_signals(
    brain_id: str | None = None,
    signal_type: str | None = None,
    limit: int = 50,
):
    from umh.brains.signals import list_all_signals, list_signals

    if brain_id:
        signals = list_signals(brain_id, signal_type=signal_type, limit=limit)
    else:
        signals = list_all_signals(signal_type=signal_type, limit=limit)
    return {"signals": [s.to_dict() for s in signals], "count": len(signals)}


@app.post("/brains/{brain_id}/correct")
def api_apply_brain_correction(brain_id: str, correction: dict):
    from umh.brains.registry import apply_correction

    ok = apply_correction(brain_id, correction)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found")
    return {"applied": True, "brain_id": brain_id}


# ── Phase 79: Observability Endpoints (read-only) ─────────────────


@app.get("/observability/status")
async def observability_system_status(request: Request):
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.system_status import build_system_status

    user_id = getattr(request.state, "identity_id", "")
    status = build_system_status(
        user_id=user_id,
        trace_store=get_trace_store(),
        feedback_store=get_feedback_store(),
    )
    return status.to_dict()


@app.get("/observability/dashboard")
async def observability_dashboard(request: Request, limit: int = 25):
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.operator_views import build_operator_dashboard_snapshot

    user_id = getattr(request.state, "identity_id", "")
    snapshot = build_operator_dashboard_snapshot(
        user_id=user_id,
        trace_store=get_trace_store(),
        feedback_store=get_feedback_store(),
        limit=min(limit, 100),
    )
    return snapshot.to_dict()


@app.get("/observability/timeline")
async def observability_timeline(request: Request, limit: int = 50):
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.timeline import build_timeline

    ts = get_trace_store()
    fs = get_feedback_store()
    traces = ts.list_traces(limit=min(limit, 100))
    outcomes = fs.list_outcomes(limit=min(limit, 100))
    feedback = fs.list_feedback(limit=min(limit, 100))
    tl = build_timeline(traces=traces, outcomes=outcomes, feedback=feedback, limit=limit)
    return tl.to_dict()


@app.get("/observability/traces")
async def observability_traces(
    request: Request,
    user_id: str | None = None,
    status: str | None = None,
    limit: int = 25,
):
    from umh.control.trace_store import get_trace_store
    from umh.observability.trace_query import TraceQuery, query_traces

    q = TraceQuery(
        user_id=user_id or "",
        status=status or "",
        limit=min(limit, 100),
    )
    result = query_traces(get_trace_store(), q)
    return result.to_dict()


@app.get("/observability/traces/{trace_id}")
async def observability_trace_detail(request: Request, trace_id: str, include_raw: bool = False):
    from umh.control.trace_store import get_trace_store
    from umh.observability.trace_query import get_trace_view

    view = get_trace_view(get_trace_store(), trace_id, include_raw=include_raw)
    if view is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return view.to_dict()


@app.get("/observability/traces/{trace_id}/explain")
async def observability_explain_trace(request: Request, trace_id: str):
    from umh.control.trace_store import get_trace_store
    from umh.observability.decision_explainer import explain_trace

    ts = get_trace_store()
    trace = ts.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    explanation = explain_trace(trace)
    return explanation.to_dict()


@app.get("/observability/failures")
async def observability_failures(
    request: Request,
    category: str | None = None,
    limit: int = 25,
):
    from umh.feedback.store import get_feedback_store
    from umh.observability.failure_search import FailureSearchQuery, search_failures

    fs = get_feedback_store()
    outcomes = fs.list_outcomes(limit=min(limit, 100))
    q = FailureSearchQuery(category=category or "", limit=min(limit, 100))
    result = search_failures(outcomes=outcomes, query=q)
    return result.to_dict()


@app.get("/observability/executions/summary")
async def observability_execution_summary(request: Request, limit: int = 100):
    from umh.control.trace_store import get_trace_store
    from umh.feedback.store import get_feedback_store
    from umh.observability.execution_summary import summarize_executions

    traces = get_trace_store().list_traces(limit=min(limit, 100))
    outcomes = get_feedback_store().list_outcomes(limit=min(limit, 100))
    summary = summarize_executions(traces=traces, outcomes=outcomes, limit=limit)
    return summary.to_dict()


# ── Phase 80: Registry Endpoints (read-only) ──────────────────────


@app.get("/registry/catalog")
async def registry_catalog(request: Request):
    from umh.registry.catalog import build_default_registry_catalog

    catalog = build_default_registry_catalog()
    return catalog.to_dict()


@app.get("/registry/overview")
async def registry_overview(request: Request):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import build_catalog_view

    catalog = build_default_registry_catalog()
    return build_catalog_view(catalog).to_dict()


@app.get("/registry/health")
async def registry_health(request: Request):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import build_registry_health_view

    catalog = build_default_registry_catalog()
    return build_registry_health_view(catalog).to_dict()


@app.get("/registry/query")
async def registry_query_endpoint(
    request: Request,
    type: str = "",
    name: str = "",
    capability: str = "",
    environment: str = "",
    tag: str = "",
    status: str = "",
    risk_level: str = "",
    limit: int = 50,
):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.contracts import RegistryQuery
    from umh.registry.query import query_registry

    catalog = build_default_registry_catalog()
    q = RegistryQuery(
        registry_type=type,
        name=name,
        capability=capability,
        environment=environment,
        tag=tag,
        status=status,
        risk_level=risk_level,
        limit=min(limit, 100),
    )
    return query_registry(catalog, q).to_dict()


@app.get("/registry/items/{item_id}")
async def registry_item_detail(request: Request, item_id: str):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    item = catalog.by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Registry item not found: {item_id}")
    return registry_item_to_view(item).to_dict()


@app.get("/registry/capabilities")
async def registry_capabilities(
    request: Request, environment: str = "", risk_level: str = "", limit: int = 50
):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_capabilities
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_capabilities(catalog, environment=environment, risk_level=risk_level, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


@app.get("/registry/adapters")
async def registry_adapters(
    request: Request, capability: str = "", environment: str = "", limit: int = 50
):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_adapters
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_adapters(catalog, capability=capability, environment=environment, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


@app.get("/registry/backends")
async def registry_backends(request: Request, environment: str = "", limit: int = 50):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_backends
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_backends(catalog, environment=environment, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


@app.get("/registry/environments")
async def registry_environments(request: Request, capability: str = "", limit: int = 50):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_environments
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_environments(catalog, capability=capability, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


@app.get("/registry/modes")
async def registry_modes(request: Request, limit: int = 50):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_workstation_modes
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_workstation_modes(catalog, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


@app.get("/registry/policies")
async def registry_policies(request: Request, limit: int = 50):
    from umh.registry.catalog import build_default_registry_catalog
    from umh.registry.query import find_policies
    from umh.registry.views import registry_item_to_view

    catalog = build_default_registry_catalog()
    items = find_policies(catalog, limit=limit)
    return [registry_item_to_view(i).to_dict() for i in items]


# ── Phase 81: Ontology Endpoints (read-only) ──────────────────────


@app.get("/ontology")
async def ontology_kernel_view(request: Request):
    from umh.ontology.correspondence import get_correspondence_maps
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.laws import get_laws
    from umh.ontology.primitives import get_primitives
    from umh.ontology.validation import validate_ontology_kernel
    from umh.ontology.views import build_ontology_kernel_view

    prims = get_primitives()
    laws = get_laws()
    projs = get_domain_projections()
    corrs = get_correspondence_maps()
    vr = validate_ontology_kernel(prims, laws, projs)
    return build_ontology_kernel_view(prims, laws, projs, corrs, vr).to_dict()


@app.get("/ontology/primitives")
async def ontology_primitives(request: Request):
    from umh.ontology.primitives import get_primitives

    return [p.to_dict() for p in get_primitives()]


@app.get("/ontology/primitives/{primitive_id}")
async def ontology_primitive_detail(request: Request, primitive_id: str):
    from umh.ontology.primitives import get_primitive_by_id

    p = get_primitive_by_id(primitive_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Primitive not found: {primitive_id}")
    return p.to_dict()


@app.get("/ontology/laws")
async def ontology_laws(request: Request):
    from umh.ontology.laws import get_laws

    return [l.to_dict() for l in get_laws()]


@app.get("/ontology/laws/{law_id}")
async def ontology_law_detail(request: Request, law_id: str):
    from umh.ontology.laws import get_law_by_id

    l = get_law_by_id(law_id)
    if l is None:
        raise HTTPException(status_code=404, detail=f"Law not found: {law_id}")
    return l.to_dict()


@app.get("/ontology/domain-projections")
async def ontology_domain_projections(request: Request):
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.views import domain_projection_to_view

    return [domain_projection_to_view(ps).to_dict() for ps in get_domain_projections()]


@app.get("/ontology/correspondence")
async def ontology_correspondence(request: Request):
    from umh.ontology.correspondence import get_correspondence_maps
    from umh.ontology.views import correspondence_to_view

    return [correspondence_to_view(cm).to_dict() for cm in get_correspondence_maps()]


@app.get("/ontology/validate")
async def ontology_validate(request: Request):
    from umh.ontology.domain_projection import get_domain_projections
    from umh.ontology.laws import get_laws
    from umh.ontology.primitives import get_primitives
    from umh.ontology.validation import validate_ontology_kernel

    prims = get_primitives()
    laws = get_laws()
    projs = get_domain_projections()
    return validate_ontology_kernel(prims, laws, projs).to_dict()


# ── Unity / Polarity Synthesis (Phase 84A) ────────────────────────


@app.get("/ontology/laws/unity-oneness")
async def ontology_unity_oneness(request: Request):
    from umh.ontology.laws import get_law_by_id

    law = get_law_by_id("law_unity_oneness")
    if law is None:
        return {"error": "Unity / Oneness law not found"}
    return law.to_dict()


class PolaritySynthesisValidateBody(BaseModel):
    pole_a_label: str = ""
    pole_a_truth: str = ""
    pole_a_value: str = ""
    pole_a_risk: str = ""
    pole_b_label: str = ""
    pole_b_truth: str = ""
    pole_b_value: str = ""
    pole_b_risk: str = ""
    shared_context: str = ""
    contradiction_layer: str = ""


@app.post("/ontology/polarity-synthesis/validate")
async def ontology_polarity_synthesis_validate(
    request: Request, body: PolaritySynthesisValidateBody
):
    from umh.ontology.polarity_synthesis import (
        create_polarity_pair,
        create_polarity_pole,
        synthesize_polarity,
    )

    pa = create_polarity_pole(
        body.pole_a_label,
        truth_claim=body.pole_a_truth,
        value_preserved=body.pole_a_value,
        risk_if_dominant=body.pole_a_risk,
    )
    pb = create_polarity_pole(
        body.pole_b_label,
        truth_claim=body.pole_b_truth,
        value_preserved=body.pole_b_value,
        risk_if_dominant=body.pole_b_risk,
    )
    pair = create_polarity_pair(
        pa, pb, shared_context=body.shared_context, contradiction_layer=body.contradiction_layer
    )
    result = synthesize_polarity(pair)
    return result.to_dict()


# ── Storage + Memory Discipline (Phase 82) ────────────────────────


@app.get("/storage/status")
async def storage_status(request: Request):
    from umh.storage.gateway import StorageGateway
    from umh.storage.views import build_storage_health_view

    gw = StorageGateway()
    descs = gw.list_descriptors(limit=500)
    view = build_storage_health_view(descs, backend_names=sorted(gw.backends.keys()))
    return view.to_dict()


@app.get("/storage/descriptors")
async def storage_descriptors(request: Request, record_type: str = "", limit: int = 50):
    from umh.storage.gateway import StorageGateway
    from umh.storage.contracts import (
        StorageRecordType,
        normalize_storage_record_type as normalize_record_type,
    )
    from umh.storage.views import build_descriptor_view

    gw = StorageGateway()
    rt = normalize_record_type(record_type) if record_type else None
    if rt == StorageRecordType.UNKNOWN and record_type:
        rt = None
    descs = gw.list_descriptors(record_type=rt, limit=limit)
    return [build_descriptor_view(d).to_dict() for d in descs]


@app.get("/storage/audit")
async def storage_audit_endpoint(request: Request, include_tests: bool = False):
    from umh.storage.audit import audit_storage_boundaries
    from umh.storage.views import build_storage_audit_view

    report = audit_storage_boundaries(include_tests=include_tests)
    return build_storage_audit_view(report).to_dict()


@app.get("/storage/policy")
async def storage_policy_endpoint(request: Request):
    from umh.storage.policy import build_default_storage_policy

    return build_default_storage_policy().to_dict()


@app.get("/memory/discipline/status")
async def memory_discipline_status(request: Request):
    from umh.memory.discipline import build_default_memory_write_policy
    from umh.memory.views import build_memory_discipline_health_view

    view = build_memory_discipline_health_view()
    return view.to_dict()


@app.get("/memory/discipline/policy")
async def memory_discipline_policy(request: Request):
    from umh.memory.discipline import build_default_memory_write_policy

    return build_default_memory_write_policy().to_dict()


@app.get("/memory/discipline/promotion-policy")
async def memory_promotion_policy(request: Request):
    from umh.memory.discipline import build_default_memory_write_policy

    policy = build_default_memory_write_policy()
    return {
        "allow_auto_promotion": policy.allow_auto_promotion,
        "min_confidence": policy.min_confidence,
        "requires_evidence": policy.requires_evidence,
        "status": "disabled" if not policy.allow_auto_promotion else "enabled",
    }


# ── Migration + Legacy Deprecation (Phase 83) ──────────────────────


@app.get("/migration/status")
async def migration_status(request: Request):
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import build_migration_health_view

    registry = build_default_deprecation_registry()
    view = build_migration_health_view(registry)
    return view.to_dict()


@app.get("/migration/inventory")
async def migration_inventory(request: Request, limit: int = 100):
    from umh.migration.inventory import build_legacy_inventory, summarize_inventory

    inv = build_legacy_inventory()
    summary = summarize_inventory(inv.records)
    records = [r.to_dict() for r in inv.records[:limit]]
    return {"summary": summary, "records": records, "warnings": inv.warnings}


@app.get("/migration/deprecated")
async def migration_deprecated(request: Request, limit: int = 100):
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import legacy_module_to_view

    registry = build_default_deprecation_registry()
    deprecated = registry.list_deprecated(limit=limit)
    return [legacy_module_to_view(r).to_dict() for r in deprecated]


@app.get("/migration/bypass-risk")
async def migration_bypass_risk(request: Request, limit: int = 100):
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.views import legacy_module_to_view

    registry = build_default_deprecation_registry()
    risks = registry.list_bypass_risk(limit=limit)
    return [legacy_module_to_view(r).to_dict() for r in risks]


@app.get("/migration/mappings")
async def migration_mappings(request: Request, limit: int = 100):
    from umh.migration.compatibility import get_known_clean_equivalents

    equivs = get_known_clean_equivalents()
    items = [{"legacy": k, "clean_equivalent": v} for k, v in list(equivs.items())[:limit]]
    return {"total": len(equivs), "mappings": items}


@app.get("/migration/import-boundary")
async def migration_import_boundary(request: Request, limit: int = 100):
    from umh.migration.import_boundary import (
        build_default_import_boundary_rules,
        import_boundary_findings_to_report,
        scan_import_boundaries,
    )

    rules = build_default_import_boundary_rules()
    findings = scan_import_boundaries(rules=rules)
    report = import_boundary_findings_to_report(findings[:limit])
    return report


@app.get("/migration/dashboard")
async def migration_dashboard(request: Request, limit: int = 100):
    from umh.migration.deprecation_registry import build_default_deprecation_registry
    from umh.migration.import_boundary import scan_import_boundaries
    from umh.migration.views import build_migration_dashboard_view

    registry = build_default_deprecation_registry()
    findings = scan_import_boundaries()
    view = build_migration_dashboard_view(registry, findings, limit=limit)
    return view.to_dict()


# ── Interface Layer (Phase 84) ───────────────────────────────────────


@app.get("/interface/status")
async def interface_status(request: Request):
    from umh.interface.surface_registry import build_default_surface_registry
    from umh.interface.safety import validate_interface_module_boundaries

    reg = build_default_surface_registry()
    safety = validate_interface_module_boundaries()
    return {
        "surface_count": reg.surface_count,
        "safety": safety.to_dict(),
        "status": "ok" if safety.safe else "degraded",
    }


@app.get("/interface/surfaces")
async def interface_surfaces(request: Request, limit: int = 100):
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    surfaces = reg.list_surfaces(limit=limit)
    return [s.to_dict() for s in surfaces]


@app.get("/interface/surfaces/{surface_id}")
async def interface_surface_detail(surface_id: str, request: Request):
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    s = reg.get_surface(surface_id)
    if s is None:
        return {"error": f"Surface {surface_id} not found"}
    return s.to_dict()


@app.get("/interface/capability-matrix")
async def interface_capability_matrix(request: Request, limit: int = 100):
    from umh.interface.surface_registry import build_default_surface_registry

    reg = build_default_surface_registry()
    matrix = reg.build_capability_matrix(limit=limit)
    return [m.to_dict() for m in matrix]


@app.get("/interface/command-center")
async def interface_command_center(request: Request):
    from umh.interface.command_center import build_command_center_snapshot

    snapshot = build_command_center_snapshot()
    return snapshot.to_dict()


@app.get("/interface/voice-wave")
async def interface_voice_wave(request: Request):
    from umh.interface.voice_wave import VoiceWaveState, get_default_six_line_wave

    glyph = get_default_six_line_wave(VoiceWaveState.IDLE)
    return glyph.to_dict()


@app.get("/interface/notifications")
async def interface_notifications(request: Request):
    return {"notifications": [], "total": 0, "note": "Phase 84: display records only, no runtime"}


@app.get("/interface/approvals")
async def interface_approvals(request: Request):
    return {"approvals": [], "total": 0, "note": "Phase 84: display records only"}


@app.get("/interface/safety")
async def interface_safety(request: Request):
    from umh.interface.safety import validate_interface_module_boundaries

    result = validate_interface_module_boundaries()
    return result.to_dict()


class CommandValidateBody(BaseModel):
    surface_id: str = ""
    command_type: str = "unknown"
    raw_intent: str | None = None
    payload: dict = {}


@app.post("/interface/commands/validate")
async def interface_command_validate(body: CommandValidateBody, request: Request):
    from umh.interface.commands import (
        InterfaceCommandType,
        create_command_envelope,
        normalize_command_type,
        validate_interface_command,
    )

    ct = normalize_command_type(body.command_type)
    envelope = create_command_envelope(
        surface_id=body.surface_id,
        command_type=ct,
        raw_intent=body.raw_intent,
        payload=body.payload,
    )
    validation = validate_interface_command(envelope)
    return validation.to_dict()


# ── Deliberation Council (Phase 85) ─────────────────────────────────


@app.get("/council/status")
async def council_status(request: Request):
    from umh.council.views import build_council_health_view

    return build_council_health_view().to_dict()


@app.get("/council/roles")
async def council_roles(request: Request):
    from umh.council.roles import get_default_council_roles

    return [r.to_dict() for r in get_default_council_roles()]


class CouncilDeliberateBody(BaseModel):
    question: str = ""
    context: str = ""
    domain: str = "unknown"
    urgency: str = "medium"
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    relevant_laws: list[str] = Field(default_factory=list)
    relevant_polarities: list[str] = Field(default_factory=list)


@app.post("/council/deliberate")
async def council_deliberate(request: Request, body: CouncilDeliberateBody):
    from umh.council.contracts import ConfidenceLevel, EvidenceStrength
    from umh.council.deliberation import deliberate
    from umh.council.perspective import PerspectiveReport, create_perspective_report
    from umh.council.request import create_deliberation_request
    from umh.council.contracts import DeliberationDomain, UrgencyLevel, EvidenceItem

    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    dreq = create_deliberation_request(
        body.question,
        context=body.context,
        domain=DeliberationDomain(body.domain)
        if body.domain in [d.value for d in DeliberationDomain]
        else DeliberationDomain.UNKNOWN,
        urgency=UrgencyLevel(body.urgency)
        if body.urgency in [u.value for u in UrgencyLevel]
        else UrgencyLevel.MEDIUM,
        constraints=body.constraints,
        success_criteria=body.success_criteria,
        relevant_laws=body.relevant_laws,
        relevant_polarities=body.relevant_polarities,
    )

    from umh.council.roles import get_default_council_roles

    roles = get_default_council_roles()
    perspectives: list[PerspectiveReport] = []
    for role in roles:
        perspectives.append(
            create_perspective_report(
                dreq.request_id,
                role.role_id,
                position=f"Deterministic stub: {role.name} perspective on '{body.question[:60]}'",
                reasoning=f"Evaluated from {role.perspective_lens}",
                recommendation=f"Consider {role.name.lower()} implications",
                evidence=[
                    EvidenceItem(
                        evidence_id=f"ev_{role.role_id}",
                        claim=f"Relevant from {role.domain.value} domain",
                        strength=EvidenceStrength.MODERATE,
                        source=role.name,
                        domain=role.domain,
                        confidence=0.6,
                    )
                ],
                confidence=ConfidenceLevel.MEDIUM,
                score=0.6,
            )
        )

    advisory = deliberate(dreq, perspectives, roles=roles)
    return advisory.to_dict()


@app.get("/council/safety")
async def council_safety(request: Request):
    from umh.council.safety import validate_council_module_boundaries

    return validate_council_module_boundaries().to_dict()


# ── Static UI ──────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
import pathlib

_frontend_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_frontend_dir), html=True), name="ui")


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("UMH_API_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
