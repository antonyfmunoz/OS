# UMH Full Convergence — Architecture & Migration Spec

**Date:** 2026-05-22
**Status:** Draft v1.0
**Supersedes:** `2026-05-21-umh-substrate-unification-design.md` (retained as migration reference)
**Scope:** Converge all legacy code into one coherent UMH system. ~616 legacy files → absorbed or deleted.
**Timeline:** 5–7 weeks, 8 phases

---

## Part I — What UMH Is

This section defines the system being built. It is the architectural contract for all convergence decisions.

### 1. Core Identity

UMH is a governed, stateful, reality-modeling intelligence operating system. It is one system — not a collection of subsystems bolted together. Digital and physical actuation, deterministic logic and AI reasoning, memory and execution, interface and kernel — all facets of one unified runtime.

UMH is not a chatbot, not a model wrapper, not a tool wrapper, not a SaaS product, not a single agent. It is the governed intelligence runtime that coordinates all of them.

### 2. The Reality Model (Core Breakthrough)

UMH mirrors reality at the first-principle level. Reality is simulated through energy; the Reality Model is simulated through code. This is general-purpose — not business-specific. Business is one domain and use case among many.

**Four layers of the Reality Model:**

| Layer | Purpose | Mutability |
|-------|---------|:----------:|
| **Canonical Reality Model** | Compressed, reusable intelligence. Universal patterns, governance laws, verified templates, domain laws. Pre-filled so the system is useful for new users from day one. | Sacred. Updated only through governed promotion. |
| **Instance Reality Model** | Live operational truth of one user/company/environment. Contextual, volatile. | Updated through governed execution outcomes. |
| **Sandbox Reality** | Temporary cloned execution state for safe experimentation. Produces diff/proof, requires governance approval before merging back to Instance. | Ephemeral. Destroyed after merge or discard. |
| **Simulation Reality** | Hypothetical, non-mutating possibility space. "What if" without consequences. | Never mutates anything. Read-only exploration. |

**The compounding loop:**

```
Canonical → Instance context → Execution → Evidence
  → Instance Update → Pattern Compression → Possible Canonical Promotion
```

Each execution cycle makes the Instance smarter. Compressed patterns from Instance may be promoted to Canonical (governed), making the platform smarter for all users.

### 3. Ontology as Computational Physics

The ontology governs UMH the way physics governs reality. These are not metadata descriptions — they are enacted constraints in code at every layer.

**10 Primitives:** state, change, constraint, resource, time, signal, feedback, goal, action, outcome

**13 Governing Laws:** causality, feedback, compounding, entropy, emergence, constraints, equilibrium, temporal dependency, resource scarcity, tradeoffs, local/global optimization, polarity/tension, system boundary effects

**Ontological Categories (8):** entity, relation, event, property, process, state, constraint, boundary

**Relationship Types (10):** causes, constrains, enables, requires, precedes, follows, produces, consumes, measures, conflicts_with

Every signal decomposed, every state transition validated, every action governed — all against this ontological framework.

### 4. Product Architecture (Peer Relationship)

OST (the company) produces peer products: UMH, EOS, CreatorOS, LyfeOS. They are at the same level — they do different things.

**UMH projects into each platform** — a scoped projection of full capability, constrained to that platform's purpose. Platforms own nothing of UMH. The boundary is absolute. Similar to the dual Reality Model: the full UMH capability set gets projected and constrained to each platform's interface and scoped purpose.

```
UMH ──projection──→ EOS (entrepreneur operations)
    ──projection──→ CreatorOS (content creation)
    ──projection──→ LyfeOS (life management)
```

Each projection integrates with UMH at a deeper level than external integrations — they are part of OST's ecosystem/infrastructure. But they do not import UMH internals. They call the substrate public API only.

### 5. The Leverage Principle

Controller → Leverage → Ownership.

UMH harnesses external systems (tools, models, APIs, platforms), learns from them, compresses patterns into canonical knowledge, and eventually replaces them with owned capability. "They coded the product, so can we."

The system is designed to supersede all other systems over time through compounding. This is why the adapter boundary exists — external systems are behind an abstraction that allows swapping or replacing without architectural change.

### 6. Deterministic + AI = One System

Not a fallback architecture. Both always active for maximum leverage.

- **Deterministic:** reliability, speed, auditability, governance enforcement, rules/regex/lookup tables.
- **AI:** reasoning, adaptation, synthesis, creative generation, contextual enhancement.
- **Intelligence is subordinate to control.** AI recommends; deterministic logic decides what moves forward.

Build deterministic result → try AI enhancement → use AI if better, keep deterministic if not. The system always produces output regardless of AI availability.

### 7. Operational Modes (Two Levels)

**System-level modes** — broad operational postures:

| Mode | Description | Parallel? |
|------|-------------|:---------:|
| Active | User at workstation | Mutually exclusive with Away/Overnight/Remote |
| Away | User stepped away | Mutually exclusive with Active/Overnight/Remote |
| Overnight | User sleeping | Mutually exclusive with Active/Away/Remote |
| Remote | User on mobile/remote device | Mutually exclusive with Active/Away/Overnight |
| Self-Improvement | System improving itself | Can run in parallel |
| Maintenance | System maintenance tasks | Can run in parallel |
| Simulation | Hypothetical exploration | Can run in parallel |
| Emergency | Critical issue handling | Can run in parallel, overrides lower priority |

**Profile modes** — personalized, customizable, stackable:

Connected to workstation/cockpit. Include tool launching and startup flows. Never restrict background work. Leverage tools for the user.

Examples: Developer, Research, Outreach, Content, Growth. These are customizable per user and can stack (e.g., Developer + Research simultaneously).

### 8. Workstation

Every connected device is part of one unified workstation. Not just the cockpit — includes other tools connected via profile modes and startup flows.

The cockpit is UMH's native interface. It allows manual control and displays system state. The interface is not the system — it is the user's window into UMH.

### 9. Physical Actuation

All one system. Robotic arms, IoT, wearables, vehicles, environmental controls — they flow through the same execution spine, same governance, same trace, same proof as every digital action. The adapter boundary law covers physical systems identically.

A command to a robotic arm and a command to a CRM API differ only in risk class and adapter implementation, not in architectural treatment. Physical-world actuation is highest risk class requiring strictest governance.

### 10. The 12 Invariant Laws

Non-negotiable. Any violation = architectural failure.

1. **Control Plane Exclusivity** — all signals, decisions, actions pass through Control Plane
2. **Single Execution Spine** — one canonical runtime path
3. **Governance Before Execution** — no execution without governance classification
4. **Typed Contracts Only** — explicit schemas, no implicit prompt-string contracts
5. **Memory Discipline** — all durable state through Memory/Storage subsystem
6. **Environment Explicitness** — every action declares target environment
7. **Trace Completeness** — every execution produces inspectable trace
8. **Deterministic + AI Core** — intelligence subordinate to control
9. **External Boundary Law** — no external system accessed directly, all through adapters
10. **Action/Execution Separation** — action ≠ capability ≠ adapter ≠ environment ≠ worker ≠ actuation ≠ work packet ≠ proof
11. **Mastery Law** — verify competence before execution
12. **Reality Mimicry** — model after effective real-world patterns when technically useful

### 11. The 10 Macro-Layers

Every subsystem belongs to exactly one layer. No orphan systems.

```
UMH
├─ 1. Interface — manual control + workstation + all user surfaces
├─ 2. Control Plane — canonical runtime, invariant enforcement, authority
├─ 3. Understanding — signal → structured meaning (perception, interpretation, decomposition)
├─ 4. State — dual Reality Model, ontology enforced as live constraints, memory, profiles
├─ 5. Composition — intent + state → executable systems (registries, libraries, templates, capabilities)
├─ 6. Governance — authority, risk, policy, approval
├─ 7. Execution — governed work through single spine, workers, actuation
├─ 8. Adapter Boundary — external system translation (digital and physical)
├─ 9. Observability + Proof — trace, proof, audit
└─ 10. Learning + Self-Regulation — feedback to ALL layers (where applicable)
```

### 12. The 27-Step Canonical Runtime Spine

The one authorized path from signal to learning:

```
Signal → Control Plane Intake → Perception → Interpretation → Decomposition
  → Ontology Mapping → Domain Mapping → Reality Model Retrieval
  → Breadth Expansion → Completeness Detection
  → Registry/Library/Template Lookup → Capability Selection
  → Adapter/Environment Matching → Composition → Planning
  → Mastery Check → Quality Check → Governance Decision
  → Work Packet Creation → Worker Routing
  → Adapter-Bound External Interaction → Actuation
  → Result Collection → Proof Validation → Trace Persistence
  → Outcome Evaluation → Learning Proposal
  → Reality Model Update → Self-Regulation
```

No module may create a shortcut around this spine. Learning feeds back to ALL layers, not just state.

---

## Part II — Current State Assessment

### 13. What Exists Today

**Production substrate (~500 LOC real implementation):**

