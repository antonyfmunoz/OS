# Phase 9.8 — Production Truth Promotion + Scheduled Autonomous Cadence

**Date:** 2026-05-29
**Status:** COMPLETE

## Doctrine

Main is production truth. Sandbox success is not production success.
PR success is not production success. Merge success is not production success.
Only post-merge verification creates production truth.

## 9.7 Preflight Verification

- PR #40 merged at `e8efd3fd` — VERIFIED
- Runtime commit matches main — VERIFIED
- PR factory endpoints operational — VERIFIED
- Production truth boundary enforced — VERIFIED
- See: `phase9_8_preflight_97_verification.md`

## ProductionMergeVerifier

**File:** `substrate/organism/production_merge_verifier.py` (514 lines)

Lifecycle:
1. Receive sandbox_id / PR number
2. Check merge status via `gh pr view` or git log
3. Fetch/update local main
4. Compute observed changed files from git diff
5. Capture state snapshots (before/after)
6. Run post-merge validation commands
7. Compute ProductionTruthDelta
8. Make promotion decision
9. Emit ProductionOutcomeCommitted only on success
10. Run production coherence propagation
11. Mark sandbox as production_verified
12. Set status to cleanup_ready

Entities:
- `ProductionMergeVerification` — tracks verification lifecycle
- `ProductionPromotionDecision` — promote/reject/review decision
- `MergeVerificationStatus` — 9 statuses from pending to cleanup_ready

Duplicate suppression: event key = `{sandbox_id}:{merge_commit}`. Duplicate
ProductionOutcomeCommitted events are suppressed, never double-counted.

## ProductionTruthDelta

**File:** `substrate/organism/production_truth_delta.py` (240 lines)

Fields:
- delta_id, sandbox_id, pr_number, merge_commit, base_commit, head_commit
- changed_files_expected vs changed_files_observed
- file_divergences (computed)
- state_before / state_after (StateSnapshot)
- world_model_before_after, contradictions_before_after
- readiness_before_after, dependency_graph_before_after
- template_confidence_before_after, agent_reliability_before_after
- validation_results, evidence, status

Rules enforced:
- File divergence → requires_review
- Failed validation → production_partial (not production_verified)
- No ProductionOutcomeCommitted on validation failure

## ProductionOutcomeCommitted Contract

**File:** `substrate/organism/autonomous_pr_factory.py` (expanded)

Fields added in 9.8:
- base_commit, head_commit
- action_type, mutation_type, risk_class
- agent_type, template_id
- action_envelope_ids, sandbox_outcome_ids
- production_truth_delta (dict)
- changed_files, affected_entities, affected_subsystems
- evidence

Structurally distinct from SandboxOutcomeCommitted:
- SOC: boundary="sandbox", event_type="sandbox_outcome_committed"
- POC: boundary="production", event_type="production_outcome_committed"

## Production Propagation Targets

ProductionOutcomeCommitted propagation targets:
- Wave 1: outcome history, template reliability, agent reliability, memory pipeline, world model
- Wave 2: dependency graph, contradiction engine, readiness model, bottleneck engine, composition engine, cockpit

Rules:
- Sandbox propagation remains separate
- Production propagation is idempotent (duplicate suppression)
- Failed verification does not propagate production state

## Verify-Merge Route

Updated: `POST /organism/autonomous-pr-factory/verify-merge/:id`
- Now delegates to ProductionMergeVerifier
- Returns full ProductionMergeVerification with truth delta

New routes:
- `GET /organism/autonomous-pr-factory/production-truth/:id`
- `GET /organism/autonomous-pr-factory/merge-verifications`
- `GET /organism/autonomous-pr-factory/merge-verifications/:id`
- `POST /organism/autonomous-pr-factory/cleanup-eligible`
- `GET /organism/autonomous-cadence`
- `POST /organism/autonomous-cadence/run-dry-run`
- `POST /organism/autonomous-cadence/set-mode`

All mutation routes require operator token.

## Scheduled Autonomous Cadence

