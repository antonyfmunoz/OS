# Post-Consolidation System Exploration Audit

> Date: 2026-05-14
> Mode: READ-ONLY — fresh-eyes exploration
> Methodology: Mirrors 2026-05-13 exploration audit, applied to consolidated state
> Trigger: Substrate consolidation arc complete (124 commits, all threads closed)

---

## Executive Summary

The substrate consolidation reduced active Python from **3,488 files / 274K LOC**
to **874 files / 273K LOC** — a 75% file reduction with near-constant LOC (scaffold
removed, real code preserved). The codebase now has clear §24 layer boundaries with
10 populated directories, a functioning production stack (2 Docker services + 30 cron
jobs), and 116 active test files maintaining a 4082/34/3 baseline.

**Key findings:**
- 874 active .py files (was 3,488) — 75% file reduction
- 273K active LOC (was 274K) — LOC preserved, scaffold archived
- 10/12 §24 layers populated (distribution, onboarding: not yet created)
- 2,142 files / 756K LOC archived (properly preserved, not deleted)
- 2 Docker services running (os-discord, os-webhook)
- 30 active cron entries
- 30 raw SQL sites remain outside state/ (mostly Law 5.5 Phase C deferred)
- 12 `core/` top-level modules still active (66 callers total) — future migration
- 3 empty runtime/ subdirectories (domain_bridge, substrate, .substrate_sandbox)
- All 10 spine modules at canonical §24 locations

**Comparison to original drift-state audit:**

| Metric | Original (2026-05-13) | Current (2026-05-14) | Delta |
|--------|----------------------|---------------------|-------|
| Active .py files | 3,488 | 874 | −75% |
| Active LOC | 274,494 | 272,663 | −0.7% |
| core/ files | 493 | 13 | −97% |
| runtime/ files | 465 | 4 | −99% |
| eos_ai/ files | 459 | 0 | −100% |
| tests/ files | 639 | 116 | −82% |
| Docker services | 2 running | 2 running | unchanged |
| Cron entries | ~30 | 30 | audited |
| §24 layers | 0 populated | 10 populated | +10 |

---

## Phase 1: Top-Level Tree Map

### Active Tree (excluding _archive/, archive/)

| Directory | .py Files | LOC | Role |
|-----------|-----------|-----|------|
| execution/ | 198 | 75,674 | §24 execution layer (transport, workers, runtime) |
| scripts/ | 155 | 44,108 | Operator tooling + cron scripts |
| tests/ | 116 | 48,296 | Active test suite |
| control_plane/ | 96 | 24,298 | §24 control plane (gateway, cognitive loop) |
| state/ | 61 | 10,051 | §24 state layer (memory, stores, context) |
| understanding/ | 47 | 10,817 | §24 understanding (perception, knowledge) |
| composition/ | 44 | 10,286 | §24 composition (mastery, registries) |
| adapters/ | 34 | 9,657 | §24 adapters (GWS, models, calendar) |
| .agents/ | 35 | 9,050 | Plugin skills (not §24) |
| interface/ | 15 | 6,590 | §24 interface (presence, API) |
| governance/ | 15 | 2,573 | §24 governance (policy, quality) |
| core/ | 13 | 5,974 | Remnant modules (12 active, pending migration) |
| services/ | 11 | 7,954 | Production daemons (discord_bot primary) |
| learning/ | 9 | 2,404 | §24 learning (feedback, evolution) |
| operations/ | 7 | 2,436 | Operator tooling (salience pipeline) |
| observability/ | 6 | 967 | §24 observability (health, status) |
| runtime/ | 4 | 808 | Remnants (interfaces, transport shim, ingestion stub) |
| saas/ | 2 | 141 | TypeScript SaaS (out of scope) |
| umh/ | 1 | 6 | Namespace stub (__init__.py only) |

**Total active:** 874 files, 272,663 LOC

### Archive

| Location | Files | LOC |
|----------|-------|-----|
| _archive/ | ~1,000 | ~400K |
| archive/ | ~1,142 | ~356K |
| **Total archived** | **2,142** | **756,466** |

---

## Phase 2: §24 Layer Audit

### Layer Health Matrix

