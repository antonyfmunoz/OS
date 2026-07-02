# P1 Phase 1 — Capability Census

**Date**: 2026-07-01
**Total substrate modules**: 878 Python files
**Classified**: 878/878 (100%)

---

## Executive Summary

UMH has two disconnected cognitive architectures that share ZERO cross-references:

1. **Organism Runtime** (`daemon.py`) — governs mutations, monitors health, learns from outcomes, manages autonomous operation. Directly imports 55 modules. All execution goes through `GovernedExecutionSpine.submit()`.

2. **Cognitive Runtime** (`cognitive_loop.py`) — processes operator conversation through 8 cognitive stages (Perceive→Understand→Plan→Execute→Verify→Reflect→Learn→Store). Imports from state/, contracts/, governance/, intelligence/. Execution calls `AgentRuntime.run()` with NO governed mutation.

The organism can govern but can't think. The cognitive loop can think but doesn't govern. This is THE #1 integration gap.

**878 substrate modules** break down as:

| Status | Count | % |
|--------|-------|---|
| PRODUCTION_ACTIVE | ~75 | 9% |
| TRANSITIVE_ACTIVE | ~90 | 10% |
| PARTIALLY_INTEGRATED | ~400 | 46% |
| DORMANT | ~280 | 32% |
| OBSOLETE | ~33 | 4% |

Only **19%** of the substrate is reachable from production entry points.

---

## 1A. Module Classification by Directory

### substrate/organism/ (318 files) — Organism Runtime

The largest directory. Contains the daemon lifecycle, governed mutation, and all autonomous operation.

- **55 PRODUCTION_ACTIVE** (daemon direct imports): governed_spine, event_spine, execution_journal, mutation_registry, homeostasis, outcome_learning, continuous_qualification, proof_store, memory_promotion, template_registry, store, advisor, coordinator, allocation_loop, autonomous_tick, autonomous_cadence, autonomous_action_gateway, automation_pipeline, maintenance_loop, spine_guard, recursion_governance, runtime_supervisor, runtime_graph, environment_graph, environment_reconciler, mesh_reconciler, tailscale_discovery, bottleneck_engine, leverage_engine, leverage_metrics, leverage_assimilation, objective_physics, objective_queue, operator_compression, workload_probes, workload_runner, worker_cell, workcell_daemon, workcell_protocol, agent_capability_model, assisted_executor, plan_execution_adapter, candidate_supply_engine, capability_compounding_runtime, readiness_model, dev_session_tracker, projection_port, approval_store, propagation_wiring, next_action_engine, async_coordinator, execution_modes, execution_economy
- **~50 TRANSITIVE_ACTIVE**: action_envelope, protocols, world_model, reality_graph, presence_runtime, composition_engine, intent_classifier, work_packet*, universal_work_queue, agent_registry, etc.
- **~130 PARTIALLY_INTEGRATED**: council, decisions, strategic engines, goal engines, capability engines, delegation, distributed runtime, session/profile runtimes, production runtimes, context/reconciliation engines, etc.
- **~30 DORMANT**: operator_loop_runtime, orchestration_loop, organism_loop, sandbox_orchestrator, deploy_verification_worker, daily_driver_log, source_truth_linker, mutation_catalog, benchmark_harness, etc.
- **2 OBSOLETE**: dex_conversation (shim), dex_reconciliation (shim)

**Subdirectories**: audits/ (7, all DORMANT), benchmarks/ (24, mostly DORMANT), executors/ (5, mixed), self_use/ (7, PARTIALLY_INTEGRATED)

### substrate/understanding/ (54 files) — Knowledge & Perception

Contains domain bridges, knowledge layers, embeddings, parsers, intelligence engines, and world model.

- **8 PRODUCTION_ACTIVE**: input_intelligence, person_recognition, knowledge_integrator, knowledge_layers, philosophy_lenses, contextual_reasoning (ontology/primitives), leverage_patterns
- **22 PARTIALLY_INTEGRATED**: domain bridges, embedding engines, stakeholder map, pattern engine, ingestion orchestrator, research engine, world pulse, etc.
- **13 DORMANT**: 6 language parsers (Python/JS/TS/SQL/config/base), interpretation engine v1, competitive intel, breadth expansion, etc.

