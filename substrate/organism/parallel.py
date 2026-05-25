"""Parallel agent execution — run multiple agents concurrently.

Uses concurrent.futures.ThreadPoolExecutor for parallel agent task
execution. Each agent runs in its own thread with isolated state.

The ParallelCoordinator handles:
  - Spawning N agents for independent tasks
  - Collecting results with timeout enforcement
  - Aggregating deliverables into a single coordination result
  - Cancellation of remaining work if a critical task fails
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from substrate.organism.protocols import AgentMessage, Deliverable

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 4
DEFAULT_TIMEOUT_S = 120.0


@dataclass
class ParallelTask:
    """A single task within a parallel execution batch."""

    task_id: str = ""
    agent_id: str = ""
    task: str = ""
    adapter: str = "shell"
    operation: str = "query"
    params: dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    risk_class: str = "READ_ONLY"

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = f"pt-{uuid4().hex[:8]}"


@dataclass
class ParallelResult:
    """Aggregated result from a parallel execution batch."""

    batch_id: str = ""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    timed_out: int = 0
    results: dict[str, Deliverable | None] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    duration_ms: float = 0.0

    def success_rate(self) -> float:
        return self.completed / self.total_tasks if self.total_tasks > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "success_rate": round(self.success_rate(), 3),
            "duration_ms": round(self.duration_ms, 1),
            "errors": self.errors,
        }


class ParallelCoordinator:
    """Executes multiple agent tasks in parallel using a thread pool."""

    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._max_workers = max_workers
        self._timeout_s = timeout_s
        self._batches_run = 0

    def execute_batch(
        self,
        tasks: list[ParallelTask],
        agent_factory: Any = None,
        fail_fast: bool = False,
    ) -> ParallelResult:
        """Execute a batch of tasks in parallel.

        Args:
            tasks: list of ParallelTask definitions
            agent_factory: callable(agent_id) -> AgentRuntime instance.
                           If None, uses organism default agents.
            fail_fast: if True, cancel remaining tasks on first failure
        """
        t0 = time.monotonic()
        batch_id = f"batch-{uuid4().hex[:8]}"
        self._batches_run += 1

        result = ParallelResult(
            batch_id=batch_id,
            total_tasks=len(tasks),
        )

        if not tasks:
            return result

        worker_count = min(self._max_workers, len(tasks))

        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            future_map: dict[Future, ParallelTask] = {}

            for task in tasks:
                future = pool.submit(
                    self._execute_single,
                    task,
                    agent_factory,
                )
                future_map[future] = task

            try:
                for future in as_completed(future_map, timeout=self._timeout_s):
                    ptask = future_map[future]
                    try:
                        deliverable = future.result()
                        result.results[ptask.task_id] = deliverable
                        result.completed += 1
                        logger.info(
                            "parallel task %s completed (agent=%s)",
                            ptask.task_id,
                            ptask.agent_id,
                        )
                    except Exception as e:
                        result.errors[ptask.task_id] = str(e)[:200]
                        result.failed += 1
                        logger.warning(
                            "parallel task %s failed: %s",
                            ptask.task_id,
                            e,
                        )
                        if fail_fast:
                            for f in future_map:
                                f.cancel()
                            break

            except TimeoutError:
                for future, ptask in future_map.items():
                    if not future.done():
                        result.timed_out += 1
                        result.errors[ptask.task_id] = f"timed out after {self._timeout_s}s"
                        future.cancel()

        result.duration_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "batch %s: %d/%d completed, %d failed, %d timed out (%.0fms)",
            batch_id,
            result.completed,
            result.total_tasks,
            result.failed,
            result.timed_out,
            result.duration_ms,
        )
        return result

    def _execute_single(
        self,
        task: ParallelTask,
        agent_factory: Any,
    ) -> Deliverable | None:
        """Execute a single task, creating an agent if needed."""
        from substrate.organism.store import OrganismStore

        if agent_factory is not None:
            agent = agent_factory(task.agent_id)
        else:
            from substrate.organism.agents import create_researcher, create_builder

            store = OrganismStore()
            if task.operation in ("query", "research", "analyze"):
                agent = create_researcher(store)
            else:
                agent = create_builder(store)

        msg = AgentMessage(
            sender="parallel_coordinator",
            recipient=task.agent_id,
            intent="delegate_task",
            payload={
                "task": task.task,
                "adapter": task.adapter,
                "operation": task.operation,
                "params": task.params,
                "risk_class": task.risk_class,
                "priority": task.priority,
            },
        )

        return agent.handle_task(msg)

    def stats(self) -> dict[str, Any]:
        return {
            "max_workers": self._max_workers,
            "timeout_s": self._timeout_s,
            "batches_run": self._batches_run,
        }
