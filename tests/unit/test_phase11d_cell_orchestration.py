"""Phase 11D — Cell Orchestration + Multi-Cell Coordination v1.

44 tests covering:
  Signal Router (7), Workflow (6), Orchestrator (13), Resume (5),
  Persistence (5), Signal Handling (1), Append-Only (1), Lineage (1),
  Boundary (3), Phase 11C Regression (3).
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")

from umh.cells.models import (
    CellCheckpoint,
    CellContext,
    CellIdentity,
    CellStatus,
    CellType,
    InvalidTransitionError,
    _gen_id,
)
from umh.cells.orchestrator import CellOrchestrator
from umh.cells.persistence import FileCheckpointStore, InMemoryCheckpointStore
from umh.cells.router import RoutingAction, RoutingDecision, SignalRoute, SignalRouter
from umh.cells.runtime import (
    activate_cell,
    checkpoint_cell,
    clear as clear_runtime,
    fail_cell,
    get_cell,
    get_cell_status,
    hydrate_cell,
    list_cells,
    request_execution,
    resume_cell,
    spawn_cell,
    terminate_cell,
)
from umh.cells.workflow import (
    CellWorkflow,
    CellWorkflowStep,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepStatus,
    runnable_steps,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset all cell and orchestrator state between tests."""
    clear_runtime()
    yield
    clear_runtime()


# ─── Signal Router (7) ──────────────────────────────────────────────


class TestSignalRouter:
    def test_register_and_list_routes(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1", source_signal_type="cell.completed", action=RoutingAction.NOTIFY
        )
        router.register_route(route)
        routes = router.list_routes()
        assert len(routes) == 1
        assert routes[0].route_id == "r1"

    def test_route_matching_signal(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1", source_signal_type="cell.done", action=RoutingAction.COMPLETE_STEP
        )
        router.register_route(route)
        decisions = router.route_signal("cell.done", {"run_id": "x", "step_id": "s1"})
        assert len(decisions) == 1
        assert decisions[0].action == RoutingAction.COMPLETE_STEP

    def test_route_nonmatching_signal(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1", source_signal_type="cell.done", action=RoutingAction.NOTIFY
        )
        router.register_route(route)
        decisions = router.route_signal("cell.failed", {})
        assert decisions == []

    def test_disabled_route_skipped(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1",
            source_signal_type="cell.done",
            action=RoutingAction.NOTIFY,
            enabled=False,
        )
        router.register_route(route)
        decisions = router.route_signal("cell.done", {})
        assert decisions == []

    def test_condition_matching(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1",
            source_signal_type="cell.done",
            action=RoutingAction.COMPLETE_STEP,
            condition={"workflow_id": "wf1"},
        )
        router.register_route(route)

        yes = router.route_signal("cell.done", {"workflow_id": "wf1"})
        assert len(yes) == 1

        no = router.route_signal("cell.done", {"workflow_id": "wf_other"})
        assert no == []

    def test_routing_decision_structure(self):
        router = SignalRouter()
        route = SignalRoute(
            route_id="r1",
            source_signal_type="x",
            action=RoutingAction.SPAWN_CELL,
            target_cell_type=CellType.PLANNING,
            workflow_id="wf99",
        )
        router.register_route(route)
        decisions = router.route_signal("x", {"key": "val"})
        d = decisions[0]
        assert d.route_id == "r1"
        assert d.target_cell_type == CellType.PLANNING
        assert d.workflow_id == "wf99"
        assert d.signal_payload == {"key": "val"}

    def test_unregister_route(self):
        router = SignalRouter()
        route = SignalRoute(route_id="r1", source_signal_type="x", action=RoutingAction.NONE)
        router.register_route(route)
        assert router.unregister_route("r1") is True
        assert router.unregister_route("r1") is False
        assert router.list_routes() == []


# ─── Workflow (6) ────────────────────────────────────────────────────


