"""Advisor cell — the top-level orchestrator of the organism.

Three execution tiers:
  1. handle_signal() — capability-aware routing for single-step tasks.
     Uses RuntimeGraph scoring (reliability × cost × latency) instead of
     keyword-only matching.
  2. execute_objective() — full organism decomposition via OrganismCoordinator
     for complex multi-step objectives with DAG dependencies and runtime selection.
  3. autonomous_tick() — one cycle of the continuous orchestration loop:
     drain signals, execute ready work units, supervise runtimes, run
     homeostasis, persist state.

The AI persona always enters through this module. The advisor decides
whether the request is simple (single runtime dispatch) or complex
(coordinator DAG).

Subsystem wiring:
  - RuntimeGraph: capability-aware runtime selection
  - RuntimeSupervisor: health monitoring, crash recovery, restart decisions
  - HomeostasisEngine: 8-dimension system health, corrective actions
  - OrganismCoordinator: DAG decomposition, dependency ordering
  - WorkcellDaemon: persistent inbox processing
  - OrganismObserver: cockpit snapshot aggregation

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from substrate.organism.agents import create_auto_research, create_builder, create_researcher
from substrate.organism.agent_runtime import AgentRuntime
from substrate.organism.coordinator import OrganismCoordinator, Objective, RuntimeCapability
from substrate.organism.handoff import HandoffRequest, HandoffRouter, HandoffType
from substrate.organism.homeostasis import HomeostasisEngine, HomeostasisReport
from substrate.organism.parallel import ParallelCoordinator, ParallelTask
from substrate.organism.delegation_followup import DelegationFollowup
from substrate.organism.protocols import AgentMessage, Deliverable
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor, SupervisedHealth
from substrate.organism.store import OrganismStore
from substrate.organism.worker_cell import WorkerCell
from substrate.sockets.envelopes import ViewFrame

logger = logging.getLogger(__name__)


_CAPABILITY_KEYWORDS: dict[str, RuntimeCapability] = {
    "create": RuntimeCapability.CODE_WRITE,
    "write": RuntimeCapability.CODE_WRITE,
    "edit": RuntimeCapability.CODE_WRITE,
    "modify": RuntimeCapability.CODE_WRITE,
    "add": RuntimeCapability.CODE_WRITE,
    "fix": RuntimeCapability.CODE_WRITE,
    "implement": RuntimeCapability.CODE_WRITE,
    "build": RuntimeCapability.CODE_WRITE,
    "update": RuntimeCapability.CODE_WRITE,
    "refactor": RuntimeCapability.CODE_WRITE,
    "delete": RuntimeCapability.CODE_WRITE,
    "remove": RuntimeCapability.CODE_WRITE,
    "audit": RuntimeCapability.RESEARCH,
    "find": RuntimeCapability.RESEARCH,
    "search": RuntimeCapability.RESEARCH,
    "check": RuntimeCapability.CODE_REVIEW,
    "analyze": RuntimeCapability.RESEARCH,
    "investigate": RuntimeCapability.RESEARCH,
    "look": RuntimeCapability.RESEARCH,
    "review": RuntimeCapability.CODE_REVIEW,
    "scan": RuntimeCapability.RESEARCH,
    "list": RuntimeCapability.RESEARCH,
    "show": RuntimeCapability.RESEARCH,
    "read": RuntimeCapability.RESEARCH,
    "examine": RuntimeCapability.RESEARCH,
    "inspect": RuntimeCapability.CODE_REVIEW,
    "run": RuntimeCapability.SHELL,
    "deploy": RuntimeCapability.SHELL,
    "execute": RuntimeCapability.SHELL,
    "start": RuntimeCapability.SHELL,
    "test": RuntimeCapability.CODE_EXECUTE,
    "think": RuntimeCapability.REASON,
    "plan": RuntimeCapability.REASON,
    "reason": RuntimeCapability.REASON,
    "decide": RuntimeCapability.REASON,
    "browse": RuntimeCapability.BROWSER,
    "scrape": RuntimeCapability.BROWSER,
    "gpu": RuntimeCapability.GPU_COMPUTE,
    "train": RuntimeCapability.GPU_COMPUTE,
    "render": RuntimeCapability.GPU_COMPUTE,
}

_COMPLEXITY_KEYWORDS = {"then", "after", "first", "finally", "step", "phase", "stages"}

_CAPABILITY_TO_AGENT: dict[RuntimeCapability, str] = {
    RuntimeCapability.CODE_WRITE: "builder",
    RuntimeCapability.CODE_REVIEW: "researcher",
    RuntimeCapability.CODE_EXECUTE: "builder",
    RuntimeCapability.RESEARCH: "researcher",
    RuntimeCapability.SHELL: "builder",
    RuntimeCapability.BROWSER: "auto-research",
    RuntimeCapability.GPU_COMPUTE: "builder",
    RuntimeCapability.REASON: "researcher",
    RuntimeCapability.FAST_RESPONSE: "researcher",
    RuntimeCapability.AUTONOMOUS: "builder",
    RuntimeCapability.FILE_OPS: "builder",
}


def _infer_capability(content: str) -> RuntimeCapability:
    """Deterministic capability inference from content keywords."""
    words = content.lower().split()
    for word in words[:8]:
        if word in _CAPABILITY_KEYWORDS:
            return _CAPABILITY_KEYWORDS[word]
    return RuntimeCapability.REASON


def _infer_risk_class(capability: RuntimeCapability) -> str:
    """Map capability to risk class — deterministic, no LLM."""
    if capability in {
        RuntimeCapability.CODE_WRITE,
        RuntimeCapability.SHELL,
        RuntimeCapability.CODE_EXECUTE,
    }:
        return "REVERSIBLE_WRITE"
    return "READ_ONLY"


class Advisor:
    """Unified orchestration hub for the UMH organism.

    Wires together all subsystems:
      - RuntimeGraph for capability-aware routing
      - RuntimeSupervisor for health/crash management
      - HomeostasisEngine for self-regulation
      - OrganismCoordinator for DAG execution
      - OrganismObserver for cockpit snapshots
    """

    def __init__(
        self,
        store: OrganismStore | None = None,
        worker: WorkerCell | None = None,
        view_socket: Any = None,
        graph: RuntimeGraph | None = None,
        coordinator: OrganismCoordinator | None = None,
        supervisor: RuntimeSupervisor | None = None,
        homeostasis: HomeostasisEngine | None = None,
    ) -> None:
        self._store = store or OrganismStore()
        self._worker = worker or WorkerCell()
        self._view_socket = view_socket
        self._graph = graph
        self._coordinator = coordinator
        self._supervisor = supervisor
        self._homeostasis = homeostasis or HomeostasisEngine()
        self._agents: dict[str, AgentRuntime] = {}
        self._handoff_router = HandoffRouter()
        self._parallel = ParallelCoordinator()
        self._delegation_followup = DelegationFollowup()
        self._tick_count = 0
        self._last_tick_at = 0.0
        self._signal_queue: list[dict[str, Any]] = []
        self._init_agents()

    def _init_agents(self) -> None:
        self._agents["researcher"] = create_researcher(self._store, self._worker)
        self._agents["builder"] = create_builder(self._store, self._worker)
        self._agents["auto-research"] = create_auto_research(self._store, self._worker)

    @property
    def graph(self) -> RuntimeGraph | None:
        return self._graph

    @property
    def supervisor(self) -> RuntimeSupervisor | None:
        return self._supervisor

    @property
    def homeostasis(self) -> HomeostasisEngine:
        return self._homeostasis

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.to_status_dict() for agent in self._agents.values()]

    # ─── Signal handling (capability-aware) ─────────────────────────

    def handle_signal(self, content: str) -> dict[str, Any]:
        """Route a signal through capability-aware selection.

        1. Infer required capability from content
        2. If graph available, try direct runtime execution first
        3. Fall back to agent dispatch if no graph or runtime fails
        """
        capability = _infer_capability(content)
        agent_id = _CAPABILITY_TO_AGENT.get(capability, "researcher")
        risk_class = _infer_risk_class(capability)

        self._emit_event(
            "organism.signal_received",
            {
                "content": content[:200],
                "capability": capability.value,
                "routed_to": agent_id,
                "has_graph": self._graph is not None,
            },
        )

        runtime_result = self._try_runtime_execution(content, capability)
        if runtime_result is not None:
            self._homeostasis.record_execution(True)
            return {
                "signal": content,
                "execution": "runtime_direct",
                "runtime_id": runtime_result.runtime_id,
                "capability": capability.value,
                "latency_ms": runtime_result.latency_ms,
                "output_length": len(runtime_result.output),
                "output": runtime_result.output[:500],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        agent = self._agents.get(agent_id)
        if agent is None:
            self._homeostasis.record_execution(False, f"no agent: {agent_id}")
            return {"error": f"no agent found for: {content[:100]}"}

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
                "risk_class": risk_class,
                "capability": capability.value,
            },
        )

        self._store.save_message(msg)

        self._emit_event(
            "organism.task_delegated",
            {
                "agent_id": agent_id,
                "task": content[:200],
                "message_id": str(msg.id),
                "capability": capability.value,
            },
        )

        deliverable = agent.handle_task(msg)

        self._homeostasis.record_execution(
            deliverable is not None and deliverable.self_critique.passed
        )

        self._emit_event(
            "organism.deliverable_produced",
            {
                "agent_id": agent_id,
                "deliverable_id": str(deliverable.id) if deliverable else None,
                "critique_score": deliverable.self_critique.score if deliverable else None,
                "critique_passed": deliverable.self_critique.passed if deliverable else None,
            },
        )

        return {
            "signal": content,
            "execution": "agent_dispatch",
            "delegated_to": agent_id,
            "capability": capability.value,
            "deliverable": deliverable.model_dump(mode="json") if deliverable else None,
            "trace_id": str(deliverable.parent_trace_id)
            if deliverable and deliverable.parent_trace_id
            else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _try_runtime_execution(
        self, content: str, capability: RuntimeCapability
    ) -> RuntimeResult | None:
        """Attempt direct runtime execution via the graph.

        Uses composite scoring: reliability, cost, latency.
        Falls through the chain on failure.
        """
        if self._graph is None:
            return None

        result = self._graph.route_and_execute(content, capability)

        if result is not None and self._supervisor is not None:
            self._supervisor.heartbeat(result.runtime_id)

        return result

    # ─── Autonomous tick (continuous orchestration) ─────────────────

    def autonomous_tick(self) -> dict[str, Any]:
        """One cycle of the continuous orchestration loop.

        Order of operations:
          1. Drain queued signals
          2. Execute ready work units from active objectives
          3. Check runtime health via supervisor
          4. Run homeostasis check
          5. Execute recovery plan for dead runtimes
          6. Check overdue delegations
          7. Persist state

        Returns a tick report with actions taken.
        """
        self._tick_count += 1
        tick_start = time.monotonic_ns()
        actions: list[dict[str, Any]] = []

        drained = self._drain_signal_queue()
        if drained:
            actions.append({"type": "signals_drained", "count": len(drained)})

        executed = self._execute_ready_objectives()
        if executed:
            actions.append({"type": "work_units_executed", "count": len(executed)})

        health_changes = self._check_runtime_health()
        if health_changes:
            actions.append({"type": "health_checked", "changes": health_changes})

        recovered = self._execute_recovery_plan()
        if recovered:
            actions.append({"type": "runtimes_recovered", "count": len(recovered)})

        homeostasis_report = self._homeostasis.check()
        if homeostasis_report.actions_taken:
            actions.append({
                "type": "homeostasis",
                "mode": homeostasis_report.mode.value,
                "actions": homeostasis_report.actions_taken,
            })

        followups = self._delegation_followup.check_and_followup()
        if followups.actions:
            actions.append({
                "type": "delegation_followups",
                "count": len(followups.actions),
            })

        elapsed_ms = (time.monotonic_ns() - tick_start) // 1_000_000
        self._last_tick_at = time.time()

        self._emit_event(
            "organism.tick_completed",
            {
                "tick": self._tick_count,
                "actions_count": len(actions),
                "elapsed_ms": elapsed_ms,
            },
        )

        return {
            "tick": self._tick_count,
            "actions": actions,
            "elapsed_ms": elapsed_ms,
            "system_mode": homeostasis_report.mode.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def queue_signal(self, content: str, priority: int = 5) -> str:
        """Queue a signal for processing on the next autonomous tick."""
        signal_id = f"sig-{uuid4().hex[:8]}"
        self._signal_queue.append({
            "id": signal_id,
            "content": content,
            "priority": priority,
            "queued_at": time.time(),
        })
        self._signal_queue.sort(key=lambda s: s["priority"])
        self._homeostasis.set_queue_depth(len(self._signal_queue))
        return signal_id

    def _drain_signal_queue(self) -> list[dict[str, Any]]:
        """Process all queued signals."""
        if not self._signal_queue:
            return []

        results = []
        batch = list(self._signal_queue)
        self._signal_queue.clear()
        self._homeostasis.set_queue_depth(0)

        for signal in batch:
            try:
                result = self.handle_signal(signal["content"])
                results.append({
                    "signal_id": signal["id"],
                    "status": "completed",
                    **result,
                })
            except Exception as exc:
                logger.warning("signal %s failed: %s", signal["id"], exc)
                self._homeostasis.record_execution(False, str(exc))
                results.append({
                    "signal_id": signal["id"],
                    "status": "failed",
                    "error": str(exc),
                })

        return results

    def _execute_ready_objectives(self) -> list[dict[str, Any]]:
        """Execute ready work units from all active objectives."""
        if self._coordinator is None:
            return []

        results = []
        for obj_dict in self._coordinator.list_objectives():
            if obj_dict["status"] != "executing":
                continue
            round_results = self._coordinator.execute_ready(obj_dict["id"])
            results.extend(round_results)

        return results

    def _check_runtime_health(self) -> dict[str, str]:
        """Check health of all supervised runtimes."""
        if self._supervisor is None:
            return {}

        health_states = self._supervisor.check_all()
        changes: dict[str, str] = {}

        for rid, health in health_states.items():
            if health in {SupervisedHealth.DEAD, SupervisedHealth.DEGRADED}:
                changes[rid] = health.value

        if changes:
            self._supervisor.reconcile_graph()

        return changes

    def _execute_recovery_plan(self) -> list[str]:
        """Attempt to recover dead runtimes per supervisor policy."""
        if self._supervisor is None or self._graph is None:
            return []

        plan = self._supervisor.get_recovery_plan()
        recovered = []

        for entry in plan:
            if not entry["should_restart"]:
                continue

            rid = entry["runtime_id"]
            node = self._graph.get(rid)
            if node is None or node.adapter is None:
                continue

            self._supervisor.mark_restarting(rid)
            try:
                available = node.adapter.check_available()
                if available:
                    self._supervisor.record_recovery_success(rid)
                    recovered.append(rid)
                    logger.info("runtime %s recovered", rid)
                else:
                    self._supervisor.record_recovery_failure(rid, "still unavailable")
            except Exception as exc:
                self._supervisor.record_recovery_failure(rid, str(exc))

        return recovered

    # ─── Event emission ─────────────────────────────────────────────

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

    # ─── Agent routing (capability-aware) ───────────────────────────

    def _route_to_agent(self, content: str) -> str:
        """Route to agent using capability inference."""
        capability = _infer_capability(content)
        return _CAPABILITY_TO_AGENT.get(capability, "researcher")

    def _decompose_to_execution(
        self, content: str, agent_id: str
    ) -> tuple[str, str, dict[str, Any]]:
        if agent_id == "researcher":
            return "shell", "query", {"command": f"echo 'Researcher task: {content[:200]}'"}
        elif agent_id == "builder":
            return "shell", "execute", {"command": f"echo 'Builder task: {content[:200]}'"}
        else:
            return "shell", "query", {"command": f"echo 'AutoResearch task: {content[:200]}'"}

    # ─── Handoffs ───────────────────────────────────────────────────

    def handoff(
        self,
        source_agent: str,
        target_agent: str,
        task: str,
        handoff_type: HandoffType = HandoffType.LATERAL,
        context: str = "",
        partial_work: str = "",
    ) -> dict[str, Any]:
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

    # ─── Parallel execution ─────────────────────────────────────────

    def execute_parallel(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        parallel_tasks = []
        for t in tasks:
            content = t.get("content", "")
            agent_id = self._route_to_agent(content)
            adapter, operation, params = self._decompose_to_execution(content, agent_id)
            parallel_tasks.append(
                ParallelTask(
                    agent_id=agent_id,
                    task=content,
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

    # ─── Delegation tracking ────────────────────────────────────────

    def check_delegations(self) -> list[dict[str, Any]]:
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

    # ─── Objective execution ────────────────────────────────────────

    def execute_objective(
        self,
        title: str,
        description: str,
        work_units: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self._coordinator is None:
            if self._graph is None:
                return {"error": "no runtime graph configured — cannot execute objectives"}
            self._coordinator = OrganismCoordinator(self._graph)

        self._emit_event(
            "organism.objective_started",
            {"title": title, "description": description[:200]},
        )

        result = self._coordinator.execute_objective(title, description, work_units)

        self._emit_event(
            "organism.objective_completed",
            {
                "objective_id": result["objective_id"],
                "status": result["status"],
                "completion_rate": result["completion_rate"],
            },
        )

        return result

    def get_objective(self, objective_id: str) -> dict[str, Any] | None:
        if self._coordinator is None:
            return None
        obj = self._coordinator.get_objective(objective_id)
        return obj.to_dict() if obj else None

    def _is_complex(self, content: str) -> bool:
        words = set(content.lower().split())
        has_sequencing = bool(words & _COMPLEXITY_KEYWORDS)
        has_multiple_sentences = content.count(".") >= 2 or content.count("\n") >= 2
        return has_sequencing and has_multiple_sentences

    @property
    def coordinator(self) -> OrganismCoordinator | None:
        return self._coordinator

    # ─── Resource topology ──────────────────────────────────────────

    def resource_topology(self) -> dict[str, Any]:
        """Return the current resource topology: all runtimes, their
        capabilities, health, and scoring."""
        topology: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtimes": {},
            "federation": {
                "total_runtimes": 0,
                "available": 0,
                "degraded": 0,
                "unavailable": 0,
            },
            "capabilities_coverage": {},
        }

        if self._graph is None:
            return topology

        for node in self._graph.all_nodes():
            topology["runtimes"][node.runtime_id] = {
                **node.to_dict(),
                "supervised": False,
                "supervised_health": None,
            }
            topology["federation"]["total_runtimes"] += 1

            if node.status == AvailabilityStatus.AVAILABLE:
                topology["federation"]["available"] += 1
            elif node.status == AvailabilityStatus.DEGRADED:
                topology["federation"]["degraded"] += 1
            else:
                topology["federation"]["unavailable"] += 1

            for cap in node.capabilities:
                cap_name = cap.value
                if cap_name not in topology["capabilities_coverage"]:
                    topology["capabilities_coverage"][cap_name] = []
                topology["capabilities_coverage"][cap_name].append(node.runtime_id)

        if self._supervisor is not None:
            sup_dict = self._supervisor.to_dict()
            for rid, sr_data in sup_dict.get("runtimes", {}).items():
                if rid in topology["runtimes"]:
                    topology["runtimes"][rid]["supervised"] = True
                    topology["runtimes"][rid]["supervised_health"] = sr_data.get("health")

        return topology

    # ─── Status ─────────────────────────────────────────────────────

    def organism_status(self) -> dict[str, Any]:
        agents = self.list_agents()
        deliverables = self._store.list_deliverables()
        learning = self._store.list_learning_signals()

        timed_out = self._handoff_router.check_timeouts()
        if timed_out:
            logger.warning("timed out handoffs: %d", len(timed_out))

        coordinator_status = self._coordinator.status() if self._coordinator else None
        supervisor_status = self._supervisor.to_dict() if self._supervisor else None
        homeostasis_report = self._homeostasis.check()

        return {
            "agents": agents,
            "total_deliverables": len(deliverables),
            "total_learning_signals": len(learning),
            "recent_deliverables": deliverables[-5:],
            "handoff_stats": self._handoff_router.stats(),
            "parallel_available": True,
            "delegation_tracking": True,
            "coordinator": coordinator_status,
            "supervisor": supervisor_status,
            "homeostasis": homeostasis_report.to_dict(),
            "tick_count": self._tick_count,
            "last_tick_at": self._last_tick_at,
            "signal_queue_depth": len(self._signal_queue),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
