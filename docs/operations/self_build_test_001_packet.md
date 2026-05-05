# Self-Build Test 001

**Date**: 2026-05-04
**Operator**: Antony F. Munoz + Claude Code (Developer Agent)
**Test type**: Planning/review only — no source code modifications
**Parallel session**: umh_tests (this session). umh_core runs business test concurrently.

---

## Current System State

### Completed Phases (75B through 88)

| Phase | Name | Tests | Status |
|-------|------|-------|--------|
| 75B | Governed Execution Spine | - | Complete |
| 76 | Adapter Pack | - | Complete |
| 77 | Workstation Continuity | - | Complete |
| 78 | Trace → Outcome → Feedback Loop | - | Complete |
| 79 | Observability + Operator Backend | - | Complete |
| 80 | Unified Registry System | - | Complete |
| 81 | Reality-Derived Ontology/Law Kernel | - | Complete |
| 82 | Storage + Memory Discipline | - | Complete |
| 83 | Legacy Migration Boundary | - | Complete |
| 84 | Interface Layer + Command Center Contracts | - | Complete |
| 84A | Unity / Oneness Law Amendment | - | Complete |
| 85 | Deliberation Council System v1 | - | Complete |
| 85B | Council Thinker Archetypes + Adversarial Deliberation | 88 | Complete |
| 86 | EOS Tomorrow Operating Loop v1 | 81 | Complete |
| 87 | Leverage + Resource / Tool Taxonomy v1 | 118 | Complete |
| 87A | Distributed Node Registry + Runtime Routing v1 | 146 | Complete |
| 87B | Tool-Agnostic Onboarding Context Ingestion v1 | 164 | Complete |
| 87B.1 | Ingestion Safety Reconciliation | included in 87B | Complete |
| 87C | Workstation Baseline + Optimization Readiness v1 | - | Complete |
| 88 | First Workflow Test Harness v1 | 100 | Complete |
| 88-NS | North Star Integrated Operating Test Harness | 116 | Complete (unformatted) |

### Test Health

- North Star tests: 116/116 passing
- Regression tests (85B–88): 697/697 passing (2 deprecation warnings, non-blocking)
- Total known test count across Phase 86–88 NS: 813 passing

### Module Count

- 64 directories under umh/ (including __pycache__)
- 14 files in umh/workflows/ (the Phase 88 / North Star module)
- CLI has 40+ command functions, no workflow-specific commands yet

### Architecture Layers Completed

1. **Governance**: execution spine, authority engine, governance module
2. **Ontology**: law kernel, unity amendment
3. **Memory/Storage**: discipline layer
4. **Council**: 23 thinker archetypes, adversarial deliberation, synthesis protocol
5. **Operating Loop**: tomorrow loop state machine (prepare→brief→execute→review→close→handoff)
6. **Leverage**: resource/tool taxonomy, scoring, recommendations
7. **Distributed**: node registry, capability routing, artifact sync
8. **Ingestion**: source classes, onboarding tiers, permissions, review policies
9. **Workflows**: business workflow definition, self-build workflow definition, integrated harness, KPIs, results, review, template candidates, safety scanner

### What Does NOT Exist Yet

- **Persistence**: no daily plan/result/review saving to Neon
- **Multi-day trending**: no KPI comparison across days
- **CLI workflow commands**: no `umh workflow` subcommands
- **Phase 86 ↔ Phase 88 integration**: tomorrow loop and workflow harness are not wired together
- **Template promotion system**: candidates identified but no template engine
- **Objection library**: no aggregation/analysis over time
- **Automated KPI calculation**: all KPIs are manual entry

---

## Highest-Leverage Next Build Candidate

### Phase 86 ↔ Phase 88 Integration (Tomorrow Loop → Workflow Harness Bridge)

**Why this is highest leverage:**

The Tomorrow Operating Loop (Phase 86) and the Workflow Test Harness (Phase 88) are the two systems the operator would actually use daily. Right now they are disconnected:

