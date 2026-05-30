"""Cockpit organism economy, recursion, advisor hierarchy, assimilation, snapshot,
runtimes, governor, workcells, topology, throughput, and reconciliation routes.

Extracted from cockpit.py (Phase 10.0). Auth model: configure() must be called
before include_router().

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

economy_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    require_operator_dep: Any,
) -> None:
    """Wire organism accessor and operator auth into the economy router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router so privileged routes carry the real auth dependency.
    """
    global _get_organism, _configured, economy_router

    _get_organism = get_organism_fn
    _configured = True

    economy_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the economy router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints (no auth required) ─────────────────────────────

    r.add_api_route("/organism/economy", _organism_economy, methods=["GET"])
    r.add_api_route("/organism/economy/records", _organism_economy_records, methods=["GET"])
    r.add_api_route("/organism/economy/task-profile/{task_class}", _organism_task_profile, methods=["GET"])
    r.add_api_route("/organism/recursion", _organism_recursion, methods=["GET"])
    r.add_api_route("/organism/recursion/escalations", _organism_recursion_escalations, methods=["GET"])
    r.add_api_route("/organism/advisors", _organism_advisor_hierarchy, methods=["GET"])
    r.add_api_route("/organism/advisors/tree", _organism_advisor_tree, methods=["GET"])
    r.add_api_route("/organism/advisors/overdue", _organism_overdue_advisors, methods=["GET"])
    r.add_api_route("/organism/assimilation", _organism_assimilation, methods=["GET"])
    r.add_api_route("/organism/assimilation/artifacts", _organism_leverage_artifacts, methods=["GET"])
    r.add_api_route("/organism/snapshot", _organism_full_snapshot, methods=["GET"])
    r.add_api_route("/organism/runtimes", _organism_runtimes, methods=["GET"])
    r.add_api_route("/organism/governor", _organism_governor, methods=["GET"])
    r.add_api_route("/organism/workcells", _organism_workcells, methods=["GET"])
    r.add_api_route("/organism/topology", _organism_topology, methods=["GET"])
    r.add_api_route("/organism/topology/live", _organism_topology_live, methods=["GET"])
    r.add_api_route("/organism/throughput", _organism_throughput, methods=["GET"])
    r.add_api_route("/organism/reconciliation", _organism_reconciliation, methods=["GET"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route("/organism/recursion/kill", _organism_kill_switch, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/recursion/resume", _organism_resume_switch, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/reconcile", _organism_reconcile_now, methods=["POST"], dependencies=auth)

    return r


# ── Economy handlers ───────────────────────────────────────────────────────────


async def _organism_economy():
    """Execution economy metrics — cost, value, leverage per runtime."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return {"total_executions": 0, "runtime_profiles": {}}
        return economy.to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_economy_records(limit: int = 50):
    """Recent execution decision records."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return []
        return economy.recent_records(limit)
    except Exception as e:
        return {"error": str(e)}


async def _organism_task_profile(task_class: str):
    """Runtime rankings for a specific task class."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        economy = getattr(daemon, "_economy", None)
        if economy is None:
            return {"task_class": task_class, "runtime_rankings": []}
        return economy.task_execution_profile(task_class).to_dict()
    except Exception as e:
        return {"error": str(e)}


# ── Recursion handlers ─────────────────────────────────────────────────────────


async def _organism_recursion():
    """Current recursion governance state and limits."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"limits": {}, "state": {}, "kill_switch": False}
        return governor.to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_recursion_escalations(limit: int = 50):
    """Recent recursion escalation events."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return []
        return governor.escalation_log(limit)
    except Exception as e:
        return {"error": str(e)}


async def _organism_kill_switch():
    """Activate the kill switch — halts all autonomous execution."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"error": "recursion governor not available"}
        governor.kill()
        return {"ok": True, "killed": True}
    except Exception as e:
        return {"error": str(e)}


async def _organism_resume_switch():
    """Deactivate the kill switch — resume autonomous execution."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        governor = getattr(daemon, "_recursion_governor", None)
        if governor is None:
            return {"error": "recursion governor not available"}
        governor.resume()
        return {"ok": True, "killed": False}
    except Exception as e:
        return {"error": str(e)}


# ── Advisor handlers ───────────────────────────────────────────────────────────


async def _organism_advisor_hierarchy():
    """Full advisor hierarchy tree."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return {"primary_id": "", "total_advisors": 0, "advisors": {}}
        return hierarchy.to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_advisor_tree():
    """Advisor hierarchy as a nested tree structure."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return {}
        return hierarchy.hierarchy_tree()
    except Exception as e:
        return {"error": str(e)}


