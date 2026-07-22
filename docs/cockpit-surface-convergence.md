# Cockpit Surface Convergence Ledger

Started 2026-07-21 (MVP Wave 1). Every known divergence from the Convergence
Law (`.claude/rules/convergence-law.md`) is recorded here with an owner
adjudication and a migration path. Entries are RESOLVED or RETIRED — never
silently deleted. New divergence may not be added to code without a ledger
entry; the ledger is the license for bounded compatibility debt, not a
graveyard.

Status values: `ACTIVE_DEBT` (bounded compatibility, retirement scheduled) |
`ADJUDICATED` (naming/ownership ruling recorded, no code debt) |
`RESOLVED` (converged; entry kept for history).

## Concept-level entries

| # | Divergence | Canonical owner | Status | Migration path |
|---|---|---|---|---|
| 1 | `ObjectiveQueue` (`objective_queue.py`) holds objective-like items with its own lifecycle | `GoalRegistry` Goal(OBJECTIVE) | ACTIVE_DEBT | Zero new Wave 1 writes; read adapters only; migrate in execution-convergence wave |
| 2 | `Coordinator.Objective` + `WorkUnit` (coordinator.py) — legacy decomposition vocabulary | Goal(OBJECTIVE) + WorkPacket | ACTIVE_DEBT | Same as #1 |
| 3 | IntentLoop records (`operator/intent_loop/`) were the work-capture truth for Cockpit submissions | Intent protocol → GoalRegistry / PlanningStore / packet store | ACTIVE_DEBT (chat path RESOLVED) | C4 cutover DONE for the Cockpit converse path (`try_chat_planning_rail` replaced the legacy rail; spy tests prove zero legacy mutation calls, §23.5). Remaining debt: explicit `POST /intent-loop/submit` + panel read surface stay as bounded legacy compatibility until the execution-convergence wave |
| 4 | `WorkLineage` name collision: continuity aggregate (`continuity_runtime.WorkLineage`) vs per-Task planning lineage | Both legitimate, DIFFERENT concepts | ADJUDICATED | New contract named `WorkLineageContext` (`substrate/contracts/work_context.py`); no shadow, no LEGACY_DUPLICATES growth |
| 5 | Planning-time gap artifact vs strategic `Gap` (strategic_gap_engine) | `Gap` = canonical strategic gap | ADJUDICATED | Planning artifact classified GapAssessmentSnapshot — evidence class, non-authoritative, goal_refs link to canonical Gaps (C3 rename of `GapModel`) |
| 6 | StrategicGapEngine gaps/recommendations/decisions still write under tracked `data/umh/strategic_gaps/` | runtime-state boundary | ACTIVE_DEBT | Goal store migrated (§22.1, Wave 1). Remaining sub-stores migrate with the strategic-engine convergence wave; no new Wave 1 write paths added to them |
| 7 | Per-store private fcntl lock idiom repeated (planning store, approval_store, settings_persistence, GoalRegistry, …) | one canonical lock utility (future) | ACTIVE_DEBT | Extract shared helper when a 6th copy would appear; do not fork the idiom further |
| 8 | SelfBuild / BuildLoop / Actions stores hold build work outside canonical packets | WorkPacket + WorkGraph | ACTIVE_DEBT | Verified read adapters only (visually distinct on Work board); store migration scheduled post-Wave-1 |
| 9 | Seat/session-derived identity in legacy auth paths | PrincipalContext (principal ≠ tenant ≠ membership ≠ seat) | ACTIVE_DEBT | `substrate/contracts/principal_resolution.py` derives legacy_derived ids deterministically; membership NEVER from a browser session; native issuance in tenancy wave |
| 10 | Per-route/per-module `EventSpine()` constructions (cockpit routes, operator engines) split event truth | `get_shared_event_spine()` (event_spine.py — persisted, recovered) | ACTIVE_DEBT | Planning path uses ONLY the shared spine (§22.6, enforced by test AC); per-route instances migrate in the observability convergence wave |
| 11 | `instruction_compilation.compile_instruction_package` has no production caller yet (Wave 1 planning is deterministic-only) | the §9 seam itself | ADJUDICATED | Deliberate: §9 mandates the seam BEFORE the first planning model call exists; contract is deterministically tested (test V); the first LLM enhancement on the planning path MUST call it — never a raw prompt string |

## Surface-level entries (Cockpit)

| # | Divergence | Canonical surface | Status | Migration path |
|---|---|---|---|---|
| S1 | 86 panels / 7 overlap clusters (panel audit 2026-07-20) | panel registry (`cockpit/src/renderer/panels/registry.ts`) | ACTIVE_DEBT | Wave 1 converges the planning cluster (intent/intentloop/objectiveplan → workdetail; tasks/universalwork → work; commands → chat; approvals → expanded HUD Decision surface). Remaining clusters converge in later waves |
| S2 | IntentPanel / IntentLoopPanel / CommandsPanel / TasksPanel rival surfaces | WorkDetailPanel / Work kanban / chat | ACTIVE_DEBT | C4: non-executable redirect stubs; ids never dead-link |
| S3 | Decision controls existed in chat cards | Top HUD ControlPanel ONLY | RESOLVED | Decision buttons removed from PlanSummaryCard (Wave 1 UI slice); chat surfaces/focuses the HUD item only |
| S4 | Hardcoded assistant persona names ("DEX") in some surfaces | `get_ai_name()` / SelfModel.ai_name | ACTIVE_DEBT | Touched surfaces converted in C4; full sweep tracked by vocabulary census (~92 terms, 12 collisions) |
| S5 | Operator-facing Layer-2 vocabulary (packet/intent/approval wording) across legacy panels | docs/LEXICON.md Layer 1 | ACTIVE_DEBT | Shrink-only gate `scripts/check_operator_language.py`; touched surfaces converge per commit |
| S6 | Live-WS voice session converses via `daemon.advisor.converse` directly, bypassing the planning rail | one protocol for text + voice (`try_chat_planning_rail` on `/advisor/converse`) | ACTIVE_DEBT | Voice MESSAGES and text already share the rail (platform-voice-adapter → POST /advisor/converse). Inject the rail into the live-WS converse fn in the voice follow-on |

## Skill classification entries

Touched Skills are inventoried during C3 archetype work as
competency | procedure | workflow | playbook | tool-instruction |
prompt-package; misclassifications land here as new rows. No full Skill
migration in Wave 1.