| Layer | Exists | Subdirs | Files | LOC | External Imports | Boundary Match |
|-------|--------|---------|-------|-----|-----------------|----------------|
| interface | ✓ | 4 | 15 | 6,590 | 101 | ✓ |
| control_plane | ✓ | 19 | 96 | 24,298 | 192 | ✓ |
| state | ✓ | 17 | 61 | 10,051 | 519 | ✓ |
| execution | ✓ | 12 | 198 | 75,674 | 1,790 | ✓ |
| adapters | ✓ | 9 | 34 | 9,657 | 147 | ✓ |
| governance | ✓ | 6 | 15 | 2,573 | 39 | ✓ |
| observability | ✓ | 2 | 6 | 967 | 4 | ✓ (thin) |
| understanding | ✓ | 13 | 47 | 10,817 | 117 | ✓ |
| composition | ✓ | 2 | 44 | 10,286 | 113 | ✓ |
| learning | ✓ | 4 | 9 | 2,404 | 12 | ✓ |
| distribution | ✗ | — | — | — | — | NOT BUILT |
| onboarding | ✗ | — | — | — | — | NOT BUILT |

### Observations

- **execution/** dominates (198 files, 75K LOC) because it holds transport (68 files)
  + workstation constitutional engines (14 files, ~20K LOC).
- **state/** has the highest inbound import ratio (519 imports for 61 files) — it's the
  most depended-upon layer, as expected for state/memory.
- **observability/** is thin (6 files, 4 external imports) — functional but minimal.
- **control_plane/orchestrator/approvals/** is empty (created but never populated).

### Top 5 Files by LOC (overall)

| # | File | LOC | Layer |
|---|------|-----|-------|
| 1 | services/discord_bot.py | 5,223 | (services) |
| 2 | interface/presence/handlers/substrate_command_handler.py | 4,424 | interface |
| 3 | control_plane/runtime/gateway.py | 1,972 | control_plane |
| 4 | control_plane/orchestrator/orchestrator.py | 1,867 | control_plane |
| 5 | execution/workers/workstation/constitutional_strategic_intelligence_engine_v1.py | 1,852 | execution |

---

## Phase 3: Runtime Remnants

| Subdirectory | Files | LOC | External Callers | Status |
|-------------|-------|-----|-----------------|--------|
| runtime/interfaces/ | 2 | 779 | 33 (1 PROD + 14 tests + proof scripts) | **ACTIVE** — pending relocation |
| runtime/transport/ | 1 | 28 | 1 (conftest shim) | **SHIM** — by design |
| runtime/ingestion/ | 1 | 1 | 0 (namespace stub) | **STUB** — actual code at understanding/perception/ |
| runtime/domain_bridge/ | 0 | 0 | 0 | **EMPTY** — archive candidate |
| runtime/substrate/ | 0 | 0 | 0 | **EMPTY** — archive candidate |
| runtime/.substrate_sandbox/ | 0 | 0 | 0 | **EMPTY** — archive candidate |

### Findings

- `runtime/interfaces/` is the only substantive remnant. Its 2 files
  (`discord_interface_adapter_v1.py`, `discord_spine_integration_v1.py`) have a real
  PROD caller (`substrate_command_handler.py`) — this was intentionally retained.
  Future §24 home: `interface/discord/` or `interface/presence/adapters/`.
- 3 empty directories (`domain_bridge`, `substrate`, `.substrate_sandbox`) should be
  cleaned up — they serve no purpose and create confusion.

---

## Phase 4: Production Entry Points

### Docker Services (2)

| Container | Entry Point | Status |
|-----------|------------|--------|
| os-discord | services/discord_bot.py | UP (41 min) |
| os-webhook | services/cc_webhook_receiver.py | UP (2 weeks) |

### discord_bot.py Dependency Surface

Direct imports from 5 §24 layers:
- `control_plane` (gateway, onboarding)
- `state` (context, business_instance)
- `understanding` (knowledge_integrator)
- `execution` (transport/*, voice)
- `interface` (discord utils, handlers)

Plus: `runtime.interfaces` (1 active remnant)

### Cron Jobs (30 entries)

| Frequency | Count | Examples |
|-----------|-------|---------|
| Every 5 min | 4 | orchestrator_loop, day_reminder, agent_task_executor, auth monitors |
| Every 15 min | 5 | call_prep, notion_tasks_sync, post_meeting, calendar, noshow |
| Daily | 13 | nightly_maintenance, morning_intel, eod_sync, discord_clear, etc. |
| Weekly | 5 | weekly_review, week_architect, portfolio_brief, relationship_nurture |
| Other | 3 | scraper, auth keepalive (6h), shim_retirement_monitor |

---

## Phase 5: Adapter + External Integration Inventory

### Integration Maturity

| System | Files | Maturity | Required Env Vars |
|--------|-------|----------|-------------------|
| Neon/Postgres | 37 | LIVE | DATABASE_URL |
| Discord | 112 | LIVE | DISCORD_TOKEN, WEBHOOK_URL |
| Google Workspace | 38 | LIVE | GOOGLE_CREDENTIALS_JSON |
| Anthropic/Claude | 59 | LIVE | CLAUDE_CODE_OAUTH_TOKEN (via /proc) |
| Notion | 55 | LIVE (partial) | NOTION_TOKEN |
| Ollama | 16 | LIVE (fallback) | OLLAMA_HOST |
| Groq | 10 | LIVE (fallback) | GROQ_API_KEY |
| Playwright | 10 | STAGED | (no special env) |
| Higgsfield | adapters/higgsfield/ | STUBBED | HIGGSFIELD_API_KEY |
| Apify | scripts/ | STAGED | APIFY_TOKEN |
| Calendly | interface/api/ | LIVE | CALENDLY_WEBHOOK_SECRET |

### adapters/ Directory Map

| Subdirectory | Files | Purpose |
|-------------|-------|---------|
| adapter_engine/ | 5 | Engine + pipeline (live_drive_docs) |
| calendar/ | 3 | Calendar/meetings integration |
| data_source_adapters/ | 4 | GWS + local file sources |
| google_workspace/ | 7 | GWS connector, email, scanner |
| higgsfield/ | 2 | Video generation (stubbed) |
| model_adapters/ | 5 | cc_sdk, Gemini, Groq, Ollama, Perplexity |
| notebooklm/ | 3 | NotebookLM adapter |
| notion/ | 3 | Notion sync |
| scrapling/ | 2 | Web scraping |

---

## Phase 6: Documentation Landscape

### docs/ Structure

```
docs/
├── audits/rollback/          — rollback procedures
├── canonical/                — umh_synthesis.md (single canonical doc)
├── migrations/               — migration guides
├── mvp/                      — MVP scope docs
├── operations/               — operational runbooks (unstale-audited)
├── plans/                    — build plans
├── strategy/                 — strategic docs
├── superpowers/plans|specs/  — superpowers plugin docs
└── system/                   — 93 contract specs + system docs
```

### Key Docs

- `docs/canonical/umh_synthesis.md` — 1,998 lines, THE canonical reference
- `docs/system/` — 93 files (down from 153 after phase report archive)
- `data/audits/` — 22 files (consolidation arc audit trail)

---

## Phase 7: Persistence Inventory

### Domain Stores (state/stores/)

| Store | File | LOC | Backing |
|-------|------|-----|---------|
| AgentRegistryStore | agent_registry_store.py | 28 | agents table |
| ApprovalStore | approval_store.py | 78 | approvals table |
| ContextCompactionStore | context_compaction_store.py | 38 | context_compaction table |
| EmailFolderStore | email_folder_store.py | 47 | email_folders table |
| EmbeddingStore | embedding_store.py | 38 | embeddings table |
| EntityLinkStore | entity_link_store.py | 38 | entity_links table |
| GoalStore | goal_store.py | 170 | goals table |
| HiggsFieldStore | higgsfield_store.py | 50 | higgsfield_jobs table |
| PermissionStore | permission_store.py | 115 | permissions table |
| PreferenceStore | preference_store.py | 47 | preferences table |
| ProfileStore | profile_store.py | 139 | profiles table |
| SkillStore | skill_store.py | 77 | skills table |
| TaskStore | task_store.py | 85 | tasks table |
| VentureStore | venture_store.py | 37 | ventures table |

**14 domain stores** backing the canonical state layer.

### Memory Stores (state/memory/)

| File | LOC | Purpose |
|------|-----|---------|
| memory.py | 1,039 | AgentMemory + ConversationMemory (canonical path) |
| contracts/canonical_memory_store_v1.py | 262 | Store contract |
| contracts/canonical_memory_reconciliation_engine_v1.py | 529 | Reconciliation |
| contracts/canonical_memory_query_contracts.py | 207 | Query contracts |
| contracts/memory_conflict_governance_v1.py | 167 | Conflict resolution |
| contracts/memory_identity_v1.py | 100 | Identity binding |

### Raw SQL Sites (outside state/ and tests/)

**30 sites found** — breakdown:

| Location | Sites | Category |
|----------|-------|----------|
| .agents/skills/last30days/ | 17 | Plugin (SQLite, not UMH) — NOT a violation |
| .claude/hooks/ | 1 | Validator (detecting SQL, not using it) — NOT a violation |
| scripts/ | 5 | Phase C deferred (known) |
| interface/presence/handlers/ | 4 | Phase C deferred (known) |
| understanding/knowledge/ | 1 | Phase C deferred (known) |
| **Actual Law 5.5 violations** | **10** | **All Phase C deferred, documented in manifest** |

---

## Phase 8: Test Landscape

### Structure

```
tests/
├── conftest.py              — root config + namespace pin
├── fixtures/                — shared test fixtures
├── integration/             — 3 integration tests
│   └── transport/           — transport integration
├── migration/               — 10 migration-pinning tests
│   └── conftest.py
└── [103 test files at root] — unit + functional tests
```

### Test Stats

| Category | Count |
|----------|-------|
| tests/ (root) | 103 |
| tests/migration/ | 10 |
| tests/integration/ | 3 |
| **Total active** | **116** |
| Baseline: passed | 4,082 |
| Baseline: skipped | 34 |
| Baseline: xfail | 3 |

### Markers in Use

- `@pytest.mark.external` — tests requiring external services
- `@pytest.mark.llm` — tests requiring LLM calls

### Coverage Gaps (structural)

- `governance/` — no dedicated test files (tested via integration)
- `observability/` — no dedicated test files
- `learning/` — no dedicated test files
- `composition/` — no dedicated test files (mastery tested via smoke scripts)

---

## Phase 9: Surprises + Orphans

### Root-Level Orphans

| File | LOC | Notes |
|------|-----|-------|
| `Untitled.md` | 5 | Accidental — should be deleted |
| `patch_pycord.py` | 121 | Runtime dependency patch for Discord library |

### Empty Directories (cleanup candidates)

| Path | Reason |
|------|--------|
| `runtime/domain_bridge/` | Actual code at `understanding/domains/` |
| `runtime/substrate/` | All shims were deleted during consolidation |
| `runtime/.substrate_sandbox/` | Dev sandbox, never populated |
| `control_plane/orchestrator/approvals/` | Created but never used |
| `eos_ai/` | All files removed (0 .py), directory shell remains |

### core/ Remnant (12 active modules, 66 callers)

These modules survived consolidation because they weren't in the Phase C
migration scope (which focused on runtime/ relocations):

| Module | LOC | Callers | Likely §24 Home |
|--------|-----|---------|-----------------|
| core.advisor | 864 | 4 | control_plane/strategy/ |
| core.agent_harness | 741 | 1 | execution/agents/ |
| core.capability | 510 | 8 | composition/registries/ |
| core.coord_assignment | 416 | 4 | control_plane/coordination/ |
| core.environment | 534 | 14 | execution/environments/ |
| core.execution_contract | 385 | 3 | execution/engine/ |
| core.observability | 408 | 6 | observability/ |
| core.optimizer | 652 | 6 | execution/engine/ |
| core.paths | 61 | 3 | (utility — could stay or move to config/) |
| core.persistent_agents | 566 | 5 | execution/agents/ |
| core.semantic_space | 509 | 10 | understanding/embedding/ |
| core.wiki_navigation | 328 | 2 | scripts/ (operator tooling) |

### Large Untouched Files

The `execution/workers/workstation/constitutional_*` engines (14 files,
~20K LOC total) are large but have callers (substrate_command_handler.py).
They were relocated from `core/workstation/` during Phase C but not
refactored — they're operational report generators, not execution engines
despite their names.

---

## Phase 10: Synthesis-vs-Reality Gap Analysis

### §5 Twelve Laws — Code Evidence

| Law | Enforcement Point | Status |
|-----|-------------------|--------|
| 5.1 Single Source of Truth | state/context/context.py + load_context_from_env (635 call sites) | ENFORCED |
| 5.2 Governed Action | governance/policy/authority_engine.py | ENFORCED |
| 5.3 State Attribution | state/memory/memory.py (source tracking per entry) | ENFORCED |
| 5.4 Type Discipline | control_plane/protocols/ (Pydantic v2 contracts) | PARTIAL (adoption gap) |
| 5.5 Single Memory Write Path | state/memory/memory.py (canonical), 10 violations remain | MOSTLY ENFORCED |
| 5.6 Environment Isolation | execution/environments/ (environment bridge) | PARTIAL |
| 5.7 Observability | observability/ (thin but present) | MINIMAL |
| 5.8 Safety Subordination | governance/quality/quality_gate.py | ENFORCED |
| 5.9 External Boundary | adapters/ + governed_shell_adapter (translate/normalize) | PARTIAL (2 of 6) |
| 5.10 Action/Execution Separation | control_plane/actions/ vs execution/ | ENFORCED (structurally) |
| 5.11 Mastery | composition/mastery/ (research + authoring + management) | ENFORCED |
| 5.12 Learning | learning/ (feedback, evolution, self_model) | EXISTS (minimal callers) |

### §29 Do-Not-Touch Core — Location Check

All spine modules at correct §24 locations:
- cognitive_loop → control_plane/runtime/ ✓
- model_router → execution/runtime/ ✓
- agent_runtime → execution/runtime/ ✓
- memory → state/memory/ ✓
- db → state/storage/ ✓
- execution_spine → execution/runtime/ ✓
- authority_engine → governance/policy/ ✓
- primitives → understanding/ontology/ ✓
- cc_sdk → adapters/model_adapters/ ✓
- gateway → control_plane/runtime/ ✓

### §34-§37 Spot Check

- §34 "Transport §24 migration": ✓ verified at execution/transport/ (68 files)
- §34 "Salience pipeline": ✓ verified at operations/memory/ (5 files)
- §35 "Composition Engine": ✓ partial at composition/ (44 files, no 15-step yet)
- §35 "Law 5.9 adapter contract": ✓ 2 adapters have methods, rest don't
- §36 "Full W0-001 triple-test": ✓ still unverified (no evidence of completion)
- §37 "Unified memory graph": ✓ still NOT BUILT (no graph traversal code)

### Synthesis Gaps (Minor)

1. Synthesis §24 mentions `distribution/` and `onboarding/` — directories don't exist.
   Status: correctly classified as NOT BUILT in §37.
2. Synthesis describes "14-stage governed runtime spine" — actual runtime path is
   gateway → cognitive_loop → model_router → execution (fewer explicit stages).
   This is expected: spec describes the end-state, not current implementation.
3. `runtime/interfaces/` is described as "active code (2 files)" in manifest but
   not mentioned in synthesis §34-§37. Should be classified §34 PROVEN (it has
   a production caller).

---

## Recommended Next Moves Before OG Build

### MUST_FIX (0 items)

No blocking issues found. The substrate is clean enough for OG build resumption.

### SHOULD_FIX (4 items)

1. **Delete 3 empty runtime/ subdirectories** (domain_bridge, substrate, .substrate_sandbox)
   — they create confusion about whether code lives there.
2. **Delete or move `Untitled.md`** from repo root.
3. **Delete empty `eos_ai/` directory** — all content removed, shell remains.
4. **Relocate `runtime/interfaces/` (2 files, 779 LOC)** to its §24 home
   (interface/presence/adapters/ or similar). 33 callers need updating.

### NICE_TO_HAVE (5 items)

1. Migrate 12 `core/` top-level modules to §24 homes (66 callers total).
2. Fix remaining 10 Law 5.5 raw SQL sites (scripts/ + interface/).
3. Add test files for governance/, observability/, learning/, composition/.
4. Remove empty `control_plane/orchestrator/approvals/` directory.
5. Rename `archive/` → `_archive/legacy/` for naming consistency.

---

## Final Comparison Table

| Metric | Drift State (2026-05-13) | Consolidated (2026-05-14) | Improvement |
|--------|-------------------------|--------------------------|-------------|
| Active .py files | 3,488 | 874 | −75% |
| Active Python LOC | 274,494 | 272,663 | −0.7% |
| §24 layers populated | 0 | 10 | +10 |
| Spine modules at canonical locations | 0 | 10/10 | Complete |
| Law 5.5 violations (est.) | ~100+ | 10 | −90% |
| Dead-code files | ~1,800 (est.) | 0 active (all archived) | Clean |
| Empty shim layers (eos_ai, substrate) | 623 files | 0 files | Removed |
| Test baseline | unknown | 4082/34/3 (pinned) | Established |
| Docker services | 2 running | 2 running | Unchanged |
| Audit coverage | 0 docs | 22 docs | Full trail |
| Navigation aids (READMEs) | 0 | 10 | Complete |
| Production namespace collisions | 1 (latent) | 0 (fixed) | Clean |

---

*End of audit.*
