# Phase 10.5 — Reliability-Weighted Cadence Ranking + Promotion Thresholds

**Date:** 2026-05-30
**Executor:** Phase 10.5 automated build
**Prerequisite:** Phase 10.4R complete (all 4 campaign loops closed, 100% success rate)
**Scope:** Convert production truth campaign outcomes into reliability-weighted cadence judgment

## Executive Summary

Phase 10.5 transforms cadence from static governance filtering into reliability-weighted ranking. Candidates are now scored using 7 production-backed signals (template reliability, agent capability, validation strength, rollback safety, source reliability, expected leverage, blast radius safety), classified into 4 promotion tiers, and evaluated against threshold policies for cadence mode transitions.

**Key outcomes:**
- 3 new substrate modules: reliability_signals.py, reliability_weighted_ranker.py, promotion_threshold_policy.py
- 6 new API endpoints with operator auth
- 71 new tests (all passing)
- Live candidate ranking: proven templates rank highest (execute_ready), unproven rank lower (supervised/recommend)
- Promotion thresholds defined but not over-applied — cadence remains dry_run_only
- Medium-risk execution permanently blocked until future phase

---

## 10.5-A — Preflight Verification

| # | Check | Result |
|---|-------|--------|
| 1 | Phase 10.4R audit exists | PASS |
| 2 | Main includes 10.4R artifacts (9 files) | PASS |
| 3 | Runtime health ok | PASS |
| 4 | PRs #50-53 all MERGED | PASS |
| 5 | ProductionTruthDelta per PR | PASS (4 deltas) |
| 6 | ProductionOutcomeCommitted once each | PASS |
| 7 | Candidate suppression (5 resolved) | PASS |
| 8 | Template reliability present | PASS (doc-alignment 0.85, test-repair 0.82) |
| 9 | Agent reliability present | PASS (developer_agent 1.0) |
| 10 | Cadence dry_run_only | PASS |

**Artifact:** data/umh/autonomous_lane/phase10_5_preflight.json

---

## 10.5-B — Reliability Signal Model

**Module:** substrate/organism/reliability_signals.py (464 lines)

6 signal types aggregated from real production artifacts:

| Signal | Source | Score Method |
|--------|--------|-------------|
| TemplateReliabilitySignal | Phase 10.4R reliability_updates + template registry | 40% confidence + 40% success rate + 20% reuse |
| AgentReliabilitySignal | Phase 10.4R agent_updates | 70% success rate + 30% validation pass rate |
| CandidateSourceReliabilitySignal | Campaign queue + merge + verification data | 30% approval + 30% merge + 40% verify rate |
| ValidationReliabilitySignal | PMV validation_results across all verifications | pass rate - FP/FN penalties + baseline bonus |
| RollbackReliabilitySignal | Candidate metadata | non-mutating=1.0, method+tested=0.9, method=0.6 |
| ProductionTruthReliabilitySignal | All PMV files in merge_verifications/ | 40% PMV + 30% idempotency + 20% dedup + 10% divergence |

**Aggregated from real data:**
- 11 templates (2 production-proven, 9 seed)
- 1 agent (developer_agent, 4/4 successes)
- 4 sources (stale_docstrings, stale_test_paths, missing_package_init, template_audit_gaps)
- 2 validation methods (import substrate, py_compile organism)
- 18 PMV files (9 production_verified, 9 requires_review from Phase 10.3 tests)

**Artifact:** data/umh/autonomous_lane/phase10_5_reliability_signals.json

---

## 10.5-C — Reliability-Weighted Ranker

**Module:** substrate/organism/reliability_weighted_ranker.py (300 lines)

### Ranking Formula

| Signal | Weight |
|--------|--------|
| template_reliability | 25% |
| agent_capability | 20% |
| validation_strength | 15% |
| rollback_safety | 15% |
| source_reliability | 10% |
| expected_leverage | 10% |
| blast_radius_safety | 5% |

**Weights sum to 1.0** (verified by test).

### Hard Gates

Before scoring, candidates must pass:
1. Risk must be LOW
2. Evidence must exist
3. Template match must exist
4. Validation method must exist
5. Rollback method or non-mutating proof must exist
6. No sensitive path (.env, credentials, etc.)
7. No blocked keywords (docker, migration, auth, etc.)
8. Candidate not already resolved

### Promotion Classes

| Class | Thresholds |
|-------|-----------|
| execute_ready_low_risk | template >= 0.80, agent >= 0.75, validation >= 0.80, rollback exists, 2+ production successes |
| supervised_low_risk | template >= 0.65, agent >= 0.65, validation exists |
| recommend_only | evidence exists but insufficient reliability |
| blocked | violates hard gates |

