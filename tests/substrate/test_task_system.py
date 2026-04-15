"""Smoke tests for eos_ai.substrate.task_system.

Validates:
  1. test_classify_autonomous       — default classification is autonomous
  2. test_classify_needs_operator   — operator keywords trigger needs_operator
  3. test_classify_needs_approval   — approval keywords trigger needs_approval
  4. test_create_autonomous_task    — autonomous task starts as READY
  5. test_create_operator_task      — operator task starts as WAITING_ON_OPERATOR
  6. test_process_autonomous_day_open   — autonomous + day open → COMPLETED
  7. test_process_autonomous_day_closed — autonomous + day closed → OVERNIGHT_QUEUED
  8. test_process_operator_task     — operator task stays WAITING_ON_OPERATOR
  9. test_overnight_execution       — run_overnight_tasks completes queued tasks
 10. test_task_summary              — get_task_summary returns correct counts
 11. test_restart_safe              — tasks persist across singleton reset
 12. test_open_day_includes_task_summary — open_day briefing contains task_summary
 13. test_close_day_triggers_overnight  — close_day with overnight mode runs queued tasks

Run directly:
    python3 tests/substrate/test_task_system.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.day_workflows import close_day, open_day  # noqa: E402
from eos_ai.substrate.operator_session import OperatorSessionStore  # noqa: E402
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402
from eos_ai.substrate.task_system import (  # noqa: E402
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    classify_task,
    create_task,
    get_task_summary,
    process_task,
    run_overnight_tasks,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset_all() -> None:
    """Reset all singletons and clear storage keys between tests."""
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("operator_session", None)
        get_storage().put("rituals", {})
        get_storage().put("task_system", None)
    except Exception:  # noqa: BLE001
        pass
    OperatorSessionStore.reset_default_for_tests()
    RitualRegistry.reset_default_for_tests()
    TaskStore.reset_default_for_tests()


# ─── Test 1: classify autonomous ────────────────────────────────────────────


def test_classify_autonomous() -> None:
    print("\n── Test 1: classify_task — autonomous (default) ──")

    result = classify_task("rebuild the graph index")
    _report(
        "default text → AUTONOMOUS",
        result == TaskExecutionPolicy.AUTONOMOUS,
        f"got {result.value}",
    )

    result2 = classify_task("send the daily report")
    _report(
        "normal task → AUTONOMOUS",
        result2 == TaskExecutionPolicy.AUTONOMOUS,
        f"got {result2.value}",
    )


# ─── Test 2: classify needs_operator ────────────────────────────────────────


def test_classify_needs_operator() -> None:
    print("\n── Test 2: classify_task — needs_operator keywords ──")

    cases = [
        ("should I use React or Vue?", "should I"),
        ("decide between Neon and Supabase", "decide"),
        ("which pricing model to choose", "which + choose"),
        ("approve the new homepage design", "approve"),
        ("pick the right framework", "pick"),
    ]
    for text, reason in cases:
        result = classify_task(text)
        _report(
            f"'{text}' → NEEDS_OPERATOR ({reason})",
            result == TaskExecutionPolicy.NEEDS_OPERATOR,
            f"got {result.value}",
        )


# ─── Test 3: classify needs_approval ────────────────────────────────────────


def test_classify_needs_approval() -> None:
    print("\n── Test 3: classify_task — needs_approval keywords ──")

    cases = [
        ("review the PR before merging", "review"),
        ("confirm the deployment is stable", "confirm"),
        ("sign off on the invoice", "sign off"),
    ]
    for text, reason in cases:
        result = classify_task(text)
        _report(
            f"'{text}' → NEEDS_APPROVAL ({reason})",
            result == TaskExecutionPolicy.NEEDS_APPROVAL,
            f"got {result.value}",
        )


# ─── Test 4: create autonomous task ─────────────────────────────────────────


def test_create_autonomous_task() -> None:
    print("\n── Test 4: create_task — autonomous → READY ──")

    _reset_all()

    task = create_task("rebuild the graph index", session_id="ds_test123")

    _report(
        "policy is AUTONOMOUS",
        task.execution_policy == TaskExecutionPolicy.AUTONOMOUS,
        f"got {task.execution_policy.value}",
    )
    _report(
        "status is READY",
        task.status == TaskStatus.READY,
        f"got {task.status.value}",
    )
    _report(
        "task_id starts with task_",
        task.task_id.startswith("task_"),
        f"got {task.task_id!r}",
    )
    _report(
        "day_session_id linked",
        task.day_session_id == "ds_test123",
        f"got {task.day_session_id!r}",
    )
    _report(
        "persisted in store",
        TaskStore.default().get(task.task_id) is not None,
    )


# ─── Test 5: create operator task ───────────────────────────────────────────


def test_create_operator_task() -> None:
    print("\n── Test 5: create_task — needs_operator → WAITING_ON_OPERATOR ──")

    _reset_all()

    task = create_task("should I deploy to production now?")

    _report(
        "policy is NEEDS_OPERATOR",
        task.execution_policy == TaskExecutionPolicy.NEEDS_OPERATOR,
        f"got {task.execution_policy.value}",
    )
    _report(
        "status is WAITING_ON_OPERATOR",
        task.status == TaskStatus.WAITING_ON_OPERATOR,
        f"got {task.status.value}",
    )
    _report(
        "requires_input_prompt set",
        task.requires_input_prompt is not None
        and "Operator input needed" in task.requires_input_prompt,
        f"got {task.requires_input_prompt!r}",
    )


# ─── Test 6: process autonomous (day open) ──────────────────────────────────


def test_process_autonomous_day_open() -> None:
    print("\n── Test 6: process_task — autonomous + day open → COMPLETED ──")

    _reset_all()

    task = create_task("send weekly digest")
    result = process_task(task, is_day_open=True)

    _report(
        "status is COMPLETED",
        result.status == TaskStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "result is set",
        result.result is not None,
        f"got {result.result!r}",
    )


# ─── Test 7: process autonomous (day closed) ────────────────────────────────


def test_process_autonomous_day_closed() -> None:
    print("\n── Test 7: process_task — autonomous + day closed → OVERNIGHT_QUEUED ──")

    _reset_all()

    task = create_task("run nightly backup")
    result = process_task(task, is_day_open=False)

    _report(
        "status is OVERNIGHT_QUEUED",
        result.status == TaskStatus.OVERNIGHT_QUEUED,
        f"got {result.status.value}",
    )


# ─── Test 8: process operator task ──────────────────────────────────────────


def test_process_operator_task() -> None:
    print("\n── Test 8: process_task — operator task stays WAITING_ON_OPERATOR ──")

    _reset_all()

    task = create_task("decide which vendor to use")
    original_status = task.status
    result = process_task(task, is_day_open=True)

    _report(
        "status unchanged (WAITING_ON_OPERATOR)",
        result.status == TaskStatus.WAITING_ON_OPERATOR,
        f"got {result.status.value}",
    )
    _report(
        "was already WAITING_ON_OPERATOR at creation",
        original_status == TaskStatus.WAITING_ON_OPERATOR,
        f"got {original_status.value}",
    )


# ─── Test 9: overnight execution ────────────────────────────────────────────


def test_overnight_execution() -> None:
    print("\n── Test 9: run_overnight_tasks completes queued tasks ──")

    _reset_all()

    # Create and queue tasks
    t1 = create_task("sync CRM data")
    process_task(t1, is_day_open=False)  # → OVERNIGHT_QUEUED

    t2 = create_task("generate report")
    process_task(t2, is_day_open=False)  # → OVERNIGHT_QUEUED

    t3 = create_task("should I change the pricing?")  # → WAITING_ON_OPERATOR

    # Run overnight
    executed = run_overnight_tasks()

    _report(
        "2 tasks executed overnight",
        len(executed) == 2,
        f"got {len(executed)}",
    )
    _report(
        "t1 now COMPLETED",
        TaskStore.default().get(t1.task_id).status == TaskStatus.COMPLETED,
    )
    _report(
        "t2 now COMPLETED",
        TaskStore.default().get(t2.task_id).status == TaskStatus.COMPLETED,
    )
    _report(
        "t3 still WAITING_ON_OPERATOR (untouched)",
        TaskStore.default().get(t3.task_id).status == TaskStatus.WAITING_ON_OPERATOR,
    )


# ─── Test 10: task summary ──────────────────────────────────────────────────


def test_task_summary() -> None:
    print("\n── Test 10: get_task_summary returns correct counts ──")

    _reset_all()

    # Create mixed tasks
    t1 = create_task("rebuild graph")
    process_task(t1, is_day_open=False)  # → OVERNIGHT_QUEUED
    run_overnight_tasks()  # → COMPLETED (overnight)

    t2 = create_task("should I use this tool?")  # → WAITING_ON_OPERATOR

    summary = get_task_summary()

    _report(
        "completed_overnight == 1",
        summary["completed_overnight"] == 1,
        f"got {summary['completed_overnight']}",
    )
    _report(
        "waiting_on_operator == 1",
        summary["waiting_on_operator"] == 1,
        f"got {summary['waiting_on_operator']}",
    )
    _report(
        "total_tasks == 2",
        summary["total_tasks"] == 2,
        f"got {summary['total_tasks']}",
    )
    _report(
        "waiting_tasks has detail",
        len(summary["waiting_tasks"]) == 1
        and summary["waiting_tasks"][0]["task_id"] == t2.task_id,
        f"got {summary['waiting_tasks']}",
    )


# ─── Test 11: restart safe ──────────────────────────────────────────────────


def test_restart_safe() -> None:
    print("\n── Test 11: tasks persist across singleton reset ──")

    _reset_all()

    task = create_task("persist me across restart", session_id="ds_persist")

    # Reset singleton (simulates process restart)
    TaskStore.reset_default_for_tests()

    # Reload from storage
    reloaded = TaskStore.default().get(task.task_id)

    _report(
        "task reloads after singleton reset",
        reloaded is not None,
        "got None" if reloaded is None else "",
    )
    if reloaded is not None:
        _report(
            "task_id survives",
            reloaded.task_id == task.task_id,
            f"expected {task.task_id!r}, got {reloaded.task_id!r}",
        )
        _report(
            "title survives",
            reloaded.title == "persist me across restart",
            f"got {reloaded.title!r}",
        )
        _report(
            "day_session_id survives",
            reloaded.day_session_id == "ds_persist",
            f"got {reloaded.day_session_id!r}",
        )
        _report(
            "status survives",
            reloaded.status == TaskStatus.READY,
            f"got {reloaded.status.value}",
        )


# ─── Test 12: open_day includes task_summary ────────────────────────────────


def test_open_day_includes_task_summary() -> None:
    print("\n── Test 12: open_day briefing contains task_summary ──")

    _reset_all()

    # Create a task that's waiting on operator
    create_task("which deployment strategy?")

    # Open the day
    result = open_day(
        workspace="builder", node_preference="local", discord_channel_id=None
    )

    briefing = result.get("briefing", {})
    task_summary = briefing.get("task_summary", {})

    _report(
        "task_summary in briefing",
        "task_summary" in briefing,
        f"briefing keys: {list(briefing.keys())}",
    )
    _report(
        "waiting_on_operator == 1",
        task_summary.get("waiting_on_operator") == 1,
        f"got {task_summary.get('waiting_on_operator')}",
    )


# ─── Test 13: close_day triggers overnight ──────────────────────────────────


def test_close_day_triggers_overnight() -> None:
    print("\n── Test 13: close_day with overnight mode runs queued tasks ──")

    _reset_all()

    # Open a day
    open_day(workspace="builder", node_preference="auto", discord_channel_id=None)

    # Create tasks, queue one for overnight
    t1 = create_task("run nightly data sync")
    process_task(t1, is_day_open=False)  # → OVERNIGHT_QUEUED

    # Close the day with overnight tasks (triggers OVERNIGHT mode)
    result = close_day(
        completed_today=["built task system"],
        unresolved=[],
        overnight_tasks=["data sync"],
        continuity_notes=None,
        resume_context=None,
        discord_channel_id=None,
    )

    _report(
        "status is ok",
        result.get("status") == "ok",
        f"got {result.get('status')!r}",
    )
    _report(
        "overnight_tasks_executed present",
        "overnight_tasks_executed" in result,
        f"keys: {list(result.keys())}",
    )

    # Verify the task was completed
    reloaded = TaskStore.default().get(t1.task_id)
    _report(
        "queued task now COMPLETED",
        reloaded is not None and reloaded.status == TaskStatus.COMPLETED,
        f"got {reloaded.status.value if reloaded else 'None'}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Task System Smoke Tests")
    print("=" * 60)

    test_classify_autonomous()
    test_classify_needs_operator()
    test_classify_needs_approval()
    test_create_autonomous_task()
    test_create_operator_task()
    test_process_autonomous_day_open()
    test_process_autonomous_day_closed()
    test_process_operator_task()
    test_overnight_execution()
    test_task_summary()
    test_restart_safe()
    test_open_day_includes_task_summary()
    test_close_day_triggers_overnight()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
