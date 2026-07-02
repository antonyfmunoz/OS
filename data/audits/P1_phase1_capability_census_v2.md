# P1 Phase 1 — Capability Census (Complete)

**Date**: 2026-07-01
**Ground truth**: 947 active Python files in substrate/ (excluding __pycache__, _dormant/)
**Including dormant**: 980 total (33 in execution/_dormant/)
**Method**: Import graph analysis from production entry points + per-file classification

---

## 1. Ground Truth File Counts

| Directory | Active Files | Dormant | Total |
|-----------|-------------|---------|-------|
| substrate/organism/ | 387 | 0 | 387 |
| substrate/execution/ | 133 | 33 | 166 |
| substrate/control_plane/ | 77 | 0 | 77 |
| substrate/state/ | 63 | 0 | 63 |
| substrate/workstation/ | 56 | 0 | 56 |
| substrate/understanding/ | 54 | 0 | 54 |
| substrate/composition/ | 45 | 0 | 45 |
| substrate/governance/ | 19 | 0 | 19 |
| substrate/sockets/ | 19 | 0 | 19 |
| substrate/operator/ | 19 | 0 | 19 |
| substrate/meta_ide/ | 18 | 0 | 18 |
| substrate/contracts/ | 12 | 0 | 12 |
| substrate/ontology/ | 8 | 0 | 8 |
| substrate/reality_model/ | 8 | 0 | 8 |
| substrate/observability/ | 5 | 0 | 5 |
| substrate/integrations/ | 5 | 0 | 5 |
| substrate/memory/ | 7 | 0 | 7 |
| substrate/intelligence/ | 4 | 0 | 4 |
| substrate/foundation/ | 4 | 0 | 4 |
| substrate/ (root) | 4 | 0 | 4 |
| **TOTAL** | **947** | **33** | **980** |

Verified: `find substrate/ -name '*.py' -not -path '*/__pycache__/*' -not -path '*/_dormant/*' | wc -l` = 947

---

## 2. Production Entry Points

Three production entry points define "active" vs "dormant":

### Entry Point 1: Discord Bot → Gateway → CognitiveLoop
```
Discord message
  → services/discord_bot.py
  → EntrepreneurOSGateway.handle() [gateway.py, 1927 lines]
    → CognitiveLoop.run() [cognitive_loop.py, 1539 lines]
      → PERCEIVE → UNDERSTAND → PLAN → EXECUTE → VERIFY → REFLECT → LEARN → STORE
```
**Uses**: SubstrateContext, TaskType, AgentRuntime, AgentMemory, AuthorityEngine, VentureKnowledgeBase, IntelligenceRuntime, KnowledgeIntegrator
**Does NOT use**: GovernedExecutionSpine, EventSpine, MutationRegistry, Homeostasis, ProofStore, any organism module

### Entry Point 2: Daemon Autonomous Tick Loop
```
daemon.py → AutonomousTick.cycle() (21 stages, every 5-30s)
  → GovernedExecutionSpine.submit() for all mutations
  → HomeostasisEngine for health monitoring
  → OutcomeLearning for learning
  → ProofStore for evidence
  → EventSpine for pub/sub
```
**Uses**: GovernedExecutionSpine, EventSpine, MutationRegistry, Homeostasis, ProofStore, OutcomeLearning, TemplateLearning, 55 direct organism imports
**Does NOT use**: CognitiveLoop, Gateway, AuthorityEngine, AgentMemory, VentureKnowledgeBase, IntelligenceRuntime

### Entry Point 3: Cockpit API → Substrate.execute_intent()
```
cockpit_organism_routes.py → Substrate.execute_intent()
  → IntentRouter → ConcreteExecutionSpine OR OrganismLoopEngine
```
**Status**: Exists, minimally exercised. Only bridge between the two brains.

### The Core Gap
**Entry points 1 and 2 share ZERO interfaces or imports.** The organism can govern mutations but can't think. The cognitive loop can think but doesn't go through governed mutation.

