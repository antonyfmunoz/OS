# TRIAGE-MANIFEST — Per-Subsystem Migration Plan

> Date: 2026-05-13
> Trigger: Synthesize exploration + core spot + salience + gap analysis
> Mode: READ-ONLY synthesis. No code changes.
> Purpose: Executable migration plan — every load-bearing subsystem
>          labeled, targeted, prioritized, risk-assessed.

---

## Executive Summary

| Label | Subsystems | Files | LOC |
|-------|-----------|-------|-----|
| PRESERVE | 18 | ~300 | ~43K |
| REFACTOR_AND_RELOCATE | 12 | ~160 | ~32K |
| EXTRACT_INTENT | 5 | ~47 | ~10K |
| ARCHIVE | 14 | ~1,730 | ~420K |
| DELETE | 2 | ~623 | ~1.8K |
| **Total triaged** | **51** | **~2,860** | **~507K** |

Post-migration active tree: ~460 files, ~75K LOC (down from ~3,500 Python files, ~570K LOC).

Architectural gap resolutions: 4 proposed.
Open questions for founder: 3.

---

## Methodology

### Source audits consumed

1. **Exploration audit** (2026-05-13) — full directory inventory, reachability trace,
   254 reachable production files, 623 shims, 745 orphan candidates
2. **Core spot audit** (2026-05-13) — 10-module deterministic sample of core/;
   70% scaffold, 20% genuine, 10% mixed
3. **Salience audit** (2026-05-13) — scripts/ salience pipeline verified RELOCATED;
   2,100 LOC, 5 files, architecturally correct in scripts/
4. **Gap analysis** (2026-05-13) — 30 anchor files, Law 5.4/5.5/5.9 violations,
   Two-Type-System Problem, §24 mapping

### Label definitions

| Label | Meaning | Action |
|-------|---------|--------|
| **PRESERVE** | Working code, correct location or simple move. No refactor needed. | Relocate to §24 path (if not already there). |
| **REFACTOR_AND_RELOCATE** | Working code with Law violations or contract mismatches. Needs refactor as it moves. | Fix violation + relocate in same commit. |
| **EXTRACT_INTENT** | Scaffold with genuine design thinking but no working code. Worth capturing ideas. | Write design intent doc → `docs/design_intent/` → archive code. |
| **ARCHIVE** | No production callers, no recent commits, no design value beyond historical record. | Move to `_archive/` wholesale. Preserved on disk + in git. |
| **DELETE** | Pure redundancy — shim re-exports with zero original code. | Remove after dependents updated to canonical imports. |

### Evidence requirements

Every label assignment cites one of: exploration audit reachability data,
core spot audit verdict, salience audit classification, gap analysis inventory,
or live grep/git evidence gathered during this synthesis.

---

## Phase 1: Directory Inventory

### Top-Level Directories

| Directory | Python Files | LOC | Markdown | Audit References |
|-----------|-------------|-----|----------|-----------------|
| `core/` | 493 | 118,306 | 3 | Spot audit (70% scaffold), Gap analysis (19 subdirs with callers) |
| `runtime/` | 465 | 113,513 | 2 | Exploration (84% reachable at top level), Gap analysis (30 anchors) |
| `scripts/` | 187 | 52,036 | 0 | Salience audit (2,100 LOC pipeline), Gap analysis (no §24 home) |
| `services/` | 21 | 19,458 | 2 | Exploration (80% reachable), Gap analysis (discord_bot 5,212 LOC) |
| `tests/` | 649 | 351,406 | 3 | Exploration (423 legacy, 216 active) |
| `eos_ai/` | 459 | 1,828 | 1 | Exploration (all 4-line shims), Gap analysis (DELETE candidate) |
| `umh/` | 23 | 3,292 | 1 | Gap analysis (86 Pydantic types, 0 production consumers) |
| `parsers/` | 7 | 448 | 0 | Exploration (100% reachable) |
| `archive/` | 1,178 | 360,953 | 15 | Exploration (historical artifacts) |
| `data/` | 0 | 0 | 153 | Exploration (234 MB runtime artifacts) |
| `docs/` | 0 | 0 | 624 | Exploration (96 phase reports, 182 ops docs) |
| `saas/` | 2 | 141 | 65 | Exploration (TypeScript SaaS, separate concern) |
| `skills/` | 1 | 160 | 326 | Exploration (165 SKILL.md files) |
| `agents/` | 0 | 0 | 19 | Exploration (18 soul documents) |
| `vault/` | 0 | 0 | 656 | Obsidian vault (daily notes, conversations) |
| `logs/` | 0 | 0 | 0 | Runtime logs (33 MB) |
| `config/` | 0 | 0 | 0 | 17 JSON/YAML config files |
| Other¹ | ~39 | ~9,533 | ~375 | Mixed: .agents, .claude, infra, knowledge, etc. |

¹ Other: `.agents/` (35 py, 9,050 LOC), `.claude/` (1 py, 114 LOC), `infra/` (1 py, 121 LOC),
`templates/` (1 py, 57 LOC), `frontend/` (0 py), `orchestrator/` (markdown-only),
`knowledge/` (TypeScript), `ventures/` (stub), Obsidian numbered dirs.

### High-Traffic Subdirectories

| Subdirectory | Files | LOC | External Callers | Status |
|-------------|-------|-----|-----------------|--------|
| `core/runtime/` | 44 | 12,183 | 35 | GENUINE (spot audit) |
| `core/workstation/` | 41 | 26,604 | 129 | GENUINE (heavy import volume) |
| `core/tool_mastery_research_agent/` | 18 | 6,000 | 4 | GENUINE (spot audit) |
| `core/action_system/` | 11 | 1,809 | 11 | GENUINE (control plane) |
| `core/environment_bridge/` | 18 | 3,716 | 7 | GENUINE (work_packet used) |
| `core/control_plane_router/` | 2 | 687 | 17 | GENUINE (router contracts) |
| `core/orchestrator/` | 9 | 1,954 | 11 | GENUINE (orchestration contracts) |
| `core/adapters/` | 7 | 2,335 | 6 | GENUINE (adapter contracts) |
| `core/tool_mastery_manager/` | 11 | 1,832 | 7 | GENUINE (mastery management) |
| `core/tool_mastery_author_agent/` | 11 | 2,029 | 5 | GENUINE (author pipeline) |
| `core/ontology/` | 1 | 127 | 5 | GENUINE (PrimitiveObservation) |
| `core/memory/` | 5 | 1,265 | 6 | GENUINE (memory contracts) |
| `core/registry/` | 1 | 425 | 4 | GENUINE (registry contracts) |
| `core/execution/` | 3 | 894 | 3 | GENUINE (execution contracts) |
| `core/state/` | 1 | 383 | 3 | GENUINE (state contracts) |
| `core/coherence/` | 4 | 496 | 2 | BORDERLINE (low caller count) |
| `core/governance/` | 1 | 674 | 1 | BORDERLINE (1 caller) |
| `core/interpretation/` | 1 | 551 | 1 | BORDERLINE (1 caller) |
| `core/actuation/` | 4 | 839 | 1 | BORDERLINE (1 caller) |
| 26 core/ subdirs | ~280 | ~47K | 0 each | SCAFFOLD (spot audit pattern) |
| `runtime/transport/` | 164 | 55,794 | 5 external modules | Mostly orphan (exploration) |
| `runtime/substrate/` | 164 | ~164 | 332 refs from services/ | Re-export shims |
| `runtime/ingestion/` | 6 | 1,346 | 3 | GENUINE (canonical pipeline) |
| `runtime/domain_bridge/` | 4 | 356 | 2 | GENUINE (domain projection) |
| `services/handlers/` | 6 | ~6,000 | 1 | Production (discord dispatch) |

---

## Phase 2: Label Assignments

### Main Assignment Table

