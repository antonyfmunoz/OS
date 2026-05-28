"""UMH Organism — distributed orchestration substrate.

Public API for the organism subsystem. All external code should
import from this module rather than reaching into submodules.

Core subsystems:
  - Advisor: unified orchestration hub (capability-aware routing,
    autonomous tick, signal queue, objective execution)
  - OrganismDaemon: persistent daemon with full subsystem wiring
  - RuntimeGraph: capability-based runtime registry and selection
  - RuntimeSupervisor: health monitoring, crash recovery, restart
  - OrganismCoordinator: DAG decomposition and execution
  - HomeostasisEngine: 8-dimension self-regulation
  - OrganismObserver: cockpit snapshot aggregation
  - LeverageAssimilator: external framework ingestion and scoring
  - Orchestration loop: PersistentLoop integration for daemon mode
"""
