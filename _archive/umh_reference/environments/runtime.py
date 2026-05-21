"""Environment runtime — real execution lifecycle.

Flow:
  PlanObjective → ExecutionTask → Sandbox.validate()
  → Telemetry check → Scheduler.select_node()
  → create ExecutionContext → ContainerManager.create_container()
  → run_task() → collect output → destroy container
  → cleanup sandbox → return ExecutionResult

Callable from the execution layer ONLY. Must NOT be imported in umh/cells.

No imports from umh/cells or umh/adapters.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.environments.containers import ContainerManager
from umh.environments.models import (
    EnvironmentPermissions,
    ExecutionContext,
    ExecutionIsolation,
    ExecutionResult,
    ExecutionTask,
    Node,
    ResourceRequirements,
    SandboxVerdict,
    TaskStatus,
    _gen_id,
)
from umh.environments.nodes import NodeRegistry
from umh.environments.sandbox import SandboxManager
from umh.environments.scheduler import select_node
from umh.environments.telemetry import NodeTelemetry, TelemetryCollector
from umh.core.clock import iso_now as _iso_now

_log = logging.getLogger(__name__)


class EnvironmentRuntime:
    """Full execution lifecycle: task → sandbox → telemetry → node → container → result → cleanup."""

    def __init__(
        self,
        registry: NodeRegistry | None = None,
        container_manager: ContainerManager | None = None,
        sandbox: SandboxManager | None = None,
        telemetry_collector: TelemetryCollector | None = None,
    ) -> None:
        self._registry = registry or NodeRegistry()
        self._containers = container_manager or ContainerManager()
        self._sandbox = sandbox or SandboxManager()
        self._telemetry = telemetry_collector or TelemetryCollector()

    @property
    def registry(self) -> NodeRegistry:
        return self._registry

    @property
    def container_manager(self) -> ContainerManager:
        return self._containers

    @property
    def sandbox(self) -> SandboxManager:
        return self._sandbox

    def execute(self, task: ExecutionTask) -> ExecutionResult:
        """Execute a task through the full environment lifecycle."""
        safety = self._sandbox.validate_task(task)
        if safety.verdict == SandboxVerdict.REJECTED:
            _log.warning("Task %s rejected by sandbox: %s", task.task_id, safety.reason)
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.REJECTED,
                output={"error": safety.reason},
                logs=[f"[sandbox] rejected: {safety.reason}"],
                finished_at=_iso_now(),
            )

        work_dir = safety.work_dir

        try:
            node = self._select_node(task)
            if node is None:
                _log.warning("No node available for task %s", task.task_id)
                return ExecutionResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    output={"error": "no available node"},
                    logs=["[scheduler] no node available"],
                    finished_at=_iso_now(),
                )

            context = self._create_context(node, task)
            container = self._containers.create_container(node.node_id, context)

            try:
                result = self._containers.run_task(container, task, work_dir=work_dir)
            except Exception as e:
                _log.error("Task %s failed: %s", task.task_id, e)
                result = ExecutionResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    output={"error": str(e)},
                    logs=[f"[runtime] exception: {e}"],
                    node_id=node.node_id,
                    container_id=container.container_id,
                    finished_at=_iso_now(),
                )
            finally:
                self._containers.destroy_container(container.container_id)

            return result

        finally:
            self._sandbox.cleanup_task(task.task_id)

    def _select_node(self, task: ExecutionTask) -> Node | None:
        nodes = self._registry.get_available_nodes()
        telemetry = self._collect_telemetry(nodes)
        return select_node(task, nodes, telemetry=telemetry)

    def _collect_telemetry(self, nodes: list[Node]) -> dict[str, NodeTelemetry] | None:
        if not nodes:
            return None
        try:
            local = self._telemetry.collect_local()
            result: dict[str, NodeTelemetry] = {}
            for n in nodes:
                result[n.node_id] = local
            return result
        except Exception as e:
            _log.debug("Telemetry collection failed: %s", e)
            return None

    def _create_context(self, node: Node, task: ExecutionTask) -> ExecutionContext:
        return ExecutionContext(
            context_id=_gen_id("ectx"),
            node_id=node.node_id,
            isolation=ExecutionIsolation.CONTAINER,
            permissions=EnvironmentPermissions(read=True, write=False, network=False),
            timeout_s=task.metadata.get("timeout_s", 30),
            metadata={"task_id": task.task_id, "operation": task.operation},
        )
