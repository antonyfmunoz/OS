# Runtime Layer Classification — Row 88
# Date: 2026-05-14
# Scope: All 115 .py files under runtime/ (top-level only)

## Executive Summary

| Category | Count | Notes |
|----------|-------|-------|
| Spine (migrated W4-5, §24 copy exists) | 6 | cognitive_loop, gateway, agent_runtime, execution_spine, cc_sdk, model_router |
| Spine (migrated W4-5, §24 copy exists, state/) | 2 | db, memory |
| Reachable non-spine (Row 88 proper) | 92 | Target of this classification |
| Unreachable (Row 89 — archive candidates) | 15 | 0 external callers |
| **Total** | **115** | |

### Row 88 breakdown

| Bucket | Count | Blocker |
|--------|-------|---------|
| Law 5.5 violations (direct SQL) | 52 | memory.py API extension (Phase A) |
| Context-dependent, Law-5.5-clean | 17 | context.py migration (Phase B) — 96 callers |
| **Fully free** (no Law 5.5, no context dep) | 23 | None — migratable now |

### Three-phase dependency chain

```
Phase A: memory.py API extension → unblocks 52 Law-5.5 modules
Phase B: context.py hub migration → unblocks 17 context-dependent modules
Phase C: remaining modules in topological order
```

Phase A is the gate. Without it, 52 modules carry raw SQL into their
new §24 homes — violating the same Law that flagged them.

---

## Per-Module Classification Table

Legend:
- **Spine**: Y = migrated in W4-5 (§24 copy exists), — = not spine
- **L5.5**: count of direct SQL sites (INSERT/UPDATE/DELETE)
- **Ctx**: Y = imports runtime.context, — = does not
- **Callers**: external caller count (excluding self-imports)
- **Target**: best-guess §24 destination
- **Risk**: L = leaf/low, M = moderate, H = hub/high
- **Status**: FREE / L5.5_BLOCKED / CTX_BLOCKED / BOTH_BLOCKED / SPINE / UNREACHABLE

### Spine modules (already migrated — not Row 88)

| Module | §24 Copy | Callers | Status |
|--------|----------|---------|--------|
| cognitive_loop | control_plane/runtime/ | 19 | SPINE |
| gateway | control_plane/runtime/ | — | SPINE |
| agent_runtime | execution/runtime/ | 38 | SPINE |
| execution_spine | execution/runtime/ | 1 | SPINE |
| cc_sdk | adapters/model_adapters/ | 2 | SPINE |
| model_router | execution/runtime/ | 57 | SPINE |
| db | state/storage/ | — | SPINE |
| memory | state/memory/ | — | SPINE |

### Unreachable modules (Row 89 — archive candidates)

| Module | L5.5 | Ctx | Callers | Notes |
|--------|------|-----|---------|-------|
| agent_messages | 1 | Y | 0 | Dead code |
| company_instantiator | 2 | — | 0 | Dead code |
| email_reviewer | 1 | Y | 0 | Dead code |
| eod_closing_loop | 0 | Y | 0 | Dead code |
| error_handler | 0 | — | 0 | Dead code |
| harness_registry | 0 | — | 0 | Dead code |
| integration_test | 0 | — | 0 | Dead code |
| knowledge_layers | 0 | — | 0 | Dead code |
| onboarding_backfill | 0 | Y | 0 | Dead code |
| primitive_registry | 0 | — | 0 | Dead code |
| system_context | 0 | Y | 0 | Dead code |
| template_library | 0 | — | 0 | Dead code (zero callers despite being listed as spine) |
| transaction_workflow | 8 | — | 0 | Dead code — heaviest L5.5 violator |
| trinity | 0 | Y | 0 | Dead code |
| voice_interface | 0 | Y | 0 | Dead code |

### Row 88 — reachable non-spine modules (92 files)