- Phase 86 produces: `TomorrowLoopState`, `DailyObjective`, `TomorrowHandoff`, `DailyBriefing`
- Phase 88 produces: `DailyWorkflowPlan`, `WorkflowTask`, `WorkflowResult`, `DailyWorkflowReview`

Neither feeds the other. The operator would need to run both systems separately and manually correlate them.

**What the bridge would do:**
1. Tomorrow Loop's PREPARE phase generates objectives from the workflow plan
2. Tomorrow Loop's BRIEF phase includes workflow tasks and leverage recommendations
3. Tomorrow Loop's REVIEW phase consumes workflow results and KPIs
4. Tomorrow Loop's HANDOFF phase carries workflow lessons and next-day recommendations

**Estimated scope:** ~150-250 lines of bridge/adapter code + ~50-80 test lines
**Risk level:** MEDIUM — modifies existing Phase 86 orchestrator or creates adapter layer
**Files likely touched:** `umh/tomorrow/orchestrator.py` (modify) or new `umh/workflows/tomorrow_bridge.py` (create)

**Why it matters more than persistence:** Without the bridge, neither system is usable as a unified operating tool. Persistence without integration just saves disconnected data. Integration without persistence at least creates a single operating flow.

---

## Alternative Build Candidates

### Alternative 1: Result Persistence to Neon

Save `DailyWorkflowPlan`, `WorkflowResult`, `DailyWorkflowReview` to Neon.

- **Leverage**: Medium — enables multi-day trending, but only useful after the workflow is actually used
- **Risk**: LOW — purely additive, no existing code modified
- **Gating question**: Has the operator actually run a full day using the harness? If not, persistence saves empty data.
- **Files**: new `umh/workflows/persistence.py`, modify `eos_ai/db.py` (add tables)

### Alternative 2: CLI Workflow Commands

Add `umh workflow north-star-plan`, `umh workflow business-plan`, `umh workflow self-build-plan`, `umh workflow dashboard`.

- **Leverage**: Medium — makes the harness accessible from terminal sessions (iPhone/iPad)
- **Risk**: LOW — purely additive
- **Gating question**: Is the workflow harness stable enough that CLI access is the bottleneck? Or is the harness itself untested?
- **Files**: modify `umh/control/cli.py`

### Alternative 3: Template Promotion System

Build the engine that converts identified template candidates into actual reusable templates.

- **Leverage**: Low right now — no real templates have been identified from actual use yet
- **Risk**: MEDIUM — creates a new system with its own storage needs
- **Gating question**: Do we have any real template candidates from actual execution? No — all candidates are hypothetical.

### Alternative 4: Objection Library

Build aggregation/analysis for captured objections across days.

- **Leverage**: Low right now — zero objections captured from real sales conversations
- **Risk**: LOW — purely additive
- **Gating question**: Has a single real sales objection been captured? No.

---

## Do-Not-Build-Yet List

1. **Autonomous code execution loop** — UMH should not run its own next phase without operator review
2. **Full Template System** — no real template candidates exist from actual execution data
3. **Automated KPI calculation via API** — requires platform connections, violates war sprint safety
4. **Multi-company parallel cell orchestration** — end-state doctrine, not current-state need
5. **Always-on intelligence loops** — end-state doctrine, not current-state need
6. **Algorithmic self-modeling** — end-state doctrine, no ingestion pipeline exists
7. **Physical product intelligence** — end-state doctrine, not relevant to first workflow
8. **New architecture expansion phases** — must validate existing phases through actual use first
9. **Objection library** — no real objections captured yet
10. **Memory promotion** — governance not yet tested through real execution cycles

---

## Drift Risks

### 1. Architecture Expansion Without Validation Drift

**Risk level**: HIGH
**Evidence**: 64 umh/ directories, 18+ completed phases, 813+ tests — but zero actual operating days logged through the harness. The system grows architecturally without execution validation.
**Mitigation**: This test (and the parallel business test) exist specifically to detect this. The decision to pause architecture expansion is correct.