### substrate/intelligence/ (4 files) — Proprietary Intelligence

- **1 PRODUCTION_ACTIVE**: IntelligenceRuntime (3-layer non-LLM intelligence: patterns, decisions, predictions)
- **2 DORMANT**: finetune_harness (LoRA scaffolding), training_extractor (trace→training data)

### substrate/memory/ (7 files) — Memory Pipeline

- **1 PRODUCTION_ACTIVE**: MemoryPromoter (candidate evaluation + queryback)
- **4 PARTIALLY_INTEGRATED**: auto_reconciler, candidate_generator, canonical_write, watcher
- **1 DORMANT**: claude_bridge (Claude Code memory sync)

### substrate/execution/ (133 files) — Execution Infrastructure

Contains ConcreteExecutionSpine (8-stage request pipeline), runtime contracts, feedback loop, execution loop, persistent loop, CPU gate, ingestion, and task pipeline.

- ConcreteExecutionSpine (pipeline.py, 18 importers) — the request execution path
- CPU gate — production-enforced subprocess safety
- feedback.py, trace.py — production execution recording
- 8+ execution pipeline variants with overlapping responsibilities

### substrate/control_plane/ (77 files) — Cognitive Pipeline & Context

Contains CognitiveLoop (1539 lines), Gateway (1927 lines), context builders, signal routing, and orchestrator pipeline.

- CognitiveLoop — THE cognitive processing pipeline
- Gateway — EntrepreneurOSGateway, creates CognitiveLoop
- Context builder — assembles execution context
- Signal routing — SignalEnvelope lifecycle

### substrate/state/ (63 files) — State Management

Contains SubstrateContext, AgentMemory, Neon DB layer, BIS (Business Intelligence State), and venture knowledge.

### substrate/governance/ (19 files) — Policy Layer

Contains AuthorityEngine, risk classification, validation engines, completeness checks.

### substrate/workstation/ (56 files) — Workstation Capabilities

Contains browser, workspace, terminal, and documentation capabilities.

### substrate/composition/ (45 files) — Tool Mastery Engine

Self-contained research→author→management pipeline. 26/40 substantive files are DORMANT. Core capability: autonomous tool skill acquisition from web research. Should be wired as governed capability.

### substrate/operator/ (19 files) — Operator Perception

Operator presence, intent classification, screen awareness, device continuity. All PARTIALLY_INTEGRATED. Should feed into cognitive pipeline's PERCEIVE stage.

### substrate/sockets/ (19 files) — Abstract Ports

Broadcaster, channel ports, view layer. Infrastructure for projection-agnostic state delivery.

### substrate/contracts/ (12 files) — Runtime Contracts

AgentRuntime contracts, TaskType, ModelProvider. PRODUCTION_ACTIVE core.

### substrate/meta_ide/ (18 files) — Engineering Intelligence

Engineering planning, workspace observation, review packages. All PARTIALLY_INTEGRATED.

### substrate/reality_model/ (8 files) — Canonical Patterns

CanonicalPattern with confidence decay, entity relationships. PARTIALLY_INTEGRATED.

### substrate/observability/ (5 files) — Error & Trace

error_recorder (11 importers, PRODUCTION_ACTIVE), jsonl_rotation, outcome_classifier, trace_store.

### substrate/ontology/ (8 files) — Laws & Primitives

Governing laws, computational physics primitives. 3 backward-compat shims to understanding/domains/.

### substrate/foundation/ (4 files) — Identity & Laws

Identity continuity, substrate laws (re-export), perspective schema.

### substrate/integrations/ (5 files) — Bridges

CORS, product connections. Mostly DORMANT. product_connections.py has projection leak.

### substrate/ (top-level, 4 files)

