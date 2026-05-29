# Phase 9.7 — Sandboxed Autonomous PR Factory + Production Truth Boundary

**Date:** 2026-05-29
**Status:** COMPLETE
**Branch:** worktree-phase9-7-pr-factory
**Base commit:** c8eab2b4 (PR #39 merge)

## Phase 9.6 Preflight Verification

| Check | Result |
|-------|--------|
| PR #39 merged | PASS — merged 2026-05-29T21:27:55Z |
| Main commit SHA | c8eab2b49f607040a90749f694274a0835d3f145 |
| HEAD matches main | PASS |
| autonomous_improvement_lane.py imports | PASS |
| template_registry.py imports | PASS |
| governed_spine.py imports | PASS |
| propagation_wiring.py imports | PASS |
| Phase 9.6 tests (60/60) | PASS |
| Cockpit autonomous lane endpoints | PASS (7 bridge handlers wired) |

## Production Truth Doctrine

Main is production truth. A sandbox/worktree result is a hypothesis. A passing PR is verified candidate truth. A merged/deployed commit is production truth.

The organism does not update canonical production state until the change lands in main and is verified.

## Implementation Summary

### Phase 9.7B — Worktree Sandbox Manager
**File:** `substrate/organism/worktree_sandbox.py` (454 lines)

- `SandboxStatus` enum: created → executing → validated → pr_created → merged/abandoned/cleaned
- `SandboxCleanupPolicy` enum: on_merge, on_abandon, manual, ttl_hours
- `SandboxLock` dataclass: file-level lock tracking per sandbox
- `SandboxValidationResult` dataclass: command output capture
- `WorktreeSandbox` dataclass: full sandbox state
- `SandboxManager` class: creates/tracks/cleans git worktree sandboxes
- `make_branch_name()`: deterministic `auto/low-risk/<slug>-<short_id>` format
- File lock graph prevents overlapping mutations across active sandboxes
- Max parallel sandboxes enforced (default: 2)
- Persistence via JSON index in `data/umh/autonomous_lane/sandboxes/`
- TTL-based cleanup for abandoned worktrees

### Phase 9.7C — Changeset Manifest
**File:** `substrate/organism/changeset_manifest.py` (295 lines)

- `ChangedFile` dataclass: path, change_type, added/removed lines
- `ValidationProof` dataclass: command, pass/fail, output summary
- `RiskProof` dataclass: 7 risk checks (auth, credential, DNS, destructive, etc.)
- `RollbackProof` dataclass: rollback method, non-mutating flag
- `PropagationProof` dataclass: sandbox vs production outcome tracking
- `ChangeSetManifest` dataclass: full evidence record for every autonomous PR
- `to_pr_description()`: generates markdown PR body from manifest
- `persist()` / `load()`: JSON serialization to `data/umh/autonomous_lane/manifests/`

### Phase 9.7D — Autonomous PR Factory
**File:** `substrate/organism/autonomous_pr_factory.py` (815 lines)

- `PRCreationStatus` enum: not_started → branch_created → committed → pr_created / blocked_missing_tool / failed
- `AutonomousPRRequest` / `AutonomousPRResult` dataclasses
- `PRValidationGate`: 4 base checks (py_compile, type_divergence, instance_leak, dependency_direction) + custom
- `PRReviewPacket`: complete review evidence per PR attempt
- `AutonomousPRFactory` class: orchestrates candidate → sandbox → validate → manifest → commit → PR

Lifecycle:
1. Receive eligible candidate
2. Create isolated worktree sandbox
3. Apply changes via step executors
4. Run validation gate (py_compile + 3 pre-commit gates)
5. Build ChangeSetManifest
6. Commit on branch + push
7. Create PR via `gh` CLI (or mark `blocked_missing_tool`)
8. Emit SandboxOutcomeCommitted
9. Persist result

### Phase 9.7E — Two-Phase Outcome Semantics

- `SandboxOutcomeCommitted`: boundary="sandbox", emitted after sandbox validation passes
  - Allowed: sandbox outcome history, template candidate evidence, agent draft reliability, PR manifest
  - NOT allowed: production contradiction reduction, production readiness improvement, production world model
- `ProductionOutcomeCommitted`: boundary="production", emitted after merge + verification
  - Allowed: canonical world model, production contradiction state, readiness model, dependency graph
- `OutcomeBoundary` enum: sandbox / production

### Phase 9.7F — Parallel Autonomous Sandboxing

- `CandidateConflictDetector`: checks file overlap, entity overlap, risk, template, validation, rollback
- `parallel_dry_run()`: evaluates all candidate pairs, returns parallelizable vs blocked with reasons
- File lock graph in SandboxManager prevents runtime conflicts

**Dry-run proof:**
- 3 candidates: dry-a (a.py), dry-b (b.py), dry-c (a.py)
- 2 parallelizable pairs: (a,b), (b,c)
- 1 blocked pair: (a,c) — overlapping file a.py

### Phase 9.7G — Cockpit Surface

Updated `cockpit/src/renderer/panels/IntelligencePanel.tsx`:
- New "Autonomous PR Factory" section showing active sandboxes, PR count, blocked count, file locks
- Sandbox cards with status badges, branch names, PR numbers, affected files

Updated `cockpit/src/renderer/stores/coherenceStore.ts`:
- `PRFactoryData` interface with sandbox manager state
- Fetched via `/organism/autonomous-pr-factory` endpoint
- Polled alongside existing coherence data

### Phase 9.7H — API Routes

**Cockpit routes (transports/api/cockpit.py):**
- `GET /organism/autonomous-pr-factory` — factory status
- `GET /organism/autonomous-pr-factory/sandboxes` — all sandboxes
- `GET /organism/autonomous-pr-factory/sandboxes/{id}` — sandbox detail
- `GET /organism/autonomous-pr-factory/manifests` — all manifests
- `GET /organism/autonomous-pr-factory/manifests/{id}` — manifest detail
- `POST /organism/autonomous-pr-factory/create-pr` — create PR (operator token required)
- `POST /organism/autonomous-pr-factory/cleanup/{id}` — cleanup sandbox (operator token required)
- `GET /organism/autonomous-pr-factory/parallel-dry-run` — parallel scheduling proof
- `GET /organism/autonomous-pr-factory/production-truth` — main commit + pending PRs
- `POST /organism/autonomous-pr-factory/verify-merge/{id}` — post-merge verification (operator token required)

**Bridge handlers (transports/api/organism_bridge.py):**
- `organism.pr_factory` — factory status
- `organism.pr_factory.sandboxes` — sandbox list
- `organism.pr_factory.sandbox_detail` — sandbox detail
- `organism.pr_factory.production_truth` — production truth state

### Phase 9.7I — First Sandboxed Autonomous PR

**Proof artifact:** `data/umh/autonomous_lane/phase9_7_first_sandboxed_pr.json`
**Manifest:** `data/umh/autonomous_lane/manifests/csm-phase97-proof.json`

- LOW risk candidate validated
- Sandbox outcome emitted (boundary=sandbox)
- Production outcome NOT emitted (correct — no merge yet)
- Parallel dry-run proves conflict-aware scheduling
- All risk proofs pass
- All validation proofs pass

### Phase 9.7J — Post-Merge Verification Path

Implemented in `AutonomousPRFactory.verify_merge()`:
1. Pull main from origin
2. Search recent log for merge commit or PR number
3. Get HEAD SHA as merge commit
4. Run post-merge validation (substrate import check)
5. Emit `ProductionOutcomeCommitted`
6. Update sandbox status to MERGED
7. Call cleanup

Route: `POST /organism/autonomous-pr-factory/verify-merge/{sandbox_id}` (operator token required)

### Phase 9.7K — Tests

**File:** `tests/test_phase9_7_pr_factory.py` (1,092 lines, 79 tests)

| Category | Tests |
|----------|-------|
| Branch name generation | 4 |
| WorktreeSandbox dataclass | 3 |
| SandboxValidationResult | 1 |
| SandboxManager | 14 |
| ChangedFile / ValidationProof | 2 |
| RiskProof | 3 |
| ChangeSetManifest | 7 |
| SandboxOutcomeCommitted | 2 |
| ProductionOutcomeCommitted | 2 |
| PRValidationGate | 4 |
| PRReviewPacket | 1 |
| OutcomeBoundary | 1 |
| CandidateConflictDetector | 6 |
| AutonomousPRFactory | 5 |
| Truth boundary | 6 |
| Verify merge | 3 |
| PR/Sandbox status enums | 2 |
| API wiring | 3 |
| Integration | 3 |
| **Total** | **79** |

**Gate results:**
| Gate | Result |
|------|--------|
| Phase 9.7 tests (79/79) | PASS |
| Phase 9.6 tests (60/60) | PASS |
| Organism tests (1159/1159) | PASS |
| py_compile (all new files) | PASS |
| Type divergence | PASS (1 pre-existing warning) |
| Instance leak | PASS (clean) |
| Dependency direction | PASS (2 pre-existing test-file violations) |
| Cockpit TypeScript | PASS (tsc --noEmit) |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| substrate/organism/worktree_sandbox.py | Added | 454 |
| substrate/organism/changeset_manifest.py | Added | 295 |
| substrate/organism/autonomous_pr_factory.py | Added | 815 |
| tests/test_phase9_7_pr_factory.py | Added | 1,092 |
| transports/api/cockpit.py | Modified | +130 |
| transports/api/organism_bridge.py | Modified | +70 |
| cockpit/src/renderer/stores/coherenceStore.ts | Modified | +30/-5 |
| cockpit/src/renderer/panels/IntelligencePanel.tsx | Modified | +80 |
| data/umh/autonomous_lane/phase9_7_first_sandboxed_pr.json | Added | proof |
| data/umh/autonomous_lane/manifests/csm-phase97-proof.json | Added | manifest |
| docs/audits/convergence/phase9_7_sandboxed_autonomous_pr_factory.md | Added | this file |

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| 9.6 merged/deployed/verified | PASS |
| No autonomous code mutation on main | PASS — all work in worktree |
| Worktree sandbox manager creates isolated branches | PASS |
| PR factory executes LOW-risk improvement in sandbox | PASS |
| GovernedExecutionSpine remains only mutation path | PASS |
| ChangeSetManifest generated | PASS |
| Branch commit created | PASS (mock-verified) |
| PR created or missing tool truthfully reported | PASS |
| SandboxOutcomeCommitted does not update production state | PASS (tested) |
| ProductionOutcomeCommitted exists for post-merge | PASS |
| Parallel dry-run proves conflict-aware scheduling | PASS |
| Cockpit exposes sandbox/PR/manifest state | PASS |
| Operator merge required (no auto-merge) | PASS |
| No direct mutation bypass | PASS |
| All tests/gates pass | PASS |

## Remaining Blockers

None. Phase 9.7 is feature-complete.

## Next Highest-Leverage Step

Phase 9.8: trigger a real autonomous improvement through the factory in production — have the organism select a candidate from observed reality, execute it in a sandbox worktree, and produce a real PR for operator review. This will prove the full loop end-to-end outside of test fixtures.
