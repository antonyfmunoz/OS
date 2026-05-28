"""Organism daemon — manages agent lifecycle within the control plane.

Integrates all subsystems into a single daemon that can be run
as a persistent process. The daemon is:
  - tmux-safe: survives terminal detach
  - restart-safe: persists state, recovers on restart
  - crash-safe: supervisor detects and recovers runtime failures
  - supervisor-managed: RuntimeSupervisor handles restart decisions

The daemon owns the full subsystem graph:
  RuntimeGraph → RuntimeSupervisor → OrganismCoordinator → Advisor
  HomeostasisEngine feeds into Advisor for self-regulation.
  WorkcellDaemon handles persistent inbox processing.
  OrganismObserver produces cockpit snapshots.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from substrate.organism.advisor import Advisor
from substrate.organism.allocation_loop import AllocationLoop
from substrate.organism.approval_store import ApprovalStore
from substrate.organism.async_coordinator import AsyncCoordinator
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.homeostasis import HomeostasisEngine
from substrate.organism.objective_queue import ObjectiveQueue
from substrate.organism.projection_port import OrganismStatePort
from substrate.organism.recursion_governance import RecursionGovernor
from substrate.organism.runtime_graph import RuntimeGraph
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.organism.store import OrganismStore
from substrate.organism.worker_cell import WorkerCell
from substrate.execution.pipeline import ExecutionPipeline

logger = logging.getLogger(__name__)

_RISK_DECISION_MAP: dict[str, str] = {
    "DENY": "high",
    "ESCALATE": "critical",
    "DEFER": "medium",
}


def _map_risk_level(data: dict[str, Any]) -> str:
    decision = data.get("decision", "")
    return _RISK_DECISION_MAP.get(decision, "medium")


class OrganismDaemon:
    """Integrated organism daemon with full subsystem wiring.

    Can be run as:
      1. Embedded (in-process): call start(), interact via methods
      2. Persistent (daemon): call run_forever() in a tmux/systemd session
      3. Single-tick: call tick() for one cycle of autonomous operation
    """

    def __init__(
        self,
        pipeline: ExecutionPipeline | None = None,
        store_dir: str = "data/umh/organism",
        view_socket: Any = None,
        graph: RuntimeGraph | None = None,
        supervisor: RuntimeSupervisor | None = None,
        homeostasis: HomeostasisEngine | None = None,
    ) -> None:
        self._store = OrganismStore(store_dir=store_dir)
        self._approval_store = ApprovalStore(store_dir=store_dir)
        self._pipeline = pipeline
        self._state_dir = Path(store_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._event_spine = EventSpine()

        self._graph = graph
        self._homeostasis = homeostasis or HomeostasisEngine()

        if self._graph is not None and supervisor is None:
            self._supervisor = RuntimeSupervisor(
                self._graph,
                state_dir=str(self._state_dir / "supervisor"),
                event_spine=self._event_spine,
            )
        else:
            self._supervisor = supervisor

        coordinator: OrganismCoordinator | None = None
        if self._graph is not None:
            coordinator = OrganismCoordinator(
                self._graph,
                state_dir=str(self._state_dir / "coordinator"),
            )

        worker = WorkerCell(pipeline=pipeline) if pipeline else WorkerCell()
        self._advisor = Advisor(
            store=self._store,
            worker=worker,
            view_socket=view_socket,
            graph=self._graph,
            coordinator=coordinator,
            supervisor=self._supervisor,
            homeostasis=self._homeostasis,
        )

        self._objective_queue = ObjectiveQueue(spine=self._event_spine)

        if self._graph and self._supervisor:
            self._allocation_loop: AllocationLoop | None = AllocationLoop(
                spine=self._event_spine,
                graph=self._graph,
                supervisor=self._supervisor,
                economy=ExecutionEconomy(),
                governor=RecursionGovernor(),
            )
        else:
            self._allocation_loop = None

        if coordinator is not None:
            self._async_coordinator: AsyncCoordinator | None = AsyncCoordinator(
                coordinator=coordinator,
                spine=self._event_spine,
            )
        else:
            self._async_coordinator = None

        self._projection_port = OrganismStatePort()

        self._view_socket = view_socket
        self._started = False
        self._tick_count = 0
        self._last_state_persist = 0.0
        self._state_persist_interval_s = 60.0

    @property
    def advisor(self) -> Advisor:
        return self._advisor

    @property
    def store(self) -> OrganismStore:
        return self._store

    @property
    def approval_store(self) -> ApprovalStore:
        return self._approval_store

    @property
    def graph(self) -> RuntimeGraph | None:
        return self._graph

    @property
    def supervisor(self) -> RuntimeSupervisor | None:
        return self._supervisor

    @property
    def homeostasis(self) -> HomeostasisEngine:
        return self._homeostasis

    @property
    def event_spine(self) -> EventSpine:
        return self._event_spine

    @property
    def objective_queue(self) -> ObjectiveQueue:
        return self._objective_queue

    @property
    def allocation_loop(self) -> AllocationLoop | None:
        return self._allocation_loop

    @property
    def async_coordinator(self) -> AsyncCoordinator | None:
        return self._async_coordinator

    @property
    def projection_port(self) -> OrganismStatePort:
        return self._projection_port

    def start(self) -> None:
        self._started = True

        if self._supervisor is not None and self._graph is not None:
            for node in self._graph.all_nodes():
                self._supervisor.supervise(node.runtime_id)
            self._supervisor.reconcile_graph()

        if self._pipeline is not None:
            self._pipeline.on_event(self._on_pipeline_event)

        logger.info(
            "organism daemon started: %d agents, graph=%s, supervisor=%s",
            len(self._advisor.list_agents()),
            self._graph is not None,
            self._supervisor is not None,
        )

    def _on_pipeline_event(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "governance" and not data.get("approved", True):
            self._approval_store.create_approval(
                title=f"Governance blocked: {data.get('decision', 'unknown')}",
                description=data.get("rationale", "No rationale provided"),
                agent="governance",
                risk_level=_map_risk_level(data),
                trace_id=data.get("verdict_id"),
                governance_rationale=data.get("rationale", ""),
            )

    def tick(self) -> dict[str, Any]:
        """Execute one autonomous tick of the organism.

        This is the core method for daemon operation. Each tick:
        1. Runs the advisor's autonomous_tick (drains signals, executes
           work units, checks health, runs homeostasis, recovers runtimes)
        2. Periodically persists state
        """
        if not self._started:
            self.start()

        self._tick_count += 1
        result = self._advisor.autonomous_tick()

        now = time.time()
        if now - self._last_state_persist > self._state_persist_interval_s:
            self._persist_state()
            self._last_state_persist = now

        return result

    def stop(self) -> None:
        self._persist_state()
        self._started = False
        logger.info("organism daemon stopped (tick_count=%d)", self._tick_count)

    @property
    def is_running(self) -> bool:
        return self._started

    def handoff(self, **kwargs: Any) -> dict[str, Any]:
        return self._advisor.handoff(**kwargs)

    def execute_parallel(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        return self._advisor.execute_parallel(tasks)

    def check_delegations(self) -> list[dict[str, Any]]:
        return self._advisor.check_delegations()

    def _persist_state(self) -> None:
        """Persist daemon state for crash recovery."""
        if self._supervisor is not None:
            self._supervisor.persist_state()

        state = {
            "started": self._started,
            "tick_count": self._tick_count,
            "timestamp": time.time(),
        }
        path = self._state_dir / "daemon_state.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(path)

    def status(self) -> dict[str, Any]:
        return {
            "running": self._started,
            "tick_count": self._tick_count,
            "graph_available": self._graph is not None,
            "supervisor_available": self._supervisor is not None,
            **self._advisor.organism_status(),
        }
