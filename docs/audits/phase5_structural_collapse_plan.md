# Phase 5: Repository Structural Collapse Plan

**Date:** 2026-04-24
**Status:** PLAN ONLY — no changes executed

---

## Current State

### Physical layout

```
/opt/OS/
├── umh/                    ← 13,131 lines — THE canonical system
├── _holding/
│   └── runtime_legacy/     ← symlinked as top-level dirs
│       ├── core/           ← 27,889 lines (68 .py files)
│       ├── eos_ai/         ← 101,651 lines (282 .py files, incl 90K substrate)
│       ├── parsers/        ← 450 lines (7 .py files)
│       ├── scripts/        ← 48,619 lines (167 .py files)
│       ├── services/       ← 15,443 lines (21 .py files)
│       └── tests/          ← test suite
│   └── infra_ops/          ← Docker, .env, .dockerignore
│   └── data_artifacts/     ← data/, backups
│   └── knowledge_vault/    ← Obsidian vault (10_Wiki)
│   └── eos_product/        ← agents/, products/, saas/, ventures/
│   └── claude_code_harnessing/ ← .claude skills, templates
│   └── prototype_surfaces/ ← prototype UIs
│   └── archive_candidates/ ← already flagged
│   └── unknown_review/     ← unclassified
├── core       → symlink → _holding/runtime_legacy/core
├── eos_ai     → symlink → _holding/runtime_legacy/eos_ai
├── parsers    → symlink → _holding/runtime_legacy/parsers
├── scripts    → symlink → _holding/runtime_legacy/scripts
├── services   → symlink → _holding/runtime_legacy/services
├── tests      → symlink → _holding/runtime_legacy/tests
├── data       → symlink → _holding/data_artifacts/data
├── Dockerfile → symlink → _holding/infra_ops/Dockerfile
├── docker-compose.yml → symlink → _holding/infra_ops/...
├── logs/               ← runtime logs
├── orchestrator/       ← empty (approvals dirs only)
├── vault/              ← memory storage
└── docs/               ← audits
```

### Line count summary

| Layer | Lines | Files | Role |
|-------|------:|------:|------|
| umh/ | 13,131 | 56 | Canonical domain system |
| core/ | 27,889 | 68 | Legacy domain logic + shims |
| eos_ai/ (excl substrate) | 10,751 | ~120 | EOS business intelligence |
| eos_ai/substrate/ | 90,900 | 272 | Runtime infrastructure |
| scripts/ | 48,619 | 167 | Tooling, ops, smoke tests |
| services/ | 15,443 | 21 | Production Docker entry points |
| parsers/ | 450 | 7 | AST parsing for graph |
| **Total runtime_legacy** | **193,602** | **~655** | |

### Production services (Docker)

| Container | Entry point | Dependency chain |
|-----------|-------------|------------------|
| os-discord | services/discord_bot.py | eos_ai.gateway → execution_spine → umh |
| os-bot | services/telegram_control.py | eos_ai.* (model_router, memory, event_bus) |
| os-monitor | services/dm_monitor.py | eos_ai.* (memory, icp_scorer) |
| os-webhook | services/calendly_webhook.py | eos_ai.* (memory, event_bus) |
| os-scraper | services/overnight_scrape.py | eos_ai.* (minimal) |

### UMH dependency direction

UMH imports from eos_ai in exactly 5 places (all lazy/adapter):
- `umh/execution/interfaces.py` → `eos_ai.adapters.umh_execution`
- `umh/goals/interfaces.py` → `eos_ai.adapters.umh_goals`
- `umh/memory/storage.py` → `eos_ai.adapters.umh_storage`
- `umh/strategy/interfaces.py` → `eos_ai.adapters.umh_strategy`
- `umh/world/state.py` → `eos_ai.decision_trace`, `eos_ai.goal_state`, `eos_ai.strategy_memory`

UMH imports from core in **0 places** (docstring reference only).

---

## Classification