### 2. Phase 86 / Phase 88 Divergence Drift

**Risk level**: MEDIUM
**Evidence**: Phase 86's `TomorrowLoopState` and Phase 88's `DailyWorkflowPlan` model overlapping concerns (daily objectives, KPIs, review) with incompatible types. If both evolve independently, reconciliation becomes harder.
**Mitigation**: Bridge them before either system gets more complex.

### 3. Self-Build Track Consuming Revenue Time

**Risk level**: HIGH
**Evidence**: The binding constraint is leads → sales → revenue. Every hour spent on self-build is an hour not spent on outreach. The self-build track must be time-boxed.
**Mitigation**: Self-build is secondary track. Business test results should gate self-build scope.

### 4. Doctrine Accumulation Without Operationalization

**Risk level**: MEDIUM
**Evidence**: 30+ doctrines indexed in `current_doctrine_index.md`. Many are strategic/end-state and not operationally relevant today. No doctrine has been tested through actual workflow execution.
**Mitigation**: The first real operating day will reveal which doctrines actually constrain or enable execution.

---

## Safety Risks

1. **No safety risks from this test** — planning/review only, no code modifications
2. **Self-build track could introduce forbidden imports if implemented carelessly** — safety scanner gates this
3. **Phase 86 ↔ 88 bridge could break existing Phase 86 tests if orchestrator is modified** — must run regression
4. **Persistence layer could expose data if Neon RLS not configured for workflow tables** — addressed at implementation time

---

## Required Context

For the highest-leverage build (Phase 86 ↔ 88 bridge):

| Document | Why |
|----------|-----|
| `umh/tomorrow/contracts.py` | Understand TomorrowLoopState, DailyObjective, TomorrowHandoff types |
| `umh/tomorrow/orchestrator.py` | Understand state machine transitions and function signatures |
| `umh/workflows/contracts.py` | Understand DailyWorkflowPlan, WorkflowTask, IntegratedOperatingPlan types |
| `umh/workflows/north_star_harness.py` | Understand integrated plan builder |
| `umh/workflows/kpis.py` | Understand KPI record structure |
| `umh/workflows/review.py` | Understand review output structure |
| `docs/strategy/first_operating_workflow.md` | Ground truth for 16-stage workflow |
| `docs/system/phase86_tomorrow_operating_loop_report.md` | Phase 86 architecture decisions |
| `docs/system/phase88_first_workflow_test_harness_report.md` | Phase 88 architecture decisions |

---

## Required Tests

For the highest-leverage build:

1. Bridge function builds a TomorrowLoopState from an IntegratedOperatingPlan
2. Bridge converts WorkflowTasks to DailyObjectives
3. Bridge converts WorkflowResult KPIs to TomorrowHandoff kpi_snapshot
4. Bridge converts DailyWorkflowReview lessons to TomorrowHandoff continuity_notes
5. Bridge preserves existing Phase 86 state machine transitions
6. Existing Phase 86 tests still pass (81/81)
7. Existing Phase 88 tests still pass (100/100)
8. Existing North Star tests still pass (116/116)
9. Safety scan passes on bridge module
10. Bridge does not import forbidden modules

---

## Files Likely To Be Touched

### If building Phase 86 ↔ 88 bridge:

| File | Action | Risk |
|------|--------|------|
| `umh/workflows/tomorrow_bridge.py` | CREATE | LOW — new file |
| `umh/tomorrow/orchestrator.py` | MODIFY (add bridge entry point) or SKIP (bridge calls orchestrator externally) | MEDIUM |
| `tests/test_phase89_tomorrow_workflow_bridge.py` | CREATE | LOW — new file |
| `docs/system/phase89_tomorrow_workflow_bridge_report.md` | CREATE | LOW — docs only |

### NOT touched:

- `umh/workflows/contracts.py` — no changes needed
- `umh/workflows/first_workflow.py` — no changes needed
- `umh/tomorrow/contracts.py` — no changes needed (import only)