types.py (48 importers), self_model.py (21 importers), canonical_types.py, __init__.py. All PRODUCTION_ACTIVE.

---

## 1B. Capability Dependency Graph

### The Two Disconnected Brains

```
COGNITIVE RUNTIME                    ORGANISM RUNTIME
(processes conversation)             (runs autonomously)

CognitiveLoop                        daemon.py
├─ PERCEIVE (inline)                 ├─ 21 tick stages
├─ UNDERSTAND                        ├─ GovernedExecutionSpine
│  ├─ InputIntelligence              ├─ Homeostasis (9 dimensions)
│  ├─ MemoryPromoter.queryback()     ├─ OutcomeLearning
│  ├─ KnowledgeLayerEngine           ├─ ProofStore
│  ├─ PhilosophyLenses               ├─ EventSpine
│  └─ PatternMatching                ├─ MutationRegistry (46 types)
├─ PLAN (AuthorityEngine)            ├─ SLO enforcement
├─ EXECUTE (AgentRuntime.run())      ├─ Continuous qualification
├─ VERIFY (quality loop)             ├─ TemplateRegistry
├─ REFLECT                           ├─ Leverage/bottleneck
├─ LEARN                             ├─ Autonomous improvement
│  ├─ AgentMemory.log_event()        └─ RuntimeSupervisor
│  ├─ KnowledgeIntegrator
│  └─ IntelligenceRuntime
└─ STORE

         × ZERO CROSS-REFERENCES ×

SHARED: SubstrateContext, self_model, types.py, error_recorder
NOT SHARED: governance model, execution path, memory, learning, events
```

### Capability Coverage Matrix

| Capability | Cognitive Loop | Organism Daemon | Integration |
|------------|---------------|-----------------|-------------|
| **Perception** | PERCEIVE (inline) | tailscale, workload, mesh | NONE |
| **Understanding** | 5-layer enrichment | intent_classifier (for work) | NONE |
| **Reasoning** | NONE | council (partial) | NONE |
| **Planning** | AuthorityEngine only | composition_engine, strategic | NONE |
| **Execution** | AgentRuntime.run() | GovernedSpine.submit() | NONE |
| **Memory** | AgentMemory, KnowledgeIntegrator | memory_promotion (governed) | NONE |
| **Learning** | 3 uncoordinated pathways | outcome_learning (governed) | NONE |
| **Recovery** | NONE | homeostasis (9 dim) | NONE |
| **Self-model** | NONE | world_model, readiness | NONE |
| **Governance** | AuthorityEngine | GovernedSpine + MutationRegistry | NONE |
| **Prediction** | NONE | leverage, bottleneck, projection | NONE |
| **Reflection** | REFLECT stage (no persistence) | execution_journal, proof_store | NONE |

Every cell in the Integration column is NONE. The two brains share zero capabilities.

---

## 1C. Fragmentation Inventory

### CRITICAL: Execution Pipeline Fragmentation (8 implementations)

| # | Module | Lines | Importers | Purpose |
|---|--------|-------|-----------|---------|
| 1 | `organism/governed_spine.py` | 889 | 9 | Governed mutation gateway (CANONICAL) |
| 2 | `control_plane/runtime/cognitive_loop.py` | 1539 | 2 | Cognitive processing pipeline |
| 3 | `execution/pipeline.py` | 557 | 18 | ConcreteExecutionSpine (request processing) |
| 4 | `execution/loop/persistent_loop.py` | 407 | 8 | Persistent execution loop |
| 5 | `execution/loop/execution_loop.py` | 328 | 3 | Execution loop variant |
| 6 | `execution/bridge/task_pipeline.py` | 480 | 4 | Task pipeline bridge |
| 7 | `execution/feedback_loop.py` | 491 | 2 | Feedback loop |
| 8 | `control_plane/runtime/orchestrator/pipeline.py` | 276 | 0 | Orchestrator pipeline (ORPHANED) |

