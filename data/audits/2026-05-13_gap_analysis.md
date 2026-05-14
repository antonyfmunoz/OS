# GAP-ANALYSIS — Audit Report

> Date: 2026-05-13
> Trigger: Pre-migration architectural gap measurement
> Mode: READ-ONLY. Static inspection + grep + git log.
> Scope: ~30 anchor subsystems reachable from production

---

## Executive Summary

| Category | Count |
|----------|-------|
| Anchor subsystems inventoried | 30 files across 7 subsystem groups |
| §24 layer mappings | 30 anchors mapped; 5 UNAMBIGUOUS, 18 REASONABLE, 7 NO-HOME |
| Law 5.4 violations (Typed Contracts) | SYSTEMIC — 0/30 production files use umh.protocols |
| Law 5.5 violations (Memory Discipline) | 46 files with direct DB writes outside canonical path |
| Law 5.9 violations (External Boundary) | 3 adapters use old execute() contract; 0 use canonical |
| §34-§37 reclassifications needed | 5 items |
| Architectural gaps (no §24 home) | 3 categories (~52K LOC) |
| Pre-migration refactors required | 0 blocking; 3 recommended during migration |

**Key finding:** The canonical typed contracts (`umh/protocols/`) exist as a
complete parallel type system (86 types across 10 files) but have **zero
production consumers**. All 30 anchor files use raw `@dataclass` or untyped
`dict`. This is the single largest gap between spec and implementation —
the contracts were written but never adopted.

---

## Phase 1: Anchor Subsystem Inventory

### Spine (§29 Do-Not-Touch Core)

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| runtime/cognitive_loop.py | 1,263 | 8-stage reasoning loop (perceive→decide→execute→learn) | 19 | fe7af75f 2026-05-10 |
| runtime/model_router.py | 1,194 | Multi-provider LLM routing (cc_sdk→Gemini→Groq→Ollama) | 57 | fe7af75f 2026-05-10 |
| runtime/agent_runtime.py | 527 | Agent dispatch with cost tracking + multi-model fallback | 38 | fe7af75f 2026-05-10 |
| runtime/memory.py | 1,018 | AgentMemory + ConversationMemory (Neon-backed) | 34 | fe7af75f 2026-05-10 |
| runtime/db.py | 123 | Neon connection pool, ORG_ID | 97 | fe7af75f 2026-05-10 |
| runtime/execution_spine.py | 170 | Input→Authority→LLM→Result governed path | 1 | fe7af75f 2026-05-10 |
| runtime/authority_engine.py | 250 | 4 risk classes, autonomy levels, governance gates | 5 | fe7af75f 2026-05-10 |
| runtime/primitives.py | 931 | 13 primitives + validity matrix + from_dict | 3 | fe7af75f 2026-05-10 |
| runtime/cc_sdk.py | 464 | Claude CLI subprocess bridge (OAuth, error-leak, timeout) | 2 | fcf78041 2026-05-13 |
| eos_ai/gateway.py | 4 | **SHIM** — redirects to runtime/gateway.py | 0 | 83891d12 2026-05-10 |

### Ingestion (recent canonical work)

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| runtime/ingestion/orchestrator.py | 1,151 | Generic 7-stage pipeline: perceive→persist→query_back | 3 | c0549188 2026-05-12 |
| runtime/ingestion/local_file_source.py | 58 | File→RawContent with SHA256 + authority tier | 2 | c0549188 2026-05-12 |
| runtime/ingestion/gws_source.py | 88 | Google Workspace doc→RawContent | 1 | c0549188 2026-05-12 |
| runtime/ingestion/authority_tier.py | 49 | T1–T9 tier constants + get_authority_tier() | 3 | c0549188 2026-05-12 |

### Domain Bridge

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| runtime/domain_bridge/contract.py | 74 | DomainBridge Protocol + DomainProjection dataclass | 2 | c0549188 2026-05-12 |
| runtime/domain_bridge/registry.py | 31 | get_all_bridges() discovery | 1 | 972e1e8e 2026-05-12 |
| runtime/domain_bridge/business.py | 245 | BusinessBridge keyword mapping → projections | 1 | c0549188 2026-05-12 |

