"""Orchestrator — execution coordinator for named workflows.

The Orchestrator is a thin registry + dispatcher:
  - `register_workflow(name, pipeline_or_callable)`
  - `run_workflow(name, context=...)`

It is NOT a scheduler. Cron/systemd/timers/signals/the autonomous loop
all sit *above* the orchestrator and call `run_workflow()` when the
right moment arrives.

State tracking is deliberately minimal: last run, last status, last
duration, per-workflow. Persisted to a single JSON file so the
autonomous loop can observe recent history without re-parsing logs.

Every execution goes through the Control Plane — either because the
workflow IS a `Pipeline` (and `run_pipeline` routes each step through
`run_action`), or because the workflow is a callable that is expected
to itself call `run_action` internally. The orchestrator never
executes side-effectful code directly.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable, Union

from core.action_system.logging import log_decision

from .pipeline import Pipeline, PipelineResult, run_pipeline

STATE_PATH = "/opt/OS/logs/orchestrator_state.json"

# A workflow is either a Pipeline (preferred) or a callable taking a
# context dict and returning a dict result. Callables must themselves
# go through run_action() for any side effects.
Workflow = Union[Pipeline, Callable[[dict[str, Any]], dict[str, Any]]]


@dataclass
class WorkflowRecord:
    name: str
    last_run_at: str | None = None
    last_status: str | None = None  # "ok" | "failed" | "deferred" | "rejected"
    last_duration_s: float | None = None
    total_runs: int = 0
    total_failures: int = 0


@dataclass
class Orchestrator:
    workflows: dict[str, Workflow] = field(default_factory=dict)
    state: dict[str, WorkflowRecord] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    # ----- registration -----

    def register_workflow(self, name: str, workflow: Workflow) -> None:
        with self._lock:
            self.workflows[name] = workflow
            self.state.setdefault(name, WorkflowRecord(name=name))

    def list_workflows(self) -> list[str]:
        with self._lock:
            return sorted(self.workflows.keys())

    # ----- execution -----

    def run_workflow(
        self,
        name: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a registered workflow by name.

        Returns a dict with keys:
          - name, ok, status, duration_s, result

        Raises KeyError if the workflow is not registered.
        """
        workflow = self.workflows.get(name)
        if workflow is None:
            raise KeyError(f"workflow not registered: {name!r}")

        log_decision(
            context=f"orchestrator.run_workflow({name})",
            options_considered=["run", "skip"],
            chosen_option="run",
            reasoning=f"Orchestrator dispatched workflow {name!r}.",
            source_agent="orchestrator",
        )

        started = time.time()
        ok: bool
        status: str
        payload: Any

        if isinstance(workflow, Pipeline):
            result: PipelineResult = run_pipeline(workflow, context=context)
            ok = result.ok
            # If any step deferred or was rejected, surface that
            # explicitly — orchestrator consumers need to distinguish
            # "failed" from "waiting on a human".
            statuses = {s.status for s in result.steps}
            if "deferred" in statuses:
                status = "deferred"
            elif "rejected" in statuses:
                status = "rejected"
            elif ok:
                status = "ok"
            else:
                status = "failed"
            payload = result.to_dict()
        else:
            try:
                raw = workflow(dict(context or {})) or {}
            except Exception as e:
                raw = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            ok = bool(raw.get("ok"))
            status = "ok" if ok else "failed"
            payload = raw

        finished = time.time()
        duration = round(finished - started, 4)

        self._record_run(name, status=status, duration_s=duration)

        return {
            "name": name,
            "ok": ok,
            "status": status,
            "duration_s": duration,
            "result": payload,
        }

    # ----- state tracking -----

    def _record_run(self, name: str, *, status: str, duration_s: float) -> None:
        with self._lock:
            rec = self.state.setdefault(name, WorkflowRecord(name=name))
            rec.last_run_at = datetime.now(timezone.utc).isoformat()
            rec.last_status = status
            rec.last_duration_s = duration_s
            rec.total_runs += 1
            if status != "ok":
                rec.total_failures += 1
            self._persist_unlocked()

    def _persist_unlocked(self) -> None:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        blob = {name: rec.__dict__ for name, rec in self.state.items()}
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(blob, f, indent=2, default=str)
        os.replace(tmp, STATE_PATH)

    def load_state(self) -> None:
        if not os.path.isfile(STATE_PATH):
            return
        try:
            with open(STATE_PATH) as f:
                blob = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        with self._lock:
            for name, data in blob.items():
                self.state[name] = WorkflowRecord(**data)

    def get_record(self, name: str) -> WorkflowRecord | None:
        with self._lock:
            return self.state.get(name)


# ---------------------------------------------------------------------------
# Module-level singleton — most callers want a single shared registry.
# ---------------------------------------------------------------------------

_default: Orchestrator | None = None


def default_orchestrator() -> Orchestrator:
    global _default
    if _default is None:
        _default = Orchestrator()
        _default.load_state()
    return _default


__all__ = [
    "Orchestrator",
    "Workflow",
    "WorkflowRecord",
    "default_orchestrator",
    "STATE_PATH",
]
