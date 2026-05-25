"""DEX Advisor cell — the top-level orchestrator of the organism."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from substrate.organism.agents import create_auto_research, create_builder, create_researcher
from substrate.organism.agent_runtime import AgentRuntime
from substrate.organism.handoff import HandoffRequest, HandoffRouter, HandoffType
from substrate.organism.parallel import ParallelCoordinator, ParallelTask
from substrate.organism.delegation_followup import DelegationFollowup
from substrate.organism.protocols import AgentMessage, Deliverable
from substrate.organism.store import OrganismStore
from substrate.organism.worker_cell import WorkerCell
from substrate.sockets.envelopes import ViewFrame

logger = logging.getLogger(__name__)

BUILD_KEYWORDS = {
    "create",
    "write",
    "edit",
    "modify",
    "add",
    "fix",
    "implement",
    "build",
    "update",
    "refactor",
    "delete",
    "remove",
}
RESEARCH_KEYWORDS = {
    "audit",
    "find",
    "search",
    "check",
    "analyze",
    "investigate",
    "look",
    "review",
    "scan",
    "list",
    "show",
    "read",
    "examine",
    "inspect",
}


class Advisor:
    def __init__(
        self,
        store: OrganismStore | None = None,
        worker: WorkerCell | None = None,
        view_socket: Any = None,
    ) -> None:
        self._store = store or OrganismStore()
        self._worker = worker or WorkerCell()
        self._view_socket = view_socket
        self._agents: dict[str, AgentRuntime] = {}
        self._handoff_router = HandoffRouter()
        self._parallel = ParallelCoordinator()
        self._delegation_followup = DelegationFollowup()
        self._init_agents()

    def _init_agents(self) -> None:
        self._agents["researcher"] = create_researcher(self._store, self._worker)
        self._agents["builder"] = create_builder(self._store, self._worker)
        self._agents["auto-research"] = create_auto_research(self._store, self._worker)

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.to_status_dict() for agent in self._agents.values()]

    def handle_signal(self, content: str) -> dict[str, Any]:
        agent_id = self._route_to_agent(content)
        agent = self._agents.get(agent_id)
        if agent is None:
            return {"error": f"no agent found for: {content[:100]}"}

        self._emit_event(
            "organism.signal_received",
            {
                "content": content[:200],
                "routed_to": agent_id,
            },
        )

        adapter, operation, params = self._decompose_to_execution(content, agent_id)

        msg = AgentMessage(
            sender="advisor",
            recipient=agent_id,
            intent="delegate_task",
            payload={
                "task": content,
                "adapter": adapter,
                "operation": operation,
                "params": params,
                "tools": [adapter],
                "risk_class": "READ_ONLY" if agent_id == "researcher" else "REVERSIBLE_WRITE",
            },
        )

        self._store.save_message(msg)

        self._emit_event(
            "organism.task_delegated",
            {
                "agent_id": agent_id,
                "task": content[:200],
                "message_id": str(msg.id),
            },
        )

        deliverable = agent.handle_task(msg)

        self._emit_event(
            "organism.deliverable_produced",
            {
                "agent_id": agent_id,
                "deliverable_id": str(deliverable.id) if deliverable else None,
                "critique_score": deliverable.self_critique.score if deliverable else None,
                "critique_passed": deliverable.self_critique.passed if deliverable else None,
            },
        )

        result = {
            "signal": content,
            "delegated_to": agent_id,
            "deliverable": deliverable.model_dump(mode="json") if deliverable else None,
            "trace_id": str(deliverable.parent_trace_id)
            if deliverable and deliverable.parent_trace_id
            else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return result

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        if self._view_socket is None:
            return
        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            stage=0,
            data=data,
            integration_id="organism",
        )
        try:
            self._view_socket.broadcast(frame)
        except Exception as exc:
            logger.debug("organism event broadcast failed: %s", exc)

    def _route_to_agent(self, content: str) -> str:
        words = set(content.lower().split())
        build_score = len(words & BUILD_KEYWORDS)
        research_score = len(words & RESEARCH_KEYWORDS)

        if build_score > research_score:
            return "builder"
        return "researcher"

    def _decompose_to_execution(
        self, content: str, agent_id: str
    ) -> tuple[str, str, dict[str, Any]]:
        if agent_id == "researcher":
            return "shell", "query", {"command": f"echo 'Researcher task: {content[:200]}'"}
        elif agent_id == "builder":
            return "shell", "execute", {"command": f"echo 'Builder task: {content[:200]}'"}
        else:
            return "shell", "query", {"command": f"echo 'AutoResearch task: {content[:200]}'"}

    def handoff(
        self,
        source_agent: str,
        target_agent: str,
        task: str,
        handoff_type: HandoffType = HandoffType.LATERAL,
        context: str = "",
        partial_work: str = "",
    ) -> dict[str, Any]:
        """Route a task handoff between agents."""
        request = HandoffRequest(
            handoff_type=handoff_type,
            source_agent=source_agent,
            target_agent=target_agent,
            task=task,
            context=context,
            partial_work=partial_work,
        )
        submitted = self._handoff_router.submit(request)
        msg = self._handoff_router.to_agent_message(submitted)
        self._store.save_message(msg)

        self._emit_event(
            "organism.handoff_submitted",
            {
                "handoff_id": str(submitted.id),
                "source": source_agent,
                "target": submitted.target_agent,
                "type": handoff_type.value,
            },
        )

        target = self._agents.get(submitted.target_agent)
        if target:
            deliverable = target.handle_task(msg)
            self._handoff_router.resolve(submitted.id, accepted=True, deliverable=deliverable)
            return {
                "handoff_id": str(submitted.id),
                "accepted": True,
                "deliverable": deliverable.model_dump(mode="json") if deliverable else None,
            }

        return {
            "handoff_id": str(submitted.id),
            "accepted": False,
            "reason": f"target agent '{submitted.target_agent}' not found",
        }

    def execute_parallel(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute multiple agent tasks in parallel."""
        parallel_tasks = []
        for t in tasks:
            agent_id = self._route_to_agent(t.get("content", ""))
            adapter, operation, params = self._decompose_to_execution(
                t.get("content", ""), agent_id
            )
            parallel_tasks.append(
                ParallelTask(
                    agent_id=agent_id,
                    task=t.get("content", ""),
                    adapter=adapter,
                    operation=operation,
                    params=params,
                )
            )

        self._emit_event(
            "organism.parallel_started",
            {
                "task_count": len(parallel_tasks),
                "agents": [t.agent_id for t in parallel_tasks],
            },
        )

        def _agent_factory(agent_id: str) -> AgentRuntime:
            if agent_id in self._agents:
                return self._agents[agent_id]
            from substrate.organism.agents import create_researcher

            return create_researcher(self._store, self._worker)

        result = self._parallel.execute_batch(parallel_tasks, _agent_factory)

        self._emit_event(
            "organism.parallel_completed",
            {
                "task_count": len(parallel_tasks),
                "success_rate": result.success_rate(),
            },
        )

        return {
            "total_tasks": result.total_tasks,
            "completed": result.completed,
            "failed": result.failed,
            "success_rate": result.success_rate(),
            "results": {
                k: v.model_dump(mode="json") if v and hasattr(v, "model_dump") else str(v)
                for k, v in result.results.items()
            },
            "errors": result.errors,
        }

    def check_delegations(self) -> list[dict[str, Any]]:
        """Check for overdue delegations and generate follow-ups."""
        report = self._delegation_followup.check_and_followup()
        followups = report.actions
        for fu in followups:
            self._emit_event(
                "organism.delegation_followup",
                {
                    "delegation_id": fu.delegation_id,
                    "task": fu.task[:100],
                    "hours_overdue": fu.hours_overdue,
                    "escalated": fu.escalated,
                },
            )
        return [
            {
                "delegation_id": fu.delegation_id,
                "task": fu.task,
                "hours_overdue": fu.hours_overdue,
                "followup_number": fu.followup_number,
                "message": fu.message,
                "escalated": fu.escalated,
            }
            for fu in followups
        ]

    def organism_status(self) -> dict[str, Any]:
        agents = self.list_agents()
        deliverables = self._store.list_deliverables()
        learning = self._store.list_learning_signals()

        timed_out = self._handoff_router.check_timeouts()
        if timed_out:
            logger.warning("timed out handoffs: %d", len(timed_out))

        return {
            "agents": agents,
            "total_deliverables": len(deliverables),
            "total_learning_signals": len(learning),
            "recent_deliverables": deliverables[-5:],
            "handoff_stats": self._handoff_router.stats(),
            "parallel_available": True,
            "delegation_tracking": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
