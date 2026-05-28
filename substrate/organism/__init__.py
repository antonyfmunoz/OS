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
"""