---

## 3. Production Status Summary

| Status | Count | % of Active |
|--------|-------|-------------|
| PRODUCTION_ACTIVE (daemon direct) | ~55 | 6% |
| PRODUCTION_ACTIVE (cognitive loop/gateway/discord) | ~25 | 3% |
| TRANSITIVE_ACTIVE (reachable from entry points) | ~180 | 19% |
| PARTIALLY_INTEGRATED (imported but not exercised) | ~250 | 26% |
| DORMANT (zero reachability from entry points) | ~370 | 39% |
| OBSOLETE / __init__.py only | ~67 | 7% |
| **Total** | **947** | **100%** |

**Key finding**: Only ~260 of 947 files (27%) are reachable from production entry points. 370+ files (39%) are completely dormant.

---

## 4. Capability Classification

### 4A. Perception (sensing the world)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| CognitiveLoop.perceive() | control_plane/runtime/ | PRODUCTION_ACTIVE | Multimodal input resolution |
| person_recognition.py | understanding/intelligence/ | PRODUCTION_ACTIVE | Recognizes known people in messages |
| founder_capture.py | understanding/signals/ | PARTIALLY_INTEGRATED | Tasks/ideas/reminders from Discord |
| tailscale_discovery.py | organism/ | PRODUCTION_ACTIVE | Network peer detection |
| workload_probes.py | organism/ | PRODUCTION_ACTIVE | Operational pressure measurement |
| workspace_observation.py | meta_ide/ | PARTIALLY_INTEGRATED | Workspace state observation |
| screen_observation_engine.py | operator/ | PARTIALLY_INTEGRATED | Screen context observation |
| orchestrator.py | understanding/perception/ | PARTIALLY_INTEGRATED | Source-agnostic 7-stage ingestion |
| TME research agent | composition/mastery/research/ | DORMANT (18 files) | Tool documentation research |
| Parsers (5 files) | understanding/perception/parsers/ | DORMANT | Python/JS/TS/SQL/config parsing |
| device_presence.py | workstation/ | PARTIALLY_INTEGRATED | Device availability tracking |
| camera_commands.py | workstation/ | PARTIALLY_INTEGRATED | Camera snapshot analysis |

**Gap**: Organism perception (network, workload, device) never feeds into cognitive processing. Operator perception (screen, workspace) wired to neither.

### 4B. Understanding (making sense of input)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| CognitiveLoop.understand() | control_plane/runtime/ | PRODUCTION_ACTIVE | Context + memory + knowledge + philosophy |
| input_intelligence.py | understanding/intelligence/ | PRODUCTION_ACTIVE | 3-stage input enhancement (ASSESS→ENHANCE→ANNOTATE) |
| knowledge_layers.py | understanding/knowledge/ | PRODUCTION_ACTIVE | 12 behavioral distillation layers (110 principles) |
| philosophy_lenses.py | understanding/knowledge/ | PRODUCTION_ACTIVE | Values-based filtering from PHILOSOPHY.md |
| knowledge_integrator.py | understanding/knowledge/ | PRODUCTION_ACTIVE | Permanent knowledge integration |
| knowledge_domains.py | understanding/knowledge/ | PARTIALLY_INTEGRATED | 21 domains across 8 categories |
| knowledge_graph.py | understanding/knowledge/ | PARTIALLY_INTEGRATED | Entity relationships and traversal |
| embedding/embedder.py | understanding/embedding/ | PARTIALLY_INTEGRATED | Text→vector embedding (384-dim) |
| embedding_engine.py | understanding/embedding/ | PARTIALLY_INTEGRATED | Batch embedding + similarity search |
| domain bridges (4 files) | understanding/domains/ | PARTIALLY_INTEGRATED | Business/creator/life domain mapping |
| human_intelligence.py | understanding/intelligence/ | PARTIALLY_INTEGRATED | Human profiling engine |
| stakeholder_map.py | understanding/intelligence/ | PARTIALLY_INTEGRATED | Stakeholder relationship mapping |
| intent_classifier.py | organism/ | TRANSITIVE_ACTIVE | Work intent classification |
| intent_router.py | operator/ | PARTIALLY_INTEGRATED | Intent routing for cockpit |
| voice_query_engine.py | operator/ | PARTIALLY_INTEGRATED | Voice-based queries |
| competitive_intel.py | understanding/intelligence/ | DORMANT | Competitive analysis |
| interpretation_engine_v1.py | understanding/interpretation/ | DORMANT | Multi-stage interpretation |