| Module | L5.5 | Ctx | Callers | Target §24 Layer | Sub-path | Risk | Status |
|--------|------|-----|---------|-----------------|----------|------|--------|
| accountability | 2 | — | 2 | governance/ | accountability/ | L | L5.5_BLOCKED |
| agent_hierarchy | 0 | — | 3 | control_plane/ | agents/ | M | FREE |
| agent_teams | 0 | Y | 2 | control_plane/ | agents/ | L | CTX_BLOCKED |
| ai_identity | 0 | — | 1 | control_plane/ | identity/ | L | FREE |
| browser_agent | 0 | Y | 2 | execution/ | agents/ | L | CTX_BLOCKED |
| business_instance | 1 | — | 19 | state/ | business/ | H | L5.5_BLOCKED |
| ceo_agent | 0 | Y | 2 | control_plane/ | agents/ | M | CTX_BLOCKED |
| ceo_intelligence | 0 | Y | 2 | control_plane/ | agents/ | L | CTX_BLOCKED |
| ceo_operational_standards | 0 | — | 1 | control_plane/ | agents/ | L | FREE |
| channel | 0 | — | 7 | interface/ | channels/ | M | FREE |
| claude_skill_registry | 1 | Y | 2 | state/ | registries/ | L | BOTH_BLOCKED |
| competitive_intel | 1 | Y | 1 | understanding/ | intelligence/ | L | BOTH_BLOCKED |
| confidentiality | 1 | Y | 2 | governance/ | policies/ | L | BOTH_BLOCKED |
| context | 0 | — | 96 | state/ | context/ | H | FREE (hub) |
| context_builder | 0 | Y | 2 | control_plane/ | context/ | M | CTX_BLOCKED |
| context_compaction | 1 | Y | 2 | control_plane/ | context/ | L | BOTH_BLOCKED |
| coordination_engine | 1 | Y | 5 | control_plane/ | coordination/ | M | BOTH_BLOCKED |
| daily_sync | 0 | — | 2 | control_plane/ | scheduling/ | L | FREE |
| decision_log | 1 | Y | 2 | state/ | logs/ | L | BOTH_BLOCKED |
| delegation_tracker | 1 | Y | 3 | control_plane/ | delegation/ | L | BOTH_BLOCKED |
| discord_utils | 0 | — | 9 | interface/ | discord/ | M | FREE |
| doc_creator | 1 | Y | 1 | adapters/ | google_workspace/ | L | BOTH_BLOCKED |
| document_filer | 1 | Y | 1 | adapters/ | google_workspace/ | L | BOTH_BLOCKED |
| ea_operational_standards | 0 | — | 2 | control_plane/ | agents/ | L | FREE |
| embedder | 0 | — | 4 | understanding/ | embedding/ | L | FREE |
| embedding_engine | 2 | — | 5 | understanding/ | embedding/ | M | L5.5_BLOCKED |
| event_bus | 1 | Y | 10 | control_plane/ | events/ | H | BOTH_BLOCKED |
| event_manager | 3 | Y | 1 | control_plane/ | events/ | L | BOTH_BLOCKED |
| evolution_engine | 2 | Y | 4 | learning/ | evolution/ | M | BOTH_BLOCKED |
| execution_engine | 2 | Y | 1 | execution/ | engine/ | L | BOTH_BLOCKED |
| execution_loop | 0 | — | 1 | execution/ | loop/ | L | FREE |
| expense_tracker | 2 | Y | 5 | state/ | finance/ | M | BOTH_BLOCKED |
| feedback_loop | 3 | — | 2 | learning/ | feedback/ | L | L5.5_BLOCKED |
| founder_capture | 1 | Y | 1 | understanding/ | signals/ | L | BOTH_BLOCKED |
| founder_rate | 3 | Y | 4 | state/ | metrics/ | M | BOTH_BLOCKED |
| goal_selector | 5 | — | 10 | control_plane/ | goals/ | H | L5.5_BLOCKED |
| gws_connector | 0 | — | 26 | adapters/ | google_workspace/ | H | FREE |
| gws_scanner | 0 | Y | 1 | adapters/ | google_workspace/ | L | CTX_BLOCKED |
| higgsfield_client | 2 | — | 1 | adapters/ | higgsfield/ | L | L5.5_BLOCKED |
| human_intelligence | 1 | Y | 6 | understanding/ | intelligence/ | M | BOTH_BLOCKED |
| ideal_week | 2 | Y | 3 | control_plane/ | scheduling/ | L | BOTH_BLOCKED |
| input_intelligence | 0 | Y | 1 | understanding/ | intelligence/ | L | CTX_BLOCKED |
| intent_router | 0 | Y | 1 | control_plane/ | routing/ | L | CTX_BLOCKED |
| knowledge_domains | 1 | Y | 2 | understanding/ | knowledge/ | L | BOTH_BLOCKED |
| knowledge_graph | 1 | Y | 3 | understanding/ | knowledge/ | L | BOTH_BLOCKED |
| knowledge_integrator | 1 | Y | 7 | understanding/ | knowledge/ | M | BOTH_BLOCKED |
| martell_patterns | 0 | — | 3 | understanding/ | patterns/ | L | FREE |
| media_processor | 0 | — | 2 | execution/ | media/ | L | FREE |
| meetings | 4 | Y | 8 | adapters/ | calendar/ | M | BOTH_BLOCKED |
| model_preferences | 6 | Y | 2 | state/ | preferences/ | L | BOTH_BLOCKED |
| notebooklm_sync | 1 | Y | 2 | adapters/ | notebooklm/ | L | BOTH_BLOCKED |
| notion_publisher | 0 | — | 3 | adapters/ | notion/ | L | FREE |
| notion_sync | 1 | Y | 4 | adapters/ | notion/ | M | BOTH_BLOCKED |
| okr_tracker | 1 | Y | 2 | state/ | metrics/ | L | BOTH_BLOCKED |
| onboarding_engine | 0 | — | 1 | control_plane/ | onboarding/ | L | FREE |
| orchestrator | 0 | Y | 5 | control_plane/ | orchestrator/ | H | CTX_BLOCKED |
| os_registry | 0 | — | 1 | state/ | registries/ | L | FREE |
| os_trinity | 3 | Y | 2 | state/ | permissions/ | L | BOTH_BLOCKED |
| output_validator | 0 | — | 3 | governance/ | validation/ | L | FREE |
| pattern_engine | 0 | Y | 2 | understanding/ | patterns/ | L | CTX_BLOCKED |
| person_recognition | 0 | Y | 10 | understanding/ | intelligence/ | H | CTX_BLOCKED |
| personal_admin | 1 | Y | 2 | control_plane/ | scheduling/ | L | BOTH_BLOCKED |
| portfolio_advisor | 0 | Y | 9 | control_plane/ | strategy/ | H | CTX_BLOCKED |
| portfolio_advisor_standards | 0 | — | 1 | control_plane/ | strategy/ | L | FREE |
| principle_engine | 0 | Y | 1 | governance/ | principles/ | L | CTX_BLOCKED |
| proactive_engine | 0 | — | 1 | control_plane/ | proactive/ | L | FREE |
| provider_health | 0 | — | 1 | observability/ | health/ | L | FREE |
| provider_state | 0 | — | 5 | state/ | providers/ | M | FREE |
| quality_gate | 1 | Y | 3 | governance/ | quality/ | L | BOTH_BLOCKED |
| reality_context | 0 | Y | 1 | understanding/ | reality/ | L | CTX_BLOCKED |
| reality_engine | 0 | Y | 2 | understanding/ | reality/ | L | CTX_BLOCKED |
| research_engine | 1 | Y | 2 | understanding/ | research/ | L | BOTH_BLOCKED |
| scrapling_connector | 0 | — | 3 | adapters/ | scrapling/ | L | FREE |
| self_awareness | 3 | — | 1 | learning/ | self_model/ | L | L5.5_BLOCKED |
| session_state | 0 | — | 1 | state/ | session/ | L | FREE |
| setup_wizard | 0 | Y | 2 | control_plane/ | onboarding/ | L | CTX_BLOCKED |
| signal_hierarchy | 0 | — | 3 | control_plane/ | signals/ | L | FREE |
| skill_improvement | 2 | — | 3 | learning/ | skills/ | L | L5.5_BLOCKED |
| skill_registry | 0 | — | 4 | state/ | registries/ | M | FREE |
| skill_registry_v2 | 1 | — | 1 | state/ | registries/ | L | L5.5_BLOCKED |
| stage_manager | 1 | Y | 2 | state/ | lifecycle/ | L | BOTH_BLOCKED |
| stakeholder_map | 1 | Y | 2 | understanding/ | intelligence/ | L | BOTH_BLOCKED |
| status | 0 | — | 1 | observability/ | status/ | L | FREE |
| strategy_engine | 0 | Y | 4 | control_plane/ | strategy/ | M | CTX_BLOCKED |
| subscription_tracker | 1 | Y | 2 | state/ | finance/ | L | BOTH_BLOCKED |
| system_health | 0 | Y | 2 | observability/ | health/ | L | CTX_BLOCKED |
| task_executor | 2 | Y | 1 | execution/ | tasks/ | L | BOTH_BLOCKED |
| task_yield_matrix | 1 | Y | 4 | control_plane/ | strategy/ | M | BOTH_BLOCKED |
| template_registry | 0 | — | 1 | state/ | registries/ | L | FREE |
| tenant | 0 | — | 1 | state/ | tenancy/ | L | FREE |
| travel_manager | 2 | Y | 2 | adapters/ | calendar/ | L | BOTH_BLOCKED |
| user_model | 1 | Y | 2 | state/ | profiles/ | L | BOTH_BLOCKED |
| venture_knowledge | 0 | — | 10 | state/ | business/ | H | FREE |
| voice_engine | 0 | — | 2 | execution/ | voice/ | L | FREE |
| week_architect | 0 | — | 1 | control_plane/ | scheduling/ | L | FREE |
| work_state | 0 | — | 4 | state/ | work/ | M | FREE |
| workflow_engine | 2 | Y | 1 | execution/ | workflows/ | L | BOTH_BLOCKED |
| world_model | 0 | — | 1 | understanding/ | world_model/ | L | FREE |
| world_pulse | 0 | Y | 1 | understanding/ | world_pulse/ | L | CTX_BLOCKED |

