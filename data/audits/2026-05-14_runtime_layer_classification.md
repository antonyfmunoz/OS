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

---

## Phase C Re-Classification — 2026-05-14

Post-Phase-A (Law 5.5 stores) + Phase-B (context.py shim):

### Blocker Status

| Blocker | Original | Current | Change |
|---------|----------|---------|--------|
| L5.5 violations | 52 modules | 2 modules (1 site each) | -50 |
| Context dependency | 64 modules (shim callers) | 0 (shim = non-blocking) | -64 |
| Both blocked | 28 modules | 0 | -28 |

Remaining L5.5: `execution_engine` (1 INSERT INTO outcomes),
`knowledge_integrator` (1 INSERT INTO interactions). Fixed inline during migration.

### Re-Classification Summary

| Original Status | Count | New Status | Notes |
|-----------------|-------|------------|-------|
| FREE (23 truly clean) | 23 | Sub-batch 1 | All still free |
| FREE (7 tangled) | 7 | Various batches | Tangled deps resolved |
| L5.5_BLOCKED | 10 | Sub-batch 1 mostly | Stores absorb SQL |
| CTX_BLOCKED | 17 | Sub-batch 1 mostly | Shim = non-blocking |
| BOTH_BLOCKED | 28 | Various batches | Both blockers cleared |
| email_gps (missing from original) | 1 | Sub-batch 2 | Added to classification |
| **Total** | **99** (excl. context) | **99** | +7 vs original 92 (context excluded, email_gps added) |

### Sub-Batch Assignment (by structural dependency tier)

**Sub-batch 1 — Zero runtime/ cross-deps (51 modules)**

Sorted by caller count ascending:

| Module | Callers | Target §24 Layer | Sub-path |
|--------|---------|-----------------|----------|
| ai_identity | 1 | control_plane/ | identity/ |
| ceo_operational_standards | 1 | control_plane/ | agents/ |
| competitive_intel | 1 | understanding/ | intelligence/ |
| doc_creator | 1 (b2) | adapters/ | google_workspace/ |
| event_manager | 1 | control_plane/ | events/ |
| feedback_loop | 3 | learning/ | feedback/ |
| founder_capture | 1 (b2) | understanding/ | signals/ |
| higgsfield_client | 1 | adapters/ | higgsfield/ |
| input_intelligence | 1 (b2) | understanding/ | intelligence/ |
| intent_router | 2 | control_plane/ | routing/ |
| media_processor | 2 | execution/ | media/ |
| os_registry | 2 | state/ | registries/ |
| principle_engine | 1 | governance/ | principles/ |
| session_state | 1 | state/ | session/ |
| template_registry | 1 | state/ | registries/ |
| voice_engine | 2 | execution/ | voice/ |
| world_model | 1 | understanding/ | world_model/ |
| ceo_intelligence | 2 | control_plane/ | agents/ |
| confidentiality | 2 | governance/ | policies/ |
| context_compaction | 2 | control_plane/ | context/ |
| decision_log | 3 | state/ | logs/ |
| delegation_tracker | 3 | control_plane/ | delegation/ |
| ea_operational_standards | 2 | control_plane/ | agents/ |
| embedding_engine | 5 | understanding/ | embedding/ |
| knowledge_domains | 3 | understanding/ | knowledge/ |
| knowledge_graph | 3 | understanding/ | knowledge/ |
| martell_patterns | 3 | understanding/ | patterns/ |
| model_preferences | 2 | state/ | preferences/ |
| notebooklm_sync | 3 | adapters/ | notebooklm/ |
| notion_publisher | 4 | adapters/ | notion/ |
| notion_sync | 4 | adapters/ | notion/ |
| okr_tracker | 2 | state/ | metrics/ |
| os_trinity | 3 | state/ | permissions/ |
| pattern_engine | 3 | understanding/ | patterns/ |
| portfolio_advisor_standards | 1 | control_plane/ | strategy/ |
| provider_health | 2 | observability/ | health/ |
| scrapling_connector | 4 | adapters/ | scrapling/ |
| signal_hierarchy | 3 | control_plane/ | signals/ |
| skill_registry_v2 | 1 | state/ | registries/ |
| subscription_tracker | 2 | state/ | finance/ |
| accountability | 3 | governance/ | accountability/ |
| browser_agent | 3 | execution/ | agents/ |
| channel | 7 | interface/ | channels/ |
| claude_skill_registry | 3 | state/ | registries/ |
| document_filer | 1 | adapters/ | google_workspace/ |
| embedder | 5 | understanding/ | embedding/ |
| founder_rate | 4 | state/ | metrics/ |
| gws_connector | 27 | adapters/ | google_workspace/ |
| agent_hierarchy | 4 | control_plane/ | agents/ |
| business_instance | 20 | state/ | business/ |
| venture_knowledge | 10 | state/ | business/ |
| work_state | 4 | state/ | work/ |
| person_recognition | 10 | understanding/ | intelligence/ |
| task_yield_matrix | 4 | control_plane/ | strategy/ |

**Sub-batch 2 — Deps only in sub-batch 1 (23 modules)**