**Gap**: CognitiveLoop.understand() does context, memory, knowledge, philosophy. Organism has its own understanding (intent classification). Neither uses the rich domain bridges, embedding, or human intelligence.

### 4C. Reasoning (evaluating options, decisions)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| council.py | organism/ | PARTIALLY_INTEGRATED | 7-role advisory council for high-risk decisions |
| council.py | understanding/deliberation/ | PARTIALLY_INTEGRATED | Multi-perspective deliberation (different impl) |
| decision_registry.py | organism/ | PARTIALLY_INTEGRATED | Decision tracking and lineage |
| decision_impact_engine.py | organism/ | PARTIALLY_INTEGRATED | Decision impact assessment |
| decision_validity_runtime.py | organism/ | PARTIALLY_INTEGRATED | Decision validity monitoring |
| contradiction_engine.py | organism/ | PARTIALLY_INTEGRATED (11 importers) | Contradiction detection |
| tradeoff_intelligence_engine.py | organism/ | PARTIALLY_INTEGRATED | Tradeoff analysis |
| assumption_tracking_runtime.py | organism/ | PARTIALLY_INTEGRATED | Assumption lifecycle |
| IntelligenceRuntime | intelligence/ | PRODUCTION_ACTIVE | 3-layer proprietary intelligence |
| contextual_reasoning | understanding/ontology/ | PRODUCTION_ACTIVE | Stage-filtered reasoning |

**Gap**: NO reasoning stage in the cognitive pipeline. CognitiveLoop goes UNDERSTAND → PLAN with no deliberation.

### 4D. Planning (deciding what to do)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| CognitiveLoop.plan() | control_plane/runtime/ | PRODUCTION_ACTIVE | Authority check ONLY |
| composition_engine.py | organism/ | TRANSITIVE_ACTIVE | Deterministic intent→plan |
| strategic_planning_engine.py | organism/ | PARTIALLY_INTEGRATED | Strategic planning |
| strategic_gap_engine.py | organism/ | PARTIALLY_INTEGRATED (14 importers) | Gap analysis |
| goal_alignment_engine.py | organism/ | PARTIALLY_INTEGRATED | Goal alignment checking |
| plan_execution_adapter.py | organism/ | PRODUCTION_ACTIVE | Plans→spine bridge |
| next_action_engine.py | organism/ | PRODUCTION_ACTIVE | Evidence-based action recommendation |
| priority_engine.py | organism/ | PARTIALLY_INTEGRATED | Priority calculation |
| engineering_planner.py | meta_ide/ | PARTIALLY_INTEGRATED | Engineering-specific planning |
| roadmap_gap_engine.py | meta_ide/ | PARTIALLY_INTEGRATED | Roadmap gap detection |
| objective_physics.py | organism/ | PRODUCTION_ACTIVE | Causal execution dynamics |
| objective_queue.py | organism/ | PRODUCTION_ACTIVE | Objective intake |

**Gap**: CognitiveLoop.plan() is just authority checking. Real planning lives in organism modules disconnected from conversation.

