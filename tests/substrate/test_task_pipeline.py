"""Smoke tests for eos_ai.substrate.task_pipeline.

Validates:
  1.  test_pipeline_step_create         — PipelineStep.new() creates with correct defaults
  2.  test_pipeline_step_serialization  — to_dict/from_dict roundtrip
  3.  test_task_pipeline_create         — TaskPipeline.new() creates with correct defaults
  4.  test_task_pipeline_serialization  — to_dict/from_dict roundtrip with nested steps
  5.  test_pipeline_store_put_get       — PipelineStore put and get by ID
  6.  test_pipeline_store_get_by_task   — PipelineStore get_by_task_id
  7.  test_pipeline_store_persistence   — survives singleton reset
  8.  test_current_step                 — current_step returns correct step at index
  9.  test_completed_steps              — completed_steps filters correctly
 10.  test_is_terminal                  — terminal state detection

Run directly:
    python3 tests/substrate/test_task_pipeline.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.task_pipeline import (  # noqa: E402
    PipelineAgentRole,
    PipelineStatus,
    PipelineStep,
    PipelineStore,
    StepStatus,
    TaskPipeline,
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

        get_storage().put("task_pipelines", None)
    except Exception:
        pass
    PipelineStore.reset_default_for_tests()


# ─── Test 1: PipelineStep creation ──────────────────────────────────────────


def test_pipeline_step_create() -> None:
    print("\n── Test 1: PipelineStep.new() creates with correct defaults ──")

    step = PipelineStep.new(
        "Analyze task",
        step_index=0,
        agent_role=PipelineAgentRole.BUILDER,
        description="Read files and understand scope.",
        status=StepStatus.READY,
    )

    _report(
        "step_id starts with step_",
        step.step_id.startswith("step_"),
        f"got {step.step_id!r}",
    )
    _report("title correct", step.title == "Analyze task")
    _report("step_index is 0", step.step_index == 0)
    _report("status is READY", step.status == StepStatus.READY)
    _report(
        "agent_role is BUILDER",
        step.agent_role == PipelineAgentRole.BUILDER,
    )
    _report("retry_count is 0", step.retry_count == 0)
    _report("updated_at set", step.updated_at != "")


# ─── Test 2: PipelineStep serialization ─────────────────────────────────────


def test_pipeline_step_serialization() -> None:
    print("\n── Test 2: PipelineStep to_dict/from_dict roundtrip ──")

    original = PipelineStep.new(
        "Execute change",
        step_index=1,
        agent_role=PipelineAgentRole.PRODUCT,
        description="Implement the change.",
    )
    original.execution_result = "done"
    original.retry_count = 1

    d = original.to_dict()
    restored = PipelineStep.from_dict(d)

    _report("step_id matches", restored.step_id == original.step_id)
    _report("title matches", restored.title == original.title)
    _report(
        "agent_role matches",
        restored.agent_role == original.agent_role,
    )
    _report("status matches", restored.status == original.status)
    _report(
        "execution_result matches",
        restored.execution_result == original.execution_result,
    )
    _report(
        "retry_count matches",
        restored.retry_count == original.retry_count,
    )


# ─── Test 3: TaskPipeline creation ──────────────────────────────────────────


def test_task_pipeline_create() -> None:
    print("\n── Test 3: TaskPipeline.new() creates with correct defaults ──")

    steps = [
        PipelineStep.new(
            "Step 0", 0, PipelineAgentRole.BUILDER, status=StepStatus.READY
        ),
        PipelineStep.new("Step 1", 1, PipelineAgentRole.BUILDER),
    ]

    pipeline = TaskPipeline.new(
        task_id="task_abc123",
        title="Build the module",
        agent_owner=PipelineAgentRole.BUILDER,
        steps=steps,
        priority=75,
    )

    _report(
        "pipeline_id starts with pipe_",
        pipeline.pipeline_id.startswith("pipe_"),
        f"got {pipeline.pipeline_id!r}",
    )
    _report("task_id correct", pipeline.task_id == "task_abc123")
    _report("status is READY", pipeline.status == PipelineStatus.READY)
    _report("2 steps", len(pipeline.steps) == 2)
    _report("current_step_index is 0", pipeline.current_step_index == 0)
    _report(
        "agent_owner is BUILDER",
        pipeline.agent_owner == PipelineAgentRole.BUILDER,
    )
    _report("priority is 75", pipeline.priority == 75)


# ─── Test 4: TaskPipeline serialization ─────────────────────────────────────


def test_task_pipeline_serialization() -> None:
    print("\n── Test 4: TaskPipeline to_dict/from_dict roundtrip ──")

    steps = [
        PipelineStep.new("Step 0", 0, PipelineAgentRole.CEO, status=StepStatus.READY),
        PipelineStep.new("Step 1", 1, PipelineAgentRole.CEO),
        PipelineStep.new("Step 2", 2, PipelineAgentRole.CEO),
    ]

    original = TaskPipeline.new(
        task_id="task_xyz789",
        title="Strategy review",
        agent_owner=PipelineAgentRole.CEO,
        steps=steps,
        day_session_id="ds_session1",
    )
    original.summary = "In progress"

    d = original.to_dict()
    restored = TaskPipeline.from_dict(d)

    _report("pipeline_id matches", restored.pipeline_id == original.pipeline_id)
    _report("task_id matches", restored.task_id == original.task_id)
    _report("title matches", restored.title == original.title)
    _report("status matches", restored.status == original.status)
    _report(
        "agent_owner matches",
        restored.agent_owner == original.agent_owner,
    )
    _report("3 steps restored", len(restored.steps) == 3)
    _report(
        "step 0 status is READY",
        restored.steps[0].status == StepStatus.READY,
    )
    _report(
        "step 1 status is PENDING",
        restored.steps[1].status == StepStatus.PENDING,
    )
    _report("summary matches", restored.summary == original.summary)
    _report(
        "day_session_id matches",
        restored.day_session_id == original.day_session_id,
    )


# ─── Test 5: PipelineStore put/get ──────────────────────────────────────────


def test_pipeline_store_put_get() -> None:
    print("\n── Test 5: PipelineStore put and get by ID ──")

    _reset_all()

    steps = [
        PipelineStep.new(
            "Step 0", 0, PipelineAgentRole.GENERAL, status=StepStatus.READY
        ),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_store1",
        title="Store test",
        agent_owner=PipelineAgentRole.GENERAL,
        steps=steps,
    )

    store = PipelineStore.default()
    store.put(pipeline)

    loaded = store.get(pipeline.pipeline_id)
    _report("loaded is not None", loaded is not None)
    if loaded:
        _report("pipeline_id matches", loaded.pipeline_id == pipeline.pipeline_id)
        _report("title matches", loaded.title == pipeline.title)

    # all() returns the pipeline
    all_pipelines = store.all()
    _report("all() contains 1", len(all_pipelines) == 1)


# ─── Test 6: PipelineStore get_by_task_id ────────────────────────────────────


def test_pipeline_store_get_by_task() -> None:
    print("\n── Test 6: PipelineStore get_by_task_id ──")

    _reset_all()

    steps = [
        PipelineStep.new(
            "Step 0", 0, PipelineAgentRole.BUILDER, status=StepStatus.READY
        ),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_lookup1",
        title="Lookup test",
        agent_owner=PipelineAgentRole.BUILDER,
        steps=steps,
    )

    store = PipelineStore.default()
    store.put(pipeline)

    found = store.get_by_task_id("task_lookup1")
    _report("found by task_id", found is not None)
    if found:
        _report(
            "pipeline_id matches",
            found.pipeline_id == pipeline.pipeline_id,
        )

    not_found = store.get_by_task_id("task_nonexistent")
    _report("None for unknown task_id", not_found is None)


# ─── Test 7: PipelineStore persistence ───────────────────────────────────────


def test_pipeline_store_persistence() -> None:
    print("\n── Test 7: Pipeline persists across singleton reset ──")

    _reset_all()

    steps = [
        PipelineStep.new(
            "Step 0", 0, PipelineAgentRole.PRODUCT, status=StepStatus.READY
        ),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_persist1",
        title="Persistence test",
        agent_owner=PipelineAgentRole.PRODUCT,
        steps=steps,
    )

    PipelineStore.default().put(pipeline)
    pid = pipeline.pipeline_id

    # Reset singleton — forces reload from storage
    PipelineStore.reset_default_for_tests()

    reloaded = PipelineStore.default().get(pid)
    _report("pipeline reloads", reloaded is not None)
    if reloaded:
        _report("title survives", reloaded.title == "Persistence test")
        _report(
            "agent_owner survives",
            reloaded.agent_owner == PipelineAgentRole.PRODUCT,
        )
        _report("1 step survives", len(reloaded.steps) == 1)


# ─── Test 8: current_step ───────────────────────────────────────────────────


def test_current_step() -> None:
    print("\n── Test 8: current_step returns correct step ──")

    steps = [
        PipelineStep.new(
            "Step 0", 0, PipelineAgentRole.BUILDER, status=StepStatus.COMPLETED
        ),
        PipelineStep.new(
            "Step 1", 1, PipelineAgentRole.BUILDER, status=StepStatus.READY
        ),
        PipelineStep.new("Step 2", 2, PipelineAgentRole.BUILDER),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_cs1",
        title="Current step test",
        agent_owner=PipelineAgentRole.BUILDER,
        steps=steps,
    )
    pipeline.current_step_index = 1

    current = pipeline.current_step()
    _report("current_step is not None", current is not None)
    if current:
        _report("step_index is 1", current.step_index == 1)
        _report("title is Step 1", current.title == "Step 1")

    # Out of bounds
    pipeline.current_step_index = 99
    _report("out of bounds returns None", pipeline.current_step() is None)


# ─── Test 9: completed_steps ────────────────────────────────────────────────


def test_completed_steps() -> None:
    print("\n── Test 9: completed_steps filters correctly ──")

    steps = [
        PipelineStep.new(
            "A", 0, PipelineAgentRole.GENERAL, status=StepStatus.COMPLETED
        ),
        PipelineStep.new("B", 1, PipelineAgentRole.GENERAL, status=StepStatus.READY),
        PipelineStep.new(
            "C", 2, PipelineAgentRole.GENERAL, status=StepStatus.COMPLETED
        ),
    ]
    pipeline = TaskPipeline.new(
        task_id="task_comp1",
        title="Completed test",
        agent_owner=PipelineAgentRole.GENERAL,
        steps=steps,
    )

    completed = pipeline.completed_steps()
    _report("2 completed steps", len(completed) == 2, f"got {len(completed)}")


# ─── Test 10: is_terminal ───────────────────────────────────────────────────


def test_is_terminal() -> None:
    print("\n── Test 10: is_terminal detection ──")

    pipeline = TaskPipeline.new(
        task_id="task_term1",
        title="Terminal test",
        agent_owner=PipelineAgentRole.GENERAL,
        steps=[],
    )

    pipeline.status = PipelineStatus.COMPLETED
    _report("COMPLETED is terminal", pipeline.is_terminal())

    pipeline.status = PipelineStatus.FAILED
    _report("FAILED is terminal", pipeline.is_terminal())

    pipeline.status = PipelineStatus.IN_PROGRESS
    _report("IN_PROGRESS is not terminal", not pipeline.is_terminal())

    pipeline.status = PipelineStatus.WAITING_ON_OPERATOR
    _report("WAITING_ON_OPERATOR is not terminal", not pipeline.is_terminal())


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Task Pipeline Smoke Tests")
    print("=" * 60)

    test_pipeline_step_create()
    test_pipeline_step_serialization()
    test_task_pipeline_create()
    test_task_pipeline_serialization()
    test_pipeline_store_put_get()
    test_pipeline_store_get_by_task()
    test_pipeline_store_persistence()
    test_current_step()
    test_completed_steps()
    test_is_terminal()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
