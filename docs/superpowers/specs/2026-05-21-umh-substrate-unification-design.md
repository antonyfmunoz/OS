# UMH Substrate Unification Design

**Date:** 2026-05-21
**Status:** Approved
**Approach:** Bottom-up substrate migration with aggressive pruning
**Timeline:** 4-6 weeks (7 phases)
**North Star:** Canonical UMH end-state spec (Google Drive doc, 8 tabs, 13,949 words)

---

## Problem Statement

The /opt/OS repository contains ~320,000 lines of Python across 1,124 files.
Only ~10,000 lines (15 files) are in the production execution path. The rest
is a combination of:

- A disconnected UMH substrate (`services/umh/`, ~12,000 lines, zero production callers)
- Constitutional engines and workstation workers (~20,000 lines, test-only)
- 40+ v1 contract files (~15,000 lines, superseded)
- 2-4 duplicate implementations of every core concept (governance, memory, primitives, routing, orchestration)
- Extensive transport infrastructure (~25,000 lines) not wired to the substrate

The canonical end-state spec defines a 6-tier, 24-subsystem architecture with
a single execution spine. The current codebase has 3 parallel execution paths,
scattered registries, and no unified trace or feedback.

## Goal

Unify the codebase into a single coherent system aligned with the canonical
end-state design. Extract all proven value from existing code. Delete everything
that doesn't serve the architecture. Produce a substrate MVP capable of hosting
EOS as its first projection.

## Constraints

- Full rebuild window approved (Discord bot offline during migration)
- No Neon schema destruction (existing data preserved, new tables added)
- Every surviving file must belong to exactly one tier
- Every execution must flow through one spine, produce a trace, capture feedback
- Projections (EOS) call the substrate through a public API, never import internals
- Directory names must be production-grade (no numbered folders, no internal jargon)

---

## Architecture

### Directory Structure

```
/opt/OS/
├── substrate/                  # Tier 0-2: The UMH kernel
│   ├── ontology/               # Tier 0: Primitives, laws, relationships
│   ├── control_plane/          # Tier 1: Identity, context, governance, memory, registry
│   │   ├── identity.py
│   │   ├── context.py
│   │   ├── governance.py
│   │   ├── memory.py
│   │   ├── registry.py
│   │   └── router.py          # Signal routing (replaces gateway.py)
│   ├── execution/              # Tier 2: Spine, trace, feedback, ingestion
│   │   ├── spine.py            # THE single execution path
│   │   ├── trace.py            # Every execution recorded
│   │   ├── feedback.py         # Outcome observation
│   │   └── ingestion/          # Canonical ingestion pipeline
│   ├── learning/               # Cross-tier: Evolution, self-improvement
│   └── __init__.py             # Public API for projections
│
├── adapters/                   # Tier 3: External system interfaces
│   ├── models/                 # LLM routing (model_router.py, cc_sdk.py)
│   ├── google_workspace/       # GWS connector, scanner, drive
│   ├── browser/                # Browser automation
│   ├── calendar/               # Calendly, meetings
│   ├── notion/                 # Notion sync
│   └── capabilities/           # Voice, vision, media
│
├── world_model/                # Tier 4: User, system, environment (post-MVP)
│
├── intelligence/               # Tier 5: Deliberation, simulation (post-MVP)
│
├── projections/                # Application layers on substrate
│   └── eos/                    # EntrepreneurOS (Phase 7)
│
├── transports/                 # User-facing interfaces
│   ├── discord/                # Discord bot
│   ├── api/                    # REST + WebSocket operator API
│   └── cockpit/                # React dashboard
│
├── knowledge/                  # Curated knowledge graph
│   ├── concepts/
│   ├── entities/
│   ├── decisions/
│   ├── synthesis/
│   ├── sources/
│   └── palace/                 # Memory palace
│
├── state/                      # Persistence layer
│   ├── storage/                # db.py (Neon connection)
│   ├── memory/                 # Proven AgentMemory + canonical store
│   ├── context/                # System context loader
│   ├── business/               # BIS, venture config
│   ├── registries/             # Backing stores for unified registry
│   ├── profiles/               # User model
│   └── preferences/            # Model preferences
│
├── composition/                # Tool Mastery Engine (operator tooling)
├── scripts/                    # Operator scripts, cron jobs
├── data/                       # Generated data, proofs, audits
├── docs/                       # Architecture specs, contracts
├── skills/                     # Claude Code tool skills
└── tests/                      # Unified test suite (mirrors source)
```

### Substrate Public API

