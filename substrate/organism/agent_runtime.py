"""Agent base runtime — the foundational behavior of every agent in the society.

Every agent:
1. Receives a task (AgentMessage with intent=delegate_task)
2. Spawns a worker cell to execute bounded work
3. Self-critiques the result (score 1-10)
4. If critique fails and iterations remain, re-executes with critique as feedback
5. Posts Deliverable to store + learning channel
6. Returns result to caller
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.organism.protocols import (
    AgentMessage,
    AgentStatus,
    CritiqueResult,
    Deliverable,
    LearningSignal,
    WorkerSpec,
)
from substrate.organism.store import OrganismStore
from substrate.organism.worker_cell import WorkerCell

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        soul_doc: str,
        store: OrganismStore,
        worker: WorkerCell | None = None,
        max_critique_iterations: int = 2,
        critique_threshold: int = 7,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.soul_doc = soul_doc
        self._store = store
        self._worker = worker or WorkerCell()
        self._max_iterations = max_critique_iterations
        self._critique_threshold = critique_threshold
        self._status = AgentStatus.IDLE
        self._tasks_completed = 0

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def tasks_completed(self) -> int:
        return self._tasks_completed

    def handle_task(self, msg: AgentMessage) -> Deliverable | None:
        if msg.intent != "delegate_task":
            logger.warning("agent %s received unknown intent: %s", self.agent_id, msg.intent)
            return None

        self._status = AgentStatus.WORKING
        task = msg.payload.get("task", "")
        adapter = msg.payload.get("adapter", "shell")
        operation = msg.payload.get("operation", "query")
        params = msg.payload.get("params", {})
        tools = msg.payload.get("tools", [adapter])

        best_result: str | None = None
        best_critique: CritiqueResult | None = None

        for iteration in range(1, self._max_iterations + 1):
            self._status = AgentStatus.WORKING

            spec = WorkerSpec(
                parent_agent_id=self.agent_id,
                task=task,
                environment_id="vps-prod",
                tools=tools,
                model_tier="sonnet",
                risk_class=msg.payload.get("risk_class", "READ_ONLY"),
            )

            pipeline_result = self._worker.execute(
                spec,
                adapter_name=adapter,
                operation=operation,
                params=params,
            )

            if pipeline_result.success:
                result_content = f"Execution successful (trace: {pipeline_result.trace_id})"
            else:
                result_content = f"Execution completed with issues (trace: {pipeline_result.trace_id})"

            self._status = AgentStatus.CRITIQUING
            critique = self._self_critique(task, result_content, iteration)

            if best_critique is None or critique.score > best_critique.score:
                best_result = result_content
                best_critique = critique

            if critique.passed:
                break

            if iteration < self._max_iterations:
                params = {**params, "_critique_feedback": critique.reasoning}
                logger.info(
                    "agent %s critique failed (score=%d), iterating (%d/%d)",
                    self.agent_id,
                    critique.score,
                    iteration,
                    self._max_iterations,
                )

        if best_result is None or best_critique is None:
            raise RuntimeError("Agent execution loop completed without producing a result")

        deliverable = Deliverable(
            agent_id=self.agent_id,
            task_id=str(msg.id),
            content=best_result,
            self_critique=best_critique,
            parent_trace_id=pipeline_result.trace_id,
        )

        self._store.save_deliverable(deliverable)

        learning = LearningSignal(
            agent_id=self.agent_id,
            deliverable_id=str(deliverable.id),
            pattern_observed=f"task={task[:100]}, critique_score={best_critique.score}",
            confidence=best_critique.score / 10.0,
        )
        self._store.save_learning_signal(learning)

        self._tasks_completed += 1
        self._status = AgentStatus.IDLE

        self._persist_state()

        return deliverable

    def _self_critique(self, task: str, result: str, iteration: int) -> CritiqueResult:
        has_content = bool(result and "successful" in result.lower())
        addresses_task = bool(task and len(result) > 20)

        score = 5
        if has_content:
            score += 2
        if addresses_task:
            score += 2
        if "blocked" in result.lower():
            score -= 3

        score = max(1, min(10, score))

        return CritiqueResult(
            score=score,
            reasoning=f"iteration {iteration}: content={'present' if has_content else 'missing'}, "
            f"task_relevance={'yes' if addresses_task else 'no'}",
            iteration=iteration,
            threshold=self._critique_threshold,
        )

    def _persist_state(self) -> None:
        self._store.save_agent_state(
            self.agent_id,
            {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "status": self._status.value,
                "tasks_completed": self._tasks_completed,
            },
        )

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self._status.value,
            "tasks_completed": self._tasks_completed,
        }
