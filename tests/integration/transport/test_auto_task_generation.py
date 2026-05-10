"""Smoke tests for eos_ai.substrate.auto_task_generation.

Validates:
  1.  test_generate_from_warning    — WARNING perception generates a task
  2.  test_skip_info                — INFO perception does NOT generate a task
  3.  test_dedup_same_perception    — same perception twice does not create duplicate task
  4.  test_run_perception_cycle     — full cycle returns valid summary dict
  5.  test_get_perception_summary   — summary returns expected keys
  6.  test_critical_generates_task  — CRITICAL perception generates a task

Run directly:
    python3 tests/substrate/test_auto_task_generation.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.perception import (  # noqa: E402
    PerceptionRecord,
    PerceptionSeverity,
    PerceptionSource,
    PerceptionStore,
)
from eos_ai.substrate.auto_task_generation import (  # noqa: E402
    generate_tasks_from_perceptions,
    get_perception_summary,
    run_perception_cycle,
)
from eos_ai.substrate.task_system import TaskStore  # noqa: E402

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
    """Reset perception and task store singletons and clear storage keys."""
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("perception_records", None)
        get_storage().put("task_system", None)
    except Exception:  # noqa: BLE001
        pass
    PerceptionStore.reset_default_for_tests()
    TaskStore.reset_default_for_tests()


# ─── Test 1: WARNING perception generates a task ────────────────────────────


def test_generate_from_warning() -> None:
    print("\n── Test 1: WARNING perception generates a task ──")

    _reset_all()

    record = PerceptionRecord.new(
        source=PerceptionSource.TASK_SYSTEM,
        summary="Task blocked >4h: rebuild graph",
        severity=PerceptionSeverity.WARNING,
        payload={"task_id": "task_abc123", "hours_blocked": 5.2},
        suggested_action="Review blocked tasks",
    )

    result = generate_tasks_from_perceptions([record])

    _report(
        "one task created",
        len(result) == 1,
        f"got {len(result)}",
    )
    if result:
        _report(
            "task title starts with [auto] ",
            result[0].title.startswith("[auto] "),
            f"got {result[0].title!r}",
        )


# ─── Test 2: INFO perception does NOT generate a task ───────────────────────


def test_skip_info() -> None:
    print("\n── Test 2: INFO perception does NOT generate a task ──")

    _reset_all()

    record = PerceptionRecord.new(
        source=PerceptionSource.GIT_STATUS,
        summary="Unpushed commits: 2",
        severity=PerceptionSeverity.INFO,
        payload={"commit_count": 2},
    )

    result = generate_tasks_from_perceptions([record])

    _report(
        "zero tasks created for INFO",
        len(result) == 0,
        f"got {len(result)}",
    )


# ─── Test 3: dedup — same perception twice does not create duplicate ─────────


def test_dedup_same_perception() -> None:
    print("\n── Test 3: dedup — same perception twice does not create duplicate ──")

    _reset_all()

    record = PerceptionRecord.new(
        source=PerceptionSource.TASK_SYSTEM,
        summary="Task blocked >4h: rebuild graph",
        severity=PerceptionSeverity.WARNING,
        payload={"task_id": "task_abc123", "hours_blocked": 5.2},
        suggested_action="Review blocked tasks",
    )

    first_result = generate_tasks_from_perceptions([record])
    _report(
        "first call creates 1 task",
        len(first_result) == 1,
        f"got {len(first_result)}",
    )

    second_result = generate_tasks_from_perceptions([record])
    _report(
        "second call creates 0 tasks (dedup)",
        len(second_result) == 0,
        f"got {len(second_result)}",
    )

    # Verify store has exactly 1 task with this title
    store = TaskStore.default()
    all_tasks = store.all()
    matching = [t for t in all_tasks if t.title == "[auto] Review blocked tasks"]
    _report(
        "TaskStore has exactly 1 task with that title",
        len(matching) == 1,
        f"got {len(matching)}",
    )


# ─── Test 4: full cycle returns valid summary dict ──────────────────────────


def test_run_perception_cycle() -> None:
    print("\n── Test 4: full cycle returns valid summary dict ──")

    _reset_all()

    result = run_perception_cycle()

    expected_keys = {
        "perceptions_collected",
        "perceptions_new",
        "critical_count",
        "warning_count",
        "info_count",
        "tasks_generated",
        "generated_task_ids",
        "top_issue_summary",
    }

    _report(
        "return type is dict",
        isinstance(result, dict),
        f"got {type(result).__name__}",
    )
    missing = expected_keys - set(result.keys())
    _report(
        "all expected keys present",
        len(missing) == 0,
        f"missing: {missing}" if missing else "",
    )
    _report(
        "perceptions_collected is int",
        isinstance(result.get("perceptions_collected"), int),
        f"got {type(result.get('perceptions_collected')).__name__}",
    )
    _report(
        "generated_task_ids is list",
        isinstance(result.get("generated_task_ids"), list),
        f"got {type(result.get('generated_task_ids')).__name__}",
    )


# ─── Test 5: summary returns expected keys ──────────────────────────────────


def test_get_perception_summary() -> None:
    print("\n── Test 5: summary returns expected keys ──")

    _reset_all()

    result = get_perception_summary()

    expected_keys = {
        "critical_count",
        "warning_count",
        "info_count",
        "generated_task_count",
        "top_issue_summary",
    }

    _report(
        "return type is dict",
        isinstance(result, dict),
        f"got {type(result).__name__}",
    )
    missing = expected_keys - set(result.keys())
    _report(
        "all expected keys present",
        len(missing) == 0,
        f"missing: {missing}" if missing else "",
    )
    _report(
        "critical_count is int",
        isinstance(result.get("critical_count"), int),
        f"got {type(result.get('critical_count')).__name__}",
    )
    _report(
        "generated_task_count is int",
        isinstance(result.get("generated_task_count"), int),
        f"got {type(result.get('generated_task_count')).__name__}",
    )


# ─── Test 6: CRITICAL perception generates a task ───────────────────────────


def test_critical_generates_task() -> None:
    print("\n── Test 6: CRITICAL perception generates a task ──")

    _reset_all()

    record = PerceptionRecord.new(
        source=PerceptionSource.PIPELINE_SYSTEM,
        summary="Pipeline failed: deploy-prod",
        severity=PerceptionSeverity.CRITICAL,
        payload={"pipeline_id": "pipe_xyz"},
        suggested_action="Review failed pipeline: deploy-prod",
    )

    result = generate_tasks_from_perceptions([record])

    _report(
        "one task created for CRITICAL",
        len(result) == 1,
        f"got {len(result)}",
    )
    if result:
        _report(
            "task title starts with [auto] ",
            result[0].title.startswith("[auto] "),
            f"got {result[0].title!r}",
        )


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Auto Task Generation Smoke Tests")
    print("=" * 60)

    test_generate_from_warning()
    test_skip_info()
    test_dedup_same_perception()
    test_run_perception_cycle()
    test_get_perception_summary()
    test_critical_generates_task()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