### 4E. Execution (doing work)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| CognitiveLoop.execute() | control_plane/runtime/ | PRODUCTION_ACTIVE | AgentRuntime.run() — UNGOVERNED |
| GovernedExecutionSpine | organism/ | PRODUCTION_ACTIVE | THE canonical mutation gateway |
| ConcreteExecutionSpine | execution/spine.py | PARTIALLY_INTEGRATED | 8-stage async pipeline |
| worker_cell.py | organism/ | PRODUCTION_ACTIVE | Bounded task execution |
| workload_runner.py | organism/ | PRODUCTION_ACTIVE | Governed job execution |
| assisted_executor.py | organism/ | PRODUCTION_ACTIVE | Governed maintenance execution |
| agent_executor.py | organism/executors/ | PARTIALLY_INTEGRATED | Governed LLM execution |
| workstation_executor.py | organism/executors/ | PARTIALLY_INTEGRATED | Workstation-routed execution |
| operator_compression.py | organism/ | PRODUCTION_ACTIVE | Automation detection |
| automation_pipeline.py | organism/ | PRODUCTION_ACTIVE | Pattern→automation promotion |

**GAP-1 (CRITICAL)**: CognitiveLoop.execute() calls AgentRuntime.run() which bypasses GovernedExecutionSpine entirely.

### 4F. Memory (retaining knowledge)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| AgentMemory | state/memory/memory.py | PRODUCTION_ACTIVE | Per-agent Neon-backed memory |
| ConversationMemory | state/memory/memory.py | PRODUCTION_ACTIVE | Conversation persistence |
| VentureKnowledgeBase | state/business/ | PRODUCTION_ACTIVE | Venture-specific knowledge |
| memory_promotion.py | organism/ | PRODUCTION_ACTIVE | Governed instance→canonical promotion |
| promoter.py | memory/ | PRODUCTION_ACTIVE | Memory candidate evaluation + queryback |
| candidate_generator.py | memory/ | PARTIALLY_INTEGRATED | Candidate staging from execution traces |
| auto_reconciler.py | memory/ | PARTIALLY_INTEGRATED | Bridging promotion to canonical store |
| CanonicalMemoryStore | state/memory/contracts/ | PRODUCTION_ACTIVE | Canonical memory persistence |
| institutional_memory_runtime.py | organism/ | PARTIALLY_INTEGRATED | Knowledge lifecycle management |
| strategic_memory_engine.py | organism/ | PARTIALLY_INTEGRATED | Timeline snapshots |
| claude_bridge.py | memory/ | DORMANT | Claude Code ↔ substrate memory sync |
| watcher.py | memory/ | PARTIALLY_INTEGRATED | Filesystem watcher for memory dirs |
| UserModel | state/profiles/ | PRODUCTION_ACTIVE | Learns founder communication patterns |

**Gap**: 8+ systems, no unified API. Two promotion pipelines write same file with incompatible formats.

### 4G. Learning (improving from experience)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| CognitiveLoop.learn() | control_plane/runtime/ | PRODUCTION_ACTIVE | 3 uncoordinated pathways |
| outcome_learning.py | organism/ | PRODUCTION_ACTIVE | Reliability tracking, fast-path |
| template_registry.py | organism/ | PRODUCTION_ACTIVE | Reusable execution templates |
| continuous_qualification.py | organism/ | PRODUCTION_ACTIVE | SLO spot checks + hourly |
| learning_extraction_runtime.py | organism/ | PARTIALLY_INTEGRATED | History extraction |
| learning_portfolio_runtime.py | organism/ | PARTIALLY_INTEGRATED | Portfolio metrics |
| capability_evolution_engine.py | organism/ | PARTIALLY_INTEGRATED | Maturity lifecycle |
| compounding_engine.py | organism/ | PARTIALLY_INTEGRATED | Learning→leverage |
| capability_compounding_runtime.py | organism/ | PRODUCTION_ACTIVE | Capability compounding metrics |
| leverage_assimilation.py | organism/ | PRODUCTION_ACTIVE | External knowledge intake |
| TME (22 files) | composition/mastery/ | MOSTLY DORMANT | Tool mastery pipeline |
| finetune_harness.py | intelligence/ | DORMANT | LoRA fine-tuning |
| training_extractor.py | intelligence/ | DORMANT | Training data extraction |

**Gap**: Conversation learning and organism learning never share signals.

