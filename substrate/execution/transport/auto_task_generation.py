"""
Auto-task generation — bridges the perception layer to the task system.

Consumes PerceptionRecords produced by the ambient collectors and generates
tasks for WARNING and CRITICAL observations.  Also provides a full
perception-to-task cycle runner and a summary endpoint for open_day briefings.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort — all public functions catch and log; never raise into callers.
- Deduplication — stable title format prevents duplicate tasks.
- Lazy imports for task_system and operator_session to avoid circular deps.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Optional

from substrate.execution.transport.perception import (
    PerceptionRecord,
    PerceptionSeverity,
    PerceptionStore,
    collect_all_perceptions,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.auto_task_generation] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


_ACTIONABLE_SEVERITIES = frozenset(
    {PerceptionSeverity.WARNING, PerceptionSeverity.CRITICAL}
)

_AUTO_PREFIX = "[auto] "


def _candidate_title(p: PerceptionRecord) -> str:
    """Compute the stable dedup title for a perception-generated task."""
    return f"{_AUTO_PREFIX}{p.suggested_action or p.summary}"


# ─── generate_tasks_from_perceptions ─────────────────────────────────────────


def generate_tasks_from_perceptions(
    perceptions: list[PerceptionRecord],
    *,
    session: Optional[object] = None,
) -> list[object]:
    """Generate tasks from actionable perception records.

    Rules:
    - Only generate tasks from WARNING and CRITICAL perceptions.
    - INFO perceptions are logged but not actionable.
    - Deduplication: skip if a non-COMPLETED task with the same title exists.
    - Uses create_task() from task_system for actual task creation.
    - Attaches session_id from session if available.

    Args:
        perceptions: List of PerceptionRecords to evaluate.
        session: Optional OperatorSession — day_session_id is attached when present.

    Returns:
        List of newly created Task objects.
    """
    try:
        from substrate.execution.transport.task_system import (
            Task,
            TaskStore,
            TaskStatus,
            create_task,
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"cannot import task_system: {exc}")
        return []

    created: list[Task] = []

    try:
        store = TaskStore.default()
        existing_tasks = store.all()

        # Build a set of non-completed task titles for fast dedup lookup
        active_titles: set[str] = {
            t.title for t in existing_tasks if t.status != TaskStatus.COMPLETED
        }

        # Resolve session_id
        session_id: Optional[str] = None
        if session is not None:
            session_id = getattr(session, "day_session_id", None)

        for p in perceptions:
            if p.severity not in _ACTIONABLE_SEVERITIES:
                continue

            title = _candidate_title(p)

            if title in active_titles:
                _log(f"skip duplicate: {title}")
                continue

            try:
                description = (
                    f"Auto-generated from {p.source.value} perception: {p.summary}"
                )
                task = create_task(
                    title,
                    session_id=session_id,
                    description=description,
                )
                created.append(task)
                # Add to active set so subsequent perceptions in the same batch dedup
                active_titles.add(title)
                _log(f"created task {task.task_id}: {title}")
            except Exception as exc:  # noqa: BLE001
                _log(f"create_task failed for '{title}': {exc}")
    except Exception as exc:  # noqa: BLE001
        _log(f"generate_tasks_from_perceptions error: {exc}")

    return created


# ─── run_perception_cycle ────────────────────────────────────────────────────


def run_perception_cycle(
    *,
    session: Optional[object] = None,
) -> dict:
    """Run a full perception-to-task cycle.

    Steps:
    1. Collect all perceptions via collect_all_perceptions().
    2. Persist each to PerceptionStore (dedup by fingerprint).
    3. Generate tasks from perceptions.
    4. Return summary dict.

    Args:
        session: Optional OperatorSession for task linkage.

    Returns:
        Dict with counts and the top-issue summary.
    """
    result: dict = {
        "perceptions_collected": 0,
        "perceptions_new": 0,
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "tasks_generated": 0,
        "generated_task_ids": [],
        "top_issue_summary": None,
    }

    try:
        # 1. Collect
        perceptions = collect_all_perceptions()
        result["perceptions_collected"] = len(perceptions)

        # 2. Persist with fingerprint dedup
        pstore = PerceptionStore.default()
        new_count = 0
        for p in perceptions:
            if not pstore.has_fingerprint(p.fingerprint):
                pstore.put(p)
                new_count += 1
        result["perceptions_new"] = new_count

        # 3. Severity counts (over all collected, not just new)
        critical_count = 0
        warning_count = 0
        info_count = 0
        first_critical: Optional[PerceptionRecord] = None
        first_warning: Optional[PerceptionRecord] = None

        for p in perceptions:
            if p.severity == PerceptionSeverity.CRITICAL:
                critical_count += 1
                if first_critical is None:
                    first_critical = p
            elif p.severity == PerceptionSeverity.WARNING:
                warning_count += 1
                if first_warning is None:
                    first_warning = p
            else:
                info_count += 1

        result["critical_count"] = critical_count
        result["warning_count"] = warning_count
        result["info_count"] = info_count

        # 4. Generate tasks (pass all perceptions — existing WARNING/CRITICAL
        #    that haven't been tasked yet should also be considered)
        tasks = generate_tasks_from_perceptions(perceptions, session=session)
        result["tasks_generated"] = len(tasks)
        result["generated_task_ids"] = [getattr(t, "task_id", "") for t in tasks]

        # 5. Top issue summary
        if first_critical is not None:
            result["top_issue_summary"] = first_critical.summary
        elif first_warning is not None:
            result["top_issue_summary"] = first_warning.summary

    except Exception as exc:  # noqa: BLE001
        _log(f"run_perception_cycle error: {exc}")

    return result


# ─── get_perception_summary ──────────────────────────────────────────────────


def get_perception_summary() -> dict:
    """Get a summary suitable for open_day briefing.

    Reads recent perceptions and counts auto-generated tasks.

    Returns:
        Dict with severity counts, auto-task count, and top issue summary.
    """
    result: dict = {
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "generated_task_count": 0,
        "top_issue_summary": None,
    }

    try:
        # Recent perceptions
        pstore = PerceptionStore.default()
        recent = pstore.recent(50)

        first_critical: Optional[PerceptionRecord] = None
        first_warning: Optional[PerceptionRecord] = None

        for p in recent:
            if p.severity == PerceptionSeverity.CRITICAL:
                result["critical_count"] += 1
                if first_critical is None:
                    first_critical = p
            elif p.severity == PerceptionSeverity.WARNING:
                result["warning_count"] += 1
                if first_warning is None:
                    first_warning = p
            else:
                result["info_count"] += 1

        # Auto-generated task count
        try:
            from substrate.execution.transport.task_system import TaskStore

            tstore = TaskStore.default()
            all_tasks = tstore.all()
            result["generated_task_count"] = sum(
                1 for t in all_tasks if t.title.startswith(_AUTO_PREFIX)
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"task count lookup failed: {exc}")

        # Top issue
        if first_critical is not None:
            result["top_issue_summary"] = first_critical.summary
        elif first_warning is not None:
            result["top_issue_summary"] = first_warning.summary

    except Exception as exc:  # noqa: BLE001
        _log(f"get_perception_summary error: {exc}")

    return result


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "generate_tasks_from_perceptions",
    "run_perception_cycle",
    "get_perception_summary",
]