| Component | Location | Lines | Status |
|-----------|----------|------:|--------|
| Public API | `substrate/__init__.py` | 94 | CONFIRMED_RUNTIME |
| Type system | `substrate/types.py` | ~700 | CONFIRMED_RUNTIME |
| Identity resolver | `substrate/control_plane/identity.py` | ~120 | CONFIRMED_RUNTIME |
| Context assembler | `substrate/control_plane/context.py` | ~80 | CONFIRMED_RUNTIME |
| Governance engine | `substrate/control_plane/governance.py` | ~150 | CONFIRMED_RUNTIME |
| Memory system | `substrate/control_plane/memory.py` | ~100 | CONFIRMED_RUNTIME |
| Component registry | `substrate/control_plane/registry.py` | ~80 | CONFIRMED_RUNTIME |
| Signal router | `substrate/control_plane/router.py` | 112 | CONFIRMED_RUNTIME |
| Execution spine | `substrate/execution/spine.py` | 274 | CONFIRMED_RUNTIME |
| Trace recorder | `substrate/execution/trace.py` | ~100 | CONFIRMED_RUNTIME |
| Feedback capture | `substrate/execution/feedback.py` | ~80 | CONFIRMED_RUNTIME |
| Ontology | `substrate/ontology/` | ~200 | CONFIRMED_RUNTIME |
| Ingestion | `substrate/execution/ingestion/` | ~400 | CONFIRMED_RUNTIME |

**Production-proven legacy (the real capabilities):**

| Component | Location | Lines | Value |
|-----------|----------|------:|-------|
| Model router | `adapters/models/model_router.py` | 1,516 | Multi-provider LLM routing with circuit breaker |
| CC SDK | `adapters/models/cc_sdk.py` | 464 | Opus 4.6 via Max subscription |
| CLI adapters | `adapters/models/codex_cli.py`, `hermes_cli.py`, `opencode_cli.py` | 616 | Agent CLI adapters |
| Agent runtime | `adapters/models/agent_runtime.py` | 628 | Multi-model dispatch |
| Discord bot | `services/discord_bot.py` | 5,481 | Primary user interface |
| Gateway | `control_plane/runtime/gateway.py` | 2,063 | Signal routing + intent classification |
| Cognitive loop | `control_plane/runtime/cognitive_loop.py` | 1,448 | 8-stage execution pattern |
| Agent memory | `state/memory/memory.py` | 1,039 | Neon-backed memory + embedding |
| Authority engine | `governance/policy/authority_engine.py` | 225 | Risk classification |
| Intent handler | `interface/presence/handlers/intent_handler.py` | 410 | Deterministic intent classification |
| Capability router | `execution/runtime/capability_router.py` | 610 | Intent-driven tool selection |
| GWS adapters | `adapters/google_workspace/` | 3,531 | Google Workspace integration |
| Cockpit API | `services/umh/control_plane/cockpit_api.py` | 1,034 | 40 live endpoints |
| Organism runtime | `services/umh/organism/` | 1,554 | Multi-agent society |
| Node mesh | `services/umh/node_mesh/` | 850 | Multi-device coordination |
| Voice first | `execution/transport/voice_first.py` | 370 | Voice-first response path |
| Domain bridges | `understanding/domains/creator.py`, `life.py` | 1,083 | Domain-typed projections |
| Platform integrations | `services/umh/integrations/` | 5,148 | CreatorOS + LyfeOS signal handlers |
| Windows daemon | `daemon/` | 1,278 | Desktop adapters |
| Operator API | `services/operator_api.py` | 554 | REST operator interface |

**Dead or duplicate (~230,000 lines across ~600 files):**

- `services/umh/` — 169 files, ZERO production callers
- `execution/workers/workstation/` — constitutional engines, never run
- `execution/transport/` — bulk transport infra (except voice_first.py)
- `execution/runtime/` — v1 contracts superseded by substrate types
- Various `control_plane/`, `core/`, `understanding/` subdirs
- `archive/` — 93 files, already archived
- Dead test files for deleted code

### 14. The Gap

The substrate is structurally correct but thin. It's scaffolding — the Protocols and types exist, but the real execution logic is still in legacy code. Specifically:

1. **Execution spine** — 274 lines with regex intent matching and simple prompt composition. Needs to absorb the cognitive loop's 8-stage pattern, memory recall, capability routing, and model dispatch.
2. **Signal router** — 112 lines. Needs the gateway's production-proven routing logic, intent classification, and fix-forever error recording.
3. **Governance** — basic risk classification. Needs authority engine's full risk class matrix and autonomy level enforcement.
4. **Memory** — thin wrapper. Needs the full `AgentMemory` + `ConversationMemory` pipeline with semantic search and authority-tiered recall.
5. **Identity** — loads from environment. Needs BIS integration, personality resolution, and multi-venture context.
6. **Context** — minimal. Needs conversation history assembly, semantic recall, active goals, business context.
7. **Reality Model** — not implemented. The dual Canonical/Instance model is the core architectural breakthrough and has no code yet.
8. **Ontology enforcement** — primitives exist as enums but are not enacted as runtime constraints.
9. **Transports** — Discord bot still routes through legacy gateway, not through substrate.

---

## Part III — Convergence Plan