---

## Success Criteria

1. A single function call produces a complete daily operating plan that includes both tomorrow loop state AND workflow tasks
2. The operator can run `initialize_loop() → run_prepare() → run_brief()` and see workflow tasks in the briefing
3. End-of-day review feeds back into `run_handoff()` with workflow lessons
4. All existing tests pass (81 + 100 + 116 + rest of regression)
5. Safety scan clean
6. Bridge is additive — no existing module signatures broken
7. Time to implement: < 2 hours
8. The operator can use one system, not two disconnected systems

## Failure Criteria

1. Bridge breaks existing Phase 86 state machine
2. Bridge requires modifying Phase 86 contract types (type changes = regression risk)
3. Implementation takes > 4 hours (scope too large)
4. Bridge introduces forbidden imports or execution patterns
5. Bridge creates coupling that makes either system harder to test independently
6. Operator still needs to run two separate systems after bridge is built

---

## Recommended Next Prompt

```
You are Claude Code operating inside /opt/OS.

MISSION: Implement Phase 89 — Tomorrow Loop ↔ Workflow Harness Bridge v1.

READ FIRST:
- umh/tomorrow/contracts.py
- umh/tomorrow/orchestrator.py
- umh/workflows/contracts.py
- umh/workflows/north_star_harness.py
- umh/workflows/kpis.py
- umh/workflows/review.py
- docs/system/phase86_tomorrow_operating_loop_report.md
- docs/system/phase88_first_workflow_test_harness_report.md

OBJECTIVE:
Create a bridge that allows the Tomorrow Operating Loop (Phase 86) to
consume Workflow Plans (Phase 88) and produce unified daily briefings,
and allows Workflow Reviews to feed back into Tomorrow Handoffs.

CREATE:
- umh/workflows/tomorrow_bridge.py
- tests/test_phase89_tomorrow_workflow_bridge.py
- docs/system/phase89_tomorrow_workflow_bridge_report.md

The bridge must:
1. Convert IntegratedOperatingPlan → objectives for initialize_loop()
2. Convert WorkflowTask list → DailyObjective list for run_prepare()
3. Enrich run_brief() output with workflow highest-leverage actions
4. Convert WorkflowResult → structured input for run_review()
5. Convert DailyWorkflowReview lessons → TomorrowHandoff continuity_notes
6. Convert WorkflowKPIRecord list → kpi_snapshot for handoff

HARD RULES:
1. Do NOT modify Phase 86 contract types (DailyObjective, TomorrowHandoff, etc.)
2. Do NOT modify existing function signatures in orchestrator.py
3. Bridge is ADDITIVE ONLY — new file(s), no breaking changes
4. No forbidden imports (subprocess, requests, etc.)
5. No external API calls
6. No LLM calls
7. All existing Phase 86 tests must pass
8. All existing Phase 88 tests must pass
9. Safety scan must pass

VALIDATION:
- python3 -m py_compile umh/workflows/tomorrow_bridge.py
- pytest tests/test_phase89_tomorrow_workflow_bridge.py -q
- pytest tests/test_phase86_tomorrow_operating_loop.py -q
- pytest tests/test_phase88_first_workflow_test_harness.py -q
- pytest tests/test_phase88_north_star_operating_harness.py -q
```

---

## Decision

**PROCEED** — but only after business test results are reviewed.

**Rationale:**
The Phase 86 ↔ 88 bridge is the highest-leverage self-build action because it unifies the two systems the operator would actually use daily. However:

1. The business test may reveal that the workflow harness itself needs changes before bridging
2. Time allocation must prioritize business track tasks over self-build
3. The bridge should be scoped to < 2 hours implementation time
4. If the business test reveals the harness is unusable/wrong, fix that first

**Recommended time allocation:**
- Business track: 70% of operating hours
- Self-build track: 30% of operating hours
- Self-build today: review only (this packet). Build only after business test debrief.