`substrate/__init__.py` exposes the only interface projections may use:

```python
class Substrate:
    def execute(signal: SignalEnvelope) -> ExecutionResult
    def query(memory_query: MemoryQuery) -> list[MemoryEntry]
    def register(component: Component) -> RegistrationResult
    def ingest(source: Source) -> IngestionResult
    def status() -> SubstrateStatus
```

No projection imports `substrate.control_plane.*` or `substrate.execution.*`
directly. The public API is the boundary.

### Unified Execution Path

Every signal follows one path regardless of transport origin:

```
Transport (Discord / API / WebSocket / Cron)
  │
  └── SignalEnvelope
        │
        ▼
  substrate/control_plane/router.py
        │
        ├── identity.resolve(signal)
        ├── context.load(identity)
        ├── governance.classify(signal) → risk class
        ├── governance.authorize(signal) → approved | needs_approval | blocked
        │
        ▼ (if approved)
  substrate/execution/spine.py
        │
        ├── ontology.interpret(signal)    → primitives
        ├── memory.recall(context)        → relevant memories
        ├── registry.lookup(intent)       → available capabilities
        ├── compose(intent, caps, ctx)    → execution plan (MVP: prompt + model selection)
        ├── adapter.route(plan)           → select adapter (MVP: model_router.call_with_fallback)
        ├── adapter.execute(plan)         → LLM / tool / API call
        ├── trace.record(execution)       → full provenance
        └── feedback.capture(outcome)     → learning signal
        │
        ▼
  Transport delivers response
```

### SignalEnvelope Schema

```python
@dataclass
class SignalEnvelope:
    id: str                          # UUID
    source: str                      # transport identifier
    content: str                     # primary text content
    modality: Modality               # TEXT | VOICE | IMAGE | MULTIMODAL
    user_id: str                     # who sent this
    organization_id: str             # which org
    venture_id: str | None           # which venture (optional)
    timestamp: datetime
    attachments: list[Attachment]    # images, files, voice
    metadata: dict                   # transport-specific data
    authority_tier: AuthorityTier    # T1-T9 from source
```

### ExecutionResult Schema

```python
@dataclass
class ExecutionResult:
    id: str                          # UUID
    signal_id: str                   # back-reference to input
    output: str                      # primary response content
    trace_id: str                    # link to full trace record
    provider: str                    # which adapter handled it
    model: str                       # which model (if LLM)
    duration_ms: int                 # wall clock time
    risk_class: RiskClass            # governance classification
    memory_candidates: list[str]     # IDs of potential memory entries
    feedback_id: str | None          # ID of feedback record if captured
```

---

## What Survives (Extract All Value)

### Production-proven code (keep as-is, relocate)

| Current Location | New Location | Lines | Why |
|------------------|-------------|-------|-----|
| `execution/runtime/model_router.py` | `adapters/models/model_router.py` | 1,254 | Crown jewel. Multi-model routing with circuit breaker. |
| `adapters/model_adapters/cc_sdk.py` | `adapters/models/cc_sdk.py` | 464 | Claude Code CLI adapter. Production-proven. |
| `state/memory/memory.py` | `state/memory/memory.py` | ~400 | 35,485 interactions. Proven Neon persistence. |
| `state/storage/db.py` | `state/storage/db.py` | ~100 | Neon connection. Used by everything. |
| `state/context/context.py` | `state/context/context.py` | ~200 | load_context_from_env. Used everywhere. |
| `state/business/business_instance.py` | `state/business/business_instance.py` | ~200 | BIS, get_ai_name(). Production. |
| `governance/policy/authority_engine.py` | `substrate/control_plane/governance.py` | ~500 | 4 risk classes. Proven classification. |
| `control_plane/identity/ai_identity.py` | `substrate/control_plane/identity.py` | ~300 | AI identity and personality. |
| `services/discord_bot.py` | `transports/discord/bot.py` | 5,342 | Primary interface. Refactored to use SignalEnvelope. |
| `services/operator_api.py` | `transports/api/operator.py` | ~1,000 | FastAPI backend. Refactored for spine. |
| `adapters/google_workspace/` | `adapters/google_workspace/` | 3,531 | GWS connector + scanner. Production. |
| `execution/voice/` | `adapters/capabilities/voice/` | ~1,000 | Voice engine. Production. |
| `state/registries/skill_registry.py` | `state/registries/skill_registry.py` | ~200 | 140 skills in Neon. Production. |

### Valuable code merged into substrate