### 15. Binding Decisions

Locked. No further discussion.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Pydantic `BaseModel` with `UUID` IDs is the sole type system | Runtime dataclasses are weaker; UMH protocols already define Pydantic models |
| 2 | `SignalEnvelope` is the universal input type for all transports | Every transport produces one shape |
| 3 | `model_router.call_with_fallback()` is the sole LLM adapter — wrapped, not replaced | 1,516 lines, circuit breaker, multi-provider, production-proven |
| 4 | No Neon schema destruction — new tables added alongside existing | 35,485 interactions, 35,277 embeddings, 27,851 events |
| 5 | `substrate/__init__.py` is the only public API for projections | Projections never import `substrate.control_plane.*` |
| 6 | Full rebuild window — Discord bot offline during migration | Founder-approved; no external users yet |
| 7 | Directory names are production-grade | `knowledge/` not `10_Wiki/`, `substrate/` not `services/umh/` |
| 8 | Ontology primitives and laws are enacted in code, not stored as text | They govern the system the way physics governs reality |
| 9 | Physical and digital actuation follow the same spine/governance/trace | All one system |
| 10 | Reality Model is general-purpose, not business-specific | Business is one domain among many |

### 16. Directory Structure

```
/opt/OS/
├── substrate/                        # The UMH kernel
│   ├── __init__.py                   # Public API: execute(), query(), register(), ingest(), status()
│   ├── types.py                      # Single Pydantic type system
│   ├── ontology/                     # Primitives, laws, relationships — enacted as runtime constraints
│   │   ├── primitives.py             # PrimitiveType, OntologicalCategory, PrimitiveObservation
│   │   ├── laws.py                   # 13 governing laws as enforceable constraints
│   │   ├── relationships.py          # RelationshipType, typed edges
│   │   └── domains/                  # Domain bridges (creator.py, life.py, business.py)
│   ├── control_plane/                # Identity, context, governance, memory, registry, router
│   │   ├── identity.py               # IdentityResolver — BIS + personality + multi-venture
│   │   ├── context.py                # ContextAssembler — conversation + memory + goals + business
│   │   ├── governance.py             # GovernanceEngine — risk classification + authority enforcement
│   │   ├── memory.py                 # MemorySystem — unified over AgentMemory + ConversationMemory
│   │   ├── registry.py               # ComponentRegistry — unified Neon-backed component discovery
│   │   └── router.py                 # SignalRouter — gateway logic + intent classification + error recording
│   ├── execution/                    # Spine, trace, feedback, ingestion
│   │   ├── spine.py                  # ExecutionSpine — full 8-stage merged pipeline
│   │   ├── trace.py                  # TraceRecorder — Neon-persisted execution traces
│   │   ├── feedback.py               # FeedbackCapture — quality scoring + learning loop
│   │   └── ingestion/                # Canonical ingestion pipeline
│   ├── reality_model/                # Dual Reality Model (post-MVP foundation, Phase 8)
│   │   ├── canonical.py              # Canonical Reality Model — governed, promoted patterns
│   │   ├── instance.py               # Instance Reality Model — live operational truth
│   │   ├── sandbox.py                # Sandbox Reality — safe experimentation
│   │   └── simulation.py             # Simulation Reality — hypothetical exploration
│   ├── organism/                     # Multi-agent society (from services/umh/organism/)
│   │   ├── daemon.py
│   │   ├── advisor.py
│   │   ├── worker_cell.py
│   │   ├── approval_store.py
│   │   └── ...
│   └── learning/                     # Feedback-to-all-layers (post-MVP)
│
├── adapters/                         # External system interfaces (digital + physical)
│   ├── protocol.py                   # Adapter Protocol
│   ├── models/                       # LLM routing (model_router.py preserved as-is)
│   ├── google_workspace/             # GWS connector + scanner
│   ├── browser/                      # Browser automation
│   ├── calendar/                     # Calendar
│   ├── notion/                       # Notion sync
│   └── capabilities/                 # Voice, vision, media processing
│
├── transports/                       # User-facing interfaces
│   ├── discord/                      # Discord bot (refactored from services/discord_bot.py)
│   │   ├── bot.py                    # Substrate-wired bot
│   │   ├── signal_factory.py         # Message → SignalEnvelope
│   │   └── voice_first.py            # Voice-first response path
│   ├── api/                          # REST + WebSocket
│   │   ├── operator.py               # Operator API
│   │   ├── cockpit.py                # Cockpit governance API (40 endpoints)
│   │   └── signal_factory.py
│   ├── cockpit/                      # React dashboard (future)
│   └── node_mesh/                    # Multi-device WebSocket mesh
│
├── projections/                      # Application layers (peer products)
│   └── eos/                          # EntrepreneurOS — constrained projection of UMH
│       ├── agents/                   # Department agents (CEO, Sales, Marketing)
│       ├── workflows/                # Outreach, follow-up, content calendar
│       └── views/                    # CRM, pipeline, KPIs as memory queries
│
├── state/                            # Persistence layer
│   ├── storage/db.py                 # Neon connection pool
│   ├── memory/memory.py              # AgentMemory + ConversationMemory
│   ├── context/context.py            # System context loader
│   ├── business/business_instance.py # BIS, venture config
│   └── registries/skill_registry.py  # Skill registry backing store
│
├── integrations/                     # Platform integration adapters
│   ├── creatoros/                    # CreatorOS signal/handler/outcome
│   └── lyfeos/                       # LyfeOS signal/handler/outcome
│
├── daemon/                           # Windows node daemon (stays — runs on desktop, not VPS)
├── knowledge/                        # Wiki, palace, concept docs (replaces 10_Wiki/)
├── scripts/                          # Operator tooling
├── data/                             # Generated data, proofs, audits
├── docs/                             # Architecture specs, contracts
├── skills/                           # Claude Code tool skills
└── tests/                            # Unified test suite
```

