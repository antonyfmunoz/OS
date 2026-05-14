"""Phase 12 — Persistent Advisor Runtime + Session System + Multi-Node Orchestration v1.

Tests covering:
  Session (6), Advisor (7), Loop (5), Node Registry (4), Node Routing (4),
  Workflow (4), Integration (4), Boundary (5), Regression (5).
  Total: 44 tests.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.runtime.session import Session, SessionManager, SessionState, SessionType
from umh.runtime.advisor import AdvisorRuntime
from umh.runtime.loop import RuntimeLoop
from umh.nodes.registry import DeviceNode, DeviceNodeRegistry, DeviceType
from umh.nodes.routing import route_task
from umh.workflows.executor import WorkflowExecutor
from umh.cells.models import CellStatus, CellType, _gen_id
from umh.cells.runtime import clear as clear_cells, get_cell_status
from umh.brains.signals import clear as clear_signals, emit_signal
from umh.environments.telemetry import NodeTelemetry


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_state():
    clear_cells()
    clear_signals()
    yield
    clear_cells()
    clear_signals()


# ═══════════════════════════════════════════════════════════════════════
# Session (6)
# ═══════════════════════════════════════════════════════════════════════


class TestSession:
    def test_start_and_end_lifecycle(self):
        sm = SessionManager()
        session = sm.start_session(SessionType.DAY)
        assert session.state == SessionState.ACTIVE
        assert session.session_type == SessionType.DAY
        assert session.session_id.startswith("sess_")
        ended = sm.end_session()
        assert ended is not None
        assert ended.state == SessionState.COMPLETED
        assert ended.end_time != ""

    def test_single_active_session_enforced(self):
        sm = SessionManager()
        sm.start_session(SessionType.DAY)
        with pytest.raises(RuntimeError, match="still active"):
            sm.start_session(SessionType.NIGHT)

    def test_cell_tracking(self):
        sm = SessionManager()
        sm.start_session(SessionType.DAY)
        assert sm.attach_cell("cell_1") is True
        assert sm.attach_cell("cell_2") is True
        session = sm.get_active_session()
        assert "cell_1" in session.active_cells
        assert "cell_2" in session.active_cells

    def test_cell_detach(self):
        sm = SessionManager()
        sm.start_session(SessionType.DAY)
        sm.attach_cell("cell_1")
        assert sm.detach_cell("cell_1") is True
        assert sm.detach_cell("cell_1") is False
        session = sm.get_active_session()
        assert "cell_1" not in session.active_cells

    def test_no_attach_without_session(self):
        sm = SessionManager()
        assert sm.attach_cell("cell_1") is False

    def test_session_history(self):
        sm = SessionManager()
        sm.start_session(SessionType.DAY)
        sm.end_session()
        sm.start_session(SessionType.NIGHT)
        sm.end_session()
        history = sm.list_history()
        assert len(history) == 2
        assert history[0].session_type == SessionType.DAY
        assert history[1].session_type == SessionType.NIGHT


# ═══════════════════════════════════════════════════════════════════════
# Advisor (7)
# ═══════════════════════════════════════════════════════════════════════


class TestAdvisor:
    def test_start_creates_session_and_advisor_cell(self):
        advisor = AdvisorRuntime()
        session = advisor.start(SessionType.DAY)
        assert session.state == SessionState.ACTIVE
        assert advisor.advisor_cell_id is not None
        assert get_cell_status(advisor.advisor_cell_id) == CellStatus.ACTIVE
        advisor.stop()

    def test_stop_terminates_advisor_cell(self):
        advisor = AdvisorRuntime()
        advisor.start()
        cell_id = advisor.advisor_cell_id
        advisor.stop()
        assert get_cell_status(cell_id) == CellStatus.TERMINATED

    def test_stop_ends_session(self):
        advisor = AdvisorRuntime()
        advisor.start()
        ended = advisor.stop()
        assert ended is not None
        assert ended.state == SessionState.COMPLETED

    def test_spawn_worker_creates_active_cell(self):
        advisor = AdvisorRuntime()
        advisor.start()
        worker_id = advisor.spawn_worker(CellType.PLANNING, "test objective")
        assert get_cell_status(worker_id) == CellStatus.ACTIVE
        session = advisor.session_manager.get_active_session()
        assert worker_id in session.active_cells
        advisor.stop()

    def test_advisor_does_not_execute(self):
        source = open("/opt/OS/umh/runtime/advisor.py").read()
        assert "import subprocess" not in source
        assert "import docker" not in source
        assert "from umh.environments" not in source

    def test_tick_processes_signals(self):
        advisor = AdvisorRuntime()
        advisor.start()
        emit_signal("test_brain", "observation", {"data": "test"})
        result = advisor.tick()
        assert result["signals_processed"] >= 1
        advisor.stop()

    def test_get_state_returns_snapshot(self):
        advisor = AdvisorRuntime()
        advisor.start()
        state = advisor.get_state()
        assert state["advisor_cell_id"] is not None
        assert state["session"] is not None
        assert state["tick_count"] == 0
        advisor.stop()


# ═══════════════════════════════════════════════════════════════════════
# Loop (5)
# ═══════════════════════════════════════════════════════════════════════


class TestRuntimeLoop:
    def test_start_and_stop(self):
        loop = RuntimeLoop()
        loop.start()
        assert loop.running is True
        loop.stop()
        assert loop.running is False

    def test_tick_runs_safely(self):
        loop = RuntimeLoop()
        loop.start()
        result = loop.tick()
        assert "tick" in result
        assert result["tick"] == 1
        loop.stop()

    def test_multiple_ticks_no_infinite_loop(self):
        loop = RuntimeLoop()
        loop.start()
        results = loop.run_ticks(5)
        assert len(results) == 5
        for i, r in enumerate(results, 1):
            assert r["tick"] == i
        loop.stop()

    def test_tick_without_start_returns_error(self):
        loop = RuntimeLoop()
        result = loop.tick()
        assert "error" in result

    def test_deterministic_progression(self):
        loop = RuntimeLoop()
        loop.start()
        r1 = loop.tick()
        r2 = loop.tick()
        assert r2["tick"] == r1["tick"] + 1
        loop.stop()


# ═══════════════════════════════════════════════════════════════════════
# Node Registry (4)
# ═══════════════════════════════════════════════════════════════════════


class TestDeviceNodeRegistry:
    def test_register_and_get(self):
        reg = DeviceNodeRegistry()
        node = DeviceNode(node_id="n1", device_type=DeviceType.LOCAL)
        reg.register_node(node)
        assert reg.get_node("n1") is node

    def test_detect_local_node(self):
        reg = DeviceNodeRegistry()
        node = reg.detect_local_node()
        assert node.device_type == DeviceType.LOCAL
        assert node.hostname != ""
        assert reg.get_node(node.node_id) is node

    def test_list_by_type(self):
        reg = DeviceNodeRegistry()
        reg.register_node(DeviceNode(node_id="l1", device_type=DeviceType.LOCAL))
        reg.register_node(DeviceNode(node_id="v1", device_type=DeviceType.VPS))
        local = reg.list_nodes(DeviceType.LOCAL)
        assert len(local) == 1
        assert local[0].node_id == "l1"

    def test_update_telemetry(self):
        reg = DeviceNodeRegistry()
        node = reg.detect_local_node()
        t = reg.update_telemetry(node.node_id)
        assert t is not None
        assert t.cpu_percent >= 0.0
        updated = reg.get_node(node.node_id)
        assert updated.telemetry is not None


# ═══════════════════════════════════════════════════════════════════════
# Node Routing (4)
# ═══════════════════════════════════════════════════════════════════════


class TestNodeRouting:
    def test_local_preferred_when_low_load(self):
        local = DeviceNode(node_id="l1", device_type=DeviceType.LOCAL)
        vps = DeviceNode(node_id="v1", device_type=DeviceType.VPS)
        telemetry = {
            "l1": NodeTelemetry(cpu_percent=20.0, memory_percent=30.0),
            "v1": NodeTelemetry(cpu_percent=10.0, memory_percent=20.0),
        }
        chosen = route_task([local, vps], telemetry=telemetry, prefer_local=True)
        assert chosen is not None
        assert chosen.node_id == "l1"

    def test_fallback_to_vps_when_local_loaded(self):
        local = DeviceNode(node_id="l1", device_type=DeviceType.LOCAL)
        vps = DeviceNode(node_id="v1", device_type=DeviceType.VPS)
        telemetry = {
            "l1": NodeTelemetry(cpu_percent=90.0, memory_percent=85.0),
            "v1": NodeTelemetry(cpu_percent=20.0, memory_percent=30.0),
        }
        chosen = route_task([local, vps], telemetry=telemetry, prefer_local=True)
        assert chosen is not None
        assert chosen.node_id == "v1"

    def test_no_nodes_returns_none(self):
        assert route_task([]) is None

    def test_deterministic_selection(self):
        local = DeviceNode(node_id="l1", device_type=DeviceType.LOCAL)
        vps = DeviceNode(node_id="v1", device_type=DeviceType.VPS)
        t = {"l1": NodeTelemetry(cpu_percent=50.0), "v1": NodeTelemetry(cpu_percent=50.0)}
        r1 = route_task([local, vps], telemetry=t)
        r2 = route_task([local, vps], telemetry=t)
        assert r1.node_id == r2.node_id


# ═══════════════════════════════════════════════════════════════════════
# Workflow (4)
# ═══════════════════════════════════════════════════════════════════════


class TestWorkflowExecutor:
    def test_execute_objective_spawns_cells(self):
        exe = WorkflowExecutor()
        run_id = exe.execute_objective("analyze market data")
        from umh.cells.workflow import WorkflowStatus

        status = exe.get_status(run_id)
        assert status == WorkflowStatus.RUNNING
        exe.clear()

    def test_multi_step_workflow(self):
        from umh.cells.workflow import WorkflowStatus

        exe = WorkflowExecutor()
        steps = [
            {"step_id": "s1", "cell_type": "planning", "objective": "plan"},
            {"step_id": "s2", "cell_type": "review", "objective": "review", "depends_on": ["s1"]},
        ]
        run_id = exe.execute_objective("full analysis", steps=steps)
        status = exe.get_status(run_id)
        assert status == WorkflowStatus.RUNNING
        exe.clear()

    def test_complete_step_advances_workflow(self):
        exe = WorkflowExecutor()
        run_id = exe.execute_objective(
            "simple task",
            steps=[
                {"step_id": "s1", "cell_type": "planning", "objective": "do it"},
            ],
        )
        assert exe.complete_step(run_id, "s1", {"result": "done"}) is True
        from umh.cells.workflow import WorkflowStatus

        status = exe.get_status(run_id)
        assert status == WorkflowStatus.COMPLETED
        exe.clear()

    def test_executor_does_not_import_environments(self):
        source = open("/opt/OS/umh/workflows/executor.py").read()
        assert "from umh.environments" not in source
        assert "import subprocess" not in source


# ═══════════════════════════════════════════════════════════════════════
# Integration (4)
# ═══════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_full_advisor_loop_flow(self):
        loop = RuntimeLoop()
        loop.start(SessionType.DAY)
        advisor = loop.advisor
        worker_id = advisor.spawn_worker(CellType.PLANNING, "integration test")
        assert get_cell_status(worker_id) == CellStatus.ACTIVE
        results = loop.run_ticks(3)
        assert len(results) == 3
        loop.stop()

    def test_session_persists_across_ticks(self):
        loop = RuntimeLoop()
        loop.start()
        session_before = loop.advisor.session_manager.get_active_session()
        loop.run_ticks(5)
        session_after = loop.advisor.session_manager.get_active_session()
        assert session_before.session_id == session_after.session_id
        loop.stop()

    def test_advisor_state_retrievable(self):
        advisor = AdvisorRuntime()
        advisor.start()
        advisor.spawn_worker(CellType.PLANNING, "task1")
        advisor.spawn_worker(CellType.REVIEW, "task2")
        state = advisor.get_state()
        assert len(state["spawned_cells"]) == 2
        assert state["session"] is not None
        advisor.stop()

    def test_workflow_through_orchestrator(self):
        exe = WorkflowExecutor()
        run_id = exe.execute_objective("orchestrated task")
        run = exe.orchestrator.get_run(run_id)
        assert run is not None
        assert len(run.step_cell_ids) >= 1
        exe.clear()


# ═══════════════════════════════════════════════════════════════════════
# Boundary (5)
# ═══════════════════════════════════════════════════════════════════════


class TestBoundary:
    _RUNTIME_MODULES = [
        "/opt/OS/umh/runtime/session.py",
        "/opt/OS/umh/runtime/advisor.py",
        "/opt/OS/umh/runtime/loop.py",
    ]

    _NODE_MODULES = [
        "/opt/OS/umh/nodes/registry.py",
        "/opt/OS/umh/nodes/routing.py",
    ]

    _WORKFLOW_MODULES = [
        "/opt/OS/umh/workflows/executor.py",
    ]

    def test_no_subprocess_in_runtime(self):
        for path in self._RUNTIME_MODULES:
            source = open(path).read()
            assert "import subprocess" not in source, f"subprocess import in {path}"

    def test_no_environment_imports_in_runtime(self):
        for path in self._RUNTIME_MODULES:
            source = open(path).read()
            assert "from umh.environments" not in source, f"environments import in {path}"

    def test_no_subprocess_in_workflows(self):
        for path in self._WORKFLOW_MODULES:
            source = open(path).read()
            assert "import subprocess" not in source, f"subprocess import in {path}"
            assert "from umh.environments" not in source, f"environments import in {path}"

    def test_no_cell_imports_in_session(self):
        source = open("/opt/OS/umh/runtime/session.py").read()
        assert "umh.cells" not in source

    def test_cells_still_cannot_import_environments(self):
        cell_modules = [
            "/opt/OS/umh/cells/models.py",
            "/opt/OS/umh/cells/runtime.py",
            "/opt/OS/umh/cells/router.py",
            "/opt/OS/umh/cells/workflow.py",
            "/opt/OS/umh/cells/orchestrator.py",
        ]
        for path in cell_modules:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""'):
                        continue
                    assert "umh.environments" not in stripped, (
                        f"Cell imports environments: {path}:{i}: {stripped}"
                    )


# ═══════════════════════════════════════════════════════════════════════
# Regression (5)
# ═══════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_cell_spawn_still_works(self):
        from umh.cells.runtime import spawn_cell, hydrate_cell, activate_cell
        from umh.cells.models import CellContext

        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="regress")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE

    def test_orchestrator_still_works(self):
        from umh.cells.orchestrator import CellOrchestrator
        from umh.cells.workflow import CellWorkflow, CellWorkflowStep, WorkflowStatus

        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_reg",
            objective="regression",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        assert run.status == WorkflowStatus.COMPLETED

    def test_signal_system_still_works(self):
        sig = emit_signal("regression_brain", "test", {"val": 1})
        assert sig.signal_id.startswith("bsig_")

    def test_environment_runtime_still_imports(self):
        from umh.environments import EnvironmentRuntime

        rt = EnvironmentRuntime()
        assert rt.registry is not None

    def test_telemetry_still_works(self):
        from umh.environments.telemetry import collect_local_telemetry

        t = collect_local_telemetry()
        assert t.cpu_percent >= 0.0
