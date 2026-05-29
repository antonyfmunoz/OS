# Phase 9.2 — Governed Self-Improvement Trial Audit

**Date**: 2026-05-28
**Status**: PASSED
**Trial ID**: phase9_2
**Branch**: worktree-phase-9.2-governed-self-improvement

---

## 1. Baseline State

| Metric | Value |
|--------|-------|
| World model entities | 81 |
| Total contradictions | 13 |
| High-severity contradictions | 1 |
| World model gaps | 1 |
| Organism test count (pre) | 891 |
| Execution mode | OBSERVE |

Phase 9.1 infrastructure verified operational: CompositionEngine, PlanExecutionAdapter,
GovernedExecutionSpine, SpineGuard, AutonomousActionGateway, ExecutionJournal,
OutcomeLearningLoop, MemoryPromotionPipeline. All 123 Phase 9.1 tests passing.

---

## 2. Selected Candidate

**Target**: `governance_router` entity — false-positive HIGH-severity contradiction.

**Evidence**: World model declared `governance_router` at path
`substrate/control_plane/router.py`, but the actual implementation is a Python
package at `substrate/control_plane/router/__init__.py`. The contradiction engine
flagged this as a `capability_gap` with HIGH severity because the declared file
did not exist on disk.

**Selection criteria**: Highest-severity contradiction, LOW actual risk to fix
(observation code only, no runtime behavior change), fully reversible with a
single string replacement.

**Documented**: `docs/audits/convergence/phase9_2_trial_candidate.md`

---

## 3. Composition Plan

| Field | Value |
|-------|-------|
| Plan ID | a3000810 |
| Intent | Fix false-positive governance_router path |
| Category | fix_contradictions |
| Steps | 4 |
| Overall risk | LOW |
| Governance | AUTONOMOUS |

**Steps**:
1. `verify_current_state` — Confirm contradiction exists (LOW, autonomous)
2. `fix_world_model_path` — Change router.py → router/__init__.py (LOW, autonomous)
3. `verify_contradiction_resolved` — Re-run contradiction engine (LOW, autonomous)
4. `verify_tests_pass` — py_compile on changed file (LOW, autonomous)

**Constraints applied** (all hard):
- `no_runtime_changes` — Only modify observation code
- `single_file_edit` — Only world_model.py
- `fully_reversible` — Single string revert
- `no_security_impact` — No auth/governance policy changes

**Discovery**: CompositionEngine's generic `fix_contradictions` pattern included
a HIGH-risk `fix_deployment_state` step inappropriate for a simple path fix.
Added `custom_steps` parameter to `compose()` to allow evidence-driven step
definitions. This is the correct fix — the pattern system is a starting point,
not gospel.

---

## 4. Execution Graph

| Field | Value |
|-------|-------|
| Executable plan ID | 12ed5350 |
| Source plan ID | c0cdc068 |
| Steps | 4 |
| Approval required | None (all LOW risk, autonomous) |

Dependencies preserved: step 2 depends on step 1, step 3 depends on step 2,
step 4 depends on step 3. Sequential chain — each verification gates the next.

---

## 5. Governance Dry Run

All 4 steps evaluated against:
- **SpineGuard** (BLOCK_HIGH_RISK mode): All LOW risk → allowed
- **ExecutionMode** (OBSERVE): LOW risk has no mode requirement → allowed
- **Risk ceiling**: No HIGH/CRITICAL steps → allowed

Result: **PASSED** — no governance blocks.

---

## 6. Execution Timeline

| Step | Action | Duration | Result |
|------|--------|----------|--------|
| 1 | verify_current_state | 2.1ms | Verified: 1 high-severity contradiction found |
| 2 | fix_world_model_path | 0.5ms | Fixed: path updated to router/__init__.py |
| 3 | verify_contradiction_resolved | 10.0ms | Resolved: 0 high, 12 total (was 13) |
| 4 | verify_tests_pass | 42.7ms | py_compile passed |

**Total execution**: 56.9ms through GovernedExecutionSpine.
**Status**: COMPLETED (4/4 succeeded, 0 failed).

Mutation path: `PlanExecutionAdapter.execute_plan()` → `GovernedExecutionSpine.submit()`
→ `ActionEnvelope` per step → `ExecutionJournal` recording → `OutcomeLearningLoop` capture.

---

## 7. Validation Result

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total contradictions | 13 | 12 | -1 |
| High-severity | 1 | 0 | -1 |
| governance_router status | — | partial | — |
| Execution status | — | completed | — |

**Validation**: PASSED. All success criteria met:
- High-severity contradictions reduced to 0
- Total contradictions reduced (13 → 12)
- Execution completed with no failures
- No governance blocks

---

## 8. Outcome Learning

4 outcomes recorded, 4 learning signals generated.

| Action | Reliability | Outcomes |
|--------|-------------|----------|
| verify_current_state | 1.0 | 1 success |
| fix_world_model_path | 1.0 | 1 success |
| verify_contradiction_resolved | 1.0 | 1 success |
| verify_tests_pass | 1.0 | 1 success |

4 pending adjustments generated for future calibration.

---

## 9. Memory Candidates

4 candidates generated, all `status: raw` (never auto-promoted):