### 17. Substrate Public API

`substrate/__init__.py` — the only import path projections may use.

```python
class Substrate:
    async def execute(self, signal: SignalEnvelope) -> ExecutionResult:
        """Route a signal through the full substrate lifecycle."""

    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Query the memory system."""

    async def register(self, component: Component) -> RegistrationResult:
        """Register a component in the registry."""

    async def ingest(self, source_uri: str, authority_tier: int = 5) -> IngestionResult:
        """Ingest a document into the ontology layer."""

    def status(self) -> SubstrateStatus:
        """Synchronous health check."""
```

**Hard invariant:** `grep -rn "from substrate\." projections/ | grep -v "from substrate import\|from substrate.types"` must produce zero output.

### 18. Subsystem Protocols

Each subsystem is a `@runtime_checkable Protocol`. The substrate wires concrete implementations at init time. Tests can substitute fakes.

**18.1 IdentityResolver** — resolves signal → Identity (BIS + personality + org/venture config)

**18.2 ContextAssembler** — assembles signal + identity → ExecutionContext (conversation history + semantic recall + goals + business context)

**18.3 GovernanceEngine** — classifies signal + context → GovernanceVerdict (risk class, decision, rationale). Risk matrix from production `authority_engine.py`:

| Class | Actions | Auto-execute? |
|-------|---------|:-------------:|
| CRITICAL | send_message, send_email, execute_payment, delete_records, physical_actuation | Never |
| HIGH | send_dm, create_outreach, post_content, update_external_crm | Autonomy ≥ 3 |
| MEDIUM | draft_message, draft_content, create_task, create_document | Autonomy ≥ 1 |
| LOW | analyze, research, score, classify, summarize, read, query | Always |

**18.4 MemorySystem** — recall, store, log_interaction. Wraps existing AgentMemory + ConversationMemory. Authority tier ordering in search.

**18.5 ComponentRegistry** — register, lookup, get, deregister. Neon-backed. If it's not registered, it doesn't exist to the substrate.

**18.6 SignalRouter** — single entry point from transports. Orchestrates: identity → context → governance → spine.

**18.7 ExecutionSpine** — the 8-stage merged pipeline:

| # | Stage | What it does | Source |
|---|-------|-------------|--------|
| 1 | Interpret | Deterministic intent classification → LLM decomposition if needed | gateway + intent_handler (deterministic-first) |
| 2 | Recall | Semantic memory search for relevant context | AgentMemory.semantic_search |
| 3 | Lookup | Registry query for capable adapters/agents + capability routing | capability_router + registry |
| 4 | Compose | Build execution plan (prompt + model selection + params) | CogLoop.PLAN |
| 5 | Route | Select adapter and dispatch | model_router.call_with_fallback() |
| 6 | Execute | Invoke adapter, deterministic fallback if all LLMs fail | CogLoop.EXECUTE + deterministic spine |
| 7 | Trace | Record full execution provenance + error recording | TraceStore + fix-forever |
| 8 | Feedback | Capture outcome observation + quality signal | CogLoop.REFLECT/LEARN + OutcomeClassifier |

**18.8 TraceRecorder** — Neon-persisted execution traces. Every completed trace has ≥2 events.

**18.9 FeedbackCapture** — every completed execution produces exactly one FeedbackRecord.

### 19. Type System

All types are Pydantic `BaseModel` with `UUID` identifiers. See the prior spec (Section 6) for the complete type definitions — they are unchanged and carry forward. Key types:

- `SignalEnvelope` — universal input
- `Identity` — resolved execution identity
- `ExecutionContext` — assembled context
- `GovernanceVerdict` — risk classification + decision
- `ExecutionPlan` — what the spine intends to do
- `AdapterResponse` — response from any adapter
- `ExecutionResult` — complete result of processing a signal
- `TraceRecord` / `TraceEvent` — execution trace
- `FeedbackRecord` — outcome quality + learning signal
- `MemoryEntry` / `MemoryQuery` — memory system
- `Component` / `RegistrationResult` — registry
- `PrimitiveType` / `OntologicalCategory` / `RelationshipType` — ontology
- `PrimitiveObservation` — decomposed observations
- `IngestionResult` / `SubstrateStatus` — operational types

### 20. Signal Lifecycle

```
CREATED → ROUTED → IDENTITY_RESOLVED → CONTEXT_ASSEMBLED
  → CLASSIFIED → APPROVED/BLOCKED/PENDING
  → EXECUTING → SUCCESS/FAILED
  → TRACED → FEEDBACK_CAPTURED
```

Terminal states: BLOCKED, FEEDBACK_CAPTURED.
Errors at any stage still trace and feed back.

### 21. Neon Schema

No existing tables modified or dropped. Three new tables added (unchanged from prior spec):
- `traces` — execution traces with RLS
- `feedback` — execution feedback with RLS
- `component_registry` — unified component discovery with RLS

### 22. Invariants as Assertions

Ten checkable statements (unchanged from prior spec Section 11):

1. Control plane exclusivity — no adapter call outside spine
2. Single execution spine — only spine.py calls adapters
3. Governance before execution — spine checks verdict
4. Trace everything — every execution path calls trace.persist()
5. Memory discipline — no direct Neon writes outside state/
6. Registry as truth — spine only routes to registered components
7. Feedback closes loops — every trace gets a feedback record
8. Public API boundary — projections never import substrate internals
9. Zero dead code — every .py file under substrate/ is imported
10. Pydantic only — no runtime dataclasses in substrate/

---

## Part IV — Migration Phases

### Phase 0 — Archive and Scaffold (Day 1–2)

**Goal:** Preserve current state, create directory structure, move files without logic changes.

1. `git tag pre-unification` on current HEAD
2. Create all directories per Section 16
3. Move surviving files to new locations
4. Update all `sys.path` and imports
5. Rename `10_Wiki/` → `knowledge/`

**Gate:** All moved files compile. `import substrate` works.

### Phase 1 — Ontology as Enacted Constraints (Day 3–4)

**Goal:** Single source of truth for primitives, laws, relationships — enacted in code, not stored as text.

1. Merge `understanding/ontology/primitives.py` + `services/umh/foundation/primitives.py` → `substrate/ontology/primitives.py`
2. Migrate `services/umh/foundation/laws.py` → `substrate/ontology/laws.py` with enforcement hooks
3. Migrate domain bridges → `substrate/ontology/domains/`

**Gate:** `len(PrimitiveType) == 10`, `len(OntologicalCategory) == 8`, `len(RelationshipType) == 10`. Laws are callable constraints, not just strings.

### Phase 2 — Control Plane (Day 5–10)

**Goal:** Unified identity, governance, memory, registry, signal routing with full production logic absorbed.

1. `identity.py` — merge ai_identity + context + BIS
2. `context.py` — merge context loader + conversation history + semantic recall + goals + business context
3. `governance.py` — merge authority_engine risk classes + UMH governance protocol
4. `memory.py` — unified protocol over existing AgentMemory + ConversationMemory
5. `registry.py` — unified registry backed by Neon component_registry table
6. `router.py` — absorb gateway routing logic, intent classification, fix-forever error recording, capability routing

**Gate:** All control plane subsystems importable and satisfy their Protocols.

### Phase 3 — Execution Spine + Trace + Feedback (Day 11–15)

**Goal:** Single execution path with full cognitive loop logic, Neon-persisted trace and feedback.

1. `spine.py` — absorb cognitive_loop 8 stages, agent_runtime dispatch, capability_router selection, deterministic-first fallbacks
2. `trace.py` — Neon persistence for traces
3. `feedback.py` — auto-generated implicit feedback per execution
4. Wire `substrate/__init__.py` public API
5. Run Neon DDL for new tables

**Gate:** End-to-end signal → trace round trip works. Every execution produces trace + feedback.

### Phase 4 — Adapters (Day 16–18)

**Goal:** All external connections through formal adapter interface.

1. `adapters/protocol.py` — Adapter Protocol
2. `adapters/models/llm_adapter.py` — wrapper around model_router (model_router untouched)
3. Wrap GWS, voice, browser as formal adapters
4. Register all adapters in component registry at boot

**Gate:** LLMAdapter satisfies Adapter protocol. All adapters registered.

### Phase 5 — Transports (Day 19–22)

**Goal:** All user interfaces produce SignalEnvelope and route through `substrate.execute()`.

