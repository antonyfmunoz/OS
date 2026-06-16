"""UMH Organism — distributed orchestration substrate.

Public API for the organism subsystem. All external code should
import from this module rather than reaching into submodules.

Core subsystems:
  - EventSpine: canonical organism event transport
  - AutonomousTick: continuous metabolism heartbeat
  - Advisor: unified orchestration hub (capability-aware routing,
    autonomous tick, signal queue, objective execution)
  - OrganismDaemon: persistent daemon with full subsystem wiring
  - RuntimeGraph: capability-based runtime registry and selection
  - RuntimeSupervisor: health monitoring, crash recovery, restart
  - OrganismCoordinator: DAG decomposition and execution
  - AsyncCoordinator: event-driven async objective execution
  - ObjectiveQueue: priority-ordered objective intake
  - AllocationLoop: governed runtime allocation
  - HomeostasisEngine: 8-dimension self-regulation
  - OrganismObserver: cockpit snapshot aggregation
  - LeverageAssimilator: external framework ingestion and scoring
  - OrganismStatePort: projection-agnostic state interface
  - Orchestration loop: PersistentLoop integration for daemon mode

Phase 5.8 — Operational Leverage Engine:
  - LeverageMetrics: measures actual organism value (time saved,
    throughput, autonomy, reliability, economic efficiency)
  - BottleneckEngine: detects operational bottlenecks with recurrence
    tracking and correction suggestions
  - ObjectivePhysics: models causal execution dynamics (dependencies,
    gravity, critical paths, leverage propagation)
  - OperatorCompression: tracks operator burden and identifies
    automation candidates from repeated intervention patterns
  - ExecutionModeManager: governed transition from observation to
    autonomous action (observe → recommend → assisted → autonomous)
  - WorkloadProbes: real-time infrastructure state (Docker, disk,
    memory, repo, processes)

Phase 5.9 — Real Workload Execution + Automation Promotion:
  - WorkloadRunner: governed execution of real operational jobs
    (repo health, docker health, disk pressure, test runs, etc.)
  - AutomationPipeline: detects repeated interventions and proposes
    automation candidates with leverage scoring and risk classification
  - MaintenanceLoop: autonomous OBSERVE-mode maintenance cycle
    wired into AutonomousTick (probes + recommendations)
  - AssistedExecutor: governed execution of approved maintenance
    actions (log rotation, container restart, graph rebuild, etc.)

Phase 28 — UMH Node Role & Version Topology:
  - UMHNodeTopology: canonical node role, version, and service models
  - UMHNodeRegistry: single source of truth for organism nodes
    (loads from infra/umh_node_registry.json)
  - UMHVersionCoherenceEngine: detects version drift across nodes
    (capability drift expected, version drift surfaced)

Phase 29 — Organism State Authority & Coherence:
  - StateDomain: 10 canonical state domains (memory, governance,
    runtime, workspace, session, observation, execution, proof,
    reality, configuration)
  - StateRegistry: single source of truth for domain authority
    (loads from infra/state_authority_registry.json)
  - StateCoherenceEngine: detects authority coherence across nodes
    (is authority online, reachable, version-coherent?)

Phase 30 — Service Dependency & Failure Graph:
  - ServiceDependencyGraph: service-to-service dependency models
    (ServiceNode, ServiceDependency, FailureImpact, topology)
  - ServiceDependencyRegistry: single source of truth for service
    dependencies (loads from infra/service_dependency_registry.json)
  - ServiceFailureEngine: computes failure impact and critical path
    (blast radius, transitive cascades, severity classification)
"""