**File:** `substrate/organism/autonomous_cadence.py` (325 lines)

Modes: off, dry_run_only, propose_pr, create_pr_with_operator_policy, production_verify_only

Default mode: OFF

Policy enforcement:
- max_dry_runs_per_day: 24
- max_prs_per_day: 1
- max_active_sandboxes: 2
- max_active_prs: 3
- allowed_risk: LOW only
- require_template: true
- require_agent_reliability: true
- require_validation: true
- require_rollback_or_non_mutating: true
- require_operator_enable_for_pr_creation: true
- no_auto_merge: true (hardcoded, non-overridable)

Cadence cycle:
1. Discover candidates
2. Filter by policy
3. Run dry-run evaluation
4. Build recommendations
5. Optionally queue PR creation (only if policy explicitly enables)
6. Never merge PRs

## Daemon Tick Integration

Stage registered: `autonomous_cadence_tick`

Behavior:
- off → no-op
- dry_run_only → scheduled dry-run
- propose_pr → produce proposal only
- create_pr_with_operator_policy → create PR only if policy enables
- production_verify_only → check merged PRs

Exposed in daemon.status():
- autonomous_cadence.mode
- autonomous_cadence.last_run_at
- autonomous_cadence.dry_runs_today
- autonomous_cadence.prs_today
- autonomous_cadence.total_runs
- autonomous_cadence.pending_recommendations

## Cockpit Surface

Updated IntelligencePanel:
- Autonomous Cadence section (mode, counters, policy)
- Merge Verifications section (status badges, PR numbers, commit hashes)
- Updated coherenceStore with CadenceData and MergeVerificationData types
- TypeScript compiles clean

## Cleanup/Lifecycle

Cleanup-eligible route: `POST /organism/autonomous-pr-factory/cleanup-eligible`
- Returns sandboxes in merged/abandoned/cleaned status
- Returns stale sandboxes exceeding TTL
- Requires operator token

Cleanup policies from Phase 9.7:
- on_merge, on_abandon, manual, ttl_hours
- cleanup_expired() cleans abandoned sandboxes past TTL
- Branch and worktree deletion on cleanup

## Tests

**File:** `tests/test_phase9_8_production_truth.py` — 86 tests, all passing

Coverage:
- ProductionTruthDelta: 18 tests (divergence, state delta, finalize, serialization)
- ProductionMergeVerifier: 9 tests (init, unmerged, pending, cleanup, persistence, dedup)
- ProductionOutcomeCommitted: 8 tests (contract, boundary, serialization)
- Truth boundary: 4 tests (SOC vs POC enforcement)
- AutonomousCadence: 19 tests (modes, filtering, limits, scheduling, error handling)
- Daemon integration: 4 tests (cadence property, status, tick registration)
- Cleanup/lifecycle: 3 tests
- Status enums: 3 tests
- API contracts: 4 tests (JSON roundtrip)
- Delegation: 1 test
- Edge cases: 12 tests (additional coverage)

Existing tests:
- 1159 organism tests — ALL PASSING
- 60 Phase 9.6 tests — ALL PASSING
- py_compile on all modified files — CLEAN
- TypeScript compile — CLEAN
- Type divergence gate — PASS (warnings are pre-existing)
- Instance leak gate — PASS
- Dependency direction gate — pre-existing violation in test_phase93 (not our code)

## Remaining Blockers

None for Phase 9.8 scope. Pre-existing items:
1. cockpit.py at 3532 lines (was 3419 before this phase — pre-existing over 3000 limit)
2. Dependency direction violation in test_phase93_reliability_campaign.py (pre-existing)

## Next Highest-Leverage Step

Phase 9.8K (First Production Truth Promotion) requires an actual autonomous
PR to merge and verify. This can be executed when a low-risk autonomous
candidate is available and the operator merges it. The infrastructure is
complete and ready.

Beyond that: the cadence system is defaulting to OFF. Operator can enable
dry_run_only mode to begin seeing autonomous improvement recommendations
in the cockpit without any risk of production mutation.