---

## Status Distribution

| Status | Count | Meaning |
|--------|-------|---------|
| FREE | 37 | No Law 5.5, no context dependency — migratable now |
| L5.5_BLOCKED | 10 | Has direct SQL but no context dependency |
| CTX_BLOCKED | 17 | Depends on context.py but no direct SQL |
| BOTH_BLOCKED | 28 | Has direct SQL AND depends on context.py |
| **Total Row 88** | **92** | |

### The 37 FREE modules — transitive dependency check

These 37 modules have no Law 5.5 violations and no direct context.py
dependency. However, some depend on other runtime modules that ARE blocked.

Modules with zero cross-dependencies on blocked modules (truly free):

| Module | Callers | Internal deps (all free) |
|--------|---------|--------------------------|
| ai_identity | 1 | (none) |
| ceo_operational_standards | 1 | (none) |
| channel | 7 | (none) |
| daily_sync | 2 | email_gps(L5.5), gws_connector, ideal_week(L5.5) — TANGLED |
| discord_utils | 9 | output_validator |
| ea_operational_standards | 2 | (none) |
| embedder | 4 | (none) |
| execution_loop | 1 | event_bus(L5.5), goal_selector(L5.5) — TANGLED |
| gws_connector | 26 | (none) |
| martell_patterns | 3 | (none) |
| media_processor | 2 | (none) |
| notion_publisher | 3 | (none) |
| onboarding_engine | 1 | business_instance(L5.5), setup_wizard(CTX) — TANGLED |
| os_registry | 1 | (none) |
| output_validator | 3 | discord_utils |
| portfolio_advisor_standards | 1 | (none) |
| proactive_engine | 1 | accountability(L5.5), business_instance(L5.5) — TANGLED |
| provider_health | 1 | (none) |
| provider_state | 5 | work_state |
| scrapling_connector | 3 | (none) |
| session_state | 1 | (none) |
| signal_hierarchy | 3 | (none) |
| skill_registry | 4 | embedder |
| status | 1 | skill_registry, venture_knowledge |
| template_registry | 1 | (none) |
| tenant | 1 | business_instance(L5.5) — TANGLED |
| venture_knowledge | 10 | (none) |
| voice_engine | 2 | (none) |
| week_architect | 1 | gws_connector, ideal_week(L5.5) — TANGLED |
| work_state | 4 | (none) |
| world_model | 1 | transport (separate package) |

