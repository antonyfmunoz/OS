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
from substrate.organism.autonomous_tick import AutonomousTick, TickConfig
from substrate.organism.bottleneck_engine import BottleneckEngine
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.environment_graph import EnvironmentGraph
from substrate.organism.environment_reconciler import EnvironmentReconciler
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.execution_modes import ExecutionModeManager
from substrate.organism.homeostasis import HomeostasisEngine
from substrate.organism.leverage_assimilation import LeverageAssimilator
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.objective_physics import ObjectivePhysics
from substrate.organism.objective_queue import ObjectiveQueue
from substrate.organism.operator_compression import OperatorCompression
from substrate.organism.projection_port import OrganismStatePort, StateSlice
from substrate.organism.recursion_governance import RecursionGovernor
from substrate.organism.runtime_graph import RuntimeGraph
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.organism.store import OrganismStore
from substrate.organism.workcell_daemon import WorkcellDaemon as WorkcellDaemonV2
from substrate.organism.workcell_protocol import Workcell, WorkcellRole
from substrate.organism.workload_probes import WorkloadProbes
from substrate.organism.workload_runner import WorkloadRunner
from substrate.organism.automation_pipeline import AutomationPipeline
from substrate.organism.maintenance_loop import MaintenanceLoop
from substrate.organism.assisted_executor import AssistedExecutor
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.spine_guard import GuardMode, SpineGuard
from substrate.organism.autonomous_action_gateway import AutonomousActionGateway, AutonomousPolicy
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
        tick_config: TickConfig | None = None,
    ) -> None:
        self._store = OrganismStore(store_dir=store_dir)
        self._approval_store = ApprovalStore(store_dir=store_dir)
        self._pipeline = pipeline
        self._state_dir = Path(store_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._event_spine = EventSpine(
            persist_path=str(self._state_dir / "events.jsonl"),
        )

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

        self._governor = RecursionGovernor()
        self._economy = ExecutionEconomy()

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
                economy=self._economy,
                governor=self._governor,
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

        self._leverage_assimilator = LeverageAssimilator(
            event_spine=self._event_spine,
            state_dir=str(self._state_dir / "leverage"),
        )

        if self._graph is not None:
            self._reconciler: EnvironmentReconciler | None = EnvironmentReconciler(
                graph=self._graph,
                spine=self._event_spine,
            )
        else:
            self._reconciler = None

        self._environment_graph = EnvironmentGraph()

        self._leverage_metrics = LeverageMetrics(
            event_spine=self._event_spine,
        )
        self._bottleneck_engine = BottleneckEngine(
            event_spine=self._event_spine,
        )
        self._objective_physics = ObjectivePhysics(
            event_spine=self._event_spine,
        )
        self._operator_compression = OperatorCompression(
            event_spine=self._event_spine,
        )
        self._execution_mode_manager = ExecutionModeManager(
            event_spine=self._event_spine,
        )
        self._workload_probes = WorkloadProbes(
            event_spine=self._event_spine,
        )

        self._workload_runner = WorkloadRunner(
            event_spine=self._event_spine,
            execution_mode=self._execution_mode_manager,
            leverage_metrics=self._leverage_metrics,
            operator_compression=self._operator_compression,
        )
        self._automation_pipeline = AutomationPipeline(
            operator_compression=self._operator_compression,
            event_spine=self._event_spine,
        )
        self._maintenance_loop = MaintenanceLoop(
            workload_runner=self._workload_runner,
            execution_mode=self._execution_mode_manager,
            event_spine=self._event_spine,
        )
        self._assisted_executor = AssistedExecutor(
            execution_mode=self._execution_mode_manager,
            event_spine=self._event_spine,
            leverage_metrics=self._leverage_metrics,
        )

        self._mutation_registry = MutationRegistry()
        self._execution_journal = ExecutionJournal(
            persist_path=str(self._state_dir / "execution_journal.jsonl"),
        )
        self._governed_spine = GovernedExecutionSpine(
            event_spine=self._event_spine,
            execution_mode=self._execution_mode_manager,
            mutation_registry=self._mutation_registry,
            journal=self._execution_journal,
            leverage_metrics=self._leverage_metrics,
        )
        self._spine_guard = SpineGuard(
            mode=GuardMode.BLOCK_HIGH_RISK,
            event_spine=self._event_spine,
            journal=self._execution_journal,
        )

        self._autonomous_gateway = AutonomousActionGateway(
            governed_spine=self._governed_spine,
            execution_mode=self._execution_mode_manager,
            event_spine=self._event_spine,
            journal=self._execution_journal,
            policy=AutonomousPolicy.ASSISTED,
        )

        self._workload_runner.set_governed_spine(self._governed_spine)
        self._workload_runner.set_autonomous_gateway(self._autonomous_gateway)
        self._assisted_executor.set_governed_spine(self._governed_spine)
        self._assisted_executor.set_autonomous_gateway(self._autonomous_gateway)
        self._maintenance_loop.set_autonomous_gateway(self._autonomous_gateway)

        self._workcell_daemon = WorkcellDaemonV2(
            state_dir=str(self._state_dir / "workcell_daemon"),
        )
        self._setup_canonical_workcells()

        self._projection_port = OrganismStatePort(
            state_dir=str(self._state_dir / "projections"),
        )

        self._autonomous_tick = AutonomousTick(
            spine=self._event_spine,
            config=tick_config or TickConfig(),
        )
        self._register_tick_stages()

        self._view_socket = view_socket
        self._started = False
        self._tick_count = 0
        self._last_state_persist = 0.0
        self._state_persist_interval_s = 60.0

    def _setup_canonical_workcells(self) -> None:
        """Create real workcells for each organism subsystem."""
        base_dir = str(self._state_dir / "workcells")

        advisor_cell = Workcell(
            workcell_id="advisor",
            role=WorkcellRole.COORDINATOR,
            base_dir=base_dir,
        )
        self._workcell_daemon.register_workcell(advisor_cell)

        executor_cell = Workcell(
            workcell_id="executor",
            role=WorkcellRole.EXECUTOR,
            base_dir=base_dir,
        )
        self._workcell_daemon.register_workcell(executor_cell)

        reviewer_cell = Workcell(
            workcell_id="reviewer",
            role=WorkcellRole.REVIEWER,
            base_dir=base_dir,
        )
        self._workcell_daemon.register_workcell(reviewer_cell)

        researcher_cell = Workcell(
            workcell_id="researcher",
            role=WorkcellRole.RESEARCHER,
            base_dir=base_dir,
        )
        self._workcell_daemon.register_workcell(researcher_cell)

        for wc in [advisor_cell, executor_cell, reviewer_cell, researcher_cell]:
            wc.write_heartbeat()

        logger.info(
            "canonical workcells created: %d",
            len(self._workcell_daemon._workcells),
        )

    def _register_tick_stages(self) -> None:
        """Register all subsystems as autonomous tick stages."""
        self._autonomous_tick.register_stage(
            "advisor",
            self._advisor.autonomous_tick,
        )
        self._autonomous_tick.register_stage(
            "homeostasis",
            self._homeostasis.check,
        )
        if self._supervisor is not None:
            self._autonomous_tick.register_stage(
                "supervisor_reconcile",
                self._supervisor.reconcile_graph,
            )
        if self._allocation_loop is not None:
            self._autonomous_tick.register_stage(
                "allocation",
                self._allocation_loop.allocation_cycle,
            )
        if self._async_coordinator is not None:
            self._autonomous_tick.register_stage(
                "async_objectives",
                self._async_coordinator.advance,
            )
        self._autonomous_tick.register_stage(
            "leverage_rebalance",
            self._leverage_assimilator.rebalance_cycle,
        )
        if self._reconciler is not None:
            self._autonomous_tick.register_stage(
                "environment_reconcile",
                self._reconciler.reconcile_tick,
            )
        self._autonomous_tick.register_stage(
            "leverage_measurement",
            self._leverage_metrics.leverage_tick,
        )
        self._autonomous_tick.register_stage(
            "bottleneck_detection",
            self._bottleneck_detection_tick,
        )
        self._autonomous_tick.register_stage(
            "objective_physics",
            self._objective_physics.physics_tick,
        )
        self._autonomous_tick.register_stage(
            "operator_compression",
            self._operator_compression.compression_tick,
        )
        self._autonomous_tick.register_stage(
            "workload_probes",
            self._workload_probes.full_probe,
        )
        self._autonomous_tick.register_stage(
            "maintenance_cycle",
            self._maintenance_loop.maintenance_tick,
        )
        self._autonomous_tick.register_stage(
            "automation_scan",
            self._automation_pipeline.pipeline_tick,
        )
        self._autonomous_tick.register_stage(
            "projection_broadcast",
            self._broadcast_state,
        )

    def _bottleneck_detection_tick(self) -> dict[str, Any]:
        """Feed real metrics into the bottleneck engine."""
        leverage_inputs = self._leverage_metrics.bottleneck_inputs()

        runtime_stats: list[dict[str, Any]] = []
        if self._graph is not None:
            for node in self._graph.all_nodes():
                runtime_stats.append({
                    "runtime_id": node.runtime_id,
                    "avg_latency_ms": node.reliability.avg_latency_ms,
                    "idle_cycles": 0,
                })

        tick_metrics = self._autonomous_tick.metrics
        bottlenecks = self._bottleneck_engine.detect(
            leverage_inputs=leverage_inputs,
            runtime_stats=runtime_stats,
            tick_metrics={
                "total_stages_executed": tick_metrics.total_stages_executed,
                "total_stages_failed": tick_metrics.total_stages_failed,
            },
            queue_depth=self._objective_queue.depth(),
        )
        return {
            "detected": len(bottlenecks),
            "critical": sum(1 for b in bottlenecks if b.severity.value == "critical"),
        }

    def _broadcast_state(self) -> None:
        """Push current state through the projection port and capture topology."""
        if self._graph is not None:
            self._projection_port.broadcast(
                StateSlice.RUNTIMES,
                self._graph.to_dict(),
            )
        if self._supervisor is not None:
            self._projection_port.broadcast(
                StateSlice.SUPERVISOR,
                self._supervisor.to_dict(),
            )
        self._projection_port.broadcast(
            StateSlice.GOVERNANCE,
            self._governor.to_dict(),
        )
        self._projection_port.broadcast(
            StateSlice.LEVERAGE,
            self._leverage_metrics.to_dict(),
        )
        self._environment_graph.capture(
            graph=self._graph,
        )

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

    @property
    def autonomous_tick(self) -> AutonomousTick:
        return self._autonomous_tick

    @property
    def leverage_assimilator(self) -> LeverageAssimilator:
        return self._leverage_assimilator

    @property
    def reconciler(self) -> EnvironmentReconciler | None:
        return self._reconciler

    @property
    def environment_graph(self) -> EnvironmentGraph:
        return self._environment_graph

    @property
    def workcell_daemon(self) -> WorkcellDaemonV2:
        return self._workcell_daemon

    @property
    def governor(self) -> RecursionGovernor:
        return self._governor

    @property
    def leverage_metrics(self) -> LeverageMetrics:
        return self._leverage_metrics

    @property
    def bottleneck_engine(self) -> BottleneckEngine:
        return self._bottleneck_engine

    @property
    def objective_physics(self) -> ObjectivePhysics:
        return self._objective_physics

    @property
    def operator_compression(self) -> OperatorCompression:
        return self._operator_compression

    @property
    def execution_mode_manager(self) -> ExecutionModeManager:
        return self._execution_mode_manager

    @property
    def workload_probes(self) -> WorkloadProbes:
        return self._workload_probes

    @property
    def workload_runner(self) -> WorkloadRunner:
        return self._workload_runner

    @property
    def automation_pipeline(self) -> AutomationPipeline:
        return self._automation_pipeline

    @property
    def maintenance_loop(self) -> MaintenanceLoop:
        return self._maintenance_loop

    @property
    def assisted_executor(self) -> AssistedExecutor:
        return self._assisted_executor

    @property
    def governed_spine(self) -> GovernedExecutionSpine:
        return self._governed_spine

    @property
    def mutation_registry(self) -> MutationRegistry:
        return self._mutation_registry

    @property
    def execution_journal(self) -> ExecutionJournal:
        return self._execution_journal

    @property
    def spine_guard(self) -> SpineGuard:
        return self._spine_guard

    @property
    def autonomous_gateway(self) -> AutonomousActionGateway:
        return self._autonomous_gateway

    def start(self) -> None:
        self._started = True

        if self._supervisor is not None and self._graph is not None:
            for node in self._graph.all_nodes():
                self._supervisor.supervise(node.runtime_id)
            self._supervisor.reconcile_graph()

        if self._pipeline is not None:
            self._pipeline.on_event(self._on_pipeline_event)

        self._projection_port.bridge_from_spine(
            self._event_spine,
            {
                EventDomain.RUNTIME: StateSlice.RUNTIMES,
                EventDomain.SUPERVISOR: StateSlice.SUPERVISOR,
                EventDomain.GOVERNANCE: StateSlice.GOVERNANCE,
                EventDomain.LEVERAGE: StateSlice.LEVERAGE,
                EventDomain.OBJECTIVE: StateSlice.OBJECTIVES,
                EventDomain.EXECUTION: StateSlice.ECONOMY,
                EventDomain.WORKCELL: StateSlice.WORKCELLS,
                EventDomain.OBSERVABILITY: StateSlice.OBSERVABILITY,
            },
        )

        self._event_spine.recover()
        self._execution_journal.recover()

        logger.info(
            "organism daemon started: %d agents, graph=%s, supervisor=%s, "
            "tick_stages=%d, events_recovered=%d",
            len(self._advisor.list_agents()),
            self._graph is not None,
            self._supervisor is not None,
            len(self._autonomous_tick.stages),
            len(self._event_spine.recent(limit=1000)),
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

        Runs all registered stages through the AutonomousTick engine:
          advisor, homeostasis, supervisor reconcile, allocation,
          async objectives, leverage rebalance, projection broadcast.
        Periodically persists daemon state.
        """
        if not self._started:
            self.start()

        self._tick_count += 1
        report = self._autonomous_tick.execute_cycle()

        now = time.time()
        if now - self._last_state_persist > self._state_persist_interval_s:
            self._persist_state()
            self._last_state_persist = now

        return {
            "cycle": report.cycle_number,
            "stages_executed": report.stages_executed,
            "stages_failed": report.stages_failed,
            "elapsed_ms": round(report.elapsed_ms, 2),
            "had_work": report.had_work,
            "stage_details": report.stage_details,
        }

    def stop(self) -> None:
        self._persist_state()
        self._event_spine.flush()
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
        result = {
            "running": self._started,
            "tick_count": self._tick_count,
            "graph_available": self._graph is not None,
            "supervisor_available": self._supervisor is not None,
            "tick_engine": self._autonomous_tick.to_dict(),
            "event_spine": self._event_spine.snapshot(),
            "governor": self._governor.to_dict(),
            "leverage": self._leverage_metrics.to_dict(),
            "bottlenecks": self._bottleneck_engine.to_dict(),
            "objective_physics": self._objective_physics.to_dict(),
            "operator_compression": self._operator_compression.to_dict(),
            "execution_mode": self._execution_mode_manager.to_dict(),
            "workload_probes": self._workload_probes.to_dict(),
            "workload_runner": self._workload_runner.to_dict(),
            "automation_pipeline": self._automation_pipeline.to_dict(),
            "maintenance_loop": self._maintenance_loop.to_dict(),
            "assisted_executor": self._assisted_executor.to_dict(),
            "governed_spine": self._governed_spine.to_dict(),
            "mutation_registry": self._mutation_registry.to_dict(),
            "execution_journal": self._execution_journal.to_dict(),
            "spine_guard": self._spine_guard.to_dict(),
            "autonomous_gateway": self._autonomous_gateway.to_dict(),
            **self._advisor.organism_status(),
        }
        if self._graph is not None:
            result["runtimes"] = self._graph.to_dict()
        if self._reconciler is not None:
            result["reconciler"] = self._reconciler.to_dict()
        return result