### 4H. Recovery (self-healing)

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| homeostasis.py | organism/ | PRODUCTION_ACTIVE | 9-dimension health, mode escalation |
| runtime_supervisor.py | organism/ | PRODUCTION_ACTIVE | Crash detection, restart |
| environment_reconciler.py | organism/ | PRODUCTION_ACTIVE | Environment drift correction |
| maintenance_loop.py | organism/ | PRODUCTION_ACTIVE | Preventive maintenance |
| error_recorder.py | observability/ | PRODUCTION_ACTIVE | Fix-forever error recording |
| work_recovery_runtime.py | organism/ | PARTIALLY_INTEGRATED | Work state recovery |
| service_failure_engine.py | organism/ | PARTIALLY_INTEGRATED | Failure impact analysis |
| drift_detection_engine.py | organism/ | PARTIALLY_INTEGRATED | Unified drift synthesis |

**Gap**: Recovery is organism-only. CognitiveLoop has zero self-healing.

### 4I. World Model

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| world_model.py | organism/ | TRANSITIVE_ACTIVE | Organism self-model |
| world_model.py | understanding/world_model/ | DORMANT | Domain knowledge (two-layer) |
| canonical.py | reality_model/ | PARTIALLY_INTEGRATED | Canonical patterns (confidence decay) |
| instance.py | reality_model/ | PARTIALLY_INTEGRATED | Live operational observations |
| reality_intelligence.py | reality_model/ | PARTIALLY_INTEGRATED | Read-only retrieval + provenance |
| reality_mutation.py | reality_model/ | PARTIALLY_INTEGRATED | Governed observation writes |
| simulation.py | reality_model/ | PARTIALLY_INTEGRATED | Non-mutating hypothesis testing |
| environment_graph.py | organism/ | PRODUCTION_ACTIVE | Operational world-state graph |
| runtime_graph.py | organism/ | PRODUCTION_ACTIVE | Runtime registry |

**Gap**: 3+ competing world models with no unified query.

### 4J. Governance

| Module | Location | Status | Unique Contribution |
|--------|----------|--------|---------------------|
| governed_spine.py | organism/ | PRODUCTION_ACTIVE | THE canonical mutation gateway |
| mutation_registry.py | organism/ | PRODUCTION_ACTIVE | 46 mutation types |
| execution_modes.py | organism/ | PRODUCTION_ACTIVE | OBSERVE/ASSIST/ACT |
| spine_guard.py | organism/ | PRODUCTION_ACTIVE | Recursion/safety |
| authority_engine.py | governance/policy/ | PRODUCTION_ACTIVE | Permission tier checking |
| policy_engine.py | governance/ | PARTIALLY_INTEGRATED | Risk → verdict |
| principle_engine.py | governance/principles/ | PRODUCTION_ACTIVE | Quality standards |
| quality_gate.py | governance/quality/ | PRODUCTION_ACTIVE | 4-value quality gate |
| risk_classes.py | governance/ | PRODUCTION_ACTIVE | Risk categorization |
| laws.py | ontology/ | PRODUCTION_ACTIVE | 14 executable laws |

**Gap**: Two governance models (AuthorityEngine vs GovernedExecutionSpine) that don't coordinate.

---

## 5. Fragmentation Inventory

| Concern | Competing Systems | Files | Key Conflict |
|---------|-------------------|-------|--------------|
| **Execution** | CognitiveLoop, GovernedExecutionSpine, ConcreteExecutionSpine | 3 spines + 5 executors | Cognitive execution UNGOVERNED |
| **Memory** | 8 distinct systems | 26+ | Two pipelines write same file incompatibly |
| **World Model** | 3+ competing models | 50+ | No unified query interface |
| **Learning** | Cognitive (3 paths) + organism + 5 runtimes + TME | 49+ | Never share signals |
| **Planning** | CognitiveLoop.plan() + 8 organism planners | 12+ | CognitiveLoop is authority-check only |
| **Reasoning** | IntelligenceRuntime + 8 organism modules | 10+ | No reasoning stage in cognitive pipeline |
| **Governance** | GovernedExecutionSpine + AuthorityEngine | 17+ | Don't coordinate |
| **Loops** | Daemon + cognitive + spine + 4 operator | 30+ | Zero shared interface |
| **Recovery** | 5 organism modules | 8+ | Zero cognitive self-healing |
| **Perception** | 6+ perception sources | 12+ | Organism↔cognitive perception isolated |