### Core substrate

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| core/ontology/primitive_decomposition_v1.py | 127 | PrimitiveObservation + PrimitiveType enum | 3 | c0549188 2026-05-12 |
| core/environment_bridge/work_packet.py | 206 | WorkPacket dataclass + approval gates | 2 | f065550f 2026-05-06 |
| core/runtime/adapter_registry_contracts.py | 115 | AdapterRegistryEntry + WorkerType contracts | 1 | 80b85866 2026-05-07 |
| core/runtime/worker_runtime_contracts.py | 140 | WorkerRuntimeContract + execution contracts | 1 | 80b85866 2026-05-07 |
| core/action_system/control_plane.py | ~200 | run_action() with risk gating + idempotency | 3 (scripts) | 8a0db076 2026-05-10 |

### Services

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| services/discord_bot.py | 5,212 | Primary interface — commands, handlers, routing | 0 (entry) | b6b0fb4a 2026-05-11 |
| services/handlers/intent_handler.py | ~300 | Intent classification dispatch | 1 | b6b0fb4a 2026-05-11 |

### Operator Tooling (salience pipeline + cron)

| File | LOC | Purpose | Callers | Last Commit |
|------|-----|---------|---------|-------------|
| scripts/salience.py | 600 | Heuristic salience scoring (per-session + cross-session) | 2 | 1b780600 2026-05-13 |
| scripts/nightly_consolidation.py | 325 | Orchestrate summarize→promote pipeline | 1 (cron) | 8a0db076 2026-05-10 |
| scripts/summarize_conversations.py | 508 | Conversation→summary with LLM extraction | 1 | b6b0fb4a 2026-05-11 |
| scripts/promote_to_wiki.py | 438 | Summary→wiki page promotion with salience gating | 1 | 8a0db076 2026-05-10 |
| scripts/memory_neon.py | 565 | Neon persistence for memory pipeline | 2 | b6b0fb4a 2026-05-11 |

### Protocol Contracts (umh/protocols/)

| File | LOC | Purpose | Prod Callers | Last Commit |
|------|-----|---------|-------------|-------------|
| umh/protocols/common.py | ~350 | 18 enums + 13 ref types + 9 sub-models | **0** | f88f4e39 2026-05-13 |
| umh/protocols/adapters.py | ~170 | Adapter Protocol (8 methods) + AccessPath | **0** | 2e45278a 2026-05-13 |
| umh/protocols/ (8 more files) | ~1,200 | All 10 layers typed | **0** | f88f4e39 2026-05-13 |

---

## Phase 2: §24 Layer Mapping

### Legend

- **UNAMBIGUOUS** — one clear §24 home
- **REASONABLE** — fits with minor stretch
- **NO-HOME** — no §24 layer exists for this concern

### Mapping Table

