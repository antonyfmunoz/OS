"""
Workflow driver — pure step machine for advancing one intent through a plan.

NOT a scheduler subscriber.  Called by IntentCoordinator only.
Returns StepResult containing mutations, step events, and terminal signal.

Emits ONLY:
- Plan step events (the real lifecycle/execution event)
- orch_intent_step_dispatched (step-level observability)

Does NOT emit:
- orch_intent_completed
- orch_intent_failed
- orch_intent_cancelled

Those are intent-level lifecycle events owned by IntentCoordinator.
The driver signals terminal status via StepResult.terminal / .terminal_status
so the coordinator can emit the appropriate lifecycle event.

Does NOT:
- Subscribe to scheduler events
- Read from store directly
- Apply mutations
- Touch active membership keys (coordinator owns those)

Usage:
    driver = WorkflowDriver(plan_registry)
    result = driver.start_workflow(intent, state)
    if result.terminal:
        # coordinator emits orch_intent_failed
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    intent_store_key,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.workflow_events import (
    build_orch_intent_step_dispatched_event,
)

_LOG_PREFIX = "[substrate.workflow_driver]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


@dataclass
class StepResult:
    """Return value from WorkflowDriver methods.

    Fields:
        mutations: State mutations to apply (intent:{id} updates).
        events: Step-level events only (plan step + step dispatched obs).
        terminal: True if the intent reached a terminal state.
        terminal_status: "completed" or "failed" when terminal, None otherwise.
        terminal_reason: Human-readable reason when terminal_status is "failed".
        steps_executed: Total steps executed (set on completion).
    """

    mutations: list[dict[str, Any]] = field(default_factory=list)
    events: list[SchedulerEvent] = field(default_factory=list)
    terminal: bool = False
    terminal_status: str | None = None
    terminal_reason: str = ""
    steps_executed: int = 0


class WorkflowDriver:
    """Pure step machine for advancing one intent through its plan.

    Every method returns a StepResult — caller decides what to do
    with the terminal signal.
    """

    def __init__(self, plan_registry: PlanRegistry) -> None:
        self._plan_registry = plan_registry

    def start_workflow(self, intent: Intent, state: dict[str, Any]) -> StepResult:
        """Start a workflow: derive plan, set total_steps, emit first step.

        Returns StepResult with terminal=True if no plan available.
        """
        plan = self._plan_registry.derive_plan(intent, state)
        if plan is None or plan.step_count == 0:
            _log(f"no plan for intent {intent.intent_id}, signaling failed")
            return self._make_failed_result(intent, "no_plan_available")

        step = plan.step_at(0)
        assert step is not None  # step_count > 0 guarantees this

        # Update intent: ACTIVE, total_steps set, current_step=0
        updated = intent.with_status(IntentStatus.ACTIVE).with_total_steps(
            plan.step_count
        )
        mutations: list[dict[str, Any]] = [
            {
                "op": "SET",
                "key": intent_store_key(updated.intent_id),
                "value": updated.to_dict(),
            },
        ]

        # Build the step event — the real lifecycle/execution event
        step_event = SchedulerEvent(
            event_type=step.event_type,
            session_name=intent.session_name,
            source="workflow_driver",
            run_id=intent.goal.get("run_id"),
            payload={
                **step.payload,
                "session_name": intent.session_name,
            },
            metadata={
                "_orch_intent_id": intent.intent_id,
                "_orch_step_index": step.step_index,
                "_orch_plan_id": plan.plan_id,
                "_orch_variant_id": plan.variant_id,
            },
        )

        # Step-level observability event
        obs_event = build_orch_intent_step_dispatched_event(
            intent_id=intent.intent_id,
            step_index=step.step_index,
            step_event_type=step.event_type,
            step_event_id=step_event.event_id,
            session_name=intent.session_name,
            run_id=intent.goal.get("run_id"),
        )

        _log(
            f"started workflow: intent={intent.intent_id} "
            f"plan={plan.plan_id} variant={plan.variant_id} steps={plan.step_count}"
        )

        return StepResult(
            mutations=mutations,
            events=[step_event, obs_event],
        )

    def advance_step(
        self, intent: Intent, completed_step_index: int, state: dict[str, Any]
    ) -> StepResult:
        """Advance intent to the next step after completed_step_index.

        If the completed step was the last one, returns terminal=True
        with terminal_status="completed" and no step events.
        Otherwise, emits the next step event.
        """
        next_step_index = completed_step_index + 1

        plan = self._plan_registry.derive_plan(intent, state)
        if plan is None:
            _log(f"plan disappeared for intent {intent.intent_id}")
            return self._make_failed_result(intent, "plan_disappeared_on_advance")

        # Advance the intent's current_step
        advanced = intent.with_step_advanced()

        if next_step_index >= plan.step_count:
            # All steps done — signal completed
            completed = advanced.with_status(IntentStatus.COMPLETED)
            mutations: list[dict[str, Any]] = [
                {
                    "op": "SET",
                    "key": intent_store_key(completed.intent_id),
                    "value": completed.to_dict(),
                },
            ]
            _log(
                f"workflow complete: intent={intent.intent_id} steps={plan.step_count}"
            )
            return StepResult(
                mutations=mutations,
                events=[],
                terminal=True,
                terminal_status="completed",
                steps_executed=plan.step_count,
            )

        # Emit next step
        step = plan.step_at(next_step_index)
        assert step is not None

        mutations = [
            {
                "op": "SET",
                "key": intent_store_key(advanced.intent_id),
                "value": advanced.to_dict(),
            },
        ]

        step_event = SchedulerEvent(
            event_type=step.event_type,
            session_name=intent.session_name,
            source="workflow_driver",
            run_id=intent.goal.get("run_id"),
            payload={
                **step.payload,
                "session_name": intent.session_name,
            },
            metadata={
                "_orch_intent_id": intent.intent_id,
                "_orch_step_index": step.step_index,
                "_orch_plan_id": plan.plan_id,
                "_orch_variant_id": plan.variant_id,
            },
        )

        obs_event = build_orch_intent_step_dispatched_event(
            intent_id=intent.intent_id,
            step_index=step.step_index,
            step_event_type=step.event_type,
            step_event_id=step_event.event_id,
            session_name=intent.session_name,
            run_id=intent.goal.get("run_id"),
        )

        _log(
            f"advanced workflow: intent={intent.intent_id} "
            f"step={next_step_index}/{plan.step_count}"
        )

        return StepResult(
            mutations=mutations,
            events=[step_event, obs_event],
        )

    def fail_workflow(self, intent: Intent, reason: str) -> StepResult:
        """Mark intent as failed. Returns terminal StepResult with no events.

        The coordinator emits orch_intent_failed.
        """
        failed = intent.with_status(IntentStatus.FAILED)
        mutations: list[dict[str, Any]] = [
            {
                "op": "SET",
                "key": intent_store_key(failed.intent_id),
                "value": failed.to_dict(),
            },
        ]
        _log(f"workflow failed: intent={intent.intent_id} reason={reason}")
        return StepResult(
            mutations=mutations,
            events=[],
            terminal=True,
            terminal_status="failed",
            terminal_reason=reason,
        )

    def cancel_workflow(self, intent: Intent, reason: str = "cancelled") -> StepResult:
        """Mark intent as cancelled. Returns terminal StepResult with no events.

        The coordinator emits orch_intent_cancelled.
        Cancelled maps to FAILED status — IntentStatus has no CANCELLED variant.
        """
        cancelled = intent.with_status(IntentStatus.FAILED)
        mutations: list[dict[str, Any]] = [
            {
                "op": "SET",
                "key": intent_store_key(cancelled.intent_id),
                "value": {
                    **cancelled.to_dict(),
                    "metadata": {
                        **cancelled.metadata,
                        "cancelled": True,
                        "cancel_reason": reason,
                    },
                },
            },
        ]
        _log(f"workflow cancelled: intent={intent.intent_id} reason={reason}")
        return StepResult(
            mutations=mutations,
            events=[],
            terminal=True,
            terminal_status="cancelled",
            terminal_reason=reason,
        )

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _make_failed_result(intent: Intent, reason: str) -> StepResult:
        """Build a terminal failed StepResult."""
        failed = intent.with_status(IntentStatus.FAILED)
        return StepResult(
            mutations=[
                {
                    "op": "SET",
                    "key": intent_store_key(failed.intent_id),
                    "value": failed.to_dict(),
                },
            ],
            events=[],
            terminal=True,
            terminal_status="failed",
            terminal_reason=reason,
        )
