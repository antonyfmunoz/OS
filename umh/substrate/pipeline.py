"""
Composition pipeline — intent-level multi-step workflow execution.

Sits ABOVE the existing task_pipeline / pipeline_execution layer.
Converts structured intent into a sequence of typed steps, executes
them sequentially, and tracks per-step status and structured output.

Does NOT replace task_pipeline.py (task decomposition) or
pipeline_execution.py (tmux/local-control dispatch). This module
is the *intent → workflow → handler* layer; the existing modules
are the *task → agent-step → dispatch* layer.

Design rules (mirror substrate conventions):
- Additive only — never touches existing modules.
- Deterministic — no LLM calls in the pipeline runner itself.
- Best-effort — step failures captured, never raised.
- Sequential only — no DAG, no parallelism (MVP).
- Structured output — every step returns a typed result dict.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from umh.substrate.dispatch_enforcement import (
    ExecutionStatus as _EnforcementStatus,
    check_denied,
    log_enforcement_trace,
)
from umh.substrate.discord_output_policy import PermissionDecision
from umh.substrate.event_spine import EventStatus, EventType, create_event
from umh.substrate.event_store import get_event_store


# ─── Constants ────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.pipeline]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "cp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Enums ────────────────────────────────────────────────────────────────────


class StepStatus(str, Enum):
    """Lifecycle of a single pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineRunStatus(str, Enum):
    """Lifecycle of the entire pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# ─── StepResult ──────────────────────────────────────────────────────────────


@dataclass
class StepResult:
    """Structured output from a single step execution."""

    status: str  # "succeeded" | "failed"
    result: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


# ─── PipelineStep ─────────────────────────────────────────────────────────────


@dataclass
class PipelineStep:
    """A single step in a composition pipeline."""

    id: str
    name: str
    handler: str  # handler function name in step_handlers registry
    requirements: list[str] = field(default_factory=list)
    input_data: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[StepResult] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "handler": self.handler,
            "requirements": self.requirements,
            "input_data": self.input_data,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def new(
        cls,
        name: str,
        handler: str,
        *,
        requirements: Optional[list[str]] = None,
        input_data: Optional[dict[str, Any]] = None,
    ) -> "PipelineStep":
        """Create a new step with generated ID."""
        return cls(
            id=_new_id("step"),
            name=name,
            handler=handler,
            requirements=requirements or [],
            input_data=input_data or {},
        )


# ─── Pipeline ─────────────────────────────────────────────────────────────────


# Handler registry: handler_name → callable(step, context) → StepResult
# Populated by step_handlers.py at import time
_HANDLER_REGISTRY: dict[str, Callable[["PipelineStep", dict], StepResult]] = {}


def register_handler(
    name: str, fn: Callable[["PipelineStep", dict], StepResult]
) -> None:
    """Register a step handler function by name."""
    _HANDLER_REGISTRY[name] = fn


def get_handler(name: str) -> Optional[Callable[["PipelineStep", dict], StepResult]]:
    """Retrieve a registered handler by name."""
    return _HANDLER_REGISTRY.get(name)


@dataclass
class Pipeline:
    """An ordered sequence of steps that execute a user intent."""

    id: str
    name: str
    steps: list[PipelineStep] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    status: PipelineRunStatus = PipelineRunStatus.PENDING
    created_at: str = field(default_factory=_utcnow)
    finished_at: Optional[str] = None

    @classmethod
    def new(
        cls,
        name: str,
        steps: list[PipelineStep],
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> "Pipeline":
        """Create a new pipeline with generated ID."""
        return cls(
            id=_new_id("pipe"),
            name=name,
            steps=list(steps),
            context=context or {},
        )

    def run(self) -> dict[str, Any]:
        """Execute all steps sequentially.

        Each step's output is available to subsequent steps via the
        pipeline context under the key ``step_results.<step_name>``.

        Emits pipeline_created spine event at start.  Each step emits
        step_started and step_completed events.  All events carry the
        correlation_id from ``self.context.get("correlation_id")``.

        Returns:
            Final pipeline result dict with status, step results,
            and any error information.
        """
        _log(f"pipeline start: {self.name} ({self.id}) — {len(self.steps)} steps")
        self.status = PipelineRunStatus.RUNNING

        store = get_event_store()
        corr_id = self.context.get("correlation_id", "")

        # Emit pipeline_created event
        if corr_id:
            pipe_event = create_event(
                EventType.PIPELINE_CREATED,
                source="pipeline",
                source_session=self.context.get("source_session", ""),
                correlation_id=corr_id,
                payload={
                    "pipeline_id": self.id,
                    "pipeline_name": self.name,
                    "step_count": len(self.steps),
                },
            )
            pipe_event.update_status(EventStatus.PROCESSING)
            store.append(pipe_event)

        for i, step in enumerate(self.steps):
            step_result = self.run_step(step, step_index=i)

            if step_result.status == "failed":
                self.status = PipelineRunStatus.FAILED
                self.finished_at = _utcnow()
                _log(
                    f"pipeline failed: {self.name} ({self.id}) at step "
                    f"{i}/{len(self.steps)} '{step.name}': {step_result.error}"
                )
                return self.to_dict()

        self.status = PipelineRunStatus.SUCCEEDED
        self.finished_at = _utcnow()
        _log(
            f"pipeline succeeded: {self.name} ({self.id}) — "
            f"all {len(self.steps)} steps completed"
        )
        return self.to_dict()

    def run_step(self, step: PipelineStep, *, step_index: int = 0) -> StepResult:
        """Execute a single step using its registered handler.

        Enforcement: if ``self.context["_enforcement_decision"]`` contains a
        PermissionDecision, the step is deny-checked before handler dispatch.
        A denied decision short-circuits immediately — the handler never runs.

        Emits step_started and step_completed spine events if a
        correlation_id is present in the pipeline context.

        Args:
            step: The step to execute.
            step_index: Position in the pipeline (for logging).

        Returns:
            StepResult with status, result data, and optional error.
        """
        _log(
            f"  step {step_index + 1}/{len(self.steps)} start: "
            f"'{step.name}' (handler={step.handler})"
        )
        step.status = StepStatus.RUNNING
        step.started_at = _utcnow()

        # ── Enforcement: deny check before handler dispatch ──────────
        decision: PermissionDecision | None = self.context.get("_enforcement_decision")
        enforcement_active = decision is not None

        if decision is not None:
            denied = check_denied(decision)
            if denied is not None:
                error_msg = f"denied by policy: {denied.control_reason}"
                _log(
                    f"  step {step_index + 1}/{len(self.steps)} DENIED: "
                    f"'{step.name}' — {error_msg}"
                )
                step.status = StepStatus.FAILED
                step.error = error_msg
                step.finished_at = _utcnow()
                result = StepResult(
                    status="failed",
                    error=error_msg,
                    result={
                        "enforcement": "dispatch_enforcement",
                        "enforcement_status": "denied",
                        "control_reason": denied.control_reason,
                    },
                )
                step.result = result
                return result

        store = get_event_store()
        corr_id = self.context.get("correlation_id", "")

        # Emit step_started spine event
        step_event_id = ""
        if corr_id:
            step_event = create_event(
                EventType.STEP_STARTED,
                source="pipeline",
                source_session=self.context.get("source_session", ""),
                correlation_id=corr_id,
                payload={
                    "pipeline_id": self.id,
                    "step_id": step.id,
                    "step_name": step.name,
                    "step_index": step_index,
                    "handler": step.handler,
                    "enforcement_active": enforcement_active,
                },
            )
            step_event.update_status(EventStatus.PROCESSING)
            store.append(step_event)
            step_event_id = step_event.event_id

        handler = get_handler(step.handler)
        if handler is None:
            error_msg = f"no handler registered for '{step.handler}'"
            _log(f"  step {step_index + 1}/{len(self.steps)} failed: {error_msg}")
            step.status = StepStatus.FAILED
            step.error = error_msg
            step.finished_at = _utcnow()
            result = StepResult(status="failed", error=error_msg)
            step.result = result
            if step_event_id:
                store.update_status(
                    step_event_id, EventStatus.FAILED, {"error": error_msg}
                )
            return result

        try:
            result = handler(step, self.context)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"handler exception: {exc}"
            _log(f"  step {step_index + 1}/{len(self.steps)} failed: {error_msg}")
            step.status = StepStatus.FAILED
            step.error = error_msg
            step.finished_at = _utcnow()
            result = StepResult(status="failed", error=error_msg)
            step.result = result
            if step_event_id:
                store.update_status(
                    step_event_id, EventStatus.FAILED, {"error": error_msg}
                )
            return result

        # Inject enforcement metadata into result if enforcement is active
        if enforcement_active and result.result is not None:
            result.result.setdefault("enforcement", "dispatch_enforcement")
            result.result.setdefault(
                "enforcement_active",
                True,
            )

        step.result = result
        step.finished_at = _utcnow()

        if result.status == "succeeded":
            step.status = StepStatus.SUCCEEDED
            # Store result in pipeline context for downstream steps
            self.context.setdefault("step_results", {})[step.name] = result.result
            _log(f"  step {step_index + 1}/{len(self.steps)} succeeded: '{step.name}'")
            # Emit step_completed spine event
            if step_event_id:
                completed_event = create_event(
                    EventType.STEP_COMPLETED,
                    source="pipeline",
                    source_session=self.context.get("source_session", ""),
                    correlation_id=corr_id,
                    parent_event_id=step_event_id,
                    payload={
                        "step_id": step.id,
                        "step_name": step.name,
                        "step_index": step_index,
                        "enforcement_active": enforcement_active,
                    },
                )
                completed_event.update_status(EventStatus.COMPLETED)
                store.append(completed_event)
        else:
            step.status = StepStatus.FAILED
            step.error = result.error
            _log(
                f"  step {step_index + 1}/{len(self.steps)} failed: "
                f"'{step.name}' — {result.error}"
            )
            if step_event_id:
                store.update_status(
                    step_event_id, EventStatus.FAILED, {"error": result.error}
                )

        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize pipeline to a structured dict."""
        # Determine enforcement mode for traceability
        has_decision = "_enforcement_decision" in self.context
        enforcement_mode = "enforced" if has_decision else "legacy"

        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "enforcement_mode": enforcement_mode,
            "steps": [s.to_dict() for s in self.steps],
            "context": {
                k: v
                for k, v in self.context.items()
                if k not in ("step_results", "_enforcement_decision")
            },
            "step_results": self.context.get("step_results", {}),
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "StepStatus",
    "PipelineRunStatus",
    "StepResult",
    "PipelineStep",
    "Pipeline",
    "register_handler",
    "get_handler",
]
