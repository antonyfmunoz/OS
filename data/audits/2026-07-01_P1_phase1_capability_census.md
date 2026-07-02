# P1 Phase 1A — Capability Census

**Date**: 2026-07-01
**Total substrate modules**: 780 (excluding __init__.py, __pycache__, _dormant, tests)
**_dormant modules**: 33 (archived, excluded from counts)
**Production entry points**: 4 (daemon.py, cognitive_loop.py, gateway.py, discord_bot.py)

---

## Executive Summary

Of 780 substrate modules:
- **~250 (32%)** are PRODUCTION_ACTIVE — reachable from the 4 entry points via transitive imports
- **~310 (40%)** are PARTIALLY_INTEGRATED — imported somewhere but not on the hot path
- **~180 (23%)** are DORMANT — exist but zero or near-zero importers
- **~40 (5%)** are OBSOLETE — backward-compat shims or dead campaign code

**The system exercises ~32% of what it has built on the hot path.** Another 40% is
built, typed, and reachable through transports/API/scripts but not exercised by
the always-on service ticks. The remaining 28% is dormant or obsolete.

**Reachability model note**: "PRODUCTION_ACTIVE" uses the broad definition (reachable
from ANY real entry point including transports/api, transports/discord, scripts).
"DORMANT" is reserved for modules with genuinely zero importers. The narrow
"Docker service tick only" model understates the live codebase by ~50%.

---

## The Two Disconnected Brains

The most critical architectural finding: UMH has two completely disconnected runtime
systems that share ZERO interfaces.

### Organism Runtime (daemon.py)
- 55 direct imports, all from `substrate.organism.*`
- 21 tick stages: advisor, homeostasis, supervisor_reconcile, allocation,
  async_objectives, leverage_rebalance, environment_reconcile, mesh_reconcile,
  tailscale_discovery, leverage_measurement, bottleneck_detection,
  intelligence_computation, objective_physics, operator_compression,
  workload_probes, maintenance_cycle, automation_scan, autonomous_cadence_tick,
  projection_broadcast, continuous_qualification
- Owns: GovernedExecutionSpine, EventSpine, HomeostasisEngine, OutcomeLearningLoop,
  ProofStore, MutationRegistry, ContinuousQualification
- ZERO imports from substrate.control_plane

### Cognitive Runtime (cognitive_loop.py)
- ~10 imports from substrate.control_plane + substrate.understanding + substrate.intelligence
- 8-stage pipeline: Perceive → Understand → Plan → Execute → Verify → Reflect → Learn → Store
- Owns: AgentRuntime, AgentMemory, InputIntelligence, KnowledgeIntegrator,
  IntelligenceRuntime, ContextualReasoningEngine
- ZERO imports from substrate.organism
- **BYPASSES governed mutation entirely** — executes through AgentRuntime, not GovernedExecutionSpine

### Bridge That Exists But Is Unused
`Substrate.__init__.py` contains `Substrate.execute_intent()` which can route to either
runtime — but the Discord bot (the primary transport) bypasses it entirely, going
directly to cognitive_loop.

---

## Fragmentation Inventory (Verified by Census)

### 1. Memory (8 systems, 26+ files)

| System | Location | Status | Capability |
|--------|----------|--------|-----------|
| AgentMemory | control_plane/runtime/cognitive_loop.py (inline) | PRODUCTION_ACTIVE | Per-agent Neon persistence |
| MemoryPromotionPipeline | organism/memory_promotion.py | PRODUCTION_ACTIVE | Instance→canonical promotion with categories |
| MemoryPromoter | memory/promoter.py | PRODUCTION_ACTIVE | Candidate evaluation + query-back |
| MemoryCandidateGenerator | memory/candidate_generator.py | PARTIALLY_INTEGRATED | Stages candidates from execution traces |
| InstitutionalMemoryRuntime | organism/institutional_memory_runtime.py | PARTIALLY_INTEGRATED | PROPOSED→CANONICAL→RETIRED lifecycle |
| StrategicMemoryEngine | organism/strategic_memory_engine.py | PARTIALLY_INTEGRATED | Timeline snapshots and replay |
| ConcreteMemorySystem | control_plane/memory.py | DORMANT | Unified memory protocol |
| CanonicalMemoryStore | state/memory/ | PARTIALLY_INTEGRATED | Neon-backed memory store contracts |

