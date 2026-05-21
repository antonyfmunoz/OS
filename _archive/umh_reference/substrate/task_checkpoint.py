"""
Task checkpoint — automatic task-boundary context hygiene.

After a completed work unit, the system:
1. Archives the task completion with a final report
2. Emits a TASK_COMPLETED event to the event spine
3. Creates a clear checkpoint preserving continuity
4. Optionally triggers a context clear via session_control
5. Leaves the system ready for the next work unit

Design rules (mirror substrate conventions):
- Additive only. No hot-path imports.
- Best-effort. Every step degrades gracefully.
- Deterministic. No LLM calls.
- Composes on top of: interaction_archive, event_spine, event_store,
  context_lifecycle, session_control.
- Never destroys history.

Trigger definition:
  A "task-complete" boundary is when:
  - A task_system.Task reaches TaskStatus.COMPLETED
  - A pipeline_execution pipeline finishes (all steps done)
  - An explicit checkpoint_task_boundary() call from any interface
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


_LOG_PREFIX = "[substrate.task_checkpoint]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_id() -> str:
    return f"tcp_{uuid.uuid4().hex[:12]}"


# ─── Auto-clear policy ────────────────────────────────────────────────────────


class AutoClearPolicy:
    """Policy controlling whether task-boundary auto-clear is enabled.

    Reads from environment: EOS_TASK_AUTOCLEAR_ENABLED (default "1").
    """

    _ENV_KEY = "EOS_TASK_AUTOCLEAR_ENABLED"

    @staticmethod
    def enabled() -> bool:
        import os

        raw = (os.getenv(AutoClearPolicy._ENV_KEY, "1") or "1").strip().lower()
        return raw in ("1", "true", "yes", "on")


# ─── Result ───────────────────────────────────────────────────────────────────


@dataclass
class TaskCheckpointResult:
    """Outcome of a task-boundary checkpoint operation."""

    checkpoint_id: str = field(default_factory=_checkpoint_id)
    task_id: str = ""
    task_title: str = ""
    final_report: str = ""
    archive_id: str = ""
    spine_event_id: str = ""
    clear_checkpoint_id: str = ""
    auto_cleared: bool = False
    clear_result: Optional[dict[str, Any]] = None
    carry_forward: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "final_report": self.final_report,
            "archive_id": self.archive_id,
            "spine_event_id": self.spine_event_id,
            "clear_checkpoint_id": self.clear_checkpoint_id,
            "auto_cleared": self.auto_cleared,
            "clear_result": self.clear_result,
            "carry_forward": list(self.carry_forward),
            "created_at": self.created_at,
            "errors": list(self.errors),
            "success": self.success,
        }


# ─── Core checkpoint function ─────────────────────────────────────────────────


def checkpoint_task_boundary(
    *,
    task_id: str = "",
    task_title: str = "",
    final_report: str = "",
    carry_forward: Optional[list[str]] = None,
    interface: str = "internal",
    source_session: str = "",
    role: str = "",
    node_id: str = "",
    correlation_id: str = "",
    auto_clear: Optional[bool] = None,
    clear_target: str = "vps",
) -> TaskCheckpointResult:
    """Execute a full task-boundary checkpoint.

    Steps:
    1. Archive the task completion as a verbatim interaction record.
    2. Emit a task_completed event to the event spine.
    3. Create a clear checkpoint preserving continuity references.
    4. If auto_clear is enabled, trigger context clear via session_control.

    Args:
        task_id: Identifier of the completed task (if any).
        task_title: Human-readable task title for the report.
        final_report: Summary or final output of the completed task.
        carry_forward: Unresolved items that should survive the clear.
        interface: Source interface (discord, webhook, etc).
        source_session: Session name (dex_builder_main, etc).
        role: Operating context (ea_product, builder, etc).
        node_id: Node that handled this task.
        correlation_id: Workflow-level correlation.
        auto_clear: Override auto-clear policy. None = use policy.
        clear_target: Target for session_control.clear_session ("vps" | "local").

    Returns:
        TaskCheckpointResult with full outcome details.
    """
    result = TaskCheckpointResult(
        task_id=task_id,
        task_title=task_title,
        final_report=final_report,
        carry_forward=list(carry_forward or []),
    )

    # 1. Archive the task completion as an outbound interaction
    try:
        from umh.substrate.interaction_archive import (
            Interface,
            archive_outbound,
        )

        archive_text = f"[Task Completed: {task_title or task_id}]\n{final_report}"
        if carry_forward:
            archive_text += f"\n\n[Carry forward: {', '.join(carry_forward)}]"

        result.archive_id = archive_outbound(
            archive_text,
            interface=interface,
            source_session=source_session,
            role=role,
            node_id=node_id,
            correlation_id=correlation_id,
            metadata={
                "is_task_checkpoint": True,
                "task_id": task_id,
                "carry_forward": list(carry_forward or []),
            },
        )
    except Exception as exc:
        msg = f"archive failed: {exc}"
        _log(msg)
        result.errors.append(msg)

    # 2. Emit task_completed event to the event spine
    try:
        from umh.substrate.event_spine import EventType, create_event
        from umh.substrate.event_store import get_event_store

        event = create_event(
            EventType.STEP_COMPLETED,
            source=interface,
            source_session=source_session,
            target="task_checkpoint",
            role=role,
            payload={
                "type": "task_completed",
                "task_id": task_id,
                "task_title": task_title,
                "checkpoint_id": result.checkpoint_id,
                "carry_forward": list(carry_forward or []),
                "has_final_report": bool(final_report),
            },
            correlation_id=correlation_id or None,
        )
        get_event_store().append(event)
        result.spine_event_id = event.event_id
    except Exception as exc:
        msg = f"spine event failed: {exc}"
        _log(msg)
        result.errors.append(msg)

    # 3. Create a clear checkpoint
    try:
        from umh.substrate.interaction_archive import create_clear_checkpoint

        cp = create_clear_checkpoint(
            session_name=source_session,
            role=role,
            node_id=node_id,
            interface=interface,
            correlation_id=correlation_id,
            reason=f"task_complete:{task_id or 'unnamed'}",
            context_summary=f"Completed: {task_title or task_id}. "
            + (
                f"Carry forward: {', '.join(carry_forward)}"
                if carry_forward
                else "No carry-forward items."
            ),
        )
        result.clear_checkpoint_id = cp.get("archive_id", "")
    except Exception as exc:
        msg = f"clear checkpoint failed: {exc}"
        _log(msg)
        result.errors.append(msg)

    # 4. Auto-clear if policy allows
    # Guard: reject if run is terminally finalized — clear is owned by
    # task_finalization, not by checkpoint.
    should_clear = auto_clear if auto_clear is not None else AutoClearPolicy.enabled()
    if should_clear and source_session:
        _clear_blocked_terminal = False
        try:
            from umh.substrate.run_lifecycle import is_run_terminally_finalized

            if is_run_terminally_finalized(source_session):
                _clear_blocked_terminal = True
                _log(
                    f"checkpoint auto-clear BLOCKED: session={source_session} "
                    f"— run terminally finalized"
                )
        except Exception:
            pass

        if not _clear_blocked_terminal:
            try:
                from umh.substrate.session_control import clear_session

                clear_result = clear_session(clear_target, source_session)
                result.auto_cleared = bool(clear_result.get("ok"))
                result.clear_result = clear_result
                if result.auto_cleared:
                    _log(
                        f"auto-clear after task {task_id or 'unnamed'} "
                        f"in session {source_session}"
                    )
            except Exception as exc:
                msg = f"auto-clear failed: {exc}"
                _log(msg)
                result.errors.append(msg)

    # 5. Record task completion in the task record store (best-effort)
    try:
        from umh.substrate.task_record import get_task_record_store

        store = get_task_record_store()
        record = store.by_correlation_id(correlation_id) if correlation_id else None
        if record is not None:
            store.complete_task(
                record.task_id,
                final_report=final_report,
                interaction_ids=[result.archive_id] if result.archive_id else None,
            )
    except Exception as exc:
        _log(f"task record completion failed: {exc}")

    _log(
        f"checkpoint complete: task={task_id or 'unnamed'} "
        f"archive={result.archive_id[:8] if result.archive_id else 'none'} "
        f"cleared={result.auto_cleared}"
    )

    return result


# ─── Convenience wrappers ──────────────────────────────────────────────────────


def checkpoint_from_task(
    task_id: str,
    *,
    source_session: str = "",
    auto_clear: Optional[bool] = None,
) -> TaskCheckpointResult:
    """Checkpoint from a task_system.Task by ID. Best-effort."""
    title = ""
    report = ""
    carry: list[str] = []
    correlation = ""

    try:
        from umh.substrate.task_system import TaskStore

        store = TaskStore.default()
        task = store.get(task_id)
        if task is not None:
            title = task.title
            report = getattr(task, "execution_result", "") or ""
            correlation = getattr(task, "pipeline_id", "") or ""
    except Exception as exc:
        _log(f"task lookup failed: {exc}")

    return checkpoint_task_boundary(
        task_id=task_id,
        task_title=title,
        final_report=report,
        carry_forward=carry,
        source_session=source_session,
        correlation_id=correlation,
        auto_clear=auto_clear,
    )


def checkpoint_from_pipeline(
    pipeline_id: str,
    *,
    source_session: str = "",
    auto_clear: Optional[bool] = None,
) -> TaskCheckpointResult:
    """Checkpoint from a pipeline completion. Best-effort."""
    title = ""
    report = ""
    carry: list[str] = []

    try:
        from umh.substrate.task_pipeline import PipelineStore

        store = PipelineStore.default()
        pipeline = store.get(pipeline_id)
        if pipeline is not None:
            title = f"Pipeline: {pipeline.name}"
            report = (
                f"Pipeline {pipeline_id} completed with {len(pipeline.steps)} steps."
            )
    except Exception as exc:
        _log(f"pipeline lookup failed: {exc}")

    return checkpoint_task_boundary(
        task_id=pipeline_id,
        task_title=title,
        final_report=report,
        carry_forward=carry,
        source_session=source_session,
        correlation_id=pipeline_id,
        auto_clear=auto_clear,
    )


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "AutoClearPolicy",
    "TaskCheckpointResult",
    "checkpoint_task_boundary",
    "checkpoint_from_task",
    "checkpoint_from_pipeline",
]