| Current Location | Merges Into | Value Extracted |
|------------------|-------------|-----------------|
| `control_plane/runtime/cognitive_loop.py` | `substrate/execution/spine.py` | 8-stage execution pattern, context assembly |
| `control_plane/runtime/gateway.py` | `substrate/control_plane/router.py` | Signal routing, intent classification |
| `execution/runtime/execution_spine.py` | `substrate/execution/spine.py` | Thin execution path structure |
| `services/umh/foundation/primitives.py` | `substrate/ontology/primitives.py` | Ontological category system |
| `services/umh/foundation/laws.py` | `substrate/ontology/laws.py` | Law definitions |
| `services/umh/governance/` | `substrate/control_plane/governance.py` | Policy engine patterns |
| `services/umh/protocols/` | `substrate/execution/` | Signal, trace, governance protocols |
| `services/umh/observability/` | `substrate/execution/trace.py` | Trace store, outcome classifier |
| `understanding/ontology/primitives.py` | `substrate/ontology/primitives.py` | PrimitiveType enum, decomposition |
| `understanding/ontology/primitive_decomposition_v1.py` | `substrate/execution/ingestion/` | LLM extraction logic |
| `learning/feedback/feedback_loop.py` | `substrate/execution/feedback.py` | Feedback capture pattern |
| `state/memory/contracts/canonical_memory_store_v1.py` | `substrate/control_plane/memory.py` | Canonical memory interface |
| `runtime/ingestion/` | `substrate/execution/ingestion/` | Pipeline stages |

### Deferred (kept but not wired into substrate MVP)

| Location | Lines | Reason for Deferral |
|----------|-------|---------------------|
| `apps/cockpit/` -> `transports/cockpit/` | ~5,000 | React UI. Wire after substrate proves itself. |
| `saas/` -> `projections/eos/saas/` | ~500 | SaaS scaffold. Build after substrate + EOS projection. |
| `composition/` | 10,286 | Tool Mastery Engine. Operator tooling, not runtime. |

---

## What Gets Deleted

### Immediate deletion (~250,000 lines)

| Category | Approx Lines | Reason |
|----------|-------------|--------|
| `execution/workers/workstation/` constitutional engines | ~20,000 | Future organism runtime. Not substrate MVP. |
| `execution/transport/` bulk | ~20,000 | Rebuilt as proper transports. |
| `execution/runtime/` v1 contracts (40+ files) | ~15,000 | Superseded by substrate contracts. |
| `services/umh/` remainder after extraction | ~8,000 | Best parts merged, rest is scaffolding. |
| `control_plane/` non-core subdirs | ~10,000 | Premature: actions, delegation, coordination, events, goals, strategy, onboarding, scheduling. |
| `core/` most files | ~4,000 | Superseded by substrate. |
| `understanding/` non-ontology | ~5,000 | Merged what's needed, rest is stubs. |
| `execution/environments/` | ~3,000 | Work packet builders. Not substrate MVP. |
| `execution/workflows/` | ~1,000 | Rebuild on substrate when needed. |
| `execution/agents/` | ~600 | Browser agent. Rebuild on adapter interface. |
| `execution/tasks/` | ~300 | Task executor. Rebuild in spine. |
| `execution/engine/` | ~300 | Superseded by spine. |
| `runtime/` (root) | ~800 | Stubs. |
| `interface/` (after transport extraction) | ~4,000 | Merged into transports. |
| `observability/` (after trace extraction) | ~900 | Merged into substrate. |
| `operations/` (after memory merge) | ~2,400 | Merged into substrate. |
| Dead test files | ~20,000 | Tests for deleted code. |
| Miscellaneous duplicates and dead imports | ~5,000+ | Cleanup. |

**Total deleted: ~250,000 lines.**
**Total surviving: ~80,000-100,000 lines.**

---

## Substrate MVP Subsystems (11 of 24)

These must be operational before EOS can build on the substrate:

| # | Subsystem | Source | Status After Migration |
|---|-----------|--------|----------------------|
| 1 | Identity | Merge ai_identity + context resolution | NEW (merged) |
| 2 | Context | Merge context.py + BIS loader | NEW (merged) |
| 3 | Memory | Keep state/memory + add canonical interface | UPGRADED |
| 4 | Governance | Keep authority_engine + add trace enforcement | UPGRADED |
| 5 | Execution Spine | New from CogLoop + ExecSpine + UMH pipeline | NEW |
| 6 | Trace | New from UMH trace_store patterns | NEW |
| 7 | Feedback | Upgrade feedback_loop.py | UPGRADED |
| 9 | Registry | Unify agent + skill + adapter registries | NEW |
| 17 | Ontology | Merge both primitives + decomposer | NEW (merged) |
| 19 | Adapter | Formalize interface, keep model_router | UPGRADED |
| 20 | Storage | Keep Neon persistence + discipline rules | UPGRADED |

