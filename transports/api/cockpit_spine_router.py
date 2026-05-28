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

from fastapi import APIRouter, Depends, HTTPException, Request

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
    r.add_api_route("/organism/journal/lifecycle/{envelope_id}", _journal_lifecycle, methods=["GET"])
    r.add_api_route("/organism/journal/statistics", _journal_statistics, methods=["GET"])
    r.add_api_route("/organism/mutations", _mutation_registry, methods=["GET"])
    r.add_api_route("/organism/mutations/{mutation_name}", _mutation_detail, methods=["GET"])
    r.add_api_route("/organism/spine-guard", _spine_guard_status, methods=["GET"])
    r.add_api_route("/organism/spine-guard/blocked", _spine_guard_blocked, methods=["GET"])
    r.add_api_route("/organism/execution-doctrine", _execution_doctrine, methods=["GET"])
    r.add_api_route("/organism/reliability", _reliability_metrics, methods=["GET"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route("/organism/spine/approve/{envelope_id}", _spine_approve, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine/reject/{envelope_id}", _spine_reject, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine/retry/{envelope_id}", _spine_retry, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/spine-guard/mode", _spine_guard_set_mode, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-gateway/policy", _autonomous_gateway_set_policy, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-gateway/threshold", _autonomous_gateway_set_threshold, methods=["POST"], dependencies=auth)

    # ── Autonomous gateway read-only endpoints ────────────────────────────

    r.add_api_route("/organism/autonomous-gateway", _autonomous_gateway_status, methods=["GET"])
    r.add_api_route("/organism/autonomous-gateway/decisions", _autonomous_gateway_decisions, methods=["GET"])
    r.add_api_route("/organism/autonomous-gateway/blocked", _autonomous_gateway_blocked, methods=["GET"])
    r.add_api_route("/organism/autonomous-gateway/pending", _autonomous_gateway_pending, methods=["GET"])

    # ── Plan execution adapter endpoints ─────────────────────────────────

    r.add_api_route("/organism/execution-graph", _execution_graph_status, methods=["GET"])
    r.add_api_route("/organism/execution-graph/{plan_id}", _execution_graph_detail, methods=["GET"])
    r.add_api_route("/organism/execute-plan", _execute_plan, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/execute-plan/{plan_id}/approve/{step_id}", _execute_plan_approve_step, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/execute-plan/{plan_id}/pending", _execute_plan_pending, methods=["GET"])

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
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    envelope = daemon.governed_spine.approve(envelope_id, approved_by=client_id)
    if envelope is None:
        return {"error": f"envelope {envelope_id} not found in pending queue"}
    logger.info("Spine envelope approved: %s by %s", envelope_id, client_id)
    return envelope.to_dict()


async def _spine_reject(envelope_id: str, payload: dict, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    reason = str(payload.get("reason", "operator_rejected"))[:500]
    envelope = daemon.governed_spine.reject(envelope_id, reason=reason)
    if envelope is None:
        return {"error": f"envelope {envelope_id} not found in pending queue"}
    logger.info("Spine envelope rejected: %s by %s — %s", envelope_id, client_id, reason)
    return envelope.to_dict()


async def _spine_retry(envelope_id: str, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    completed = daemon.governed_spine.completed_envelopes(500)
    target = None
    for env_dict in completed:
        if env_dict.get("envelope_id") == envelope_id:
            target = env_dict
            break

    if target is None:
        return {"error": f"envelope {envelope_id} not found in completed queue"}

    if target.get("status") not in ("failed", "verification_failed", "rolled_back"):
        return {"error": f"envelope {envelope_id} status is {target.get('status')} — only failed envelopes can be retried"}

    logger.info("Spine envelope retry requested: %s by %s", envelope_id, client_id)
    return {"acknowledged": True, "envelope_id": envelope_id, "note": "re-submit a new envelope for this action"}


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
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

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
    old_mode = daemon.spine_guard.mode
    daemon.spine_guard.set_mode(new_mode)
    logger.info(
        "SpineGuard mode changed via cockpit: %s → %s by %s",
        old_mode.value, new_mode.value, client_id,
    )
    return {
        "old_mode": old_mode.value,
        "new_mode": new_mode.value,
        "changed_by": client_id,
    }


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
        "journal": journal_stats,
        "spine_guard": daemon.spine_guard.to_dict(),
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
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

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
    old_policy = daemon.autonomous_gateway.policy
    daemon.autonomous_gateway.set_policy(new_policy)
    logger.info(
        "Autonomous gateway policy changed via cockpit: %s → %s by %s",
        old_policy.value, new_policy.value, client_id,
    )
    return {
        "old_policy": old_policy.value,
        "new_policy": new_policy.value,
        "changed_by": client_id,
    }


async def _autonomous_gateway_set_threshold(payload: dict, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    threshold = payload.get("threshold")
    if threshold is None or not isinstance(threshold, (int, float)):
        return {"error": "threshold must be a number between 0.0 and 1.0"}

    threshold = float(threshold)
    if not (0.0 <= threshold <= 1.0):
        return {"error": "threshold must be between 0.0 and 1.0"}

    daemon.autonomous_gateway.set_reliability_threshold(threshold)
    logger.info(
        "Autonomous gateway threshold set to %.2f by %s", threshold, client_id,
    )
    return {
        "threshold": threshold,
        "changed_by": client_id,
    }


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
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    intent = str(payload.get("intent", ""))
    if not intent:
        return {"error": "intent is required"}

    from substrate.organism.composition_engine import compose_plan

    composition_plan = compose_plan(intent)
    adapter = daemon.plan_execution_adapter

    executable = adapter.convert_plan(composition_plan)
    result = adapter.execute_plan(executable)

    logger.info(
        "Plan executed via cockpit: %s → %s (%d steps) by %s",
        result.id, result.status.value, len(result.steps), client_id,
    )
    return result.to_dict()


async def _execute_plan_approve_step(plan_id: str, step_id: str, request: Request):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)

    adapter = daemon.plan_execution_adapter
    plan = adapter.get_execution_graph(plan_id)
    if plan is None:
        return {"error": f"execution graph {plan_id} not found"}

    step = adapter.approve_step(plan, step_id, approved_by=client_id)
    if step is None:
        return {"error": f"step {step_id} not found or not awaiting approval"}

    logger.info(
        "Plan step approved: %s/%s by %s → %s",
        plan_id, step_id, client_id, step.status.value,
    )
    return step.to_dict()


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
