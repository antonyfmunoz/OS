# Campaign 2 — Operator Ascension — PLAN

## Objective

Transform UMH from organism into primary operating environment. The operator can build UMH, build projections, manage agents, manage compute, execute work, create content, and maintain continuity from inside UMH.

## Current State

- Compute Fabric ✓ (W1)
- Capability Loop ✓ (Gates 5-9)
- Continuity ✓ (Phase 32)
- Workstation ✓ (Gate 4)

## Missing

- Unified Agent Layer (W3)
- Unified Development Layer (W2)
- Unified Embodiment Layer (W4)
- Unified Daily Operation Layer (W5)

## Build Order

W3 Agent Fleet → W2 Meta IDE → W4 Embodiment → W5 Operator Migration

Each workstream composes existing substrate. No new memory/governance/execution/routing systems.

## W3 — Agent Fleet Runtime

**"Who should do this work?"**

Composes: AgentCapabilityModel + ComputeFabricRuntime + ExecutorRuntime + AgentRegistry + CompoundingEngine

- `substrate/organism/agent_fleet_runtime.py` (~500 LOC)
- `transports/api/cockpit_agent_fleet_routes.py` (~180 LOC) — 8 endpoints
- `tests/test_agent_fleet_runtime.py` (~450 LOC)

Core: `assign(work_packet) → FleetAssignment` with agent + compute node + deterministic rationale

Types: FleetAssignment, FleetDispatch, FleetDispatchResult, FleetSnapshot, FleetHealth, WaveResult

## W2 — Meta IDE Convergence

**"One development surface"**

Composes: EngineeringSessionCoordinator + RepositoryModel + WorkspaceObservation + EngineeringPlanner + ReviewPackageBuilder + AgentFleetRuntime (W3) + IntentRuntime + ExecutionGraph

- `substrate/organism/meta_ide_runtime.py` (~550 LOC)
- `transports/api/cockpit_meta_ide_conv_routes.py` (~200 LOC) — 11 endpoints
- `tests/test_meta_ide_runtime.py` (~500 LOC)

Core: inspect → plan → assign → monitor → review → merge without leaving UMH

Types: WorkspaceSnapshot, DevelopmentStream, ReviewDetail, MergeResult, IDEStatusSnapshot

## W4 — Embodiment Runtime

**"Natural language intent becomes governed work without prompt engineering"**

Composes: Persona + IntentRuntime + CommandRuntime + AgentFleetRuntime (W3) + MetaIDERuntime (W2) + CapabilityRuntime + OperationalizationRuntime + CompoundingEngine

- `substrate/organism/embodiment_runtime.py` (~550 LOC)
- `transports/api/cockpit_embodiment_routes.py` (~180 LOC) — 7 endpoints
- `tests/test_embodiment_runtime.py` (~500 LOC)

Core: `process_intent(text) → EmbodimentResponse` with classification → context → routing → persona shaping

Deterministic routing table:
- WORK → AgentFleetRuntime
- DEVELOPMENT → MetaIDERuntime
- QUERY → read-only subsystem queries
- COMMAND → CommandRuntime
- CONVERSATION → context-enriched pass-through

Types: IntentClassification, EmbodimentContext, EmbodimentResponse, ProcessedIntent

## W5 — Operator Migration Runtime

**"UMH identifies the highest-value reasons the operator still leaves"**

Composes: CapabilityRuntime + OperationalizationRuntime + InfrastructureRuntime + CompoundingEngine + EmbodimentRuntime (W4) + ScreenAwareness + PresenceTimeline

- `substrate/organism/operator_migration_runtime.py` (~500 LOC)
- `transports/api/cockpit_migration_routes.py` (~180 LOC) — 9 endpoints
- `tests/test_operator_migration_runtime.py` (~450 LOC)

Core: Track exits, classify (capability_gap/tooling_gap/preference/external), score by frequency × duration × feasibility, bridge to operationalizations

Types: ExitEvent, ExitClassification, MigrationPriority, CoverageReport, Migration, MigrationStatusSnapshot

## Campaign Totals

- 12 new files + 2 modified files
- ~4,840 LOC
- All 4 runtimes compose existing subsystems
- Must consume: ComputeFabricRuntime, IntentRuntime, CapabilityRuntime, OperationalizationRuntime, ExecutionGraph, CompoundingEngine

## Campaign Acceptance Test

For 7 consecutive days, operator can build UMH, build projections, manage agents, manage compute, execute work, create content, maintain continuity while remaining primarily inside UMH.

Verified by:
1. W3: `fleet.assign(packet)` → agent + node + rationale
2. W2: inspect → plan → assign → review → merge loop
3. W4: natural language → governed work through deterministic classification
4. W5: coverage report > 70%, migration priorities for remaining exits
