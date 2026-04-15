"""Smoke tests for eos_ai.substrate.task_queue.

Validates:
  1.  test_priority_urgent_keywords    — urgency keywords → CRITICAL
  2.  test_priority_operator_tasks     — NEEDS_OPERATOR → HIGH
  3.  test_priority_autonomous_default — AUTONOMOUS → NORMAL
  4.  test_priority_default_low        — NEEDS_APPROVAL → LOW
  5.  test_queue_operator_blocked      — NEEDS_OPERATOR → operator_blocked
  6.  test_queue_autonomous_day        — AUTONOMOUS + day open → autonomous_day
  7.  test_queue_autonomous_overnight  — AUTONOMOUS + day closed → autonomous_overnight
  8.  test_queue_approval_waiting      — NEEDS_APPROVAL → approval_waiting
  9.  test_get_ready_tasks_sorted      — priority desc, created_at asc
 10.  test_get_tasks_sorted_for_execution — READY + OVERNIGHT combined
 11.  test_enhanced_task_summary       — includes queued_autonomous + top_priority
 12.  test_prepare_overnight_queue     — READY → OVERNIGHT_QUEUED
 13.  test_prioritize_and_queue        — single call sets both fields
 14.  test_overnight_preserves_operator — prepare_overnight_queue skips operator tasks

Run directly:
    python3 tests/substrate/test_task_queue.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.operator_session import OperatorSessionStore  # noqa: E402
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402
from eos_ai.substrate.task_queue import (  # noqa: E402
    QUEUE_APPROVAL_WAITING,
    QUEUE_AUTONOMOUS_DAY,
    QUEUE_AUTONOMOUS_OVERNIGHT,
    QUEUE_OPERATOR_BLOCKED,
    TaskPriority,
    assign_queue,
    get_enhanced_task_summary,
    get_ready_tasks,
    get_tasks_sorted_for_execution,
    get_waiting_on_operator_tasks,
    infer_task_priority,
    prepare_overnight_queue,
    prioritize_and_queue,
)
from eos_ai.substrate.task_system import (  # noqa: E402
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    create_task,
    process_task,
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
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("task_system", None)
        get_storage().put("operator_session", None)
        get_storage().put("rituals", {})
    except Exception:
        pass
    TaskStore.reset_default_for_tests()
    OperatorSessionStore.reset_default_for_tests()
    RitualRegistry.reset_default_for_tests()


# ─── Test 1: priority urgent keywords ──────────────────────────────────────


def test_priority_urgent_keywords() -> None:
    print("\n── Test 1: urgency keywords → CRITICAL ──")

    _reset_all()

    cases = [
        "urgent fix needed for the API",
        "ASAP deploy the security patch",
        "critical production issue",
        "blocked on database migration",
    ]
    for text in cases:
        task = create_task(text)
        priority = infer_task_priority(task)
        _report(
            f"'{text}' → CRITICAL ({TaskPriority.CRITICAL})",
            priority == TaskPriority.CRITICAL,
            f"got {priority}",
        )


# ─── Test 2: priority operator tasks ──────────────────────────────────────


def test_priority_operator_tasks() -> None:
    print("\n── Test 2: NEEDS_OPERATOR → HIGH ──")

    _reset_all()

    task = create_task("decide which framework to use")
    priority = infer_task_priority(task)
    _report(
        "NEEDS_OPERATOR → HIGH",
        priority == TaskPriority.HIGH,
        f"got {priority}",
    )


# ─── Test 3: priority autonomous default ──────────────────────────────────


def test_priority_autonomous_default() -> None:
    print("\n── Test 3: AUTONOMOUS → NORMAL ──")

    _reset_all()

    task = create_task("send the weekly digest")
    priority = infer_task_priority(task)
    _report(
        "AUTONOMOUS → NORMAL",
        priority == TaskPriority.NORMAL,
        f"got {priority}",
    )


# ─── Test 4: priority default low ─────────────────────────────────────────


def test_priority_default_low() -> None:
    print("\n── Test 4: NEEDS_APPROVAL → LOW ──")

    _reset_all()

    task = create_task("review the PR before merging")
    priority = infer_task_priority(task)
    _report(
        "NEEDS_APPROVAL → LOW",
        priority == TaskPriority.LOW,
        f"got {priority}",
    )


# ─── Test 5: queue operator blocked ───────────────────────────────────────


def test_queue_operator_blocked() -> None:
    print("\n── Test 5: NEEDS_OPERATOR → operator_blocked ──")

    _reset_all()

    task = create_task("decide on the vendor")
    queue = assign_queue(task, is_day_open=True)
    _report(
        "queue is operator_blocked",
        queue == QUEUE_OPERATOR_BLOCKED,
        f"got {queue}",
    )


# ─── Test 6: queue autonomous day ─────────────────────────────────────────


def test_queue_autonomous_day() -> None:
    print("\n── Test 6: AUTONOMOUS + day open → autonomous_day ──")

    _reset_all()

    task = create_task("send the report")
    queue = assign_queue(task, is_day_open=True)
    _report(
        "queue is autonomous_day",
        queue == QUEUE_AUTONOMOUS_DAY,
        f"got {queue}",
    )


# ─── Test 7: queue autonomous overnight ───────────────────────────────────


def test_queue_autonomous_overnight() -> None:
    print("\n── Test 7: AUTONOMOUS + day closed → autonomous_overnight ──")

    _reset_all()

    task = create_task("sync the database")
    queue = assign_queue(task, is_day_open=False)
    _report(
        "queue is autonomous_overnight",
        queue == QUEUE_AUTONOMOUS_OVERNIGHT,
        f"got {queue}",
    )


# ─── Test 8: queue approval waiting ───────────────────────────────────────


def test_queue_approval_waiting() -> None:
    print("\n── Test 8: NEEDS_APPROVAL → approval_waiting ──")

    _reset_all()

    task = create_task("review the new homepage design")
    queue = assign_queue(task, is_day_open=True)
    _report(
        "queue is approval_waiting",
        queue == QUEUE_APPROVAL_WAITING,
        f"got {queue}",
    )


# ─── Test 9: get_ready_tasks sorted ───────────────────────────────────────


def test_get_ready_tasks_sorted() -> None:
    print("\n── Test 9: get_ready_tasks — priority desc, created_at asc ──")

    _reset_all()

    t1 = create_task("low priority task")
    t1.priority = 25
    TaskStore.default().put(t1)

    time.sleep(0.01)  # ensure distinct timestamps

    t2 = create_task("high priority task")
    t2.priority = 75
    TaskStore.default().put(t2)

    time.sleep(0.01)

    t3 = create_task("another high priority task")
    t3.priority = 75
    TaskStore.default().put(t3)

    ready = get_ready_tasks()
    ids = [t.task_id for t in ready]

    _report(
        "3 ready tasks",
        len(ready) == 3,
        f"got {len(ready)}",
    )
    _report(
        "highest priority first (t2)",
        ids[0] == t2.task_id,
        f"got {ids[0]}, expected {t2.task_id}",
    )
    _report(
        "same priority → FIFO (t2 before t3)",
        ids.index(t2.task_id) < ids.index(t3.task_id),
        f"t2 at {ids.index(t2.task_id)}, t3 at {ids.index(t3.task_id)}",
    )
    _report(
        "low priority last (t1)",
        ids[-1] == t1.task_id,
        f"got {ids[-1]}, expected {t1.task_id}",
    )


# ─── Test 10: get_tasks_sorted_for_execution ──────────────────────────────


def test_get_tasks_sorted_for_execution() -> None:
    print("\n── Test 10: READY + OVERNIGHT combined and sorted ──")

    _reset_all()

    t1 = create_task("ready task low")
    t1.priority = 25
    TaskStore.default().put(t1)

    t2 = create_task("overnight task high")
    t2.status = TaskStatus.OVERNIGHT_QUEUED
    t2.priority = 90
    TaskStore.default().put(t2)

    all_exec = get_tasks_sorted_for_execution()

    _report(
        "2 executable tasks",
        len(all_exec) == 2,
        f"got {len(all_exec)}",
    )
    _report(
        "overnight high-priority first",
        all_exec[0].task_id == t2.task_id,
        f"got {all_exec[0].task_id}",
    )


# ─── Test 11: enhanced task summary ───────────────────────────────────────


def test_enhanced_task_summary() -> None:
    print("\n── Test 11: enhanced summary includes queued_autonomous + top_priority ──")

    _reset_all()

    t1 = create_task("sync CRM data")
    t1.priority = 75
    TaskStore.default().put(t1)

    t2 = create_task("should I use React?")  # → WAITING_ON_OPERATOR

    summary = get_enhanced_task_summary()

    _report(
        "queued_autonomous present",
        "queued_autonomous" in summary,
        f"keys: {list(summary.keys())}",
    )
    _report(
        "queued_autonomous >= 1",
        summary.get("queued_autonomous", 0) >= 1,
        f"got {summary.get('queued_autonomous')}",
    )
    _report(
        "top_priority_task_title present",
        "top_priority_task_title" in summary,
    )
    _report(
        "top_priority is the READY task",
        summary.get("top_priority_task_title") == "sync CRM data",
        f"got {summary.get('top_priority_task_title')}",
    )


# ─── Test 12: prepare overnight queue ─────────────────────────────────────


def test_prepare_overnight_queue() -> None:
    print("\n── Test 12: READY autonomous → OVERNIGHT_QUEUED ──")

    _reset_all()

    t1 = create_task("nightly sync")
    t2 = create_task("background research")

    result = prepare_overnight_queue()

    _report(
        "moved_to_overnight == 2",
        result["moved_to_overnight"] == 2,
        f"got {result['moved_to_overnight']}",
    )

    reloaded1 = TaskStore.default().get(t1.task_id)
    _report(
        "t1 now OVERNIGHT_QUEUED",
        reloaded1 is not None and reloaded1.status == TaskStatus.OVERNIGHT_QUEUED,
        f"got {reloaded1.status.value if reloaded1 else 'None'}",
    )
    _report(
        "t1 queue_name is autonomous_overnight",
        reloaded1 is not None and reloaded1.queue_name == QUEUE_AUTONOMOUS_OVERNIGHT,
        f"got {reloaded1.queue_name if reloaded1 else 'None'}",
    )


# ─── Test 13: prioritize_and_queue ────────────────────────────────────────


def test_prioritize_and_queue() -> None:
    print("\n── Test 13: prioritize_and_queue sets both fields ──")

    _reset_all()

    task = create_task("urgent fix the production issue")
    prioritize_and_queue(task, is_day_open=True)

    _report(
        "priority is CRITICAL",
        task.priority == TaskPriority.CRITICAL,
        f"got {task.priority}",
    )
    _report(
        "queue_name is autonomous_day",
        task.queue_name == QUEUE_AUTONOMOUS_DAY,
        f"got {task.queue_name}",
    )


# ─── Test 14: overnight preserves operator tasks ──────────────────────────


def test_overnight_preserves_operator() -> None:
    print("\n── Test 14: prepare_overnight_queue skips operator tasks ──")

    _reset_all()

    t1 = create_task("nightly sync")  # → READY
    t2 = create_task("decide on the vendor")  # → WAITING_ON_OPERATOR

    result = prepare_overnight_queue()

    _report(
        "only 1 moved (autonomous only)",
        result["moved_to_overnight"] == 1,
        f"got {result['moved_to_overnight']}",
    )
    _report(
        "preserved_operator_blocked == 1",
        result["preserved_operator_blocked"] == 1,
        f"got {result['preserved_operator_blocked']}",
    )

    # Operator task untouched
    reloaded = TaskStore.default().get(t2.task_id)
    _report(
        "operator task still WAITING_ON_OPERATOR",
        reloaded is not None and reloaded.status == TaskStatus.WAITING_ON_OPERATOR,
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Task Queue Smoke Tests")
    print("=" * 60)

    test_priority_urgent_keywords()
    test_priority_operator_tasks()
    test_priority_autonomous_default()
    test_priority_default_low()
    test_queue_operator_blocked()
    test_queue_autonomous_day()
    test_queue_autonomous_overnight()
    test_queue_approval_waiting()
    test_get_ready_tasks_sorted()
    test_get_tasks_sorted_for_execution()
    test_enhanced_task_summary()
    test_prepare_overnight_queue()
    test_prioritize_and_queue()
    test_overnight_preserves_operator()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