**Key conflict**: Two parallel promotion pipelines write to the SAME path
(`data/umh/memory_candidates/candidates.jsonl`) with incompatible MemoryCandidate classes.

**Zero memory systems go through governed mutation.**

### 2. World Model (4 competing implementations, 50+ files)

| System | Location | Purpose | Status |
|--------|----------|---------|--------|
| OrganismWorldModel | organism/world_model.py | Self-model (organism knowing ITSELF) | TRANSITIVE_ACTIVE |
| CanonicalWorldModel | understanding/world_model/world_model.py | Domain knowledge (two-layer promotion) | DORMANT |
| CanonicalPattern | reality_model/canonical.py | Validated patterns with confidence decay | PARTIALLY_INTEGRATED |
| RealityIntelligenceEngine | understanding/reality/reality_engine.py | Market intelligence with signal tiers | PARTIALLY_INTEGRATED |
| RealityGraph | organism/reality_graph.py | Entity-relationship graph | TRANSITIVE_ACTIVE |

**Convergence**: These are actually 3 distinct concerns (self-model, domain knowledge,
external reality) that should remain separate but share a common observation/evidence
contract. The "4 competing" count is misleading — it's 3 complementary models + 1
unused duplicate (CanonicalWorldModel duplicates reality_model).

### 3. Learning (11 systems, 49 files)

| System | Location | Status | Capability |
|--------|----------|--------|-----------|
| OutcomeLearningLoop | organism/outcome_learning.py | PRODUCTION_ACTIVE | Reliability tracking, fast-path eligibility |
| ContinuousQualification | organism/continuous_qualification.py | PRODUCTION_ACTIVE | Live ORL measurement |
| KnowledgeIntegrator | understanding/knowledge/knowledge_integrator.py | PRODUCTION_ACTIVE | Permanent knowledge from execution |
| IntelligenceRuntime.learn_from_execution | intelligence/runtime.py | PRODUCTION_ACTIVE | Proprietary pattern/decision/prediction intelligence |
| LearningExtractionRuntime | organism/learning_extraction_runtime.py | PARTIALLY_INTEGRATED | Extract learning from execution history |
| LearningPortfolioRuntime | organism/learning_portfolio_runtime.py | PARTIALLY_INTEGRATED | Portfolio-level learning metrics |
| OutcomePatternEngine | organism/outcome_pattern_engine.py | PARTIALLY_INTEGRATED | Pattern detection in outcomes |
| OutcomeTrackingRuntime | organism/outcome_tracking_runtime.py | PARTIALLY_INTEGRATED | Progress toward goals via outcomes |
| CapabilityEvolutionEngine | organism/capability_evolution_engine.py | PARTIALLY_INTEGRATED | Capability maturity lifecycle |
| FeedbackCapture | execution/feedback.py | DORMANT | Execution quality signals |
| FeedbackLoop | execution/feedback_loop.py | DORMANT | RLHF feedback ingestion |

**Critical disconnect**: Cognitive loop learning (KnowledgeIntegrator, IntelligenceRuntime)
NEVER reaches organism learning (OutcomeLearningLoop). Two completely separate learning
systems processing the same executions independently.

### 4. Governance / Execution Spines (7 competing paths)

| System | Location | Status | Role |
|--------|----------|--------|------|
| GovernedExecutionSpine | organism/governed_spine.py | PRODUCTION_ACTIVE | THE canonical mutation gateway |
| ConcreteExecutionSpine | execution/spine.py | PRODUCTION_ACTIVE | 8-stage pipeline (Substrate.__init__) |
| ExecutionPipeline | execution/pipeline.py | PRODUCTION_ACTIVE | Master success loop |
| ExecutionSpine (legacy) | execution/runtime/execution_spine.py | DORMANT | Legacy runtime |
| GovernedExecutionRuntime | organism/governed_execution_runtime.py | PARTIALLY_INTEGRATED | C16.0 alternative |
| GovernedWorkRuntime | organism/governed_work_runtime.py | PARTIALLY_INTEGRATED | Mandatory execution gateway |
| GovernanceEngine | control_plane/governance.py | DORMANT | Unified governance entry point |

