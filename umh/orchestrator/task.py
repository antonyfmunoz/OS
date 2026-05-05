"""UMH Task — multi-step execution graph with context passing.

A Task is an ordered list of TaskSteps. Each step executes through the
engine, and its outputs feed into subsequent steps via template resolution.

Templates use {{context.key}} or {{prev_output.key}} syntax.

Usage:
    from umh.orchestrator.task import Task, TaskStep, execute_task

    task = Task(steps=[
        TaskStep(operation="classify_intent", inputs_template={"prompt": "hello"}, output_key="classification"),
        TaskStep(operation="respond", inputs_template={"intent": "{{context.classification.outputs.response}}"}),
    ])
    result = execute_task(task)
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.core.clock import iso_now as _iso_now

_log = logging.getLogger(__name__)

_MAX_STEPS = 10


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class TaskStep:
    operation: str
    inputs_template: dict = field(default_factory=dict)
    output_key: str = ""
    execution_class: str = "llm_call"
    id: str = ""
    status: StepStatus = StepStatus.PENDING
    result: dict | None = None
    retry_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = f"step_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation": self.operation,
            "inputs_template": self.inputs_template,
            "output_key": self.output_key,
            "execution_class": self.execution_class,
            "status": self.status.value,
            "result": self.result,
            "retry_count": self.retry_count,
        }


@dataclass
class Task:
    steps: list[TaskStep]
    id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    current_step_index: int = 0
    context: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    issued_by: str = ""
    error: str = ""
    paused_step_index: int | None = None
    paused_approval_id: str = ""
    paused_request: dict | None = None
    paused_reason: str = ""
    pause_count: int = 0
    resumed_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()
        if not self.updated_at:
            self.updated_at = self.created_at
        if len(self.steps) > _MAX_STEPS:
            raise ValueError(f"Task exceeds max steps ({_MAX_STEPS})")

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "context": self.context,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "issued_by": self.issued_by,
            "error": self.error,
        }
        if self.status == TaskStatus.PAUSED or self.paused_step_index is not None:
            d["paused_step_index"] = self.paused_step_index
            d["paused_approval_id"] = self.paused_approval_id
            d["paused_reason"] = self.paused_reason
            d["pause_count"] = self.pause_count
            d["resumed_at"] = self.resumed_at
        return d


_TEMPLATE_RE = re.compile(r"\{\{([\w.]+)\}\}")


def _resolve_value(value: str, context: dict, prev_output: dict | None) -> str:
    """Resolve {{context.key}} and {{prev_output.key}} references."""
    if not isinstance(value, str):
        return value

    def _lookup(match: re.Match) -> str:
        path = match.group(1)
        parts = path.split(".")
        if parts[0] == "context":
            obj = context
            for p in parts[1:]:
                if isinstance(obj, dict):
                    obj = obj.get(p, "")
                else:
                    return match.group(0)
            return str(obj) if not isinstance(obj, str) else obj
        if parts[0] == "prev_output":
            if prev_output is None:
                return match.group(0)
            obj = prev_output
            for p in parts[1:]:
                if isinstance(obj, dict):
                    obj = obj.get(p, "")
                else:
                    return match.group(0)
            return str(obj) if not isinstance(obj, str) else obj
        return match.group(0)

    return _TEMPLATE_RE.sub(_lookup, value)


def resolve_inputs(template: dict, context: dict, prev_output: dict | None = None) -> dict:
    """Resolve all template references in an inputs dict."""
    resolved = {}
    for key, value in template.items():
        if isinstance(value, str):
            resolved[key] = _resolve_value(value, context, prev_output)
        elif isinstance(value, dict):
            resolved[key] = resolve_inputs(value, context, prev_output)
        else:
            resolved[key] = value
    return resolved


def enqueue_task(task: Task) -> Task:
    """Save a task as PENDING for background worker pickup. Does not execute."""
    task.status = TaskStatus.PENDING
    task.updated_at = _iso_now()
    _save_task(task)
    from umh.events.stream import publish as _publish_event

    _publish_event(
        "task.enqueued",
        payload={"task_id": task.id, "step_count": len(task.steps)},
        actor_id=task.issued_by,
    )
    return task


def execute_task(task: Task) -> Task:
    """Execute all steps in a task sequentially."""
    from umh.events.stream import publish as _publish_event
    from umh.execution.contract import (
        ExecutionClass,
        ExecutionConstraints,
        ExecutionContext,
        ExecutionRequest,
        ExecutionStatus,
        ExecutionTarget,
    )
    from umh.execution.engine import execute

    if len(task.steps) > _MAX_STEPS:
        task.status = TaskStatus.FAILED
        task.error = f"Exceeds max steps ({_MAX_STEPS})"
        return task

    task.status = TaskStatus.RUNNING
    task.updated_at = _iso_now()

    _publish_event(
        "task.started",
        payload={"task_id": task.id, "step_count": len(task.steps)},
        actor_id=task.issued_by,
    )

    prev_output: dict | None = None

    for i, step in enumerate(task.steps):
        task.current_step_index = i
        step.status = StepStatus.RUNNING
        task.updated_at = _iso_now()

        resolved_inputs = resolve_inputs(step.inputs_template, task.context, prev_output)

        exec_id = f"exec_{uuid.uuid4().hex[:16]}"

        _publish_event(
            "task.step.started",
            payload={
                "task_id": task.id,
                "step_id": step.id,
                "step_index": i,
                "operation": step.operation,
            },
            actor_id=task.issued_by,
            execution_id=exec_id,
        )

        request = ExecutionRequest(
            execution_id=exec_id,
            correlation_id=task.id,
            causal_event_id="",
            session_id="",
            operation=step.operation,
            inputs=resolved_inputs,
            execution_class=ExecutionClass(step.execution_class),
            constraints=ExecutionConstraints(timeout_s=30),
            target=ExecutionTarget(node_id="local", transport="task"),
            context=ExecutionContext(
                metadata={"task_id": task.id, "step_id": step.id, "step_index": i}
            ),
            issued_at=_iso_now(),
            issued_by=task.issued_by,
            idempotency_key="",
        )

        result = execute(request)
        result_dict = result.to_dict()
        step.result = result_dict

        if result.status != ExecutionStatus.SUCCEEDED:
            outputs = result_dict.get("outputs", {})
            if outputs.get("requires_approval") and outputs.get("approval_id"):
                step.status = StepStatus.WAITING_APPROVAL
                task.status = TaskStatus.PAUSED
                task.paused_step_index = i
                task.paused_approval_id = outputs["approval_id"]
                task.paused_request = request.to_dict()
                task.paused_reason = outputs.get("reason", "Requires approval")
                task.pause_count += 1
                task.updated_at = _iso_now()

                _publish_event(
                    "task.step.completed",
                    payload={
                        "task_id": task.id,
                        "step_id": step.id,
                        "step_index": i,
                        "status": "waiting_approval",
                        "approval_id": outputs["approval_id"],
                    },
                    actor_id=task.issued_by,
                    execution_id=exec_id,
                )

                _publish_event(
                    "task.paused",
                    payload={
                        "task_id": task.id,
                        "paused_step_index": i,
                        "approval_id": outputs["approval_id"],
                        "reason": task.paused_reason,
                    },
                    actor_id=task.issued_by,
                )

                _save_task(task)
                return task

            step.status = StepStatus.FAILED
            task.status = TaskStatus.FAILED
            task.error = (
                f"Step {i} ({step.operation}) failed: {result.error or result.status.value}"
            )
            task.updated_at = _iso_now()

            _publish_event(
                "task.step.completed",
                payload={
                    "task_id": task.id,
                    "step_id": step.id,
                    "step_index": i,
                    "status": "failed",
                },
                actor_id=task.issued_by,
                execution_id=exec_id,
            )

            for remaining in task.steps[i + 1 :]:
                remaining.status = StepStatus.SKIPPED

            _publish_event(
                "task.completed",
                payload={
                    "task_id": task.id,
                    "status": "failed",
                    "failed_step": i,
                },
                actor_id=task.issued_by,
            )
            _save_task(task)
            return task

        step.status = StepStatus.COMPLETED
        prev_output = result_dict.get("outputs", {})

        if step.output_key:
            task.context[step.output_key] = result_dict

        _publish_event(
            "task.step.completed",
            payload={
                "task_id": task.id,
                "step_id": step.id,
                "step_index": i,
                "status": "completed",
            },
            actor_id=task.issued_by,
            execution_id=exec_id,
        )

    task.status = TaskStatus.COMPLETED
    task.updated_at = _iso_now()

    _publish_event(
        "task.completed",
        payload={"task_id": task.id, "status": "completed", "steps_completed": len(task.steps)},
        actor_id=task.issued_by,
    )

    _save_task(task)
    return task


def resume_task(task_id: str, approval_id: str) -> Task | None:
    """Resume a paused task after its approval is granted.

    Validates the task is PAUSED and the approval_id matches, then re-executes
    from the paused step with the approval injected. Continues sequentially
    through remaining steps.
    """
    from umh.events.stream import publish as _publish_event
    from umh.execution.contract import (
        ExecutionRequest,
        ExecutionStatus,
    )
    from umh.execution.engine import execute

    task = get_task(task_id)
    if task is None:
        _log.warning("resume_task: task %s not found", task_id)
        return None

    if task.status != TaskStatus.PAUSED:
        _log.warning("resume_task: task %s status is %s, not PAUSED", task_id, task.status.value)
        return None

    if task.paused_approval_id != approval_id:
        _log.warning(
            "resume_task: approval mismatch on task %s: expected %s, got %s",
            task_id,
            task.paused_approval_id,
            approval_id,
        )
        return None

    if task.paused_request is None or task.paused_step_index is None:
        _log.error("resume_task: task %s missing pause state", task_id)
        return None

    paused_index = task.paused_step_index

    task.status = TaskStatus.RUNNING
    task.resumed_at = _iso_now()
    task.updated_at = _iso_now()

    _publish_event(
        "task.resumed",
        payload={
            "task_id": task.id,
            "resumed_step_index": paused_index,
            "approval_id": approval_id,
        },
        actor_id=task.issued_by,
    )

    original_request = ExecutionRequest.from_dict(task.paused_request)
    new_inputs = {**original_request.inputs, "approval_id": approval_id}

    from dataclasses import replace as _replace

    new_context_meta = {
        **original_request.context.metadata,
        "approval_id": approval_id,
        "resumed_from_pause": True,
    }
    new_context = _replace(original_request.context, metadata=new_context_meta)

    exec_id = f"exec_{uuid.uuid4().hex[:16]}"
    resumed_request = _replace(
        original_request,
        execution_id=exec_id,
        inputs=new_inputs,
        context=new_context,
        issued_at=_iso_now(),
        retry_count=original_request.retry_count + 1,
    )

    step = task.steps[paused_index]
    step.status = StepStatus.RUNNING
    task.current_step_index = paused_index

    result = execute(resumed_request)
    result_dict = result.to_dict()
    step.result = result_dict

    if result.status != ExecutionStatus.SUCCEEDED:
        outputs = result_dict.get("outputs", {})
        if outputs.get("requires_approval") and outputs.get("approval_id"):
            step.status = StepStatus.WAITING_APPROVAL
            task.status = TaskStatus.PAUSED
            task.paused_approval_id = outputs["approval_id"]
            task.paused_request = resumed_request.to_dict()
            task.paused_reason = outputs.get("reason", "Requires approval")
            task.pause_count += 1
            task.updated_at = _iso_now()
            _save_task(task)
            return task

        step.status = StepStatus.FAILED
        task.status = TaskStatus.FAILED
        task.error = (
            f"Step {paused_index} ({step.operation}) failed on resume: "
            f"{result.error or result.status.value}"
        )
        task.paused_step_index = None
        task.paused_approval_id = ""
        task.paused_request = None
        task.paused_reason = ""
        task.updated_at = _iso_now()

        for remaining in task.steps[paused_index + 1 :]:
            remaining.status = StepStatus.SKIPPED

        _publish_event(
            "task.completed",
            payload={"task_id": task.id, "status": "failed", "failed_step": paused_index},
            actor_id=task.issued_by,
        )
        _save_task(task)
        return task

    step.status = StepStatus.COMPLETED
    prev_output = result_dict.get("outputs", {})

    if step.output_key:
        task.context[step.output_key] = result_dict

    task.paused_step_index = None
    task.paused_approval_id = ""
    task.paused_request = None
    task.paused_reason = ""

    for j in range(paused_index + 1, len(task.steps)):
        next_step = task.steps[j]
        task.current_step_index = j
        next_step.status = StepStatus.RUNNING
        task.updated_at = _iso_now()

        resolved_inputs = resolve_inputs(next_step.inputs_template, task.context, prev_output)

        next_exec_id = f"exec_{uuid.uuid4().hex[:16]}"

        from umh.execution.contract import (
            ExecutionClass,
            ExecutionConstraints,
            ExecutionContext,
            ExecutionTarget,
        )

        next_request = ExecutionRequest(
            execution_id=next_exec_id,
            correlation_id=task.id,
            causal_event_id="",
            session_id="",
            operation=next_step.operation,
            inputs=resolved_inputs,
            execution_class=ExecutionClass(next_step.execution_class),
            constraints=ExecutionConstraints(timeout_s=30),
            target=ExecutionTarget(node_id="local", transport="task"),
            context=ExecutionContext(
                metadata={"task_id": task.id, "step_id": next_step.id, "step_index": j}
            ),
            issued_at=_iso_now(),
            issued_by=task.issued_by,
            idempotency_key="",
        )

        next_result = execute(next_request)
        next_result_dict = next_result.to_dict()
        next_step.result = next_result_dict

        if next_result.status != ExecutionStatus.SUCCEEDED:
            next_outputs = next_result_dict.get("outputs", {})
            if next_outputs.get("requires_approval") and next_outputs.get("approval_id"):
                next_step.status = StepStatus.WAITING_APPROVAL
                task.status = TaskStatus.PAUSED
                task.paused_step_index = j
                task.paused_approval_id = next_outputs["approval_id"]
                task.paused_request = next_request.to_dict()
                task.paused_reason = next_outputs.get("reason", "Requires approval")
                task.pause_count += 1
                task.updated_at = _iso_now()

                _publish_event(
                    "task.paused",
                    payload={
                        "task_id": task.id,
                        "paused_step_index": j,
                        "approval_id": next_outputs["approval_id"],
                    },
                    actor_id=task.issued_by,
                )
                _save_task(task)
                return task

            next_step.status = StepStatus.FAILED
            task.status = TaskStatus.FAILED
            task.error = (
                f"Step {j} ({next_step.operation}) failed: "
                f"{next_result.error or next_result.status.value}"
            )
            task.updated_at = _iso_now()

            for remaining in task.steps[j + 1 :]:
                remaining.status = StepStatus.SKIPPED

            _publish_event(
                "task.completed",
                payload={"task_id": task.id, "status": "failed", "failed_step": j},
                actor_id=task.issued_by,
            )
            _save_task(task)
            return task

        next_step.status = StepStatus.COMPLETED
        prev_output = next_result_dict.get("outputs", {})

        if next_step.output_key:
            task.context[next_step.output_key] = next_result_dict

    task.status = TaskStatus.COMPLETED
    task.updated_at = _iso_now()

    _publish_event(
        "task.completed",
        payload={"task_id": task.id, "status": "completed", "steps_completed": len(task.steps)},
        actor_id=task.issued_by,
    )
    _save_task(task)
    return task


def cancel_task(task_id: str) -> Task | None:
    """Cancel a PENDING or PAUSED task.

    RUNNING/COMPLETED/FAILED/CANCELLED tasks cannot be cancelled.
    Sets remaining steps to SKIPPED and emits ``task.cancelled``.
    """
    from umh.events.stream import publish as _publish_event

    task = get_task(task_id)
    if task is None:
        _log.warning("cancel_task: task %s not found", task_id)
        return None

    if task.status not in (TaskStatus.PENDING, TaskStatus.PAUSED):
        _log.warning(
            "cancel_task: task %s status is %s, cannot cancel",
            task_id,
            task.status.value,
        )
        return None

    task.status = TaskStatus.CANCELLED
    task.updated_at = _iso_now()

    for step in task.steps:
        if step.status in (StepStatus.PENDING, StepStatus.WAITING_APPROVAL):
            step.status = StepStatus.SKIPPED

    _publish_event(
        "task.cancelled",
        payload={"task_id": task.id},
        actor_id=task.issued_by,
    )

    _save_task(task)
    return task


def retry_task(task_id: str) -> Task | None:
    """Retry a FAILED task by creating a new task with the same steps.

    Only FAILED tasks can be retried. The new task's context includes
    ``retried_from`` pointing to the original task_id.
    """
    from umh.events.stream import publish as _publish_event

    task = get_task(task_id)
    if task is None:
        _log.warning("retry_task: task %s not found", task_id)
        return None

    if task.status != TaskStatus.FAILED:
        _log.warning(
            "retry_task: task %s status is %s, only FAILED can be retried",
            task_id,
            task.status.value,
        )
        return None

    fresh_steps = [
        TaskStep(
            operation=s.operation,
            inputs_template=dict(s.inputs_template),
            output_key=s.output_key,
            execution_class=s.execution_class,
        )
        for s in task.steps
    ]

    new_context = dict(task.context)
    new_context["retried_from"] = task.id

    new_task = Task(
        steps=fresh_steps,
        context=new_context,
        issued_by=task.issued_by,
    )

    _publish_event(
        "task.retried",
        payload={"task_id": task.id, "new_task_id": new_task.id},
        actor_id=task.issued_by,
    )

    enqueue_task(new_task)
    return new_task


_tasks: dict[str, Task] = {}
_tasks_lock = threading.Lock()


def _save_task(task: Task) -> None:
    with _tasks_lock:
        _tasks[task.id] = task
    try:
        from umh.orchestrator.task_store import get_task_store

        get_task_store().save(task)
    except Exception as exc:
        _log.error("Failed to persist task %s to store: %s", task.id, exc)


def get_task(task_id: str) -> Task | None:
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is not None:
        return task
    try:
        from umh.orchestrator.task_store import get_task_store

        return get_task_store().get(task_id)
    except Exception:
        return None


def list_tasks() -> list[Task]:
    try:
        from umh.orchestrator.task_store import get_task_store

        return get_task_store().list_all()
    except Exception:
        with _tasks_lock:
            return list(_tasks.values())


def find_paused_task_by_approval(approval_id: str) -> Task | None:
    """Find a PAUSED task waiting on the given approval_id."""
    with _tasks_lock:
        for task in _tasks.values():
            if task.status == TaskStatus.PAUSED and task.paused_approval_id == approval_id:
                return task
    try:
        from umh.orchestrator.task_store import get_task_store

        for task in get_task_store().list_by_status(TaskStatus.PAUSED):
            if task.paused_approval_id == approval_id:
                return task
    except Exception:
        pass
    return None


def reset_tasks() -> None:
    with _tasks_lock:
        _tasks.clear()
    try:
        from umh.orchestrator.task_store import get_task_store

        get_task_store().reset()
    except Exception:
        pass
