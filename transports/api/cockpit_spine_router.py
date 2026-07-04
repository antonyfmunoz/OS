"""Cockpit spine router — GovernedExecutionSpine, Journal, MutationRegistry,
SpineGuard endpoints.

Extracted from cockpit.py (Phase 6.2) to keep the main cockpit under 3000 lines.
All routes are mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency from cockpit.py and wires it into every
privileged route. Calling any route before configure() returns 503.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

spine_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_check_rate_limit: Callable[[str, str], None] = lambda action, client_id: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    check_rate_limit_fn: Callable[[str, str], None],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities and operator auth into the spine router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router so privileged routes carry the real auth dependency.
    """
    global _get_organism, _check_rate_limit, _configured, spine_router

    _get_organism = get_organism_fn
    _check_rate_limit = check_rate_limit_fn
    _configured = True

    # Register organism accessor in substrate socket port
    try:
        from substrate.sockets.organism_port import register_organism_accessor

        register_organism_accessor(get_organism_fn)
    except Exception:
        pass

    spine_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the spine router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints (no auth required) ─────────────────────────────

    r.add_api_route("/organism/spine", _spine_status, methods=["GET"])
    r.add_api_route("/organism/spine/pending", _spine_pending, methods=["GET"])
    r.add_api_route("/organism/spine/active", _spine_active, methods=["GET"])
    r.add_api_route("/organism/spine/completed", _spine_completed, methods=["GET"])
    r.add_api_route("/organism/spine/lifecycle/{envelope_id}", _spine_lifecycle, methods=["GET"])
    r.add_api_route("/organism/journal", _journal_status, methods=["GET"])
    r.add_api_route("/organism/journal/recent", _journal_recent, methods=["GET"])
    r.add_api_route(
        "/organism/journal/lifecycle/{envelope_id}", _journal_lifecycle, methods=["GET"]
    )
    r.add_api_route("/organism/journal/statistics", _journal_statistics, methods=["GET"])
    r.add_api_route("/organism/mutations", _mutation_registry, methods=["GET"])
    r.add_api_route("/organism/mutations/{mutation_name}", _mutation_detail, methods=["GET"])
    r.add_api_route("/organism/spine-guard", _spine_guard_status, methods=["GET"])
    r.add_api_route("/organism/spine-guard/blocked", _spine_guard_blocked, methods=["GET"])
    r.add_api_route("/organism/execution-doctrine", _execution_doctrine, methods=["GET"])
    r.add_api_route("/organism/reliability", _reliability_metrics, methods=["GET"])
    r.add_api_route("/organism/reliability-history", _reliability_history, methods=["GET"])
    r.add_api_route("/organism/capability-compounding", _capability_compounding, methods=["GET"])
    r.add_api_route("/organism/adapter-health", _adapter_health, methods=["GET"])
    r.add_api_route("/organism/spine-analytics", _spine_analytics, methods=["GET"])
    r.add_api_route("/organism/projection-health", _projection_health, methods=["GET"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route(
        "/organism/spine/approve/{envelope_id}", _spine_approve, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/organism/spine/reject/{envelope_id}", _spine_reject, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/organism/spine/retry/{envelope_id}", _spine_retry, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/organism/spine-guard/mode", _spine_guard_set_mode, methods=["POST"], dependencies=auth
    )
    r.add_api_route(
        "/organism/autonomous-gateway/policy",
        _autonomous_gateway_set_policy,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/autonomous-gateway/threshold",
        _autonomous_gateway_set_threshold,
        methods=["POST"],
        dependencies=auth,
    )

    # ── Autonomous gateway read-only endpoints ────────────────────────────

    r.add_api_route("/organism/autonomous-gateway", _autonomous_gateway_status, methods=["GET"])
    r.add_api_route(
        "/organism/autonomous-gateway/decisions", _autonomous_gateway_decisions, methods=["GET"]
    )
    r.add_api_route(
        "/organism/autonomous-gateway/blocked", _autonomous_gateway_blocked, methods=["GET"]
    )
    r.add_api_route(
        "/organism/autonomous-gateway/pending", _autonomous_gateway_pending, methods=["GET"]
    )

    # ── Plan execution adapter endpoints ─────────────────────────────────

    r.add_api_route("/organism/execution-graph", _execution_graph_status, methods=["GET"])
    r.add_api_route("/organism/execution-graph/{plan_id}", _execution_graph_detail, methods=["GET"])
    r.add_api_route("/organism/execute-plan", _execute_plan, methods=["POST"], dependencies=auth)
    r.add_api_route(
        "/organism/execute-plan/{plan_id}/approve/{step_id}",
        _execute_plan_approve_step,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/organism/execute-plan/{plan_id}/pending", _execute_plan_pending, methods=["GET"]
    )

    # ── Projection registry endpoints ────────────────────────────────────

    r.add_api_route("/organism/projections", _projections_list, methods=["GET"])
    r.add_api_route("/organism/projections/drift", _projection_drift, methods=["GET"])
    r.add_api_route("/organism/projections/{projection_id}", _projection_detail, methods=["GET"])

    # ── Dev session + daily driver endpoints ─────────────────────────────

    r.add_api_route("/organism/dev-sessions", _dev_sessions, methods=["GET"])
    r.add_api_route("/organism/dev-sessions/active", _dev_sessions_active, methods=["GET"])
    r.add_api_route("/organism/daily-driver", _daily_driver_summary, methods=["GET"])

    return r


# ── GovernedExecutionSpine handlers ────────────────────────────────────────────


async def _spine_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.to_dict()


async def _spine_pending(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.pending_envelopes(limit)


async def _spine_active():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.active_envelopes()


async def _spine_completed(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.governed_spine.completed_envelopes(limit)


async def _spine_lifecycle(envelope_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.governed_spine.envelope_lifecycle(envelope_id)


async def _spine_approve(envelope_id: str, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    def _do_approve():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        envelope = daemon.governed_spine.approve(envelope_id, approved_by=client_id)
        if envelope is None:
            return f"envelope {envelope_id} not found in pending queue", False
        return f"approved {envelope_id}", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"approve spine envelope {envelope_id}",
        execute_fn=_do_approve,
        source="cockpit",
        metadata={"envelope_id": envelope_id, "operator": client_id},
    )
    return resp.to_http_dict()


async def _spine_reject(envelope_id: str, payload: dict, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    reason = str(payload.get("reason", "operator_rejected"))[:500]

    def _do_reject():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        envelope = daemon.governed_spine.reject(envelope_id, reason=reason)
        if envelope is None:
            return f"envelope {envelope_id} not found in pending queue", False
        return f"rejected {envelope_id}: {reason}", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"reject spine envelope {envelope_id}: {reason[:100]}",
        execute_fn=_do_reject,
        source="cockpit",
        metadata={"envelope_id": envelope_id, "reason": reason, "operator": client_id},
    )
    return resp.to_http_dict()


async def _spine_retry(envelope_id: str, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    def _do_retry():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False

        completed = daemon.governed_spine.completed_envelopes(500)
        target = None
        for env_dict in completed:
            if env_dict.get("envelope_id") == envelope_id:
                target = env_dict
                break

        if target is None:
            return f"envelope {envelope_id} not found in completed queue", False

        if target.get("status") not in ("failed", "verification_failed", "rolled_back"):
            return (
                f"envelope {envelope_id} status is {target.get('status')} — only failed envelopes can be retried",
                False,
            )

        return f"retry acknowledged for {envelope_id}", True

    resp = governed_mutation(
        mutation_name="state_mutate",
        intent=f"retry spine envelope {envelope_id}",
        execute_fn=_do_retry,
        source="cockpit",
        metadata={"envelope_id": envelope_id, "operator": client_id},
    )
    return resp.to_http_dict()


# ── Execution Journal handlers ─────────────────────────────────────────────────


async def _journal_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.to_dict()


async def _journal_recent(limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return [e.to_dict() for e in daemon.execution_journal.recent(limit)]


async def _journal_lifecycle(envelope_id: str):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.execution_journal.execution_lifecycle(envelope_id)


async def _journal_statistics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.execution_journal.statistics()


# ── Mutation Registry handlers ─────────────────────────────────────────────────


async def _mutation_registry():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.mutation_registry.to_dict()


async def _mutation_detail(mutation_name: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    spec = daemon.mutation_registry.lookup(mutation_name)
    if spec is None:
        return {"error": f"mutation {mutation_name} not registered"}
    return spec.to_dict()


# ── SpineGuard handlers ───────────────────────────────────────────────────────


async def _spine_guard_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.spine_guard.to_dict(),
        "recent_violations": daemon.spine_guard.recent_violations(),
    }


async def _spine_guard_blocked(limit: int = 20):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.spine_guard.blocked_violations(limit)


async def _spine_guard_set_mode(payload: dict, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    from substrate.organism.spine_guard import GuardMode

    mode_str = str(payload.get("mode", "")).lower()
    valid_modes = {m.value: m for m in GuardMode}
    if mode_str not in valid_modes:
        return {
            "error": f"invalid mode: {mode_str}",
            "valid_modes": list(valid_modes.keys()),
        }

    new_mode = valid_modes[mode_str]

    def _do_set_mode():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        old_mode = daemon.spine_guard.mode
        daemon.spine_guard.set_mode(new_mode)
        return f"mode changed: {old_mode.value} → {new_mode.value}", True

    resp = governed_mutation(
        mutation_name="governance_update",
        intent=f"set spine guard mode to {mode_str}",
        execute_fn=_do_set_mode,
        source="cockpit",
        metadata={"mode": mode_str, "operator": client_id},
    )
    return resp.to_http_dict()


# ── Unified views ──────────────────────────────────────────────────────────────


async def _execution_doctrine():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    return {
        "execution_mode": daemon.execution_mode_manager.to_dict(),
        "spine": daemon.governed_spine.to_dict(),
        "spine_guard": daemon.spine_guard.to_dict(),
        "autonomous_gateway": daemon.autonomous_gateway.to_dict(),
        "journal_statistics": daemon.execution_journal.statistics(),
        "mutation_registry": {
            "total_specs": len(daemon.mutation_registry.all_specs()),
            "by_risk": {
                risk: len(daemon.mutation_registry.specs_by_risk(risk))
                for risk in ("low", "medium", "high", "critical")
            },
        },
    }


async def _reliability_metrics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    spine_stats = daemon.governed_spine.to_dict()
    journal_stats = daemon.execution_journal.statistics()
    learning_stats = daemon.outcome_learning.summary()

    return {
        "total_executed": spine_stats["total_executed"],
        "total_succeeded": spine_stats["total_succeeded"],
        "total_failed": spine_stats["total_failed"],
        "total_rejected": spine_stats["total_rejected"],
        "total_verified": spine_stats["total_verified"],
        "total_rolled_back": spine_stats["total_rolled_back"],
        "success_rate": spine_stats["success_rate"],
        "verification_rate": round(
            spine_stats["total_verified"] / max(spine_stats["total_succeeded"], 1), 4
        ),
        "rollback_rate": round(
            spine_stats["total_rolled_back"] / max(spine_stats["total_failed"], 1), 4
        ),
        "learning_loop_connected": spine_stats.get("learning_loop_connected", False),
        "learning": learning_stats,
        "journal": journal_stats,
        "spine_guard": daemon.spine_guard.to_dict(),
    }


async def _reliability_history():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.outcome_learning.reliability_history()


async def _capability_compounding():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.capability_compounding.snapshot().to_dict()


async def _adapter_health():
    """Cycle 2: Adapter health dashboard — maturity + capabilities across all adapters."""
    try:
        from adapters.adapter_engine.production_manifests import ALL_PRODUCTION_MANIFESTS
    except ImportError:
        return {"error": "production_manifests not available"}

    adapters = []
    for m in ALL_PRODUCTION_MANIFESTS:
        adapters.append(
            {
                "adapter_id": m.adapter_id,
                "adapter_type": m.adapter_type,
                "maturity": m.maturity.value if hasattr(m.maturity, "value") else str(m.maturity),
                "capabilities": [
                    {"id": c.capability_id, "action_type": c.action_type}
                    for c in (m.capabilities or [])
                ],
                "capability_count": len(m.capabilities or []),
                "version": m.version,
            }
        )

    maturity_counts: dict[str, int] = {}
    for a in adapters:
        mat = a["maturity"]
        maturity_counts[mat] = maturity_counts.get(mat, 0) + 1

    return {
        "total_adapters": len(adapters),
        "total_capabilities": sum(a["capability_count"] for a in adapters),
        "maturity_distribution": maturity_counts,
        "adapters": adapters,
    }


async def _spine_analytics():
    """Cycle 3: Spine execution analytics — success rate, duration, action types."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    journal = daemon.execution_journal
    entries = journal.recent(limit=1000)
    if not entries:
        return {"total_executions": 0, "analytics": {}}

    completed = [e for e in entries if e.phase.value == "execution_completed"]
    failed = [e for e in entries if e.phase.value == "execution_failed"]
    total = len(completed) + len(failed)
    success_rate = len(completed) / total if total > 0 else 0.0

    source_counts: dict[str, int] = {}
    durations: list[float] = []
    for e in entries:
        source_counts[e.source] = source_counts.get(e.source, 0) + 1
        elapsed = e.details.get("elapsed_ms") or e.details.get("duration_s")
        if elapsed is not None:
            durations.append(float(elapsed))

    avg_duration = sum(durations) / len(durations) if durations else 0.0

    action_types: dict[str, int] = {}
    for e in entries:
        at = e.details.get("type") or e.details.get("action_type") or "unknown"
        action_types[at] = action_types.get(at, 0) + 1

    return {
        "total_executions": total,
        "success_rate": round(success_rate, 4),
        "completed": len(completed),
        "failed": len(failed),
        "avg_duration_ms": round(avg_duration, 2),
        "source_distribution": source_counts,
        "action_type_distribution": action_types,
        "total_journal_entries": len(entries),
    }


async def _projection_health():
    """Cycle 4: Projection health — drift status + adapter coverage for all projections."""
    # WP-P3 read-side convergence: read the projection seed config through the
    # canonical ProjectionPort view instead of opening the registry JSON here.
    from substrate.sockets.projection_port import load_umh_projection_seed

    registry = load_umh_projection_seed()
    if not registry:
        return {"error": "projection registry unavailable"}

    try:
        from adapters.adapter_engine.production_manifests import ALL_PRODUCTION_MANIFESTS

        adapter_ids = {m.adapter_id for m in ALL_PRODUCTION_MANIFESTS}
        total_adapters = len(adapter_ids)
    except ImportError:
        adapter_ids = set()
        total_adapters = 0

    projections = []
    for pid, pdata in registry.items():
        projections.append(
            {
                "projection_id": pid,
                "app_name": pdata.get("app_name", ""),
                "health_url": pdata.get("health_url", ""),
                "public_url": pdata.get("public_url", ""),
                "has_l4_workflow": bool(pdata.get("l4_workflow")),
                "adapter_coverage": total_adapters,
            }
        )

    return {
        "total_projections": len(projections),
        "total_adapters_available": total_adapters,
        "projections": projections,
    }


# ── Autonomous Action Gateway handlers ───────────────────────────────────────


async def _autonomous_gateway_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.autonomous_gateway.to_dict()


async def _autonomous_gateway_decisions(limit: int = 20):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.autonomous_gateway.recent_decisions(limit)


async def _autonomous_gateway_blocked(limit: int = 20):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.autonomous_gateway.blocked_attempts(limit)


async def _autonomous_gateway_pending():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.autonomous_gateway.pending_autonomous_envelopes()


async def _autonomous_gateway_set_policy(payload: dict, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    from substrate.organism.autonomous_action_gateway import AutonomousPolicy

    policy_str = str(payload.get("policy", "")).lower()
    valid = {p.value: p for p in AutonomousPolicy}
    if policy_str not in valid:
        return {
            "error": f"invalid policy: {policy_str}",
            "valid_policies": list(valid.keys()),
        }

    new_policy = valid[policy_str]

    def _do_set_policy():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        old_policy = daemon.autonomous_gateway.policy
        daemon.autonomous_gateway.set_policy(new_policy)
        return f"policy changed: {old_policy.value} → {new_policy.value}", True

    resp = governed_mutation(
        mutation_name="governance_update",
        intent=f"set autonomous gateway policy to {policy_str}",
        execute_fn=_do_set_policy,
        source="cockpit",
        metadata={"policy": policy_str, "operator": client_id},
    )
    return resp.to_http_dict()


async def _autonomous_gateway_set_threshold(payload: dict, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    threshold = payload.get("threshold")
    if threshold is None or not isinstance(threshold, (int, float)):
        return {"error": "threshold must be a number between 0.0 and 1.0"}

    threshold = float(threshold)
    if not (0.0 <= threshold <= 1.0):
        return {"error": "threshold must be between 0.0 and 1.0"}

    def _do_set_threshold():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        daemon.autonomous_gateway.set_reliability_threshold(threshold)
        return f"threshold set to {threshold:.2f}", True

    resp = governed_mutation(
        mutation_name="settings_update",
        intent=f"set autonomous gateway reliability threshold to {threshold:.2f}",
        execute_fn=_do_set_threshold,
        source="cockpit",
        metadata={"threshold": threshold, "operator": client_id},
    )
    return resp.to_http_dict()


# ── Plan Execution Adapter handlers ──────────────────────────────────────────


async def _execution_graph_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.plan_execution_adapter.to_dict()


async def _execution_graph_detail(plan_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    plan = daemon.plan_execution_adapter.get_execution_graph(plan_id)
    if plan is None:
        return {"error": f"execution graph {plan_id} not found"}
    return plan.to_dict()


async def _execute_plan(payload: dict, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    intent = str(payload.get("intent", ""))
    if not intent:
        return {"error": "intent is required"}

    def _do_execute_plan():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False

        from substrate.organism.composition_engine import compose_plan

        composition_plan = compose_plan(intent)
        adapter = daemon.plan_execution_adapter
        executable = adapter.convert_plan(composition_plan)
        result = adapter.execute_plan(executable)
        return f"plan {result.id}: {result.status.value} ({len(result.steps)} steps)", True

    resp = governed_mutation(
        mutation_name="work_packet_create",
        intent=f"execute plan: {intent[:100]}",
        execute_fn=_do_execute_plan,
        source="cockpit",
        metadata={"intent": intent, "operator": client_id},
    )
    return resp.to_http_dict()


async def _execute_plan_approve_step(plan_id: str, step_id: str, request: Request):
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    def _do_approve_step():
        daemon = _get_organism()
        if daemon is None:
            return "organism not running", False
        adapter = daemon.plan_execution_adapter
        plan = adapter.get_execution_graph(plan_id)
        if plan is None:
            return f"execution graph {plan_id} not found", False
        step = adapter.approve_step(plan, step_id, approved_by=client_id)
        if step is None:
            return f"step {step_id} not found or not awaiting approval", False
        return f"step {step_id} approved → {step.status.value}", True

    resp = governed_mutation(
        mutation_name="approval_decide",
        intent=f"approve plan step {plan_id}/{step_id}",
        execute_fn=_do_approve_step,
        source="cockpit",
        metadata={"plan_id": plan_id, "step_id": step_id, "operator": client_id},
    )
    return resp.to_http_dict()


async def _execute_plan_pending(plan_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    adapter = daemon.plan_execution_adapter
    plan = adapter.get_execution_graph(plan_id)
    if plan is None:
        return {"error": f"execution graph {plan_id} not found"}

    pending = adapter.check_pending_approvals(plan)
    return [s.to_dict() for s in pending]


# ── Projection registry handlers ────────────────────────────────────────────


async def _projections_list():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.substrate_projection_port.summary()


async def _projection_detail(projection_id: str):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    reg = daemon.substrate_projection_port.get(projection_id)
    if reg is None:
        return {"error": f"projection '{projection_id}' not found"}
    return reg.to_dict()


async def _projection_drift():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.substrate_projection_port.audit_all()


# ── Dev session + daily driver handlers ──────────────────────────────────────


async def _dev_sessions():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.dev_session_tracker.to_dict()


async def _dev_sessions_active():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return [s.to_dict() for s in daemon.dev_session_tracker.active_sessions()]


async def _daily_driver_summary():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    spine_stats = daemon.governed_spine.to_dict()
    learning = daemon.outcome_learning.summary()
    cap = daemon.capability_compounding.snapshot().to_dict()
    projections = daemon.substrate_projection_port.summary()
    dev = daemon.dev_session_tracker.summary()
    return {
        "spine": {
            "total_executed": spine_stats.get("total_executed", 0),
            "success_rate": spine_stats.get("success_rate", 0),
            "pending_count": spine_stats.get("pending_count", 0),
        },
        "learning": learning,
        "capability_compounding": cap,
        "projections": projections,
        "dev_sessions": dev,
        "learning_loop_connected": spine_stats.get("learning_loop_connected", False),
    }