**Truly clean (zero tangled deps): 23 modules**

| Module | Callers | Target |
|--------|---------|--------|
| ai_identity | 1 | control_plane/identity/ |
| ceo_operational_standards | 1 | control_plane/agents/ |
| channel | 7 | interface/channels/ |
| discord_utils | 9 | interface/discord/ |
| ea_operational_standards | 2 | control_plane/agents/ |
| embedder | 4 | understanding/embedding/ |
| gws_connector | 26 | adapters/google_workspace/ |
| martell_patterns | 3 | understanding/patterns/ |
| media_processor | 2 | execution/media/ |
| notion_publisher | 3 | adapters/notion/ |
| os_registry | 1 | state/registries/ |
| output_validator | 3 | governance/validation/ |
| portfolio_advisor_standards | 1 | control_plane/strategy/ |
| provider_health | 1 | observability/health/ |
| provider_state | 5 | state/providers/ |
| scrapling_connector | 3 | adapters/scrapling/ |
| session_state | 1 | state/session/ |
| signal_hierarchy | 3 | control_plane/signals/ |
| skill_registry | 4 | state/registries/ |
| template_registry | 1 | state/registries/ |
| venture_knowledge | 10 | state/business/ |
| voice_engine | 2 | execution/voice/ |
| work_state | 4 | state/work/ |

