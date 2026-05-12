# Runtime Domain Architecture Plan

> Date: 2026-05-11
> Phase: Runtime Capability Stabilization
> Status: PLAN — awaiting approval before implementation
> Commit scope: runtime-stabilization-plan

---

## 1. Current State

runtime/ contains 289 Python modules:
- 125 top-level (runtime/*.py)
- 164 in substrate/ (runtime/substrate/*.py)
- 164 in transport/ (runtime/transport/*.py — exact mirror of substrate/)

There is no directory-level domain separation. All modules sit flat in
runtime/ or in the substrate/ / transport/ mirrors. The audit classified
every module into one of 11 domains.

### Current directory structure

```
runtime/
├── *.py              (125 modules — all domains mixed)
├── substrate/        (164 modules — mirrors transport/)
├── transport/        (164 modules — mirrors substrate/)
├── runtime/          (2 files: work_state.py, provider_state.py)
├── interfaces/       (dormant contracts)
└── CLAUDE.md
```

---

## 2. Target Domain Architecture

11 domains, each a subdirectory of runtime/. Every module belongs to
exactly one domain. No module crosses domain boundaries in its ownership
— cross-domain dependencies use imports, not co-location.

```
runtime/
├── cognition/        — reasoning, LLM dispatch, context assembly
├── orchestration/    — scheduling, workflow, delegation, task coordination
├── execution/        — action execution, spine, lifecycle tracking
├── transport/        — messaging, events, session management, buses
├── topology/         — agent hierarchy, capability routing, teams
├── world_model/      — knowledge, reality, environment state
├── memory/           — persistence, state tracking, embeddings
├── governance/       — authority, policy, approval gates, health
├── identity/         — AI identity, primitives, templates, tenancy
├── integration/      — external service connectors (GWS, Notion, etc.)
├── platform/         — EOS-specific modules (NOT platform-agnostic)
├── substrate/        — (kept as-is during stabilization, not restructured)
├── runtime/          — (kept as-is: work_state, provider_state)
├── interfaces/       — (dormant, unchanged)
└── CLAUDE.md
```

### Why 11 domains (not fewer, not more)

- Fewer would conflate concerns (e.g., merging cognition + execution
  loses the distinction between reasoning and acting).
- More would create single-module domains with no cohesion benefit.
- 11 matches the natural clusters found by the audit with zero forcing.

---

## 3. Domain Definitions

### 3.1 cognition/ — Reasoning and LLM Dispatch

The thinking layer. Receives context, reasons about it, produces decisions.

| Module | Purpose |
|--------|---------|
| cognitive_loop.py | 8-stage PERCEIVE→STORE cycle |
| context_builder.py | Single-pass context assembly |
| context_compaction.py | Context window management |
| input_intelligence.py | Input elevation to execution prompts |
| signal_hierarchy.py | Signal ranking by reality tier |
| quality_gate.py | Output transformation through 4 values |
| model_router.py | Task-type multi-model routing |
| model_preferences.py | Model selection with business context |
| strategy_engine.py | First-principles strategic reasoning |
| ceo_intelligence.py | Real-time business diagnostics |
| portfolio_advisor.py | Board-level intelligence |
| proactive_engine.py | Unsolicited insight surfacing |
| user_model.py | Founder behavioral learning |
| martell_patterns.py | Leverage Killer detection |

**14 modules.** This is the largest platform-agnostic domain because UMH
is fundamentally a reasoning system.

### 3.2 orchestration/ — Scheduling, Workflow, Delegation

Coordinates what happens when. Does not execute — delegates to execution/.

| Module | Purpose |
|--------|---------|
| orchestrator.py | Strategic intelligence + morning brief dispatch |
| coordination_engine.py | Event-driven task coordination |
| delegation_tracker.py | Delegated task tracking |
| daily_sync.py | Daily sync meeting format |
| eod_closing_loop.py | End-of-day report |
| week_architect.py | Weekly planning |
| goal_selector.py | Goal selection and focus |
| workflow_engine.py | Generic workflow orchestration |

**8 modules.**

### 3.3 execution/ — Action Execution and Lifecycle

Does the work. Every LLM call flows through the execution spine.

| Module | Purpose |
|--------|---------|
| execution_spine.py | Single execution path (authority + LLM + memory) |
| execution_engine.py | Formal task lifecycle tracking |
| execution_loop.py | Closed-loop goal execution with feedback |
| task_executor.py | Agent task execution with approval gates |
| agent_runtime.py | LLM call routing to correct model |
| provider_state.py | Provider backpressure and budget |
| work_state.py | Work state detection and throttling |
| integration_test.py | End-to-end chain validation |

**8 modules.**

### 3.4 transport/ — Messaging, Events, Sessions

Moves data between domains and external surfaces. Does not process content.

| Module | Purpose |
|--------|---------|
| event_bus.py | Reactive producer/consumer coordination |
| event_manager.py | Event routing |
| agent_messages.py | Inter-agent communication via Neon |
| session_state.py | Market reality snapshot cache |
| gateway.py | Single control plane for AI operations |
| channel.py | Two-way execution surfaces |
| discord_utils.py | Discord message posting |

**7 modules.**

Note: The existing transport/ subdirectory (164 files mirroring substrate/)
is NOT this domain. That mirror stays as-is during stabilization.

### 3.5 topology/ — Agent Hierarchy and Routing

Defines who can do what and where messages go.

| Module | Purpose |
|--------|---------|
| agent_hierarchy.py | Founder→EA→CEO→Dept authority structure |
| agent_teams.py | Domain team registry |
| ceo_agent.py | Per-company CEO agent |
| intent_router.py | Keyword routing to correct domain |
| person_recognition.py | Known person identification |

**5 modules.**

### 3.6 world_model/ — Knowledge, Reality, Environment

The system's understanding of the world outside itself.

| Module | Purpose |
|--------|---------|
| world_model.py | Two-layer canonical/instance model |
| world_pulse.py | Market + creator intelligence monitoring |
| reality_engine.py | Market signal scanning and classification |
| reality_context.py | Ambient state snapshot injection |
| knowledge_graph.py | Entity relationship layer |
| knowledge_integrator.py | Permanent knowledge accumulation |
| knowledge_domains.py | Base equilibrium awareness |
| knowledge_layers.py | Behavioral/strategic knowledge injection |
| venture_knowledge.py | Venture-specific knowledge base |
| research_engine.py | Autonomous knowledge gap detection |
| evolution_engine.py | Continuous self-improvement lifecycle |
| system_context.py | Interface-aware intelligence |

**12 modules.**

### 3.7 memory/ — Persistence, State, Embeddings

Stores and retrieves. Does not reason about content.

| Module | Purpose |
|--------|---------|
| memory.py | AgentMemory + ConversationMemory (Neon) |
| db.py | Neon PostgreSQL connection layer |
| decision_log.py | Permanent decision records |
| feedback_loop.py | Outcome tracking and signal closure |
| pattern_engine.py | Cross-session behavioral pattern detection |
| context.py | EOSContext dataclass + env loader |
| skill_registry.py | Skill registry v1 |
| skill_registry_v2.py | Skill objects with trust scoring |
| skill_improvement.py | RLHF-driven skill rewriting |
| claude_skill_registry.py | Claude Code skill tracking |
| embedding_engine.py | Three-tier hybrid embeddings |
| harness_registry.py | Tool/model/agent inventory |

**12 modules.**

### 3.8 governance/ — Authority, Policy, Health

Enforces rules. Says yes or no. Does not execute.

| Module | Purpose |
|--------|---------|
| authority_engine.py | Risk classification + autonomy levels |
| principle_engine.py | Quality standard injection |
| output_validator.py | Constraint validation before shipping |
| confidentiality.py | Sensitive negotiation handling |
| ceo_operational_standards.py | CEO agent ruleset |
| portfolio_advisor_standards.py | Portfolio advisor ruleset |
| ea_operational_standards.py | EA operational ruleset |
| system_health.py | Provider + chain health monitoring |
| status.py | Daily health dashboard |
| error_handler.py | Self-healing error handling |

**10 modules.**

### 3.9 identity/ — AI Identity, Primitives, Templates, Tenancy

Defines what the system IS, not what it DOES.

| Module | Purpose |
|--------|---------|
| ai_identity.py | Foundational AI identity principles |
| primitives.py | Stage-aware business rules (13 primitives) |
| primitive_registry.py | 10 ontological building blocks |
| template_library.py | Pre-composed primitive assemblies |
| template_registry.py | Formal template schema |
| os_registry.py | EOS/CreatorOS/LyfeOS registry |
| os_trinity.py | Cross-product data sharing |
| trinity.py | Cross-OS intelligence routing |
| business_instance.py | Venture-stage context |
| company_instantiator.py | Company template instantiation |
| onboarding_engine.py | New founder onboarding |
| onboarding_backfill.py | Integration backfill on first connect |
| setup_wizard.py | Onboarding flow + soul doc generation |
| tenant.py | Multi-tenant isolation |

**14 modules.**

### 3.10 integration/ — External Service Connectors

Adapters to the outside world. Stateless where possible.

| Module | Purpose |
|--------|---------|
| gws_connector.py | Google Workspace via gws CLI |
| gws_scanner.py | Google Docs business context extraction |
| browser_agent.py | Playwright-based web operator |
| notion_sync.py | Neon → Notion push |
| notion_publisher.py | Notion publishing |
| scrapling_connector.py | Stealth HTTP fetching |
| higgsfield_client.py | Higgsfield image generation |
| notebooklm_sync.py | NotebookLM bidirectional sync |
| cc_sdk.py | Claude Code Agent SDK wrapper |
| voice_engine.py | Discord voice (STT + TTS) |
| voice_interface.py | Voice conversation layer |

**11 modules.**

### 3.11 platform/ — EOS-Specific Application Logic

Modules that implement EntrepreneurOS-specific features. These are
projections of the runtime — they USE the runtime but are not part of
the platform-agnostic substrate.

| Module | Purpose |
|--------|---------|
| personal_admin.py | Important dates, gifts |
| email_gps.py | Dan Martell 7-folder email |
| email_reviewer.py | Email classification review |
| meetings.py | Meeting lifecycle management |
| founder_capture.py | Task/idea detection from Discord |
| founder_rate.py | Founder time valuation |
| document_filer.py | Drive document filing |
| doc_creator.py | Briefing/board/investor docs |
| media_processor.py | Multimodal file handler |
| expense_tracker.py | Receipt processing |
| subscription_tracker.py | Subscription registry |
| okr_tracker.py | OKR tracking per venture |
| competitive_intel.py | Competitor signal tracking |
| stakeholder_map.py | Stakeholder tracking |
| stage_manager.py | Venture stage advancement |
| ideal_week.py | Ideal week template |
| travel_manager.py | Trip logistics |
| task_yield_matrix.py | Dan Martell task audit |
| human_intelligence.py | Behavioral profiling |

**19 modules.**

---

## 4. Execution Spine Design

The execution spine is the single path through which every action flows.
It already exists as `runtime/execution_spine.py`. The stabilization plan
does NOT rebuild it — it clarifies and documents the canonical flow.

### Current spine (verified from code)

```
User message
    │
    ▼
gateway.py              ← classify, validate, route
    │
    ▼
cognitive_loop.py       ← 8-stage reasoning cycle
    │
    ├── context_builder  ← assemble unified context
    ├── authority_engine  ← risk classification
    ├── model_router     ← select LLM provider
    │
    ▼
execution_spine.py      ← execute (LLM call + memory write)
    │
    ├── agent_runtime    ← actual LLM dispatch
    ├── memory           ← persist conversation + agent memory
    ├── event_bus        ← notify subscribers
    │
    ▼
transport (response)    ← channel.py / discord_utils.py
```

### Spine invariants (must hold after stabilization)

1. **Single entry**: All user-facing operations enter through gateway.py
2. **Authority before execution**: No LLM call without risk classification
3. **Memory after execution**: Every response persists to Neon
4. **Provider isolation**: model_router abstracts all LLM providers
5. **Event notification**: execution_spine fires events after completion

### What stays unchanged

- ExecutionSpine.run() signature and guarantees
- CognitiveLoop 8-stage cycle
- model_router.call_with_fallback() as the single LLM entry point
- gateway.py as the single control plane

### What this plan adds (implementation phase)

- Domain import paths (e.g., `from runtime.cognition.cognitive_loop import ...`)
- __init__.py files per domain with public API exports
- Backward-compatible re-exports from current flat locations

---

## 5. World Model Primitive Design

Two distinct primitive systems exist and must be preserved:

### 5A. Business Primitives (runtime/primitives.py)

13 stage-aware business rules in PRIMITIVE_LIBRARY. These are
domain-specific (business/entrepreneurship) and inject into
CognitiveLoop step 1f.

**These stay in identity/ — they define what EOS believes.**

### 5B. Ontological Primitives (runtime/primitive_registry.py)

10 fundamental building blocks for the Meta Harness. These are
domain-agnostic and compose all templates, world models, and behaviors.

Current 10 primitives:
Entity, State, Constraint, Capability, Signal, Action,
Outcome, Relationship, Environment, Resource

**Proposed additions (2 more to complete the ontology):**

| Primitive | Why |
|-----------|-----|
| **Goal** | Every system needs purpose representation. Currently implicit in goal_selector.py and OKR tracking but not formalized as an ontological primitive. Goals compose with Constraints (feasibility), Capabilities (achievability), and Actions (execution path). |
| **Policy** | Governance rules that constrain primitive composition. Currently implicit in authority_engine.py and principle_engine.py. Policies compose with Constraints and determine which Actions are permissible for which Entities. |

**These move to world_model/ — they define what the system models.**

The separation is load-bearing: business primitives change per stage/venture,
ontological primitives are universal and stable.

---

## 6. Memory Architecture

### Current state

Memory is scattered across 12 modules with overlapping concerns:

- memory.py — AgentMemory + ConversationMemory (Neon)
- db.py — raw connection layer
- skill_registry.py / v2 — skill persistence
- decision_log.py — decision records
- pattern_engine.py — cross-session patterns
- feedback_loop.py — outcome tracking
- embedding_engine.py — vector embeddings
- context.py — identity/env loader (misplaced — should be identity/)

### Recommended architecture

```
memory/
├── core.py          ← AgentMemory + ConversationMemory (from memory.py)
├── db.py            ← Neon connection layer (unchanged)
├── decisions.py     ← Decision log
├── patterns.py      ← Cross-session pattern detection
├── feedback.py      ← Outcome tracking
├── embeddings.py    ← Three-tier embedding engine
├── skills.py        ← Unified skill registry (merge v1 + v2)
├── claude_skills.py ← Claude Code skill tracking
└── harness.py       ← Tool/model/agent inventory
```

### Key change: context.py → identity/

context.py contains EOSContext (org_id, user_id, venture_id) and
load_context_from_env(). This is identity configuration, not memory.
It should move to identity/context.py.

### Migration path

1. Create domain __init__.py with re-exports
2. Move files into domain directories
3. Add backward-compatible imports at old locations
4. Verify import chain through test baseline

---

## 7. Projection Isolation Rules

### The boundary

Platform-agnostic runtime (10 domains) vs. EOS-specific projections
(platform/ domain).

### Rules

1. **platform/ imports from runtime domains, never the reverse.**
   A module in cognition/ must never import from platform/.

2. **platform/ modules are EOS application logic.**
   They implement EntrepreneurOS features using runtime primitives.

3. **New projections (CreatorOS, LyfeOS) get their own platform/ subdirectory.**
   ```
   runtime/platform/
   ├── eos/       ← current 19 EOS modules
   ├── creator/   ← future CreatorOS projection
   └── lyfe/      ← future LyfeOS projection
   ```

4. **os_registry.py, os_trinity.py, trinity.py stay in identity/.**
   They define the projection system itself, not any specific projection.

5. **Shared modules stay in their domain.**
   If a module is used by multiple projections, it belongs in the
   platform-agnostic domain, not in any projection.

### Import direction (enforced by convention, verifiable by lint)

```
platform/eos/*.py  →  runtime/{cognition,execution,...}/*.py  ✓
runtime/cognition/*.py  →  platform/eos/*.py                  ✗ VIOLATION
```

---

## 8. Immediate Build Sequence

After approval, implementation proceeds in this order:

### Phase 1: Domain directories (LOW risk)

Create 11 domain subdirectories with __init__.py files.
No module moves — just directory creation and empty init files.

Validation: `python3 -c "import runtime"` still works.

### Phase 2: Module classification commit (LOW risk)

Add the module map JSON (data/system/runtime_domain_module_map.json)
as the single source of truth for which module belongs where.

Validation: Every runtime/*.py file appears exactly once in the map.

### Phase 3: Core domain moves (MEDIUM risk)

Move modules into domain directories, starting with the smallest
domains (topology: 5 modules) and ending with the largest
(cognition: 14, platform: 19).

Each domain move is one commit:
1. Move files
2. Add re-export shims at old locations
3. Run test baseline
4. Verify discord bot imports

Order: topology → transport → governance → orchestration →
execution → world_model → memory → identity → cognition →
integration → platform

Validation: Test baseline holds (8684/2691/495).

### Phase 4: Re-export cleanup (LOW risk)

After all moves, the flat runtime/*.py shims can be retired
(same monitoring pattern as eos_ai/ shims).

Validation: `grep -r "from runtime\." --include="*.py" | grep -v domain_path`

### Phase 5: Projection isolation (LOW risk)

Split platform/ into platform/eos/. Add import direction linter.

Validation: No reverse imports found.

---

## 9. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Import breakage during moves | MEDIUM | HIGH | Re-export shims at old locations; test baseline after every move |
| Docker container env miss | LOW | HIGH | Restart os-discord after each domain move; verify with docker exec |
| substrate/ mirror divergence | LOW | MEDIUM | Do not touch substrate/ or transport/ mirrors during stabilization |
| Cron job breakage | LOW | HIGH | Cron uses runtime.orchestrator — add re-export shim |
| test suite false failures | MEDIUM | LOW | Use --continue-on-collection-errors; compare against known baseline |
| Circular imports from domain splits | MEDIUM | MEDIUM | Audit import graph before each move; use lazy imports where needed |

### Hard constraints (from user directive)

- Do NOT rename /opt/OS
- Do NOT delete eos_ai/
- Do NOT remove shims
- Do NOT start another broad migration
- Do NOT blur core/runtime/platform boundaries

### Validation plan

After each phase:
1. `python3 -m pytest tests/ --continue-on-collection-errors -q` → baseline match
2. `python3 -c "from runtime.db import get_conn; print('db ok')"` → core import
3. `docker exec os-discord python3 -c "from runtime.gateway import EOSGateway"` → container
4. `crontab -l | grep runtime` → cron references intact

---

## 10. What This Plan Does NOT Do

1. **Does not restructure substrate/ or transport/.** The 164-file mirrors
   stay as-is. They are a separate concern with their own cleanup timeline.

2. **Does not rename modules.** Files keep their current names. Only their
   directory location changes.

3. **Does not change any public API.** `from runtime.cognitive_loop import CognitiveLoop`
   continues to work via re-export shims.

4. **Does not touch eos_ai/ shims.** The dead shim layer is on its own
   14-day monitoring timeline.

5. **Does not move services/ or core/ modules.** Those directories are
   already correctly placed.

6. **Does not create new abstractions.** No new base classes, no new
   protocols, no new frameworks. Just directory organization.

---

## Appendix A: Module Count by Domain

| Domain | Top-level | Substrate | Total |
|--------|-----------|-----------|-------|
| cognition | 14 | 13 | 27 |
| orchestration | 8 | 20 | 28 |
| execution | 8 | 17 | 25 |
| transport | 7 | 25 | 32 |
| topology | 5 | 15 | 20 |
| world_model | 12 | 7 | 19 |
| memory | 12 | 9 | 21 |
| governance | 10 | 11 | 21 |
| identity | 14 | 5 | 19 |
| integration | 11 | 22 | 33 |
| platform | 19 | 8 | 27 |
| **Total** | **120** | **152** | **272** |

Note: 5 top-level and 12 substrate modules are utility/system files
not classified into domains (total 289 - 272 = 17 uncategorized infra).

## Appendix B: substrate/ Domain Breakdown

The substrate/ audit classified 164 modules into the same 11 domains.
Key findings:

- **orchestration** is the largest substrate domain (20 modules) —
  ritual management, workflow delegation, task systems
- **transport** has 25 modules — voice/audio pipelines, session bridges,
  message buses
- **integration** has 22 modules — Google Docs/Drive/Meet, Chrome, MCP,
  computer use backends
- **execution** has 17 modules — work orders, execution contracts,
  browser agents, shell executors
- **topology** has 15 modules — station management, node routing,
  capability discovery