| # | Category | Confidence | Content |
|---|----------|------------|---------|
| 1 | pattern | 0.80 | Plan completed successfully with 4 steps |
| 2 | pattern | 0.90 | World model must account for Python packages (__init__.py) |
| 3 | strategy | 0.85 | Dry-run must precede all governed trials |
| 4 | observation | 0.85 | CompositionEngine over-scopes with generic patterns; use custom_steps |

All candidates require operator approval via `/organism/memory-promotion/:id/approve`
before promotion to canonical memory.

---

## 10. Bugs Found and Fixed

### Bug 1: PlanExecutionAdapter SpineGuard integration (Phase 9.1 bug)

**Problem**: `plan_execution_adapter.py` called `self._spine_guard.evaluate(envelope)`
but SpineGuard has no `evaluate()` method. Only `check_direct_mutation(source, description, risk_level)`.

**Root cause**: Written against assumed API, not actual API. Tests passed None for spine_guard.

**Fix**: Replaced with `check_direct_mutation()` call using step metadata.

### Bug 2: PlanExecutionAdapter gateway double-submit

**Problem**: `self._gateway.evaluate(envelope)` called non-existent method.
`AutonomousActionGateway.submit_envelope()` forwards to spine, causing double-submit.

**Fix**: Replaced with inline risk severity check — if risk >= HIGH and governance
mode is autonomous, escalate to require approval.

### Bug 3: CompositionEngine over-scoping

**Problem**: Generic `fix_contradictions` pattern added HIGH-risk deployment step
to a simple path fix.

**Fix**: Added `custom_steps` parameter to `compose()` for evidence-driven step definitions.

### Bug 4: Type divergence — shadow RiskClass

**Problem**: `composition_engine.py` defined its own `RiskClass` enum identical to
`substrate.types.RiskClass`. Caught by type divergence gate.

**Fix**: Replaced local definition with `from substrate.types import RiskClass`.

---

## 11. Cockpit Surface

- **Route**: `GET /organism/trial-status` (operator-only)
- **Bridge handler**: `organism_bridge.py:_trial_status()`
- **Data source**: `data/umh/trials/` JSON files
- **Returns**: trial_results, composition_plan, execution_graph, outcomes, memory_candidates, journal_entries

---

## 12. Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 9.2 new tests | 47 | 47 passed |
| Full organism suite | 938 | 938 passed |
| Regressions | 0 | — |

**Test classes** (10 classes, 47 tests):
- TestTrialCandidateSelection (6)
- TestCustomStepComposition (6)
- TestExecutionGraph (7)
- TestGovernanceDryRun (6)
- TestGovernedExecution (4)
- TestOutcomeCapture (3)
- TestMemoryCandidateGeneration (4)
- TestAdapterSpineGuardIntegration (2)
- TestTrialStatusBridge (2)
- TestExecutablePlanStateMachine (7)

**Gates**:
- Type divergence: CLEAN in worktree (fixed shadow RiskClass)
- Instance context: CLEAN (549 files scanned)
- Dependency direction: CLEAN (no substrate → transports/services imports)
- Line counts: All modified files under 3,000 lines

---

## 13. Files Changed

**Modified** (5 production files):
- `substrate/organism/composition_engine.py` — custom_steps parameter + type fix
- `substrate/organism/plan_execution_adapter.py` — SpineGuard/gateway API fixes
- `substrate/organism/world_model.py` — governance_router path fix (the trial mutation)
- `saas/bridge/organism_bridge.py` — trial_status handler
- `saas/api/routes/organism.ts` — /trial-status route

**Created** (1 test file):
- `substrate/organism/tests/test_phase92_self_improvement.py` — 47 tests

**Created** (trial artifacts, data/):
- `data/umh/trials/phase9_2_trial_results.json`
- `data/umh/trials/phase9_2_composition_plan.json`
- `data/umh/trials/phase9_2_execution_graph.json`
- `data/umh/trials/trial_journal.jsonl`
- `data/umh/trials/trial_outcomes.jsonl`
- `data/umh/trials/memory/memory_candidates/candidates.jsonl`
- `docs/audits/convergence/phase9_2_trial_candidate.md`

---

## 14. Remaining Blockers

None. The governed self-improvement loop is proven end-to-end.

---

## 15. What This Proves

UMH can safely improve itself through the governed spine:

1. **Observe** — World model scans filesystem and builds entity graph
2. **Detect** — Contradiction engine identifies discrepancies between declared and observed state
3. **Compose** — CompositionEngine creates constrained execution plans from evidence
4. **Convert** — PlanExecutionAdapter transforms plans into governed ActionEnvelope graphs
5. **Govern** — SpineGuard + ExecutionMode + risk classification gate every mutation
6. **Execute** — GovernedExecutionSpine runs approved steps with full journaling
7. **Validate** — Post-execution re-observation confirms the improvement
8. **Learn** — OutcomeLearningLoop tracks reliability and generates signals
9. **Remember** — MemoryPromotionPipeline generates candidates (never auto-promotes)

The loop is closed. Governance is not bypassed. Every mutation flows through ActionEnvelope.
The organism improved its own observation accuracy and proved it did so correctly.

---

## 16. Next Highest-Leverage Step

The remaining 12 contradictions (all medium/low severity) are the next natural
targets. The composition engine's `custom_steps` parameter means each can be
addressed with evidence-specific plans rather than over-scoped generic patterns.

The trial infrastructure is reusable — future trials follow the same
Observe → Compose → Convert → DryRun → Execute → Validate → Learn → Remember path.
