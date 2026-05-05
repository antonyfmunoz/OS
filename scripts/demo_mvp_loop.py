#!/usr/bin/env python3
"""UMH MVP Demo — exercises the complete operator loop.

Runs through: plan -> validate -> quality -> execute -> monitor -> summary
Uses internal APIs for reliability (no HTTP server needed).

Exit codes:
    0 — all paths passed
    1 — one or more paths failed
"""

import sys

sys.path.insert(0, "/opt/OS")

import os

os.environ["UMH_TASK_BACKEND"] = "memory"
os.environ.setdefault("UMH_API_KEY", "demo-key-mvp")

from umh.orchestrator.summary import summarize_task
from umh.orchestrator.task import (
    Task,
    TaskStatus,
    TaskStep,
    enqueue_task,
    execute_task,
)
from umh.orchestrator.timeline import build_task_timeline
from umh.planning.models import PlanObjective, PlanStatus
from umh.planning.planner import create_plan, create_plan_from_raw, execute_plan

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        _PASS += 1
    else:
        _FAIL += 1
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def demo_path1_plan_only() -> None:
    """Path 1: Plan Only — create_plan_from_raw without execution."""
    print("\n--- Path 1: Plan Only ---")

    plan = create_plan_from_raw("check system health")

    _report(
        "plan created",
        plan is not None and plan.plan_id.startswith("eplan_"),
        f"plan_id={plan.plan_id}",
    )
    _report(
        "plan validated",
        plan.status == PlanStatus.VALIDATED,
        f"status={plan.status.value}",
    )
    _report(
        "quality scored",
        plan.quality_score is not None and "verdict" in plan.quality_score,
        f"verdict={plan.quality_score.get('verdict', 'none') if plan.quality_score else 'none'}",
    )
    _report(
        "explanation attached",
        plan.explanation is not None and "objective_summary" in plan.explanation,
    )
    _report(
        "steps populated",
        len(plan.steps) > 0,
        f"step_count={len(plan.steps)}",
    )
    _report(
        "source is template",
        plan.source.value == "template",
        f"source={plan.source.value}",
    )


def demo_path2_execute_safe() -> None:
    """Path 2: Execute Safe Workflow — plan + execute through task system."""
    print("\n--- Path 2: Execute Safe Workflow ---")

    plan = create_plan_from_raw("check system health")
    _report(
        "plan validated for execution",
        plan.status == PlanStatus.VALIDATED,
        f"plan_id={plan.plan_id}",
    )

    task = execute_plan(plan)
    _report(
        "task returned",
        task is not None,
    )

    if task is None:
        _report("task execution", False, "execute_plan returned None")
        return

    _report(
        "task completed",
        task.status == TaskStatus.COMPLETED,
        f"status={task.status.value}, task_id={task.id}",
    )

    completed_steps = sum(1 for s in task.steps if s.status.value == "completed")
    _report(
        "all steps completed",
        completed_steps == len(task.steps),
        f"{completed_steps}/{len(task.steps)}",
    )

    # Verify summary works
    summary = summarize_task(task)
    _report(
        "summary generated",
        summary is not None and summary["status"] == "completed",
        f"final_summary={summary['final_summary'][:60]}",
    )

    # Verify timeline works
    timeline = build_task_timeline(task.id)
    _report(
        "timeline populated",
        len(timeline) > 0,
        f"entries={len(timeline)}",
    )


def demo_path3_enqueue_task() -> None:
    """Path 3: Enqueue Task — verify pending state without execution."""
    print("\n--- Path 3: Enqueue Task ---")

    steps = [
        TaskStep(
            operation="file_read",
            inputs_template={"path": "/opt/OS/README.md"},
            execution_class="side_effect",
        ),
    ]
    task = Task(steps=steps, issued_by="demo")
    result = enqueue_task(task)

    _report(
        "task enqueued",
        result is not None,
        f"task_id={result.id}",
    )
    _report(
        "status is pending",
        result.status == TaskStatus.PENDING,
        f"status={result.status.value}",
    )
    _report(
        "steps preserved",
        len(result.steps) == 1,
        f"step_count={len(result.steps)}",
    )


def demo_path4_plan_rejection() -> None:
    """Path 4: Plan Rejection — unknown intent fails quality gate."""
    print("\n--- Path 4: Plan Rejection ---")

    plan = create_plan_from_raw("do something completely invalid and weird")

    _report(
        "plan created",
        plan is not None,
        f"plan_id={plan.plan_id}",
    )
    _report(
        "plan rejected",
        plan.status == PlanStatus.REJECTED,
        f"status={plan.status.value}",
    )
    _report(
        "quality is fail",
        plan.quality_score is not None and plan.quality_score.get("verdict") == "fail",
        f"verdict={plan.quality_score.get('verdict', 'none') if plan.quality_score else 'none'}",
    )
    _report(
        "validation errors present",
        len(plan.validation_errors) > 0,
        f"errors={plan.validation_errors}",
    )


def demo_path5_summary_and_timeline() -> None:
    """Path 5: Summary + Timeline — verify summary and timeline modules."""
    print("\n--- Path 5: Summary + Timeline ---")

    # Execute a plan to get a real task
    plan = create_plan_from_raw("check system health")
    task = execute_plan(plan)

    if task is None:
        _report("setup failed", False, "execute_plan returned None")
        return

    # Test summarize_task
    summary = summarize_task(task)
    _report(
        "summary is dict",
        isinstance(summary, dict),
    )
    _report(
        "summary has required keys",
        all(
            k in summary
            for k in [
                "task_id",
                "status",
                "completed_steps",
                "failed_steps",
                "total_steps",
                "final_summary",
                "next_action",
                "step_summaries",
                "errors",
            ]
        ),
    )
    _report(
        "step summaries match step count",
        len(summary["step_summaries"]) == len(task.steps),
        f"summaries={len(summary['step_summaries'])}, steps={len(task.steps)}",
    )
    _report(
        "no errors on success",
        len(summary["errors"]) == 0,
    )

    # Test timeline
    timeline = build_task_timeline(task.id)
    _report(
        "timeline has entries",
        len(timeline) > 0,
        f"entries={len(timeline)}",
    )

    event_types = [e.event_type for e in timeline]
    _report(
        "timeline has task events",
        any("task." in t for t in event_types),
        f"types={event_types[:5]}",
    )


def main() -> int:
    print("=" * 60)
    print("UMH MVP Demo — Golden Path Verification")
    print("=" * 60)

    demo_path1_plan_only()
    demo_path2_execute_safe()
    demo_path3_enqueue_task()
    demo_path4_plan_rejection()
    demo_path5_summary_and_timeline()

    print("\n" + "=" * 60)
    total = _PASS + _FAIL
    print(f"Results: {_PASS}/{total} passed, {_FAIL}/{total} failed")
    print("=" * 60)

    if _FAIL > 0:
        print("\nDEMO FAILED")
        return 1

    print("\nDEMO PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
