"""
Pipeline execution engine — step-level execution, retry, and resume.

Executes pipelines one step at a time using the existing capability routing
and tmux-backed dispatch infrastructure. Steps transition through typed
states with step-level retry and operator-block detection.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort — execution failures captured, never raised.
- Deterministic state transitions — no ambiguous intermediate states.
- Restart-safe — all state persisted via PipelineStore after each step.
- Step-level retry — max 2 retries per step before pipeline pauses.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from eos_ai.transport.task_pipeline import (
    PipelineStatus,
    PipelineStore,
    PipelineStep,
    StepStatus,
    TaskPipeline,
    _MAX_STEP_RETRIES,
)

if TYPE_CHECKING:
    from eos_ai.transport.operator_session import OperatorSession


def _log(msg: str) -> None:
    print(f"[substrate.pipeline_execution] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Streaming Events ──────────────────────────────────────────────────────


def _stream_step_event(
    event_type_name: str,
    message: str,
    *,
    pipeline: "TaskPipeline",
    step: "PipelineStep",
) -> None:
    """Best-effort streaming event emission for pipeline steps."""
    try:
        from eos_ai.platforms.eos.streaming_bridge import StreamEventType, stream_event

        type_map = {
            "step_started": StreamEventType.STEP_STARTED,
            "step_completed": StreamEventType.STEP_COMPLETED,
            "error": StreamEventType.ERROR,
        }
        etype = type_map.get(event_type_name, StreamEventType.INFO)
        stream_event(
            etype,
            message,
            payload={
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_title": pipeline.title,
                "step_id": step.step_id,
                "step_index": str(step.step_index),
                "step_title": step.title or "",
            },
            source="pipeline_execution",
        )
    except Exception as exc:
        _log(f"stream step event failed: {exc}")


# ─── Local Control Action Detection ──────────────────────────────────────────

_BROWSER_KEYWORDS = frozenset(
    {
        "browser_open",
        "browser_click",
        "browser_type",
        "browser_extract",
        "open_url",
        "navigate",
        "screenshot",
    }
)
_MACHINE_KEYWORDS = frozenset(
    {
        "machine_open_app",
        "machine_focus_app",
        "machine_open_scene",
        "machine_type_text",
        "machine_click",
        "machine_press_keys",
        "open_app",
        "focus_app",
        "open_scene",
    }
)


def _map_keyword_to_action(
    keyword: str, rest: str, step: PipelineStep
) -> Optional[tuple[str, dict]]:
    """Map a detected keyword to a (LocalControlAction value, payload) tuple.

    Args:
        keyword: The action keyword extracted from step title.
        rest: The text after "keyword:" in the step title.
        step: The pipeline step (unused currently, reserved for future context).

    Returns:
        (action_value, payload) or None if keyword is unrecognised.
    """
    rest = rest.strip()

    # Browser actions
    if keyword in ("browser_open", "open_url", "navigate"):
        return ("open_url", {"url": rest})
    if keyword == "browser_click":
        return ("click_mouse", {"selector": rest})
    if keyword == "browser_type":
        parts = rest.split(None, 1)
        selector = parts[0] if parts else ""
        text = parts[1] if len(parts) > 1 else ""
        return ("type_text", {"selector": selector, "text": text})
    if keyword == "browser_extract":
        return ("read_screen_state", {"selector": rest})
    if keyword == "screenshot":
        return ("read_screen_state", {})

    # Machine actions
    if keyword in ("machine_open_app", "open_app"):
        return ("open_app", {"app_id": rest})
    if keyword in ("machine_focus_app", "focus_app"):
        return ("focus_app", {"app_id": rest})
    if keyword in ("machine_open_scene", "open_scene"):
        return ("open_scene", {"scene_name": rest})
    if keyword == "machine_type_text":
        return ("type_text", {"text": rest})
    if keyword == "machine_click":
        return ("click_mouse", {"selector": rest})
    if keyword == "machine_press_keys":
        return ("press_keys", {"keys": rest})

    return None


def _detect_local_control_action(
    step: PipelineStep,
) -> Optional[tuple[str, dict]]:
    """Check if a step title starts with a local control action keyword.

    Expected format: "keyword: payload_text"
    e.g. "browser_open: https://example.com" or "open_app: OBS"

    Returns:
        (LocalControlAction value string, payload dict) or None.
    """
    title = step.title or ""
    # Check for "keyword:" prefix
    colon_idx = title.find(":")
    if colon_idx < 1:
        return None

    candidate = title[:colon_idx].strip().lower()
    rest = title[colon_idx + 1 :]

    all_keywords = _BROWSER_KEYWORDS | _MACHINE_KEYWORDS
    if candidate not in all_keywords:
        return None

    return _map_keyword_to_action(candidate, rest, step)


def _execute_local_control_step(
    step: PipelineStep,
    action_value: str,
    payload: dict,
    *,
    dry_run: bool = False,
) -> PipelineStep:
    """Dispatch a pipeline step through local control instead of tmux.

    Args:
        step: The pipeline step being executed.
        action_value: The LocalControlAction enum value string.
        payload: The action payload dict.
        dry_run: If True, mark completed without dispatching.

    Returns:
        The updated step with status set.
    """
    if dry_run:
        step.status = StepStatus.COMPLETED
        step.execution_result = f"dry_run — local_control: {action_value}"
        step.execution_finished_at = _utcnow()
        step.updated_at = _utcnow()
        return step

    try:
        from eos_ai.transport.local_control import (
            LocalControlAction,
            RequestStatus,
            execute_control_request,
            submit_control_request,
        )

        action_enum = LocalControlAction(action_value)
        req = submit_control_request(action_enum, payload, local_available=True)

        if req.status == RequestStatus.BLOCKED:
            step.status = StepStatus.WAITING_ON_OPERATOR
            step.requires_input_prompt = f"local_control blocked: {action_value} — {req.error or 'mode restriction'}"
            step.execution_finished_at = _utcnow()
            step.updated_at = _utcnow()
            _log(f"local control blocked for step {step.step_id}: {action_value}")
            return step

        result_req = execute_control_request(req.request_id)

        if result_req.status == RequestStatus.COMPLETED:
            step.status = StepStatus.COMPLETED
            step.execution_result = (
                f"local_control: {action_value} — {result_req.result or 'ok'}"
            )
        else:
            step.status = StepStatus.FAILED
            step.execution_error = (
                f"local_control {action_value} failed: {result_req.error or 'unknown'}"
            )
            _log(f"local control failed for step {step.step_id}: {result_req.error}")

    except Exception as exc:  # noqa: BLE001
        step.status = StepStatus.FAILED
        step.execution_error = f"local_control dispatch error: {exc}"
        _log(f"local control exception for step {step.step_id}: {exc}")

    step.execution_finished_at = _utcnow()
    step.updated_at = _utcnow()
    return step


# ─── Step Execution ───────────────────────────────────────────────────────────


def _execute_step(
    step: PipelineStep,
    pipeline: TaskPipeline,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
) -> PipelineStep:
    """Execute a single pipeline step.

    Uses capability routing to select the target, then dispatches through
    the tmux-backed session bridge. Detects human-block signals in output.

    State transitions:
      READY → IN_PROGRESS → COMPLETED (success)
      READY → IN_PROGRESS → WAITING_ON_OPERATOR (human block)
      READY → IN_PROGRESS → FAILED (execution error)
    """
    # ── Transition to IN_PROGRESS ───────────────────────────────────────────
    step.status = StepStatus.IN_PROGRESS
    step.execution_started_at = _utcnow()
    step.updated_at = _utcnow()

    # ── Route the step ──────────────────────────────────────────────────────
    try:
        from eos_ai.transport.capability_routing import choose_execution_target
        from eos_ai.transport.task_system import Task, TaskExecutionPolicy, TaskStatus

        # Build a lightweight proxy Task for routing — reuses existing
        # capability_routing infrastructure without modification
        proxy = Task(
            task_id=pipeline.task_id,
            title=f"{pipeline.title} — {step.title}",
            description=step.description,
            execution_policy=TaskExecutionPolicy.AUTONOMOUS,
            status=TaskStatus.IN_PROGRESS,
            created_at=pipeline.created_at,
            updated_at=step.updated_at,
        )
        target = choose_execution_target(proxy, session, local_available)
        step.chosen_target = target.value
        step.routing_reason = f"step routed → {target.value}"
    except Exception as exc:  # noqa: BLE001
        _log(f"routing failed for step {step.step_id}: {exc}")
        step.chosen_target = "vps_builder"
        step.routing_reason = f"routing fallback: {exc}"

    # Check for local control action
    local_action = _detect_local_control_action(step)
    if local_action is not None:
        action_value, payload = local_action
        return _execute_local_control_step(step, action_value, payload, dry_run=dry_run)

    if dry_run:
        step.status = StepStatus.COMPLETED
        step.execution_result = "dry_run — no dispatch"
        step.execution_finished_at = _utcnow()
        step.updated_at = _utcnow()
        return step

    # ── Dispatch to tmux ────────────────────────────────────────────────────
    dispatch_text = f"[Pipeline: {pipeline.title}] Step {step.step_index}: {step.title}"
    if step.description:
        dispatch_text += f"\n{step.description}"

    try:
        from runtime.transport.task_execution import _resolve_tmux_target

        tmux_target, session_name = _resolve_tmux_target(step.chosen_target)

        from eos_ai.transport.claude_session_bridge import ask_session

        result = ask_session(
            tmux_target,
            session_name,
            dispatch_text,
            ensure=True,
            poll_interval_s=2.0,
            max_polls=60,
        )
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "reason": f"dispatch_exception: {exc}"}
        _log(f"dispatch exception for step {step.step_id}: {exc}")

    # ── Process result ──────────────────────────────────────────────────────
    if result.get("ok"):
        reply_text = result.get("reply_text", "")
        step.execution_result = reply_text or "completed (no output)"

        # Check for human-block signals
        from eos_ai.transport.task_execution import detect_human_block

        block_signal = detect_human_block(reply_text)
        if block_signal:
            step.status = StepStatus.WAITING_ON_OPERATOR
            step.requires_input_prompt = f"Step paused: {block_signal}"
            _log(f"human block at step {step.step_id}: {block_signal}")
        else:
            step.status = StepStatus.COMPLETED
    else:
        reason = result.get("reason", "unknown")
        step.execution_error = reason
        step.status = StepStatus.FAILED
        _log(f"step {step.step_id} failed: {reason}")

    step.execution_finished_at = _utcnow()
    step.updated_at = _utcnow()
    return step


# ─── Pipeline Execution ──────────────────────────────────────────────────────


def execute_pipeline(
    pipeline: TaskPipeline,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
    advance_all: bool = False,
) -> TaskPipeline:
    """Execute the current READY step of a pipeline.

    If advance_all=True, continues executing steps until blocked, failed,
    or completed. This is the mode used by overnight execution.

    State transitions on the pipeline:
      READY → IN_PROGRESS (step executing)
      IN_PROGRESS → COMPLETED (all steps done)
      IN_PROGRESS → WAITING_ON_OPERATOR (step blocked)
      IN_PROGRESS → PAUSED (step failed, retryable)
      IN_PROGRESS → FAILED (step failed, retries exhausted)

    Args:
        pipeline: The pipeline to execute.
        session: Current operator session for routing context.
        local_available: Whether a local node is reachable.
        dry_run: If True, route steps but skip actual dispatch.
        advance_all: If True, keep advancing until blocked or done.

    Returns:
        The updated pipeline (also persisted in PipelineStore).
    """
    store = PipelineStore.default()

    # Guard: skip terminal pipelines
    if pipeline.is_terminal():
        _log(f"skip {pipeline.pipeline_id}: terminal ({pipeline.status.value})")
        return pipeline

    pipeline.status = PipelineStatus.IN_PROGRESS
    store.put(pipeline)

    while True:
        step = pipeline.current_step()
        if step is None:
            # All steps processed
            pipeline.status = PipelineStatus.COMPLETED
            pipeline.summary = f"All {len(pipeline.steps)} steps completed"
            store.put(pipeline)
            _log(f"pipeline {pipeline.pipeline_id} completed")
            return pipeline

        # Only execute READY steps
        if step.status != StepStatus.READY:
            # If step already completed, advance
            if step.status == StepStatus.COMPLETED:
                pipeline.current_step_index += 1
                store.put(pipeline)
                if advance_all:
                    continue
                return pipeline
            # If step is in a blocked/failed state, propagate to pipeline
            if step.status == StepStatus.WAITING_ON_OPERATOR:
                pipeline.status = PipelineStatus.WAITING_ON_OPERATOR
                store.put(pipeline)
                return pipeline
            if step.status == StepStatus.FAILED:
                if step.retry_count >= _MAX_STEP_RETRIES:
                    pipeline.status = PipelineStatus.FAILED
                else:
                    pipeline.status = PipelineStatus.PAUSED
                store.put(pipeline)
                return pipeline
            # Any other status (PENDING, IN_PROGRESS, SKIPPED) — skip
            _log(
                f"step {step.step_id} in unexpected status {step.status.value}, "
                f"skipping"
            )
            pipeline.current_step_index += 1
            store.put(pipeline)
            if advance_all:
                continue
            return pipeline

        # ── Execute the step ────────────────────────────────────────────────
        _stream_step_event(
            "step_started",
            f"Starting step {step.step_index}: {step.title}",
            pipeline=pipeline,
            step=step,
        )
        _execute_step(
            step,
            pipeline,
            session,
            local_available=local_available,
            dry_run=dry_run,
        )
        _stream_step_event(
            "step_completed" if step.status == StepStatus.COMPLETED else "error",
            f"Step {step.step_index} {step.status.value}: {step.title}",
            pipeline=pipeline,
            step=step,
        )

        # ── Handle step outcome ─────────────────────────────────────────────
        if step.status == StepStatus.COMPLETED:
            # Advance to next step
            pipeline.current_step_index += 1
            # Mark next step as READY if it exists
            if pipeline.current_step_index < len(pipeline.steps):
                next_step = pipeline.steps[pipeline.current_step_index]
                if next_step.status == StepStatus.PENDING:
                    next_step.status = StepStatus.READY
                    next_step.updated_at = _utcnow()
            store.put(pipeline)

            if advance_all:
                continue

            # Check if we just completed the last step
            if pipeline.current_step_index >= len(pipeline.steps):
                pipeline.status = PipelineStatus.COMPLETED
                pipeline.summary = f"All {len(pipeline.steps)} steps completed"
                store.put(pipeline)
                _log(f"pipeline {pipeline.pipeline_id} completed")
            return pipeline

        elif step.status == StepStatus.WAITING_ON_OPERATOR:
            pipeline.status = PipelineStatus.WAITING_ON_OPERATOR
            store.put(pipeline)
            _log(
                f"pipeline {pipeline.pipeline_id} blocked at step "
                f"{step.step_index}: {step.requires_input_prompt}"
            )
            return pipeline

        elif step.status == StepStatus.FAILED:
            step.retry_count += 1
            if step.retry_count > _MAX_STEP_RETRIES:
                pipeline.status = PipelineStatus.FAILED
                pipeline.summary = (
                    f"Failed at step {step.step_index} ({step.title}) "
                    f"after {step.retry_count} attempts: {step.execution_error}"
                )
                _log(
                    f"pipeline {pipeline.pipeline_id} failed at step {step.step_index}"
                )
            else:
                pipeline.status = PipelineStatus.PAUSED
                _log(
                    f"pipeline {pipeline.pipeline_id} paused: step {step.step_index} "
                    f"failed (retry {step.retry_count}/{_MAX_STEP_RETRIES})"
                )
            store.put(pipeline)
            return pipeline

        else:
            # Unexpected — log and stop
            _log(
                f"unexpected step status {step.status.value} after execution, "
                f"pausing pipeline {pipeline.pipeline_id}"
            )
            pipeline.status = PipelineStatus.PAUSED
            store.put(pipeline)
            return pipeline


# ─── Step-Level Retry ─────────────────────────────────────────────────────────


def retry_step(
    pipeline_id: str,
    step_id: str,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
) -> TaskPipeline:
    """Retry a failed step without restarting the whole pipeline.

    Resets the step to READY, increments its retry_count, and re-executes.
    Pipeline transitions back to IN_PROGRESS if currently PAUSED/FAILED.

    Args:
        pipeline_id: The pipeline containing the step.
        step_id: The step to retry.
        session: Operator session for routing.
        local_available: Whether local node is reachable.
        dry_run: If True, skip actual dispatch.

    Returns:
        The updated pipeline.

    Raises:
        ValueError: If pipeline or step not found.
    """
    store = PipelineStore.default()
    pipeline = store.get(pipeline_id)
    if pipeline is None:
        raise ValueError(f"pipeline not found: {pipeline_id}")

    # Find the step
    target_step: Optional[PipelineStep] = None
    for step in pipeline.steps:
        if step.step_id == step_id:
            target_step = step
            break
    if target_step is None:
        raise ValueError(f"step not found: {step_id} in pipeline {pipeline_id}")

    # Guard: only retry FAILED steps
    if target_step.status != StepStatus.FAILED:
        _log(
            f"cannot retry step {step_id}: status is {target_step.status.value}, "
            f"not FAILED"
        )
        return pipeline

    # Reset step for retry
    target_step.status = StepStatus.READY
    target_step.execution_error = None
    target_step.execution_result = None
    target_step.execution_started_at = None
    target_step.execution_finished_at = None
    target_step.updated_at = _utcnow()

    # Set pipeline index to this step and resume
    pipeline.current_step_index = target_step.step_index
    pipeline.status = PipelineStatus.IN_PROGRESS
    store.put(pipeline)

    _log(f"retrying step {step_id} (attempt {target_step.retry_count + 1})")

    return execute_pipeline(
        pipeline,
        session,
        local_available=local_available,
        dry_run=dry_run,
    )


# ─── Pipeline Resume ─────────────────────────────────────────────────────────


def resume_pipeline(
    pipeline_id: str,
    session: Optional["OperatorSession"] = None,
    *,
    local_available: bool = False,
    dry_run: bool = False,
    advance_all: bool = False,
) -> TaskPipeline:
    """Resume a pipeline from its current step.

    Does not restart completed steps. Handles PAUSED, WAITING_ON_OPERATOR,
    and IN_PROGRESS pipelines.

    For PAUSED pipelines with a FAILED step: resets the failed step to READY.
    For WAITING_ON_OPERATOR pipelines: resets the waiting step to READY.

    Args:
        pipeline_id: The pipeline to resume.
        session: Operator session for routing.
        local_available: Whether local node is reachable.
        dry_run: If True, skip actual dispatch.
        advance_all: If True, keep advancing until blocked or done.

    Returns:
        The updated pipeline.

    Raises:
        ValueError: If pipeline not found.
    """
    store = PipelineStore.default()
    pipeline = store.get(pipeline_id)
    if pipeline is None:
        raise ValueError(f"pipeline not found: {pipeline_id}")

    if pipeline.is_terminal():
        _log(f"cannot resume {pipeline_id}: terminal ({pipeline.status.value})")
        return pipeline

    # If paused with a failed step, reset it to READY
    current = pipeline.current_step()
    if current is not None:
        if current.status == StepStatus.FAILED:
            current.status = StepStatus.READY
            current.execution_error = None
            current.execution_result = None
            current.execution_started_at = None
            current.execution_finished_at = None
            current.updated_at = _utcnow()
        elif current.status == StepStatus.WAITING_ON_OPERATOR:
            current.status = StepStatus.READY
            current.requires_input_prompt = None
            current.updated_at = _utcnow()

    pipeline.status = PipelineStatus.IN_PROGRESS
    store.put(pipeline)

    return execute_pipeline(
        pipeline,
        session,
        local_available=local_available,
        dry_run=dry_run,
        advance_all=advance_all,
    )


# ─── Pipeline Summary Helpers ─────────────────────────────────────────────────


def get_pipeline_summary() -> dict:
    """Build a summary dict for briefings.

    Returns:
        {
            "active_pipelines": int,
            "completed_pipelines": int,
            "failed_pipelines": int,
            "waiting_on_operator": int,
            "top_blocked_prompt": str | None,
            "top_priority_task_title": str | None,
        }
    """
    store = PipelineStore.default()
    all_pipelines = store.all()

    active = [p for p in all_pipelines if not p.is_terminal()]
    completed = store.by_status(PipelineStatus.COMPLETED)
    failed = store.by_status(PipelineStatus.FAILED)
    waiting = store.by_status(PipelineStatus.WAITING_ON_OPERATOR)

    # Find top blocked prompt
    top_blocked_prompt: Optional[str] = None
    top_priority_title: Optional[str] = None
    if waiting:
        # Sort by priority descending
        waiting_sorted = sorted(waiting, key=lambda p: p.priority, reverse=True)
        top = waiting_sorted[0]
        top_priority_title = top.title
        current = top.current_step()
        if current and current.requires_input_prompt:
            top_blocked_prompt = current.requires_input_prompt

    return {
        "active_pipelines": len(active),
        "completed_pipelines": len(completed),
        "failed_pipelines": len(failed),
        "waiting_on_operator": len(waiting),
        "top_blocked_prompt": top_blocked_prompt,
        "top_priority_task_title": top_priority_title,
    }


# ─── Discord Formatter Helpers ────────────────────────────────────────────────


def format_blocked_summary(pipeline: TaskPipeline) -> str:
    """Format a single pipeline's blocked status for Discord output."""
    current = pipeline.current_step()
    lines = [f"**{pipeline.title}**"]
    if current:
        lines.append(f"  Blocked at: {current.title}")
        if current.requires_input_prompt:
            lines.append(f"  Needs: {current.requires_input_prompt}")
    lines.append(f"  Priority: {pipeline.priority}")
    return "\n".join(lines)


def format_pipeline_summary(pipeline: TaskPipeline) -> str:
    """Format a single pipeline's status for Discord output."""
    completed = len(pipeline.completed_steps())
    total = len(pipeline.steps)
    progress = f"{completed}/{total}"

    current = pipeline.current_step()
    current_info = f" → {current.title}" if current else ""

    return (
        f"**{pipeline.title}** [{pipeline.status.value}] "
        f"({progress} steps){current_info}"
    )


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "execute_pipeline",
    "retry_step",
    "resume_pipeline",
    "get_pipeline_summary",
    "format_blocked_summary",
    "format_pipeline_summary",
]