Deferred subsystems (13): Template, Library, Composition, Completeness,
Quality, World Model, Simulation, Law Kernel (full), Workstation (full),
Self-Recursion, Resource Allocation, Homeostasis, Learning (full).

---

## Migration Phases

### Phase 0 — Archive and Scaffold (Day 1-2)

**Goal:** Preserve current state, create new structure, move files without code changes.

Actions:
- Git tag `pre-unification` on current HEAD
- Create all new directories per the structure above
- Move surviving files to new locations
- Update all Python `sys.path` and imports to resolve
- Verify: `python3 -c "import substrate"` succeeds
- Verify: all moved files compile (`py_compile`)

Deliverable: New directory structure with all files in their canonical locations.
No code logic changes. Old directories are empty shells or deleted.

### Phase 1 — Tier 0: Ontology (Day 3-4)

**Goal:** Single source of truth for primitives and laws.

Actions:
- Merge `understanding/ontology/primitives.py` (PrimitiveType enum, relationships)
  with `services/umh/foundation/primitives.py` (OntologicalCategory system)
  into `substrate/ontology/primitives.py`
- Merge `services/umh/foundation/laws.py` into `substrate/ontology/laws.py`
- Define RelationshipType enum for primitive relationships
- Write tests: primitive creation, validation, law lookup

Deliverable: `substrate/ontology/` with unified primitives and laws.
Everything that references primitives imports from here.

### Phase 2 — Tier 1: Control Plane (Day 5-10)

**Goal:** Unified identity, governance, memory, and registry.

Actions:
- Build `substrate/control_plane/identity.py` (merge ai_identity + context resolution)
- Build `substrate/control_plane/context.py` (merge context loader + BIS)
- Build `substrate/control_plane/governance.py` (merge authority_engine + trace enforcement)
- Build `substrate/control_plane/memory.py` (unified interface over state/memory/)
- Build `substrate/control_plane/registry.py` (unified agent + skill + adapter registry)
- Build `substrate/control_plane/router.py` (signal routing, replaces gateway)
- Write integration tests for each subsystem

Deliverable: Complete Tier 1 with tests. Each subsystem callable independently.

### Phase 3 — Tier 2: Execution Spine (Day 11-15)

**Goal:** Single execution path with trace and feedback.

Actions:
- Build `substrate/execution/spine.py` implementing the canonical sequence:
  interpret -> recall -> lookup -> compose -> route -> execute -> trace -> feedback
- Build `substrate/execution/trace.py` (every execution produces a trace record in Neon)
- Build `substrate/execution/feedback.py` (outcome capture)
- Wire spine to call Tier 1 subsystems (governance, memory, registry)
- Wire spine to call Tier 3 adapters (model routing)
- Migrate ingestion pipeline into `substrate/execution/ingestion/`
- Build `substrate/__init__.py` public API
- Write end-to-end tests: signal in -> trace out

Deliverable: The single execution spine works end-to-end.
`substrate.execute(signal)` produces a traced, governed result.

### Phase 4 — Tier 3: Adapters (Day 16-18)

**Goal:** All external connections through formal adapter interface.

Actions:
- Move model_router + cc_sdk to `adapters/models/`
- Define `Adapter` protocol (connect, execute, health_check, capabilities)
- Wrap GWS connector as adapter
- Wrap voice engine as adapter
- Wrap vision (camera/image analysis) as adapter
- Register all adapters in unified registry
- Write adapter health check tests

Deliverable: Every external system reached through a typed adapter interface.
Spine routes to adapters via registry lookup.

### Phase 5 — Transports (Day 19-22)

**Goal:** All user interfaces produce SignalEnvelopes and route through substrate.

Actions:
- Refactor discord_bot.py into `transports/discord/bot.py`
  - Strip direct gateway calls
  - Produce SignalEnvelope for every message
  - Call `substrate.execute(envelope)` for responses
  - Keep voice/vision attachment handling (produce multimodal envelopes)
- Refactor operator_api.py into `transports/api/operator.py`
  - WebSocket and REST both produce SignalEnvelopes
  - Call substrate for execution
- Move cockpit to `transports/cockpit/` (wire later)
- Rebuild Docker containers with new paths
- Write transport integration tests

Deliverable: Discord bot and operator API running through the substrate spine.
Every message traced. Containers rebuilt.

