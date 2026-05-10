"""Smoke tests for eos_ai.substrate.pipeline_execution.

Validates:
  1.  test_pipeline_dry_run_completes       — full pipeline dry_run → COMPLETED
  2.  test_pipeline_step_by_step            — single step advance per call
  3.  test_pipeline_advance_all             — advance_all pushes all steps
  4.  test_pipeline_blocked_on_operator     — human block pauses pipeline
  5.  test_failed_step_retry                — retry_step resets and re-executes
  6.  test_resume_pipeline_from_step        — resume skips completed steps
  7.  test_overnight_pipelines_priority     — overnight advances multiple pipelines
  8.  test_completed_steps_not_rerun        — completed steps skipped on resume
  9.  test_persistence_survives_restart     — pipeline persists across reset
 10.  test_task_pipeline_integration        — task.pipeline_id set after execution
 11.  test_pipeline_summary                 — get_pipeline_summary returns counts
 12.  test_format_blocked_summary           — format_blocked_summary output
 13.  test_format_pipeline_summary          — format_pipeline_summary output

Run directly:
    python3 tests/substrate/test_pipeline_execution.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.operator_session import (  # noqa: E402
    OperatorSession,
    OperatorSessionStore,
)
from eos_ai.substrate.pipeline_execution import (  # noqa: E402
    execute_pipeline,
    format_blocked_summary,
    format_pipeline_summary,
    get_pipeline_summary,
    resume_pipeline,
    retry_step,
)
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402
from eos_ai.substrate.task_decomposition import decompose_task  # noqa: E402
from eos_ai.substrate.task_execution import execute_task  # noqa: E402
from eos_ai.substrate.task_pipeline import (  # noqa: E402
    PipelineAgentRole,
    PipelineStatus,
    PipelineStep,
    PipelineStore,
    StepStatus,
    TaskPipeline,
)
from eos_ai.substrate.task_system import (  # noqa: E402
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
        get_storage().put("task_pipelines", None)
        get_storage().put("operator_session", None)
        get_storage().put("rituals", {})
    except Exception:
        pass
    TaskStore.reset_default_for_tests()
    PipelineStore.reset_default_for_tests()
    OperatorSessionStore.reset_default_for_tests()
    RitualRegistry.reset_default_for_tests()


# ─── Test 1: dry_run pipeline completes ──────────────────────────────────────


def test_pipeline_dry_run_completes() -> None:
    print("\n── Test 1: full pipeline dry_run → COMPLETED ──")

    _reset_all()

    task = create_task("fix the broken test suite")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    result = execute_pipeline(pipeline, dry_run=True, advance_all=True)

    _report(
        "pipeline COMPLETED",
        result.status == PipelineStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "all steps COMPLETED",
        all(s.status == StepStatus.COMPLETED for s in result.steps),
        f"got {[s.status.value for s in result.steps]}",
    )
    _report(
        "summary set",
        result.summary is not None and "completed" in result.summary.lower(),
        f"got {result.summary}",
    )


# ─── Test 2: step-by-step execution ─────────────────────────────────────────


def test_pipeline_step_by_step() -> None:
    print("\n── Test 2: single step advance per call ──")

    _reset_all()

    task = create_task("build the new module")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Execute step 0 only (advance_all=False is default)
    result = execute_pipeline(pipeline, dry_run=True)

    _report(
        "step 0 COMPLETED",
        result.steps[0].status == StepStatus.COMPLETED,
        f"got {result.steps[0].status.value}",
    )
    _report(
        "step 1 now READY",
        result.steps[1].status == StepStatus.READY,
        f"got {result.steps[1].status.value}",
    )
    _report(
        "current_step_index advanced to 1",
        result.current_step_index == 1,
        f"got {result.current_step_index}",
    )
    _report(
        "pipeline still IN_PROGRESS",
        result.status == PipelineStatus.IN_PROGRESS,
        f"got {result.status.value}",
    )


# ─── Test 3: advance_all pushes all steps ───────────────────────────────────


def test_pipeline_advance_all() -> None:
    print("\n── Test 3: advance_all pushes all steps to completion ──")

    _reset_all()

    task = create_task("write outreach email copy")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    result = execute_pipeline(pipeline, dry_run=True, advance_all=True)

    _report(
        "pipeline COMPLETED",
        result.status == PipelineStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "3 steps (product template)",
        len(result.steps) == 3,
        f"got {len(result.steps)}",
    )
    _report(
        "all steps completed",
        all(s.status == StepStatus.COMPLETED for s in result.steps),
    )


# ─── Test 4: pipeline blocked on operator ────────────────────────────────────


def test_pipeline_blocked_on_operator() -> None:
    print("\n── Test 4: operator block pauses pipeline at step N ──")

    _reset_all()

    task = create_task("deploy the new code")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Manually set step 1 to simulate a human block result
    # First, advance step 0 via dry_run
    execute_pipeline(pipeline, dry_run=True)  # step 0 → COMPLETED

    # Now manually mark step 1 as WAITING_ON_OPERATOR
    step1 = pipeline.steps[1]
    step1.status = StepStatus.WAITING_ON_OPERATOR
    step1.requires_input_prompt = "Step paused: need approval"
    PipelineStore.default().put(pipeline)

    # Execute should detect the waiting step and propagate
    result = execute_pipeline(pipeline, dry_run=True)

    _report(
        "pipeline WAITING_ON_OPERATOR",
        result.status == PipelineStatus.WAITING_ON_OPERATOR,
        f"got {result.status.value}",
    )
    _report(
        "current_step_index at 1",
        result.current_step_index == 1,
        f"got {result.current_step_index}",
    )
    _report(
        "blocked step has prompt",
        result.steps[1].requires_input_prompt is not None,
        f"got {result.steps[1].requires_input_prompt}",
    )


# ─── Test 5: failed step retry ──────────────────────────────────────────────


def test_failed_step_retry() -> None:
    print("\n── Test 5: retry_step resets failed step and re-executes ──")

    _reset_all()

    task = create_task("fix the code migration")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Advance step 0
    execute_pipeline(pipeline, dry_run=True)

    # Manually mark step 1 as FAILED
    step1 = pipeline.steps[1]
    step1.status = StepStatus.FAILED
    step1.execution_error = "timeout"
    step1.retry_count = 0
    pipeline.status = PipelineStatus.PAUSED
    PipelineStore.default().put(pipeline)

    # Retry step 1
    result = retry_step(
        pipeline.pipeline_id,
        step1.step_id,
        dry_run=True,
    )

    _report(
        "step 1 now COMPLETED (after retry)",
        result.steps[1].status == StepStatus.COMPLETED,
        f"got {result.steps[1].status.value}",
    )
    _report(
        "pipeline not PAUSED anymore",
        result.status != PipelineStatus.PAUSED,
        f"got {result.status.value}",
    )
    _report(
        "step 1 execution_error cleared",
        result.steps[1].execution_error is None,
    )


# ─── Test 6: resume pipeline from step ──────────────────────────────────────


def test_resume_pipeline_from_step() -> None:
    print("\n── Test 6: resume skips completed steps ──")

    _reset_all()

    task = create_task("patch the test suite")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Complete step 0 and 1 via dry_run step-by-step
    execute_pipeline(pipeline, dry_run=True)  # step 0
    execute_pipeline(pipeline, dry_run=True)  # step 1

    _report(
        "step 0 COMPLETED before resume",
        pipeline.steps[0].status == StepStatus.COMPLETED,
    )
    _report(
        "step 1 COMPLETED before resume",
        pipeline.steps[1].status == StepStatus.COMPLETED,
    )

    # Mark step 2 as FAILED to simulate pause
    step2 = pipeline.steps[2]
    step2.status = StepStatus.FAILED
    step2.execution_error = "transient"
    pipeline.status = PipelineStatus.PAUSED
    PipelineStore.default().put(pipeline)

    # Resume — should NOT rerun steps 0 and 1
    result = resume_pipeline(
        pipeline.pipeline_id,
        dry_run=True,
        advance_all=True,
    )

    _report(
        "step 0 still COMPLETED (not rerun)",
        result.steps[0].status == StepStatus.COMPLETED,
    )
    _report(
        "step 1 still COMPLETED (not rerun)",
        result.steps[1].status == StepStatus.COMPLETED,
    )
    _report(
        "step 2 now COMPLETED (after resume)",
        result.steps[2].status == StepStatus.COMPLETED,
        f"got {result.steps[2].status.value}",
    )


# ─── Test 7: overnight pipelines in priority order ──────────────────────────


def test_overnight_pipelines_priority() -> None:
    print("\n── Test 7: overnight advances multiple pipelines in priority order ──")

    _reset_all()

    # Create tasks with different priorities
    t_low = create_task("sync CRM data")
    t_low.priority = 25
    t_low.status = TaskStatus.OVERNIGHT_QUEUED
    TaskStore.default().put(t_low)

    t_high = create_task("urgent security patch for code")
    t_high.priority = 100
    t_high.status = TaskStatus.OVERNIGHT_QUEUED
    TaskStore.default().put(t_high)

    t_mid = create_task("generate weekly summary report")
    t_mid.priority = 50
    t_mid.status = TaskStatus.OVERNIGHT_QUEUED
    TaskStore.default().put(t_mid)

    # Execute via the overnight path
    from eos_ai.substrate.task_execution import run_overnight_execution

    result = run_overnight_execution(dry_run=True)

    _report(
        "3 tasks executed",
        result["executed"] == 3,
        f"got {result['executed']}",
    )
    _report(
        "3 completed",
        result["completed"] == 3,
        f"got {result['completed']}",
    )

    # All tasks should now have pipelines
    for t in [t_low, t_high, t_mid]:
        reloaded = TaskStore.default().get(t.task_id)
        _report(
            f"task {t.task_id[:12]} has pipeline_id",
            reloaded is not None and reloaded.pipeline_id is not None,
            f"got {reloaded.pipeline_id if reloaded else 'None'}",
        )

    # Priority ordering
    ids = [tr["task_id"] for tr in result["task_results"]]
    _report(
        "highest priority first",
        ids[0] == t_high.task_id,
        f"expected {t_high.task_id}, got {ids[0]}",
    )


# ─── Test 8: completed steps not rerun on resume ────────────────────────────


def test_completed_steps_not_rerun() -> None:
    print("\n── Test 8: completed steps NOT rerun on resume ──")

    _reset_all()

    task = create_task("debug the module imports")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Complete all steps
    execute_pipeline(pipeline, dry_run=True, advance_all=True)

    # Record step results
    step0_result = pipeline.steps[0].execution_result
    step0_finished = pipeline.steps[0].execution_finished_at

    # Attempt resume on completed pipeline
    result = execute_pipeline(pipeline, dry_run=True, advance_all=True)

    _report(
        "pipeline still COMPLETED",
        result.status == PipelineStatus.COMPLETED,
        f"got {result.status.value}",
    )
    _report(
        "step 0 result unchanged",
        result.steps[0].execution_result == step0_result,
    )
    _report(
        "step 0 finished_at unchanged",
        result.steps[0].execution_finished_at == step0_finished,
    )


# ─── Test 9: persistence survives restart ────────────────────────────────────


def test_persistence_survives_restart() -> None:
    print("\n── Test 9: pipeline persists across singleton reset ──")

    _reset_all()

    task = create_task("build the data pipeline")
    pipeline = decompose_task(task)
    PipelineStore.default().put(pipeline)

    # Execute step 0
    execute_pipeline(pipeline, dry_run=True)

    pid = pipeline.pipeline_id

    # Reset singletons
    PipelineStore.reset_default_for_tests()
    TaskStore.reset_default_for_tests()

    # Reload
    reloaded = PipelineStore.default().get(pid)
    _report("pipeline reloads", reloaded is not None)
    if reloaded:
        _report(
            "step 0 still COMPLETED",
            reloaded.steps[0].status == StepStatus.COMPLETED,
            f"got {reloaded.steps[0].status.value}",
        )
        _report(
            "step 1 is READY",
            reloaded.steps[1].status == StepStatus.READY,
            f"got {reloaded.steps[1].status.value}",
        )
        _report(
            "current_step_index is 1",
            reloaded.current_step_index == 1,
            f"got {reloaded.current_step_index}",
        )


# ─── Test 10: task ↔ pipeline integration ───────────────────────────────────


def test_task_pipeline_integration() -> None:
    print("\n── Test 10: task.pipeline_id set after pipeline execution ──")

    _reset_all()

    task = create_task("deploy the new API endpoint")
    session = OperatorSession.new()
    session.node_preference = "vps"

    result = execute_task(task, session, dry_run=True)

    _report(
        "task has pipeline_id",
        result.pipeline_id is not None,
        f"got {result.pipeline_id}",
    )
    _report(
        "task has agent_owner",
        result.agent_owner is not None,
        f"got {result.agent_owner}",
    )
    _report(
        "task status is COMPLETED",
        result.status == TaskStatus.COMPLETED,
        f"got {result.status.value}",
    )

    # Verify pipeline exists in store
    if result.pipeline_id:
        pipe = PipelineStore.default().get(result.pipeline_id)
        _report(
            "pipeline exists in store",
            pipe is not None,
        )
        if pipe:
            _report(
                "pipeline.task_id matches",
                pipe.task_id == result.task_id,
            )


# ─── Test 11: pipeline summary ──────────────────────────────────────────────


def test_pipeline_summary() -> None:
    print("\n── Test 11: get_pipeline_summary returns counts ──")

    _reset_all()

    # Create and complete one pipeline
    t1 = create_task("fix the test suite")
    p1 = decompose_task(t1)
    PipelineStore.default().put(p1)
    execute_pipeline(p1, dry_run=True, advance_all=True)

    # Create a waiting pipeline
    t2 = create_task("write the summary report")
    p2 = decompose_task(t2)
    p2.status = PipelineStatus.WAITING_ON_OPERATOR
    p2.steps[0].requires_input_prompt = "Need approval"
    PipelineStore.default().put(p2)

    summary = get_pipeline_summary()

    _report(
        "completed_pipelines >= 1",
        summary["completed_pipelines"] >= 1,
        f"got {summary['completed_pipelines']}",
    )
    _report(
        "waiting_on_operator >= 1",
        summary["waiting_on_operator"] >= 1,
        f"got {summary['waiting_on_operator']}",
    )
    _report(
        "top_blocked_prompt set",
        summary["top_blocked_prompt"] is not None,
        f"got {summary['top_blocked_prompt']}",
    )


# ─── Test 12: format_blocked_summary ────────────────────────────────────────


def test_format_blocked_summary() -> None:
    print("\n── Test 12: format_blocked_summary output ──")

    steps = [
        PipelineStep.new(
            "Deploy",
            0,
            PipelineAgentRole.BUILDER,
            status=StepStatus.WAITING_ON_OPERATOR,
        ),
    ]
    steps[0].requires_input_prompt = "Need operator approval"

    pipeline = TaskPipeline.new(
        task_id="task_fmt1",
        title="Deploy to production",
        agent_owner=PipelineAgentRole.BUILDER,
        steps=steps,
        priority=100,
    )

    output = format_blocked_summary(pipeline)

    _report("contains title", "Deploy to production" in output)
    _report("contains blocked step", "Deploy" in output)
    _report("contains prompt", "operator approval" in output)
    _report("contains priority", "100" in output)


# ─── Test 13: format_pipeline_summary ────────────────────────────────────────


def test_format_pipeline_summary() -> None:
    print("\n── Test 13: format_pipeline_summary output ──")

    steps = [
        PipelineStep.new(
            "A", 0, PipelineAgentRole.GENERAL, status=StepStatus.COMPLETED
        ),
        PipelineStep.new("B", 1, PipelineAgentRole.GENERAL, status=StepStatus.READY),
        PipelineStep.new("C", 2, PipelineAgentRole.GENERAL),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_fmt2",
        title="Process data",
        agent_owner=PipelineAgentRole.GENERAL,
        steps=steps,
    )
    pipeline.status = PipelineStatus.IN_PROGRESS
    pipeline.current_step_index = 1

    output = format_pipeline_summary(pipeline)

    _report("contains title", "Process data" in output)
    _report("contains status", "in_progress" in output)
    _report("contains progress", "1/3" in output)
    _report("contains current step", "B" in output)


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Pipeline Execution Smoke Tests")
    print("=" * 60)

    test_pipeline_dry_run_completes()
    test_pipeline_step_by_step()
    test_pipeline_advance_all()
    test_pipeline_blocked_on_operator()
    test_failed_step_retry()
    test_resume_pipeline_from_step()
    test_overnight_pipelines_priority()
    test_completed_steps_not_rerun()
    test_persistence_survives_restart()
    test_task_pipeline_integration()
    test_pipeline_summary()
    test_format_blocked_summary()
    test_format_pipeline_summary()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