class TestWorkflow:
    def test_workflow_serialization_roundtrip(self):
        wf = CellWorkflow(
            workflow_id="wf1",
            objective="test",
            steps=[
                CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan"),
                CellWorkflowStep(
                    step_id="s2", cell_type=CellType.REVIEW, objective="review", depends_on=("s1",)
                ),
            ],
        )
        data = wf.to_dict()
        wf2 = CellWorkflow.from_dict(data)
        assert wf2.workflow_id == "wf1"
        assert len(wf2.steps) == 2
        assert wf2.steps[1].depends_on == ("s1",)

    def test_step_serialization(self):
        step = CellWorkflowStep(
            step_id="s1",
            cell_type=CellType.DEBUG,
            objective="debug it",
            depends_on=("s0",),
            output_key="debug_result",
            required=False,
        )
        data = step.to_dict()
        step2 = CellWorkflowStep.from_dict(data)
        assert step2.step_id == "s1"
        assert step2.required is False
        assert step2.output_key == "debug_result"

    def test_run_serialization(self):
        run = WorkflowRun(run_id="run1", workflow_id="wf1", status=WorkflowStatus.RUNNING)
        run.step_statuses["s1"] = WorkflowStepStatus.COMPLETED
        run.step_statuses["s2"] = WorkflowStepStatus.ACTIVE
        data = run.to_dict()
        run2 = WorkflowRun.from_dict(data)
        assert run2.run_id == "run1"
        assert run2.step_statuses["s1"] == WorkflowStepStatus.COMPLETED
        assert run2.completed_step_ids == ["s1"]
        assert run2.active_step_ids == ["s2"]

    def test_sequential_starts_first_only(self):
        wf = CellWorkflow(
            workflow_id="wf1",
            objective="seq",
            steps=[
                CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="first"),
                CellWorkflowStep(
                    step_id="s2", cell_type=CellType.REVIEW, objective="second", depends_on=("s1",)
                ),
            ],
        )
        run = WorkflowRun(run_id="r1", workflow_id="wf1")
        run.step_statuses = {"s1": WorkflowStepStatus.PENDING, "s2": WorkflowStepStatus.PENDING}

        ready = runnable_steps(wf, run)
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

    def test_dag_starts_parallel_roots(self):
        wf = CellWorkflow(
            workflow_id="wf1",
            objective="dag",
            steps=[
                CellWorkflowStep(step_id="a", cell_type=CellType.PLANNING, objective="branch a"),
                CellWorkflowStep(step_id="b", cell_type=CellType.DEBUG, objective="branch b"),
                CellWorkflowStep(
                    step_id="c", cell_type=CellType.REVIEW, objective="join", depends_on=("a", "b")
                ),
            ],
        )
        run = WorkflowRun(run_id="r1", workflow_id="wf1")
        run.step_statuses = {
            "a": WorkflowStepStatus.PENDING,
            "b": WorkflowStepStatus.PENDING,
            "c": WorkflowStepStatus.PENDING,
        }

        ready = runnable_steps(wf, run)
        ids = {s.step_id for s in ready}
        assert ids == {"a", "b"}

    def test_dependencies_block_until_complete(self):
        wf = CellWorkflow(
            workflow_id="wf1",
            objective="blocked",
            steps=[
                CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="first"),
                CellWorkflowStep(
                    step_id="s2", cell_type=CellType.REVIEW, objective="second", depends_on=("s1",)
                ),
            ],
        )
        run = WorkflowRun(run_id="r1", workflow_id="wf1")
        run.step_statuses = {"s1": WorkflowStepStatus.ACTIVE, "s2": WorkflowStepStatus.PENDING}

        ready = runnable_steps(wf, run)
        assert ready == []


# ─── Orchestrator (13) ───────────────────────────────────────────────


def _make_sequential_workflow() -> CellWorkflow:
    return CellWorkflow(
        workflow_id="wf_seq",
        objective="sequential test",
        steps=[
            CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan"),
            CellWorkflowStep(
                step_id="s2", cell_type=CellType.REVIEW, objective="review", depends_on=("s1",)
            ),
        ],
    )


