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
| 11 | `instruction_compilation.compile_instruction_package` has no production caller yet (Wave 1 planning is deterministic-only) | the §9 seam itself | RESOLVED (Wave 2) | First production consumer landed: `substrate/execution/attempts/dispatch.py::compile_attempt_package` seals one ModelExecutionPackage per attempt (Wave 2 C3). No raw prompt strings on the execution path |
| 12 | Legacy execution stores (coordinator `CoordinatorExecutionPlan` JSON + `LifecycleEvent` JSONL; `ExecutionReceipt`) | `ExecutionAttempt` ledger + shared EventSpine | ACTIVE_DEBT | Zero new Wave 2 writes from the canonical execution path (attempts/* imports none of them — enforced by `test_wave2_convergence_gates`). Coordinator plan/lifecycle stores are read-only compat; retire in a later wave |
| 13 | `ExecutionGraph` defined twice — `plan_execution_adapter.py:269` (ExecutablePlan DAG) vs `execution_graph.py` (ExecutionGraphNode DAG) | `execution_graph.ExecutionGraph` canonical | ADJUDICATED | Distinct concerns; adapter-local one registered as a Wave 2 legacy-duplicate homonym in `canonical_types.LEGACY_DUPLICATES_META` (shrink-only, sunset 2026-12-31), retired when the adapter leaves the legacy path |
| 14 | Execution-readiness had TWO representations and ZERO enforcement: `readiness.evaluate_execution_readiness` defined 15 fail-closed checks with **no production caller**, while the scheduler open-coded a partial subset inline. `grant.role_ids`, `grant.allowed_tools`, `grant.cost_limit_usd`, `work_scope.target_kind`, prohibited skills and rollback obligations were therefore unenforced at admission — operator-set bounds that imposed nothing. Comments in `lifecycle.py` ("requires AUTHORIZED readiness", "authorization re-validated at that instant") and `placement.py` ("tools already validated ... in readiness") asserted guarantees no code provided | `admission.authorize_admission` — the ONE canonical fail-closed admission authority | RESOLVED (Wave 2 R3) | `substrate/execution/attempts/admission.py` decides all 17 admission conditions and is consumed ATOMICALLY by `AttemptScheduler._admit` under the scheduler lock, on the re-read packet and re-read grant, immediately before the lease. `ExecutionReadinessAssessment` is retained as the PRE-GRANT advisory assessment surface only — it is not an enforcement rival and holds no admission authority. The three false comments are corrected in the same change. 12/12 mutations killed (each guard independently load-bearing) |

## Surface-level entries (Cockpit)

| # | Divergence | Canonical surface | Status | Migration path |
|---|---|---|---|---|
| S1 | 86 panels / 7 overlap clusters (panel audit 2026-07-20) | panel registry (`cockpit/src/renderer/panels/registry.ts`) | ACTIVE_DEBT | Wave 1 converges the planning cluster (intent/intentloop/objectiveplan → workdetail; tasks/universalwork → work; commands → chat; approvals → expanded HUD Decision surface). Remaining clusters converge in later waves |
| S2 | IntentPanel / IntentLoopPanel / CommandsPanel / TasksPanel rival surfaces | WorkDetailPanel / Work kanban / chat | ACTIVE_DEBT | C4: non-executable redirect stubs; ids never dead-link |
| S3 | Decision controls existed in chat cards | Top HUD ControlPanel ONLY | RESOLVED | Decision buttons removed from PlanSummaryCard (Wave 1 UI slice); chat surfaces/focuses the HUD item only |
| S4 | Hardcoded assistant persona names ("DEX") in some surfaces | `get_ai_name()` / SelfModel.ai_name | ACTIVE_DEBT | Touched surfaces converted in C4; full sweep tracked by vocabulary census (~92 terms, 12 collisions) |
| S5 | Operator-facing Layer-2 vocabulary (packet/intent/approval wording) across legacy panels | docs/LEXICON.md Layer 1 | ACTIVE_DEBT | Shrink-only gate `scripts/check_operator_language.py`; touched surfaces converge per commit |
| S6 | Live-WS voice session converses via `daemon.advisor.converse` directly, bypassing the planning rail | one protocol for text + voice (`try_chat_planning_rail` on `/advisor/converse`) | ACTIVE_DEBT | Voice MESSAGES and text already share the rail (platform-voice-adapter → POST /advisor/converse). Inject the rail into the live-WS converse fn in the voice follow-on |
| S7 | Execution-family rival panels (UnifiedExecution / Executor / Runtime / DistributedRuntime / ExecCoord / unwired AgentFleet) | one canonical `execution` surface | RESOLVED (Wave 2 C6) | Registry aliases `unifiedexecution/executor/distributedruntime/runtime/execcoord/agentfleet → execution`; the four rival panels are non-executable redirect stubs (pinned by `surfaceAuthority.test.tsx`); distinct diagnostics absorbed as the Execution panel's Runtime tab |
| S8 | Rival execution-decision writes at `/unified-execution/approve|reject` and `/execution/approvals/*` | `/unified-approval` ONLY (HUD) | ACTIVE_DEBT | Execution decisions surface only via `ApprovalSourceType.EXECUTION_AUTH` in the HUD; the rival panels that POSTed decisions are retired stubs. Legacy GET diagnostics remain; POST decision routes to be refused in a follow-on |
| S9 | `unifiedExecutionStore` + ExecutorPanel raw unauthenticated `fetch()` reads | canonical `executionAttemptStore` over `/execution/*` (authed `fetchApi`) | RESOLVED (Wave 2 C6) | The new store reads only the canonical execution routes via `fetchApi`; retired panels do no fetching |
| S10 | Ungoverned execution entries on operator surfaces (ExecutorPanel `/agents/run` launcher, RuntimePanel handoff input) | governed attempt path only | RESOLVED (Wave 2 C6) | Those surfaces are retired stubs; execution runs only under a governed, HUD-authorized attempt. `/fleet/*` POST fail-closed behind a decision_ref is a follow-on |

## Skill classification entries

Touched Skills are inventoried during C3 archetype work as
competency | procedure | workflow | playbook | tool-instruction |
prompt-package; misclassifications land here as new rows. No full Skill
migration in Wave 1.
