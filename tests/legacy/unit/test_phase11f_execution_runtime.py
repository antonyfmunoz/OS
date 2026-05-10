"""Phase 11F — Real Execution + Distributed Node Runtime v1.

Tests covering:
  Telemetry (3), Scheduler (5), Containers (7), Sandbox (6),
  Runtime (5), Timeout (3), Integration (2), Boundary (5), Regression (4).
  Total: 40 tests.
"""

from __future__ import annotations

import os
import signal
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from umh.environments.models import (
    ContainerStatus,
    EnvironmentPermissions,
    ExecutionContainer,
    ExecutionContext,
    ExecutionIsolation,
    ExecutionMode,
    ExecutionResult,
    ExecutionTask,
    Node,
    NodeStatus,
    NodeType,
    ResourceRequirements,
    SandboxVerdict,
    TaskStatus,
    _gen_id,
)
from umh.environments.nodes import NodeRegistry
from umh.environments.scheduler import select_node
from umh.environments.containers import ContainerManager
from umh.environments.sandbox import SandboxDecision, SandboxManager
from umh.environments.runtime import EnvironmentRuntime
from umh.environments.telemetry import NodeTelemetry, TelemetryCollector, collect_local_telemetry


# ─── Helpers ─────────────────────────────────────────────────────────


def _local_node(load: float = 0.0, **kw) -> Node:
    return Node(
        node_id=kw.get("node_id", _gen_id("node")),
        node_type=NodeType.LOCAL,
        cpu_cores=kw.get("cpu_cores", 8.0),
        memory_mb=kw.get("memory_mb", 16384),
        current_load=load,
        status=kw.get("status", NodeStatus.AVAILABLE),
    )


def _vps_node(load: float = 0.0, **kw) -> Node:
    return Node(
        node_id=kw.get("node_id", _gen_id("node")),
        node_type=NodeType.VPS,
        cpu_cores=kw.get("cpu_cores", 4.0),
        memory_mb=kw.get("memory_mb", 8192),
        current_load=load,
        status=kw.get("status", NodeStatus.AVAILABLE),
    )


def _task(operation: str = "analyze", **kw) -> ExecutionTask:
    return ExecutionTask(
        task_id=kw.get("task_id", _gen_id("task")),
        plan_objective_id=kw.get("plan_objective_id", "obj_1"),
        operation=operation,
        resources=kw.get("resources", ResourceRequirements()),
        priority=kw.get("priority", 0),
        latency_sensitive=kw.get("latency_sensitive", False),
        environment_preference=kw.get("environment_preference", None),
        inputs=kw.get("inputs", {}),
        metadata=kw.get("metadata", {}),
    )


# ═══════════════════════════════════════════════════════════════════════
# Telemetry (3)
# ═══════════════════════════════════════════════════════════════════════


class TestTelemetry:
    def test_local_telemetry_returns_valid_values(self):
        t = collect_local_telemetry()
        assert 0.0 <= t.cpu_percent <= 100.0
        assert 0.0 <= t.memory_percent <= 100.0
        assert t.memory_available_mb >= 0
        assert t.load_avg_1m >= 0.0
        assert t.collected_at != ""
        assert t.source in ("psutil", "proc")

    def test_telemetry_collector_class(self):
        tc = TelemetryCollector()
        t = tc.collect_local()
        assert isinstance(t, NodeTelemetry)
        assert t.cpu_percent >= 0.0

    def test_telemetry_to_dict(self):
        t = collect_local_telemetry()
        d = t.to_dict()
        assert "cpu_percent" in d
        assert "memory_percent" in d
        assert "memory_available_mb" in d
        assert "load_avg_1m" in d
        assert "collected_at" in d
        assert "source" in d


# ═══════════════════════════════════════════════════════════════════════
# Scheduler (5)
# ═══════════════════════════════════════════════════════════════════════


