"""Execution workflow — governed task lifecycle tracking.

Wraps coding/execution sessions so the organism learns from dev work.
Does NOT replace Claude Code — captures the task lifecycle around it.

Steps: define_task → record_start → record_completion → record_outcome
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _runtime_state_file(subsystem: str, filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(subsystem, filename, create_parent=False))


_TASKS_DIR = os.path.join(_REPO_ROOT, "data", "umh", "tasks")


@dataclass
class TaskRecord:
    task_id: str = ""
    description: str = ""
    status: str = "defined"
    started_at: str = ""
    completed_at: str = ""
    outcome: str = ""
    files_changed: list[str] = field(default_factory=list)


class ExecutionWorkflow:
    """Task lifecycle workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._task: TaskRecord | None = None

    def steps_define(self, description: str) -> list[WorkflowStep]:
        """Steps for defining a new task."""
        return [
            WorkflowStep(
                name="define_task",
                mutation_name="work_packet_create",
                intent=f"Define task: {description[:80]}",
                execute_fn=lambda: self._define_task(description),
            ),
            WorkflowStep(
                name="record_start",
                mutation_name="work_packet_update",
                intent=f"Start task: {description[:80]}",
                execute_fn=self._record_start,
            ),
        ]

    def steps_complete(self, summary: str = "") -> list[WorkflowStep]:
        """Steps for completing the current task."""
        return [
            WorkflowStep(
                name="record_completion",
                mutation_name="work_packet_update",
                intent=f"Complete task: {summary[:80] or 'current task'}",
                execute_fn=lambda: self._record_completion(summary),
            ),
            WorkflowStep(
                name="record_outcome",
                mutation_name="outcome_record",
                intent=f"Record outcome: {summary[:80] or 'task outcome'}",
                execute_fn=self._record_outcome,
            ),
        ]

    def _define_task(self, description: str) -> tuple[str, bool]:
        now = datetime.now(timezone.utc)
        task_id = f"task-{now.strftime('%Y%m%d-%H%M%S')}"
        self._task = TaskRecord(
            task_id=task_id,
            description=description,
            status="defined",
        )

        os.makedirs(_TASKS_DIR, exist_ok=True)
        task_path = os.path.join(_TASKS_DIR, f"{task_id}.json")
        with open(task_path, "w") as f:
            json.dump(
                {
                    "task_id": task_id,
                    "description": description,
                    "status": "defined",
                    "created_at": now.isoformat(),
                    "org_id": self._org_id,
                    "venture_id": self._venture_id,
                },
                f,
                indent=2,
            )

        return (f"Task defined: {task_id} — {description[:100]}", True)

    def _record_start(self) -> tuple[str, bool]:
        if not self._task:
            return ("no task defined", False)

        now = datetime.now(timezone.utc)
        self._task.status = "in_progress"
        self._task.started_at = now.isoformat()

        task_path = os.path.join(_TASKS_DIR, f"{self._task.task_id}.json")
        if os.path.exists(task_path):
            with open(task_path) as f:
                data = json.load(f)
            data["status"] = "in_progress"
            data["started_at"] = now.isoformat()
            with open(task_path, "w") as f:
                json.dump(data, f, indent=2)

        return (f"Task started: {self._task.task_id}", True)

    def _record_completion(self, summary: str) -> tuple[str, bool]:
        if not self._task:
            task = self._load_latest_task()
            if task:
                self._task = task
            else:
                return ("no active task found", False)

        now = datetime.now(timezone.utc)
        self._task.status = "completed"
        self._task.completed_at = now.isoformat()
        self._task.outcome = summary

        task_path = os.path.join(_TASKS_DIR, f"{self._task.task_id}.json")
        if os.path.exists(task_path):
            with open(task_path) as f:
                data = json.load(f)
            data["status"] = "completed"
            data["completed_at"] = now.isoformat()
            data["summary"] = summary
            with open(task_path, "w") as f:
                json.dump(data, f, indent=2)

        return (f"Task completed: {self._task.task_id} — {summary[:100]}", True)

    def _record_outcome(self) -> tuple[str, bool]:
        if not self._task:
            return ("no task to record outcome for", False)

        outcome_path = _runtime_state_file("organism", "outcome_learning.jsonl")
        os.makedirs(os.path.dirname(outcome_path), exist_ok=True)

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "task_outcome",
            "task_id": self._task.task_id,
            "description": self._task.description,
            "outcome": self._task.outcome or "completed",
            "status": self._task.status,
        }

        try:
            with open(outcome_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.debug("outcome write failed: %s", exc)

        return (
            f"Outcome recorded for {self._task.task_id}: {self._task.outcome[:100]}",
            True,
        )

    def _load_latest_task(self) -> TaskRecord | None:
        if not os.path.isdir(_TASKS_DIR):
            return None
        task_files = sorted(
            [f for f in os.listdir(_TASKS_DIR) if f.endswith(".json")],
            reverse=True,
        )
        for tf in task_files:
            try:
                with open(os.path.join(_TASKS_DIR, tf)) as f:
                    data = json.load(f)
                if data.get("status") == "in_progress":
                    return TaskRecord(
                        task_id=data["task_id"],
                        description=data.get("description", ""),
                        status=data.get("status", ""),
                        started_at=data.get("started_at", ""),
                    )
            except (json.JSONDecodeError, OSError, KeyError):
                continue
        return None