---

## 6. True Orphans (~65 files, 6.9%)

### PROMOTE (unique capability)
1. `intelligence/finetune_harness.py` — LoRA fine-tuning
2. `intelligence/training_extractor.py` — Training data extraction
3. `organism/daily_driver_log.py` — H5 deliverable, unwired
4. `memory/claude_bridge.py` — Claude Code ↔ substrate memory sync

### ARCHIVE (superseded or dead)
5. `control_plane/runtime/substrate_gateway.py`
6. `organism/orchestration_loop.py`
7. `organism/template_seeder.py`
8. `organism/mission.py`
9-15. 7 protocol files in `contracts/` with zero implementations

### EVALUATE (may have value)
16-26. 11 workstation orphans (app_resolver, jarvis_command, loop_engine, security_mode, tracker_stack, trigger_chains, vision_presets, vision_privacy, vision_query, vision_scene, work_lane)
27-46. 20 TME pipeline files (mostly CLI tools)
47-65. 19 state/socket/ontology/integration orphans

---

## 7. Integration Gaps (ranked by severity)

| Rank | Gap | Severity | Description |
|------|-----|----------|-------------|
| GAP-1 | Execution | CRITICAL | CognitiveLoop.execute() bypasses GovernedExecutionSpine — ungoverned |
| GAP-2 | Learning | HIGH | 3 cognitive pathways + organism learning never share signals |
| GAP-3 | Memory | HIGH | 8+ systems, no unified API, incompatible promotion pipelines |
| GAP-4 | Reasoning | HIGH | Zero reasoning stage in cognitive pipeline |
| GAP-5 | Perception | MEDIUM | Organism↔cognitive perception isolated |
| GAP-6 | Self-Knowledge | MEDIUM | Cognitive loop blind to organism state |
| GAP-7 | Recovery | MEDIUM | Zero cognitive self-healing |
| GAP-8 | Planning | LOW-MEDIUM | CognitiveLoop.plan() is authority-check only |

---

## 8. Recommended Canonical Owners

| Capability | Canonical Owner | Convergence Action |
|-----------|----------------|-------------------|
| Perception | CognitiveLoop.perceive() | Wire organism perception as sensing sources |
| Understanding | CognitiveLoop.understand() | Integrate domain bridges, embedding, human intelligence |
| Reasoning | ADD NEW STAGE | Wire council, decisions, contradictions into pipeline |
| Planning | composition_engine + CognitiveLoop | Route real planning through cognitive loop |
| Execution | GovernedExecutionSpine | CognitiveLoop MUST route through governed spine |
| Memory | Unified API (AgentMemory + memory_promotion) | Single interface for both entry points |
| Learning | outcome_learning.py | All learning feeds single governed pipeline |
| Recovery | homeostasis.py | Add cognitive loop health as 10th dimension |
| World Model | reality_model/ | Absorb organism/world_model, retire understanding/world_model |
| Governance | GovernedExecutionSpine + AuthorityEngine | Unify: authority check → governed mutation |

---

## 9. Census Verification

```
Ground truth (find): 947 active files
Classified:  organism 387 + execution 133 + control_plane 77 + state 63 +
  workstation 56 + understanding 54 + composition 45 + governance 19 +
  sockets 19 + operator 19 + meta_ide 18 + contracts 12 + ontology 8 +
  reality_model 8 + observability 5 + integrations 5 + memory 7 +
  intelligence 4 + foundation 4 + root 4 = 947 ✓
```

All 947 active files accounted for. Census complete.