class TestSchedulerUpgrade:
    def test_selects_lowest_load_node(self):
        nodes = [_local_node(load=0.7, node_id="n1"), _vps_node(load=0.2, node_id="n2")]
        task = _task()
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_id == "n2"

    def test_respects_local_preference_when_low_load(self):
        nodes = [_local_node(load=0.3, node_id="local"), _vps_node(load=0.1, node_id="vps")]
        task = _task(latency_sensitive=True)
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_id == "local"

    def test_falls_back_to_vps_when_local_overloaded(self):
        nodes = [_local_node(load=0.95, node_id="local"), _vps_node(load=0.2, node_id="vps")]
        task = _task(latency_sensitive=True)
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_id == "vps"

    def test_telemetry_informed_selection(self):
        n1 = _local_node(load=0.1, node_id="n1")
        n2 = _vps_node(load=0.1, node_id="n2")
        telemetry = {
            "n1": NodeTelemetry(cpu_percent=90.0, memory_percent=80.0),
            "n2": NodeTelemetry(cpu_percent=20.0, memory_percent=30.0),
        }
        chosen = select_node(_task(), [n1, n2], telemetry=telemetry)
        assert chosen is not None
        assert chosen.node_id == "n2"

    def test_telemetry_filters_high_memory_node(self):
        n1 = _local_node(load=0.1, node_id="n1")
        telemetry = {
            "n1": NodeTelemetry(cpu_percent=10.0, memory_percent=95.0, memory_available_mb=100),
        }
        heavy_task = _task(resources=ResourceRequirements(memory_mb=200))
        chosen = select_node(heavy_task, [n1], telemetry=telemetry)
        assert chosen is None


# ═══════════════════════════════════════════════════════════════════════
# Containers (7)
# ═══════════════════════════════════════════════════════════════════════


