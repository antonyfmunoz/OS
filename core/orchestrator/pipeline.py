"""Pipeline — sequential composition of Control Plane actions.

A Pipeline is an ordered list of Steps. Each Step either:
  - wraps a direct call to `run_action()` via an ActionStep descriptor, OR
  - wraps a plain Python callable that receives the shared context dict
    and returns a result dict (FuncStep).

The shared `context` dict flows through every step. Each step's result is
written back to `context[step.name]` so later steps can reference outputs
from earlier steps. This is the simplest possible composition model and
avoids reinventing a DAG engine.

Execution rules:
  - Steps run sequentially.
  - If `stop_on_fail=True` (default), any step whose result is not "ok"
    halts the pipeline. Later steps are marked "skipped".
  - Every ActionStep goes through `run_action()` — idempotency,
    validation, deferral, notification all still apply.
  - The pipeline itself logs a single decision record at completion so
    the audit trail shows *why* the sequence ran and how it ended.

This module is intentionally small. Complex orchestration (events,
loops, retries) lives in higher layers that call `run_pipeline()`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.action_system.control_plane import run_action
from core.action_system.logging import log_decision


# ---------------------------------------------------------------------------
# Step descriptors
# ---------------------------------------------------------------------------


@dataclass
class ActionStep:
    """A pipeline step that dispatches through `run_action()`.

    All keyword arguments map 1:1 to `run_action()` parameters. The
    `inputs_fn` hook lets a step derive its inputs from the running
    context — useful when step N depends on output from step N-1.
    """

    name: str
    type: str
    description: str
    inputs: dict[str, Any] | None = None
    inputs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    expected_output: str = ""
    risk_level: str = "low"
    source_agent: str = "orchestrator"
    explicit_approval: bool = False
    consult_tme: bool = False
    business_action_type: str | None = None
    idempotency_key: str | None = None
    idempotency_key_fn: Callable[[dict[str, Any]], str] | None = None
    idempotency_ttl_seconds: int | None = None


@dataclass
class FuncStep:
    """A pipeline step that runs a plain Python callable.

    The callable receives the shared `context` dict and must return a
    dict. Convention: include an `"ok"` key so `stop_on_fail` can tell
    success from failure uniformly with ActionStep results.

    FuncSteps do NOT go through `run_action()`. Use them sparingly — for
    pure in-memory transforms (e.g. shaping data between two actions).
    Side-effectful work belongs in an ActionStep.
    """

    name: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]


Step = ActionStep | FuncStep


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@dataclass
class Pipeline:
    name: str
    steps: list[Step]
    stop_on_fail: bool = True
    source_agent: str = "orchestrator"


@dataclass
class StepOutcome:
    name: str
    status: str  # "ok" | "failed" | "skipped" | "deferred" | "rejected"
    result: dict[str, Any] = field(default_factory=dict)
    action_id: str | None = None


@dataclass
class PipelineResult:
    name: str
    ok: bool
    started_at: float
    finished_at: float
    steps: list[StepOutcome]
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.finished_at - self.started_at, 4),
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "action_id": s.action_id,
                    "result": s.result,
                }
                for s in self.steps
            ],
        }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _run_action_step(step: ActionStep, context: dict[str, Any]) -> StepOutcome:
    inputs = step.inputs_fn(context) if step.inputs_fn else (step.inputs or {})
    idem = (
        step.idempotency_key_fn(context)
        if step.idempotency_key_fn
        else step.idempotency_key
    )

    action = run_action(
        type=step.type,
        description=step.description,
        inputs=inputs,
        expected_output=step.expected_output,
        risk_level=step.risk_level,
        source_agent=step.source_agent,
        explicit_approval=step.explicit_approval,
        consult_tme=step.consult_tme,
        business_action_type=step.business_action_type,
        idempotency_key=idem,
        idempotency_ttl_seconds=step.idempotency_ttl_seconds,
    )

    # Translate Action.status into pipeline-level semantics.
    result = action.result or {}
    if action.status == "executed":
        pipe_status = "ok"
    elif action.status == "skipped_duplicate":
        # Duplicate suppression is a success for pipeline purposes — the
        # work either already ran or is already in flight.
        pipe_status = "ok" if result.get("ok") else "failed"
    elif action.status == "deferred":
        pipe_status = "deferred"
    elif action.status == "rejected":
        pipe_status = "rejected"
    else:
        pipe_status = "failed"

    return StepOutcome(
        name=step.name,
        status=pipe_status,
        result=result,
        action_id=action.id,
    )


def _run_func_step(step: FuncStep, context: dict[str, Any]) -> StepOutcome:
    try:
        result = step.fn(context) or {}
    except Exception as e:
        return StepOutcome(
            name=step.name,
            status="failed",
            result={"ok": False, "error": f"{type(e).__name__}: {e}"},
        )
    if not isinstance(result, dict):
        result = {"ok": True, "value": result}
    status = "ok" if result.get("ok", True) else "failed"
    return StepOutcome(name=step.name, status=status, result=result)


def run_pipeline(
    pipeline: Pipeline,
    context: dict[str, Any] | None = None,
) -> PipelineResult:
    """Execute a pipeline sequentially.

    Returns a PipelineResult with per-step outcomes. Every ActionStep
    still passes through the full Control Plane, so idempotency,
    validation, deferral, and logging behave exactly as they do for a
    bare `run_action()` call.
    """
    ctx: dict[str, Any] = dict(context or {})
    outcomes: list[StepOutcome] = []
    started = time.time()
    halted = False

    for step in pipeline.steps:
        if halted:
            outcomes.append(StepOutcome(name=step.name, status="skipped"))
            continue

        if isinstance(step, ActionStep):
            outcome = _run_action_step(step, ctx)
        elif isinstance(step, FuncStep):
            outcome = _run_func_step(step, ctx)
        else:  # pragma: no cover - type guard
            outcome = StepOutcome(
                name=getattr(step, "name", "unknown"),
                status="failed",
                result={
                    "ok": False,
                    "error": f"unknown step type: {type(step).__name__}",
                },
            )

        ctx[outcome.name] = outcome.result
        outcomes.append(outcome)

        if pipeline.stop_on_fail and outcome.status not in ("ok",):
            halted = True

    finished = time.time()
    ok = all(o.status == "ok" for o in outcomes)

    # Single pipeline-level decision record. Keeps the audit trail linking
    # the choice-to-run back to the individual action logs.
    log_decision(
        context=f"pipeline:{pipeline.name}",
        options_considered=["run pipeline", "skip"],
        chosen_option="run pipeline",
        reasoning=(
            f"Pipeline {pipeline.name!r} executed {len(outcomes)} step(s); "
            f"ok={ok}; stop_on_fail={pipeline.stop_on_fail}."
        ),
        related_action_id=None,
        source_agent=pipeline.source_agent,
    )

    return PipelineResult(
        name=pipeline.name,
        ok=ok,
        started_at=started,
        finished_at=finished,
        steps=outcomes,
        context=ctx,
    )


__all__ = [
    "ActionStep",
    "FuncStep",
    "Step",
    "Pipeline",
    "PipelineResult",
    "StepOutcome",
    "run_pipeline",
]