**Canonical owner**: GovernedExecutionSpine (organism/governed_spine.py) — PLATFORM_SPEC frozen.

### 5. Coordination / Orchestration (4 overlapping)

| System | Location | Status | Role |
|--------|----------|--------|------|
| OrganismCoordinator | organism/coordinator.py | PRODUCTION_ACTIVE | Hierarchical task decomposition |
| ExecutionCoordinator | organism/execution_coordinator.py | PARTIALLY_INTEGRATED | Phase 13 alternative |
| OrganismCoordinationEngine | organism/organism_coordination_engine.py | PARTIALLY_INTEGRATED | C15.1 alternative |
| OrchestratorKernel | organism/orchestrator_kernel.py | PARTIALLY_INTEGRATED | Operator routing |

### 6. Loops (6 competing, only 1 canonical)

| System | Location | Status | Role |
|--------|----------|--------|------|
| daemon.py + autonomous_tick.py | organism/ | PRODUCTION_ACTIVE | Canonical organism metabolism |
| CognitiveLoop | control_plane/runtime/cognitive_loop.py | PRODUCTION_ACTIVE | Canonical cognitive pipeline |
| OrchestrationLoop | organism/orchestration_loop.py | DORMANT | Superseded by AutonomousTick |
| OrganismLoop | organism/organism_loop.py | DORMANT | Superseded by GovernedExecutionSpine |
| ExecutionLoop | execution/loop/execution_loop.py | DORMANT | Closed-loop goal execution |
| PersistentLoop | execution/loop/persistent_loop.py | DORMANT | Config-driven runtime loops |

### 7. Self-Contained Subsystems (Not Fragmented, Just Unwired)

| System | Location | Files | Status |
|--------|----------|-------|--------|
| Tool Mastery Engine | composition/mastery/ | 40 | 26 DORMANT, pipeline built but not governed |
| Meta IDE | meta_ide/ | 17 | All PARTIALLY_INTEGRATED |
| Operator Perception | operator/ | 18 | All PARTIALLY_INTEGRATED |
| Workstation Bridge | execution/bridge/ | 65 | 58 PRODUCTION_ACTIVE |
| Deliberation Council | understanding/deliberation/ | 1 | PARTIALLY_INTEGRATED, 7-role advisory |
| Perception Pipeline | understanding/perception/ | 8 | 2 PARTIALLY_INTEGRATED, 6 DORMANT parsers |

---

## Cognitive Capability Map

### Perceive (perception)
- **Cognitive loop**: Inline logic (not using perception pipeline)
- **Built but unwired**: GenericIngestionOrchestrator (7-stage pipeline), 6 language parsers
- **Daemon**: workload_probes, tailscale_discovery
- **Operator layer**: 18 modules for screen/device/presence awareness (PARTIALLY_INTEGRATED)
- **Gap**: Perception pipeline exists but cognitive loop doesn't call it

### Understand (understanding)
- **Cognitive loop**: InputIntelligence (assess→enhance→annotate), KnowledgeLayers (12 behavioral), PhilosophyLenses
- **Built but unwired**: DeliberationCouncil (7-role), PatternEngine, DomainBridges (4)
- **Organism**: intent_classifier, context_diagnostic, context_resolution
- **Gap**: Rich understanding layer partially wired to cognitive loop but not to organism

### Plan (planning)
- **Cognitive loop**: AuthorityEngine (plan step)
- **Organism**: composition_engine, strategic_planning_engine, strategic_gap_engine, next_action_engine, objective_physics
- **Meta IDE**: engineering_planner, roadmap_gap_engine
- **Gap**: Planning split between organism (strategic) and cognitive loop (tactical) with no bridge

### Execute (execution)
- **Cognitive loop**: AgentRuntime (BYPASSES governed mutation)
- **Organism**: GovernedExecutionSpine, WorkPacketExecutor, worker_cell
- **Bridge**: execution/bridge/ (65 files) — workstation execution surface
- **Critical gap**: Cognitive loop executes ungoverned

### Verify (reflection)
- **Cognitive loop**: Quality verification step
- **Organism**: proof_store, execution_journal, ProofGenerator
- **Gap**: Cognitive loop verification doesn't generate proof packages