### core/ — 68 files → 27,889 lines

#### SHIM (delete) — 5 files, 879 lines

Already superseded by UMH. All consumers migrated in Waves 2–3.

| File | Lines | Shims to | Action |
|------|------:|----------|--------|
| agent_harness.py | 778 | umh.execution.harness | DELETE (REPLACED_NOT_SHIMMED, Wave 2B) |
| improvement_governor.py | 33 | umh.governance.governor | DELETE |
| objective_engine.py | 24 | umh.goals.objective | DELETE |
| primitives.py | 23 | umh.primitives.ontological | DELETE |
| dynamics.py | 21 | umh.feedback.dynamics | DELETE |

#### UMH-DUPLICATE (absorb into umh/ or delete) — 10 files, 4,187 lines

Logic that duplicates or should live in UMH's domain.

| File | Lines | Duplicates | Action |
|------|------:|------------|--------|
| execution_contract.py | 384 | umh.execution.contract | ABSORB into umh/execution/ |
| execution_bridge.py | 1,313 | umh.execution.pipeline | ABSORB key logic into umh/execution/ |
| router.py | 319 | umh.capability.router | ABSORB into umh/capability/ |
| matcher.py | 338 | umh.capability.router (scoring) | ABSORB into umh/capability/ |
| feedback.py | 385 | umh.feedback.loop | ABSORB into umh/feedback/ |
| self_improvement.py | 481 | umh.governance.governor | ABSORB into umh/governance/ |
| transformer.py | 337 | No UMH equiv — unique | PROMOTE to umh/primitives/transformer.py |
| objective.py | 230 | umh.goals.objective | DELETE (UMH has it) |
| memory_evolution.py | 557 | umh.feedback.dynamics | ABSORB into umh/feedback/ |
| context.py | 124 | umh.context.types | DELETE (UMH has it) |

#### EOS INTEGRATION (keep, move to eos/) — 12 files, 5,668 lines

Thin wrappers binding UMH to EOS-specific infrastructure (Neon, model_router, eos_ai.memory).
Not domain logic — integration glue. Moves to a new `eos/` directory.

| File | Lines | Purpose | New location |
|------|------:|---------|-------------|
| advisor.py | 865 | Executor+Advisor model routing | eos/advisor.py |
| persistent_agents.py | 565 | Observer/Healer/Librarian ticking | eos/agents.py |
| control_plane.py | 321 | Orchestrator + agent lifecycle | eos/control_plane.py |
| optimizer.py | 651 | Log-reading improvement proposals | eos/optimizer.py |
| observability.py | 407 | Read-only system snapshot | eos/observability.py |
| environment.py | 534 | Prod/sandbox/playground paths | eos/environment.py |
| reality_input.py | 328 | Signal → primitive ingestion | eos/reality_input.py |
| composer.py | 319 | Intent → primitive composition | eos/composer.py |
| primitives_extended.py | 243 | Computed overlays on L0 | eos/primitives_ext.py |
| wiki_navigation.py | 325 | Graph ↔ Obsidian bridge | eos/wiki.py |
| coord_assignment.py | 414 | Semantic space coords | eos/coords.py |
| semantic_space.py | 506 | Hybrid coordinate index | eos/semantic_space.py |

#### EOS INTEGRATION — subdirectories

| Subdirectory | Files | Lines | Purpose | New location |
|-------------|------:|------:|---------|-------------|
| core/security/ | 9 | 2,993 | RBAC, approval, audit, identity | eos/security/ |
| core/orchestrator/ | 9 | 2,016 | Workflow registry, signal handlers | eos/orchestrator/ |
| core/action_system/ | 11 | 1,546 | Action lifecycle, validators | eos/actions/ |
| core/connectors/ | 5 | 536 | CRM/email/content connectors | eos/connectors/ |
| core/domain/ | 4 | 564 | EOS/Lyfe/Creator domain L2 | eos/domain/ |

### eos_ai/ — ~120 files (excl substrate) → 10,751 lines