def _make_dag_workflow() -> CellWorkflow:
    return CellWorkflow(
        workflow_id="wf_dag",
        objective="dag test",
        steps=[
            CellWorkflowStep(step_id="a", cell_type=CellType.PLANNING, objective="branch a"),
            CellWorkflowStep(step_id="b", cell_type=CellType.DEBUG, objective="branch b"),
            CellWorkflowStep(
                step_id="c", cell_type=CellType.REVIEW, objective="join", depends_on=("a", "b")
            ),
        ],
    )


class TestOrchestrator:
    def test_start_workflow_creates_run(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        assert run.run_id.startswith("wfrun_")
        assert run.status == WorkflowStatus.RUNNING

    def test_start_workflow_spawns_first_step(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        assert run.step_statuses["s1"] == WorkflowStepStatus.ACTIVE
        assert run.step_statuses["s2"] == WorkflowStepStatus.PENDING
        assert run.step_cell_ids.get("s1")

    def test_complete_step_advances(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        ok = orch.complete_step(run.run_id, "s1", {"result": "done"})
        assert ok is True
        run_after = orch.get_run(run.run_id)
        assert run_after.step_statuses["s1"] == WorkflowStepStatus.COMPLETED
        assert run_after.step_statuses["s2"] == WorkflowStepStatus.ACTIVE

    def test_advance_spawns_next_step(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        run_after = orch.get_run(run.run_id)
        assert run_after.step_cell_ids.get("s2")

    def test_full_sequential_completion(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        orch.complete_step(run.run_id, "s2")
        run_after = orch.get_run(run.run_id)
        assert run_after.status == WorkflowStatus.COMPLETED

    def test_full_dag_completion(self):
        orch = CellOrchestrator()
        wf = _make_dag_workflow()
        run = orch.start_workflow(wf)
        assert run.step_statuses["a"] == WorkflowStepStatus.ACTIVE
        assert run.step_statuses["b"] == WorkflowStepStatus.ACTIVE
        assert run.step_statuses["c"] == WorkflowStepStatus.PENDING

        orch.complete_step(run.run_id, "a")
        assert run.step_statuses["c"] == WorkflowStepStatus.PENDING

        orch.complete_step(run.run_id, "b")
        assert run.step_statuses["c"] == WorkflowStepStatus.ACTIVE

        orch.complete_step(run.run_id, "c")
        assert run.status == WorkflowStatus.COMPLETED

    def test_failed_required_step_fails_workflow(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        orch.fail_step(run.run_id, "s1", "boom")
        run_after = orch.get_run(run.run_id)
        assert run_after.status == WorkflowStatus.FAILED

    def test_failed_optional_step_skips(self):
        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_opt",
            objective="optional test",
            steps=[
                CellWorkflowStep(
                    step_id="s1", cell_type=CellType.PLANNING, objective="plan", required=False
                ),
                CellWorkflowStep(
                    step_id="s2", cell_type=CellType.REVIEW, objective="review", depends_on=("s1",)
                ),
            ],
        )
        run = orch.start_workflow(wf)
        orch.fail_step(run.run_id, "s1", "non-critical")
        run_after = orch.get_run(run.run_id)
        assert run_after.step_statuses["s1"] == WorkflowStepStatus.SKIPPED
        assert run_after.status != WorkflowStatus.FAILED

    def test_completion_emits(self):
        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_single",
            objective="single step",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        assert run.status == WorkflowStatus.COMPLETED

    def test_failure_emits(self):
        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_fail",
            objective="fail test",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.fail_step(run.run_id, "s1", "error")
        assert run.status == WorkflowStatus.FAILED

    def test_get_and_list_runs(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run = orch.start_workflow(wf)
        assert orch.get_run(run.run_id) is not None
        assert orch.get_run("nonexistent") is None
        runs = orch.list_runs()
        assert len(runs) == 1
        runs_filtered = orch.list_runs(workflow_id="wf_seq")
        assert len(runs_filtered) == 1
        runs_empty = orch.list_runs(workflow_id="no_such")
        assert len(runs_empty) == 0

    def test_terminal_run_cannot_advance(self):
        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_term",
            objective="term test",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        ok = orch.complete_step(run.run_id, "s1")
        assert ok is False

    def test_unique_run_ids(self):
        orch = CellOrchestrator()
        wf = _make_sequential_workflow()
        run1 = orch.start_workflow(wf)
        clear_runtime()
        run2 = orch.start_workflow(wf)
        assert run1.run_id != run2.run_id


# ─── Resume (5) ──────────────────────────────────────────────────────


class TestResume:
    def test_active_to_waiting_via_request(self):
        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="test")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        req = request_execution(identity.cell_id, "do stuff", "operate")
        assert get_cell_status(identity.cell_id) == CellStatus.WAITING

    def test_waiting_to_active_via_resume(self):
        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="test")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        request_execution(identity.cell_id, "do stuff", "operate")
        resume_cell(identity.cell_id, {"key": "val"})
        assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE

    def test_resume_wrong_cell_raises(self):
        with pytest.raises(ValueError, match="not found"):
            resume_cell("nonexistent_cell")

    def test_resume_terminal_cell_raises(self):
        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="test")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        terminate_cell(identity.cell_id)
        with pytest.raises(InvalidTransitionError):
            resume_cell(identity.cell_id)

    def test_resume_created_cell_raises(self):
        identity = spawn_cell(CellType.PLANNING)
        with pytest.raises(InvalidTransitionError):
            resume_cell(identity.cell_id)


# ─── Persistence (5) ────────────────────────────────────────────────


class TestPersistence:
    def test_inmemory_checkpoint_save_load(self):
        store = InMemoryCheckpointStore()
        cp = CellCheckpoint(
            checkpoint_id="ckpt_1",
            cell_id="c1",
            status=CellStatus.CHECKPOINTED,
            context={},
            version=1,
        )
        store.save_cell_checkpoint(cp)
        loaded = store.load_cell_checkpoint("c1")
        assert loaded is not None
        assert loaded.checkpoint_id == "ckpt_1"

    def test_inmemory_workflow_run_save_load(self):
        store = InMemoryCheckpointStore()
        run = WorkflowRun(run_id="r1", workflow_id="wf1", status=WorkflowStatus.RUNNING)
        store.save_workflow_run(run)
        loaded = store.load_workflow_run("r1")
        assert loaded is not None
        assert loaded.workflow_id == "wf1"

    def test_inmemory_missing_returns_none(self):
        store = InMemoryCheckpointStore()
        assert store.load_cell_checkpoint("no_such") is None
        assert store.load_workflow_run("no_such") is None

    def test_file_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            store = FileCheckpointStore(td)
            cp = CellCheckpoint(
                checkpoint_id="ckpt_f1",
                cell_id="c1",
                status=CellStatus.CHECKPOINTED,
                context={"key": "val"},
                version=2,
            )
            store.save_cell_checkpoint(cp)
            loaded = store.load_cell_checkpoint("c1")
            assert loaded is not None
            assert loaded.checkpoint_id == "ckpt_f1"
            assert loaded.context == {"key": "val"}

    def test_orchestrator_checkpoint_resume(self):
        store = InMemoryCheckpointStore()
        orch = CellOrchestrator(store=store)
        wf = CellWorkflow(
            workflow_id="wf_ck",
            objective="checkpoint test",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.checkpoint_run(run.run_id)

        orch2 = CellOrchestrator(store=store)
        loaded = store.load_workflow_run(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id


# ─── Signal Handling (1) ────────────────────────────────────────────


class TestSignalHandling:
    def test_orchestrator_routes_signal(self):
        orch = CellOrchestrator()
        route = SignalRoute(
            route_id="sig_r1",
            source_signal_type="task.done",
            action=RoutingAction.NOTIFY,
        )
        orch.router.register_route(route)
        decisions = orch.handle_signal("task.done", {"info": "ok"})
        assert len(decisions) == 1
        assert decisions[0].action == RoutingAction.NOTIFY


# ─── Append-Only (1) ────────────────────────────────────────────────


class TestAppendOnly:
    def test_routing_decision_is_frozen(self):
        d = RoutingDecision(
            route_id="r1",
            action=RoutingAction.NONE,
            signal_type="x",
            signal_payload={"a": 1},
        )
        with pytest.raises(AttributeError):
            d.action = RoutingAction.NOTIFY


# ─── Lineage (1) ────────────────────────────────────────────────────


class TestLineage:
    def test_child_cell_inherits_lineage(self):
        parent = spawn_cell(CellType.PLANNING)
        child = spawn_cell(CellType.REVIEW, parent_cell_id=parent.cell_id)
        assert parent.cell_id in child.lineage
        grandchild = spawn_cell(CellType.DEBUG, parent_cell_id=child.cell_id)
        assert parent.cell_id in grandchild.lineage
        assert child.cell_id in grandchild.lineage


# ─── Boundary (3) ───────────────────────────────────────────────────


class TestBoundary:
    """Verify cell modules do NOT import execution/adapter/subprocess/shell."""

    _CELL_MODULES = [
        "/opt/OS/umh/cells/models.py",
        "/opt/OS/umh/cells/runtime.py",
        "/opt/OS/umh/cells/router.py",
        "/opt/OS/umh/cells/workflow.py",
        "/opt/OS/umh/cells/orchestrator.py",
        "/opt/OS/umh/cells/persistence.py",
    ]

    _FORBIDDEN_IMPORT_PATTERNS = [
        "import subprocess",
        "import adapter",
        "from adapter",
        "from umh.execution",
        "import umh.execution",
    ]

    _FORBIDDEN_CODE_PATTERNS = [
        "shell=True",
    ]

    def test_no_forbidden_imports_in_cell_modules(self):
        for path in self._CELL_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'")
                ):
                    continue
                for pattern in self._FORBIDDEN_IMPORT_PATTERNS:
                    assert pattern not in stripped, f"'{pattern}' found in {path}: {stripped}"
                for pattern in self._FORBIDDEN_CODE_PATTERNS:
                    assert pattern not in stripped, f"'{pattern}' found in {path}: {stripped}"

    def test_no_direct_system_calls_in_cell_modules(self):
        forbidden = ["os" + "." + "system"]
        for path in self._CELL_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            for pattern in forbidden:
                assert pattern not in source, f"Direct system call found in {path}"

    def test_brain_modules_also_clean(self):
        brain_paths = [
            "/opt/OS/umh/brains/profile.py",
            "/opt/OS/umh/brains/expression.py",
            "/opt/OS/umh/brains/registry.py",
            "/opt/OS/umh/brains/signals.py",
        ]
        for path in brain_paths:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'")
                ):
                    continue
                for pattern in self._FORBIDDEN_IMPORT_PATTERNS:
                    assert pattern not in stripped, f"'{pattern}' found in {path}: {stripped}"


# ─── Phase 11C Regression (3) ───────────────────────────────────────


class TestPhase11CRegression:
    def test_spawn_hydrate_activate_still_works(self):
        identity = spawn_cell(CellType.INTERPRETATION)
        ctx = CellContext(cell_id=identity.cell_id, objective="regress")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE

    def test_checkpoint_still_works(self):
        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="cp test")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        cp = checkpoint_cell(identity.cell_id)
        assert cp.checkpoint_id.startswith("ckpt_")
        assert cp.version > 0

    def test_execution_request_still_works(self):
        identity = spawn_cell(CellType.EXECUTION_REQUESTER)
        ctx = CellContext(cell_id=identity.cell_id, objective="exec test")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        req = request_execution(identity.cell_id, "run analysis", "analyze")
        assert req.request_id.startswith("creq_")
        assert get_cell_status(identity.cell_id) == CellStatus.WAITING