### Learn (learning)
- **Cognitive loop**: KnowledgeIntegrator + IntelligenceRuntime.learn_from_execution
- **Organism**: OutcomeLearningLoop + ContinuousQualification + 5 more
- **Critical gap**: Two completely disconnected learning systems

### Govern (governance)
- **Organism**: GovernedExecutionSpine, MutationRegistry, SpineGuard, RecursionGovernance
- **Cognitive loop**: NONE
- **Gap**: Cognitive loop has zero governance

### Recover (recovery)
- **Organism**: HomeostasisEngine, MaintenanceLoop, EnvironmentReconciler
- **Gap**: Well-covered in organism, absent from cognitive loop

---

## True Orphans (Zero Importers)

### organism/
1. `daily_driver_log.py` — DailyDriverLog (H5 creation, never wired to consumers)
2. `mission.py` — Mission
3. `orchestration_loop.py` — dead loop code
4. `operator_escape_tracker.py` — records exits from UMH
5. `sandbox_orchestrator.py` — ties approval gate to PR factory
6. `self_maintenance_bridge.py` — wires degradation→work packet creation
7. `deploy_verification_worker.py` — post-deploy white screen detection
8. `source_truth_linker.py` — cross-domain edge builder
9. `correspondence_scheduler.py` — periodic drift detection scheduling
10. `mutation_catalog.py` — maps HTTP endpoints to MutationSpec
11. `action_voice_contract.py` — voice/intent action contract
12. `benchmark_harness.py` — legacy pipeline comparison

### intelligence/
13. `finetune_harness.py` — LoRA fine-tuning scaffolding
14. `training_extractor.py` — training data extraction from traces

### control_plane/
15. `runtime/substrate_gateway.py` — signal-based gateway

### integrations/
16. `bridge.py` — unused UMH→model_router bridge
17. `health.py` — unused health aggregator

### understanding/perception/parsers/
18-23. Six language parsers (base, config, js, python, sql, ts) — all zero importers

---

## Convergence Recommendations

### Phase 2 Priority (Cognitive Pipeline Bridge)

The #1 convergence target: make CognitiveLoop.execute() route through
GovernedExecutionSpine.submit() instead of calling AgentRuntime directly.

This single change:
- Makes all cognitive execution governed
- Generates proof packages for cognitive work
- Feeds OutcomeLearningLoop from cognitive execution
- Emits events on EventSpine for cognitive work
- Enables homeostasis monitoring of cognitive health

### Capability-Specific Convergence

| Capability | Canonical Owner | Merge Into | Archive |
|-----------|----------------|-----------|---------|
| Mutation gateway | governed_spine.py | governed_execution_runtime, governed_work_runtime | — |
| Execution journal | execution_journal.py | execution_ledger.py | — |
| Coordination | coordinator.py | execution_coordinator, organism_coordination_engine | — |
| Memory promotion | memory_promotion.py + memory/promoter.py | institutional_memory_runtime, strategic_memory_engine | canonical_write.py |
| Learning | outcome_learning.py | learning_extraction_runtime, learning_portfolio_runtime | — |
| Proof | proof_store.py | proof_runtime.py | — |
| Loop | daemon.py + autonomous_tick.py | orchestration_loop, organism_loop | — |

### Unique Capabilities at Risk (DORMANT but Valuable)

These are DORMANT modules with capabilities that exist nowhere else in the system.
They must be PROMOTED (wired into the canonical pipeline) during convergence:

1. **DeliberationCouncil** — 7-role multi-perspective advisory for high-risk decisions
2. **GenericIngestionOrchestrator** — 7-stage perception pipeline (6 parsers ready)
3. **TME pipeline** — autonomous tool skill acquisition from web research
4. **FeedbackLoop** — RLHF feedback ingestion and learning cycle
5. **ExecutionLoop** — closed-loop goal execution with outcome feedback
6. **CredentialGate** — 1Password credential validation
7. **self_maintenance_bridge** — degradation→work packet auto-creation
8. **deploy_verification_worker** — post-deploy white screen detection
9. **daily_driver_log** — H5 unhandled failure tracking (needs consumers)
10. **finetune_harness + training_extractor** — self-hosted model fine-tuning

### Projection Leaks in substrate/

