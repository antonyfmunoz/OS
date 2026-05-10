"""Smoke tests for eos_ai.substrate.task_decomposition.

Validates:
  1.  test_infer_builder_role       — builder keywords → BUILDER
  2.  test_infer_portfolio_role     — portfolio keywords → PORTFOLIO
  3.  test_infer_ceo_role           — ceo/strategy keywords → CEO
  4.  test_infer_product_role       — product/content keywords → PRODUCT
  5.  test_infer_general_role       — no keywords → GENERAL
  6.  test_decompose_builder_task   — builder task → 4 steps
  7.  test_decompose_product_task   — product task → 3 steps
  8.  test_decompose_ceo_task       — ceo task → 3 steps
  9.  test_step_zero_is_ready       — first step starts as READY
 10.  test_subsequent_steps_pending — later steps start as PENDING
 11.  test_pipeline_links_to_task   — pipeline.task_id matches task.task_id

Run directly:
    python3 tests/substrate/test_task_decomposition.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.task_decomposition import (  # noqa: E402
    decompose_task,
    infer_agent_role,
)
from eos_ai.substrate.task_pipeline import (  # noqa: E402
    PipelineAgentRole,
    PipelineStatus,
    PipelineStore,
    StepStatus,
)
from eos_ai.substrate.task_system import (  # noqa: E402
    Task,
    TaskStore,
    create_task,
)
from eos_ai.substrate.operator_session import OperatorSessionStore  # noqa: E402
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402

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


# ─── Test 1: builder role inference ──────────────────────────────────────────


def test_infer_builder_role() -> None:
    print("\n── Test 1: builder keywords → BUILDER ──")

    _reset_all()

    cases = [
        "fix the deployment script",
        "debug the API endpoint",
        "build the new module",
        "patch the test suite",
        "refactor the schema migration",
    ]
    for text in cases:
        task = create_task(text)
        role = infer_agent_role(task)
        _report(
            f"'{text}' → BUILDER",
            role == PipelineAgentRole.BUILDER,
            f"got {role.value}",
        )


# ─── Test 2: portfolio role inference ────────────────────────────────────────


def test_infer_portfolio_role() -> None:
    print("\n── Test 2: portfolio keywords → PORTFOLIO ──")

    _reset_all()

    cases = [
        "review portfolio allocation",
        "analyze investment returns",
        "update the watchlist with new risk metrics",
    ]
    for text in cases:
        task = create_task(text)
        role = infer_agent_role(task)
        _report(
            f"'{text}' → PORTFOLIO",
            role == PipelineAgentRole.PORTFOLIO,
            f"got {role.value}",
        )


# ─── Test 3: ceo role inference ──────────────────────────────────────────────


def test_infer_ceo_role() -> None:
    print("\n── Test 3: ceo/strategy keywords → CEO ──")

    _reset_all()

    cases = [
        "update company priorities for Q2",
        "revenue growth strategy",
        "evaluate the new business direction",
    ]
    for text in cases:
        task = create_task(text)
        role = infer_agent_role(task)
        _report(
            f"'{text}' → CEO",
            role == PipelineAgentRole.CEO,
            f"got {role.value}",
        )


# ─── Test 4: product role inference ──────────────────────────────────────────


def test_infer_product_role() -> None:
    print("\n── Test 4: product/content keywords → PRODUCT ──")

    _reset_all()

    cases = [
        "write outreach email copy",
        "launch the new campaign",
        "research the target audience",
    ]
    for text in cases:
        task = create_task(text)
        role = infer_agent_role(task)
        _report(
            f"'{text}' → PRODUCT",
            role == PipelineAgentRole.PRODUCT,
            f"got {role.value}",
        )


# ─── Test 5: general role inference ──────────────────────────────────────────


def test_infer_general_role() -> None:
    print("\n── Test 5: no keywords → GENERAL ──")

    _reset_all()

    cases = [
        "send the weekly update",
        "schedule a meeting",
        "organize files",
    ]
    for text in cases:
        task = create_task(text)
        role = infer_agent_role(task)
        _report(
            f"'{text}' → GENERAL",
            role == PipelineAgentRole.GENERAL,
            f"got {role.value}",
        )


# ─── Test 6: decompose builder task ─────────────────────────────────────────


def test_decompose_builder_task() -> None:
    print("\n── Test 6: builder task → 4 steps ──")

    _reset_all()

    task = create_task("fix the broken API test")
    pipeline = decompose_task(task)

    _report("4 steps", len(pipeline.steps) == 4, f"got {len(pipeline.steps)}")
    _report(
        "agent_owner is BUILDER",
        pipeline.agent_owner == PipelineAgentRole.BUILDER,
    )
    _report(
        "step titles correct",
        pipeline.steps[0].title == "Analyze task"
        and pipeline.steps[1].title == "Execute change"
        and pipeline.steps[2].title == "Verify result"
        and pipeline.steps[3].title == "Summarize outcome",
        f"got {[s.title for s in pipeline.steps]}",
    )
    _report(
        "pipeline status is READY",
        pipeline.status == PipelineStatus.READY,
    )
    _report(
        "pipeline.task_id links to task",
        pipeline.task_id == task.task_id,
    )


# ─── Test 7: decompose product task ─────────────────────────────────────────


def test_decompose_product_task() -> None:
    print("\n── Test 7: product task → 3 steps ──")

    _reset_all()

    task = create_task("write outreach email copy")
    pipeline = decompose_task(task)

    _report("3 steps", len(pipeline.steps) == 3, f"got {len(pipeline.steps)}")
    _report(
        "agent_owner is PRODUCT",
        pipeline.agent_owner == PipelineAgentRole.PRODUCT,
    )
    _report(
        "step titles correct",
        pipeline.steps[0].title == "Analyze request"
        and pipeline.steps[1].title == "Produce output"
        and pipeline.steps[2].title == "Summarize outcome",
        f"got {[s.title for s in pipeline.steps]}",
    )


# ─── Test 8: decompose ceo task ─────────────────────────────────────────────


def test_decompose_ceo_task() -> None:
    print("\n── Test 8: ceo task → 3 steps ──")

    _reset_all()

    task = create_task("update company priorities for Q2")
    pipeline = decompose_task(task)

    _report("3 steps", len(pipeline.steps) == 3, f"got {len(pipeline.steps)}")
    _report(
        "agent_owner is CEO",
        pipeline.agent_owner == PipelineAgentRole.CEO,
    )
    _report(
        "step titles correct",
        pipeline.steps[0].title == "Analyze context"
        and pipeline.steps[1].title == "Generate recommendation"
        and pipeline.steps[2].title == "Summarize decision points",
        f"got {[s.title for s in pipeline.steps]}",
    )


# ─── Test 9: step 0 is READY ────────────────────────────────────────────────


def test_step_zero_is_ready() -> None:
    print("\n── Test 9: first step starts as READY ──")

    _reset_all()

    task = create_task("sync the data pipeline")
    pipeline = decompose_task(task)

    _report(
        "step 0 status is READY",
        pipeline.steps[0].status == StepStatus.READY,
        f"got {pipeline.steps[0].status.value}",
    )


# ─── Test 10: subsequent steps PENDING ───────────────────────────────────────


def test_subsequent_steps_pending() -> None:
    print("\n── Test 10: later steps start as PENDING ──")

    _reset_all()

    task = create_task("debug the test failures")
    pipeline = decompose_task(task)

    for step in pipeline.steps[1:]:
        _report(
            f"step {step.step_index} is PENDING",
            step.status == StepStatus.PENDING,
            f"got {step.status.value}",
        )


# ─── Test 11: pipeline links to task ────────────────────────────────────────


def test_pipeline_links_to_task() -> None:
    print("\n── Test 11: pipeline.task_id matches task.task_id ──")

    _reset_all()

    task = create_task("generate the summary report")
    pipeline = decompose_task(task)

    _report(
        "task_id matches",
        pipeline.task_id == task.task_id,
        f"pipeline={pipeline.task_id}, task={task.task_id}",
    )
    _report(
        "priority inherited",
        pipeline.priority == task.priority,
        f"pipeline={pipeline.priority}, task={task.priority}",
    )


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Task Decomposition Smoke Tests")
    print("=" * 60)

    test_infer_builder_role()
    test_infer_portfolio_role()
    test_infer_ceo_role()
    test_infer_product_role()
    test_infer_general_role()
    test_decompose_builder_task()
    test_decompose_product_task()
    test_decompose_ceo_task()
    test_step_zero_is_ready()
    test_subsequent_steps_pending()
    test_pipeline_links_to_task()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
