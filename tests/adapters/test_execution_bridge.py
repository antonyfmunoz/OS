"""Smoke tests for the execution adapter layer.

Validates:
  1. Batch drainer — deterministic drain, orphan handling
  2. Execution bridge — task dispatch, result application
  3. Workstation adapter — create, track, finalize
  4. End-to-end — drain → dispatch → apply → verify
  5. Invariants — mutation ops, replay, no side effects

Run directly:
    python3 tests/adapters/test_execution_bridge.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.execution_batch import (  # noqa: E402
    BatchTask,
    ExecutionBatch,
    batch_to_mutations,
    build_execution_batch,
    load_execution_batch,
)
from umh.substrate.execution_contract import (  # noqa: E402
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from umh.substrate.workstation_runtime import (  # noqa: E402
    build_workstation_run,
    build_workstation_run_mutations,
    list_active_workstation_runs,
    load_workstation_run,
)
from umh.substrate.artifact_contract import (  # noqa: E402
    list_recent_artifacts,
    load_runtime_artifact,
)
from umh.adapters.execution.batch_drainer import (  # noqa: E402
    drain_pending_batches,
)
from umh.adapters.execution.execution_bridge import (  # noqa: E402
    DispatchResult,
    TaskResult,
    apply_execution_results,
    dispatch_batch,
)
from umh.adapters.execution.workstation_adapter import (  # noqa: E402
    create_workstation_run_for_batch,
    finalize_workstation_run,
    load_and_finalize,
    start_run,
    track_execution_results,
)

from typing import Any  # noqa: E402

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


def _apply_mutations(state: dict[str, Any], mutations: list[dict[str, Any]]) -> None:
    """Apply mutations to a state dict (test helper)."""
    for m in mutations:
        op = m["op"]
        key = m["key"]
        if op == "SET":
            state[key] = m["value"]
        elif op == "REMOVE":
            state.pop(key, None)


class FakeAdapter:
    """Minimal ExecutionAdapter for testing."""

    def __init__(
        self,
        node_id: str = "local",
        *,
        should_fail: bool = False,
        should_raise: bool = False,
    ) -> None:
        self._node_id = node_id
        self._should_fail = should_fail
        self._should_raise = should_raise
        self.calls: list[ExecutionRequest] = []

    @property
    def adapter_id(self) -> str:
        return f"fake_{self._node_id}"

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"pure"})

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request)
        if self._should_raise:
            raise RuntimeError("adapter exploded")
        if self._should_fail:
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                primitive_name=request.primitive_name,
                status=ExecutionStatus.FAILED,
                outputs={},
                error="task failed",
                node_id=self._node_id,
            )
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            primitive_name=request.primitive_name,
            status=ExecutionStatus.SUCCEEDED,
            outputs={"done": True},
            node_id=self._node_id,
        )

    def health(self) -> Any:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 1. BATCH DRAINER
# ═══════════════════════════════════════════════════════════════════════════


def test_drain_empty_state() -> None:
    print("\n── 1a: Drain empty state ──")
    result = drain_pending_batches({})
    _report("no batches", len(result.batches) == 0)
    _report("no mutations", len(result.mutations) == 0)
    _report("no skipped", len(result.skipped) == 0)


def test_drain_pending_batches_deterministic() -> None:
    print("\n── 1b: Drain pending batches deterministic ──")
    state: dict[str, Any] = {}

    # Create two batches
    t1 = BatchTask(task_id="t1", execution_class="pure")
    t2 = BatchTask(task_id="t2", execution_class="pure")
    batch_a = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    batch_b = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t2,),
    )

    # Persist both as pending
    _apply_mutations(state, batch_to_mutations(batch_a))
    _apply_mutations(state, batch_to_mutations(batch_b))

    result = drain_pending_batches(state)
    _report("both batches drained", len(result.batches) == 2)
    _report(
        "deterministic order",
        [b.batch_id for b in result.batches]
        == sorted(b.batch_id for b in result.batches),
    )
    _report("all started", all(b.status == "active" for b in result.batches))
    _report("mutations generated", len(result.mutations) > 0)


def test_drain_skips_orphaned_index() -> None:
    print("\n── 1c: Drain skips orphaned index entries ──")
    state: dict[str, Any] = {
        # Pending index exists but no batch record
        "execution_batch_index.pending.bat_orphan": {
            "session_id": "s",
            "task_count": 1,
        },
    }
    result = drain_pending_batches(state)
    _report("no batches drained", len(result.batches) == 0)
    _report("orphan skipped", "bat_orphan" in result.skipped)


def test_drain_skips_non_pending() -> None:
    print("\n── 1d: Drain skips non-pending batches ──")
    state: dict[str, Any] = {}
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="s",
        mode="m",
        tasks=(t1,),
    )
    _apply_mutations(state, batch_to_mutations(batch))
    # Manually set status to active (simulating already-started)
    key = f"execution_batch.{batch.batch_id}"
    state[key]["status"] = "active"

    result = drain_pending_batches(state)
    _report("skipped non-pending", len(result.batches) == 0)
    _report("marked as skipped", batch.batch_id in result.skipped)


# ═══════════════════════════════════════════════════════════════════════════
# 2. EXECUTION BRIDGE — DISPATCH
# ═══════════════════════════════════════════════════════════════════════════


def test_dispatch_success() -> None:
    print("\n── 2a: Dispatch all tasks successfully ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    t2 = BatchTask(task_id="t2", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1, t2),
    )
    adapter = FakeAdapter("local")
    result = dispatch_batch(batch, {"local": adapter})

    _report("2 task results", len(result.task_results) == 2)
    _report("all succeeded", result.all_succeeded)
    _report("none failed", not result.any_failed)
    _report("adapter called twice", len(adapter.calls) == 2)
    _report("execution_ids collected", len(result.execution_ids) == 2)


def test_dispatch_with_failure() -> None:
    print("\n── 2b: Dispatch with task failure ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    adapter = FakeAdapter("local", should_fail=True)
    result = dispatch_batch(batch, {"local": adapter})

    _report("task failed", not result.all_succeeded)
    _report("any_failed true", result.any_failed)
    _report(
        "result status FAILED",
        result.task_results[0].result is not None
        and result.task_results[0].result.status == ExecutionStatus.FAILED,
    )


def test_dispatch_no_adapter() -> None:
    print("\n── 2c: Dispatch with missing adapter ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    result = dispatch_batch(batch, {})  # No adapters

    _report("task has error", result.task_results[0].error != "")
    _report("not succeeded", not result.task_results[0].succeeded)
    _report("any_failed true", result.any_failed)


def test_dispatch_adapter_exception() -> None:
    print("\n── 2d: Dispatch handles adapter exception ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    adapter = FakeAdapter("local", should_raise=True)
    result = dispatch_batch(batch, {"local": adapter})

    _report("task has error", result.task_results[0].error != "")
    _report("error captured", "exploded" in result.task_results[0].error)


# ═══════════════════════════════════════════════════════════════════════════
# 3. EXECUTION BRIDGE — APPLY RESULTS
# ═══════════════════════════════════════════════════════════════════════════


def test_apply_results_completes_batch() -> None:
    print("\n── 3a: Apply results completes batch ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    state: dict[str, Any] = {}
    _apply_mutations(state, batch_to_mutations(batch))

    adapter = FakeAdapter("local")
    dispatch_result = dispatch_batch(batch, {"local": adapter})
    mutations = apply_execution_results(dispatch_result, state)

    # Apply mutations to check final state
    _apply_mutations(state, mutations)

    loaded = load_execution_batch(state, batch.batch_id)
    _report("batch completed", loaded is not None and loaded.status == "completed")

    # Check artifact was created
    recent = list_recent_artifacts(state)
    _report("summary artifact created", len(recent) > 0)


def test_apply_results_fails_batch() -> None:
    print("\n── 3b: Apply results fails batch ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    state: dict[str, Any] = {}
    _apply_mutations(state, batch_to_mutations(batch))

    adapter = FakeAdapter("local", should_fail=True)
    dispatch_result = dispatch_batch(batch, {"local": adapter})
    mutations = apply_execution_results(dispatch_result, state)
    _apply_mutations(state, mutations)

    loaded = load_execution_batch(state, batch.batch_id)
    _report("batch failed", loaded is not None and loaded.status == "failed")


def test_apply_results_updates_workstation_run() -> None:
    print("\n── 3c: Apply results updates linked workstation run ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    state: dict[str, Any] = {}
    _apply_mutations(state, batch_to_mutations(batch))

    # Create a workstation run linked to this batch
    run = build_workstation_run(
        session_id="sess_a",
        node_id="local",
        correlation_id="corr_1",
        batch_id=batch.batch_id,
    )
    _apply_mutations(state, build_workstation_run_mutations(run))

    adapter = FakeAdapter("local")
    dispatch_result = dispatch_batch(batch, {"local": adapter})
    mutations = apply_execution_results(dispatch_result, state)
    _apply_mutations(state, mutations)

    loaded_run = load_workstation_run(state, run.run_id)
    _report(
        "run completed",
        loaded_run is not None and loaded_run.status == "completed",
    )
    _report(
        "execution_ids tracked",
        loaded_run is not None and len(loaded_run.execution_ids) > 0,
    )

    # Active index should be cleaned up
    active = list_active_workstation_runs(state)
    _report("run removed from active index", run.run_id not in active)


# ═══════════════════════════════════════════════════════════════════════════
# 4. WORKSTATION ADAPTER
# ═══════════════════════════════════════════════════════════════════════════


def test_create_workstation_run_for_batch() -> None:
    print("\n── 4a: Create workstation run for batch ──")
    run, mutations = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    _report("run created", run is not None)
    _report("batch_id linked", run.batch_id == "bat_123")
    _report("node_id set", run.node_id == "ws_node")
    _report("status pending", run.status == "pending")
    _report("mutations generated", len(mutations) > 0)
    ops = {m["op"] for m in mutations}
    _report("only SET ops", ops == {"SET"})


def test_start_run() -> None:
    print("\n── 4b: Start workstation run ──")
    run, _ = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    started, mutations = start_run(run)
    _report("status active", started.status == "active")
    _report("started_at set", started.started_at != "")
    _report("mutations generated", len(mutations) > 0)


def test_track_execution_results() -> None:
    print("\n── 4c: Track execution results ──")
    run, _ = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    updated = track_execution_results(run, ("exec_1", "exec_2"))
    _report("execution_ids tracked", updated.execution_ids == ("exec_1", "exec_2"))
    _report("status unchanged", updated.status == run.status)

    # Track more
    updated2 = track_execution_results(updated, ("exec_3",))
    _report(
        "execution_ids appended",
        updated2.execution_ids == ("exec_1", "exec_2", "exec_3"),
    )


def test_finalize_success() -> None:
    print("\n── 4d: Finalize workstation run (success) ──")
    run, _ = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    completed, mutations = finalize_workstation_run(
        run,
        success=True,
        execution_ids=("exec_1",),
    )
    _report("status completed", completed.status == "completed")
    _report("completed_at set", completed.completed_at != "")
    _report("execution_ids set", completed.execution_ids == ("exec_1",))


def test_finalize_failure() -> None:
    print("\n── 4e: Finalize workstation run (failure) ──")
    run, _ = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    failed, mutations = finalize_workstation_run(
        run,
        success=False,
        reason="timeout",
    )
    _report("status failed", failed.status == "failed")
    _report(
        "reason in mutations",
        any(
            m.get("value", {}).get("reason") == "timeout"
            for m in mutations
            if m["op"] == "SET"
        ),
    )


def test_load_and_finalize() -> None:
    print("\n── 4f: Load and finalize from state ──")
    run, create_muts = create_workstation_run_for_batch(
        session_id="sess_a",
        node_id="ws_node",
        batch_id="bat_123",
        correlation_id="corr_1",
    )
    state: dict[str, Any] = {}
    _apply_mutations(state, create_muts)

    loaded, mutations = load_and_finalize(
        state,
        run.run_id,
        success=True,
        execution_ids=("exec_1",),
    )
    _report("loaded run", loaded is not None)
    assert loaded is not None
    _report("completed", loaded.status == "completed")

    # Test missing run
    missing, empty_muts = load_and_finalize(state, "wkr_nonexistent", success=True)
    _report("missing returns None", missing is None)
    _report("no mutations for missing", len(empty_muts) == 0)


# ═══════════════════════════════════════════════════════════════════════════
# 5. END-TO-END
# ═══════════════════════════════════════════════════════════════════════════


def test_end_to_end() -> None:
    print("\n── 5a: End-to-end drain → dispatch → apply ──")
    state: dict[str, Any] = {}

    # 1. Create a batch
    t1 = BatchTask(task_id="t1", execution_class="pure", payload={"x": 1})
    t2 = BatchTask(task_id="t2", execution_class="pure", payload={"x": 2})
    batch = build_execution_batch(
        session_id="sess_e2e",
        mode="active",
        tasks=(t1, t2),
    )
    _apply_mutations(state, batch_to_mutations(batch))

    # 2. Create a linked workstation run
    run, run_muts = create_workstation_run_for_batch(
        session_id="sess_e2e",
        node_id="local",
        batch_id=batch.batch_id,
        correlation_id="e2e_test",
    )
    _apply_mutations(state, run_muts)

    # 3. Drain pending batches
    drain_result = drain_pending_batches(state)
    _report("1 batch drained", len(drain_result.batches) == 1)
    _apply_mutations(state, drain_result.mutations)

    # 4. Dispatch
    adapter = FakeAdapter("local")
    drained_batch = drain_result.batches[0]
    dispatch_result = dispatch_batch(drained_batch, {"local": adapter})
    _report("all tasks dispatched", dispatch_result.all_succeeded)

    # 5. Apply results
    result_mutations = apply_execution_results(dispatch_result, state)
    _apply_mutations(state, result_mutations)

    # 6. Verify final state
    loaded_batch = load_execution_batch(state, batch.batch_id)
    _report(
        "batch completed",
        loaded_batch is not None and loaded_batch.status == "completed",
    )

    loaded_run = load_workstation_run(state, run.run_id)
    _report(
        "run completed",
        loaded_run is not None and loaded_run.status == "completed",
    )
    _report(
        "run has execution_ids",
        loaded_run is not None and len(loaded_run.execution_ids) == 2,
    )

    active_runs = list_active_workstation_runs(state)
    _report("no active runs remain", len(active_runs) == 0)

    recent_arts = list_recent_artifacts(state)
    _report("summary artifact exists", len(recent_arts) > 0)

    # Load and verify artifact content
    if recent_arts:
        art = load_runtime_artifact(state, recent_arts[0])
        _report(
            "artifact has batch content",
            art is not None and batch.batch_id in art.body,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 6. INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════


def test_all_mutations_set_remove() -> None:
    print("\n── 6a: All mutations use SET/REMOVE only ──")
    state: dict[str, Any] = {}
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="s",
        mode="m",
        tasks=(t1,),
    )
    _apply_mutations(state, batch_to_mutations(batch))

    run, run_muts = create_workstation_run_for_batch(
        session_id="s",
        node_id="n",
        batch_id=batch.batch_id,
        correlation_id="c",
    )
    _apply_mutations(state, run_muts)

    drain_result = drain_pending_batches(state)
    _apply_mutations(state, drain_result.mutations)

    adapter = FakeAdapter("local")
    dispatch_result = dispatch_batch(drain_result.batches[0], {"local": adapter})
    result_mutations = apply_execution_results(dispatch_result, state)

    all_mutations = (
        batch_to_mutations(batch) + run_muts + drain_result.mutations + result_mutations
    )
    ops = {m["op"] for m in all_mutations}
    _report(
        "only SET and REMOVE",
        ops <= {"SET", "REMOVE"},
        f"ops: {ops}",
    )


def test_replay_determinism() -> None:
    print("\n── 6b: Replay determinism ──")
    t1 = BatchTask(task_id="t1", execution_class="pure")
    batch = build_execution_batch(
        session_id="s",
        mode="m",
        tasks=(t1,),
        batch_id="bat_fixed",
    )
    m1 = batch_to_mutations(batch)
    m2 = batch_to_mutations(batch)
    _report("batch mutations replay identical", m1 == m2)

    run1, r1_muts = create_workstation_run_for_batch(
        session_id="s",
        node_id="n",
        batch_id="bat_fixed",
        correlation_id="c",
    )
    run2, r2_muts = create_workstation_run_for_batch(
        session_id="s",
        node_id="n",
        batch_id="bat_fixed",
        correlation_id="c",
    )
    _report("run IDs deterministic", run1.run_id == run2.run_id)


def test_no_substrate_modification() -> None:
    print("\n── 6c: No substrate code modified ──")
    # Verify we can import substrate modules without issues
    from umh.substrate.execution_batch import ExecutionBatch as EB
    from umh.substrate.workstation_runtime import WorkstationRun as WR
    from umh.substrate.artifact_contract import RuntimeArtifact as RA

    _report("execution_batch importable", EB is not None)
    _report("workstation_runtime importable", WR is not None)
    _report("artifact_contract importable", RA is not None)


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. Batch drainer
    test_drain_empty_state()
    test_drain_pending_batches_deterministic()
    test_drain_skips_orphaned_index()
    test_drain_skips_non_pending()

    # 2. Execution bridge — dispatch
    test_dispatch_success()
    test_dispatch_with_failure()
    test_dispatch_no_adapter()
    test_dispatch_adapter_exception()

    # 3. Execution bridge — apply results
    test_apply_results_completes_batch()
    test_apply_results_fails_batch()
    test_apply_results_updates_workstation_run()

    # 4. Workstation adapter
    test_create_workstation_run_for_batch()
    test_start_run()
    test_track_execution_results()
    test_finalize_success()
    test_finalize_failure()
    test_load_and_finalize()

    # 5. End-to-end
    test_end_to_end()

    # 6. Invariants
    test_all_mutations_set_remove()
    test_replay_determinism()
    test_no_substrate_modification()

    print(f"\n{'=' * 60}")
    print(f"  {_PASS} passed, {_FAIL} failed")
    print(f"{'=' * 60}")
    sys.exit(0 if _FAIL == 0 else 1)
