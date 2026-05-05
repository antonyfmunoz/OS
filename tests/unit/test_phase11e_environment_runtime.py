"""Phase 11E — Environment Runtime + Secure Execution Layer v1.

Tests covering:
  Nodes (5), Scheduler (6), Containers (5), Sandbox (5),
  Runtime (6), Integration (2), Boundary (4), Regression (3).
  Total: 36 tests.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from umh.environments.models import (
    ContainerStatus,
    EnvironmentPermissions,
    ExecutionContainer,
    ExecutionContext,
    ExecutionIsolation,
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
    )


# ─── Nodes (5) ───────────────────────────────────────────────────────


class TestNodeRegistry:
    def test_register_and_get(self):
        reg = NodeRegistry()
        node = _local_node(node_id="n1")
        reg.register_node(node)
        assert reg.get_node("n1") is node

    def test_unregister(self):
        reg = NodeRegistry()
        node = _local_node(node_id="n1")
        reg.register_node(node)
        assert reg.unregister_node("n1") is True
        assert reg.unregister_node("n1") is False
        assert reg.get_node("n1") is None

    def test_list_nodes(self):
        reg = NodeRegistry()
        reg.register_node(_local_node(node_id="n1"))
        reg.register_node(_vps_node(node_id="n2"))
        assert len(reg.list_nodes()) == 2

    def test_list_by_type(self):
        reg = NodeRegistry()
        reg.register_node(_local_node(node_id="n1"))
        reg.register_node(_vps_node(node_id="n2"))
        local = reg.list_nodes(node_type=NodeType.LOCAL)
        assert len(local) == 1
        assert local[0].node_id == "n1"

    def test_get_available_nodes(self):
        reg = NodeRegistry()
        reg.register_node(_local_node(node_id="n1"))
        reg.register_node(_local_node(node_id="n2", status=NodeStatus.OFFLINE))
        available = reg.get_available_nodes()
        assert len(available) == 1
        assert available[0].node_id == "n1"


# ─── Scheduler (6) ──────────────────────────────────────────────────


class TestScheduler:
    def test_selects_local_when_available(self):
        nodes = [_local_node(), _vps_node()]
        task = _task(latency_sensitive=True)
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_type == NodeType.LOCAL

    def test_falls_back_to_vps_when_local_overloaded(self):
        nodes = [_local_node(load=0.95), _vps_node(load=0.2)]
        task = _task(latency_sensitive=True)
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_type == NodeType.VPS

    def test_no_nodes_returns_none(self):
        result = select_node(_task(), [])
        assert result is None

    def test_all_offline_returns_none(self):
        nodes = [_local_node(status=NodeStatus.OFFLINE)]
        result = select_node(_task(), nodes)
        assert result is None

    def test_resource_requirements_filter(self):
        heavy = ResourceRequirements(cpu_cores=16.0, memory_mb=65536)
        task = _task(resources=heavy)
        nodes = [_local_node(cpu_cores=8.0, memory_mb=16384)]
        result = select_node(task, nodes)
        assert result is None

    def test_environment_preference_honored(self):
        nodes = [_local_node(node_id="n1"), _vps_node(node_id="n2")]
        task = _task(environment_preference=NodeType.VPS)
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_type == NodeType.VPS


# ─── Containers (5) ─────────────────────────────────────────────────


class TestContainerManager:
    def test_create_container(self):
        cm = ContainerManager()
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        assert container.container_id.startswith("ctr_")
        assert container.status == ContainerStatus.CREATED

    def test_run_task_succeeds(self):
        cm = ContainerManager()
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        task = _task()
        result = cm.run_task(container, task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.container_id == container.container_id

    def test_destroy_container(self):
        cm = ContainerManager()
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        assert cm.destroy_container(container.container_id) is True
        got = cm.get_container(container.container_id)
        assert got.status == ContainerStatus.TERMINATED

    def test_run_on_terminated_fails(self):
        cm = ContainerManager()
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        container = cm.create_container("n1", ctx)
        cm.destroy_container(container.container_id)
        result = cm.run_task(container, _task())
        assert result.status == TaskStatus.FAILED

    def test_unique_container_ids(self):
        cm = ContainerManager()
        ctx = ExecutionContext(
            context_id="ctx1", node_id="n1", isolation=ExecutionIsolation.CONTAINER
        )
        c1 = cm.create_container("n1", ctx)
        c2 = cm.create_container("n1", ctx)
        assert c1.container_id != c2.container_id


# ─── Sandbox (5) ────────────────────────────────────────────────────


class TestSandboxManager:
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
        assert "dangerous" in decision.reason

    def test_manual_reject(self):
        sm = SandboxManager()
        task = _task()
        decision = sm.reject_execution(task, "not today")
        assert decision.verdict == SandboxVerdict.REJECTED
        assert decision.reason == "not today"

    def test_custom_validator(self):
        sm = SandboxManager()

        def block_if_test(task: ExecutionTask) -> SandboxDecision | None:
            if task.operation == "test_blocked":
                return SandboxDecision(
                    verdict=SandboxVerdict.REJECTED,
                    task_id=task.task_id,
                    reason="custom block",
                )
            return None

        sm.register_validator(block_if_test)
        assert sm.validate_task(_task(operation="test_blocked")).verdict == SandboxVerdict.REJECTED
        assert sm.validate_task(_task(operation="safe")).verdict == SandboxVerdict.APPROVED

    def test_decisions_logged(self):
        sm = SandboxManager()
        sm.validate_task(_task(operation="a"))
        sm.validate_task(_task(operation="b"))
        assert len(sm.list_decisions()) == 2


# ─── Runtime (6) ────────────────────────────────────────────────────


class TestEnvironmentRuntime:
    def _runtime_with_node(self) -> EnvironmentRuntime:
        rt = EnvironmentRuntime()
        rt.registry.register_node(_local_node(node_id="n1"))
        return rt

    def test_execute_completes(self):
        rt = self._runtime_with_node()
        task = _task()
        result = rt.execute(task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.node_id == "n1"

    def test_result_has_container_id(self):
        rt = self._runtime_with_node()
        result = rt.execute(_task())
        assert result.container_id is not None
        assert result.container_id.startswith("ctr_")

    def test_container_destroyed_after_execution(self):
        rt = self._runtime_with_node()
        result = rt.execute(_task())
        container = rt.container_manager.get_container(result.container_id)
        assert container.status == ContainerStatus.TERMINATED

    def test_no_node_returns_failed(self):
        rt = EnvironmentRuntime()
        result = rt.execute(_task())
        assert result.status == TaskStatus.FAILED
        assert "no available node" in result.output.get("error", "")

    def test_dangerous_task_rejected_by_sandbox(self):
        rt = self._runtime_with_node()
        task = _task(operation="drop_table")
        result = rt.execute(task)
        assert result.status == TaskStatus.REJECTED

    def test_correct_node_selected(self):
        nodes = [_local_node(node_id="local1", load=0.9), _vps_node(node_id="vps1", load=0.1)]
        task = _task()
        chosen = select_node(task, nodes)
        assert chosen is not None
        assert chosen.node_id == "vps1"


# ─── Integration (2) ────────────────────────────────────────────────


class TestIntegration:
    def test_full_flow_plan_objective_to_result(self):
        rt = EnvironmentRuntime()
        rt.registry.register_node(_local_node(node_id="n1"))
        task = ExecutionTask(
            task_id="task_int_1",
            plan_objective_id="plan_obj_42",
            operation="classify",
            resources=ResourceRequirements(cpu_cores=2.0, memory_mb=1024),
        )
        result = rt.execute(task)
        assert result.status == TaskStatus.SUCCEEDED
        assert result.task_id == "task_int_1"
        assert result.node_id == "n1"
        assert result.finished_at != ""

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


# ─── Boundary (4) ───────────────────────────────────────────────────


class TestBoundary:
    _ENV_MODULES = [
        "/opt/OS/umh/environments/models.py",
        "/opt/OS/umh/environments/nodes.py",
        "/opt/OS/umh/environments/scheduler.py",
        "/opt/OS/umh/environments/containers.py",
        "/opt/OS/umh/environments/sandbox.py",
        "/opt/OS/umh/environments/runtime.py",
    ]

    _FORBIDDEN_IMPORT_PATTERNS = [
        "from umh.cells",
        "from umh.adapters",
    ]

    _SUBPROCESS_FORBIDDEN_MODULES = [
        "/opt/OS/umh/environments/models.py",
        "/opt/OS/umh/environments/nodes.py",
        "/opt/OS/umh/environments/scheduler.py",
        "/opt/OS/umh/environments/sandbox.py",
        "/opt/OS/umh/environments/runtime.py",
    ]

    def test_no_forbidden_imports(self):
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
                for pattern in self._FORBIDDEN_IMPORT_PATTERNS:
                    assert pattern not in stripped, f"'{pattern}' found in {path}: {stripped}"

    def test_subprocess_only_in_containers(self):
        for path in self._SUBPROCESS_FORBIDDEN_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            assert "import subprocess" not in source, (
                f"subprocess import found outside containers.py: {path}"
            )

    def test_no_shell_true(self):
        for path in self._ENV_MODULES:
            if not os.path.isfile(path):
                continue
            with open(path) as f:
                source = f.read()
            assert "shell=True" not in source, f"shell=True found in {path}"

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


# ─── Regression (3) ─────────────────────────────────────────────────


class TestRegression:
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