class TestContainerManager:
    def test_subprocess_execution_works(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(inputs={"command": ["echo", "hello"]})
        result = cm.run_task(container, task)
        assert result.status == TaskStatus.SUCCEEDED
        assert "hello" in result.output.get("stdout", "")
        assert result.output["mode"] == "subprocess"

    def test_subprocess_captures_stderr(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(
            inputs={"command": ["python3", "-c", "import sys; sys.stderr.write('err\\n')"]}
        )
        result = cm.run_task(container, task)
        assert "err" in result.output.get("stderr", "")

    def test_subprocess_nonzero_exit_is_failed(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(inputs={"command": ["python3", "-c", "raise SystemExit(1)"]})
        result = cm.run_task(container, task)
        assert result.status == TaskStatus.FAILED
        assert result.output["return_code"] == 1

    def test_no_command_returns_simulated(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task()
        result = cm.run_task(container, task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.output.get("simulated") is True

    def test_run_on_terminated_fails(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        cm.destroy_container(container.container_id)
        result = cm.run_task(container, _task(inputs={"command": ["echo", "x"]}))
        assert result.status == TaskStatus.FAILED

    def test_destroy_container_terminates(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        assert cm.destroy_container(container.container_id) is True
        got = cm.get_container(container.container_id)
        assert got.status == ContainerStatus.TERMINATED

    def test_execution_mode_detected(self):
        cm = ContainerManager()
        assert cm.mode in (ExecutionMode.DOCKER, ExecutionMode.SUBPROCESS)


# ═══════════════════════════════════════════════════════════════════════
# Timeout (3)
# ═══════════════════════════════════════════════════════════════════════


class TestTimeout:
    def test_timeout_kills_process(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(
            inputs={"command": ["sleep", "30"]},
            metadata={"timeout_s": 1},
        )
        start = time.monotonic()
        result = cm.run_task(container, task)
        elapsed = time.monotonic() - start
        assert result.status == TaskStatus.FAILED
        assert "timeout" in result.output.get("error", "")
        assert elapsed < 10

    def test_timeout_metadata_set(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(
            inputs={"command": ["sleep", "30"]},
            metadata={"timeout_s": 1},
        )
        result = cm.run_task(container, task)
        assert result.metadata.get("timed_out") is True

    def test_system_does_not_hang(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task(
            inputs={"command": ["python3", "-c", "import time; time.sleep(60)"]},
            metadata={"timeout_s": 2},
        )
        start = time.monotonic()
        result = cm.run_task(container, task)
        elapsed = time.monotonic() - start
        assert elapsed < 15
        assert result.status == TaskStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════
# Sandbox (6)
# ═══════════════════════════════════════════════════════════════════════


class TestSandboxUpgrade:
    def test_safe_task_approved(self):
        sm = SandboxManager()
        task = _task(operation="analyze")
        decision = sm.validate_task(task)
        assert decision.verdict == SandboxVerdict.APPROVED

    def test_dangerous_task_rejected(self):
        sm = SandboxManager()
        task = _task(operation="rm_rf")
        decision = sm.validate_task(task)
        assert decision.verdict == SandboxVerdict.REJECTED

    def test_creates_temp_directory(self):
        sm = SandboxManager()
        task = _task(task_id="sandbox_test_1")
        decision = sm.validate_task(task)
        assert decision.verdict == SandboxVerdict.APPROVED
        assert decision.work_dir is not None
        work_path = Path(decision.work_dir)
        assert work_path.exists()
        assert work_path.is_dir()
        sm.cleanup_task("sandbox_test_1")
        assert not work_path.exists()

    def test_cleans_temp_directory(self):
        sm = SandboxManager()
        task = _task(task_id="sandbox_test_2")
        decision = sm.validate_task(task)
        work_dir = Path(decision.work_dir)
        (work_dir / "testfile.txt").write_text("data")
        sm.cleanup_task("sandbox_test_2")
        assert not work_dir.exists()

    def test_rejects_excessive_timeout(self):
        sm = SandboxManager()
        task = _task(metadata={"timeout_s": 9999})
        decision = sm.validate_task(task)
        assert decision.verdict == SandboxVerdict.REJECTED
        assert "exceeds maximum" in decision.reason

    def test_rejects_invalid_timeout(self):
        sm = SandboxManager()
        task = _task(metadata={"timeout_s": -5})
        decision = sm.validate_task(task)
        assert decision.verdict == SandboxVerdict.REJECTED
        assert "Invalid timeout" in decision.reason


# ═══════════════════════════════════════════════════════════════════════
# Runtime (5)
# ═══════════════════════════════════════════════════════════════════════


class TestRuntimeUpgrade:
    def _runtime_with_node(self) -> EnvironmentRuntime:
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        rt = EnvironmentRuntime(container_manager=cm)
        rt.registry.register_node(_local_node(node_id="n1"))
        return rt

    def test_full_execution_flow(self):
        rt = self._runtime_with_node()
        task = _task(inputs={"command": ["echo", "real-output"]})
        result = rt.execute(task)
        assert result.status == TaskStatus.SUCCEEDED
        assert "real-output" in result.output.get("stdout", "")

    def test_result_returned_correctly(self):
        rt = self._runtime_with_node()
        task = _task(task_id="rt_test_1", inputs={"command": ["echo", "data"]})
        result = rt.execute(task)
        assert result.task_id == "rt_test_1"
        assert result.node_id == "n1"
        assert result.container_id is not None

    def test_failure_path_handled(self):
        rt = self._runtime_with_node()
        task = _task(inputs={"command": ["python3", "-c", "raise SystemExit(42)"]})
        result = rt.execute(task)
        assert result.status == TaskStatus.FAILED
        assert result.output["return_code"] == 42

    def test_timeout_path_handled(self):
        rt = self._runtime_with_node()
        task = _task(
            inputs={"command": ["sleep", "30"]},
            metadata={"timeout_s": 1},
        )
        result = rt.execute(task)
        assert result.status == TaskStatus.FAILED
        assert "timeout" in result.output.get("error", "")

    def test_sandbox_cleanup_after_execution(self):
        sm = SandboxManager()
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        rt = EnvironmentRuntime(container_manager=cm, sandbox=sm)
        rt.registry.register_node(_local_node(node_id="n1"))
        task = _task(task_id="cleanup_test", inputs={"command": ["echo", "x"]})
        rt.execute(task)
        assert sm.get_work_dir("cleanup_test") is None


# ═══════════════════════════════════════════════════════════════════════
# Integration (2)
# ═══════════════════════════════════════════════════════════════════════


class TestIntegrationF:
    def test_full_flow_plan_objective_to_real_result(self):
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        rt = EnvironmentRuntime(container_manager=cm)
        rt.registry.register_node(_local_node(node_id="n1"))
        task = ExecutionTask(
            task_id="task_int_f1",
            plan_objective_id="plan_obj_99",
            operation="classify",
            resources=ResourceRequirements(cpu_cores=2.0, memory_mb=1024),
            inputs={"command": ["python3", "-c", "print('classified')"]},
        )
        result = rt.execute(task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.task_id == "task_int_f1"
        assert "classified" in result.output.get("stdout", "")

    def test_cells_cannot_import_environments(self):
        cell_modules = [
            "/opt/OS/umh/cells/models.py",
            "/opt/OS/umh/cells/runtime.py",
            "/opt/OS/umh/cells/router.py",
            "/opt/OS/umh/cells/workflow.py",
            "/opt/OS/umh/cells/orchestrator.py",
            "/opt/OS/umh/cells/persistence.py",
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
                        f"Cell module imports environments: {path}:{i}: {stripped}"
                    )


# ═══════════════════════════════════════════════════════════════════════
# Boundary (5)
# ═══════════════════════════════════════════════════════════════════════


class TestBoundaryF:
    _ENV_MODULES = [
        "/opt/OS/umh/environments/models.py",
        "/opt/OS/umh/environments/nodes.py",
        "/opt/OS/umh/environments/scheduler.py",
        "/opt/OS/umh/environments/containers.py",
        "/opt/OS/umh/environments/sandbox.py",
        "/opt/OS/umh/environments/runtime.py",
        "/opt/OS/umh/environments/telemetry.py",
    ]

    def test_no_cell_imports_in_environments(self):
        for path in self._ENV_MODULES:
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
                assert "from umh.cells" not in stripped, (
                    f"'from umh.cells' found in {path}: {stripped}"
                )
                assert "from umh.adapters" not in stripped, (
                    f"'from umh.adapters' found in {path}: {stripped}"
                )

    def test_no_shell_true_in_environments(self):
        for path in self._ENV_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            assert "shell=True" not in source, f"shell=True found in {path}"

    def test_subprocess_only_in_containers(self):
        non_container_modules = [
            "/opt/OS/umh/environments/models.py",
            "/opt/OS/umh/environments/nodes.py",
            "/opt/OS/umh/environments/scheduler.py",
            "/opt/OS/umh/environments/sandbox.py",
            "/opt/OS/umh/environments/runtime.py",
        ]
        for path in non_container_modules:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            assert "import subprocess" not in source, (
                f"subprocess import found outside containers.py: {path}"
            )

    def test_no_direct_system_calls(self):
        forbidden = ["os" + "." + "system", "os" + "." + "popen"]
        for path in self._ENV_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            for pattern in forbidden:
                assert pattern not in source, f"Direct system call found in {path}"

    def test_cell_modules_still_clean(self):
        cell_paths = [
            "/opt/OS/umh/cells/models.py",
            "/opt/OS/umh/cells/runtime.py",
            "/opt/OS/umh/cells/orchestrator.py",
        ]
        forbidden = ["import subprocess", "from umh.execution", "from umh.adapters"]
        for path in cell_paths:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                for pattern in forbidden:
                    assert pattern not in stripped, f"'{pattern}' in {path}: {stripped}"


# ═══════════════════════════════════════════════════════════════════════
# Regression (4)
# ═══════════════════════════════════════════════════════════════════════


class TestRegressionF:
    def test_cell_spawn_still_works(self):
        from umh.cells.runtime import clear as clear_cells, spawn_cell
        from umh.cells.models import CellType, CellStatus
        from umh.cells.runtime import get_cell_status, hydrate_cell, activate_cell
        from umh.cells.models import CellContext

        clear_cells()
        identity = spawn_cell(CellType.PLANNING)
        ctx = CellContext(cell_id=identity.cell_id, objective="regress")
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)
        assert get_cell_status(identity.cell_id) == CellStatus.ACTIVE
        clear_cells()

    def test_orchestrator_still_works(self):
        from umh.cells.runtime import clear as clear_cells
        from umh.cells.orchestrator import CellOrchestrator
        from umh.cells.workflow import CellWorkflow, CellWorkflowStep, WorkflowStatus
        from umh.cells.models import CellType

        clear_cells()
        orch = CellOrchestrator()
        wf = CellWorkflow(
            workflow_id="wf_reg",
            objective="regression",
            steps=[CellWorkflowStep(step_id="s1", cell_type=CellType.PLANNING, objective="plan")],
        )
        run = orch.start_workflow(wf)
        orch.complete_step(run.run_id, "s1")
        assert run.status == WorkflowStatus.COMPLETED
        clear_cells()

    def test_signal_router_still_works(self):
        from umh.cells.router import SignalRouter, SignalRoute, RoutingAction

        router = SignalRouter()
        route = SignalRoute(route_id="r1", source_signal_type="test", action=RoutingAction.NOTIFY)
        router.register_route(route)
        decisions = router.route_signal("test", {})
        assert len(decisions) == 1

    def test_11e_simulated_path_still_works(self):
        """Backward compat: tasks with no command still return simulated success."""
        cm = ContainerManager(mode=ExecutionMode.SUBPROCESS)
        rt = EnvironmentRuntime(container_manager=cm)
        rt.registry.register_node(_local_node(node_id="n1"))
        task = _task()
        result = rt.execute(task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.output.get("simulated") is True