**Total**: 4,967 lines of execution pipeline code. Three are production-active (#1, #2, #3). Five are partially integrated or orphaned.

### HIGH: Governance Model Split (3 implementations)

| # | Module | Importers | Purpose |
|---|--------|-----------|---------|
| 1 | `organism/governed_spine.py` | 9 | THE canonical mutation gateway |
| 2 | `organism/governed_execution_runtime.py` | 9 | Campaign 16.0 alternative |
| 3 | `organism/governed_work_runtime.py` | 5 | Mandatory execution gateway |

All three define governance over execution. Only #1 is the canonical contract (PLATFORM_SPEC.md frozen). #2 and #3 should route through #1.

### HIGH: Memory System Fragmentation (8 systems)

| # | System | Location | Used By |
|---|--------|----------|---------|
| 1 | AgentMemory | state/memory/ | CognitiveLoop |
| 2 | memory_promotion | organism/ | Daemon |
| 3 | MemoryPromoter | memory/ | CognitiveLoop (queryback) |
| 4 | MemoryCandidateGenerator | memory/ | Partially |
| 5 | institutional_memory_runtime | organism/ | Partially |
| 6 | strategic_memory_engine | organism/ | Partially |
| 7 | claude_bridge | memory/ | Dormant |
| 8 | canonical_write | memory/ | Orphaned |

Two parallel promotion pipelines (#2 and #3) write to the SAME file path with incompatible formats.

### HIGH: World Model Fragmentation (4 competing models)

| # | Module | Focus | Importers |
|---|--------|-------|-----------|
| 1 | `organism/world_model.py` | Self-model (organism health, subsystem status) | 13 |
| 2 | `understanding/world_model/world_model.py` | Domain knowledge (canonical + instance layers) | 1 |
| 3 | `reality_model/canonical.py` | Validated patterns (confidence decay, relationships) | ~5 |
| 4 | `understanding/reality/reality_engine.py` | Market intelligence (signal tiers, truth reports) | 3 |

Four classes named or functioning as "world model" with different focuses. Only #1 has significant integration.

### HIGH: Council/Deliberation Duplication (2 implementations)

| # | Module | Importers | Roles |
|---|--------|-----------|-------|
| 1 | `understanding/deliberation/council.py` | 2 | 7 roles (strategist, skeptic, completeness, risk, domain, engineer, synthesis) |
| 2 | `organism/council.py` | 2 | Different role set, different class name |

Two independent advisory councils with different role enums and no shared contract.

### HIGH: Coordination/Orchestration Overlap (4+ implementations)

| # | Module | Importers | Purpose |
|---|--------|-----------|---------|
| 1 | `organism/coordinator.py` | 10 | Hierarchical task decomposition (CANONICAL) |
| 2 | `organism/execution_coordinator.py` | 11 | Phase 13 orchestration |
| 3 | `organism/organism_coordination_engine.py` | 2 | C15.1 coordination |
| 4 | `organism/orchestrator_kernel.py` | 4 | Operator routing |

### HIGH: Learning System Fragmentation (9+ systems)

| # | System | Used By |
|---|--------|---------|
| 1 | outcome_learning | Daemon (governed) |
| 2 | CognitiveLoop.learn() | 3 uncoordinated pathways |
| 3 | template_registry | Daemon (template storage) |
| 4 | continuous_qualification | Daemon (SLO measurement) |
| 5 | learning_extraction_runtime | Partially |
| 6 | learning_portfolio_runtime | Partially |
| 7 | capability_evolution_engine | Partially |
| 8 | compounding_engine | Partially |
| 9 | capability_compounding_runtime | Daemon (partial overlap with #8) |

### MEDIUM: Planning Fragmentation (8 implementations)

| # | Module | Importers | Purpose |
|---|--------|-----------|---------|
| 1 | composition_engine | 11 | Deterministic intent→plan |
| 2 | strategic_planning_engine | 7 | Strategic planning |
| 3 | strategic_gap_engine | 14 | Gap analysis (most-connected) |
| 4 | plan_execution_adapter | 8 | Plan→spine bridge |
| 5 | engineering_planner | 4 | Engineering-specific planning |
| 6 | roadmap_gap_engine | 3 | Engineering roadmap gaps |
| 7 | next_action_engine | 2 | Action recommendation |
| 8 | priority_engine | 1 | Priority calculation |

### MEDIUM: Decision System Fragmentation (5 implementations)

| # | Module | Importers |
|---|--------|-----------|
| 1 | decision_registry | 6 |
| 2 | decision_impact_engine | 5 |
| 3 | decision_lineage_engine | 2 |
| 4 | decision_validity_engine | 5 |
| 5 | contradiction_engine | 11 |

### MEDIUM: Perception Fragmentation

- CognitiveLoop.PERCEIVE (inline) — conversation input
- 6 language parsers (DORMANT) — code perception
- GenericIngestionOrchestrator (PARTIALLY_INTEGRATED) — 7-stage pipeline
- screen_observation_engine — visual workspace
- workspace_observation — engineering state
- founder_capture — task/idea detection from Discord
- tailscale_discovery — network perception
- workload_probes — operational pressure

All disconnected. No unified perception model.

### LOW: Backward-Compatibility Shims (can be removed)

1. `organism/dex_conversation.py` → `advisor_conversation.py`
2. `organism/dex_reconciliation.py` → `advisor_reconciliation.py`
3. `ontology/domains/contract.py` → re-export from `understanding/domains/contract.py`
4. `ontology/domains/creator.py` → re-export from `understanding/domains/creator.py`
5. `ontology/domains/life.py` → re-export from `understanding/domains/life.py`
6. `foundation/laws.py` → re-export from `ontology/laws.py`

---

## 1D. True Orphans (zero importers across entire codebase)

| Module | Unique Capability | Disposition |
|--------|-------------------|-------------|
| `organism/daily_driver_log.py` | H5 failure tracking | WIRE to homeostasis consumers |
| `organism/source_truth_linker.py` | Cross-domain edge builder | WIRE to reality_graph |
| `organism/mutation_catalog.py` | HTTP→MutationSpec mapping | WIRE to cockpit routes |
| `organism/deploy_verification_worker.py` | Post-deploy white-screen detection | WIRE to maintenance_loop |
| `organism/self_maintenance_bridge.py` | Degradation→work packet creation | WIRE to homeostasis |
| `organism/sandbox_orchestrator.py` | Approval gate→PR factory | WIRE to autonomous_improvement_lane |
| `organism/operator_escape_tracker.py` | Records exits from UMH | WIRE to learning |
| `organism/benchmark_harness.py` | Legacy pipeline comparison | ARCHIVE |
| `organism/action_voice_contract.py` | Voice/Intent action contract | ARCHIVE or WIRE |
| `organism/correspondence_scheduler.py` | Periodic drift scheduling | WIRE to maintenance_loop |
| `organism/operator_loop_runtime.py` | "The Jarvis Runtime" — 7-method API | EVALUATE for orchestrator_kernel merge |
| `intelligence/finetune_harness.py` | LoRA fine-tuning scaffolding | PRESERVE for future |
| `intelligence/training_extractor.py` | Trace→training data extraction | PRESERVE for future |
| `control_plane/runtime/substrate_gateway.py` | Signal-based gateway | SUPERSEDED by EntrepreneurOSGateway |
| `control_plane/runtime/orchestrator/pipeline.py` | Orchestrator pipeline | ORPHANED — 0 importers |

---

## 1E. Integration Gaps (ranked by severity)

### GAP-1: EXECUTION SPLIT (CRITICAL)

CognitiveLoop.execute() calls AgentRuntime.run() which bypasses GovernedExecutionSpine entirely. Every conversation-triggered execution is:
- **Ungoverned** — no mutation validation
- **Unproven** — no proof package generated
- **Unjournaled** — no execution journal entry
- **Unevented** — no EventSpine emission
- **Untracked** — no SLO measurement
- **Unlearned** — outcome_learning never sees it

**Impact**: The primary user-facing execution path has no governance.

### GAP-2: LEARNING DISCONNECT (HIGH)

CognitiveLoop.learn() fires three independent pathways:
1. `AgentMemory.log_event()` — per-agent event log
2. `KnowledgeIntegrator.integrate()` — permanent knowledge
3. `IntelligenceRuntime.learn_from_execution()` — proprietary intelligence

Organism learns through `outcome_learning` (governed, reliability tracking).

These five learning channels never share signals. What the cognitive loop learns is invisible to the organism. What the organism learns is invisible to the next conversation.

### GAP-3: MEMORY INCOHERENCE (HIGH)

8 memory systems with no unified API. Two write to the same file path (`data/umh/organism/promoted_memories.jsonl`) with incompatible formats. The cognitive pipeline's memory is invisible to the organism and vice versa.

### GAP-4: MISSING REASONING (HIGH)

No reasoning stage exists in the cognitive pipeline. CognitiveLoop goes UNDERSTAND → PLAN (which is just authority checking). Council, decisions, contradictions, tradeoff analysis — all exist as organism modules but are not used by either production entry point.

### GAP-5: PERCEPTION FRAGMENTATION (MEDIUM)

Organism perceives (network, workload, device state). Cognitive loop perceives (conversation input). Operator perceives (screen, workspace, device continuity). None feed into each other.

### GAP-6: SELF-KNOWLEDGE BLINDNESS (MEDIUM)

Cognitive loop doesn't know organism health, readiness, capabilities, or operational truth when processing a request. The organism doesn't know what the cognitive loop is doing.

### GAP-7: NO COGNITIVE RECOVERY (MEDIUM)

If CognitiveLoop fails, homeostasis can't detect or recover it. No retry, no escalation, no mode change.

### GAP-8: PLANNING GAP (LOW-MEDIUM)

Real planning exists (composition, strategic, gap analysis) but CognitiveLoop.plan() is just authority checking. Planning modules are wired to daemon but not to conversation processing.

---

## 1F. Recommended Canonical Owners per Capability

| Capability | Canonical Owner | Absorbs |
|------------|----------------|---------|
| **Mutation** | GovernedExecutionSpine | governed_execution_runtime, governed_work_runtime |
| **Execution** | ConcreteExecutionSpine + GovernedSpine | cognitive loop execute, all pipeline variants |
| **Coordination** | OrganismCoordinator | execution_coordinator, organism_coordination_engine |
| **Council** | understanding/deliberation/council.py | organism/council.py |
| **Memory** | MemoryPromoter + memory_promotion (governed) | canonical_write, watcher |
| **World Model** | organism/world_model.py (self-model) + reality_model/canonical.py (patterns) | understanding world_model merge into reality |
| **Learning** | outcome_learning (governed) | learning_extraction, portfolio, evolution should feed into it |
| **Planning** | composition_engine + strategic_gap_engine | roadmap_gap_engine, strategic_planning merge |
| **Decisions** | decision_registry | lineage/impact/validity become methods |
| **Events** | EventSpine | no duplicates — already canonical |
| **Proof** | proof_store | proof_runtime merge |
| **Perception** | GenericIngestionOrchestrator (for structured) + CognitiveLoop.perceive() (for conversation) | parsers wire into orchestrator |
| **Recovery** | homeostasis | drift_detection, work_recovery feed into it |
| **Identity** | self_model.py + system_identity.py | foundation/identity.py |

---

## Exit Criteria for Phase 1

- [x] All 878 substrate modules classified by capability and status
- [x] Capability dependency graph mapped with cross-references
- [x] Fragmentation inventory with exact duplicate counts
- [x] 8 integration gaps ranked by severity
- [x] Canonical owner recommended per capability
- [x] True orphan list with disposition recommendation
- [x] Verified totals match `find` ground truth (878)

**Phase 1 is COMPLETE. Phase 2 (Cognitive Pipeline Bridge) is next.**