| Current Path | §24 Target | Fit |
|-------------|-----------|-----|
| runtime/cognitive_loop.py | control_plane/runtime/ | UNAMBIGUOUS |
| runtime/model_router.py | execution/runtime/ or adapters/model_adapters/ | REASONABLE (dual concern: routing logic + model boundary) |
| runtime/agent_runtime.py | execution/runtime/ | UNAMBIGUOUS |
| runtime/memory.py | state/memory/ | UNAMBIGUOUS |
| runtime/db.py | state/storage/ | UNAMBIGUOUS |
| runtime/execution_spine.py | execution/runtime/ | UNAMBIGUOUS |
| runtime/authority_engine.py | governance/policy/ | REASONABLE |
| runtime/primitives.py | understanding/ontology/ | REASONABLE |
| runtime/cc_sdk.py | adapters/model_adapters/ or adapters/cli_adapters/ | REASONABLE |
| runtime/ingestion/orchestrator.py | understanding/perception/ | REASONABLE |
| runtime/ingestion/local_file_source.py | adapters/data_source_adapters/ | REASONABLE |
| runtime/ingestion/gws_source.py | adapters/data_source_adapters/ | REASONABLE |
| runtime/ingestion/authority_tier.py | governance/policy/ | REASONABLE |
| runtime/domain_bridge/contract.py | understanding/domains/ | REASONABLE |
| runtime/domain_bridge/business.py | understanding/domains/ | REASONABLE |
| core/ontology/primitive_decomposition_v1.py | understanding/ontology/ | REASONABLE |
| core/environment_bridge/work_packet.py | execution/work_packets/ | REASONABLE |
| core/runtime/adapter_registry_contracts.py | composition/registries/ | REASONABLE |
| core/runtime/worker_runtime_contracts.py | execution/workers/ | REASONABLE |
| core/action_system/control_plane.py | control_plane/runtime/ | REASONABLE |
| services/discord_bot.py | interface/cli/ or interface/presence/ | REASONABLE |
| services/handlers/*.py | interface/ (dispatch layer) | REASONABLE |
| umh/protocols/*.py | control_plane/protocols/ | REASONABLE |
| **scripts/salience.py** | **??? — no §24 layer for batch/scheduled work** | **NO-HOME** |
| **scripts/nightly_consolidation.py** | **??? — no §24 layer** | **NO-HOME** |
| **scripts/summarize_conversations.py** | **??? — learning/feedback/? or state/memory/?** | **NO-HOME** |
| **scripts/promote_to_wiki.py** | **??? — learning/update_proposals/?** | **NO-HOME** |
| **scripts/memory_neon.py** | **state/storage/ (could fit)** | **REASONABLE** |
| **eos_ai/*.py (459 files)** | **DEAD — all shims, pending removal** | **NO-HOME (legacy)** |
| **runtime/substrate/ (164 files)** | **DEAD — all re-exports from transport/** | **NO-HOME (legacy)** |

---

## Phase 3: Law Violation Audit

### Law 5.4 — Typed Contracts Only

**Status: SYSTEMIC VIOLATION**

The canonical typed contracts exist in `umh/protocols/` (86 types,
~1,720 LOC, Pydantic v2). **Zero production files import them.**
All 30 anchor files use either:

- Raw `@dataclass` (spine, ingestion, domain bridge, work_packet)
- Untyped `dict` for cross-module payloads (cognitive_loop, model_router)
- No type contracts at all (some scripts/)

| Component | Type System Used | umh/protocols Used? |
|-----------|-----------------|-------------------|
| Spine (5 files) | @dataclass + raw dict | NO |
| Ingestion (4 files) | @dataclass | NO |
| Domain bridge (3 files) | @dataclass + Protocol | NO |
| Core contracts (3 files) | @dataclass | NO |
| Services (2 files) | Untyped | NO |
| Operator tooling (5 files) | @dataclass + raw dict | NO |
| umh/protocols/ (10 files) | Pydantic v2 | N/A (is the spec) |

**Specific violations:**

| File | Line | Issue |
|------|------|-------|
| runtime/cognitive_loop.py | 74 | `authority: dict \| None` — governance result is untyped |
| runtime/cognitive_loop.py | 765, 801 | Two functions returning `-> dict` (should be typed result) |
| runtime/cognitive_loop.py | 974 | `req: dict` — request payload untyped |
| runtime/model_router.py | 554 | `kwargs: dict` — LLM call params untyped |
| runtime/model_router.py | 635 | `payload: dict` — Groq request untyped |
| runtime/agent_runtime.py | 138 | `authority: dict \| None` — governance result untyped |
| ControlPlaneEvent (§8 spec) | — | Spec has `payload: dict` — the SPEC ITSELF violates 5.4 |

**Refactor scope:** CROSS-CUTTING. Adopting umh/protocols in production
would touch every anchor file. This is not a pre-migration requirement
but should be a migration-phase goal: as files move to §24 locations,
they adopt their corresponding protocol types.

### Law 5.5 — Memory Discipline

**Status: WIDESPREAD VIOLATION**

**46 files** write directly to Neon `events` table via raw SQL
`INSERT INTO events`. The canonical memory write path
(`runtime/memory.py` → `AgentMemory.log_event()`) is used by only
27 files.

Many modules bypass `memory.py` entirely and call `db.get_conn()`
+ raw INSERT directly. This means:

- No uniform source/timestamp/confidence metadata
- No promotion status tracking
- No governed memory candidacy
- Different payload schemas per module

**Direct-write sites in services/ (highest risk):**

| File | Writes |
|------|--------|
| services/discord_bot.py | 1 direct INSERT |
| services/calendly_webhook.py | direct INSERT |
| services/handlers/intent_handler.py | direct INSERT |
| services/handlers/cc_command_handler.py | direct INSERT |

**Direct-write sites in runtime/ (sampling — 42 files total):**

| File | Nature |
|------|--------|
| runtime/accountability.py | INSERT INTO events |
| runtime/workflow_engine.py | 2× INSERT INTO events |
| runtime/founder_rate.py | 3× INSERT INTO events |
| runtime/email_gps.py | 2× INSERT INTO events |
| runtime/expense_tracker.py | 2× INSERT INTO events |
| runtime/travel_manager.py | 2× INSERT INTO events |
| runtime/event_manager.py | 3× INSERT INTO events |
| runtime/feedback_loop.py | INSERT INTO events |
| runtime/quality_gate.py | INSERT INTO events |
| runtime/self_awareness.py | INSERT INTO events |
| ... | (32 more files) |

**§36 claim: "2 of 13 message paths write to memory":**
The discord_bot.py has 1 direct INSERT and imports memory.py
for conversation logging. The "2 of 13" claim appears roughly
accurate for the Discord bot entry point, but the problem is far
wider — 46 files across the whole runtime bypass the canonical path.

**Refactor scope:** MEDIUM. A `memory.log_event()` wrapper exists.
Most direct INSERTs could be mechanically replaced. However, each
site has different payload shapes — unifying these requires either
making `log_event()` more flexible or defining per-domain event
schemas.

### Law 5.9 — External Boundary Law

**Status: CONTRACT MISMATCH**

The canonical adapter protocol (`umh/protocols/adapters.py`)
defines 8 methods:

```
connect() → validate_connection() → describe_capabilities()
→ translate_request() → validate_operation()
→ normalize_result() → observe_state() → disconnect()
```

The production adapter protocol (`runtime/transport/execution_adapter.py`)
defines a different contract:

```
adapter_id → node_id → capabilities → execute() → health()
```

| Adapter | Contract | Location |
|---------|----------|----------|
| umh/protocols/Adapter | translate_request/normalize_result/observe_state | Spec only |
| ExecutionAdapter (Protocol) | execute() | runtime/transport/ |
| LocalRuntimeAdapter | execute() | runtime/transport/ |
| WorkstationAdapter | execute() | runtime/transport/ |
| governed_shell_adapter_v1 | execute() | core/workstation/ |
| governed_browser_adapter_v1 | execute() | core/workstation/ |

**Production adapters: 5** (all use old `execute()` contract).
**Canonical adapters: 0** (no production code implements the new contract).

**Refactor scope:** CLASS-LEVEL per adapter. Each adapter needs its
`execute()` split into `translate_request()` + external call +
`normalize_result()`. The `observe_state()` method is new capability.
5 files to modify, no cross-cutting dependency changes.

---

## Phase 4: §34-§37 Per-Item Verification

### §34 — Proven

| Item | Verified Status | Location | Gap |
|------|----------------|----------|-----|
| Relay transport (Discord bridge) | STILL_PROVEN | services/discord_bot.py + runtime/substrate/session_discord_bridge.py | None |
| Authority gates | STILL_PROVEN | runtime/authority_engine.py (250 LOC, 4 risk classes) | None |
| WorkPacket validation | STILL_PROVEN | core/environment_bridge/work_packet.py (206 LOC) | None |
| VPS orchestration | STILL_PROVEN | /opt/OS on srv1500858, running | None |
| Foreground CU ingestion (API slice) | STILL_PROVEN | runtime/ingestion/gws_source.py + orchestrator.py | None |
| Phase 75B execution spine | STILL_PROVEN | runtime/execution_spine.py (170 LOC) | None |
| Salience pipeline | **VERIFIED (Appendix C)** | scripts/ (2,100 LOC) | Episodic→conversation logging |
| Tailscale mesh | STILL_PROVEN (infra) | Not code — network config | None |
| ttyd/Termius/code-server | STILL_PROVEN (infra) | Not code — access paths | None |
| Persistent claude tmux | STILL_PROVEN (infra) | Not code — tmux session | None |
| OAuth token + keepalive | STILL_PROVEN | .env.sessions + cron | None |
| Remotion | STILL_PROVEN | content/remotion/ | Separate repo |
| Clerk auth flow | STILL_PROVEN | saas/ (TypeScript) | feature/company-system branch |
| Core user flow | STILL_PROVEN | saas/ (TypeScript) | feature/company-system branch |
| saas-dev-skill | STILL_PROVEN | Standalone repo | None |

### §35 — Partially Proven

| Item | Verified Status | Location | Gap |
|------|----------------|----------|-----|
| Workstation automation | STILL_PARTIAL | core/workstation/ (41 files, 26K LOC) — contracts exist, no runtime integration | Large |
| Google session routing | STILL_PARTIAL | runtime/ingestion/gws_source.py (API path) | CU path still provisional |
| **UserPromptSubmit hook** | **RECLASSIFY → PROVEN** | scripts/user_prompt_capture.py + .claude/settings.json hook configured | Capturing to vault/memory/conversations/ — 453 files |
| Semantic retrieval tuning | STILL_PARTIAL | runtime/embedding_engine.py + knowledge_integrator.py | Basic recall, naive ranking |
| Subprocess lifecycle mgmt | STILL_PARTIAL | 4GB swapfile works, manual ceiling | None |

### §36 — Unverified

| Item | Verified Status | Location | Gap |
|------|----------------|----------|-----|
| Foreground extraction (W-GDOCS-CU-001) | STILL_UNVERIFIED | Blocked on local GUI gaps | N/A |
| Full W0-001 triple-test | STILL_UNVERIFIED | Only API path proven | CU + parity missing |
| End-to-end RLHF loop | STILL_UNVERIFIED | runtime/feedback_loop.py exists (called from 2 paths); services/dm_monitor.py has _log_rlhf_outcome() | Memory writes limited |

### §37 — Not Built

| Item | Verified Status | Location | Gap |
|------|----------------|----------|-----|
| **Full ingestion system** | **RECLASSIFY → PROVEN** | runtime/ingestion/ (1,346 LOC) + domain_bridge/ (350 LOC) — GenericIngestionOrchestrator + 2 sources + domain bridge | Production pipeline with proofs |
| Unified memory graph | STILL_NOT_BUILT | runtime/memory.py is flat, no graph traversal | Confirmed |
| Autonomous reconciliation | STILL_NOT_BUILT | No code | Confirmed |
| Workstation UI runtime | STILL_NOT_BUILT | saas/ has stub, not Command Center | Confirmed |
| Composition Engine v1 | PARTIAL (2 files exist) | core/ has classes but not wired | Confirmed |
| Completeness Engine v1 | STILL_NOT_BUILT | 0 files | Confirmed |
| Quality Engine v1 | PARTIAL (1 file) | runtime/quality_gate.py exists | Not wired as spec envisions |
| World Model Core | PARTIAL | runtime/world_model.py (256 LOC) — seed data, no real entity/relationship/fact tables | Not spec-grade |
| **Multi-Model Routing** | **RECLASSIFY → PROVEN** | runtime/model_router.py (1,194 LOC) — cc_sdk/Anthropic/Gemini/Groq/Ollama with fallback chains | Running in production |
| Computer Use access path | STILL_NOT_BUILT | CU blocked on local GUI | Confirmed |
| Mobile (Appium) control | STILL_NOT_BUILT | No code | Confirmed |
| Desktop (PyAutoGUI) control | STILL_NOT_BUILT | No code beyond Playwright | Confirmed |
| Distribution/Installer | STILL_NOT_BUILT | No code | Confirmed |
| Onboarding wizard | STILL_NOT_BUILT | No code | Confirmed |
| Security hardening | STILL_NOT_BUILT | No code | Confirmed |
| Proprietary intelligence runtime | STILL_NOT_BUILT | No code | Confirmed |

### Reclassifications Needed (5 items)

1. **§35 → §34:** UserPromptSubmit hook capture — IS in production, 453 conversation files captured
2. **§37 → §34:** Full ingestion system — built and proven (GenericIngestionOrchestrator + 2 sources + domain bridge + 63 memory entries)
3. **§37 → §34:** Multi-Model Routing — built and running (cc_sdk→Gemini→Groq→Ollama, 1,194 LOC)
4. **§37 → §35:** Composition Engine v1 — partial code exists in core/
5. **§37 → §35:** World Model Core — runtime/world_model.py exists (256 LOC), seed data only

---

## Phase 5: Architectural Gaps

### Gap 1: No §24 Layer for Operator Tooling / Batch Work

**Scale:** 183 Python files, 52,036 LOC in `scripts/`

**What lives here:**
- Salience pipeline (5 files, 2,436 LOC)
- Nightly consolidation (cron orchestration)
- Morning prep (cron)
- Weekly review (cron)
- Session bootstrap
- Graph builder, query engine
- Wiki hooks (start/stop)
- User prompt capture
- Emit_signal (cron→orchestrator bridge)
- Migration scripts (one-off)

**Proposed resolution:** Add `operations/` to §24:
```
operations/
  scheduled/      # cron jobs, nightly_consolidation, morning_prep
  memory/         # salience scoring, summarization, promotion
  migration/      # one-off migration scripts
  diagnostics/    # audit scripts, health checks
```

Alternatively, distribute: salience → `learning/`, scheduled → `control_plane/`, migration → `tests/`.
The dedicated `operations/` layer is cleaner because these are neither request-path nor test concerns.

### Gap 2: No §24 Layer for Shim/Compatibility Layers

**Scale:** 459 files in `eos_ai/` (125 generated shims) + 164 files in `runtime/substrate/` (all re-exports)

These are migration artifacts. `eos_ai/` redirects old imports to `runtime/`. `runtime/substrate/` re-exports from `runtime/transport/`.

**Proposed resolution:** Remove during migration. These exist only for backwards compatibility. Once callers are updated to use canonical import paths, these directories can be deleted. No §24 layer needed — they should cease to exist.

### Gap 3: Two Parallel Type Systems

**Scale:** ~1,720 LOC in `umh/protocols/` (Pydantic) vs. ~3,000 LOC of `@dataclass` definitions across runtime/

The canonical contracts (umh/protocols/) and the production type definitions (scattered @dataclass in runtime/) define overlapping but incompatible types for the same concepts.

**Examples:**
- umh/protocols/understanding.py `Signal` (Pydantic) vs runtime/ingestion/orchestrator.py `SignalResult` (@dataclass)
- umh/protocols/execution.py `WorkPacket` (Pydantic) vs core/environment_bridge/work_packet.py `WorkPacket` (@dataclass)
- umh/protocols/adapters.py `Adapter` (Protocol, 8 methods) vs runtime/transport/execution_adapter.py `ExecutionAdapter` (Protocol, 3 methods)

**Proposed resolution:** During migration, as files move to §24 locations, adopt the umh/protocols type for that layer. Production @dataclass types become the "v0" that gets replaced. This is not a pre-migration requirement but should be a migration-phase goal with per-layer adoption:

1. Understanding layer types first (Signal, Interpretation, Decomposition) — ingestion already close
2. Execution layer types second (WorkPacket, Action) — small surface
3. Adapter layer types third (Adapter Protocol) — 5 adapters to update
4. Spine types last (ControlPlaneEvent, Trace) — highest risk, most callers

---

## Recommended Next-Phase Actions

### Synthesis corrections needed (append to Appendix C)

5 reclassifications:
1. §35 → §34: UserPromptSubmit hook capture
2. §37 → §34: Full ingestion system
3. §37 → §34: Multi-Model Routing
4. §37 → §35: Composition Engine v1
5. §37 → §35: World Model Core

### Refactors needed BEFORE migration (0 blocking)

None. All three law violations are real but can be addressed
during migration rather than before it. The system runs today
with these violations — they are debt, not blockers.

### Refactors recommended DURING migration

1. **Law 5.9 — Adapter contract migration** (5 files)
   Split `execute()` into `translate_request()` + `normalize_result()`.
   Do this as each adapter moves to `adapters/` in §24 tree.

2. **Law 5.5 — Memory write consolidation** (46 files)
   Replace direct `INSERT INTO events` with `memory.log_event()`
   calls. Do this per-module as files move to §24 locations.

3. **Law 5.4 — Type adoption** (30+ files)
   Replace `@dataclass` with umh/protocols Pydantic types.
   Do this per-layer as files move, starting with Understanding.

### New §24 layers to add

1. **operations/** — operator tooling, batch/scheduled work, diagnostics
2. (No other new layers needed — Gap 2 resolves by deletion, Gap 3 resolves by adoption)

---

## Chat Summary

- Anchors inventoried: 30 files across 7 subsystem groups
- Law violations: Law 5.4 SYSTEMIC (0/30 use canonical types), Law 5.5 46 files, Law 5.9 5 adapters
- §34-§37 corrections: 5 items need reclassification
- Architectural gaps: 3 categories — operator tooling (52K LOC), shim layers (623 files), parallel type systems
- Pre-migration refactors required: 0 blocking; 3 recommended during migration