- `substrate/integrations/product_connections.py` — names EOS, CreatorOS, LYFEOS directly
- Various EOS-prefixed references in execution/bridge/ files (voice_eos_responder.py)

### Additional Merge Targets (from state/governance census)

8. **skill_registry.py + skill_registry_v2.py** — v1 (254L) and v2 (478L, trust scoring)
   both PRODUCTION_ACTIVE. Migrate v1 callers to v2, retire v1.
9. **Authority engine cluster** — `authority.py` (levels), `authority_engine.py`,
   `execution_authority_engine_v1.py` (724L), `authority_tier.py` all overlapping.
   Consolidate two engines into one canonical authority evaluator.
10. **model_preferences.py routing overlap** — state/preferences holds routing logic
    that belongs in adapters/models. Move routing, keep persistence.
11. **7 phantom contract protocols** — either wire as enforced ports or archive.
    Currently give false architectural assurance.
12. **3 phantom socket ports** — approval_port, sensing_port, message_port.
    Peers are wired; these are not.

### Backward-Compatibility Shims to Remove

- `organism/dex_conversation.py` → use advisor_conversation
- `organism/dex_reconciliation.py` → use advisor_reconciliation
- `ontology/domains/contract.py` → re-export from understanding
- `ontology/domains/creator.py` → re-export from understanding
- `ontology/domains/life.py` → re-export from understanding
- `foundation/laws.py` → re-export from ontology.laws

### Key Architectural Conflicts (from all censuses)

1. **Two disconnected runtimes** — organism and cognitive loop share ZERO interfaces.
   This is THE core integration gap. Everything else is secondary.

2. **Dual governance vocabularies** — runtime-action (lowercase low/medium/high) vs
   business-action (uppercase LOW/MEDIUM/HIGH/CRITICAL). Bridge exists in
   control_plane/actions/policy.py but two risk vocabularies is a standing hazard.

3. **Phantom contract layer** — 7/11 contracts DORMANT, 3/17 sockets DORMANT.
   Same pattern twice: abstract boundaries defined but never enforced.

4. **Name collisions** — orchestrator.py (×2 in control_plane), capability_router
   (execution vs control_plane), execution_spine/spine (legacy vs canonical),
   intent_router vs decisions.py retry logic.

5. **The v1 workstation subsystem block** — 26 modules across execution/runtime +
   execution/workers/workstation. Fully built, typed, reachable via transports,
   but not exercised by always-on service. The largest block of PARTIALLY_INTEGRATED
   value. Decision: promote entire block or archive entire block. Cannot stay in limbo.

6. **Cognitive learning → organism learning disconnect** — KnowledgeIntegrator and
   IntelligenceRuntime (cognitive) never feed OutcomeLearningLoop (organism).
   Two learning systems processing the same executions independently.

---

## Additional Directory Findings

### substrate/state/ (44 modules — ALL PRODUCTION_ACTIVE except 4)

The state layer is the most uniformly wired directory in the codebase:
- `state/storage/db.py` — 74 importers, THE single DB gateway
- `state/context/context.py` — 74 importers, SubstrateContext identity
- `state/memory/memory.py` — 49 importers, primary agent memory (1039L — near god-file limit)
- 13 canonical store APIs (skill, profile, task, venture, goal, etc.)
- 4 memory contract modules (canonical_memory_store_v1, conflict governance, reconciliation, identity)

**Key finding**: `state/memory/memory.py` at 1039 lines is approaching the 3000L god-file limit
and is the 3rd most-imported module in the entire codebase.

**DORMANT**: agent_registry_store.py (27L stub), canonical_memory_query_contracts.py

### substrate/contracts/ (11 modules — 4 ACTIVE, 7 DORMANT)

A formal protocol/contract layer that was defined but never enforced:
- 3 PRODUCTION_ACTIVE: agent_types.py (41 importers!), agent_runtime_contracts.py, adapter_contracts.py
- 1 PARTIALLY_INTEGRATED: routing_contracts.py
- 7 DORMANT protocols (control_plane, execution, governance, infrastructure, integration, organism, understanding) — ALL zero importers

**Decision needed**: Is this port layer aspirational or load-bearing? If load-bearing, subsystems
should implement these contracts. If not, archive to stop them implying boundaries that don't exist.