1. Refactor `services/discord_bot.py` → `transports/discord/bot.py` (strip direct gateway/cognitive_loop calls, use signal_factory + substrate.execute)
2. Refactor `services/operator_api.py` → `transports/api/operator.py`
3. Migrate cockpit API → `transports/api/cockpit.py`
4. Migrate node mesh → `transports/node_mesh/`
5. Migrate voice_first → `transports/discord/voice_first.py`
6. Rebuild Docker containers

**Gate:** Discord bot starts, connects, routes through substrate. Traces appear in Neon.

### Phase 6 — Prune and Verify (Day 23–25)

**Goal:** Delete everything not wired. Verify clean system.

1. Delete all empty/dead directories
2. Delete all files not imported by surviving modules (~230,000 lines, ~600 files)
3. Full test suite pass
4. `py_compile` all files, `ruff format` all code
5. Rebuild codebase graph
6. Update memory palace, CLAUDE.md files, skill files

**Gate:** Zero dead code. All invariants pass. All Docker containers healthy.

### Phase 7 — EOS Projection (Day 26–30)

**Goal:** First application layer on the substrate.

1. `projections/eos/__init__.py` — EOS-specific signal handlers
2. Department agents (CEO, Sales, Marketing) registered in registry
3. Outreach workflow as substrate execution plan
4. CRM views as memory queries
5. Wire EOS agents to respond via Discord transport

**Gate:** EOS agents registered. Outreach workflow executes through substrate.

### Phase 8 — Reality Model Foundation (Day 31–35)

**Goal:** Lay the structural foundation for the dual Reality Model. Not full implementation — that's post-MVP. But the architectural skeleton must exist.

1. `substrate/reality_model/canonical.py` — Canonical Reality Model store interface
2. `substrate/reality_model/instance.py` — Instance Reality Model per-user state
3. Schema for canonical patterns + instance state in Neon
4. Promotion pipeline: Instance observation → pattern compression → canonical promotion candidate → governance gate → canonical write
5. Integration with ingestion pipeline: decomposed observations feed Instance Reality Model

**Gate:** Canonical store persists and retrieves patterns. Instance store per-user. Promotion pipeline has governance gate. Ingestion feeds instance.

---

## Part V — What Gets Deleted (~230,000 lines)

| Category | ~Lines | ~Files | Value Extracted? |
|----------|-------:|-------:|:----------------:|
| `execution/workers/workstation/` constitutional engines | 20,000 | 45 | No — future organism runtime |
| `execution/transport/` (except voice_first.py) | 19,600 | 59 | Partial — patterns inform transports/ |
| `execution/runtime/` v1 contracts (except model_router, agent_runtime, capability_router) | 12,000 | 37 | Yes — superseded by substrate/types.py |
| `services/umh/` remainder after extraction | 15,000 | 80 | Yes — protocols + organism + mesh extracted |
| `control_plane/` non-core subdirs | 10,000 | 35 | No — rebuild on substrate when needed |
| `core/` most files | 4,000 | 20 | Partial |
| `understanding/` non-ontology remainder | 4,000 | 12 | Yes — ontology merged |
| `execution/environments/`, `workflows/`, `agents/`, `tasks/`, `engine/` | 5,200 | 22 | Partial — patterns absorbed |
| `runtime/` root-level stubs | 800 | 8 | Yes |
| `interface/` (after intent_handler extraction) | 3,600 | 14 | Yes |
| `observability/` (after trace extraction) | 900 | 5 | Yes |
| `operations/` (after memory merge) | 2,400 | 10 | Yes |
| `archive/` | 23,000 | 93 | No — already archived |
| `.agents/` soul docs | 9,000 | 35 | Partial — agent definitions → registry |
| Dead test files | 20,000 | 100+ | No |
| Misc duplicates and dead imports | 5,000+ | 50+ | N/A |

**Total deleted: ~230,000 lines across ~600+ files.**
**Total surviving: ~100,000–110,000 lines across ~250 files.**

Pre-deletion safeguard: `git tag pre-unification` preserves full history.

---

## Part VI — What Survives (Source Mapping)

### Production-proven code (relocate, do not modify logic)

| Current Location | New Location | Lines |
|------------------|-------------|------:|
| `adapters/models/model_router.py` | stays | 1,516 |
| `adapters/models/cc_sdk.py` | stays | 464 |
| `adapters/models/codex_cli.py` | stays | 258 |
| `adapters/models/hermes_cli.py` | stays | 178 |
| `adapters/models/opencode_cli.py` | stays | 180 |
| `adapters/models/agent_runtime.py` | stays | 628 |
| `state/memory/memory.py` | stays | 1,039 |
| `state/storage/db.py` | stays | ~100 |
| `state/context/context.py` | stays | ~200 |
| `state/business/business_instance.py` | stays | ~200 |
| `adapters/google_workspace/` | stays | 3,531 |
| `state/registries/skill_registry.py` | stays | ~200 |
| `services/discord_bot.py` | `transports/discord/bot.py` | 5,481 |
| `services/operator_api.py` | `transports/api/operator.py` | 554 |