Sorted by caller count ascending:

| Module | Callers | Deps (all in B1) | Target §24 |
|--------|---------|-------------------|-----------|
| agent_teams | 3 | browser_agent | control_plane/agents/ |
| ceo_agent | 3 | business_instance, ceo_intelligence | control_plane/agents/ |
| doc_creator | 1 | gws_connector | adapters/google_workspace/ |
| email_gps | 7 | browser_agent, document_filer, gws_connector, person_recognition | adapters/google_workspace/ |
| execution_engine | 2 | channel | execution/engine/ |
| expense_tracker | 5 | gws_connector | state/finance/ |
| founder_capture | 1 | founder_rate, task_yield_matrix | understanding/signals/ |
| human_intelligence | 6 | gws_connector | understanding/intelligence/ |
| ideal_week | 3 | skill_registry_v2 | control_plane/scheduling/ |
| input_intelligence | 1 | business_instance | understanding/intelligence/ |
| knowledge_integrator | 8 | embedding_engine | understanding/knowledge/ |
| meetings | 8 | gws_connector, person_recognition | adapters/calendar/ |
| personal_admin | 2 | person_recognition | control_plane/scheduling/ |
| provider_state | 6 | work_state | state/providers/ |
| quality_gate | 3 | signal_hierarchy | governance/quality/ |
| setup_wizard | 3 | business_instance | control_plane/onboarding/ |
| skill_registry | 4 | embedder | state/registries/ |
| stage_manager | 3 | business_instance | state/lifecycle/ |
| stakeholder_map | 2 | person_recognition | understanding/intelligence/ |
| strategy_engine | 5 | venture_knowledge | control_plane/strategy/ |
| system_health | 2 | channel | observability/health/ |
| tenant | 2 | business_instance | state/tenancy/ |
| user_model | 3 | os_trinity | state/profiles/ |

**Sub-batch 3 — Recursive deps (25 modules)**

Tier 3a (deps only in B1+B2, no B3 deps): 8

| Module | Callers | Target §24 |
|--------|---------|-----------|
| context_builder | 2 | control_plane/context/ |
| onboarding_engine | 1 | control_plane/onboarding/ |
| portfolio_advisor | 10 | control_plane/strategy/ |
| research_engine | 3 | understanding/research/ |
| skill_improvement | 3 | learning/skills/ |
| status | 1 | observability/status/ |
| travel_manager | 2 | adapters/calendar/ |
| week_architect | 1 | control_plane/scheduling/ |

Tier 3b (deps in B1+B2+3a): 3

| Module | Callers | B3 deps | Target §24 |
|--------|---------|---------|-----------|
| daily_sync | 2 | portfolio_advisor | control_plane/scheduling/ |
| evolution_engine | 5 | research_engine, skill_improvement | learning/evolution/ |
| task_executor | 2 | portfolio_advisor | execution/tasks/ |

Tier 3c (deps in B1+B2+3a+3b): 2

| Module | Callers | B3 deps | Target §24 |
|--------|---------|---------|-----------|
| proactive_engine | 1 | evolution_engine | control_plane/proactive/ |
| workflow_engine | 1 | task_executor | execution/workflows/ |

Tier 3d (remaining — contains 2 circular pairs): 12

| Module | Callers | B3 deps (within 3d) | Target §24 |
|--------|---------|---------------------|-----------|
| discord_utils ↔ output_validator | 9, 3 | (cycle) | interface/discord/, governance/validation/ |
| goal_selector ↔ event_bus | 11, 11 | (cycle) | control_plane/goals/, control_plane/events/ |
| coordination_engine | 5 | event_bus | control_plane/coordination/ |
| execution_loop | 2 | event_bus, goal_selector | execution/loop/ |
| gws_scanner | 2 | discord_utils | adapters/google_workspace/ |
| orchestrator | 5 | coordination_engine, discord_utils, reality_context, reality_engine, world_pulse | control_plane/orchestrator/ |
| reality_context | 2 | reality_engine | understanding/reality/ |
| reality_engine | 3 | event_bus | understanding/reality/ |
| self_awareness | 2 | output_validator | learning/self_model/ |
| world_pulse | 2 | discord_utils, gws_scanner | understanding/world_pulse/ |

**Circular pairs:** Migrate together in single commit.
- `discord_utils` + `output_validator` (lazy imports — no load-time cycle)
- `goal_selector` + `event_bus` (lazy imports — no load-time cycle)

### Migration Order Within Tier 3d

After resolving cycles (migrate pairs together):

1. discord_utils + output_validator (9+3 callers)
2. goal_selector + event_bus (11+11 callers)
3. gws_scanner (2, deps: discord_utils)
4. self_awareness (2, deps: output_validator)
5. reality_engine (3, deps: event_bus)
6. reality_context (2, deps: reality_engine)
7. coordination_engine (5, deps: event_bus)
8. execution_loop (2, deps: event_bus, goal_selector)
9. world_pulse (2, deps: discord_utils, gws_scanner)
10. orchestrator (5, deps on most of above)
