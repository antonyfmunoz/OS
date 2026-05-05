"""
Orchestration bootstrap — wires IntentCoordinator into the EventScheduler.

This is the single wiring point for the orchestration layer.  It creates
the PlanRegistry, WorkflowDriver, AutonomyPolicy, and IntentCoordinator,
then registers the coordinator's handlers as scheduler subscribers.

The coordinator is the ONLY orchestration-level subscriber.  No other
orchestration component subscribes to the scheduler directly.

Usage:
    from umh.substrate.orchestration_bootstrap import bootstrap_orchestration

    coordinator = bootstrap_orchestration(scheduler)
"""

from __future__ import annotations

import sys

from umh.substrate.autonomy_policy import AutonomyPolicy
from umh.substrate.event_scheduler import EventScheduler
from umh.substrate.intent_coordinator import IntentCoordinator
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.workflow_driver import WorkflowDriver

_LOG_PREFIX = "[substrate.orchestration_bootstrap]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ── Raw ingress event types ─────────────────────────────────────────

_INGRESS_EVENTS = (
    "decision_intent_proposed",
    "operator_intent_requested",
    "cron_intent_requested",
    "result_intent_requested",
)

# ── Execution result event types ────────────────────────────────────

_EXECUTION_RESULT_EVENTS = (
    "execution_completed",
    "execution_failed",
    "execution_timed_out",
    "execution_rejected",
)

# ── Cancellation event type ─────────────────────────────────────────

_CANCEL_EVENT = "intent_cancel_requested"


def bootstrap_orchestration(
    scheduler: EventScheduler,
    max_active: int = 1,
    preemption_enabled: bool = False,
    autonomy_policy: AutonomyPolicy | None = None,
) -> IntentCoordinator:
    """Wire the orchestration layer into the scheduler.

    Creates PlanRegistry (with built-in generators from planner.py),
    WorkflowDriver, AutonomyPolicy, and IntentCoordinator, then
    subscribes all coordinator handlers.

    Args:
        scheduler: The EventScheduler to wire into.
        max_active: Maximum concurrent active intents.
        preemption_enabled: Whether active intents can be preempted.
        autonomy_policy: Optional bounded autonomy controls.
            When None, a default policy (enabled=False) is used,
            preserving existing behavior.

    Returns the coordinator instance for inspection/testing.
    """
    # Build dependency chain
    plan_registry = PlanRegistry.with_defaults()
    workflow_driver = WorkflowDriver(plan_registry)
    coordinator = IntentCoordinator(
        plan_registry=plan_registry,
        workflow_driver=workflow_driver,
        max_active=max_active,
        preemption_enabled=preemption_enabled,
        autonomy_policy=autonomy_policy or AutonomyPolicy(),
    )

    # Subscribe ingress handler to all 4 raw ingress event types
    for event_type in _INGRESS_EVENTS:
        scheduler.subscribe(
            event_type=event_type,
            handler=coordinator._handle_intent_ingress,
            name=f"orch.ingress.{event_type}",
        )

    # Subscribe execution result handler to all 4 result types
    for event_type in _EXECUTION_RESULT_EVENTS:
        scheduler.subscribe(
            event_type=event_type,
            handler=coordinator._handle_execution_result,
            name=f"orch.result.{event_type}",
        )

    # Subscribe cancellation handler
    scheduler.subscribe(
        event_type=_CANCEL_EVENT,
        handler=coordinator._handle_intent_cancel,
        name="orch.cancel",
    )

    _log(
        f"orchestration wired: "
        f"{len(_INGRESS_EVENTS)} ingress + "
        f"{len(_EXECUTION_RESULT_EVENTS)} result + "
        f"1 cancel = {len(_INGRESS_EVENTS) + len(_EXECUTION_RESULT_EVENTS) + 1} subscriptions"
    )

    return coordinator