### Code merged into substrate (extract logic, delete originals)

| Current Location | Merges Into |
|------------------|-------------|
| `control_plane/runtime/cognitive_loop.py` (1,448) | `substrate/execution/spine.py` |
| `control_plane/runtime/gateway.py` (2,063) | `substrate/control_plane/router.py` |
| `governance/policy/authority_engine.py` (225) | `substrate/control_plane/governance.py` |
| `control_plane/identity/ai_identity.py` (~300) | `substrate/control_plane/identity.py` |
| `interface/presence/handlers/intent_handler.py` (410) | `substrate/control_plane/router.py` |
| `execution/runtime/capability_router.py` (610) | `substrate/control_plane/router.py` |
| `services/umh/foundation/primitives.py` | `substrate/ontology/primitives.py` |
| `services/umh/foundation/laws.py` | `substrate/ontology/laws.py` |
| `services/umh/protocols/*.py` | `substrate/types.py` |
| `services/umh/governance/` | `substrate/control_plane/governance.py` |
| `services/umh/observability/` | `substrate/execution/trace.py` |
| `services/umh/control_plane/pipeline.py` | `substrate/execution/spine.py` |
| `understanding/ontology/primitives.py` | `substrate/ontology/primitives.py` |
| `learning/feedback/feedback_loop.py` | `substrate/execution/feedback.py` |

### New subsystems relocated intact

| Current Location | New Location | Lines |
|------------------|-------------|------:|
| `services/umh/organism/` | `substrate/organism/` | 1,554 |
| `services/umh/node_mesh/` | `transports/node_mesh/` | 850 |
| `services/umh/integrations/creatoros/` | `integrations/creatoros/` | ~2,500 |
| `services/umh/integrations/lyfeos/` | `integrations/lyfeos/` | ~2,500 |
| `services/umh/control_plane/cockpit_api.py` | `transports/api/cockpit.py` | 1,034 |
| `understanding/domains/creator.py` | `substrate/ontology/domains/creator.py` | 515 |
| `understanding/domains/life.py` | `substrate/ontology/domains/life.py` | 568 |
| `execution/transport/voice_first.py` | `transports/discord/voice_first.py` | 370 |
| `daemon/` | stays | 1,278 |

---

## Part VII — Test Contracts

### Unit Tests (15)

See prior spec Section 13 — all 15 unit tests carry forward unchanged.

### Integration Tests (5)

See prior spec Section 13 — all 5 integration tests carry forward unchanged.

### Acceptance Tests (10)

See prior spec Section 13 — all 10 acceptance tests carry forward unchanged.

### Additional Convergence Tests

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_ontology_laws_are_callable` | Each law in `substrate/ontology/laws.py` is a callable constraint, not just a string description |
| 2 | `test_reality_model_canonical_promotion_governance` | Promoting from Instance → Canonical requires governance approval |
| 3 | `test_physical_actuation_risk_class` | Any adapter with `physical_actuation` capability is auto-classified CRITICAL |
| 4 | `test_deterministic_plus_ai_both_active` | Spine produces deterministic result AND attempts AI enhancement — uses AI if better |
| 5 | `test_projection_isolation_eos` | EOS projection only calls substrate public API, never imports internals |

---

## Part VIII — Post-MVP Roadmap

After convergence, these subsystems build on the foundation. Each uses the public API.

| Priority | Subsystem | Layer | Unlocks |
|:--------:|-----------|-------|---------|
| 1 | Template System | Composition | Reusable execution patterns |
| 2 | Library System | Composition | Knowledge reuse |
| 3 | Composition Engine | Composition | Multi-step workflows |
| 4 | Completeness Engine | Composition | Validation before execution |
| 5 | Quality Engine | Composition | Output scoring |
| 6 | Law Kernel (full) | Ontology | Domain-specific state transitions |
| 7 | Workstation Modes | Interface | Session continuity + mode management |
| 8 | Reality Model (full) | State | User + system + environment models |
| 9 | Simulation Reality | State | Test actions before execution |
| 10 | Deliberation Council | Composition | Multi-perspective reasoning |
| 11 | Self-Recursion | Learning | Self-improvement loop |
| 12 | Resource Allocation | Control Plane | Compute/attention budgeting |
| 13 | Homeostasis | Learning | Self-regulation |
| 14 | Physical Adapter Framework | Adapter Boundary | IoT, robotics, wearables |
| 15 | Profile Mode System | Interface | Customizable stackable user modes |