These 23 can migrate immediately without any prerequisite work.
7 additional "free" modules are TANGLED — they depend on blocked
modules and should wait for Phase A/B.

---

## Dependency Graph (rough — runtime-internal only)

Hub modules (≥10 callers) form the skeleton:
```
context.py (96) ──→ nearly everything
gws_connector (26) ──→ email_gps, meetings, expense_tracker, ...
business_instance (19) ──→ ceo_agent, evolution_engine, orchestrator, ...
event_bus (10) ──→ coordination_engine, execution_loop, reality_engine
goal_selector (10) ──→ execution_loop
venture_knowledge (10) ──→ reality_context, strategy_engine, ...
person_recognition (10) ──→ email_gps, meetings, personal_admin, ...
portfolio_advisor (9) ──→ orchestrator, task_executor
discord_utils (9) ──→ gws_scanner, world_pulse, eod_closing_loop, ...
```

context.py is the single highest-connectivity node. It's a dataclass
+ env-loader (~40 lines) but is imported by 96 files. Phase B (moving it)
is the largest single blast-radius migration in the codebase.

### §24 Layer Distribution (92 reachable modules)

| Target Layer | Module Count | Notes |
|--------------|-------------|-------|
| control_plane/ | 24 | agents, scheduling, strategy, goals, events |
| state/ | 19 | context, business, registries, finance, metrics |
| understanding/ | 16 | intelligence, knowledge, patterns, embedding |
| adapters/ | 10 | google_workspace, notion, calendar, scrapling |
| execution/ | 8 | engine, loop, agents, media, voice, workflows |
| governance/ | 5 | accountability, policies, quality, validation |
| learning/ | 5 | evolution, feedback, skills, self_model |
| observability/ | 3 | health, status |
| interface/ | 2 | channels, discord |

---

## Migration Order Recommendation

### Immediate (23 modules — no blockers)
The 23 truly clean modules listed above. Topological order:
1. Leaves with 0 internal deps: ai_identity, ceo_operational_standards,
   ea_operational_standards, gws_connector, martell_patterns,
   media_processor, os_registry, portfolio_advisor_standards,
   provider_health, scrapling_connector, session_state, template_registry,
   venture_knowledge, voice_engine
2. Modules depending only on other free modules: channel, embedder,
   signal_hierarchy, work_state, notion_publisher, provider_state,
   skill_registry, output_validator, discord_utils

### Phase A (prerequisite for 52 modules)
Extend memory.py API to cover direct SQL patterns. See companion audit:
`data/audits/2026-05-14_law_5_5_memory_api_design.md`

### Phase B (prerequisite for 17 modules)
Migrate context.py (96 callers) — or install re-export shim.

### Phase C (remaining 52 modules after A+B)
Topological order, hubs last. Largest batches:
- understanding/ group: 16 modules
- control_plane/ group: 24 modules
- state/ group: 19 modules