async def _organism_overdue_advisors():
    """Advisors with overdue reports."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        hierarchy = getattr(daemon, "_advisor_hierarchy", None)
        if hierarchy is None:
            return []
        return [a.to_dict() for a in hierarchy.overdue_reports()]
    except Exception as e:
        return {"error": str(e)}


# ── Assimilation handlers ──────────────────────────────────────────────────────


async def _organism_assimilation():
    """External leverage assimilation status."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        assimilator = getattr(daemon, "_assimilator", None)
        if assimilator is not None:
            return assimilator.to_dict()
        from substrate.organism.leverage_assimilation import LeverageAssimilator

        return LeverageAssimilator().to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_leverage_artifacts():
    """List all assimilation artifacts."""
    daemon = _get_organism()
    if daemon is None:
        return []
    try:
        assimilator = getattr(daemon, "_assimilator", None)
        if assimilator is None:
            return []
        return assimilator.list_artifacts()
    except Exception as e:
        return {"error": str(e)}


# ── Snapshot + infrastructure handlers ────────────────────────────────────────


async def _organism_full_snapshot():
    """Full organism snapshot — objectives, runtimes, workcells, bottlenecks."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        from substrate.organism.observability import OrganismObserver

        observer = OrganismObserver(
            coordinator=daemon.advisor.coordinator if daemon.advisor else None,
            graph=daemon.graph,
            supervisor=daemon.supervisor,
            homeostasis=daemon.homeostasis,
        )
        snap = observer.snapshot()
        return snap.to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_runtimes():
    daemon = _get_organism()
    if daemon is None:
        return {"runtimes": [], "count": 0}
    graph = getattr(daemon, "graph", None)
    if graph is None:
        return {"runtimes": [], "count": 0}
    data = graph.to_dict()
    runtimes_dict = data.get("runtimes", {})
    return {
        "runtimes": list(runtimes_dict.values()),
        "count": data.get("total_runtimes", 0),
        "available": data.get("available", 0),
    }


async def _organism_governor():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    gov = getattr(daemon, "governor", None)
    if gov is None:
        return {"error": "governor not available"}
    return gov.to_dict()


async def _organism_workcells():
    daemon = _get_organism()
    if daemon is None:
        return {"workcells": [], "count": 0}
    try:
        wc = getattr(daemon, "_workcell_daemon", None)
        if wc is None:
            return {"workcells": [], "count": 0, "note": "workcell daemon not wired"}
        return wc.to_dict()
    except Exception:
        return {"workcells": [], "count": 0}


# ── Topology handlers ──────────────────────────────────────────────────────────


async def _organism_topology():
    """Full operational topology — runtimes, workcells, system metrics."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        env_graph = getattr(daemon, "_environment_graph", None)
        if env_graph is not None:
            return env_graph.to_dict()
        return daemon.advisor.resource_topology()
    except Exception as e:
        return {"error": str(e)}


async def _organism_topology_live():
    """Capture a fresh topology snapshot and return it with diff."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        env_graph = getattr(daemon, "_environment_graph", None)
        if env_graph is None:
            return {"error": "environment graph not available"}

        workcell_data = []
        wcd = getattr(daemon, "_workcell_daemon", None)
        if wcd is not None:
            for wc in wcd._workcells.values():
                workcell_data.append(wc.to_dict())

        snapshot = env_graph.capture(
            graph=daemon.graph,
            workcells=workcell_data,
        )
        diff = env_graph.diff()
        return {
            "snapshot": snapshot.to_dict(),
            "diff": diff.to_dict() if diff.has_changes else None,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Throughput + reconciliation handlers ──────────────────────────────────────


async def _organism_throughput():
    """Event throughput, tick timing, and pressure metrics."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        spine = daemon.event_spine
        tick = daemon.autonomous_tick
        snap = spine.snapshot()

        tick_data = tick.to_dict()
        metrics = tick_data.get("metrics", {})

        result = {
            "event_spine": {
                "total_events": snap.get("total_events", 0),
                "events_by_domain": snap.get("events_by_domain", {}),
                "subscriber_count": snap.get("subscriber_count", 0),
            },
            "tick_engine": {
                "cycle_count": tick_data.get("cycle_count", 0),
                "current_interval": tick_data.get("current_interval", 0),
                "is_paused": tick_data.get("is_paused", False),
                "stages": tick_data.get("stages", []),
                "avg_cycle_ms": metrics.get("avg_cycle_ms", 0),
                "total_stages_executed": metrics.get("total_stages_executed", 0),
                "total_stages_failed": metrics.get("total_stages_failed", 0),
                "consecutive_idle": metrics.get("consecutive_idle", 0),
            },
            "runtimes": {
                "total": daemon.graph.node_count if daemon.graph else 0,
                "available": daemon.graph.available_count if daemon.graph else 0,
            },
        }

        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is not None:
            result["reconciler"] = reconciler.to_dict()

        return result
    except Exception as e:
        return {"error": str(e)}


async def _organism_reconciliation():
    """Last reconciliation report and history."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is None:
            return {"error": "reconciler not available"}
        return reconciler.to_dict()
    except Exception as e:
        return {"error": str(e)}


async def _organism_reconcile_now():
    """Force an immediate reconciliation cycle."""
    import asyncio

    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    try:
        reconciler = getattr(daemon, "_reconciler", None)
        if reconciler is None:
            return {"error": "reconciler not available"}

        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, reconciler.reconcile)
        return report.to_dict()
    except Exception as e:
        return {"error": str(e)}
