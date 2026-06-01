"""Cockpit organism core routes — status, agents, deliverables, events, tick,
leverage, metrics, bottlenecks, intelligence, physics, compression, workload,
execution-mode, workloads, automation-candidates, maintenance, assisted, signal.

Extracted from cockpit.py (Phase 10.0) to bring the main file under 3000 lines.
All routes are mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency from cockpit.py and wires it into every
privileged route.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

organism_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_check_rate_limit: Callable[[str, str], None] = lambda action, client_id: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    check_rate_limit_fn: Callable[[str, str], None],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities and operator auth into the organism router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router so privileged routes carry the real auth dependency.
    """
    global _get_organism, _check_rate_limit, _configured, organism_router

    _get_organism = get_organism_fn
    _check_rate_limit = check_rate_limit_fn
    _configured = True

    organism_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the organism router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints (no auth required) ─────────────────────────────

    r.add_api_route("/organism/status", _organism_status, methods=["GET"])
    r.add_api_route("/organism/agents", _organism_agents, methods=["GET"])
    r.add_api_route("/organism/deliverables", _organism_deliverables, methods=["GET"])
    r.add_api_route("/organism/events", _organism_events, methods=["GET"])
    r.add_api_route("/organism/tick", _organism_tick_status, methods=["GET"])
    r.add_api_route("/organism/leverage", _organism_leverage, methods=["GET"])
    r.add_api_route("/organism/metrics", _organism_metrics, methods=["GET"])
    r.add_api_route("/organism/bottlenecks", _organism_bottlenecks, methods=["GET"])
    r.add_api_route("/organism/intelligence", _organism_intelligence, methods=["GET"])
    r.add_api_route("/organism/intelligence/leverage", _organism_intelligence_leverage, methods=["GET"])
    r.add_api_route("/organism/intelligence/next-actions", _organism_intelligence_next_actions, methods=["GET"])
    r.add_api_route("/organism/intelligence/readiness", _organism_intelligence_readiness, methods=["GET"])
    r.add_api_route("/organism/physics", _organism_physics, methods=["GET"])
    r.add_api_route("/organism/compression", _organism_compression, methods=["GET"])
    r.add_api_route("/organism/workload", _organism_workload, methods=["GET"])
    r.add_api_route("/organism/execution-mode", _organism_execution_mode, methods=["GET"])
    r.add_api_route("/organism/workloads", _organism_workloads, methods=["GET"])
    r.add_api_route("/organism/workloads/outcomes", _organism_workload_outcomes, methods=["GET"])
    r.add_api_route("/organism/automation-candidates", _organism_automation_candidates, methods=["GET"])
    r.add_api_route("/organism/maintenance", _organism_maintenance, methods=["GET"])
    r.add_api_route("/organism/assisted", _organism_assisted, methods=["GET"])
    r.add_api_route("/organism/assisted/audit", _organism_assisted_audit, methods=["GET"])
    r.add_api_route("/organism/signal", _organism_signal, methods=["POST"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route("/organism/execution-mode/promote", _organism_promote_mode, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/workloads/run", _organism_run_workload, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/workloads/run-all", _organism_run_all_workloads, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/automation-candidates/{proposal_id}/approve", _organism_approve_automation, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/automation-candidates/{proposal_id}/deny", _organism_deny_automation, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/maintenance/run", _organism_run_maintenance, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/assisted/execute", _organism_assisted_execute, methods=["POST"], dependencies=auth)

    # ── Operator acceptance endpoints ────────────────────────────────────
    r.add_api_route("/organism/operator-acceptance", _operator_acceptance_overview, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/runs", _operator_acceptance_runs, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/runs/{run_id}", _operator_acceptance_run_detail, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/artifacts", _operator_acceptance_artifacts, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/scenarios", _operator_acceptance_scenarios, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/readiness", _operator_acceptance_readiness, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/start", _operator_acceptance_start, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/operator-acceptance/primary-proof", _operator_acceptance_primary_proof, methods=["GET"])
    r.add_api_route("/organism/operator-acceptance/safety-proof", _operator_acceptance_safety_proof, methods=["GET"])

    return r


# ── Handler implementations ────────────────────────────────────────────────


async def _organism_status():
    daemon = _get_organism()
    if daemon is None:
        return {
            "running": False,
            "agents": [],
            "total_deliverables": 0,
            "total_learning_signals": 0,
        }
    return daemon.status()


async def _organism_agents():
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.advisor.list_agents()


async def _organism_deliverables(agent_id: str | None = None, limit: int = 50):
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.store.list_deliverables(agent_id=agent_id, limit=limit)


async def _organism_events(limit: int = 50, since: float | None = None):
    daemon = _get_organism()
    if daemon is None:
        return {"events": [], "count": 0, "transport": "polling"}
    spine = daemon.event_spine
    if since is not None:
        events = spine.replay(since=since)[-limit:]
    else:
        events = spine.recent(limit=limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "transport": "polling",
    }


async def _organism_tick_status():
    daemon = _get_organism()
    if daemon is None:
        return {"running": False}
    return daemon.autonomous_tick.to_dict()


async def _organism_leverage():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.leverage_metrics.summary()


async def _organism_metrics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        "leverage": daemon.leverage_metrics.to_dict(),
        "bottlenecks": daemon.bottleneck_engine.to_dict(),
        "physics": daemon.objective_physics.to_dict(),
        "compression": daemon.operator_compression.to_dict(),
        "execution_mode": daemon.execution_mode_manager.to_dict(),
    }


async def _organism_bottlenecks():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.bottleneck_engine.to_dict()


async def _organism_intelligence():
    """Unified operational intelligence — bottlenecks, leverage, actions, readiness."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        "bottlenecks": daemon.bottleneck_engine.to_dict(),
        "leverage": daemon.leverage_engine.to_dict(),
        "next_actions": daemon.next_action_engine.to_dict(),
        "readiness": daemon.readiness_model.to_dict(),
    }


async def _organism_intelligence_leverage():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.leverage_engine.to_dict()


async def _organism_intelligence_next_actions():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.next_action_engine.to_dict()


async def _organism_intelligence_readiness():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.readiness_model.to_dict()


async def _organism_physics():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.objective_physics.to_dict(),
        "critical_paths": [
            cp.to_dict() for cp in daemon.objective_physics.critical_paths()[:5]
        ],
        "top_gravity": daemon.objective_physics.what_matters_most(5),
        "blockers": daemon.objective_physics.what_blocks_everything(),
    }


async def _organism_compression():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.operator_compression.to_dict(),
        "candidates": [
            c.to_dict() for c in daemon.operator_compression.automation_candidates()
        ],
    }


async def _organism_workload():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cached = daemon.workload_probes.cached
    if cached:
        return cached
    return daemon.workload_probes.full_probe()


async def _organism_execution_mode():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.execution_mode_manager.to_dict(),
        "history": daemon.execution_mode_manager.transition_history(),
    }


async def _organism_promote_mode(payload: dict, request: Request):
    """Promote execution mode. Rate-limited, operator-auth required."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("promote", client_id)

    target = payload.get("target_mode", "")
    justification = str(payload.get("justification", "operator promotion"))[:500]
    try:
        from substrate.organism.execution_modes import ExecutionMode, TransitionReason
        mode = ExecutionMode(target)
        ok = daemon.execution_mode_manager.promote(
            mode,
            reason=TransitionReason.OPERATOR_PROMOTION,
            justification=justification,
        )
        logger.info("Execution mode promotion: %s → %s by %s", target, ok, client_id)
        return {"ok": ok, "current_mode": daemon.execution_mode_manager.current_mode.value}
    except (ValueError, KeyError) as e:
        return {"error": str(e)}


async def _organism_workloads():
    """Recent workload run outcomes."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.workload_runner.to_dict()


async def _organism_workload_outcomes(limit: int = 20):
    """Detailed workload outcome history."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.workload_runner.recent_outcomes(limit)


async def _organism_run_workload(payload: dict):
    """Manually trigger a specific workload."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    workload_type = payload.get("workload_type", "")
    force = payload.get("force", False)

    try:
        from substrate.organism.workload_runner import WorkloadType
        wt = WorkloadType(workload_type)
    except ValueError:
        return {
            "error": f"unknown workload_type: {workload_type}",
            "available": [t.value for t in __import__("substrate.organism.workload_runner", fromlist=["WorkloadType"]).WorkloadType],
        }

    loop = asyncio.get_running_loop()
    outcome = await loop.run_in_executor(
        None,
        lambda: daemon.workload_runner.run_workload(wt, force=force),
    )
    return outcome.to_dict()


async def _organism_run_all_workloads():
    """Run all OBSERVE-safe workloads."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    loop = asyncio.get_running_loop()
    outcomes = await loop.run_in_executor(
        None,
        daemon.workload_runner.run_all_observe,
    )
    return [o.to_dict() for o in outcomes]


async def _organism_automation_candidates():
    """List all automation candidate proposals."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.automation_pipeline.to_dict(),
        "all_proposals": daemon.automation_pipeline.list_proposals(),
    }


async def _organism_approve_automation(proposal_id: str, request: Request):
    """Approve an automation candidate. Rate-limited, operator-auth required."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("approve", client_id)
    logger.info("Automation approval: %s by %s", proposal_id, client_id)
    ok = daemon.automation_pipeline.approve(proposal_id)
    if not ok:
        return {"ok": False, "error": "proposal not found or not in proposed state"}
    return {"ok": True, "proposal_id": proposal_id}


async def _organism_deny_automation(proposal_id: str, payload: dict | None = None):
    """Deny an automation candidate."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    reason = (payload or {}).get("reason", "")
    ok = daemon.automation_pipeline.deny(proposal_id, reason=reason)
    if not ok:
        return {"ok": False, "error": "proposal not found or not in proposed state"}
    return {"ok": True, "proposal_id": proposal_id}


async def _organism_maintenance():
    """Maintenance loop status and recommendations."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return {
        **daemon.maintenance_loop.to_dict(),
        "pending_recommendations": [
            r.to_dict() for r in daemon.maintenance_loop.pending_recommendations
        ],
        "recent_reports": daemon.maintenance_loop.recent_reports(5),
    }


async def _organism_run_maintenance():
    """Trigger a manual maintenance cycle."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(
        None,
        daemon.maintenance_loop.maintenance_tick,
    )
    return report


async def _organism_assisted():
    """Assisted executor status and audit trail."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    return daemon.assisted_executor.to_dict()


async def _organism_assisted_execute(payload: dict, request: Request):
    """Execute an approved maintenance action. Rate-limited, operator-auth required."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}

    client_id = request.client.host if request.client else "unknown"
    _check_rate_limit("execute", client_id)

    category = payload.get("category", "")
    description = str(payload.get("description", ""))[:500]
    params = payload.get("params", {})

    try:
        from substrate.organism.maintenance_loop import ActionCategory
        cat = ActionCategory(category)
    except ValueError:
        return {
            "error": f"unknown category: {category}",
            "available": [c.value for c in __import__("substrate.organism.maintenance_loop", fromlist=["ActionCategory"]).ActionCategory],
        }

    action_id = f"assisted-{category}-{int(time.time())}"
    logger.info("Assisted execution requested: %s by %s", category, client_id)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: daemon.assisted_executor.execute_action(
            action_id=action_id,
            category=cat,
            description=description or f"Assisted: {category}",
            approved_by=f"operator:{client_id}",
            params=params,
        ),
    )
    return result.to_dict()


async def _organism_assisted_audit(limit: int = 50):
    """Full audit trail of assisted actions."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.assisted_executor.audit_trail(limit)


async def _organism_signal(payload: dict):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}
    return daemon.advisor.handle_signal(content)


