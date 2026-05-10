"""Smoke tests for eos_ai.substrate.capability_routing.

Validates:
  1.  test_builder_context_keywords    — builder keywords → BUILDER_CONTEXT
  2.  test_product_context_default     — non-builder text → PRODUCT_CONTEXT
  3.  test_heavy_compute_keywords      — heavy keywords → LOCAL_COMPUTE + HEAVY_REASONING
  4.  test_lightweight_default         — default → LIGHTWEIGHT_REASONING
  5.  test_vps_eligible_autonomous     — autonomous + lightweight → VPS_COMPUTE
  6.  test_target_vps_builder          — builder context + vps pref → VPS_BUILDER
  7.  test_target_local_builder        — builder + local pref + local up → LOCAL_BUILDER
  8.  test_target_vps_product          — product context → VPS_PRODUCT
  9.  test_target_local_heavy          — heavy compute + local up → LOCAL target
 10.  test_route_task_attaches_metadata — route_task populates all routing fields
 11.  test_routing_without_session     — route_task works with session=None

Run directly:
    python3 tests/substrate/test_capability_routing.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.capability_routing import (  # noqa: E402
    ExecutionTarget,
    TaskCapability,
    choose_execution_target,
    infer_task_capabilities,
    route_task,
)
from eos_ai.substrate.operator_session import (  # noqa: E402
    OperatorSession,
    OperatorSessionStore,
)
from eos_ai.substrate.task_system import (  # noqa: E402
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
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
    except Exception:
        pass
    TaskStore.reset_default_for_tests()
    OperatorSessionStore.reset_default_for_tests()


def _make_task(title: str, policy: str = "autonomous") -> Task:
    return Task.new(
        title=title,
        execution_policy=TaskExecutionPolicy(policy),
        status=TaskStatus.READY,
    )


# ─── Test 1: builder context keywords ──────────────────────────────────────


def test_builder_context_keywords() -> None:
    print("\n── Test 1: builder keywords → BUILDER_CONTEXT ──")

    cases = [
        "fix the login bug in the code",
        "deploy the new service",
        "debug the tmux script",
        "refactor the API endpoint",
        "build the new module",
    ]
    for text in cases:
        task = _make_task(text)
        caps = infer_task_capabilities(task)
        _report(
            f"'{text}' → BUILDER_CONTEXT",
            TaskCapability.BUILDER_CONTEXT in caps,
            f"got {[c.value for c in caps]}",
        )


# ─── Test 2: product context default ───────────────────────────────────────


def test_product_context_default() -> None:
    print("\n── Test 2: non-builder text → PRODUCT_CONTEXT ──")

    cases = [
        "send the weekly report to clients",
        "summarize the meeting notes",
        "create a proposal for the new project",
        "analyze the sales data",
    ]
    for text in cases:
        task = _make_task(text)
        caps = infer_task_capabilities(task)
        _report(
            f"'{text}' → PRODUCT_CONTEXT",
            TaskCapability.PRODUCT_CONTEXT in caps,
            f"got {[c.value for c in caps]}",
        )


# ─── Test 3: heavy compute keywords ────────────────────────────────────────


def test_heavy_compute_keywords() -> None:
    print("\n── Test 3: heavy keywords → LOCAL_COMPUTE + HEAVY_REASONING ──")

    cases = [
        "train the local model on new data",
        "compile the GPU-optimized binary",
        "run the heavy embedding generation",
    ]
    for text in cases:
        task = _make_task(text)
        caps = infer_task_capabilities(task)
        _report(
            f"'{text}' has LOCAL_COMPUTE",
            TaskCapability.LOCAL_COMPUTE in caps,
            f"got {[c.value for c in caps]}",
        )
        _report(
            f"'{text}' has HEAVY_REASONING",
            TaskCapability.HEAVY_REASONING in caps,
            f"got {[c.value for c in caps]}",
        )


# ─── Test 4: lightweight default ───────────────────────────────────────────


def test_lightweight_default() -> None:
    print("\n── Test 4: default → LIGHTWEIGHT_REASONING ──")

    task = _make_task("send the daily summary email")
    caps = infer_task_capabilities(task)
    _report(
        "lightweight task → LIGHTWEIGHT_REASONING",
        TaskCapability.LIGHTWEIGHT_REASONING in caps,
        f"got {[c.value for c in caps]}",
    )
    _report(
        "no LOCAL_COMPUTE",
        TaskCapability.LOCAL_COMPUTE not in caps,
    )


# ─── Test 5: VPS eligible for autonomous ───────────────────────────────────


def test_vps_eligible_autonomous() -> None:
    print("\n── Test 5: autonomous + lightweight → VPS_COMPUTE ──")

    task = _make_task("generate the report", "autonomous")
    caps = infer_task_capabilities(task)
    _report(
        "VPS_COMPUTE present",
        TaskCapability.VPS_COMPUTE in caps,
        f"got {[c.value for c in caps]}",
    )

    # Non-autonomous should NOT get VPS_COMPUTE
    task2 = _make_task("generate the report", "needs_operator")
    caps2 = infer_task_capabilities(task2)
    _report(
        "non-autonomous → no VPS_COMPUTE",
        TaskCapability.VPS_COMPUTE not in caps2,
        f"got {[c.value for c in caps2]}",
    )


# ─── Test 6: target VPS_BUILDER ────────────────────────────────────────────


def test_target_vps_builder() -> None:
    print("\n── Test 6: builder context + vps pref → VPS_BUILDER ──")

    task = _make_task("fix the broken test in the repo")
    session = OperatorSession.new()
    session.node_preference = "vps"

    target = choose_execution_target(task, session, local_available=False)
    _report(
        "target is VPS_BUILDER",
        target == ExecutionTarget.VPS_BUILDER,
        f"got {target.value}",
    )


# ─── Test 7: target LOCAL_BUILDER ──────────────────────────────────────────


def test_target_local_builder() -> None:
    print("\n── Test 7: builder + local pref + local up → LOCAL_BUILDER ──")

    task = _make_task("compile the local build script")
    session = OperatorSession.new()
    session.node_preference = "local"

    target = choose_execution_target(task, session, local_available=True)
    _report(
        "target is LOCAL_BUILDER",
        target == ExecutionTarget.LOCAL_BUILDER,
        f"got {target.value}",
    )


# ─── Test 8: target VPS_PRODUCT ────────────────────────────────────────────


def test_target_vps_product() -> None:
    print("\n── Test 8: product context → VPS_PRODUCT ──")

    task = _make_task("send weekly digest to clients")
    session = OperatorSession.new()
    session.node_preference = "auto"

    target = choose_execution_target(task, session, local_available=False)
    _report(
        "target is VPS_PRODUCT",
        target == ExecutionTarget.VPS_PRODUCT,
        f"got {target.value}",
    )


# ─── Test 9: target local for heavy compute ────────────────────────────────


def test_target_local_heavy() -> None:
    print("\n── Test 9: heavy compute + local up → LOCAL target ──")

    task = _make_task("train the model with GPU")
    session = OperatorSession.new()
    session.node_preference = "auto"

    target = choose_execution_target(task, session, local_available=True)
    _report(
        "target is local (builder or product)",
        target in (ExecutionTarget.LOCAL_BUILDER, ExecutionTarget.LOCAL_PRODUCT),
        f"got {target.value}",
    )

    # Without local available, should fall back to VPS
    target2 = choose_execution_target(task, session, local_available=False)
    _report(
        "no local → VPS fallback",
        target2 in (ExecutionTarget.VPS_BUILDER, ExecutionTarget.VPS_PRODUCT),
        f"got {target2.value}",
    )


# ─── Test 10: route_task attaches metadata ─────────────────────────────────


def test_route_task_attaches_metadata() -> None:
    print("\n── Test 10: route_task populates all routing fields ──")

    _reset_all()

    task = _make_task("debug the failing test")
    session = OperatorSession.new()
    session.node_preference = "vps"

    route_task(task, session, local_available=False)

    _report(
        "required_capabilities populated",
        len(task.required_capabilities) > 0,
        f"got {task.required_capabilities}",
    )
    _report(
        "chosen_target set",
        task.chosen_target is not None,
        f"got {task.chosen_target}",
    )
    _report(
        "routing_reason set",
        task.routing_reason is not None and len(task.routing_reason) > 0,
        f"got {task.routing_reason}",
    )


# ─── Test 11: routing without session ──────────────────────────────────────


def test_routing_without_session() -> None:
    print("\n── Test 11: route_task works with session=None ──")

    _reset_all()

    task = _make_task("send the daily report")
    route_task(task, session=None, local_available=False)

    _report(
        "chosen_target set without session",
        task.chosen_target is not None,
        f"got {task.chosen_target}",
    )
    _report(
        "routing_reason mentions node_pref=auto",
        task.routing_reason is not None and "node_pref=auto" in task.routing_reason,
        f"got {task.routing_reason}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Capability Routing Smoke Tests")
    print("=" * 60)

    test_builder_context_keywords()
    test_product_context_default()
    test_heavy_compute_keywords()
    test_lightweight_default()
    test_vps_eligible_autonomous()
    test_target_vps_builder()
    test_target_local_builder()
    test_target_vps_product()
    test_target_local_heavy()
    test_route_task_attaches_metadata()
    test_routing_without_session()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