#### EOS BUSINESS INTELLIGENCE (keep, move to eos/) — ~90 files

This is EOS-specific business logic: CEO intelligence, portfolio advisor,
knowledge graph, strategy engines, meetings, daily sync, etc. None of it
is generic UMH — it's the EOS *application* built on UMH.

| Category | Files | Lines | New location |
|----------|------:|------:|-------------|
| Gateway + Spine | 2 | 2,152 | eos/gateway.py, eos/spine.py |
| Context + Runtime | 5 | 5,934 | eos/runtime/ |
| Orchestration | 12 | 5,500 | eos/orchestration/ |
| Planning + Goals | 15 | 6,200 | eos/planning/ |
| Learning + Adaptation | 18 | 7,200 | eos/learning/ |
| Knowledge + Memory | 15 | 7,000 | eos/knowledge/ |
| Strategy + Mutation | 8 | 3,400 | eos/strategy/ |
| Execution + Control | 12 | 3,800 | eos/execution/ |
| Decision + Reasoning | 12 | 3,300 | eos/reasoning/ |
| Business Operations | 20 | 7,200 | eos/operations/ |
| Media + Communication | 8 | 3,700 | eos/media/ |
| Analytics + Monitoring | 10 | 3,100 | eos/analytics/ |
| Adapters | 21 | 3,490 | eos/adapters/ |
| Platforms | 13 | 3,849 | eos/platforms/ |
| Runtime | 13 | 2,196 | eos/session/ |
| Stages | 10 | 901 | eos/stages/ |
| Infrastructure | 20 | 4,700 | eos/infra/ |
| Stubs/Minimal | 11 | 400 | DELETE |

#### eos_ai/substrate/ — 272 files → 90,900 lines

Substrate is the runtime infrastructure layer: Discord transport, voice
pipelines, meeting intelligence, session management, operator workflows,
rituals, validation, etc.

