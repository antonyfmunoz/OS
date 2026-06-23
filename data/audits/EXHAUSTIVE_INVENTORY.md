# EXHAUSTIVE CODEBASE AUDIT - /opt/OS COMPLETE INVENTORY

**Generated:** June 20, 2026  
**Scope:** Every file, directory, subsystem, and module  
**Total Files:** 160,350+  
**Total Code Files:** 3,478 Python + 1,124 TypeScript/React + 611 Documentation

---

# TABLE OF CONTENTS

1. [Root Level Files](#root-level-files)
2. [Substrate (909 files)](#substrate)
3. [Adapters (101 files)](#adapters)
4. [Transports (184 files)](#transports)
5. [Services (27 files)](#services)
6. [Projections (48 files)](#projections)
7. [Tests (287 files)](#tests)
8. [Scripts (120 files)](#scripts)
9. [Documentation (611 files)](#documentation)
10. [Knowledge Base (280 files)](#knowledge-base)
11. [Frontend (SaaS) (1,321 files)](#frontend)
12. [Skills (2,015 files)](#skills)
13. [Data Artifacts (11,029 files)](#data-artifacts)
14. [Configuration](#configuration)

---

## ROOT LEVEL FILES

Location: `/opt/OS/`

| File | Purpose | Lines |
|------|---------|-------|
| **README.md** | Project overview, quick start, services table | ~115 |
| **PHILOSOPHY.md** | Foundation principles, why this exists | ~485 |
| **ARCHITECTURE.md** | System design, entity model, agent hierarchy | ~465 |
| **CLAUDE.md** | Developer agent soul, tool mastery engine, cognition stack | ~672 |
| **PROTOCOLS.md** | Communication contracts, governance rules | ~240 |
| **AGENTS.md** | Cross-agent configuration rules | ~25 |
| **cloud.md** | Cloud deployment guide | ~80 |
| **.mcp.json** | MCP server configuration | ~10 |
| **docker-compose.yml** | Service orchestration (os-discord, os-operator, os-webhook) | ~127 |
| **pyproject.toml** | Python dependencies, metadata | ~35 |
| **requirements.txt** | Direct dependencies | ~15 |
| **install.sh** | Installation helper | ~65 |
| **setup.sh** | Development setup | ~48 |
| **patch_pycord.py** | Discord library patching | ~120 |
| **.env.example** | Environment template | ~85 |
| **.gitignore** | Git exclusions | ~65 |
| **.dockerignore** | Docker build exclusions | ~10 |
| **Dockerfile** | Container image definition | ~35 |
| **Makefile** | Build automation | ~8 |

**Key Insight:** All documentation is at root level and must be read first. No subdirectory README files — single sources of truth.

---

## SUBSTRATE

**Location:** `/opt/OS/substrate/`  
**Files:** 909 Python modules  
**Status:** Core intelligence layer, fully mature

### Substrate Structure (19 subsystems)

```
substrate/
├── foundation/          (9 files)    — Ontological primitives
├── contracts/           (5 files)    — Interface definitions
├── control_plane/       (77 files)   — Strategic decision making
├── execution/           (164 files)  — Execution engine + bridge
├── governance/          (20 files)   — Policy + authority
├── intelligence/        (4 files)    — LLM routing + training
├── memory/              (7 files)    — Canonical memory system
├── meta_ide/            (15 files)   — Engineering workspace
├── observability/       (6 files)    — Traces, errors, proofs
├── ontology/            (9 files)    — Domain concepts
├── operator/            (19 files)   — Workstation presence
├── organism/            (318 files)  — Multi-agent orchestration
├── reality_model/       (8 files)    — Canonical state
├── sockets/             (19 files)   — Port abstractions
├── state/               (63 files)   — Persistence + stores
├── understanding/       (55 files)   — Perception → knowledge
├── workstation/         (56 files)   — Workstation runtime
├── types.py             (1,400 lines) — Canonical type definitions
├── canonical_types.py   (1,249 lines) — Type registry
├── self_model.py        (exported API)
└── __init__.py          (public API)
```

### 1. FOUNDATION (9 files)

**Purpose:** Ontological primitives — the building blocks of reality modeling

| File | Contents |
|------|----------|
| **primitives.py** | Base concepts: Action, State, Capability, Causality, Intention |
| **identity.py** | Entity identity, persistence, transformation |
| **epistemology.py** | Knowledge representation, certainty, evidence |
| **perspective.py** | Observer-dependent truths, relativity |
| **possibility.py** | Possible worlds, counterfactuals, planning |
| **laws.py** | Invariants: Conservation, Causality, Consistency |
| **persona.py** | Individual identity across time |
| **derived_constructs.py** | Complex concepts built from primitives |
| **__init__.py** | Module exports |

**Why It Matters:** LLMs hallucinate because they lack grounding. These primitives are checked before every major decision.

---

### 2. CONTRACTS (5 files)

**Purpose:** Interface contracts — what the system promises

| File | Contents |
|------|----------|
| **agent_runtime_contracts.py** | `AgentRuntime` interface: load context, execute task, stream result |
| **agent_types.py** | `TaskType`, `ModelProvider`, `AuthorityClass`, cost tables |
| **adapter_contracts.py** | `Adapter` interface: health(), execute(), rollback() |
| **routing_contracts.py** | Intent → Agent routing protocol |
| **__init__.py** | Exports |

**Key Class:** `TaskType` enum (ANALYZE, GENERATE, EXECUTE, APPROVE, REFLECT, LEARN)

---

### 3. CONTROL PLANE (77 files)

**Location:** `substrate/control_plane/`

**Purpose:** Strategic decision-making layer. Plans, delegates, reviews. Does NOT execute.

| Subsystem | Files | What It Does |
|-----------|-------|------|
| **actions/** | 11 | Action execution, deferred actions, idempotency, validation |
| **agents/** | 8 | CEO/Portfolio advisor agents, organizational hierarchy |
| **context/** | 2 | Context assembly, compaction (shrink context for cheaper LLM calls) |
| **coordination/** | 1 | Cross-agent coordination engine |
| **delegation/** | 1 | Delegation tracking |
| **events/** | 2 | Event bus, event manager |
| **goals/** | 1 | Goal selection, active objectives |
| **identity/** | 1 | AI identity, persona definition |
| **invariants/** | 3 | Coherence validators, spine contracts |
| **onboarding/** | 2 | New user/venture setup, wizard |
| **orchestrator/** | 1 | Orchestrator role (highest level) |
| **proactive/** | 1 | Proactive action generation |
| **router/** | 3 | Intent routing, control plane router, contracts |
| **runtime/** | 19 | Cognitive loop, gateway, orchestrator pipeline |
| **scheduling/** | 4 | Week planning, daily sync, ideal week |
| **signals/** | 1 | Signal hierarchy |
| **strategy/** | 4 | Portfolio advisor, strategy engine, task yield matrix |

**Critical Files:**

- **runtime/cognitive_loop.py** (1,539 lines) — Entry point for ALL AI reasoning
- **agents/ceo_agent.py** — Orchestrates company-level decisions
- **agents/agent_hierarchy.py** — How agents delegate to each other
- **router/control_plane_router_v1.py** — Routes signals to right agent

---

### 4. EXECUTION (164 files)

**Location:** `substrate/execution/`

**Purpose:** Makes things actually happen in the real world

| Subsystem | Files | What It Does |
|-----------|-------|------|
| **actuation/** | 4 | Hardware control (desktop windows, mouse, keyboard) |
| **adapters/** | 2 | Physical adapters, device abstraction |
| **agents/** | 2 | Browser agent, computer use agent |
| **bridge/** | 60 | Integration bridges to external systems (Discord, Claude API, local control, rituals, scenes, stations) |
| **runtime/** | 15 | Distributed runtime workers, session registry, heartbeat, presence, continuity, recovery |
| **workers/workstation/** | 55 | Workstation-specific execution (GUI, browser, shell, constitutionality) |
| **executor.py** | Main execution engine |
| **pipeline.py** | Execution pipeline architecture |
| **queue.py** | Task queue |
| **spine.py** | Execution spine (event stream) |
| **trace.py** | Execution tracing |
| **feedback.py** | Feedback collection |
| **feedback_loop.py** | RLHF signal generation |
| **proof_generator.py** | Cryptographic proof generation |
| **mastery_gate.py** | Tool mastery verification before execution |
| **cpu_gate.py** | CPU resource limiting |
| **understanding_bridge.py** | Bridge to understanding layer |
| **media/** | Media processor |
| **voice/** | Voice session management |
| **ingestion/** | Data ingestion pipeline |
| **loop/** | Persistent execution loop, stages |

**Key Pattern:** Every execution follows:
```
Task → Decomposition → Queue → Governance Gate → Execution → Proof → Memory Write → Event Emission
```

---

### 5. GOVERNANCE (20 files)

**Location:** `substrate/governance/`

**Purpose:** Constitutional enforcement. Every action goes through here.

| File | What It Does |
|------|------|
| **policy_engine.py** | Maps RiskClass + context → GovernanceVerdict (APPROVE/DEFER/DENY/ESCALATE) |
| **policy/authority_engine.py** | Verifies user has permission tier for action |
| **policy/authority_tier.py** | 4-tier permission model (READ/DRAFT/EXECUTE/COMMIT) |
| **policy/execution_authority_engine_v1.py** | Approves/denies execution based on action type |
| **policy/confidentiality.py** | Data privacy rules |
| **risk_classes.py** | Risk classification: READ_ONLY, SAFE_WRITE, REVERSIBLE_WRITE, IRREVERSIBLE_WRITE, FINANCIAL, SECURITY, PHYSICAL |
| **security.py** | Security boundaries, access control |
| **authority.py** | Authority levels and hierarchy |
| **principles/** | Core principles (principle_engine.py) |
| **quality/** | Quality gates (quality_gate.py) |
| **validation/** | Output validation, completeness checking |
| **accountability/** | Accountability tracking |
| **__init__.py** | Exports |

**Risk Classification:**
- `READ_ONLY` → AUTONOMOUS (no approval)
- `SAFE_WRITE` → Check safe roots, else APPROVE
- `REVERSIBLE_WRITE` → APPROVE (can undo)
- `IRREVERSIBLE_WRITE` → DENY (touches data permanently)
- `EXTERNAL_COMMUNICATION` → DENY (emails, posts, calls)
- `FINANCIAL` → DENY (touches money)
- `SECURITY_SENSITIVE` → ESCALATE (admin only)
- `PHYSICAL_WORLD` → ESCALATE (hardware/robotics)

---

### 6. MEMORY (7 files)

**Location:** `substrate/memory/` and `substrate/state/memory/`

**Purpose:** Canonical memory. Single source of truth for all facts.

| File | What It Does |
|------|------|
| **canonical_write.py** | Safe write path for facts into memory |
| **canonical_memory_store_v1.py** | Persistent store implementation |
| **canonical_memory_query_contracts.py** | Query interface |
| **canonical_memory_reconciliation_engine_v1.py** | Reconciles conflicts, updates confidence |
| **memory_conflict_governance_v1.py** | Handles contradictions |
| **memory_identity_v1.py** | Entity identity tracking |
| **auto_reconciler.py** | Automatic reconciliation process |
| **candidate_generator.py** | Generates candidate memories from interactions |
| **watcher.py** | Watches for new facts to promote |
| **promoter.py** | Moves facts from uncertain to certain |
| **claude_bridge.py** | Integration with Claude API memory operations |

**Memory Entry Structure:**
```python
MemoryType: FACT | BELIEF | DECISION | OBSERVATION | COMMITMENT
confidence: 0.0-1.0  (updated with new evidence)
authority_tier: 1-9  (higher = more reliable source)
tags: list[str]      (semantic indexing)
source_signal_id: UUID  (what created this)
```

---

### 7. ORGANISM (318 files)

**Location:** `substrate/organism/`

**Purpose:** Multi-agent orchestration. Where all agents coordinate and work flows.

**Structure (30+ subsystems):**

| Component | Files | Purpose |
|-----------|-------|---------|
| **agent_** (6 files) | Agent runtime, registry, capability models |
| **action_** (4 files) | Action catalog, bridge, voice contracts |
| **advisor_** (4 files) | Advisor hierarchy, reconciliation, conversation |
| **allocation_loop.py** | Resource allocation strategy |
| **approval_** (2 files) | Approval gates, approval store |
| **autonomous_** (4 files) | Autonomous action gateway, cadence, lane |
| **bottleneck_** (1 file) | Bottleneck analysis engine |
| **capability_** (10 files) | Capability gap, evolution, portfolio, graph engines |
| **canonical_update.py** | Updates canonical memory |
| **change_event.py** | Tracks changes |
| **coherence_propagation.py** | Ensures consistency across system |
| **command_runtime.py** | Command execution |
| **composition_engine.py** | Composes complex actions |
| **compounding_engine.py** | Compounds learning over time |
| **compute_fabric_runtime.py** | Distributed computation |
| **context_** (3 files) | Context ingestion, resolution, diagnostics |
| **continuity_runtime.py** | Session continuity |
| **contradiction_engine.py** | Detects logical contradictions |
| **coordinator.py** | Coordinates work units |
| **council.py** | Advisor council |
| **daemon.py** | Background worker |
| **decision_** (4 files) | Decision registry, lineage, validity, impact |
| **delegation_** (5 files) | Delegation runtime, readiness, followup |
| **dependency_graph.py** | Work dependencies |
| **device_** (2 files) | Device awareness, capacity |
| **dex_** (2 files) | Developer experience, reconciliation |
| **drift_detection_engine.py** | Detects goal drift |
| **embodiment_runtime.py** | Agent embodiment |
| **empire_router.py** | Reality-aware routing |
| **environment_** (2 files) | Environment graph, discovery, reconciliation |
| **event_spine.py** | Event transport layer |
| **execution_** (6 files) | Execution orchestration, economy, journal |
| **executive_** (2 files) | Executive briefing, portfolio |
| **executor_runtime.py** | Executor role |
| **executors/** (2 files) | Agent and workstation executors |
| **goal_** (3 files) | Goal alignment, hierarchy, drift |
| **governance_runtime.py** | Governance enforcement |
| **grounded_** (2 files) | Grounded handlers, registry |
| **handoff.py** | Agent handoff |
| **homeostasis.py** | System self-regulation |
| **impact_analyzer.py** | Decision impact analysis |
| **infrastructure_runtime.py** | Infrastructure management |
| **ingestion_job.py** | Async ingestion worker |
| **institutional_memory_runtime.py** | Organizational memory |
| **intent_classifier.py** | Classifies user intent |
| **knowledge_** (2 files) | Knowledge awareness, models |
| **learning_** (2 files) | Learning extraction, portfolio |
| **leverage_** (5 files) | Leverage patterns, metrics, assimilation |
| **maintenance_loop.py** | System maintenance |
| **memory_promotion.py** | Promotes memories up confidence ladder |
| **mesh_reconciler.py** | Node mesh reconciliation |
| **meta_ide_runtime.py** | Meta IDE integration |
| **mission.py** | Mission tracking |
| **next_action_engine.py** | Generates next action |
| **objective_** (2 files) | Objectives, queue |
| **observability.py** | Internal observability |
| **operating_loop_** (2 files) | Main operating loop, coherence |
| **operational_truth.py** | Source of truth for operations |
| **operationalization_runtime.py** | Operationalization engine |
| **operator_** (10 files) | Operator acceptance, session, readiness, migration |
| **orchestration_loop.py** | Orchestration cycle |
| **orchestrator_awareness_runtime.py** | Orchestrator presence |
| **outcome_** (3 files) | Outcome learning, patterns, tracking |
| **packet_router.py** | Routes work packets |
| **parallel.py** | Parallel execution |
| **permission_dialogue.py** | Permission negotiation |
| **plan_execution_adapter.py** | Executes plans |
| **prediction_portfolio_runtime.py** | Prediction portfolio |
| **presence_runtime.py** | Presence tracking |
| **priority_engine.py** | Priority assignment |
| **production_** (2 files) | Production truth tracking, merge verification |
| **profile_runtime.py** | User profile management |
| **project_registry.py** | Project tracking |
| **projection_** (6 files) | Projection reconciliation, ports, gating |
| **promotion_threshold_policy.py** | When to promote memories |
| **proof_runtime.py** | Proof artifact management |
| **propagation_** (5 files) | Propagates changes through system |
| **protocols.py** | System protocols |
| **readiness_model.py** | Readiness assessment |
| **reality_graph.py** | Reality modeling |
| **recommendation_engine.py** | Recommendation generation |
| **reconciliation_** (2 files) | Cross-source reconciliation |
| **recursion_governance.py** | Controls recursive delegation |
| **reliability_** (2 files) | Reliability signals, weighted ranker |
| **report_dispatcher.py** | Report delivery |
| **repository_awareness_runtime.py** | Repo awareness |
| **resource_allocation_runtime.py** | Resource scheduling |
| **risk_engine.py** | Risk assessment |
| **roadmap_engine.py** | Roadmap management |
| **role_contracts.py** | Role specifications |
| **runtime_** (8 files) | Runtime management, supervisor, fleet |
| **sandbox_orchestrator.py** | Sandbox environment |
| **scenario_intelligence_engine.py** | Scenario planning |
| **self_build_queue.py** | Self-improvement queue |
| **service_dependency_** (2 files) | Service dependencies, failures |
| **session_runtime.py** | Session lifecycle |
| **shell_runtime_adapter.py** | Shell command execution |
| **source_** (2 files) | Source truth, registry |
| **spine_guard.py** | Protects execution spine |
| **state_** (3 files) | State coherence, authority, registry |
| **store.py** | Persistence |
| **strategic_** (4 files) | Strategic context, memory, planning |
| **sync_policy.py** | Synchronization rules |
| **system_identity.py** | System-level identity |
| **template_** (3 files) | Template governance, registry, seeding |
| **tradeoff_intelligence_engine.py** | Tradeoff analysis |
| **trajectory_intelligence_runtime.py** | Path planning |
| **trial_runner.py** | Experiment execution |
| **umh_** (3 files) | UMH node topology, registry, versioning |
| **universal_work_queue.py** | Global work queue |
| **work_** (7 files) | Work packets, graph, queues, portfolios |
| **workcell** (2 files) | Workcell protocol, daemon |
| **worker_** (3 files) | Worker lifecycle, registry |
| **workload_** (2 files) | Workload placement, probes |
| **workspace_awareness.py** | Workspace tracking |
| **workstation_runtime.py** | Workstation environment |
| **worktree_sandbox.py** | Git worktree isolation |
| **world_model.py** | World modeling |
| **tests/** (70+ test files) | Unit tests for all components |

**Key Insight:** Organism is where work actually flows through the system. Every major decision happens here.

---

### 8. CONTROL PLANE / OPERATOR / WORKSTATION

These three work together:
- **control_plane/** — Strategic decisions
- **operator/** → Workstation presence tracking
- **workstation/** → Workstation runtime commands

---

### 9. UNDERSTANDING (55 files)

**Purpose:** Perception → Knowledge conversion

| Subsystem | Files | Purpose |
|-----------|-------|---------|
| **interpretation/** | 1 | NL → semantic action interpretation |
| **perception/** | 10 | Code/config/DB parsing, source extraction |
| **intelligence/** | 9 | Competitive intel, stakeholder maps, person recognition |
| **knowledge/** | 7 | Knowledge graph, layers, integrator |
| **embedding/** | 2 | Vector representations, embedder |
| **patterns/** | 2 | Leverage pattern recognition |
| **world_model/** | 1 | World state modeling |
| **world_pulse/** | 1 | Real-time signals |
| **reality/** | 2 | Reality context and engine |
| **research/** | 1 | Research automation |
| **deliberation/** | 1 | Advisor council |
| **domains/** | 5 | Domain-specific reasoning (business, creator, life, contract) |
| **signals/** | 1 | Founder signal capture |
| **breadth_expansion.py** | Expand understanding |
| **__init__.py** | Exports |

---

### 10. STATE & PERSISTENCE (63 files)

**Location:** `substrate/state/`

**Purpose:** All persistent data and its management

| Subsystem | Files | What It Stores |
|-----------|-------|------|
| **storage/** | 1 | PostgreSQL connection pool |
| **registries/** | 4 | Skill registry, OS registry, template registry |
| **business/** | 2 | Business instance spec, venture knowledge |
| **config/** | 1 | Configuration store |
| **context/** | 1 | Execution context |
| **finance/** | 2 | Expense/subscription tracking |
| **lifecycle/** | 1 | Stage manager |
| **logs/** | 1 | Decision log |
| **memory/** | 5 | Canonical memory contracts |
| **metrics/** | 2 | OKR tracker, founder rate metrics |
| **permissions/** | 1 | OS trinity (user/AI/system) |
| **preferences/** | 1 | Model preferences |
| **profiles/** | 1 | User model |
| **providers/** | 1 | Provider state (LLM, weather, etc) |
| **session/** | 1 | Session state |
| **stores/** | 12 | Typed stores for each entity (approval, entity_link, embedding, entity, goal, higgsfield, permission, preference, profile, skill, task, venture) |
| **tenancy/** | 1 | Multi-tenancy support |
| **work/** | 1 | Work state |
| **transformation_state_ledger.py** | Transformation tracking |

---

### 11. SOCKETS & INTEGRATION

**Files:** 19 socket/port abstractions

**Purpose:** Pluggable I/O and event ports

| File | What It Does |
|------|------|
| **approval_port.py** | Approval request/response |
| **capability_socket.py** | Capability availability |
| **channel_port.py** | Channel abstraction |
| **config_port.py** | Configuration |
| **message_port.py** | Message I/O |
| **notification_engine.py** | Notification dispatch |
| **outcome_socket.py** | Outcome reporting |
| **projection_port.py** | Domain projection |
| **sensing_port.py** | Sensing/observation |
| **signal_socket.py** | Signal ingestion |
| **view_socket.py** | View updates |
| **protocols.py** | Socket protocols |
| **registry.py** | Port registry |
| **view/broadcaster.py** | WebSocket broadcasting |
| **view/websocket.py** | WebSocket implementation |

---

### 12. REALITY MODEL (8 files)

**Purpose:** Separation of belief from reality

| File | Purpose |
|------|---------|
| **canonical.py** | Source of truth |
| **instance.py** | User-specific reality instance |
| **simulation.py** | Possible futures |
| **reality_mutation.py** | How reality changes |
| **reality_query.py** | Query interface |
| **reality_intelligence.py** | Analysis layer |

---

### 13. OTHER SUBSTRATE MODULES

| Module | Files | Purpose |
|--------|-------|---------|
| **composition/** | 46 | Mastery research, authoring, management, knowledge gaps |
| **meta_ide/** | 15 | Engineering workspace observation, planning, execution |
| **observability/** | 6 | Error recording, proof storage, trace storage, outcome classification |
| **ontology/** | 9 | Domain contracts, creator, life domains, primitives |
| **intelligence/** | 4 | LLM routing, training extraction, finetune harness |
| **integrations/** | 5 | CORS, health checks, product connections, bridges |

---

## ADAPTERS

**Location:** `/opt/OS/adapters/`  
**Files:** 101 Python modules  
**Purpose:** External system integrations

### Adapter Subsystems

| Subsystem | Files | What It Connects To |
|-----------|-------|------|
| **models/** | 11 | LLM providers (Claude, Gemini, Groq, Ollama) |
| **adapter_engine/** | 16 | Adapter lifecycle, routing, health checks |
| **notion/** | 14 | Notion databases, pages, properties |
| **tool_adapters/** | 6 | Tool execution abstractions |
| **data_source_adapters/** | 8 | Generic data sources |
| **google_workspace/** | 7 | Gmail, Calendar, Drive, Workspace |
| **browser_exports/** | 8 | Browser state extraction |
| **capabilities/** | 6 | Capability definitions |
| **broadcast/** | 10 | Broadcast systems |
| **calendar/** | 3 | Calendar integration |
| **higgsfield/** | 2 | Media generation webhook |
| **notebooklm/** | 2 | NotebookLM integration |
| **scrapling/** | 2 | Web scraping |
| **shannon/** | 2 | Shannon indexing |
| **browser/** | 1 | Playwright/browser control |

### Key Adapter Files

**models/llm_adapter.py** — Base adapter class for LLMs
- Implement: `call()`, `stream()`, `health_check()`
- Return: standardized `LLMResponse`
- Track: cost, latency, errors

**models/routing.py** — LLM routing logic
```python
Priority order:
1. Claude (tier 1, best quality)
2. Gemini 2.5 Flash (tier 2, faster, cheaper)
3. Groq (tier 3, local, no API cost)
4. Ollama (tier 4, offline fallback)
```

---

## TRANSPORTS

**Location:** `/opt/OS/transports/`  
**Files:** 184 Python modules  
**Purpose:** I/O surfaces and communication

### Transport Subsystems

| Subsystem | Files | What It Handles |
|-----------|-------|------|
| **api/** | 140 | REST API, routes, middleware, auth |
| **discord/** | 6 | Discord bot, voice, text |
| **channels/** | 2 | Channel abstraction |
| **node_mesh/** | 12 | Distributed node network |
| **presence/** | 23 | Presence tracking, device awareness |

### Key Files

**api/routes/** — All REST endpoints
- `/message` — Send message
- `/approve/{id}` — Approve action
- `/spend` — Query spend
- `/interactions` — Get history
- `/status` — System health

**discord/** — Discord bot implementation
- Message ingestion
- Voice channel connection
- TTS output
- STX input
- Presence tracking

---

## SERVICES

**Location:** `/opt/OS/services/`  
**Files:** 27 Python modules  
**Purpose:** Deployment entrypoints

### Services

| Service | File | What It Does |
|---------|------|------|
| **os-discord** | `discord_bot.py` | Primary interface, runs organism loop |
| **os-operator** | `operator_api.py` | Workstation API, cockpit backend |
| **os-webhook** | `webhook.py` | Higgsfield media generation |

### auth_flows/ (3 files)

- OAuth2 flow
- API key validation
- Session management

---

## PROJECTIONS

**Location:** `/opt/OS/projections/`  
**Files:** 48 Python modules  
**Purpose:** Domain-specific applications built on UMH

### Projection Subsystems

| Projection | Files | What It Does |
|-----------|-------|------|
| **eos/** | 31 | EntrepreneurOS — business operating system |
| **creatoros/** | 8 | CreatorOS — creator/solopreneur OS |
| **lyfeos/** | 8 | LYFEOS — life operating system |

**Key Insight:** All three projections consume the same UMH substrate. Different domains, same brain.

---

## TESTS

**Location:** `/opt/OS/tests/`  
**Files:** 287 test files  
**Purpose:** Verify system behavior

### Test Organization

| Category | Files | What's Tested |
|----------|-------|------|
| **P0 Smoke** | 1 | Critical path (DB, LLM, types, memory, governance) |
| **Governance** | 8 | Policy engine, approval gates, authority tiers |
| **Execution** | 15 | Executor, work packets, proofs |
| **Memory** | 12 | Canonical memory, reconciliation, conflicts |
| **Organism** | 70+ | Organism loop, orchestration, agent runtime |
| **Agent** | 20 | Agent-specific tests |
| **Integration** | 50+ | Full end-to-end flows |
| **Phase-specific** | 60+ | Phase-based development tests |
| **Adapters** | 5 | Adapter tests |
| **Fixtures** | 1 | Shared test fixtures |
| **Substrate** | 4 | Substrate-level tests |

### Critical Test Files

- **test_p0_smoke.py** — Must pass before every commit
- **test_governance_routes.py** — Verify governance is never bypassed
- **test_daemon_e2e.py** — Full organism loop cycle
- **test_operator_loop_mvp.py** — Operator experience

---

## SCRIPTS

**Location:** `/opt/OS/scripts/`  
**Files:** 120 Python/shell scripts  
**Purpose:** Operational tooling

### Script Categories

| Category | Scripts | Purpose |
|----------|---------|---------|
| **Graph Management** | 5 | Build, query, verify knowledge graph |
| **Database** | 8 | Migrations, backups, schema |
| **Deployment** | 12 | Docker, cloud, staging |
| **Testing** | 15 | Run tests, report, coverage |
| **Monitoring** | 10 | Health, logs, alerts |
| **Scheduled Tasks** | 3 | Cron jobs (daily sync, weekly review, etc) |
| **Workers** | 1 | Background worker scripts |
| **Git** | 8 | Version management, hooks |
| **LLM** | 5 | Model routing tests, cost tracking |
| **Development** | 20 | Setup, format, lint, type check |
| **Utilities** | 28 | Various helpers |

---

## DOCUMENTATION

**Location:** `/opt/OS/docs/`  
**Files:** 611 markdown files  
**Subsystems:**

| Subsystem | Files | Content |
|-----------|-------|---------|
| **audits/** | 284 | Code audits, reviews, analysis |
| **operations/** | 182 | Runbooks, troubleshooting, procedures |
| **system/** | 88 | Architecture, design, decisions |
| **superpowers/** | 23 | Advanced capabilities documentation |
| **strategy/** | 11 | Strategic plans, roadmaps |
| **sessions/** | 6 | Session notes, transcripts |
| **setup/** | 1 | Installation guide |
| **research/** | 2 | Research notes |
| **plans/** | 3 | Development plans |
| **mvp/** | 2 | MVP specs |
| **design-system/** | 2 | UI/UX guidelines |
| **changes/** | 1 | Changelog |
| **canonical/** | 1 | Canonical reference |

---

## KNOWLEDGE BASE

**Location:** `/opt/OS/knowledge/`  
**Files:** 280 markdown files  
**Purpose:** Structured knowledge for decision-making

### Knowledge Subsystems

| Subsystem | Files | Purpose |
|-----------|-------|---------|
| **palace/** | 19 | Memory palace (navigation by concern) |
| **concepts/** | 135 | Conceptual knowledge (definitions, theory) |
| **entities/** | 29 | Entity definitions (companies, people, etc) |
| **skills/** | 46 | Skill knowledge |
| **synthesis/** | 37 | Synthesized insights |
| **decisions/** | 5 | Recorded decisions |
| **domains/** | 1 | Domain-specific knowledge |

**Key Files:**

- **palace/index.md** — Entry point
- **palace/rooms/*.md** — Topics (governance, memory system, execution trace, etc)
- **concepts/*.md** — 135 conceptual definitions
- **WIKI_RULES.md** — How to query the knowledge system

---

## FRONTEND (SaaS)

**Location:** `/opt/OS/saas/`  
**Files:** 1,321 files (mostly node_modules)  
**Frontend:** `/opt/OS/cockpit/`  
**Files:** 258 files (TypeScript/React)

### Cockpit Frontend Structure

```
cockpit/
├── src/               (255 files)
│   ├── pages/         Dashboard pages
│   ├── components/    React components
│   ├── lib/           Utilities
│   ├── styles/        CSS
│   ├── hooks/         React hooks
│   └── api/           Backend integration
└── tests/             (1 file)
```

**Key Pages:**
- Dashboard (overview)
- Interactions (message history)
- Approvals (pending decisions)
- Memory (facts store)
- Agents (agent status)
- Settings (configuration)
- Spend (cost tracking)

---

## SKILLS

**Location:** `/opt/OS/skills/`  
**Files:** 2,015 total  
**Purpose:** Reusable agent capabilities

### Skill Organization

| Category | Files | What They Do |
|----------|-------|------|
| **Sales/** | 20 | Sales techniques, closing, objection handling |
| **Ops/** | 13 | Operations, scaling, process |
| **Research/** | 6 | Research methodologies |
| **Marketing/** | 4 | Marketing campaigns, positioning |
| **Content/** | 5 | Content creation, copywriting |
| **Outreach/** | 2 | Outreach templates |
| **CustomerSuccess/** | 2 | CS playbooks |
| **tools/** | 250 | Tool-specific skills |
| **meta/** | 14 | Meta-skills (learning, reasoning) |
| **saas-dev-skill/** | 1,698 | SaaS development guide |
| **developer/** | 1 | Developer workflow |

---

## DATA ARTIFACTS

**Location:** `/opt/OS/data/`  
**Files:** 11,029 total  
**Purpose:** Generated data, caches, indexes

### Data Subsystems

| Subsystem | Files | What It Stores |
|-----------|-------|------|
| **codebase_pages/** | 10,441 | Knowledge graph nodes (one per file/class/function) |
| **vault/** | 104 | Encrypted secrets |
| **repos/** | 153 | Repository mirrors/snapshots |
| **umh/** | 234 | UMH-specific models |
| **audits/** | 57 | Audit reports |
| **reports/** | 12 | Generated reports |
| **migration/** | 11 | Migration scripts |
| **proofs/** | 10 | Execution proofs |
| **proposals/** | 1 | Proposals |

---

## CONFIGURATION FILES

### Environment Configuration

**`.env.example`**
```bash
# LLM Routing
CC_SDK_API_KEY=...
GEMINI_API_KEY=...
GROQ_API_KEY=...

# Database
DATABASE_URL=postgresql://...

# Discord
DISCORD_TOKEN=...

# Governance
SAFE_ROOTS=/home/safe/:/opt/safe/
ALLOWED_SHELL_PREFIXES=cat,ls,grep

# Limits
DAILY_SPEND_LIMIT_USD=10
MAX_CONCURRENT_TASKS=20
```

### Docker Configuration

**`docker-compose.yml`**
- **os-discord** — Main service
- **os-operator** — API + UI
- **os-webhook** — Media generation
- **postgres** — Database
- Network, volumes, environment

### Python Configuration

**`pyproject.toml`**
- Dependencies: pydantic, asyncio, aiohttp, psycopg, etc
- Build system: setuptools
- Testing: pytest

---

## DEVELOPMENT WORKFLOWS

### Adding a Feature

1. Check CLAUDE.md for current phase
2. Read relevant subsystem code
3. Run `pytest tests/test_p0_smoke.py` (baseline)
4. Write test for new behavior
5. Implement feature
6. Run full test suite
7. Update documentation
8. Commit with clear message

### Debugging

```bash
# Check system health
python3 scripts/verify_knowledge_system.py

# Query codebase
python3 scripts/query_graph.py deps substrate/memory/

# Run specific test
pytest tests/test_governance_routes.py -v

# Check recent interactions
python3 scripts/query_trace.py {interaction_id}

# View logs
docker logs os-discord -f | grep ERROR
```

### Deployment

```bash
# Local
docker compose up

# Production
# (See cloud.md)
```

---

## CRITICAL STATISTICS

| Metric | Value |
|--------|-------|
| Total files | 160,350+ |
| Python modules | 3,478 |
| TypeScript/React | 1,124 |
| Documentation | 611 |
| Lines of code (Python) | ~500,000 |
| Test files | 287 |
| Test coverage | Critical paths covered |
| Subsystems | 22 major |
| Services | 3 deployed |
| Agent roles | 7+ specialized |
| Database tables | 25+ |
| API endpoints | 50+ |
| Risk classes | 8 categories |
| Permission tiers | 4 levels |
| Memory types | 5 categories |
| Business stages | 6 (validation → portfolio) |

---

## ARCHITECTURAL PRINCIPLES IMPLEMENTED

### 1. Single Source of Truth
- Canonical types in `substrate/canonical_types.py`
- Canonical memory in `substrate/memory/`
- Canonical reality in `substrate/reality_model/`

### 2. Constitutional Governance
- Every action through PolicyEngine
- Risk classification (8 categories)
- Authority verification (4 tiers)
- Immutable proof generation

### 3. Unified Intelligence
- All three projections (EOS, CreatorOS, LYFEOS) use same substrate
- No domain-specific forks
- Shared memory and learning

### 4. Asynchronous by Default
- Everything is async/await
- Non-blocking I/O
- Background workers
- Event-driven

### 5. Observable
- Execution traces (complete audit trail)
- Proof artifacts
- Error recording
- Spend tracking

### 6. Resilient
- Fallback responses (no LLM = still work)
- Connection pooling
- Automatic retries
- Session recovery

### 7. Modular
- Adapters for external systems
- Pluggable transports (Discord, API, local)
- Portable workers
- Reusable skills

---

## KEY METRICS & TARGETS

### Performance
- Message → Response: <5 sec (with LLM)
- Governance gate: <100ms
- Memory reconciliation: <500ms
- Database query: <200ms

### Reliability
- Uptime target: 99.9%
- Error tracking: 100% of failures
- Proof generation: 100% of actions
- Memory reconciliation: hourly

### Cost Control
- Spend limit: per-day and per-month
- Model routing: picks cheapest available
- Token accounting: precise tracking
- Budget alerts: real-time

### Scalability
- Concurrent sessions: 10-100+
- Work packets/min: 100-1000
- Distributed workers: any number
- Database: scales to billions of facts

---

END OF EXHAUSTIVE AUDIT

This document catalogs every major component, subsystem, and file type in UMH. Use it as a reference when exploring the codebase.

**Next Steps:**
1. Read PHILOSOPHY.md
2. Study ARCHITECTURE.md
3. Review key files: types.py, cognitive_loop.py, organism_loop.py, policy_engine.py
4. Run tests: `pytest tests/test_p0_smoke.py`
5. Deploy locally: `docker compose up`
6. Trace a full user flow end-to-end

