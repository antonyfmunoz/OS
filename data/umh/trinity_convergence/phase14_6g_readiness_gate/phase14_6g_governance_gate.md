---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "UMH governance stack (risk_classes.py, policy_engine.py, governance.py)"
  - "Architecture Layer Law and pre-commit gates"
  - "Phase 14.6G acceptance criteria and work packets"
---

# Phase 14.6G: Governance Gate

## What This Is

This document defines the exact conditions required to open the UMH Stage 1 implementation gate. Implementation CANNOT begin until these conditions are met and the operator explicitly approves.

## Gate Conditions

### Condition 1: Source-Truth Checks

Before implementation begins, the following must be verified:

| Check | Command | Expected |
|-------|---------|----------|
| All 18 P0 decisions reflected in canon | Run test_phase14_6f_canon_revision.py | All tests pass |
| No stale contradictions in canon | Run test_phase14_6g_readiness_gate.py | All tests pass |
| Implementation gates closed in all artifacts | `grep -r "allows_implementation: true" data/umh/` | Zero results |
| Product name canonical | `grep -r "Universal Mastery Hierarchy" data/umh/` returns only debt/gap docs | Verified |
| Pre-commit gates pass | `python3 scripts/check_dependency_direction.py --all` | Exit 0 |
| Pre-commit gates pass | `python3 scripts/check_type_divergence.py --all` | Exit 0 |
| Pre-commit gates pass | `python3 scripts/check_instance_leak.py --all` | Exit 0 |
| Pre-commit gates pass | `python3 scripts/check_projection_leak.py --all` | Exit 0 |

### Condition 2: Branch and Worktree Rules

| Rule | Requirement |
|------|-------------|
| Implementation branch | Create `stage1-wave-N` branches from `main` for each wave |
| Worktree isolation | Each implementation wave uses a dedicated git worktree |
| No direct main commits | All Stage 1 implementation goes through PR review |
| Worktree cleanup | Remove worktrees immediately after merge |
| Branch cleanup | Delete local branches after merge; run `git gc --prune=now` after bulk cleanup |

### Condition 3: Allowed Mutation Scope

Implementation is scoped to these directories only:

| Directory | Allowed Mutations | Restrictions |
|-----------|-------------------|-------------|
| `transports/api/cockpit*.py` | Add/modify HTTP routes for reality model, memory, execution, work packets | Do not remove existing working routes |
| `transports/api/http/routes/` | Add TypeScript route files | Follow existing patterns |
| `cockpit/src/renderer/` | Modify panels, stores, services to wire to new endpoints | Do not remove existing panels |
| `substrate/organism/work_packet_engine.py` | Extend with routing, outcome recording, verification triggers | Do not modify WorkPacket dataclass |
| `substrate/execution/spine.py` | Wire execution control (start/pause/resume/stop) | Do not modify the 8-stage pipeline logic |
| `tests/` | Add Stage 1 acceptance tests | Do not modify passing tests |

**Explicitly FORBIDDEN mutations:**

| Directory/File | Reason |
|----------------|--------|
| `substrate/types.py` | Type coherence law -- no new types without canonical_types.py check |
| `substrate/reality_model/*.py` | Production code -- extend via routes, not modification |
| `substrate/state/memory/memory.py` | Production code -- call existing methods, don't modify |
| `adapters/models/model_router.py` | CONFIRMED_RUNTIME -- do not touch |
| `substrate/governance/` | Production governance stack -- do not modify risk classifications |
| `services/discord_bot.py` | Production service -- do not touch during Stage 1 |
| `saas/` | EOS projection -- blocked until Stage 1 complete |
| `projections/` | Projection configs -- blocked until Stage 1 complete |
| Database schemas | No schema migrations without explicit separate approval |

### Condition 4: Approval Levels

| Risk Level | Approval Required | Approver |
|------------|-------------------|----------|
| LOW | Automated (pre-commit gates pass) | System |
| MEDIUM | Operator review of PR diff | AFM |
| HIGH | Operator review + explicit approval message | AFM |
| CRITICAL | Operator review + explicit approval + rollback plan documented | AFM |
| FORBIDDEN | Never permitted | N/A |

Work packet risk level determines PR approval level:

| Wave | Packets | Risk Level | Approval Level |
|------|---------|------------|----------------|
| Wave 1 | WP-1.1 through WP-1.4 | MEDIUM | Operator PR review |
| Wave 2 | WP-2.1 through WP-2.4 | MEDIUM | Operator PR review |
| Wave 3 | WP-3.1 through WP-3.4 | LOW-MEDIUM | Operator PR review |

### Condition 5: Test Requirements

| Requirement | Specification |
|-------------|---------------|
| Pre-implementation | All existing tests pass (845+ from Phase 14.6C/D/E/F) |
| Per work packet | Each packet adds tests verifying its acceptance criteria |
| Per wave gate | All wave tests pass before proceeding to next wave |
| Stage 1 complete | All 50 acceptance criteria tests pass (from phase14_6g_stage1_acceptance_criteria.md) |
| Pre-commit gates | All 4 architecture gates pass on every commit |
| No regressions | Existing test count never decreases |

### Condition 6: Rollback Requirements

| Scope | Rollback Method |
|-------|----------------|
| Per work packet | Each packet specifies rollback expectation |
| Per wave | `git revert` the wave branch merge commit |
| Full Stage 1 | Revert all wave merges; system returns to pre-14.7A state |
| Data rollback | Reality model and memory data persists through code rollbacks (data is append-only) |

### Condition 7: Audit Requirements

| Audit | When | What |
|-------|------|------|
| Pre-wave | Before starting each wave | Verify previous wave gate passed |
| Post-wave | After completing each wave | Run wave acceptance criteria tests |
| Architecture audit | After each PR | All 4 pre-commit gates pass |
| Final audit | After Wave 3 | All 50 acceptance criteria pass; comprehensive audit report |
| Canon consistency | After Stage 1 | Verify canon artifacts still accurate after implementation |

## Implementation Gate Opening Procedure

To open the implementation gate for Phase 14.7A, the operator must:

1. **Read** this governance gate document
2. **Read** phase14_6g_stage1_readiness_gate.md (the overview)
3. **Read** phase14_6g_stage1_acceptance_criteria.md (what success looks like)
4. **Read** phase14_6g_stage1_work_packet_index.md (what will be built)
5. **Read** phase14_6g_stage1_dependency_graph.md (build sequence)
6. **Read** phase14_6g_projection_dependency_gate.md (when projections can start)
7. **Approve** by explicit message: "Approve Phase 14.7A implementation gate"
8. **Specify** which wave to begin (Wave 1 recommended)

The implementation gate opens ONLY after step 7. No implicit approval. No assumed approval. No approval by proximity.

## What This Gate Does NOT Authorize

Even after the implementation gate opens:
- Individual CRITICAL-risk work packets still require separate operator approval
- Schema migrations still require separate operator approval
- Projection app implementation remains blocked until Stage 1 Wave 3 is complete
- Autonomous cadence `dry_run_only` remains true until separate operator decision
- Production deployments (Fly.io, Docker) require separate confirmation
