"""UMH Orchestrator — event-driven rule engine for automatic follow-up actions.

Subscribes to the EventStream and evaluates registered rules against each
event. When a rule matches, its action fires — enabling the system to react
to its own state transitions without manual re-triggering.

Built-in rules:
  - approval.approved → replay the original execution with the approval_id
  - execution.completed (rejected, requires_approval) → log pending approval

Safety:
  - Max 1 replay per approval (prevents infinite loops)
  - Orchestrator events (orchestration.*) never trigger rules
  - Processed set tracks all handled events

Usage:
    from umh.orchestrator.engine import get_orchestrator, start_orchestrator

    start_orchestrator()  # subscribes to event stream, registers built-in rules
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable

from umh.core.clock import iso_now as _iso_now
from umh.events.stream import Event, get_event_stream, publish

_log = logging.getLogger(__name__)


@dataclass
class Rule:
    id: str
    event_type: str
    condition: Callable[[Event], bool]
    action: Callable[[Event], None]
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "description": self.description,
        }


class Orchestrator:
    """Event-driven rule engine. Thread-safe."""

    def __init__(self) -> None:
        self._rules: list[Rule] = []
        self._lock = threading.Lock()
        self._processed: set[str] = set()
        self._pending_requests: dict[str, dict] = {}
        self._replay_count: dict[str, int] = {}
        self._max_replays = 1

    def register_rule(self, rule: Rule) -> None:
        with self._lock:
            self._rules.append(rule)

    def list_rules(self) -> list[Rule]:
        with self._lock:
            return list(self._rules)

    def store_pending_request(self, execution_id: str, request_dict: dict) -> None:
        with self._lock:
            self._pending_requests[execution_id] = request_dict

    def get_pending_request(self, execution_id: str) -> dict | None:
        with self._lock:
            return self._pending_requests.get(execution_id)

    def remove_pending_request(self, execution_id: str) -> None:
        with self._lock:
            self._pending_requests.pop(execution_id, None)

    def handle_event(self, event: Event) -> None:
        if event.type.startswith("orchestration."):
            return

        with self._lock:
            if event.id in self._processed:
                return
            self._processed.add(event.id)
            rules = list(self._rules)

        for rule in rules:
            if rule.event_type != event.type:
                continue
            try:
                if not rule.condition(event):
                    continue
            except Exception as exc:
                _log.debug("Rule %s condition error: %s", rule.id, exc)
                continue

            publish(
                "orchestration.triggered",
                payload={"rule_id": rule.id, "source_event_id": event.id},
                actor_id=event.actor_id,
                execution_id=event.execution_id,
                approval_id=event.approval_id,
            )

            try:
                rule.action(event)
            except Exception as exc:
                _log.error("Rule %s action failed: %s", rule.id, exc)

    def can_replay(self, approval_id: str) -> bool:
        with self._lock:
            return self._replay_count.get(approval_id, 0) < self._max_replays

    def record_replay(self, approval_id: str) -> None:
        with self._lock:
            self._replay_count[approval_id] = self._replay_count.get(approval_id, 0) + 1

    def reset(self) -> None:
        with self._lock:
            self._rules.clear()
            self._processed.clear()
            self._pending_requests.clear()
            self._replay_count.clear()


def _build_replay_action(orchestrator: Orchestrator) -> Callable[[Event], None]:
    def replay_on_approval(event: Event) -> None:
        from dataclasses import replace as _replace

        from umh.execution.approval import get_approval_store
        from umh.execution.contract import (
            ExecutionContext,
            ExecutionRequest,
        )
        from umh.execution.engine import execute

        approval_id = event.approval_id
        if not approval_id:
            return

        if not orchestrator.can_replay(approval_id):
            _log.warning("Replay limit reached for approval %s", approval_id)
            return

        store = get_approval_store()
        approval = store.get(approval_id)
        if approval is None:
            return

        request_dict = orchestrator.get_pending_request(approval.execution_id)
        if request_dict is None:
            _log.debug("No pending request for execution %s", approval.execution_id)
            return

        orchestrator.record_replay(approval_id)

        original = ExecutionRequest.from_dict(request_dict)
        exec_id = f"exec_{uuid.uuid4().hex[:16]}"
        new_inputs = {**original.inputs, "approval_id": approval_id}
        new_context = _replace(
            original.context,
            metadata={
                **original.context.metadata,
                "replay_of": original.execution_id,
                "approval_id": approval_id,
            },
        )
        replayed = _replace(
            original,
            execution_id=exec_id,
            correlation_id=original.correlation_id,
            inputs=new_inputs,
            context=new_context,
            issued_at=_iso_now(),
            retry_count=original.retry_count + 1,
        )

        publish(
            "orchestration.executed",
            payload={
                "original_execution_id": original.execution_id,
                "replay_execution_id": exec_id,
                "approval_id": approval_id,
            },
            actor_id=event.actor_id,
            execution_id=exec_id,
            approval_id=approval_id,
        )

        result = execute(replayed)
        orchestrator.remove_pending_request(approval.execution_id)
        _log.info(
            "Replay complete: approval=%s exec=%s status=%s",
            approval_id,
            exec_id,
            result.status.value,
        )

    return replay_on_approval


def _build_approval_pending_action() -> Callable[[Event], None]:
    def log_pending_approval(event: Event) -> None:
        outputs = event.payload
        if not outputs.get("requires_approval"):
            return
        approval_id = outputs.get("approval_id", "")
        _log.info(
            "Execution requires approval: exec=%s approval=%s",
            event.execution_id,
            approval_id,
        )

    return log_pending_approval


def _build_task_resume_action() -> Callable[[Event], None]:
    def resume_paused_task(event: Event) -> None:
        from umh.orchestrator.task import find_paused_task_by_approval, resume_task

        approval_id = event.approval_id
        if not approval_id:
            return

        task = find_paused_task_by_approval(approval_id)
        if task is None:
            return

        _log.info(
            "Resuming paused task %s on approval %s",
            task.id,
            approval_id,
        )
        resume_task(task.id, approval_id)

    return resume_paused_task


def register_built_in_rules(orchestrator: Orchestrator) -> None:
    orchestrator.register_rule(
        Rule(
            id="builtin:resume_task_on_approval",
            event_type="approval.approved",
            condition=lambda e: True,
            action=_build_task_resume_action(),
            description="Resume a paused task when its approval is granted",
        )
    )
    orchestrator.register_rule(
        Rule(
            id="builtin:replay_on_approval",
            event_type="approval.approved",
            condition=lambda e: True,
            action=_build_replay_action(orchestrator),
            description="Re-execute original request when approval is granted",
        )
    )
    orchestrator.register_rule(
        Rule(
            id="builtin:log_pending_approval",
            event_type="execution.completed",
            condition=lambda e: (
                e.payload.get("status") == "rejected" and e.payload.get("requires_approval")
            ),
            action=_build_approval_pending_action(),
            description="Log when execution is blocked pending approval",
        )
    )


_orchestrator: Orchestrator | None = None
_orchestrator_lock = threading.Lock()
_started = False


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = Orchestrator()
    return _orchestrator


def start_orchestrator() -> Orchestrator:
    global _started
    orch = get_orchestrator()
    with _orchestrator_lock:
        if _started:
            return orch
        register_built_in_rules(orch)
        get_event_stream().subscribe(orch.handle_event)
        _started = True
    return orch


def reset_orchestrator() -> Orchestrator:
    global _orchestrator, _started
    with _orchestrator_lock:
        if _orchestrator is not None:
            get_event_stream().unsubscribe(_orchestrator.handle_event)
        _orchestrator = Orchestrator()
        _started = False
    return _orchestrator