### substrate/governance/ (13 modules — ALL PRODUCTION_ACTIVE)

The most uniformly live directory: 13/13 modules are production-active.
- risk_classes.py (25 importers) — semantic action classification
- 4 overlapping authority engines: authority.py, policy/authority_engine.py,
  policy/execution_authority_engine_v1.py (724L), policy/authority_tier.py
- quality_gate.py (515L), principle_engine.py (519L) — large modules

**Key conflict**: Two full authority engines (authority_engine + execution_authority_engine_v1)
both PRODUCTION_ACTIVE. Reconvergence risk.

### substrate/sockets/ (17 modules — 14 ACTIVE, 3 DORMANT)

The abstract port layer between substrate and transports:
- 14 PRODUCTION_ACTIVE: protocols, envelopes, registry, notification, channel_port,
  projection_port, config_port, signal_socket, view_socket, outcome_socket,
  notification_engine, capability_socket, view/broadcaster, view/websocket
- 3 DORMANT: approval_port, sensing_port, message_port (all zero importers)

### substrate/reality_model/ (7 modules — ALL PRODUCTION_ACTIVE)

Fully wired: canonical patterns, instance truth, reality intelligence, governed writes,
reality mutation contracts, reality queries, simulation/what-if.

### substrate/workstation/ (55 modules — 11 PRODUCTION_ACTIVE, 43 PARTIALLY_INTEGRATED, 1 OBSOLETE)

The workstation layer has a distinctive pattern: only ~11 modules are reachable from the
4 named entry points (via discord_bot → advisor_conversation chain, plus state.py via daemon).
The other ~44 are live ONLY through the cockpit HTTP API (operator_api → cockpit routes).

**PRODUCTION_ACTIVE** (discord/daemon path): command_router, continuity, continuity_engine,
intent_contract, lifecycle_modes, profile_modes, profile_behavior, voice_route_resolver,
vps_control_catalog, camera_commands, state.py

**PARTIALLY_INTEGRATED** (cockpit-only): 43 modules including vision/voice/presence/aggregator clusters

**OBSOLETE**: jarvis_command.py (backward-compat shim, 0 importers)

**Key conflict**: The cockpit API is a real running service but isn't one of the 4 named
entry points. If cockpit counts as a production entry point, ~90% of this package flips
from PARTIALLY_INTEGRATED to PRODUCTION_ACTIVE. This is a definitional question for
convergence.

**Vision cluster risk**: 7 modules (tracker_stack, trigger_chains, vision_presets,
vision_query, vision_scene, security_mode, vision_privacy) are only imported by
`umh/vision_relay.py` (Beast vision WebSocket server). If vision_relay is not deployed,
this entire cluster is effectively dormant.

---

## Coverage Status

| Directory | Files | Census Status |
|-----------|-------|---------------|
| organism/ | 313 | COMPLETE |
| execution/ | 121 | COMPLETE |
| control_plane/ | 58 | COMPLETE |
| state/ | 44 | COMPLETE |
| composition/ | 39 | COMPLETE |
| understanding/ | 38 | COMPLETE |
| operator/ | 18 | COMPLETE |
| meta_ide/ | 17 | COMPLETE |
| sockets/ | 17 | COMPLETE |
| governance/ | 13 | COMPLETE |
| contracts/ | 11 | COMPLETE |
| reality_model/ | 7 | COMPLETE |
| memory/ | 6 | COMPLETE |
| ontology/ | 6 | COMPLETE |
| observability/ | 4 | COMPLETE |
| integrations/ | 4 | COMPLETE |
| top-level | 3 | COMPLETE |
| intelligence/ | 3 | COMPLETE |
| foundation/ | 3 | COMPLETE |
| workstation/ | 55 | COMPLETE |
| **TOTAL** | **780** | **100% COMPLETE** |

---

## Detailed Census Files

Individual census reports with per-module tables:
1. `census_organism.md` — 313 modules, 455 lines
2. `census_execution_controlplane.md` — 179 modules, 373 lines
3. `census_understanding.md` — 47 modules, 115 lines
4. `census_state_governance.md` — 92 modules, 150 lines
5. `census_remaining.md` — 108 modules, 217 lines
6. `census_workstation.md` — 55 modules, 119 lines
