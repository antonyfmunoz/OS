"""Smoke tests for eos_ai.substrate.task_execution.

Validates:
  1.  test_execute_autonomous_dry_run      — dry_run routes + completes without tmux
  2.  test_execute_skips_non_autonomous     — non-autonomous tasks returned unchanged
  3.  test_execute_skips_wrong_status       — only READY/OVERNIGHT_QUEUED are executed
  4.  test_human_block_detection            — detect_human_block catches block phrases
  5.  test_human_block_negative             — normal output does not trigger block
  6.  test_execution_attaches_routing       — executed task has routing metadata
  7.  test_execution_timestamps             — execution_started_at and finished_at set
  8.  test_overnight_execution_dry_run      — batch execution in priority order
  9.  test_overnight_skips_operator_tasks   — operator tasks not processed
 10.  test_state_transitions_correct        — dry_run: READY → IN_PROGRESS → COMPLETED
 11.  test_persistence_survives_restart     — executed task persists across singleton reset

Run directly:
    python3 tests/substrate/test_task_execution.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.operator_session import (  # noqa: E402
    OperatorSession,
    OperatorSessionStore,
)
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402
from eos_ai.substrate.task_execution import (  # noqa: E402
    detect_human_block,
    execute_task,
    run_overnight_execution,
)
from eos_ai.substrate.task_system import (  # noqa: E402
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    create_task,
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


# ─── Test 1: dry_run execution ─────────────────────────────────────────────


def test_execute_autonomous_dry_run() -> None:
    print("\n── Test 1: dry_run routes + completes without tmux ──")

    _reset_all()

    task = create_task("rebuild the graph index")
    session = OperatorSession.new()
    session.node_preference = "vps"

    result = execute_task(task, session, dry_run=True)

    _report(
        "status is COMPLETED",
        result.status == TaskStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "execution_result set",
        result.execution_result is not None and len(result.execution_result) > 0,
        f"got {result.execution_result}",
    )
    _report(
        "chosen_target set",
        result.chosen_target is not None,
        f"got {result.chosen_target}",
    )


# ─── Test 2: skip non-autonomous ──────────────────────────────────────────


def test_execute_skips_non_autonomous() -> None:
    print("\n── Test 2: non-autonomous tasks returned unchanged ──")

    _reset_all()

    task = create_task("decide which vendor to use")  # → NEEDS_OPERATOR
    original_status = task.status

    result = execute_task(task, dry_run=True)

    _report(
        "status unchanged",
        result.status == original_status,
        f"got {result.status.value}",
    )


# ─── Test 3: skip wrong status ────────────────────────────────────────────


def test_execute_skips_wrong_status() -> None:
    print("\n── Test 3: only READY/OVERNIGHT_QUEUED are executed ──")

    _reset_all()

    task = create_task("send report")
    task.status = TaskStatus.COMPLETED
    TaskStore.default().put(task)

    result = execute_task(task, dry_run=True)

    _report(
        "still COMPLETED (not re-executed)",
        result.status == TaskStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "no execution_result (not re-executed)",
        result.execution_result is None,
    )


# ─── Test 4: human block detection ────────────────────────────────────────


def test_human_block_detection() -> None:
    print("\n── Test 4: detect_human_block catches block phrases ──")

    cases = [
        ("I need your input on the next step", "need your input"),
        ("Need approval before continuing", "Need approval"),
        ("Please choose between option A and B", "choose between"),
        ("Which option do you prefer?", "which option"),
        ("Please confirm before proceeding", "confirm before"),
    ]
    for text, expected_phrase in cases:
        result = detect_human_block(text)
        _report(
            f"'{text}' → blocked",
            result is not None,
            f"got {result!r}",
        )


# ─── Test 5: human block negative ─────────────────────────────────────────


def test_human_block_negative() -> None:
    print("\n── Test 5: normal output does not trigger block ──")

    cases = [
        "Task completed successfully",
        "Generated 15 entries",
        "Report sent to all recipients",
        "Build passed with 0 errors",
        "",
    ]
    for text in cases:
        result = detect_human_block(text)
        _report(
            f"'{text}' → not blocked",
            result is None,
            f"got {result!r}",
        )


# ─── Test 6: execution attaches routing ───────────────────────────────────


def test_execution_attaches_routing() -> None:
    print("\n── Test 6: executed task has routing metadata ──")

    _reset_all()

    task = create_task("deploy the new API endpoint")
    session = OperatorSession.new()
    session.node_preference = "vps"

    result = execute_task(task, session, dry_run=True)

    _report(
        "required_capabilities populated",
        len(result.required_capabilities) > 0,
        f"got {result.required_capabilities}",
    )
    _report(
        "routing_reason set",
        result.routing_reason is not None,
        f"got {result.routing_reason}",
    )


# ─── Test 7: execution timestamps ─────────────────────────────────────────


def test_execution_timestamps() -> None:
    print("\n── Test 7: execution_started_at and finished_at set ──")

    _reset_all()

    task = create_task("generate the summary")
    result = execute_task(task, dry_run=True)

    _report(
        "execution_started_at set",
        result.execution_started_at is not None,
        f"got {result.execution_started_at}",
    )
    _report(
        "execution_finished_at set",
        result.execution_finished_at is not None,
        f"got {result.execution_finished_at}",
    )
    _report(
        "started <= finished",
        result.execution_started_at <= result.execution_finished_at,
    )


# ─── Test 8: overnight execution dry_run ──────────────────────────────────


def test_overnight_execution_dry_run() -> None:
    print("\n── Test 8: batch execution in priority order (dry_run) ──")

    _reset_all()

    # Create tasks with different priorities
    t1 = create_task("sync CRM data")
    t1.status = TaskStatus.OVERNIGHT_QUEUED
    t1.priority = 50
    TaskStore.default().put(t1)

    t2 = create_task("urgent security patch for code")
    t2.status = TaskStatus.OVERNIGHT_QUEUED
    t2.priority = 100
    TaskStore.default().put(t2)

    t3 = create_task("generate weekly summary")
    t3.status = TaskStatus.OVERNIGHT_QUEUED
    t3.priority = 25
    TaskStore.default().put(t3)

    result = run_overnight_execution(dry_run=True)

    _report(
        "3 tasks executed",
        result["executed"] == 3,
        f"got {result['executed']}",
    )
    _report(
        "3 tasks completed",
        result["completed"] == 3,
        f"got {result['completed']}",
    )
    _report(
        "0 blocked",
        result["blocked"] == 0,
        f"got {result['blocked']}",
    )

    # Verify priority ordering in task_results
    ids = [tr["task_id"] for tr in result["task_results"]]
    _report(
        "highest priority executed first",
        ids[0] == t2.task_id,
        f"expected {t2.task_id}, got {ids[0]}",
    )


# ─── Test 9: overnight skips operator tasks ───────────────────────────────


def test_overnight_skips_operator_tasks() -> None:
    print("\n── Test 9: operator tasks not processed in overnight ──")

    _reset_all()

    t1 = create_task("sync data")
    t1.status = TaskStatus.OVERNIGHT_QUEUED
    TaskStore.default().put(t1)

    t2 = create_task("should I change pricing?")  # → NEEDS_OPERATOR
    # t2 is WAITING_ON_OPERATOR from creation — not in executable queue

    result = run_overnight_execution(dry_run=True)

    _report(
        "only 1 task executed (autonomous one)",
        result["executed"] == 1,
        f"got {result['executed']}",
    )

    # Operator task untouched
    reloaded = TaskStore.default().get(t2.task_id)
    _report(
        "operator task still WAITING_ON_OPERATOR",
        reloaded is not None and reloaded.status == TaskStatus.WAITING_ON_OPERATOR,
        f"got {reloaded.status.value if reloaded else 'None'}",
    )


# ─── Test 10: state transitions ───────────────────────────────────────────


def test_state_transitions_correct() -> None:
    print("\n── Test 10: READY → COMPLETED via dry_run ──")

    _reset_all()

    task = create_task("generate report")
    _report(
        "starts as READY",
        task.status == TaskStatus.READY,
        f"got {task.status.value}",
    )

    result = execute_task(task, dry_run=True)
    _report(
        "ends as COMPLETED",
        result.status == TaskStatus.COMPLETED,
        f"got {result.status.value}",
    )


# ─── Test 11: persistence survives restart ─────────────────────────────────


def test_persistence_survives_restart() -> None:
    print("\n── Test 11: executed task persists across singleton reset ──")

    _reset_all()

    task = create_task("persist execution result")
    execute_task(task, dry_run=True)

    # Reset singleton
    TaskStore.reset_default_for_tests()

    reloaded = TaskStore.default().get(task.task_id)
    _report(
        "task reloads",
        reloaded is not None,
    )
    if reloaded:
        _report(
            "status survives",
            reloaded.status == TaskStatus.COMPLETED,
            f"got {reloaded.status.value}",
        )
        _report(
            "execution_result survives",
            reloaded.execution_result is not None
            and len(reloaded.execution_result) > 0,
            f"got {reloaded.execution_result}",
        )
        _report(
            "chosen_target survives",
            reloaded.chosen_target is not None,
            f"got {reloaded.chosen_target}",
        )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Task Execution Smoke Tests")
    print("=" * 60)

    test_execute_autonomous_dry_run()
    test_execute_skips_non_autonomous()
    test_execute_skips_wrong_status()
    test_human_block_detection()
    test_human_block_negative()
    test_execution_attaches_routing()
    test_execution_timestamps()
    test_overnight_execution_dry_run()
    test_overnight_skips_operator_tasks()
    test_state_transitions_correct()
    test_persistence_survives_restart()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