# ── Operator acceptance handlers ──────────────────────────────────────────


async def _operator_acceptance_overview():
    from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
    return OperatorLoopCoordinator().get_overview()


async def _operator_acceptance_runs():
    from substrate.organism.operator_acceptance import load_runs
    return [r.to_dict() for r in load_runs()]


async def _operator_acceptance_run_detail(run_id: str):
    from substrate.organism.operator_acceptance import get_run
    run = get_run(run_id)
    if not run:
        return {"error": "run not found"}
    return run.to_dict()


async def _operator_acceptance_artifacts():
    from substrate.organism.operator_acceptance import load_artifacts
    return [a.to_dict() for a in load_artifacts()]


async def _operator_acceptance_scenarios():
    from substrate.organism.operator_acceptance_scenarios import get_all_scenarios
    return [s.to_dict() for s in get_all_scenarios()]


async def _operator_acceptance_readiness():
    from substrate.organism.operator_readiness_gate import assess_readiness
    return assess_readiness().to_dict()


async def _operator_acceptance_start(payload: dict):
    input_text = payload.get("input_text", "")
    if not input_text:
        return {"error": "input_text required"}
    from substrate.organism.operator_loop_coordinator import OperatorLoopCoordinator
    coord = OperatorLoopCoordinator()
    return coord.run_scenario_e2e(
        input_text,
        payload.get("input_mode", "text"),
        skip_runtime=payload.get("skip_runtime", False),
    )


async def _operator_acceptance_primary_proof():
    import json as _json
    import os
    path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "operator_acceptance", "phase13_4_primary_e2e_proof.json",
    )
    if not os.path.isfile(path):
        return {"error": "primary proof not found"}
    with open(path) as f:
        return _json.load(f)


async def _operator_acceptance_safety_proof():
    import json as _json
    import os
    path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "operator_acceptance", "phase13_4_policy_safety_proof.json",
    )
    if not os.path.isfile(path):
        return {"error": "safety proof not found"}
    with open(path) as f:
        return _json.load(f)
