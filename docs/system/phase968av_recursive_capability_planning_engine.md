# Phase 96.8AV — Recursive Capability Planning Engine

## Summary

Built the substrate capability to recursively analyze its own maturity,
identify capability gaps, generate upgrade paths, prioritize leverage
opportunities, and propose the next safest/highest-value substrate
expansions. Transitions from static maturity evaluation to recursive
self-improving capability planning.

## What was built

### Core engine
- `core/workstation/recursive_capability_planning_engine_v1.py`
  - 21 substrate capabilities with full dependency graph
  - 8 bottleneck categories (manual, replay, governance, execution,
    relay, ingestion, maturity, scaling)
  - 5 upgrade catalog entries with 8-dimensional leverage scoring
  - L0-L5 maturity model extending adapter maturity with
    L5_RECURSIVE_CAPABILITY_PLANNING
  - Hard ceilings preventing maturity claims without evidence
  - Capability graph with proven/blocked/missing status per node
  - Evidence quality scoring (0.8 base + 0.1 replay + 0.1 governance)
  - Reverse-computed dependents for impact analysis
  - Circular dependency detection (none found)
  - Infrastructure self-analysis (registries, proofs, governance surface)
  - Infrastructure reuse detection across upgrade proposals
  - Proof persistence to `data/runtime/workstation_relay/capability_reports/`

### Leverage scoring
- 8 dimensions: leverage_gain, governance_risk, replayability_impact,
  execution_complexity, evidence_quality, infrastructure_reuse,
  recursive_expansion_value, automation_potential
- Weighted composite: positive = gain*0.25 + replay*0.15 + evidence*0.15
  + reuse*0.15 + recursive*0.15 + automation*0.15;
  penalty = governance*0.2 + complexity*0.2
- Floor at 0.0 (no negative composites)

### Command registration (6 files)
- `core/registry/canonical_command_registry_v1.py` — `!capability-report` CommandEntry
- `core/control_plane_router/router_contracts.py` — CAPABILITY_PLANNING CapabilityType, ALLOWED_ACTION_TYPES
- `core/control_plane_router/control_plane_router_v1.py` — ACTION_CAPABILITY_MAP entry
- `core/environment_bridge/windows_desktop_adapter_contracts.py` — CAPABILITY_REPORT enum value
- `config/control_plane_router_v1.json` — allowed_action_types updated
- `data/registries/local_worker_adapter_registry_v1.json` — capability_report added

### Discord handler
- `services/handlers/substrate_command_handler.py` — `!capability-report` intercept
  - VPS-side execution (no relay dispatch needed)
  - Loads most recent environment mapping and adapter proofs from disk
  - Builds full capability graph with bottleneck analysis
  - Generates ranked upgrade proposals with leverage scoring
  - Reports capabilities, bottlenecks, proposals, maturity, strategy
  - Founder confirmation required for proof persistence
  - Persists proof artifact

## Test results

91 tests across 21 test classes. All passing.

Test classes:
- TestCapabilityNode(4), TestLeverageScore(6), TestBottleneck(3)
- TestUpgradeProposal(3), TestSubstrateCapabilities(5)
- TestCapabilityGraph(6), TestDependencyGraph(4)
- TestBottleneckAnalysis(5), TestLeverageScoring(4)
- TestUpgradeProposals(4), TestMaturityClassification(7)
- TestHardCeilings(10), TestProofPersistence(4)
- TestFullPipeline(5), TestInfrastructureAnalysis(4)
- TestCanonicalInstanceSeparation(2), TestRegistryIntegration(8)
- TestMaturityRequirements(4), TestPlanningEvidence(3)

## Regression

858/858 core substrate tests passing (including registry count fixes
for the new 16-command registry).

1764/1764 broad substrate tests passing (excluding 37 pre-existing
failures in test_engine_spine_migration.py and older UMH test files
that reference removed modules — unrelated to this phase).

## Maturity levels

| Level | Name | Requirements |
|-------|------|-------------|
| L0 | SIMULATED | No evidence |
| L1 | VISIBLE_ACTUATION | Actuation proven |
| L2 | FOREGROUND_CU_INGESTION | + CU ingestion proven |
| L3 | ENVIRONMENT_INTELLIGENCE | + Environment mapped |
| L4 | ADAPTER_MATURITY | + Blueprints, replay contracts, governance |
| L5 | RECURSIVE_CAPABILITY_PLANNING | + Capability graph, leverage analysis, upgrade paths |

## Hard ceilings

| Missing evidence | Maximum maturity |
|-----------------|-----------------|
| Dry run | L0 |
| No screenshots | L1 |
| No environment map | L2 |
| No blueprints | L3 |
| No governance | L3 |
| No capability graph | L4 |
| No leverage analysis | L4 |
| No founder confirmation | L4 |

## Substrate capabilities (21)

| Capability | Dependencies |
|-----------|-------------|
| relay_transport | (root) |
| desktop_actuation | relay_transport |
| foreground_cu | desktop_actuation |
| clipboard_extraction | foreground_cu |
| screenshot_capture | desktop_actuation |
| chrome_proof | desktop_actuation, screenshot_capture |
| environment_discovery | relay_transport, desktop_actuation |
| topology_mapping | environment_discovery |
| relationship_synthesis | topology_mapping |
| ingestion_lane_planning | topology_mapping, relationship_synthesis |
| adapter_autogeneration | topology_mapping, ingestion_lane_planning |
| replay_contract_generation | adapter_autogeneration |
| governance_classification | adapter_autogeneration |
| maturity_evaluation | adapter_autogeneration, replay_contract_generation |
| canonical_instance_separation | topology_mapping |
| proof_persistence | relay_transport |
| founder_confirmation | (root) |
| command_registration | (root) |
| spine_routing | command_registration |
| router_routing | command_registration |
| recursive_planning | adapter_autogeneration, replay_contract_generation, governance_classification, maturity_evaluation |

## Upgrade catalog

| Proposal | Leverage | Governance Risk | Composite |
|----------|---------|----------------|-----------|
| local_adapter_execution | 0.9 | 0.1 | highest |
| relationship_graph_expansion | 0.6 | 0.2 | high |
| cu_adapter_execution | 0.8 | 0.3 | medium |
| multi_platform_ingestion | 0.7 | 0.4 | medium |
| world_model_integration | 0.9 | 0.5 | lower (high risk) |

## Date
2026-05-09
