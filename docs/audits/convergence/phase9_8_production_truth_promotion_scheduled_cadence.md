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

**File:** `substrate/organism/production_merge_verifier.py` (598 lines)

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
- `MergeVerificationStatus` — 12 statuses from pending to cleanup_ready

Duplicate suppression: event key = `{sandbox_id}:{merge_commit}`. Duplicate
ProductionOutcomeCommitted events are suppressed, never double-counted.

## ProductionTruthDelta

**File:** `substrate/organism/production_truth_delta.py` (311 lines)

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

Exposed in daemon.status() — 9 new top-level fields:
- autonomous_cadence_mode
- last_dry_run_at
- last_candidate_count
- last_recommendation_count
- active_sandbox_count
- active_pr_count
- pending_merge_verification_count
- last_production_truth_delta_id
- last_production_outcome_at

## Cockpit Surface

Updated IntelligencePanel:
- Autonomous Cadence section with controls (mode, counters, last run result, dry-run button, mode toggle)
- Production Truth section (production outcomes count, sandbox outcomes, pending verifications, cleanup ready, last delta ID)
- Merge Verifications section (status badges, PR numbers, commit hashes)
- Updated coherenceStore with CadenceData, MergeVerificationData, and ProductionTruthData types
- Added actions: runDryRun(), setCadenceMode(), verifyMerge(), cleanupEligible()
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

## Security Preflight (PR #42)

See: `phase9_8_security_preflight_pr42.md`

Fixes applied before Phase 9.8 implementation:
- Path traversal protection on all ID parameters (regex validation)
- Missing auth on `GET /organism/autonomous-pr-factory/production-truth`
- All production truth endpoints now require operator token

## First Production Truth Promotion

**File:** `data/umh/autonomous_lane/phase9_8_first_production_truth_promotion.json`

PR #42 (security fixes) verified as production truth:
- Merge detected on main at `d1543edf`
- Expected files match observed files (2/2)
- 32 lines added, 20 removed
- All post-merge validations passed
- ProductionOutcomeCommitted emitted with idempotency key
- Wave 1 + Wave 2 propagation targets documented

## Tests

**File:** `tests/test_phase9_8_production_truth.py` — 140 tests, all passing
**File:** `tests/test_phase9_7_pr_factory.py` — 79 tests, all passing (regression fixed)

Phase 9.8 test coverage (140 tests):
- ProductionTruthDelta: 18 tests (divergence, state delta, finalize, serialization)
- ProductionMergeVerifier: 9 tests (init, unmerged, pending, cleanup, persistence, dedup)
- ProductionOutcomeCommitted: 8 tests (contract, boundary, serialization)
- MergeVerificationStatus extended: 3 tests (new statuses)
- ProductionTruthDelta extended fields: 5 tests (line counts, bottlenecks, mismatch)
- Idempotency key: 5 tests (format, uniqueness, determinism)
- Security extended: 6 tests (path traversal, regex validation)
- Thread-safe duplicate suppression: 5 tests (concurrent emission)
- Production propagation waves: 6 tests (wave 1, wave 2, sequencing)
- Daemon status extended: 5 tests (new fields)
- Truth boundary extended: 5 tests (sandbox vs production)
- Verifier expected-observed mismatch: 5 tests
- Cadence policy extended: 5 tests
- Compute line counts: 5 tests
- ProductionTruthDelta finalize: 5 tests (all paths)
- Truth boundary: 4 tests (SOC vs POC enforcement)
- AutonomousCadence: 19 tests (modes, filtering, limits, scheduling, error handling)
- Daemon integration: 4 tests (cadence property, status, tick registration)
- Cleanup/lifecycle: 3 tests
- Status enums: 3 tests
- API contracts: 4 tests (JSON roundtrip)
- Delegation: 1 test

Phase 9.7 regression fix:
- `test_verify_merge_found` was failing due to mock returning "ok\n" for git diff commands
- Fix: added explicit "diff" case returning empty stdout, changed fallthrough to empty stdout
- Root cause: mock stdout parsed as filename, creating false file divergence

Cross-phase verification:
- 219 total tests (79 Phase 9.7 + 140 Phase 9.8) — ALL PASSING
- py_compile on all modified files — CLEAN
- TypeScript compile — CLEAN
- Type divergence gate — PASS (warnings are pre-existing)
- Instance leak gate — PASS
- Dependency direction gate — pre-existing violation in test_phase93 (not our code)

## MergeVerificationStatus — Extended (Phase 9.8)

Added 3 new statuses to the original 9:
- `PR_NOT_FOUND` — gh pr view returned non-zero or unparseable JSON
- `MAIN_UPDATE_FAILED` — git fetch origin main failed
- `EXPECTED_OBSERVED_MISMATCH` — file divergence between expected and observed changes

Total: 12 statuses covering full lifecycle from `pending` to `cleanup_ready`.

## ProductionTruthDelta — Extended Fields (Phase 9.8)

- `manifest_id` — links delta to source changeset manifest
- `added_lines_expected`, `removed_lines_expected` — expected line counts
- `added_lines_observed`, `removed_lines_observed` — from `git diff --stat`
- `bottlenecks_before_after` — bottleneck engine state delta
- `mismatch_reasons` — per-file divergence reasons
- `requires_operator_review` — flag set on divergence or partial validation

## ProductionOutcomeCommitted — Extended (Phase 9.8)

- `production_validation_result` — dict with all_passed, results, file_divergence, mismatch_reasons
- `idempotency_key` — `production_outcome:{merge_commit}:{manifest_id}:{validation_hash}`
- Thread-safe duplicate suppression with `threading.Lock`

## Remaining Blockers

None for Phase 9.8 scope. Pre-existing items:
1. cockpit.py at ~3240 lines (pre-existing over 3000 limit)
2. Dependency direction violation in test_phase93_reliability_campaign.py (pre-existing)

## Next Highest-Leverage Step

The autonomous lane infrastructure is complete through Phase 9.8.
The cadence system defaults to OFF. Operator can enable `dry_run_only`
mode via cockpit to begin seeing autonomous improvement recommendations
without any risk of production mutation.

To run a real production truth promotion:
1. Enable `dry_run_only` mode in cockpit
2. Review a dry-run recommendation
3. Enable `create_pr_with_operator_policy` when ready
4. Autonomous lane creates PR, operator reviews and merges
5. Production merge verifier confirms production truth
6. ProductionOutcomeCommitted emits, coherence propagation runs