### Phase 6 — Prune and Verify (Day 23-25)

**Goal:** Delete everything not wired. Verify the system is clean.

Actions:
- Delete all empty/dead directories from the old structure
- Delete all files not imported by any surviving module
- Run full test suite, fix failures
- Run `python3 -m py_compile` on every .py file
- Run `ruff format` on all surviving code
- Rebuild codebase graph (`scripts/update-graph`)
- Update memory palace rooms to reflect new structure
- Update all CLAUDE.md files with new paths
- Update all skill files with new paths
- Rename `10_Wiki/` to `knowledge/` and update all references
- Verify Docker containers start and process messages

Deliverable: Clean repository. No dead code. No broken imports.
Full test suite green. Docker running.

### Phase 7 — EOS Projection (Day 26-30)

**Goal:** First application layer on the substrate.

Actions:
- Build `projections/eos/__init__.py` with EOS-specific signal handlers
- Build `projections/eos/agents/` with department agents (CEO, Sales, Marketing)
  registered in unified registry
- Build `projections/eos/workflows/` with outreach, follow-up, content calendar
  as substrate execution plans
- Build `projections/eos/views/` with CRM state, pipeline, KPIs as memory queries
- Wire EOS agents to respond via Discord transport
- Test: Initiate Arena outreach workflow flows through substrate

Deliverable: EOS running on the substrate. First business operations
flowing through the canonical architecture.

---

## Neon Schema Changes

### Keep (no changes)
- `interactions` (35,485 rows)
- `embeddings` (35,277 rows)
- `events` (27,851 rows)
- `entity_links` (30,717 rows)
- `organizations` (2 rows)
- `ventures` (8 rows)
- `agents` (16 rows)
- `skills` (140 rows)
- `memory_store` (63 entries)

### Add
- `traces` — one row per execution (signal_id, execution_id, provider,
  model, duration_ms, risk_class, input_hash, output_hash, timestamp)
- `feedback` — one row per outcome observation (trace_id, outcome_type,
  quality_score, learning_signal, timestamp)
- `adapter_registry` — unified adapter registration (adapter_id, type,
  capabilities, health_status, last_check)
- `component_registry` — unified component registration (component_id,
  component_type, metadata, registered_at)

### Migrate (additive, no destruction)
- `outcomes` (4 rows) — link to new `feedback` table via trace_id

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Import breakage after file moves | Phase 0 verifies all imports before code changes |
| Lost functionality during merge | Phase-by-phase integration tests verify each tier |
| CLAUDE.md/skills path rot | Dedicated cleanup in Phase 6 with grep verification |
| Neon data loss | No destructive schema changes. New tables added alongside existing. |
| Docker container failures | Full rebuild in Phase 5 with health check verification |
| Knowledge graph breakage | Full rebuild in Phase 6 after structure stabilizes |
| Regression in proven code | model_router, memory, db, GWS move without logic changes |

---

## Success Criteria

Substrate MVP is complete when:
1. Every signal (Discord, API, cron) enters through one spine
2. Every execution produces a trace record in Neon
3. Governance classifies and can block every execution
4. Memory stores and retrieves through one interface
5. Registry discovers agents, skills, and adapters from one source
6. Ontology primitives are used in ingestion and signal interpretation
7. Adapters connect through a formal interface
8. Zero dead code remains (every file imported by something)
9. All tests pass
10. Docker containers run and process messages
11. EOS projection handles at least one business workflow through substrate

---

## Post-MVP Roadmap

After substrate MVP, the remaining 13 subsystems build on this foundation:

1. **Template System** -> `substrate/control_plane/templates.py`
2. **Library System** -> `substrate/control_plane/library.py`
3. **Composition Engine** -> `substrate/execution/composition.py`
4. **Completeness Engine** -> `substrate/execution/completeness.py`
5. **Quality Engine** -> `substrate/execution/quality.py`
6. **World Model** -> `world_model/` (Tier 4)
7. **Simulation** -> `intelligence/simulation/` (Tier 5)
8. **Deliberation Council** -> `intelligence/deliberation/` (Tier 5)
9. **Law Kernel (full)** -> `substrate/ontology/law_kernel.py`
10. **Workstation Modes** -> `substrate/control_plane/workstation.py`
11. **Self-Recursion** -> `substrate/learning/self_recursion.py`
12. **Resource Allocation** -> `substrate/control_plane/resources.py`
13. **Homeostasis** -> `substrate/learning/homeostasis.py`

Each builds on the substrate API. No architectural changes needed.