**Decision: Move to eos/substrate/** — this is EOS application infrastructure,
not UMH domain logic.

### services/ — 21 files → 15,443 lines

**Classification: INTERFACE**

These are production entry points for Docker containers. They're thin enough
to stay at top level as `services/` or move to `eos/services/`.

| File | Lines | Classification |
|------|------:|---------------|
| discord_bot.py | 5,305 | INTERFACE (production) |
| telegram_control.py | 3,381 | INTERFACE (production) |
| dm_monitor.py | 1,474 | INTERFACE (production) |
| apify_scraper.py | 910 | INTERFACE (production) |
| icp_scorer.py | 629 | INTERFACE (production) |
| calendly_webhook.py | 486 | INTERFACE (production) |
| Other 15 files | 3,258 | INTERFACE (production + utility) |

### scripts/ — 167 files → 48,619 lines

**Classification: TOOLING**

| Category | Files | Lines | Action |
|----------|------:|------:|--------|
| Smoke tests (substrate) | 58 | ~15,000 | Move to tests/substrate/ |
| Daily operations | 20 | ~4,000 | Move to eos/ops/ |
| Notion integration | 11 | ~5,000 | Move to eos/integrations/notion/ |
| Memory/graph tools | 9 | ~4,000 | Move to tools/ |
| Orchestration scripts | 5 | ~3,000 | Move to eos/orchestration/ |
| Tool mastery engine | 5 | ~1,500 | Move to tools/tme/ |
| Session/context | 7 | ~2,000 | Move to tools/ |
| Sandbox/security | 5 | ~1,500 | Move to eos/security/ |
| action_system.py | 1 | 1,178 | Move to eos/actions/ |
| eos_os_smoke_test.py | 1 | 265 | Move to tests/ |
| Other utilities | ~45 | ~10,000 | Move to tools/ |

### parsers/ — 7 files → 450 lines

**Classification: TOOLING**

Used by `codebase_graph.py` for knowledge graph extraction. Not domain
logic. Move to `tools/parsers/`.

### orchestrator/ — empty

Contains only `approvals/pending/` and `approvals/approved/` directories.
The actual orchestration logic is in `core/orchestrator/`.
**Action:** DELETE directory, ensure `eos/orchestrator/` handles approval paths.

---

## Proposed New Directory Tree

```
/opt/OS/
├── umh/                        ← CANONICAL DOMAIN SYSTEM (13K lines)
│   ├── adapters/               ←   LLM + storage adapters
│   ├── capability/             ←   registry + router
│   ├── context/                ←   context types + builder
│   ├── decision/               ←   decision trace
│   ├── execution/              ←   harness, pipeline, contract, engine
│   ├── feedback/               ←   dynamics + loop
│   ├── goals/                  ←   engine, objective, state
│   ├── governance/             ←   capability, governor, authority
│   ├── intent/                 ←   compiler
│   ├── memory/                 ←   storage
│   ├── primitives/             ←   ontological + transformer (NEW)
│   ├── signal/                 ←   event_bus, ingest, types
│   ├── strategy/               ←   interfaces, memory
│   └── world/                  ←   model, state, simulation, reasoning
│
├── eos/                        ← EOS APPLICATION (thin wrappers + biz logic)
│   ├── actions/                ←   from core/action_system/
│   ├── adapters/               ←   from eos_ai/adapters/
│   ├── analytics/              ←   from eos_ai/ analytics modules
│   ├── connectors/             ←   from core/connectors/
│   ├── domain/                 ←   from core/domain/ (L2 compositions)
│   ├── gateway.py              ←   from eos_ai/gateway.py
│   ├── knowledge/              ←   from eos_ai/ knowledge modules
│   ├── learning/               ←   from eos_ai/ learning modules
│   ├── media/                  ←   from eos_ai/ media modules
│   ├── operations/             ←   from eos_ai/ business ops
│   ├── orchestration/          ←   from core/orchestrator/ + eos_ai/
│   ├── planning/               ←   from eos_ai/ planning modules
│   ├── platforms/              ←   from eos_ai/platforms/
│   ├── reasoning/              ←   from eos_ai/ reasoning modules
│   ├── runtime/                ←   from eos_ai/runtime/
│   ├── security/               ←   from core/security/
│   ├── session/                ←   from eos_ai/runtime/
│   ├── spine.py                ←   from eos_ai/execution_spine.py
│   ├── stages/                 ←   from eos_ai/stages/
│   ├── strategy/               ←   from eos_ai/ strategy modules
│   ├── substrate/              ←   from eos_ai/substrate/ (90K lines)
│   ├── advisor.py              ←   from core/advisor.py
│   ├── agents.py               ←   from core/persistent_agents.py
│   ├── composer.py             ←   from core/composer.py
│   ├── control_plane.py        ←   from core/control_plane.py
│   ├── environment.py          ←   from core/environment.py
│   ├── observability.py        ←   from core/observability.py
│   ├── optimizer.py            ←   from core/optimizer.py
│   └── ...                     ←   other eos_ai/ modules
│
├── services/                   ← PRODUCTION ENTRY POINTS (keep top-level)
│   ├── discord_bot.py
│   ├── telegram_control.py
│   ├── dm_monitor.py
│   ├── calendly_webhook.py
│   ├── overnight_scrape.py
│   └── handlers/
│
├── tools/                      ← DEVELOPER TOOLING
│   ├── parsers/                ←   from parsers/
│   ├── tme/                    ←   tool mastery engine
│   ├── graph/                  ←   codebase_graph, query_graph, etc.
│   ├── notion/                 ←   Notion integration scripts
│   ├── ops/                    ←   morning_intel, eod_sync, etc.
│   └── session_bootstrap.py    ←   session management
│
├── tests/                      ← ALL TESTS
│   ├── test_umh_*.py           ←   UMH unit tests (existing)
│   ├── substrate/              ←   substrate smoke tests (from scripts/)
│   └── integration/            ←   integration tests
│
├── infra/                      ← INFRASTRUCTURE
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.sessions
│   └── .dockerignore
│
├── data/                       ← RUNTIME DATA (keep symlink or move)
├── logs/                       ← RUNTIME LOGS
├── vault/                      ← MEMORY STORAGE
├── docs/                       ← DOCUMENTATION
└── .claude/                    ← CLAUDE CODE CONFIG
```

---

## File Move Plan

### Phase 5A: Delete shims (5 files, 879 lines)

```
DELETE  core/agent_harness.py        (778 lines — REPLACED_NOT_SHIMMED)
DELETE  core/improvement_governor.py  (33 lines — shim)
DELETE  core/objective_engine.py      (24 lines — shim)
DELETE  core/primitives.py            (23 lines — shim)
DELETE  core/dynamics.py              (21 lines — shim)
```

**Pre-check:** Verify no live imports remain for each.

### Phase 5B: Absorb UMH-duplicates (10 files, 4,187 lines)

```
ABSORB  core/execution_contract.py  → umh/execution/contract.py (merge unique logic)
ABSORB  core/execution_bridge.py    → umh/execution/pipeline.py (merge unique logic)
ABSORB  core/router.py              → umh/capability/router.py (merge scoring)
ABSORB  core/matcher.py             → umh/capability/router.py (merge scoring)
ABSORB  core/feedback.py            → umh/feedback/loop.py (merge)
ABSORB  core/self_improvement.py    → umh/governance/governor.py (merge)
ABSORB  core/memory_evolution.py    → umh/feedback/dynamics.py (merge)
PROMOTE core/transformer.py         → umh/primitives/transformer.py (no UMH equiv)
DELETE  core/objective.py           → already in umh/goals/objective.py
DELETE  core/context.py             → already in umh/context/types.py
```

**Risk: HIGH** — these have consumers. Each absorb requires:
1. Diff the two versions
2. Identify unique logic not in UMH
3. Port unique logic into UMH module
4. Migrate consumers to import from UMH
5. Delete core/ version

### Phase 5C: Create eos/ and migrate integration layer

```
MKDIR   eos/
MOVE    core/security/       → eos/security/
MOVE    core/orchestrator/   → eos/orchestrator/
MOVE    core/action_system/  → eos/actions/
MOVE    core/connectors/     → eos/connectors/
MOVE    core/domain/         → eos/domain/
MOVE    core/advisor.py      → eos/advisor.py
MOVE    core/persistent_agents.py → eos/agents.py
MOVE    core/control_plane.py → eos/control_plane.py
MOVE    core/optimizer.py    → eos/optimizer.py
MOVE    core/observability.py → eos/observability.py
MOVE    core/environment.py  → eos/environment.py
MOVE    core/reality_input.py → eos/reality_input.py
MOVE    core/composer.py     → eos/composer.py
MOVE    core/primitives_extended.py → eos/primitives_ext.py
MOVE    core/wiki_navigation.py → eos/wiki.py
MOVE    core/coord_assignment.py → eos/coords.py
MOVE    core/semantic_space.py → eos/semantic_space.py
```

Then fix all imports: `from core.X` → `from eos.X`

### Phase 5D: Migrate eos_ai/ to eos/

```
MOVE    eos_ai/gateway.py           → eos/gateway.py
MOVE    eos_ai/execution_spine.py   → eos/spine.py
MOVE    eos_ai/context_builder.py   → eos/runtime/context_builder.py
MOVE    eos_ai/agent_runtime.py     → eos/runtime/agent_runtime.py
MOVE    eos_ai/memory.py            → eos/runtime/memory.py
MOVE    eos_ai/model_router.py      → eos/runtime/model_router.py
MOVE    eos_ai/orchestrator.py      → eos/orchestration/orchestrator.py
MOVE    eos_ai/event_bus.py         → eos/runtime/event_bus.py
MOVE    eos_ai/db.py                → eos/runtime/db.py
MOVE    eos_ai/context.py           → eos/runtime/context.py
MOVE    eos_ai/adapters/            → eos/adapters/
MOVE    eos_ai/platforms/           → eos/platforms/
MOVE    eos_ai/runtime/             → eos/session/
MOVE    eos_ai/stages/              → eos/stages/
MOVE    eos_ai/substrate/           → eos/substrate/
MOVE    eos_ai/<business modules>   → eos/<category>/
DELETE  eos_ai/cognitive_loop.py    (DEPRECATED)
DELETE  eos_ai/<stub files>         (~11 files, 400 lines)
```

**Risk: CRITICAL** — services/ Docker entry points import from `eos_ai.*`.
Every `from eos_ai.` import in 100+ files must be rewritten.
Strategy: Create `eos_ai/__init__.py` compatibility shim during migration,
then delete after all consumers updated.

### Phase 5E: Reorganize scripts/ and parsers/

```
MKDIR   tools/
MOVE    parsers/                    → tools/parsers/
MOVE    scripts/codebase_graph.py   → tools/graph/codebase_graph.py
MOVE    scripts/query_graph.py      → tools/graph/query_graph.py
MOVE    scripts/incremental_graph.py → tools/graph/incremental_graph.py
MOVE    scripts/build_semantic_coords.py → tools/graph/build_coords.py
MOVE    scripts/session_bootstrap.py → tools/session_bootstrap.py
MOVE    scripts/action_system.py    → eos/actions/cli.py
MOVE    scripts/morning_intel.py    → tools/ops/morning_intel.py
MOVE    scripts/eod_sync.py         → tools/ops/eod_sync.py
MOVE    scripts/orchestrator.py     → eos/orchestration/loop.py
MOVE    scripts/notion_*.py         → tools/notion/
MOVE    scripts/*smoke*.py          → tests/substrate/
MOVE    scripts/eos_os_smoke_test.py → tests/eos_smoke_test.py
```

### Phase 5F: Infrastructure

```
MKDIR   infra/
MOVE    _holding/infra_ops/Dockerfile        → infra/Dockerfile
MOVE    _holding/infra_ops/docker-compose.yml → infra/docker-compose.yml
MOVE    _holding/infra_ops/.env.sessions     → infra/.env.sessions
MOVE    _holding/infra_ops/.dockerignore     → infra/.dockerignore
UPDATE  top-level symlinks to point to infra/
DELETE  orchestrator/ (empty — approvals dirs)
```

### Phase 5G: Remove symlinks and _holding/runtime_legacy/

Once all files moved out of `_holding/runtime_legacy/`:

```
REMOVE  symlink core
REMOVE  symlink eos_ai
REMOVE  symlink parsers
REMOVE  symlink scripts
REMOVE  symlink tests
REMOVE  symlink data
REMOVE  symlink Dockerfile
REMOVE  symlink docker-compose.yml
REMOVE  symlink .dockerignore
REMOVE  symlink .env.sessions
DELETE  _holding/runtime_legacy/  (should be empty)
```

---

## Deletion Candidates

### Immediate (zero consumers, already superseded)

| File | Lines | Reason |
|------|------:|--------|
| core/agent_harness.py | 778 | REPLACED_NOT_SHIMMED Wave 2B |
| core/improvement_governor.py | 33 | Shim to umh.governance.governor |
| core/objective_engine.py | 24 | Shim to umh.goals.objective |
| core/primitives.py | 23 | Shim to umh.primitives.ontological |
| core/dynamics.py | 21 | Shim to umh.feedback.dynamics |
| core/objective.py | 230 | Duplicate of umh.goals.objective |
| core/context.py | 124 | Duplicate of umh.context.types |
| eos_ai/cognitive_loop.py | 1,099 | DEPRECATED, only format_response_footer used |
| eos_ai/ stub files (~11) | ~400 | Empty/stub modules |
| orchestrator/ | 0 | Empty directory |
| **Total** | **~2,732** | |

### After absorb (Phase 5B)

| File | Lines | After absorbing into |
|------|------:|---------------------|
| core/execution_contract.py | 384 | umh/execution/ |
| core/execution_bridge.py | 1,313 | umh/execution/ |
| core/router.py | 319 | umh/capability/ |
| core/matcher.py | 338 | umh/capability/ |
| core/feedback.py | 385 | umh/feedback/ |
| core/self_improvement.py | 481 | umh/governance/ |
| core/memory_evolution.py | 557 | umh/feedback/ |
| **Total** | **3,777** | |

---

## Execution Order and Risk Assessment

| Phase | Risk | Lines affected | Import rewrites | Blocking? |
|-------|------|---------------:|----------------:|-----------|
| 5A: Delete shims | LOW | 879 | ~10 | No |
| 5B: Absorb duplicates | HIGH | 4,187 | ~30 | Yes — needs diff analysis |
| 5C: core/ → eos/ | MEDIUM | 12,323 | ~80 | Partially — security/orchestrator have consumers |
| 5D: eos_ai/ → eos/ | CRITICAL | 101,651 | ~500+ | Yes — production services depend on eos_ai.* |
| 5E: scripts/ → tools/ | LOW | 48,619 | ~20 | No — mostly standalone |
| 5F: Infrastructure | LOW | 0 | 4 symlinks | No |
| 5G: Remove symlinks | LOW | 0 | 0 | After 5A–5F complete |

### Recommended execution sequence

```
5A (shims) → 5B (absorb) → 5E (scripts) → 5F (infra)
    → 5C (core → eos) → 5D (eos_ai → eos) → 5G (cleanup)
```

5D is the hardest because 500+ import statements in production code
must change. Strategy: batch by subdirectory, use `sed` with verification,
test each batch before proceeding.

---

## Final "Clean" Repo Structure

```
/opt/OS/                        Lines
├── umh/            13,131      Canonical domain system
├── eos/           ~130,000     EOS application (integration + business logic)
│   ├── actions/                Action lifecycle
│   ├── adapters/               UMH adapter implementations
│   ├── analytics/              Monitoring + metrics
│   ├── connectors/             CRM/email/content connectors
│   ├── domain/                 L2 business compositions
│   ├── knowledge/              Knowledge graph + layers
│   ├── learning/               Adaptation + evolution
│   ├── media/                  Voice + video + comms
│   ├── operations/             Daily sync + business ops
│   ├── orchestration/          Workflow + signal handling
│   ├── planning/               Goal + plan engines
│   ├── platforms/              Platform runtimes
│   ├── reasoning/              Decision + reality engines
│   ├── runtime/                Gateway, spine, memory, model router
│   ├── security/               RBAC, approval, audit
│   ├── session/                Session lifecycle
│   ├── stages/                 Execution stages
│   ├── strategy/               Strategy + mutation
│   └── substrate/              Runtime infrastructure (90K)
├── services/       15,443      Docker entry points (5 containers)
├── tools/          ~50,000     Dev tooling + ops scripts
│   ├── graph/                  Codebase graph tools
│   ├── notion/                 Notion integration
│   ├── ops/                    Daily operations
│   ├── parsers/                AST parsers
│   └── tme/                    Tool mastery engine
├── tests/          ~15,000     All tests
├── infra/                      Docker, env
├── data/                       Runtime data
├── logs/                       Runtime logs
├── vault/                      Memory storage
├── docs/                       Documentation
└── .claude/                    Claude Code config
```

### Invariants achieved

1. **No execution logic outside umh/** — all domain execution in umh/execution/
2. **No routing logic outside umh/** — all capability routing in umh/capability/
3. **No capability logic outside umh/** — all governance in umh/governance/
4. **No structural ambiguity** — every file has exactly one home
5. **Clean dependency direction** — umh/ ← eos/ ← services/ (never reversed)
6. **Zero shims** — all compatibility layers eliminated