**Artifact:** data/umh/autonomous_lane/phase10_5_ranked_candidates.json

---

## 10.5-D — Promotion Threshold Policy

**Module:** substrate/organism/promotion_threshold_policy.py (271 lines)

| Level | Key Thresholds | Met? |
|-------|---------------|------|
| dry_run_only | always available | YES |
| supervised_pr_creation | template >= 0.80, agent >= 0.75, validation >= 0.80, 3+ successes, no failures | NO (maintenance template has 1 failure) |
| low_risk_batch_mode | all above + last 5 PMVs pass + operator enables | NO |
| medium_risk_recommendation_only | template >= 0.90, agent >= 0.85, validation >= 0.90, 5+ successes, operator review | NO |
| medium_risk_supervised_review | BLOCKED until future phase | NO |

**Current highest eligible: dry_run_only** (correct — the maintenance template's 1 failure gates supervised_pr_creation)

**Artifact:** data/umh/autonomous_lane/phase10_5_promotion_threshold_policy.json

---

## 10.5-E — Cadence Dry-Run Integration

Live ranking of current candidates:

| Rank | Candidate | Score | Promotion Class |
|------|-----------|-------|----------------|
| 1 | cse-af691e02 (stale docstring in check_projection_leak.py) | 0.9200 | execute_ready_low_risk |
| 2 | cse-7d173828 (template audit gap: require_template) | 0.7550 | supervised_low_risk |
| 3 | cse-cf52300e (template audit gap: wrong path) | 0.7550 | supervised_low_risk |
| 4 | cse-bc552c93 (template audit gap: zero templates) | 0.7550 | supervised_low_risk |

The stale docstring candidate ranks highest because its template family (documentation-alignment) has 0.85 confidence with 3 production successes. The 3 audit gap candidates rank lower because they lack affected_files and their template family (maintenance-action) has lower confidence with a failure.

**Artifact:** data/umh/autonomous_lane/phase10_5_cadence_ranked_dry_run.json

---

## 10.5-F — Cockpit / API Surface

6 new endpoints, all requiring operator auth:

| Endpoint | Status | Auth | Key Data |
|----------|--------|------|----------|
| /organism/reliability-signals | 200 | 403 without | 11 templates |
| /organism/cadence-ranked-candidates | 200 | 403 without | 6 candidates ranked |
| /organism/promotion-thresholds | 200 | 403 without | highest=dry_run_only |
| /organism/template-reliability | 200 | 403 without | 11 templates |
| /organism/agent-reliability | 200 | 403 without | 1 agent |
| /organism/candidate-source-reliability | 200 | 403 without | 4 sources |

**Note:** Cockpit frontend auth (Clerk) blocks automated browser testing. All endpoints verified via direct API calls.

**Artifact:** data/umh/autonomous_lane/phase10_5_cockpit_api_verification.json

---

## 10.5-G — Decision Simulation

| Candidate | Before (Phase 10.4) | After (Phase 10.5) |
|-----------|--------------------|--------------------|
| stale docstring (check_projection_leak.py) | cadence_eligible (equal with all) | #1, score=0.92, execute_ready_low_risk |
| audit gap: require_template | cadence_eligible (equal) | #2, score=0.76, supervised_low_risk |
| audit gap: wrong path | cadence_eligible (equal) | #3, score=0.76, supervised_low_risk |
| audit gap: zero templates | cadence_eligible (equal) | #4, score=0.76, supervised_low_risk |

**Simulation verifications (all PASS):**
- Resolved candidates remain suppressed
- Proven template families rank higher
- Unproven templates rank lower
- Weak validation lowers rank
- Missing rollback lowers rank
- Source reliability affects rank
- Medium-risk candidates remain non-executable
- Recommendations are explainable

**Artifact:** data/umh/autonomous_lane/phase10_5_decision_simulation.json

---

## 10.5-H — Tests + Gates

### Test Suites

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Phase 10.5 tests | 71 | 0 | 0 |
| Phase 10.x + 9.x tests | 535 | 0 | 0 |
| Organism infrastructure tests | 329 | 0 | 4 |

### Gate Checks

| Gate | Result |
|------|--------|
| py_compile (4 modified files) | PASS |
| check_instance_leak.py --all | PASS (577 files) |
| check_dependency_direction.py --all | PASS |
| check_type_divergence.py --all | PASS (no new divergences) |
| Line count check | PASS (max 712, all under 3000) |
| API route auth | PASS (403 without auth) |
| No fake data | PASS |

**Artifact:** data/umh/autonomous_lane/phase10_5_test_gate_results.json

---

## New Infrastructure

| File | Lines | Purpose |
|------|-------|---------|
| substrate/organism/reliability_signals.py | 464 | Signal model + aggregator |
| substrate/organism/reliability_weighted_ranker.py | 300 | Deterministic ranker with hard gates |
| substrate/organism/promotion_threshold_policy.py | 271 | Cadence mode transition thresholds |
| transports/api/cockpit_autonomous_routes.py | +66 | 6 API routes + handlers |
| tests/test_phase10_5_reliability_weighted_cadence.py | 712 | 71 tests (20 test classes) |

---

## Data Artifacts

All in data/umh/autonomous_lane/:

| File | Content |
|------|---------|
| phase10_5_preflight.json | 10-check preflight verification |
| phase10_5_reliability_signals.json | Aggregated signals from real artifacts |
| phase10_5_ranked_candidates.json | 4 candidates ranked with scores |
| phase10_5_promotion_threshold_policy.json | 5-level threshold evaluations |
| phase10_5_cadence_ranked_dry_run.json | Full dry-run with ranking + thresholds |
| phase10_5_decision_simulation.json | Before/after comparison |
| phase10_5_cockpit_api_verification.json | 6 endpoints verified |
| phase10_5_test_gate_results.json | 935+ tests, 7 gates |

---

## Safety Invariant Verification

| Constraint | Status |
|-----------|--------|
| No auto-merge | ENFORCED — cadence remains dry_run_only |
| No medium-risk execution | ENFORCED — permanently blocked |
| No production mutations | ENFORCED — no PRs created, no code changed outside new modules |
| No DNS changes | ENFORCED |
| No credential changes | ENFORCED |
| No auth/security changes | ENFORCED (except adding auth to new routes) |
| No broad refactors | ENFORCED — 3 new files + route additions only |
| No fake reliability data | ENFORCED — all signals trace to Phase 10.3/10.4/10.4R artifacts |
| No fake candidates | ENFORCED — all candidates from CandidateSupplyEngine |
| No fake production outcomes | ENFORCED — PMV data from merge_verifications/ |
| Cadence dry_run_only | ENFORCED |

---

## Remaining Blockers

| Blocker | Impact | Resolution |
|---------|--------|-----------|
| Maintenance template has 1 failure | Gates supervised_pr_creation threshold | Investigate tpl-seed-maintenance-action-01 failure; may be false positive from governance block |
| 9 PMVs in requires_review | Lowers production truth PMV pass rate to 0.50 | These are Phase 10.3 test sandboxes; consider classifying as non-production |
| Clerk blocks browser testing | Can't verify cockpit UI rendering | API endpoints verified directly |

---

## Decision: Ready for Phase 11?

### Evidence Summary

| Criterion | Met? |
|-----------|------|
| Phase 10.4R verified complete | YES |
| Reliability signals from real outcomes | YES |
| 7-signal weighted ranking | YES |
| Deterministic and explainable | YES |
| Cadence returns ranked candidates | YES |
| Resolved candidates suppressed | YES |
| Proven templates rank higher | YES |
| Weak validation lowers rank | YES |
| Medium-risk blocked | YES |
| Promotion thresholds defined | YES |
| Cockpit/API exposes state | YES |
| Tests/gates pass (935+) | YES |
| No fake data | YES |

### Readiness Assessment

**READY FOR PHASE 11.**

Phase 10.5 completes the autonomous improvement pipeline's judgment layer. The system no longer treats all LOW-risk template matches equally — it uses production-backed reliability to rank, classify, and recommend. The full pipeline is:

```
Discovery -> Template Match -> Governance -> Reliability Score -> Rank -> Promote -> Sandbox -> PR -> Merge -> Verify -> Learn
```

Phase 10.x (10.0 through 10.5) has proven:
- Template library works (10.0)
- Candidate supply works (10.0)
- Sandbox PR creation works (10.1)
- Operator-approved execution works (10.2)
- Production truth verification works (10.3)
- Reliability campaign with 100% success (10.4/10.4R)
- Reliability-weighted ranking with promotion thresholds (10.5)

**Next: Phase 11 — UMH Self-Build Engineering Queue.**

---

*Phase 10.5 completed 2026-05-30. All artifacts preserved in data/umh/autonomous_lane/. Audit chain: preflight -> signals -> ranker -> thresholds -> ranking -> API -> simulation -> tests -> this report.*
