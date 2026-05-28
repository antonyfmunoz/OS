"""Orchestration loop — persistent autonomous execution for the organism.

Registers named stages with the PersistentLoop infrastructure so the
organism can run as a config-driven daemon loop. Each stage maps to an
Advisor method:

  signal_drain       → advisor.autonomous_tick() (full tick)
  health_check       → supervisor.check_all() + reconcile
  homeostasis_check  → homeostasis.check()
  recovery_sweep     → supervisor recovery plan execution
  delegation_check   → advisor.check_delegations()
  objective_advance  → execute ready work units from active objectives
  state_persist      → persist supervisor + daemon state

The loop is designed to be:
  - tmux-safe: runs as a daemon thread
  - restart-safe: PersistentLoop writes heartbeats
  - crash-safe: state is persisted every cycle
  - configurable: interval and stages from JSONL definition

Usage:
    from substrate.organism.orchestration_loop import (
        create_orchestration_loop,
        register_organism_stages,
    )
    from substrate.organism.daemon import OrganismDaemon

    daemon = OrganismDaemon(graph=build_default_graph())
    daemon.start()

    register_organism_stages(daemon)
    loop = create_orchestration_loop(interval_seconds=30)
    loop.start()

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from substrate.execution.loop.persistent_loop import (
    CycleReport,
    LoopDefinition,
    PersistentLoop,
    register_stage,
)

logger = logging.getLogger(__name__)

_daemon_ref: Any = None


def _get_daemon() -> Any:
    """Get the daemon reference. Set via register_organism_stages()."""
    return _daemon_ref


def _emit_stage_event(daemon: Any, stage_name: str, details: dict[str, Any]) -> None:
    spine = getattr(daemon, "_event_spine", None)
    if spine is None:
        return
    from substrate.organism.event_spine import EventDomain
    spine.emit(EventDomain.EXECUTION, "stage_completed", "orchestration_loop", {
        "stage": stage_name,
        "details": details,
    })


def _stage_organism_tick(loop: PersistentLoop, report: CycleReport) -> None:
    """Full organism tick — the primary stage."""
    daemon = _get_daemon()
    if daemon is None:
        report.errors += 1
        report.details.append({"stage": "organism_tick", "error": "no daemon registered"})
        return

    result = daemon.tick()
    actions_count = len(result.get("actions", []))
    report.actions_taken += actions_count
    detail = {
        "stage": "organism_tick",
        "tick": result.get("tick", 0),
        "actions": actions_count,
        "system_mode": result.get("system_mode", "unknown"),
        "elapsed_ms": result.get("elapsed_ms", 0),
    }
    report.details.append(detail)
    _emit_stage_event(daemon, "organism_tick", detail)


def _stage_health_check(loop: PersistentLoop, report: CycleReport) -> None:
    """Check runtime health and reconcile graph."""
    daemon = _get_daemon()
    if daemon is None or daemon.supervisor is None:
        return

    health = daemon.supervisor.check_all()
    dead_count = sum(1 for h in health.values() if h.value == "dead")
    degraded_count = sum(1 for h in health.values() if h.value == "degraded")

    if dead_count > 0 or degraded_count > 0:
        daemon.supervisor.reconcile_graph()
        detail = {
            "stage": "health_check",
            "dead": dead_count,
            "degraded": degraded_count,
            "reconciled": True,
        }
        report.details.append(detail)
        _emit_stage_event(daemon, "health_check", detail)


def _stage_homeostasis(loop: PersistentLoop, report: CycleReport) -> None:
    """Run homeostasis health check."""
    daemon = _get_daemon()
    if daemon is None:
        return

    hreport = daemon.homeostasis.check()
    if hreport.actions_taken:
        report.actions_taken += len(hreport.actions_taken)
        detail = {
            "stage": "homeostasis",
            "mode": hreport.mode.value,
            "unhealthy": hreport.unhealthy,
            "actions": hreport.actions_taken,
        }
        report.details.append(detail)
        _emit_stage_event(daemon, "homeostasis", detail)


def _stage_recovery(loop: PersistentLoop, report: CycleReport) -> None:
    """Execute recovery plan for dead runtimes."""
    daemon = _get_daemon()
    if daemon is None or daemon.supervisor is None or daemon.graph is None:
        return

    plan = daemon.supervisor.get_recovery_plan()
    for entry in plan:
        if not entry["should_restart"]:
            continue

        rid = entry["runtime_id"]
        node = daemon.graph.get(rid)
        if node is None or node.adapter is None:
            continue

        daemon.supervisor.mark_restarting(rid)
        try:
            available = node.adapter.check_available()
            if available:
                daemon.supervisor.record_recovery_success(rid)
                report.actions_taken += 1
                detail = {
                    "stage": "recovery",
                    "runtime": rid,
                    "status": "recovered",
                }
                report.details.append(detail)
                _emit_stage_event(daemon, "recovery", detail)
            else:
                daemon.supervisor.record_recovery_failure(rid, "still unavailable")
        except Exception as exc:
            daemon.supervisor.record_recovery_failure(rid, str(exc))
            report.details.append({
                "stage": "recovery",
                "runtime": rid,
                "status": "failed",
                "error": str(exc)[:200],
            })


def _stage_delegation_check(loop: PersistentLoop, report: CycleReport) -> None:
    """Check for overdue delegations."""
    daemon = _get_daemon()
    if daemon is None:
        return

    followups = daemon.advisor.check_delegations()
    if followups:
        report.actions_taken += len(followups)
        detail = {
            "stage": "delegation_check",
            "overdue": len(followups),
        }
        report.details.append(detail)
        _emit_stage_event(daemon, "delegation_check", detail)


def _stage_objective_advance(loop: PersistentLoop, report: CycleReport) -> None:
    """Advance active objectives by executing ready work units."""
    daemon = _get_daemon()
    if daemon is None or daemon.advisor.coordinator is None:
        return

    coordinator = daemon.advisor.coordinator
    for obj_dict in coordinator.list_objectives():
        if obj_dict["status"] != "executing":
            continue
        results = coordinator.execute_ready(obj_dict["id"])
        report.actions_taken += len(results)
        if results:
            detail = {
                "stage": "objective_advance",
                "objective_id": obj_dict["id"],
                "work_units_executed": len(results),
            }
            report.details.append(detail)
            _emit_stage_event(daemon, "objective_advance", detail)


def _stage_state_persist(loop: PersistentLoop, report: CycleReport) -> None:
    """Persist daemon and supervisor state."""
    daemon = _get_daemon()
    if daemon is None:
        return

    daemon._persist_state()
    detail = {"stage": "state_persist", "persisted": True}
    report.details.append(detail)
    _emit_stage_event(daemon, "state_persist", detail)


def register_organism_stages(daemon: Any) -> None:
    """Register all organism stages with the PersistentLoop stage registry
    and bind them to the given daemon instance."""
    global _daemon_ref
    _daemon_ref = daemon

    register_stage("organism_tick", _stage_organism_tick)
    register_stage("health_check", _stage_health_check)
    register_stage("homeostasis_check", _stage_homeostasis)
    register_stage("recovery_sweep", _stage_recovery)
    register_stage("delegation_check", _stage_delegation_check)
    register_stage("objective_advance", _stage_objective_advance)
    register_stage("state_persist", _stage_state_persist)

    logger.info("organism stages registered: 7 stages bound to daemon")


def create_orchestration_loop(
    interval_seconds: int = 30,
    stages: list[str] | None = None,
) -> PersistentLoop:
    """Create the organism's orchestration loop.

    Default stages run the full organism tick (which includes all
    subsystem operations). For finer control, specify individual stages.
    """
    if stages is None:
        stages = [
            "organism_tick",
            "state_persist",
        ]

    defn = LoopDefinition(
        name="organism_orchestration",
        domain="organism",
        interval_seconds=interval_seconds,
        stages=stages,
        enabled=True,
        description="Continuous organism orchestration — autonomous tick + state persistence",
    )

    return PersistentLoop(defn)


def create_full_orchestration_loop(interval_seconds: int = 60) -> PersistentLoop:
    """Create an orchestration loop with all individual stages.

    Use this for fine-grained control where each stage runs
    independently rather than bundled in organism_tick.
    """
    defn = LoopDefinition(
        name="organism_full_orchestration",
        domain="organism",
        interval_seconds=interval_seconds,
        stages=[
            "health_check",
            "recovery_sweep",
            "homeostasis_check",
            "objective_advance",
            "delegation_check",
            "state_persist",
        ],
        enabled=True,
        description="Full organism orchestration with individual stage control",
    )

    return PersistentLoop(defn)