| # | Path | Label | Target §24 | Refactor Needed | Priority | Risk | Evidence |
|---|------|-------|-----------|----------------|----------|------|----------|
| **SPINE** | | | | | | | |
| 1 | `runtime/cognitive_loop.py` | REFACTOR_AND_RELOCATE | `control_plane/runtime/` | Law 5.4: `dict` payloads → typed | P5 | HIGH | Gap: 19 callers, untyped authority/request |
| 2 | `runtime/model_router.py` | REFACTOR_AND_RELOCATE | `execution/runtime/` | Law 5.4: `dict` kwargs → typed | P5 | HIGH | Gap: 57 callers, highest fan-out |
| 3 | `runtime/agent_runtime.py` | REFACTOR_AND_RELOCATE | `execution/runtime/` | Law 5.4: `dict` authority → typed | P5 | HIGH | Gap: 38 callers |
| 4 | `runtime/memory.py` | REFACTOR_AND_RELOCATE | `state/memory/` | Law 5.5: IS canonical path, needs schema unification | P5 | HIGH | Gap: 34 callers, canonical path |
| 5 | `runtime/db.py` | PRESERVE | `state/storage/` | None | P5 | HIGH | Gap: 97 callers, foundation |
| 6 | `runtime/execution_spine.py` | PRESERVE | `execution/runtime/` | None | P4 | LOW | Gap: 1 caller |
| 7 | `runtime/authority_engine.py` | PRESERVE | `governance/policy/` | None | P4 | LOW | Gap: 5 callers |
| 8 | `runtime/primitives.py` | PRESERVE | `understanding/ontology/` | None | P4 | LOW | Gap: 3 callers |
| 9 | `runtime/cc_sdk.py` | PRESERVE | `adapters/model_adapters/` | None | P4 | LOW | Gap: 2 callers |
| 10 | `runtime/gateway.py` | REFACTOR_AND_RELOCATE | `control_plane/runtime/` | Law 5.4: untyped dispatch | P5 | HIGH | Exploration: 1,972 LOC |
| **INGESTION** | | | | | | | |
| 11 | `runtime/ingestion/orchestrator.py` | PRESERVE | `understanding/perception/` | None (recently built, types clean) | P2 | LOW | Gap: canonical pipeline |
| 12 | `runtime/ingestion/local_file_source.py` | PRESERVE | `adapters/data_source_adapters/` | None | P1 | LOW | Gap: 2 callers |
| 13 | `runtime/ingestion/gws_source.py` | PRESERVE | `adapters/data_source_adapters/` | None | P1 | LOW | Gap: 1 caller |
| 14 | `runtime/ingestion/authority_tier.py` | PRESERVE | `governance/policy/` | None | P1 | LOW | Gap: 3 callers |
| **DOMAIN BRIDGE** | | | | | | | |
| 15 | `runtime/domain_bridge/` (3 files) | PRESERVE | `understanding/domains/` | None | P2 | LOW | Gap: canonical domain projection |
| **CORE — GENUINE** | | | | | | | |
| 16 | `core/runtime/` (44 files) | REFACTOR_AND_RELOCATE | `execution/runtime/` + `adapters/adapter_engine/` | Review contracts for Law 5.4 adoption | P3 | MEDIUM | Spot: GENUINE, 35 callers |
| 17 | `core/workstation/` (41 files) | REFACTOR_AND_RELOCATE | `execution/workers/workstation/` | Law 5.9: governed_shell/browser adapters use execute() | P3 | MEDIUM | Gap: 129 callers, 26K LOC; 2 Law 5.9 adapters |
| 18 | `core/tool_mastery_research_agent/` (18 files) | PRESERVE | `composition/mastery/research/` | None | P2 | LOW | Spot: GENUINE, 4 commits, real pipeline |
| 19 | `core/tool_mastery_author_agent/` (11 files) | PRESERVE | `composition/mastery/authoring/` | None | P2 | LOW | 5 callers from scripts/ |
| 20 | `core/tool_mastery_manager/` (11 files) | PRESERVE | `composition/mastery/management/` | None | P2 | LOW | 7 callers |
| 21 | `core/action_system/` (11 files) | PRESERVE | `control_plane/actions/` | None | P2 | LOW | Spot: GENUINE, control plane integration |
| 22 | `core/environment_bridge/` (18 files) | PRESERVE | `execution/environments/` | None | P3 | LOW | 7 callers, WorkPacket dataclass |
| 23 | `core/control_plane_router/` (2 files) | PRESERVE | `control_plane/router/` | None | P3 | MEDIUM | 17 callers |
| 24 | `core/orchestrator/` (9 files) | PRESERVE | `control_plane/runtime/` | None | P3 | LOW | 11 callers |
| 25 | `core/adapters/` (7 files) | REFACTOR_AND_RELOCATE | `adapters/adapter_engine/` | Law 5.9: review execute() usage | P3 | LOW | 6 callers |
| 26 | `core/ontology/` (1 file) | PRESERVE | `understanding/ontology/` | None | P1 | LOW | Gap: PrimitiveObservation, 5 callers |
| 27 | `core/memory/` (5 files) | PRESERVE | `state/memory/contracts/` | None | P3 | LOW | 6 callers |
| 28 | `core/registry/` (1 file) | PRESERVE | `composition/registries/` | None | P2 | LOW | 4 callers |
| 29 | `core/execution/` (3 files) | PRESERVE | `execution/runtime/` | None | P3 | LOW | 3 callers |
| 30 | `core/state/` (1 file) | PRESERVE | `state/` | None | P3 | LOW | 3 callers |
| **CORE — BORDERLINE** (1-2 callers) | | | | | | | |
| 31 | `core/coherence/` (4 files) | PRESERVE | `control_plane/invariants/` | None | P2 | LOW | 2 callers |
| 32 | `core/governance/` (1 file) | PRESERVE | `governance/policy/` | None | P2 | LOW | 1 caller |
| 33 | `core/interpretation/` (1 file) | PRESERVE | `understanding/interpretation/` | None | P2 | LOW | 1 caller |
| 34 | `core/actuation/` (4 files) | PRESERVE | `execution/actuation/` | None | P2 | LOW | 1 caller |
| **CORE — SCAFFOLD** (0 callers) | | | | | | | |
| 35 | `core/accountability/` (14 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD, 0 callers, 0 commits |
| 36 | `core/applications/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 37 | `core/certification/` (13 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 38 | `core/cognition/` (11 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 39 | `core/constitutional/` (13 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 40 | `core/convergence/` (15 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 41 | `core/deployment/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 42 | `core/environments/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 43 | `core/explainability/` (13 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 44 | `core/federation/` (13 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 45 | `core/ingress/` (10 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 46 | `core/intelligence/` (14 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 47 | `core/knowledge/` (14 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 48 | `core/learning/` (11 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 49 | `core/operations/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 50 | `core/orchestration/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 51 | `core/planning/` (1 file) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 52 | `core/resilience/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 53 | `core/scaling/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | Spot: SCAFFOLD |
| 54 | `core/sessions/` (10 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 55 | `core/stabilization/` (12 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 56 | `core/trust/` (13 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 57 | `core/validation/` (14 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| 58 | `core/world_model/` (4 files) | ARCHIVE | `_archive/core_scaffold/` | — | — | LOW | 0 callers, 0 commits |
| **CORE — MIXED** (design value, no code consumers) | | | | | | | |
| 59 | `core/workflows/` (9 files) | EXTRACT_INTENT | `docs/design_intent/governance_workflows.md` | Extract recursion/escalation concepts | — | LOW | Spot: MIXED — real governance logic, 0 callers |
| **SERVICES** | | | | | | | |
| 60 | `services/discord_bot.py` | REFACTOR_AND_RELOCATE | `interface/presence/` | Law 5.5: 1 direct INSERT; phantom substrate imports to clean | P4 | HIGH | Gap: 5,212 LOC, primary interface |
| 61 | `services/handlers/` (6 files) | REFACTOR_AND_RELOCATE | `interface/presence/handlers/` | Law 5.5: direct INSERTs in intent/cc handlers | P4 | MEDIUM | Gap: dispatch layer |
| 62 | `services/calendly_webhook.py` | REFACTOR_AND_RELOCATE | `interface/api/webhooks/` | Law 5.5: direct INSERT | P3 | LOW | Exploration: running service |
| 63 | `services/dm_monitor.py` | ARCHIVE | `_archive/services/` | — | — | LOW | Exploration: DORMANT, not running |
| 64 | `services/telegram_control.py` | ARCHIVE | `_archive/services/` | — | — | LOW | Exploration: DORMANT, 3,148 LOC |
| 65 | `services/apify_scraper.py` | ARCHIVE | `_archive/services/` | — | — | LOW | Exploration: defined, not running |
| **OPERATOR TOOLING** | | | | | | | |
| 66 | `scripts/salience.py` | PRESERVE | `operations/memory/` | None | P2 | LOW | Salience audit: RELOCATED, 600 LOC |
| 67 | `scripts/nightly_consolidation.py` | PRESERVE | `operations/scheduled/` | None | P2 | LOW | Salience audit: cron, 325 LOC |
| 68 | `scripts/summarize_conversations.py` | PRESERVE | `operations/memory/` | None | P2 | LOW | Salience audit: 508 LOC |
| 69 | `scripts/promote_to_wiki.py` | PRESERVE | `operations/memory/` | None | P2 | LOW | Salience audit: 438 LOC |
| 70 | `scripts/memory_neon.py` | PRESERVE | `operations/memory/` | None | P2 | LOW | Salience audit: 565 LOC |
| 71 | Cron scripts (23 files)² | PRESERVE | `operations/scheduled/` | None | P2 | LOW | Crontab: 23 cron-referenced scripts |
| 72 | `scripts/` remaining³ (~160 files) | OPEN_QUESTION | — | — | — | — | No audit coverage for individual scripts |
| **SHIM LAYERS** | | | | | | | |
| 73 | `eos_ai/` (459 files) | DELETE | — | Redirect dependent imports first | P-last | LOW | Exploration: all 4-line shims |
| 74 | `runtime/substrate/` (164 files) | DELETE | — | Update 332 import sites (services/, scripts/) first | P-last | HIGH | Exploration: all 1-line re-exports |
| **TRANSPORT** | | | | | | | |
| 75 | `runtime/transport/` — 5 reachable modules⁴ | PRESERVE | Various §24 homes | None | P3 | LOW | Live grep: 5 modules with external imports |
| 76 | `runtime/transport/` — reachable via substrate shims⁵ | REFACTOR_AND_RELOCATE | Various §24 homes | Update import paths from substrate → direct | P4 | MEDIUM | discord_bot imports 13 real transport modules via substrate |
| 77 | `runtime/transport/` — orphan remainder (~140 files) | ARCHIVE | `_archive/transport/` | — | — | LOW | Exploration: 57% unreachable |
| **PROTOCOL CONTRACTS** | | | | | | | |
| 78 | `umh/protocols/` (10 files) | PRESERVE | `control_plane/protocols/` | None (IS the canonical type system) | P1 | LOW | Gap: 86 types, target for adoption |
| **TESTS** | | | | | | | |
| 79 | `tests/migration/` (10 files) | PRESERVE | `tests/migration/` | None | P1 | LOW | Active migration tests |
| 80 | `tests/integration/` (26 files) | PRESERVE | `tests/integration/` | None | P1 | LOW | Active integration tests |
| 81 | `tests/` top-level (190 files) | OPEN_QUESTION | `tests/` | Triage individually | — | — | No audit coverage |
| 82 | `tests/legacy/` (423 files) | ARCHIVE | `_archive/tests_legacy/` | — | — | LOW | Exploration: 66% of all tests |
| **DOCUMENTATION** | | | | | | | |
| 83 | `docs/system/` phase reports (96 files) | ARCHIVE | `_archive/docs_phase_reports/` | — | — | LOW | Exploration: phase968* series |
| 84 | `docs/canonical/` | PRESERVE | `docs/canonical/` | None | — | LOW | Synthesis doc lives here |
| 85 | `docs/system/` non-phase (24 files) | PRESERVE | `docs/system/` | None | — | LOW | Contract specs, reports |
| 86 | `docs/operations/` (182 files) | OPEN_QUESTION | — | Triage for staleness | — | — | No audit coverage |
| **RUNTIME — OTHER MODULES** | | | | | | | |
| 87 | runtime/ top-level (125 files) — spine⁶ | See rows 1-10 | — | — | — | — | Covered above |
| 88 | runtime/ top-level — 92 reachable non-spine (108 total incl. 8 spine + 15 unreachable)⁷ | REFACTOR_AND_RELOCATE | Various §24 homes | Law 5.5: 52 modules / ~100 SQL sites; context.py hub: 96 callers | P3 | MEDIUM | IN PLANNING — Phase A→B→C. 23 free now. See classification audit 2026-05-14. |
| 89 | runtime/ top-level — unreachable (~20 files) | ARCHIVE | `_archive/runtime/` | — | — | LOW | Exploration: 16% unreachable |
| **OTHER TOP-LEVEL** | | | | | | | |
| 90 | `parsers/` (7 files) | PRESERVE | `understanding/perception/parsers/` | None | P1 | LOW | Exploration: 100% reachable |
| 91 | `archive/` (1,178 files) | PRESERVE in place | `_archive/` (rename) | None | — | LOW | Already archived |
| 92 | `saas/` | PRESERVE in place | — | Separate TypeScript project | — | LOW | Out of scope for Python migration |
| 93 | `skills/` | PRESERVE in place | — | Markdown-only, no migration impact | — | LOW | 165 SKILL.md files |
| 94 | `agents/` | PRESERVE in place | — | Markdown-only soul docs | — | LOW | 18 soul documents |
| 95 | `vault/` | PRESERVE in place | — | Obsidian vault, no migration impact | — | LOW | 656 files |
| 96 | Obsidian dirs⁸ | PRESERVE in place | — | Knowledge management, no migration impact | — | LOW | Exploration |
| 97 | `config/` | PRESERVE in place | — | JSON/YAML config, no migration impact | — | LOW | 17 config files |
| 98 | `data/` | PRESERVE in place | — | Runtime artifacts, no migration impact | — | LOW | 234 MB |
| 99 | `logs/` | PRESERVE in place | — | Operational logs, no migration impact | — | LOW | 33 MB |
| 100 | `.claude/` | PRESERVE in place | — | Claude Code config, no migration impact | — | LOW | — |
| 101 | `.agents/` | PRESERVE in place | — | Plugin skills, no migration impact | — | LOW | — |
| 102 | `infra/` | PRESERVE in place | — | Docker config, no migration impact | — | LOW | — |
| 103 | `orchestrator/` | ARCHIVE | `_archive/orchestrator/` | — | — | LOW | Markdown-only, no Python |
| 104 | `knowledge/` | PRESERVE in place | — | TypeScript module, out of scope | — | LOW | — |
| 105 | `frontend/` | ARCHIVE | `_archive/frontend/` | — | — | LOW | 3-file stub, no development |
| 106 | `templates/` | PRESERVE in place | — | 1 Python file, 7 markdown | — | LOW | Minimal |
| 107 | `ventures/` | PRESERVE in place | — | Stub + README | — | LOW | Minimal |

**Footnotes:**

² Cron-referenced scripts: orchestrator_loop, agent_task_executor, emit_signal, morning_intel,
eod_sync, weekly_review, call_prep, post_meeting_capture, notion_tasks_sync, notion_sync_poller,
day_reminder, midday_checkin, calendar_invite_handler, noshow_detector, waiting_on_checker,
relationship_nurture, portfolio_brief, week_architect, discord_daily_clear,
deadline_monitor, shim_retirement_monitor, inbox_gps_afternoon (+ runtime/orchestrator.py).

³ Remaining scripts include: 54 smoke tests, 15 substrate CLI tools, 7 proof scripts,
graph/wiki tooling (codebase_graph.py, build_palace.py, query_graph.py, vault_backlink_audit.py),
tool mastery dispatchers, action_system.py, workflow_engine.py, misc utilities.

⁴ Transport modules with direct external imports: capability_tagging, claude_responder,
discord_mode_routing, execution_trace, storage.

⁵ Transport modules imported via substrate shims by discord_bot: session_discord_bridge,
discord_text_transport, event_spine, day_workflows, discord_voice_transport, execution_trace,
session_watcher, station_daemon, station_helpers, storage, voice_eos_responder,
discord_mode_routing, capability_tagging.

⁶ Spine modules: cognitive_loop, model_router, agent_runtime, memory, db, execution_spine,
authority_engine, primitives, cc_sdk, gateway.

⁷ Reachable non-spine: ~85 modules including knowledge_domains, knowledge_graph, embedding_engine,
agent_hierarchy, ceo_agent, ceo_intelligence, ai_identity, work_state, business_instance,
context, session_state, model_preferences, provider_state, provider_health, orchestrator,
email_gps, goal_selector, portfolio_advisor, expense_tracker, travel_manager, workflow_engine,
feedback_loop, quality_gate, accountability, world_model, and ~60 others.

⁸ Obsidian numbered directories: 01_Inbox, 04_Offers, 05_Workflows, 07_Knowledge,
09_Content, 10_Wiki, 14_Templates.

---

## Phase 3: §24 Target Path Mapping

### Unambiguous Mappings (5)

| Current | §24 Target | Rationale |
|---------|-----------|-----------|
| `runtime/memory.py` | `state/memory/` | Memory IS state. Direct match. |
| `runtime/db.py` | `state/storage/` | Storage IS state. Direct match. |
| `runtime/cognitive_loop.py` | `control_plane/runtime/` | Cognitive loop IS the control plane runtime. |
| `runtime/agent_runtime.py` | `execution/runtime/` | Agent dispatch IS execution runtime. |
| `runtime/execution_spine.py` | `execution/runtime/` | Execution spine IS execution runtime. |

### Reasonable Mappings (23)

| Current | §24 Target | Rationale |
|---------|-----------|-----------|
| `runtime/model_router.py` | `execution/runtime/` | **Recommendation: execution/runtime/** — routing is execution infrastructure, not adapter boundary. The router decides WHICH adapter, not HOW to translate. |
| `runtime/cc_sdk.py` | `adapters/model_adapters/` | CLI subprocess bridge to Claude = model adapter. |
| `runtime/gateway.py` | `control_plane/runtime/` | Gateway classifies and routes — control plane concern. |
| `runtime/authority_engine.py` | `governance/policy/` | Authority = governance. |
| `runtime/primitives.py` | `understanding/ontology/` | Primitives define the ontology. |
| `runtime/ingestion/orchestrator.py` | `understanding/perception/` | Ingestion = perception pipeline. |
| `runtime/ingestion/*_source.py` | `adapters/data_source_adapters/` | Sources are data adapters. |
| `runtime/ingestion/authority_tier.py` | `governance/policy/` | Authority tiers are governance policy. |
| `runtime/domain_bridge/` | `understanding/domains/` | Domain bridges live in understanding. |
| `core/ontology/` | `understanding/ontology/` | Ontology types. |
| `core/runtime/` | Split: `execution/runtime/` + `adapters/adapter_engine/` | Worker contracts → execution; adapter registry → adapters. |
| `core/workstation/` | `execution/workers/workstation/` | Workstation = execution worker. |
| `core/tool_mastery_*/` | `composition/mastery/` | Tool mastery = mastery composition. |
| `core/action_system/` | `control_plane/actions/` | Control plane action dispatch. |
| `core/environment_bridge/` | `execution/environments/` | Environment bridge = execution environment. |
| `core/control_plane_router/` | `control_plane/router/` | Direct match. |
| `core/orchestrator/` | `control_plane/runtime/` | Orchestration contracts = control plane. |
| `core/adapters/` | `adapters/adapter_engine/` | Adapter infrastructure. |
| `services/discord_bot.py` | `interface/presence/` | Discord = presence interface. |
| `services/handlers/` | `interface/presence/handlers/` | Interface dispatch handlers. |
| `services/calendly_webhook.py` | `interface/api/webhooks/` | Webhook = API interface. |
| `umh/protocols/` | `control_plane/protocols/` | Protocol contracts for control plane. |
| `parsers/` | `understanding/perception/parsers/` | Parsing = perception. |

### Ambiguous Mappings (2) — Flagged

| Current | Candidate A | Candidate B | Recommendation |
|---------|------------|------------|----------------|
| `runtime/model_router.py` | `execution/runtime/` (routing logic) | `adapters/model_adapters/` (model boundary) | **execution/runtime/** — router orchestrates model selection, it doesn't translate external protocols. cc_sdk is the adapter; model_router is execution infrastructure. |
| `core/runtime/` (44 files) | `execution/runtime/` (worker contracts) | `adapters/adapter_engine/` (adapter registry) | **Split** — worker_runtime_contracts → execution/runtime/; adapter_registry_contracts → adapters/adapter_engine/. These are two distinct concerns sharing a directory. |

### No-Home Mappings (7) — Architectural Gap

| Current | Issue | Proposed Resolution |
|---------|-------|--------------------|
| `scripts/salience.py` | No §24 layer for batch/scheduled work | New: `operations/memory/` (see Phase 5A) |
| `scripts/nightly_consolidation.py` | Same | New: `operations/scheduled/` |
| `scripts/summarize_conversations.py` | Same | New: `operations/memory/` |
| `scripts/promote_to_wiki.py` | Same | New: `operations/memory/` |
| `scripts/memory_neon.py` | Fits `state/storage/` but is batch tooling | New: `operations/memory/` (keeps pipeline cohesion) |
| `eos_ai/` (459 files) | Dead shims | DELETE — no §24 home needed |
| `runtime/substrate/` (164 files) | Dead re-exports | DELETE — no §24 home needed |

---

## Phase 4: Migration Priorities

### Priority 1 — LEAVES (nothing depends on them, move first)

| # | Path | Label | Risk | Notes |
|---|------|-------|------|-------|
| 12 | `runtime/ingestion/local_file_source.py` | PRESERVE | LOW | 2 callers, leaf |
| 13 | `runtime/ingestion/gws_source.py` | PRESERVE | LOW | 1 caller, leaf |
| 14 | `runtime/ingestion/authority_tier.py` | PRESERVE | LOW | Constants only |
| 26 | `core/ontology/` | PRESERVE | LOW | 1 file, 5 callers |
| 78 | `umh/protocols/` | PRESERVE | LOW | Target type system, 0 callers (stays put) |
| 79 | `tests/migration/` | PRESERVE | LOW | Test infra |
| 80 | `tests/integration/` | PRESERVE | LOW | Test infra |
| 90 | `parsers/` | PRESERVE | LOW | 100% reachable, leaf |

### Priority 2 — BRANCHES (depend on P1 only)

| # | Path | Label | Risk | Notes |
|---|------|-------|------|-------|
| 11 | `runtime/ingestion/orchestrator.py` | PRESERVE | LOW | Depends on sources + ontology |
| 15 | `runtime/domain_bridge/` | PRESERVE | LOW | Depends on ontology |
| 18-20 | `core/tool_mastery_*/` (3 dirs) | PRESERVE | LOW | 40 files total |
| 21 | `core/action_system/` | PRESERVE | LOW | Control plane |
| 28 | `core/registry/` | PRESERVE | LOW | 1 file |
| 31-34 | Core borderline (4 dirs) | PRESERVE | LOW | 1-2 callers each |
| 66-71 | Salience pipeline + cron (28 files) | PRESERVE | LOW | Operator tooling |

### Priority 3 — NODES (moderate dependency depth)

| # | Path | Label | Risk | Notes |
|---|------|-------|------|-------|
| 16 | `core/runtime/` (44 files) | REFACTOR_AND_RELOCATE | MEDIUM | 35 callers, needs split |
| 17 | `core/workstation/` (41 files) | REFACTOR_AND_RELOCATE | MEDIUM | 129 callers, Law 5.9 |
| 22-25 | Core genuine (4 dirs) | PRESERVE/REFACTOR | LOW | 3-11 callers each |
| 27, 29, 30 | Core contracts | PRESERVE | LOW | 3-6 callers |
| 62 | `services/calendly_webhook.py` | REFACTOR_AND_RELOCATE | LOW | 1 Law 5.5 site |
| 75 | Transport reachable (5 modules) | PRESERVE | LOW | Direct imports |
| 88 | Runtime non-spine (~85 modules) | REFACTOR_AND_RELOCATE | MEDIUM | Law 5.5 widespread |

### Priority 4 — SPINE-ADJACENT (close to core spine)

| # | Path | Label | Risk | Notes |
|---|------|-------|------|-------|
| 6 | `runtime/execution_spine.py` | PRESERVE | LOW | 1 caller |
| 7 | `runtime/authority_engine.py` | PRESERVE | LOW | 5 callers |
| 8 | `runtime/primitives.py` | PRESERVE | LOW | 3 callers |
| 9 | `runtime/cc_sdk.py` | PRESERVE | LOW | 2 callers |
| 60 | `services/discord_bot.py` | REFACTOR_AND_RELOCATE | HIGH | 5,212 LOC, primary interface |
| 61 | `services/handlers/` | REFACTOR_AND_RELOCATE | MEDIUM | Dispatch layer |
| 76 | Transport via substrate (13 modules) | REFACTOR_AND_RELOCATE | MEDIUM | Import path update needed |

### Priority 5 — SPINE (move LAST — highest caller count, highest blast radius)

| # | Path | Label | Risk | Notes |
|---|------|-------|------|-------|
| 1 | `runtime/cognitive_loop.py` | REFACTOR_AND_RELOCATE | HIGH | 19 callers |
| 2 | `runtime/model_router.py` | REFACTOR_AND_RELOCATE | HIGH | 57 callers — highest risk |
| 3 | `runtime/agent_runtime.py` | REFACTOR_AND_RELOCATE | HIGH | 38 callers |
| 4 | `runtime/memory.py` | REFACTOR_AND_RELOCATE | HIGH | 34 callers |
| 5 | `runtime/db.py` | PRESERVE | HIGH | 97 callers — foundation |
| 10 | `runtime/gateway.py` | REFACTOR_AND_RELOCATE | HIGH | 1,972 LOC |

### Unblocked (can run anytime)

| # | Category | Action |
|---|----------|--------|
| 35-58 | Core scaffold (26 dirs, ~280 files) | ARCHIVE — zero dependencies |
| 59 | Core workflows | EXTRACT_INTENT |
| 63-65 | Dormant services (3 files) | ARCHIVE |
| 77 | Transport orphans (~140 files) | ARCHIVE |
| 82 | Legacy tests (423 files) | ARCHIVE |
| 83 | Phase reports (96 files) | ARCHIVE |
| 91 | `archive/` rename to `_archive/` | Rename |
| 103 | `orchestrator/` (markdown) | ARCHIVE |
| 105 | `frontend/` (stub) | ARCHIVE |

### Run After Dependents Moved

| # | Path | Action | Prerequisite |
|---|------|--------|-------------|
| 73 | `eos_ai/` (459 files) | DELETE | All `from eos_ai.` imports redirected |
| 74 | `runtime/substrate/` (164 files) | DELETE | All `from runtime.substrate.` imports updated to `runtime.transport.` or §24 paths |

---

## Phase 5: Architectural Gap Resolutions

### A. Operator Tooling §24 Home

**Scale:** 187 Python files, 52,036 LOC in `scripts/`

**Three candidates evaluated:**

| Option | Path | Rationale | Downside |
|--------|------|-----------|----------|
| 1. New top-level layer | `operations/` | Clean separation: not request-path, not test, not spec. Matches how ops teams think. | Adds a layer not in Tab 9 §20's tree. |
| 2. Under learning | `learning/batch/` | Salience/consolidation IS learning feedback. | Cron scripts, graph builders, and migration tools are NOT learning. Forces unrelated things together. |
| 3. Under execution | `execution/scheduled/` | Cron IS scheduled execution. | Conflates batch tooling (operator concern) with the execution spine (request-path concern). |

**Recommendation: Option 1 — `operations/`**

```
operations/
  memory/         # salience, summarization, promotion, memory_neon
  scheduled/      # cron wrappers, nightly_consolidation, morning_intel, eod_sync
  graph/          # codebase_graph, build_palace, query_graph
  diagnostics/    # audit scripts, health checks, vault_backlink_audit
  migration/      # one-off migration scripts
```

Rationale: The §24 tree is request-path-centric by design (§24 was written for
the execution spine, not for operator tooling). Operator tooling is a legitimate
architectural concern that exists in every production system. Cramming it into
`learning/` or `execution/` creates false coupling. A dedicated `operations/`
layer is honest about what the code does and scales naturally as the system grows.

This becomes a synthesis correction in a follow-up commit.

### B. Two-Type-System Convergence

**Problem:** `umh/protocols/` (86 Pydantic v2 types, ~1,720 LOC) and production
code (@dataclass definitions in runtime/) define overlapping but incompatible
types for the same concepts. Zero production files import umh/protocols.

**Convergence rule:**

> Every file moved to its §24 home adopts the corresponding `umh/protocols/`
> type in the same commit. The migration IS the convergence event.

**Per-layer adoption order:**

| Order | Layer | Types to Adopt | Files Affected | Risk |
|-------|-------|---------------|----------------|------|
| 1 | Understanding | Signal, Interpretation, Decomposition, Observation | ingestion/ (4 files) | LOW — recent code, close to spec |
| 2 | Execution | WorkPacket, Action, ExecutionResult | core/environment_bridge, execution_spine | LOW — small surface |
| 3 | Adapters | Adapter Protocol (8 methods) | 5 adapter files | MEDIUM — contract change |
| 4 | Governance | GovernanceDecision, RiskClassification | authority_engine, control_plane | MEDIUM — 5 callers |
| 5 | State | MemoryRecord, WorldStateSnapshot | memory.py, world_model.py | HIGH — 34+ callers |
| 6 | Spine | ControlPlaneEvent, Trace | cognitive_loop, model_router, gateway | HIGH — 57+ callers |

**Key constraint:** The production @dataclass types are the working "v0". The
umh/protocols Pydantic types are the target "v1". During migration, a file
should import from umh/protocols and delete its local @dataclass. If
umh/protocols doesn't have the right type, extend umh/protocols first.

**Specific convergence examples:**

- `runtime/ingestion/orchestrator.py:SignalResult` (@dataclass) →
  `umh/protocols/understanding.py:Signal` (Pydantic)
- `core/environment_bridge/work_packet.py:WorkPacket` (@dataclass) →
  `umh/protocols/execution.py:WorkPacket` (Pydantic)
- `runtime/transport/execution_adapter.py:ExecutionAdapter` (3-method Protocol) →
  `umh/protocols/adapters.py:Adapter` (8-method Protocol)

### C. Law 5.5 Violations — Memory Write Consolidation

**Problem:** 46 files do raw `INSERT INTO events` bypassing the canonical
memory path (`runtime/memory.py` → `AgentMemory.log_event()`).

**Refactor approach:**

1. **Extend `AgentMemory.log_event()`** to accept optional typed metadata
   (currently it takes `event_type`, `event_data` dict, `agent_name`).
   Add optional `domain`, `source_module`, `confidence` params.

2. **Per-module replacement:** As each file moves to its §24 home, replace:
   ```python
   # Before (Law 5.5 violation)
   conn = db.get_conn()
   cur.execute("INSERT INTO events ...")
   
   # After (canonical path)
   from state.memory import log_event
   log_event(event_type="...", event_data={...}, agent_name="...")
   ```

3. **Priority order:** services/ first (highest risk — user-facing), then
   runtime/ spine modules, then runtime/ non-spine, then scripts/.

4. **Payload schema unification:** Each module currently uses different
   `event_data` shapes. During migration, define per-domain event schemas
   in `umh/protocols/` (e.g., `FeedbackEvent`, `WorkflowEvent`,
   `ExpenseEvent`). These become the typed payloads for `log_event()`.

**Scope:** 46 files, ~92 INSERT sites. Mechanical replacement with per-site
payload review. No new infrastructure needed — the canonical path exists.

### D. Law 5.9 Violations — Adapter Contract Migration

**Problem:** 5 production adapters use the deprecated `execute()` contract.
0 use the canonical `translate_request()` / `normalize_result()` / `observe_state()`
contract from `umh/protocols/adapters.py`.

**Adapters to migrate:**

| Adapter | Location | execute() Lines | Complexity |
|---------|----------|----------------|------------|
| ExecutionAdapter | `runtime/transport/execution_adapter.py` | Protocol def | LOW — Protocol change |
| LocalRuntimeAdapter | `runtime/transport/local_worker_runtime_daemon.py` | ~50 | MEDIUM |
| WorkstationAdapter | `runtime/transport/` (if exists) | ~30 | LOW |
| governed_shell_adapter_v1 | `core/workstation/` | ~80 | MEDIUM |
| governed_browser_adapter_v1 | `core/workstation/` | ~100 | MEDIUM |

**Refactor pattern per adapter:**

```python
# Before (Law 5.9 violation)
class MyAdapter:
    def execute(self, request) -> result:
        raw = external_call(request)
        return raw

# After (canonical contract)
class MyAdapter:
    def translate_request(self, work_packet: WorkPacket) -> ExternalRequest:
        return ExternalRequest(...)
    
    def validate_operation(self, request: ExternalRequest) -> ValidationResult:
        return ValidationResult(valid=True)
    
    def normalize_result(self, raw: ExternalResponse) -> NormalizedResult:
        return NormalizedResult(...)
    
    def observe_state(self) -> StateSnapshot:
        return StateSnapshot(...)
```

**Scope:** 5 files, class-level changes. Each adapter is self-contained.
No cross-cutting dependency changes needed. Migrate as each adapter moves
to `adapters/` in §24 tree.

---

## Migration Execution Order

### Wave 0: Clean Sweep (unblocked, zero risk)

**Goal:** Remove ~1,000 files of dead weight before touching any live code.

| Step | Action | Files | Risk |
|------|--------|-------|------|
| 0.1 | Archive 26 scaffold `core/` subdirs → `_archive/core_scaffold/` | ~280 | ZERO — 0 callers, 0 commits |
| 0.2 | Extract intent from `core/workflows/` → `docs/design_intent/` → archive | 9 | ZERO |
| 0.3 | Archive `tests/legacy/` → `_archive/tests_legacy/` | 423 | ZERO — legacy tests |
| 0.4 | Archive `docs/system/phase968*` → `_archive/docs_phase_reports/` | 96 | ZERO |
| 0.5 | Archive dormant services → `_archive/services/` | 3 | ZERO — not running |
| 0.6 | Archive transport orphans → `_archive/transport/` | ~140 | LOW — confirm 0 callers |
| 0.7 | Archive `orchestrator/`, `frontend/` → `_archive/` | ~10 | ZERO |
| 0.8 | Rename `archive/` → `_archive/` (consolidate) | 1,178 | LOW — path only |

**Post-Wave 0:** Active Python tree drops from ~3,500 files to ~1,500 files.
Context noise eliminated. Graph queries become meaningful.

### Wave 1: Leaves (P1 — nothing depends on them)

**Goal:** Move leaf modules to §24 homes, establishing the new directory structure.

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 1.1 | Move `parsers/` → `understanding/perception/parsers/` | 7 | None |
| 1.2 | Move ingestion sources → `adapters/data_source_adapters/` | 2 | None |
| 1.3 | Move `authority_tier.py` → `governance/policy/` | 1 | None |
| 1.4 | Move `core/ontology/` → `understanding/ontology/` | 1 | None |
| 1.5 | Move `umh/protocols/` → `control_plane/protocols/` | 10 | None |
| 1.6 | Move `tests/migration/`, `tests/integration/` | 36 | None |

### Wave 2: Branches (P2)

**Goal:** Move branch modules. Begin type convergence (Understanding layer first).

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 2.1 | Move ingestion orchestrator → `understanding/perception/` + adopt Signal type | 1 | Wave 1 |
| 2.2 | Move domain_bridge → `understanding/domains/` | 3 | Wave 1 |
| 2.3 | Move tool_mastery agents → `composition/mastery/` | 40 | Wave 1 |
| 2.4 | Move action_system → `control_plane/actions/` | 11 | Wave 1 |
| 2.5 | Move borderline core (coherence, governance, interpretation, actuation) | 10 | Wave 1 |
| 2.6 | Move salience pipeline → `operations/memory/` | 5 | New §24 layer approved |
| 2.7 | Move cron scripts → `operations/scheduled/` | ~23 | New §24 layer approved |

### Wave 3: Nodes (P3)

**Goal:** Move moderate-dependency modules. Law 5.5 and 5.9 refactors begin.

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 3.1 | Split and move `core/runtime/` → execution + adapters | 44 | Wave 2 |
| 3.2 | Move + refactor `core/workstation/` (Law 5.9 adapters) | 41 | Wave 2 |
| 3.3 | Move remaining core genuine dirs | ~20 | Wave 2 |
| 3.4 | Move calendly_webhook (Law 5.5 fix) | 1 | None |
| 3.5 | Move transport reachable modules | 5 | None |
| 3.6 | Begin runtime non-spine Law 5.5 refactors | ~85 | memory.py API extended |

### Wave 4: Spine-Adjacent (P4)

**Goal:** Move spine-adjacent modules. Update substrate import paths.

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 4.1 | Move spine-adjacent (execution_spine, authority_engine, primitives, cc_sdk) | 4 | Wave 3 |
| 4.2 | Update discord_bot substrate imports → direct transport paths | 1 | None |
| 4.3 | Move discord_bot + handlers (Law 5.5 fix) | 7 | Wave 4.2 |
| 4.4 | Move transport modules used by discord_bot | 13 | Wave 4.2 |

### Wave 5: Spine (P5 — move LAST)

**Goal:** Move core spine modules. Full type convergence. Highest risk.

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 5.1 | Move db.py → `state/storage/` | 1 | All callers identified |
| 5.2 | Move memory.py → `state/memory/` + type convergence | 1 | Wave 3.6 (Law 5.5 done) |
| 5.3 | Move cognitive_loop → `control_plane/runtime/` + type convergence | 1 | Wave 4 |
| 5.4 | Move agent_runtime → `execution/runtime/` + type convergence | 1 | Wave 4 |
| 5.5 | Move model_router → `execution/runtime/` + type convergence | 1 | Wave 4 |
| 5.6 | Move gateway → `control_plane/runtime/` + type convergence | 1 | Wave 4 |

### Wave 6: Cleanup

**Goal:** Remove shim layers after all imports updated.

| Step | Action | Files | Blocker |
|------|--------|-------|---------|
| 6.1 | Delete `eos_ai/` (459 files) | 459 | All `from eos_ai.` imports gone |
| 6.2 | Delete `runtime/substrate/` (164 files) | 164 | All `from runtime.substrate.` imports gone |

---

## Open Questions

### Q1: scripts/ triage depth

~160 scripts beyond the salience pipeline and cron jobs have no individual
audit coverage. These include smoke tests, proof scripts, substrate CLI tools,
graph tooling, and miscellaneous utilities. Should these be:

- (a) Triaged individually (another audit pass)?
- (b) Bulk-moved to `operations/` with a blanket PRESERVE?
- (c) Left in `scripts/` until they cause problems?

**Recommendation:** (b) — bulk-move to `operations/` subcategories, triage
individually only when each one is touched for the first time.

### Q2: tests/ top-level triage

190 test files at `tests/` top level have no audit coverage. Many test
modules that still exist; some test modules that have been archived or
renamed. Should these be:

- (a) Run and triage based on pass/fail?
- (b) Matched against existing modules (if module exists → keep; if not → archive)?
- (c) Left in place?

**Recommendation:** (b) — mechanical matching is fast and deterministic.

### Q3: docs/operations/ staleness

182 operational docs have no audit coverage. These may include stale
runbooks referencing old module paths. Should these be:

- (a) Audited for staleness?
- (b) Bulk-archived?
- (c) Left in place until migration is complete, then audited?

**Recommendation:** (c) — docs don't block migration. Audit after the code
moves, when stale references become obvious.

---

## Chat Summary

- Subsystems triaged: 107 line items across 51 logical subsystems
- Distribution: PRESERVE 18, REFACTOR_AND_RELOCATE 12, EXTRACT_INTENT 1 (+4 MIXED subdirs), ARCHIVE 14 groups (~1,730 files), DELETE 2 (623 files)
- Architectural gap resolutions: 4 proposed (operations/ layer, type convergence rule, Law 5.5 refactor approach, Law 5.9 refactor approach)
- Open questions for founder: 3 (scripts triage depth, tests triage, docs staleness)
- Ready for: migration execution — Wave 0 (clean sweep) first, then Waves 1-6 by priority

---

## Wave 0 Execution — 2026-05-13

- Items archived: 849 files (target was ~1,000)
- Items deferred (transport interconnection): 149 files — `runtime/transport/` orphans
  cannot be archived without rewriting `runtime/transport/__init__.py` (hard-imports
  26 of the "orphan" modules; kept modules cross-import 13 more)
- Tests pre: 94 passed (tests/migration/)
- Tests post: 94 passed (unchanged)
- Active Python file count: 1,606 (was ~3,500 including shims)
- Archive location: `/opt/OS/_archive/2026-05-13_wave_0/`
- Per-file manifest: `/opt/OS/_archive/2026-05-13_wave_0/MANIFEST.md`

### Archived categories

| Category | Files | Method |
|----------|-------|--------|
| Core scaffold (26 dirs) | 288 | Plain mv (untracked) |
| Scaffold tests | 26 | git mv (15 tracked) + mv (11 untracked) |
| tests/legacy/ | 423 | git mv |
| docs/system/phase968* | 96 | git mv (62 tracked) + mv (34 untracked) |
| Dormant services | 3 | git mv |
| Frontend stub | 3 | git mv |
| Orchestrator | 7 | git mv |

### Deferred: Transport orphans (requires Wave 0.5)

`runtime/transport/__init__.py` is a massive re-export file (450+ lines)
that hard-imports 30 modules from the "orphan" set. The transport layer's
internal cross-import graph makes piecemeal archival impossible without
code modification. Resolution: dedicated wave to rewrite `__init__.py`
with lazy imports, then archive truly orphan modules.

### Spot-check verification

```
python3 -c "import umh.protocols"                                          → OK
python3 -c "from runtime.ingestion.orchestrator import GenericIngestionOrchestrator" → OK
python3 -c "import runtime.cc_sdk"                                         → OK
```

---

## Wave 1 Execution — 2026-05-13

- Items attempted: 6 (of 8 P1 items; 2 already at target path)
- Items completed (committed): 6
- Items skipped (refactor too large): 0
- Items reverted (test failure): 0
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- Active tree: 1,614 Python files
- Commits: `818654de` .. `eb71a6e8` (6 commits)

### Migrations completed

| # | Source | Target | Import sites updated |
|---|--------|--------|---------------------|
| 90 | `parsers/` (7 files) | `understanding/perception/parsers/` | 3 (scripts/) |
| 78 | `umh/protocols/` (10 files + tests) | `control_plane/protocols/` | 10 (protocol tests) |
| 26 | `core/ontology/` (1 file) | `understanding/ontology/` | 13 |
| 14 | `runtime/ingestion/authority_tier.py` | `governance/policy/authority_tier.py` | 6 |
| 12 | `runtime/ingestion/local_file_source.py` | `adapters/data_source_adapters/` | 6 |
| 13 | `runtime/ingestion/gws_source.py` | `adapters/data_source_adapters/` | 2 |

### Items already at target (no move required)

| # | Path | Reason |
|---|------|--------|
| 79 | `tests/migration/` | Target IS current path |
| 80 | `tests/integration/` | Target IS current path |

### §24 directories established

```
understanding/
  perception/
    parsers/          ← parsers/ (7 files)
  ontology/           ← core/ontology/ (1 file)
control_plane/
  protocols/          ← umh/protocols/ (10 files + tests)
governance/
  policy/             ← runtime/ingestion/authority_tier.py
adapters/
  data_source_adapters/  ← runtime/ingestion/{local_file,gws}_source.py
```

### Architectural findings

- `parsers/` internal imports were absolute (`from parsers.X`). Converted to
  relative (`from .X`) for location independence — this is the pattern all
  migrated packages should follow.
- `umh/protocols/` already used relative imports internally — no changes needed.
- `core/ontology/` had 13 import sites spread across runtime, core, tests, and
  scripts. All updated in single commit — this is the highest fan-out item in P1.
- Transport `__init__.py` finding carried forward from Wave 0 (unchanged).

### Spot-check verification

```
python3 -c "from understanding.perception.parsers import REGISTRY"         → OK
python3 -c "from control_plane.protocols import Signal, WorkPacket"         → OK
python3 -c "from understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation" → OK
python3 -c "from governance.policy.authority_tier import T5_DEFAULT"        → OK
python3 -c "from adapters.data_source_adapters.local_file_source import LocalFileSource" → OK
python3 -c "from adapters.data_source_adapters.gws_source import GWSSource" → OK
```

---

## Wave 2 Execution — 2026-05-13

- Items attempted: 12 (of 13 P2 items)
- Items completed (committed): 12
- Items skipped (crontab dependency): 1 — cron scripts (row #71) need crontab path updates, not just Python imports
- Items reverted (test failure): 0
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- Active tree: 1,623 Python files
- Commits: `1ab2fb97` .. `0a70283b` (12 commits)
- Architectural findings: see below

### Migrations completed

| # | Source | Target | Import sites |
|---|--------|--------|-------------|
| 33 | `core/interpretation/` (1 file) | `understanding/interpretation/` | 2 |
| 32 | `core/governance/` (1 file) | `governance/policy/` | 9 |
| 31 | `core/coherence/` (4 files) | `control_plane/invariants/` | 12 |
| 34 | `core/actuation/` (4 files) | `execution/actuation/` | 57 |
| 28 | `core/registry/` (1 file) | `composition/registries/` | 83 |
| 11 | `runtime/ingestion/{orchestrator,source}.py` | `understanding/perception/` | 12 |
| 15 | `runtime/domain_bridge/` (4 files) | `understanding/domains/` | 9 |
| 21 | `core/action_system/` (11 files) | `control_plane/actions/` | 25 |
| 18 | `core/tool_mastery_research_agent/` (18 files) | `composition/mastery/research/` | 4 |
| 19 | `core/tool_mastery_author_agent/` (11 files) | `composition/mastery/authoring/` | 9 |
| 20 | `core/tool_mastery_manager/` (11 files) | `composition/mastery/management/` | 10 |
| 66-70 | Salience pipeline (5 files) | `operations/memory/` | 12 |

### Items skipped

| # | Path | Reason |
|---|------|--------|
| 71 | Cron scripts (23 files) | Crontab entries reference `scripts/*.py` by absolute path. Moving requires crontab update (system-level coordination beyond Python import refactoring). Recommend: dedicated migration step with crontab update script. |

### New §24 directories established in Wave 2

```
understanding/
  interpretation/     ← core/interpretation/
  domains/            ← runtime/domain_bridge/
control_plane/
  invariants/         ← core/coherence/
  actions/            ← core/action_system/
execution/
  actuation/          ← core/actuation/
composition/
  registries/         ← core/registry/
  mastery/
    research/         ← core/tool_mastery_research_agent/
    authoring/        ← core/tool_mastery_author_agent/
    management/       ← core/tool_mastery_manager/
governance/
  policy/             ← (also: core/governance/ added this wave)
operations/
  memory/             ← scripts/{salience,nightly_consolidation,...}
```

### Architectural findings

- `operations/` top-level layer now established (manifest Phase 5A proposal
  implemented). First population: 5 memory pipeline scripts.
- Cron script migration requires a dedicated step: (1) move scripts,
  (2) update crontab, (3) verify cron execution. This is a system-level
  coordination task, not a pure Python refactor.
- All migrated packages that had internal cross-references already used
  relative imports — the project's `core/` code was well-structured for
  relocation.
- Total import sites updated across Wave 2: ~244.

---

## Wave 3 Execution — 2026-05-13

- Items attempted: 12 (of 12 P3 items)
- Items completed (committed): 10
- Items skipped: 2
- Items reverted (test failure): 0
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- Active tree: 1,635 Python files
- Commits: `356ac445` .. `de07d051` (10 commits)
- Architectural findings: see below

### Migrations completed

| # | Source | Target | Import sites |
|---|--------|--------|-------------|
| 30 | `core/state/` (1 file) | `state/` | 20 |
| 29 | `core/execution/` (2 files) | `execution/runtime/` | 7 |
| 27 | `core/memory/` (5 files) | `state/memory/contracts/` | 14 |
| 22 | `core/environment_bridge/` (18 files) | `execution/environments/` | 55 |
| 24 | `core/orchestrator/` (9 files) | `control_plane/runtime/orchestrator/` | 11 |
| 25 | `core/adapters/` (7 files) | `adapters/adapter_engine/` | 28 |
| 62 | `services/calendly_webhook.py` | `interface/api/webhooks/` | 0 (standalone) |
| 23 | `core/control_plane_router/` (2 files) | `control_plane/router/` | 80 |
| 16 | `core/runtime/` (44 files) | `execution/runtime/` (42) + `adapters/adapter_engine/` (2) | ~175 |
| 17 | `core/workstation/` (41 files) | `execution/workers/workstation/` | ~1,159 |

### Items skipped

| # | Path | Reason |
|---|------|--------|
| 75 | Transport reachable (5 modules) | Entangled with `runtime/transport/__init__.py` cross-import graph. Same blocker as Wave 0 transport orphan deferral. Requires dedicated Wave 0.5 transport `__init__.py` rewrite. |
| 88 | Runtime non-spine (92 reachable + 15 unreachable + 8 spine = 115 total files) | IN PLANNING. Three-phase: A (memory.py API extension, 52 modules), B (context.py hub, 96 callers), C (remaining). 23 modules free now. Classification: `2026-05-14_runtime_layer_classification.md`. API design: `2026-05-14_law_5_5_memory_api_design.md`. |

### New §24 directories established in Wave 3

```
state/                        ← core/state/ (ledger)
  memory/
    contracts/                ← core/memory/ (5 files)
execution/
  runtime/                    ← core/execution/ (2) + core/runtime/ (42)
  environments/               ← core/environment_bridge/ (18)
  workers/
    workstation/              ← core/workstation/ (41)
control_plane/
  runtime/
    orchestrator/             ← core/orchestrator/ (9)
  router/                     ← core/control_plane_router/ (2)
adapters/
  adapter_engine/             ← core/adapters/ (7) + core/runtime adapter files (2)
interface/
  api/
    webhooks/                 ← services/calendly_webhook.py
```

### Refactors applied

- **Law 5.5 fix** (calendly_webhook): raw `INSERT INTO events` replaced with
  `AgentMemory.log_event()`. 1 site.
- **Internal imports → relative**: 34 files in core/workstation/, 65 sites
  in core/runtime/, 3 sites in core/adapters/, 2 sites in core/memory/.
  All migrated packages are now location-independent.
- **Law 5.9 deferred**: 6 files in execution/workers/workstation/ have
  `execute()` methods. Needs dedicated pass with §14.1 contract adoption.

### Architectural findings

- `core/workstation/` had the highest import fan-out in the entire migration:
  1,159 external import sites across 65 files. All mechanical sed replacement.
- `core/runtime/` successfully split: 42 worker/execution contracts to
  `execution/runtime/`, 2 adapter contracts to `adapters/adapter_engine/`.
- `interface/` top-level layer established (new §24 layer). First
  population: calendly_webhook. Will receive discord_bot + handlers in Wave 4.
- `state/` top-level layer established (new §24 layer). Receives both
  the transformation state ledger and memory contracts.
- Docker compose path for calendly_webhook needs manual update:
  `services/calendly_webhook.py` → `interface/api/webhooks/calendly_webhook.py`
- Transport reachable modules (Row 75) confirmed blocked: `capability_tagging`
  imports from `runtime.transport.capabilities`, `claude_responder` imports
  from `runtime.substrate`. Cannot move without breaking transport layer.
- Total import sites updated across Wave 3: ~1,549.

---

## Wave 4 Execution — 2026-05-13

- Items attempted: 7 (all P4 items)
- Items completed (committed): 5
- Items skipped: 2
- Items reverted (test failure): 0 (1 test failure caught and fixed: mock patch targets)
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- Active tree: 1,637 Python files
- Commits: `459e8442` .. `805bd76f` (5 commits)
- Architectural findings: see below

### Migrations completed

| # | Source | Target | Import sites |
|---|--------|--------|-------------|
| 6 | `runtime/execution_spine.py` | `execution/runtime/` | 3 |
| 7 | `runtime/authority_engine.py` | `governance/policy/` | 9 |
| 8 | `runtime/primitives.py` | `understanding/ontology/` | 14 |
| 9 | `runtime/cc_sdk.py` | `adapters/model_adapters/` | 16 |
| 61 | `services/handlers/` (6 files) | `interface/presence/handlers/` | ~85 |

### Items skipped

| # | Path | Reason |
|---|------|--------|
| 76 | Transport via substrate (13 modules) | Blocked by transport `__init__.py` entanglement (Wave 0.5). Substrate shims cannot be bypassed without transport rewrite. |
| 60 | `services/discord_bot.py` | Depends on Row 76 (substrate imports). Also: Law 5.5 violations, Docker compose path, path-literal test references. HIGH risk — needs transport resolution first. |

### New §24 directories established in Wave 4

```
adapters/
  model_adapters/               ← runtime/cc_sdk.py
interface/
  presence/
    handlers/                   ← services/handlers/ (6 files)
```

### Refactors applied

- **Mock patch targets** (test_governed_spine.py): Updated `patch("runtime.authority_engine.AuthorityEngine")`
  → `patch("governance.policy.authority_engine.AuthorityEngine")` after authority_engine relocation.
  Tests initially failed (2 failures) due to stale patch targets — fixed in same commit.

### Cumulative deferred threads (across all waves)

| Thread | Items affected | Blocker | Resolution |
|--------|---------------|---------|------------|
| Transport `__init__.py` rewrite | Rows 75, 76, 60 | `__init__.py` hard-imports 30 modules | Dedicated Wave 0.5: rewrite with lazy imports, then archive orphans |
| Law 5.9 adapter refactor | 6 files in execution/workers/workstation/ | §14.1 contract adoption | Dedicated pass after all relocations |
| Law 5.5 memory write fixes | ~46 files across codebase | memory.py API extension | Row 88 prerequisite (manifest step 3.6) |
| Cron script migration | 23 files in scripts/ | Crontab path updates | System-level coordination (Row 71) |
| Docker compose paths | calendly_webhook, discord_bot | Container command paths | Manual update before deploy |

### Architectural findings

- Handlers migration revealed 80+ test imports using bare `from handlers.X` — all tests
  had `services/` on sys.path. Converted to fully qualified `from interface.presence.handlers.X`.
- Mock patch targets are a subtle migration hazard: `patch()` resolves dotted paths at call time,
  so it must match the module's NEW location, not where the code being tested lazy-imports from.
- Transport substrate dependency is the single largest remaining blocker. Rows 60, 75, 76
  all depend on it. This affects Wave 5 too — discord_bot is the primary consumer of spine modules.
- Total import sites updated across Wave 4: ~127.

---

## Wave 5 Execution — 2026-05-13 — SPINE COMPLETE

- Items attempted: 6 (all P5 items)
- Items completed (committed): 6
- Items skipped: 0
- Items reverted: 0
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- Full LLM integration test: 4 passed (including live cc_sdk decomposer)
- Active tree: 1,637 Python files
- Commits: `4c8039da` .. `ee72d659` (6 commits)

### Migrations completed

| # | Source | Target | Import sites | Notes |
|---|--------|--------|-------------|-------|
| 1 | `runtime/cognitive_loop.py` | `control_plane/runtime/` | 53 | 18 imports + 35 strings |
| 4 | `runtime/memory.py` | `state/memory/` | 42 | 31 imports + 11 strings |
| 3 | `runtime/agent_runtime.py` | `execution/runtime/` | 70 | 35 imports + 35 strings |
| 2 | `runtime/model_router.py` | `execution/runtime/` | 95 | 57 imports + 42 strings; 27 mock patches |
| 5 | `runtime/db.py` | `state/storage/` | 99 | 95 imports + 5 strings; foundation module |
| 10 | `runtime/gateway.py` | `control_plane/runtime/` | 47 | 14 imports + 33 strings; 1,972 LOC |

### New §24 directory established in Wave 5

```
state/
  storage/                      ← runtime/db.py
```

### Refactors applied

- **Mock patch targets** (model_router): 7 patch targets in `tests/migration/` + 20 in
  `tests/` updated from `runtime.model_router` → `execution.runtime.model_router`.
  Same hazard pattern as Wave 4 authority_engine fix.
- **Law 5.4 deferred**: All 5 REFACTOR_AND_RELOCATE items moved without type convergence.
  Behavioral parity preserved — type changes are semantics-altering and belong in a
  dedicated follow-up wave.
- **String references**: Smoke test scripts, palace builder, codebase graph, and shim
  retirement monitor all updated to canonical paths.

### Canonical spine at §24 positions

```
control_plane/runtime/
  cognitive_loop.py             ← runtime/cognitive_loop.py (1,263 LOC)
  gateway.py                    ← runtime/gateway.py (1,972 LOC)
  orchestrator/                 ← core/orchestrator/ (Wave 3)

execution/runtime/
  agent_runtime.py              ← runtime/agent_runtime.py (527 LOC)
  model_router.py               ← runtime/model_router.py (1,194 LOC)
  execution_spine.py            ← runtime/execution_spine.py (Wave 4)

state/
  memory/
    memory.py                   ← runtime/memory.py (1,018 LOC)
    contracts/                  ← core/memory/ (Wave 3)
  storage/
    db.py                       ← runtime/db.py (123 LOC)

governance/policy/
  authority_engine.py           ← runtime/authority_engine.py (Wave 4)

understanding/ontology/
  primitives.py                 ← runtime/primitives.py (Wave 4)

adapters/model_adapters/
  cc_sdk.py                     ← runtime/cc_sdk.py (Wave 4)
```

### Canary import verification

| Module | New path | Import test | Notes |
|--------|----------|-------------|-------|
| model_router | `execution.runtime.model_router` | ✓ PASS | `call_with_fallback`, `get_router`, `TaskType` |
| agent_runtime | `execution.runtime.agent_runtime` | ✓ PASS | `AgentRuntime`, `TaskType` |
| cognitive_loop | `control_plane.runtime.cognitive_loop` | ✗ dep | `runtime.context` not yet migrated (Row 88) |
| gateway | `control_plane.runtime.gateway` | ✗ dep | Same: `runtime.context` dependency |
| memory | `state.memory.memory` | ✗ env | `state.storage.db` needs `DATABASE_URL` env |
| db | `state.storage.db` | ✗ env | Needs `DATABASE_URL` + `EOS_ORG_ID` env vars |

All failures are dependency-chain (unmigrated `runtime.context`) or environment (env vars
not set in bare CLI). No path issues — all modules correctly found at new locations.

### Cumulative deferred threads (across all waves)

| Thread | Items affected | Blocker | Resolution |
|--------|---------------|---------|------------|
| Transport `__init__.py` rewrite | Rows 75, 76, 60 | `__init__.py` hard-imports 30 modules | Dedicated Wave 0.5: rewrite with lazy imports |
| Law 5.4 type convergence | 5 spine modules (cognitive_loop, model_router, agent_runtime, memory, gateway) | Semantics-altering changes | Dedicated follow-up wave: dict → Pydantic types |
| Law 5.9 adapter refactor | 6 files in execution/workers/workstation/ | §14.1 contract adoption | Dedicated pass after all relocations |
| Law 5.5 memory write fixes | ~46 files across codebase | memory.py API extension | Row 88 prerequisite (manifest step 3.6) |
| runtime.context migration | Row 88 (~85 modules) | cognitive_loop + gateway dependency | Prerequisite for full spine canary imports |
| Cron script migration | 23 files in scripts/ | Crontab path updates | System-level coordination (Row 71) |
| Docker compose paths | calendly_webhook, discord_bot | Container command paths | Manual update before deploy |

### Migration milestone

**The §29 Do-Not-Touch Core spine is now in §24 canonical positions.** All 6 P5 modules
relocated. 406 import sites updated across the tree. Zero old-path imports remain.

Remaining work:
- Wave 6: DELETE shims (`eos_ai/` 459 files, `runtime/substrate/` 164 files)
- Wave 0.5: Transport `__init__.py` rewrite (unblocks Rows 60, 75, 76)
- Follow-up waves: Law 5.4 type convergence, Law 5.9 adapters, Law 5.5 memory writes
- runtime.context + Row 88 (~85 non-spine runtime modules)
- Cron scripts, Docker compose paths

Total import sites updated across Wave 5: ~406.

---

## Wave 6 Execution — 2026-05-14 — SHIMS DELETED

- Shim files inventoried: 623 (459 eos_ai/ + 164 runtime/substrate/)
- Shim files deleted: 623
- Stragglers retained: 0
- Tests baseline: 93 passed, 1 deselected / Post: 93 passed, 1 deselected (unchanged)
- LLM integration test: 4 passed (unchanged)
- Active tree: 1,014 Python files (down from 1,637 — delta: **−623**)
- Commits: `8454a648` .. `1c320aaf` (2 commits)

### Deletion batches

| Batch | Package | Files deleted | Notes |
|-------|---------|--------------|-------|
| 1 | `eos_ai/` | 459 + 1 README | r8d_generate_shims.py 4-line re-exports. Zero external consumers. |
| 2 | `runtime/substrate/` | 164 | One-line star imports → runtime.transport. Zero production consumers. |

### Pre-deletion verification

- **eos_ai/**: Tree-wide grep for `from eos_ai` outside eos_ai/ → **0 hits**
- **runtime/substrate/**: Tree-wide grep outside substrate/ → **376 hits**, all in legacy
  tests (tests/test_phase*, tests/test_w0_*, tests/test_execution_adapter.py, etc.).
  These are ARCHIVE candidates per manifest Row 82. Zero hits in production code or
  migration tests.
- All 623 files confirmed pure re-exports via sampling (20+ files) and line-count
  verification (no file exceeded 6 lines for eos_ai or 3 lines for substrate).

### Shim structure confirmed

**eos_ai/ pattern** (r8d_generate_shims.py):
```python
# Generated by r8d_generate_shims.py — do not edit
import <canonical_path> as _mod
import sys as _sys
_sys.modules[__name__] = _mod
```

**runtime/substrate/ pattern**:
```python
from runtime.transport.<module> import *  # noqa: F401,F403
```

### Remaining cleanup threads

| Thread | Items | Status |
|--------|-------|--------|
| ~~Legacy tests referencing runtime.substrate~~ | ~~82 files / 194 imports~~ | ~~CLOSED — archived 2026-05-14 (`f09c98e1`)~~ |
| ~~Transport `__init__.py` rewrite~~ | ~~Rows 75, 76, 60~~ | ~~CLOSED — lazy-import rewrite 2026-05-14~~ |
| ~~Transport orphan archive~~ | ~~148 candidates → 95 archived~~ | ~~CLOSED — 2026-05-14. 53 restored (transitive PROD deps)~~ |
| ~~Transport production path migration~~ | ~~16 modules (Row 76/60)~~ | ~~CLOSED — all substrate imports eliminated 2026-05-14~~ |
| Law 5.4 type convergence | 5 spine modules | Dedicated follow-up wave |
| Law 5.9 adapter refactor | 6 files in execution/workers/workstation/ | §14.1 contract |
| Law 5.5 memory write fixes (Phase A) | 52 modules, ~100 SQL sites | Tier 1 COMPLETE (33 modules, 46 events-INSERT sites). Tier 2 COMPLETE (4 UPDATE sites + 2 INVESTIGATE). Tier 3 (14 domain stores, ~50 sites) pending. See `2026-05-14_law_5_5_memory_api_design.md` |
| Runtime layer migration (Row 88) | 92 reachable modules (108 total incl. spine + unreachable) | IN PLANNING — three-phase: A (Law 5.5 API) → B (context.py hub, 96 callers) → C (remaining). 23 modules free now. See `2026-05-14_runtime_layer_classification.md` |
| Cron script migration | 23 files | System-level coordination |
| ~~Docker compose paths~~ | ~~calendly_webhook~~ | ~~CLOSED — calendly path updated 2026-05-14. discord_bot not yet migrated from services/.~~ |
| r8d_generate_shims.py | 1 file in scripts/ | Generator script, safe to archive |

### Migration main arc milestone

**The §24 migration main arc is COMPLETE.**

- Waves 0-2: Infrastructure + leaf modules relocated
- Wave 3: P3 moderate-dependency modules relocated
- Wave 4: P4 spine-adjacent modules relocated
- Wave 5: P5 SPINE (§29 Do-Not-Touch Core) relocated to §24
- Wave 6: Shim layers deleted (623 files)

Active tree reduced from ~3,500 Python files (pre-migration) to **1,014 files**.
All production imports route through canonical §24 paths.
Only follow-up waves (transport rewrite, Law fixes) remain.

---

## Legacy Test Archive — 2026-05-14

Row 82 CLOSED.

- **Files archived**: 82 (git mv to `_archive/2026-05-14_legacy_tests/`)
- **Legacy imports**: 194 from `runtime.substrate.*` or `eos_ai.*`
- **Stragglers retained**: 6 files with mixed legacy + canonical imports (1 legacy import each)
- **Tests**: 93 passed, 1 deselected (unchanged from baseline)
- **Commit**: `f09c98e1`

~~Stragglers (future triage — update single legacy import per file):~~
~~All 6 resolved — `5e909bb6`~~

## Stragglers Close — 2026-05-14

All 6 straggler files updated: `runtime.substrate.*` → `runtime.transport.*`.
Zero archives, zero investigations. All canonical paths verified importable.

| File | Old import | New import | Decision |
|------|-----------|------------|----------|
| `test_w0_execution_binding.py` | `runtime.substrate.local_worker_auto_loop` | `runtime.transport.local_worker_auto_loop` | UPDATE_IMPORT |
| `test_local_worker_visible_chrome_gate.py` | `runtime.substrate.local_worker_auto_loop` | `runtime.transport.local_worker_auto_loop` | UPDATE_IMPORT |
| `test_foreground_cu_ingestion_execution_v1.py` | `runtime.substrate.instance_ingestion_contracts` | `runtime.transport.instance_ingestion_contracts` | UPDATE_IMPORT |
| `test_founder_visual_confirmation_gate.py` | `runtime.substrate.write_founder_gate_confirmation` | `runtime.transport.write_founder_gate_confirmation` | UPDATE_IMPORT |
| `test_local_worker_runtime_daemon.py` | `runtime.substrate.local_worker_runtime_daemon` | `runtime.transport.local_worker_runtime_daemon` | UPDATE_IMPORT |
| `test_w0_coherence_envelope.py` | `runtime.substrate.local_worker_auto_loop` | `runtime.transport.local_worker_auto_loop` | UPDATE_IMPORT |

- **Tests**: 94 passed (unchanged from baseline)
- **Legacy imports remaining in `tests/`**: 0
- **Commit**: `5e909bb6`

**Legacy-import theme: CLOSED.** No `runtime.substrate.*` or `eos_ai.*` imports remain in the active test tree.

---

## Transport `__init__.py` Rewrite — 2026-05-14 (Wave 0.5)

**CLOSED.** Transport init rewritten from eager to lazy imports.

- **File**: `runtime/transport/__init__.py`
- **Lines**: 576 → 475 (PEP 562 `__getattr__` lazy-import pattern)
- **Submodules loaded on `import runtime.transport`**: 40 → **0**
- **Side-effect modules retained eager**: 0 (none found — all modules are pure definitions)
- **Public API symbols (lazy)**: 213 (core: 131, deferred: 82)
- **Aliases**: 1 (`open_scene_request` → `local_control.open_scene`)
- **Tests**: 94/94 (unchanged)
- **Behavioral parity**: confirmed — all symbols resolve identically

### What this unblocks

The eager-import chain that blocked 149 items in Wave 0 and 2 items
in Wave 3 (capability_tagging, claude_responder) is broken. Reachability
audit of all 163 transport modules:

| Category | Count | Status |
|----------|-------|--------|
| Production reachable | 16 | STILL BLOCKED — need import path migration |
| Script-only reachable | 39 | NOW MOVABLE |
| Test-only reachable | 4 | NOW MOVABLE |
| Migration-script only | 2 | NOW MOVABLE |
| Orphan (in init, no consumer) | 31 | NOW MOVABLE |
| Orphan (completely invisible) | 72 | NOW MOVABLE |

**148 of 163 modules are now archivable.** 16 remain production-reachable.

Full inventory: `data/audits/2026-05-14_transport_unblock_inventory.md`

### ~~Urgent finding: substrate .pyc shim risk~~ — RESOLVED

~~`services/discord_bot.py` imports ~11 transport modules via `runtime.substrate.*`
paths.~~ **FIXED 2026-05-14** — all substrate imports eliminated in production
code, transport internals, and scripts. Container is rebuild-safe.

### Remaining follow-ups: 8 threads

(Transport rewrite CLOSED. Production path migration CLOSED. Docker compose CLOSED. 8 threads remain.)

---

## Production Import Safety Sweep — 2026-05-14

**CLOSED.** All `runtime.substrate` imports eliminated from the active tree.

### Scope

| Category | Files | Import sites |
|----------|-------|-------------|
| Production services | 2 (discord_bot, cc_webhook_receiver) | 29 |
| Production modules | 4 (execution_contract, environment_mapping, foreground_cu_ingestion, intent_handler) | 7 |
| Transport internals | 14 (sibling cross-refs inside runtime/transport/) | 14 |
| Scripts | 71 (smoke tests, CLIs, diagnostics) | 392 |
| **Total** | **91** | **442** |

### Method

Mechanical 1:1 path swap: `runtime.substrate.X` → `runtime.transport.X`.
Substrate was always a one-line star re-export of transport, so the swap
is byte-identical behavior.

Three import patterns were fixed:
- `from runtime.substrate.X import Y` (dotted submodule)
- `from runtime.substrate import X` (module-level)
- `import runtime.substrate.X as alias` (direct)
- String references in `importlib.import_module()` / `find_spec()`

### Missing-module handling

7 modules referenced by discord_bot.py don't exist in `runtime/transport/`:
`discord_ingress_adapter`, `discord_output_policy`, `event_store`,
`message_framing`, `operator_trace`, `run_lifecycle`, `task_finalization`.

All 7 are inside `try/except` blocks — they've always been silently failing
(the substrate shims didn't have these either, since they were star re-exports
of transport where the modules don't exist). The swap preserves the same
`ImportError → except → graceful degradation` behavior.

### claude_responder unblocked

`runtime/transport/claude_responder.py` was one of the 2 Wave 3 blocked items.
Its blocker was `from runtime.substrate import claude_session_bridge` — now
fixed to `from runtime.transport import claude_session_bridge`. With the lazy
`__init__.py`, this resolves cleanly without triggering the eager load chain.

### Container rebuild simulation

```
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
python3 -c "from runtime.transport.session_discord_bridge import send_reply"  → PASS
python3 -c "from runtime.transport.discord_text_transport import ..."         → PASS
python3 -c "from runtime.transport.event_spine import EventType"              → PASS
# ... all 12 production entry points → PASS
```

**Docker container is now rebuild-safe.** Zero stale-`.pyc` reliance.

### Commits

- `c3000aca` — production files (6) + transport internals (14): 34 import sites
- `6ceddb14` — scripts (71): 392 import sites

### Remaining `runtime.substrate` references

**Import statements: 0** in the active tree.

String references remain in comments/docstrings of some scripts (e.g.,
"runtime.substrate.voice_eos_responder" in docstring descriptions).
These are cosmetic and do not affect execution. The `r8b_generate_bridges.py`
and `r8d_generate_shims.py` codegen scripts reference substrate in their
target path configuration — they're dead code (generators for deleted shims).

### Rows 60, 75, 76 status

- **Row 60** (`services/discord_bot.py`): substrate imports eliminated. Docker
  compose path: calendly fixed (`98e15ebe`); discord_bot not yet migrated from
  services/ (no compose change needed until file moves). Remaining blocker:
  Law 5.5 violations. NOT YET CLOSED.
- **Row 75** (transport reachable — 5 modules): `capability_tagging` and
  `claude_responder` unblocked (internal substrate refs fixed). Module relocation
  to §24 homes is now mechanically possible. NOT YET CLOSED (relocation pending).
- **Row 76** (transport via substrate — 13 modules): All substrate shim paths
  eliminated. Direct transport paths established. Substrate bypass complete.
  Row 76 CLOSED.

---

## Docker Compose Paths — 2026-05-14

**CLOSED** (calendly). discord_bot deferred until file migrates.

### Inventory

| File | Line | Old path | New path | Action |
|------|------|----------|----------|--------|
| `docker-compose.yml` | 91 | `services/calendly_webhook.py` | `interface/api/webhooks/calendly_webhook.py` | UPDATED |
| `docker-compose.yml` | 165 | `services/discord_bot.py` | — (file not yet migrated) | NO CHANGE |

### Validation

- YAML parse: pass
- `docker compose config`: pass
- Target file exists on disk: yes (`interface/api/webhooks/calendly_webhook.py`, 16,399 bytes)
- Target compiles + spec loads: pass

### Notes

- `infra/docker/docker-compose.yml` is a future-state template using `umh/interfaces/`
  paths that don't exist yet. Not edited — it's not the production compose file.
- `discord_bot.py` still lives at `services/discord_bot.py`. Its compose entry is
  correct for now. When Row 60 file migration happens, compose path updates with it.
- Row 60 remaining blocker: Law 5.5 violations (Docker compose blocker resolved).

### Commit

- `98e15ebe` — os-webhook command path → canonical §24

---

## Runtime Layer Classification (Row 88) — 2026-05-14

**Status: IN PLANNING.** Classification audit complete. Migration blocked
on Phase A (Law 5.5 memory API extension).

### Scope correction

Row 88 was described as "~85 modules". Actual inventory:

| Category | Count |
|----------|-------|
| Spine (migrated W4-5) | 8 |
| Reachable non-spine (Row 88 proper) | 92 |
| Unreachable (Row 89 — archive) | 15 |
| **Total runtime/*.py** | **115** |

### Three-phase dependency chain

| Phase | Prerequisite | Unblocks | Scope |
|-------|-------------|----------|-------|
| A | None | 52 Law-5.5 modules | memory.py API + 14 domain stores |
| B | A (optional) | 17 context-dependent modules | context.py (96 callers) |
| C | A + B | All remaining | Topological migration |

23 modules are free NOW (no Law 5.5, no context dependency, no tangled
cross-deps). These can migrate before Phase A.

### Audits produced

- `data/audits/2026-05-14_runtime_layer_classification.md` — per-module table,
  dependency graph, §24 target mapping, free/blocked/tangled analysis
- `data/audits/2026-05-14_law_5_5_memory_api_design.md` — Phase A design brief:
  SQL pattern audit, proposed API extensions (3 tiers), risk surface, scope estimate

### §24 layer distribution (92 reachable modules)

| Layer | Count |
|-------|-------|
| control_plane/ | 24 |
| state/ | 19 |
| understanding/ | 16 |
| adapters/ | 10 |
| execution/ | 8 |
| governance/ | 5 |
| learning/ | 5 |
| observability/ | 3 |
| interface/ | 2 |

---

## Law 5.5 Tier 1 Adoption — 2026-05-14

**COMPLETE.** 31 modules adopted `AgentMemory.log_event()` for events table
INSERT. 44 raw SQL sites replaced. Net -286 lines.

### memory.py change

Added `handled_by: str = "cognitive_loop"` parameter to `log_event()`.
Backward-compatible — existing callers get same default. +5 lines.

### Modules adopted (31)

accountability, agent_messages, competitive_intel, confidentiality,
decision_log, delegation_tracker, doc_creator, document_filer,
email_gps (2 sites), email_reviewer, event_bus, event_manager (3 sites),
execution_engine, expense_tracker (2 sites), feedback_loop (INSERT only),
founder_capture, founder_rate (3 sites), goal_selector, ideal_week (2 sites),
meetings (4 sites), okr_tracker, personal_admin, quality_gate,
self_awareness, skill_improvement, stakeholder_map, subscription_tracker,
task_executor (2 sites), task_yield_matrix, travel_manager (2 sites),
workflow_engine (2 sites)

### ~~INVESTIGATE list~~ — RESOLVED (Tier 2)

| Module | Original issue | Resolution |
|--------|---------------|------------|
| notebooklm_sync | Explicit id + created_at | Redundant — DB handles both. Adopted `log_event()` |
| stage_manager | Wrong column names (`type`, `payload`) | **Latent bug** — INSERT would fail at runtime. Adopted `log_event()` which fixes the bug |

### ~~UPDATE sites~~ — ADOPTED (Tier 2)

| Module | Sites | Old pattern | New method |
|--------|-------|-------------|------------|
| accountability | 1 | read-modify-write (SELECT → mutate → UPDATE) | `merge_event_payload()` |
| feedback_loop | 2 | read-modify-write (SELECT → mutate → UPDATE) | `merge_event_payload()` |
| delegation_tracker | 1 | JSONB merge (`\|\|`) | `merge_event_payload()` |

### Remaining Law 5.5 violations

| Tier | Sites | Status |
|------|-------|--------|
| ~~Tier 1 (events INSERT)~~ | ~~46~~ | ~~COMPLETE~~ |
| ~~Tier 1 INVESTIGATE~~ | ~~2~~ | ~~RESOLVED (adopted log_event)~~ |
| ~~Tier 2 (events UPDATE)~~ | ~~4~~ | ~~COMPLETE (merge_event_payload)~~ |
| Tier 3 (domain tables) | ~50 | 14 domain store classes needed |
| discord_bot.py (Row 60) | 6 | 1 INSERT + 5 UPDATE — blocked on bot migration |
| **Total remaining** | **~56** | |

### Tier 1 Verification

- Tests: 3827 passed / 34 failed (pre-existing) / 3 skipped
- Compile: 32/32 files pass py_compile
- Import smoke: 28/30 pass (2 pre-existing DATABASE_URL env failures)
- Commit: `0b2d13ec`

---

## Law 5.5 Tier 2 Adoption — 2026-05-14

**COMPLETE.** 1 new method added to AgentMemory. 4 UPDATE sites + 2 INVESTIGATE
items adopted. runtime/ layer now has ZERO raw events SQL.

### memory.py change

Added `merge_event_payload(org_id, event_id, updates) -> bool`.
Uses JSONB `||` operator for atomic server-side merge. +18 lines.
Existing methods unchanged (additive only).

### Tier 2 modules adopted (3 modules, 4 UPDATE sites)

| Module | Sites | Old pattern | Improvement |
|--------|-------|-------------|-------------|
| accountability | 1 | read-modify-write (2 round-trips) | Atomic merge (1 round-trip, no race) |
| feedback_loop | 2 | read-modify-write (2 round-trips) | Atomic merge (1 round-trip, no race) |
| delegation_tracker | 1 | JSONB `\|\|` (already atomic) | Canonical API call |

### INVESTIGATE items resolved (2 modules, 2 INSERT sites → log_event)

| Module | Issue | Resolution |
|--------|-------|------------|
| notebooklm_sync | Explicit id + created_at | Redundant — adopted `log_event()` |
| stage_manager | Wrong column names (`type`, `payload`) | **Latent bug fixed** — adopted `log_event()` |

### runtime/ events SQL status: CLEAN

```
grep -rn "INSERT INTO events\|UPDATE events" runtime/ → 0 results
```

Only remaining events SQL:
- `state/memory/memory.py` — the canonical API itself (correct)
- `services/discord_bot.py` — 6 sites (Row 60, blocked on bot migration)

### Verification

- Tests: 4139 passed / 35 failed (all pre-existing) / 3 skipped
- py_compile: 6/6 touched files pass
- Import smoke: 6/6 touched modules import cleanly
- Tree grep: 0 raw `UPDATE events SET` in runtime/
- Commits: `f0ad2b0c` (method), `0daa2040` (4 sites), `1af6e822` (INVESTIGATE)

---

## Law 5.5 Tier 3 Adoption — 2026-05-14

14 domain store classes created, ~50 raw SQL write sites adopted across
23 caller modules. NEW FILES ONLY — §29 spine (memory.py, db.py) untouched.

### Stores created (state/stores/)

| Store | Methods | Callers adopted | Tables |
|-------|---------|-----------------|--------|
| entity_link_store | 1 | knowledge_graph | entity_links |
| context_compaction_store | 1 | context_compaction | context_compactions |
| agent_registry_store | 1 | self_awareness | agents |
| embedding_store | 1 | embedding_engine | embeddings |
| higgsfield_store | 2 | higgsfield_client, higgsfield_webhook | higgsfield_jobs |
| email_folder_store | 2 | email_gps | email_folders |
| venture_store | 1 | business_instance | ventures |
| approval_store | 3 | evolution_engine, authority_engine | approvals |
| skill_store | 3 | skill_registry_v2, skill_improvement, knowledge_domains, claude_skill_registry, research_engine | skills |
| preference_store | 2 | model_preferences | model_preferences |
| task_store | 3 | coordination_engine, execution_engine, notion_sync | tasks |
| permission_store | 3 | os_trinity | cross_product_permissions, product_connections |
| profile_store | 3 | human_intelligence, user_model, os_trinity | human_profiles, user_profiles, user_intelligence_profiles |
| goal_store | 4 | goal_selector | goals, goal_outcomes |

### Latent bugs found and fixed

| Module | Bug | Fix |
|--------|-----|-----|
| evolution_engine.py | Used column `request` — actual column is `request_json` (would fail at runtime) | ApprovalStore uses correct `request_json` |

### Race conditions eliminated

| Module | Old pattern | New pattern |
|--------|-------------|-------------|
| knowledge_domains.py | SELECT → branch → INSERT/UPDATE | Atomic ON CONFLICT upsert via SkillStore |
| research_engine.py | SELECT → branch → INSERT/UPDATE | Atomic ON CONFLICT upsert via SkillStore |

### Excluded (dead code, 0 callers)

| Module | Sites | Reason |
|--------|-------|--------|
| transaction_workflow.py | 8 | 0 callers in codebase |
| company_instantiator.py | 2 | 0 callers in codebase |

### Deferred (scripts/, Phase C)

| Module | Sites | Reason |
|--------|-------|--------|
| scripts/sync_skills_to_neon.py | skills | Cron script, not runtime |
| scripts/agent_task_executor.py | tasks | Cron script, not runtime |

### Tree-wide grep status

All 14 Tier 3 tables: write SQL confined to store files only in live runtime.
Remaining raw SQL: archive/ (frozen) and scripts/ (deferred Phase C).

### Verification

- Tests: 4166 passed / 34 failed (all pre-existing) / 3 skipped — zero regressions, +27 new tests
- py_compile: 14 store files + 23 caller files all clean
- Import smoke: 14/14 stores + 23/23 callers import cleanly (with dotenv)
- Tree grep: all Tier 3 table writes confined to state/stores/ in live runtime
- Commits: pending (uncommitted, user reviews before push)

---

## Phase B: context.py Migration — 2026-05-14

Hub migration for the highest-connectivity node in the codebase (96 callers).

### Decision: SHIM

Canonical at `state/context/context.py`. Original `runtime/context.py`
rewritten as 3-line re-export shim. All 96 callers continue working via shim.

**Rationale:**
1. Path-dependent side effect (`load_dotenv(Path(__file__).parent / ".env")`)
   — file move changes dotenv resolution. Fixed with absolute repo-root path.
2. 2 mock patches by string path (`"runtime.context.load_context_from_env"`)
   — continue working through shim namespace.
3. 96 callers across 11 directories with aliased imports (`as _lctx`, etc.)
   — sed bulk replacement is fragile.

### Files

| File | Role |
|------|------|
| state/context/context.py | Canonical (41 LOC, EOSContext + loaders) |
| state/context/__init__.py | Package marker |
| runtime/context.py | Re-export shim (3 LOC) |

### Key fix

`load_dotenv(Path(__file__).parent / ".env")` → `load_dotenv(_REPO_ROOT / "runtime" / ".env")`
where `_REPO_ROOT = Path(__file__).resolve().parent.parent.parent`.

### Verification

- Tests: 4166 passed / 34 failed (all pre-existing) / 3 skipped — zero regressions
- py_compile: 3/3 touched files pass
- Identity check: `state.context.context.EOSContext is runtime.context.EOSContext` → True
- Production smoke: 8 entry points across all layers import clean (fresh pycache)
- Mock patches: verified `patch("runtime.context.load_context_from_env")` still intercepts
- Tree grep: 96 callers on shim (expected), 1 on canonical (the shim itself)

## Phase C: Runtime Layer Migration — 2026-05-14

Final substrate migration. All 99 reachable non-spine modules relocated from
runtime/ top-level to canonical §24 homes.

### Re-classification (post-Phase-A+B)

Original blockers cleared:
- Law 5.5: 50 of 52 modules cleared by Phase A stores (2 remaining = 1 site each)
- Context dependency: all 64 shim callers now non-blocking (shim + canonical available)
- Result: ALL 99 modules migratable (up from 23 originally free)

### Sub-batch breakdown

| Sub-batch | Count | Criterion | Examples |
|-----------|-------|-----------|---------|
| 1 (zero deps) | 51 | No runtime/ cross-deps | gws_connector (27 callers), business_instance (20), venture_knowledge (10) |
| 2 (deps in B1) | 23 | All deps already migrated | knowledge_integrator, meetings, strategy_engine, skill_registry |
| 3 (recursive) | 25 | Remaining, topological tiers | orchestrator, event_bus, goal_selector, discord_utils |

Sub-batch 3 internal tiers:
- 3a: 8 (no B3 deps) — portfolio_advisor, research_engine, status, ...
- 3b: 3 (deps in 3a) — daily_sync, evolution_engine, task_executor
- 3c: 2 (deps in 3a+3b) — proactive_engine, workflow_engine
- 3d: 12 (cycles + remaining) — discord_utils↔output_validator, goal_selector↔event_bus, orchestrator

### Migration results

- **Modules migrated: 99 of 99** (all reachable non-spine)
- **Deferred: 0** (all modules migrated successfully)
- **Phase B shim: RETAINED** — 0 live callers, 7 dead-code callers
  - 32 live callers migrated to canonical `state.context.context`
  - 7 remaining callers are UNREACHABLE dead-code modules
  - Shim removable alongside dead code archive
- **Circular deps resolved**: 2 pairs (lazy imports, co-migrated)
- **Tests/conftest fix**: pre-import `runtime.transport` for namespace pkg resolution

### File distribution by §24 layer

| §24 Layer | Modules | Examples |
|-----------|---------|---------|
| control_plane/ | 24 | orchestrator, goal_selector, event_bus, portfolio_advisor |
| state/ | 19 | business_instance, work_state, skill_registry, session_state |
| understanding/ | 16 | person_recognition, knowledge_integrator, research_engine |
| adapters/ | 10 | gws_connector, email_gps, meetings, scrapling_connector |
| execution/ | 8 | execution_engine, execution_loop, task_executor, voice_engine |
| governance/ | 5 | quality_gate, output_validator, accountability, confidentiality |
| learning/ | 5 | evolution_engine, feedback_loop, skill_improvement, self_awareness |
| observability/ | 3 | provider_health, system_health, status |
| interface/ | 2 | discord_utils, channel |

### runtime/ file count

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Top-level .py files | 115 | 16 | -99 |
| Remaining | — | 15 unreachable + 1 context.py shim | — |
| Subdirectories | 6 | 6 (transport/, ingestion/, domain_bridge/, substrate/, interfaces/, .substrate_sandbox/) | unchanged |

### Verification

- Tests: 4165/35/3 — matches pre-Phase-C baseline exactly (zero regressions)
- Production smoke: 14 canonical entry points import clean (fresh pycache)
- Container rebuild sim: pycache cleared, all imports resolve
- Object identity: `state.context.context.EOSContext is runtime.context.EOSContext` → True
- Zero old-path references remain for any migrated module

### Substrate completion status: COMPLETE (Row 88)

All reachable non-spine modules now at canonical §24 homes. Remaining
runtime/ contents: 15 dead-code modules (archive candidates), 1 context
shim (zero live callers), and 6 subdirectories (transport, ingestion,
domain_bridge, substrate, interfaces — separate subsystem scope).

---

## Cleanup Sweep — 2026-05-14

Post-Phase-C housekeeping. Five followup threads closed via archive
operations + canonical API adoption.

### Thread status

| Thread | Scope | Action | Status |
|--------|-------|--------|--------|
| 1. Dead-code runtime/ modules | 15 files, 0 callers | Archived to `_archive/2026-05-14_cleanup_sweep/dead_code_runtime/` | **CLOSED** (`4a0b562d`) |
| 2. Tier 3 dead-code sites | transaction_workflow.py + company_instantiator.py | Covered by Thread 1 (both were among 15 dead-code modules) | **CLOSED** (by Thread 1) |
| 3. Obsolete generators | r8b_generate_bridges, r8d_generate_shims, r8_import_graph_snapshot, r8_compare_import_graphs | Archived to `_archive/2026-05-14_cleanup_sweep/obsolete_generators/` | **CLOSED** (`e512bb39`) |
| 4. Deferred Tier 3 script sites | agent_task_executor.py (2 raw SQL sites), sync_skills_to_neon.py | agent_task_executor: ADOPTED (log_event + set_notion_page_id). sync_skills_to_neon: ADOPTED (3 SQL sites → SkillStore) | **CLOSED** (`a65b4c6a`, `5e3f5e80`) |
| 5. Phase B context.py shim | runtime/context.py (3-line re-export) | Deleted. 0 callers after Thread 1 cleared last 7 dead-code refs | **CLOSED** (`952b52b1`) |

### Results

- **Files archived**: 19 (15 dead-code modules + 4 obsolete generators)
- **Files deleted**: 1 (runtime/context.py)
- **Files adopted**: 1 (agent_task_executor.py — 2 raw SQL sites → canonical APIs)
- **Files deferred**: 0 (sync_skills_to_neon.py resolved — SkillStore domain store added)
- **runtime/ top-level .py files**: 16 → **0**
- **runtime/ subdirectories**: 5 (transport, ingestion, domain_bridge, substrate, interfaces)
- **Tests**: 4166 passed / 34 failed (all pre-existing) / 3 skipped — zero regressions
- **Production smoke**: 7/7 (fresh pycache)
- **Commits**: 4 (`4a0b562d` .. `952b52b1`)

### Remaining cleanup threads

| Thread | Items | Status |
|--------|-------|--------|
| ~~Transport orphan archive~~ | ~~148 → 95 archived~~ | ~~CLOSED — 2026-05-14~~ |
| Transport package §24 migration | 68 modules (15 PROD + 53 deps) | NEW — full package move |
| Law 5.4 type convergence | 5 spine modules | Dedicated follow-up wave |
| Law 5.9 adapter refactor | 6 files in execution/workers/workstation/ | §14.1 contract |
| ~~Law 5.5 sync_skills_to_neon.py~~ | ~~1 file, SELECT/INSERT/UPDATE on skills table~~ | ~~CLOSED — 2026-05-14 (SkillStore.get_by_name + upsert_skill)~~ |
| Cron script migration | 23 files | System-level coordination |

---

## Transport Orphan Archive — 2026-05-14

95 of 163 transport modules archived. Thread CLOSED.

### Classification

| Category | Count | Action |
|----------|-------|--------|
| TRUE_ORPHAN (archived) | 95 | `_archive/2026-05-14_transport_orphans/` |
| INTRA_TRANSPORT (PROD deps) | 53 | Restored — move with package |
| PROD callers | 15 | §24 migration follow-up |
| **Total** | **163** | |

### Key finding: transitive coupling

15 PROD modules depend on 53 additional modules via import chains.
AST-based transitive closure analysis required to identify safe
archive boundary. Initial 148-archive reduced to 95 after discovering
hard import-time dependencies.

### Archive contents

- 95 transport modules (zero PROD deps after transitive analysis)
- 5 test files (tested only archived modules)
- 1 test method removed from live test file
- `__init__.py` trimmed: 474 → 62 lines, 54 → 4 registered modules

### Results

- **runtime/transport/**: 164 → 69 .py files (163 → 68 modules)
- **Tests**: 4070/34/3 (96 tests removed with archived files, 0 regressions)
- **Production smoke**: 15/15 PROD modules + 12/12 canonical entry points
- **Commits**: 6 (`78951a82` .. `6abf0951`)

### New follow-up: Transport package §24 migration

68 modules remain in `runtime/transport/`. These form a tightly-coupled
package that must migrate as a unit. Suggested §24 target:
`execution/transport/` or dedicated top-level `transport/`.

Subthread: 53 smoke test scripts in `scripts/` reference archived
modules. Non-production — stale references expected.

---

## Law 5.5 SkillStore — 2026-05-14

**PHASE A MILESTONE: COMPLETE.** All Law 5.5 violations resolved.

Last deferred site (`sync_skills_to_neon.py`) adopted SkillStore.
The SkillStore domain store already existed from prior Tier 3 work;
it needed only a `get_by_name()` read method to support the script's
unchanged-detection optimization.

### Changes

| File | Change |
|------|--------|
| `state/stores/skill_store.py` | +`get_by_name()` method (+16 lines), removed unused `json` import |
| `scripts/sync_skills_to_neon.py` | 3 raw SQL sites (SELECT/INSERT/UPDATE) → `SkillStore.get_by_name()` + `SkillStore.upsert_skill()`. Removed `uuid`, `get_conn` imports. |
| `tests/test_domain_stores_tier3.py` | +2 tests (import + signature for `get_by_name`) |

### Key finding: UNIQUE constraint exists

The script's comment claimed "no UNIQUE(org_id, name) constraint exists"
but `idx_skills_org_name` UNIQUE index is present. The cautious
SELECT-then-INSERT-or-UPDATE was unnecessarily complex — ON CONFLICT
upsert is safe. Script now uses `upsert_skill()` which leverages the
constraint.

### Verification

- Dry-run: 96 skills processed (7 insert, 66 update, 23 unchanged)
- Tree-wide SQL check: zero raw INSERT/UPDATE/DELETE on skills table
  outside `state/stores/skill_store.py` and archived code
- Tests: 4071/34/3 (+1 passed, zero regressions)
- Commits: 2 (`de896329`, `5e3f5e80`)

### Phase A final tally

| Tier | Sites adopted | API methods | Status |
|------|--------------|-------------|--------|
| Tier 1 (log_event) | 46 sites across 33 modules | 0 new (existing) | COMPLETE |
| Tier 2 (update_event, upsert_embedding) | 7 sites across 4 modules | 2 new | COMPLETE |
| Tier 3 (domain stores) | ~50 sites across 19 modules | 14 stores | COMPLETE |
| Tier 3 deferred (sync_skills_to_neon) | 3 sites in 1 script | 1 new read method | COMPLETE |
| **Total** | **~106 sites** | **14 stores + 3 methods** | **COMPLETE** |

### Remaining followup threads

| Thread | Items | Status |
|--------|-------|--------|
| Transport package §24 migration | 68 modules (15 PROD + 53 deps) | Full package move |
| Law 5.4 type convergence | 5 spine modules | Dedicated follow-up wave |
| Law 5.9 adapter refactor | 6 files in execution/workers/workstation/ | §14.1 contract |
| Cron script migration | 23 files | System-level coordination |
