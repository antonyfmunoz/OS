# C26 — Reality Correspondence Certification

**Campaign:** C26 | **Status:** COMPLETE | **Date:** 2026-06-22
**Commit:** e0276959 | **Branch:** worktree-remaining-phases
**Tests:** 106 passing | **LOC:** 6,284 added | **Files:** 28 changed

---

## Strategic Context

C25 proved UMH can produce software through its cockpit pipeline (20/20 tasks, 93% pattern reuse). C25 also exposed a critical epistemological failure: both EOS and COS were marked "PRODUCTION" with green checkmarks while showing white screens. The organism believed its own paperwork.

C26 fixes that class of failure permanently.

---

## Phase 1 — Outcome Correspondence (28 tasks + 9 ambush tests)

### C26A — Outcome Verification Runtime (10 tasks)

**File:** `substrate/organism/outcome_verification.py`

Replaces "Task Complete" with "Outcome Verified." Every task gains graduated verification through a data-driven VerificationPlan:

| Level | Gate |
|-------|------|
| ARTIFACT_EXISTS | File/endpoint/resource was created |
| BUILD_PASSES | Artifact compiles/builds |
| DEPLOY_HEALTHY | Health endpoint returns 200 |
| UI_OPERATIONAL | Frontend loads, key elements render |
| WORKFLOW_OPERATIONAL | Critical user path completes |

- VerificationPlanRegistry loads plans from `data/umh/verification_plans.json`
- OutcomeVerificationEngine executes plans, stops on first required failure
- Wired into GovernedSpine._verify() and EngineeringProofPackage
- Feeds verified outcomes to OutcomeLearningLoop

### C26B — Post-Deploy Verification Worker (8 tasks)

**File:** `substrate/organism/deploy_verification_worker.py`

No human should discover a white screen. UMH should.

Post-deploy pipeline (runs after every deployment):
1. Poll health endpoint with backoff (max 120s)
2. Fetch HTML — verify `<div id="root">` present
3. Fetch JS bundle — verify expected baked-in values present
4. Emit CRITICAL attention item on any failure
5. Write results to telemetry + reality model

Integrated into `cockpit/deploy.sh` and standalone `scripts/verify_deploy.py`.

### C26C — Projection Certification Framework (10 tasks)

**File:** `substrate/organism/projection_certification.py`

Every projection receives graduated certification:

| Level | Gate | Evidence |
|-------|------|----------|
| L0 ARTIFACT | Code exists | Fly app status = running |
| L1 BUILD | Builds successfully | Last build passed |
| L2 DEPLOY | Deployed, health 200 | curl health endpoint |
| L3 UI | Frontend loads, no JS errors | Bundle contains expected values |
| L4 WORKFLOW | Core workflow completes | Login page renders |
| L5 OUTCOME | End-to-end verified | User can accomplish app's purpose |

**Config:** `data/umh/projection_registry.json` — per-projection settings for LyfeOS, EOS, COS.

**Integration:** RealityGraph entities gain certification_level. OperatorContextEngine surfaces certification. Cockpit API endpoint at `/api/projections/certification`.

### Phase 1 Exit Gate — EOS + COS Rerun

Fixed both EOS and COS Dockerfiles (the exact C25 bug: VITE_CLERK_PUBLISHABLE_KEY not injected at build time via ARG/ENV). Redeployed both. Ran automated certification:

```
Before fix:
  LyfeOS:  L5 CERTIFIED
  EOS:     L2 DEPLOY (L3 FAILED — no Clerk key in bundle)
  COS:     L1 BUILD  (suspended, unreachable)

After fix:
  LyfeOS:  L5 CERTIFIED ✓
  EOS:     L5 CERTIFIED ✓
  COS:     L5 CERTIFIED ✓
```

### Reality Ambush Test — 9/9 Detected (16 tests)

**File:** `tests/test_reality_ambush.py`

9 intentional breakages. All detected by UMH before operator:

| # | Ambush | Detection Layer | Result |
|---|--------|----------------|--------|
| 1 | Remove VITE_CLERK_KEY (C25 bug) | L3 certification + deploy worker | DETECTED |
| 2 | Health returns 500 | L2 certification + deploy worker | DETECTED |
| 3 | Critical route removed | L4 layered model | DETECTED |
| 4 | Wrong DATABASE_URL | L2 certification | DETECTED |
| 5 | DNS wrong IP | L2 connection error | DETECTED |
| 6 | Wrong internal_port | Deploy worker (502) | DETECTED |
| 7 | Missing Clerk secret | L2 health 500 | DETECTED |
| 8 | Wrong Clerk key | L3 bundle mismatch | DETECTED |
| 9 | False-success proof package | ReviewPackageBuilder REJECT | DETECTED |

**Ambush 9** is the most important: proves the organism cannot believe its own paperwork. A session where every task claims success but outcome_verification says "failed" produces REJECT.

---

## Phase 2 — Correspondence Infrastructure (24 tasks)

### C26D — Reality Correspondence Ledger (8 tasks, 26 tests)

**Files:**
- `substrate/organism/production_truth_delta.py` — added CorrespondenceStatus, CorrespondenceResult, CorrespondenceChecker
- `substrate/organism/correspondence_scheduler.py` — NEW

Extends execution ledger with reality verification:
- `CorrespondenceChecker.check()` — compares system belief vs live reality via certification engine
- `CorrespondenceScheduler` — periodic check (configurable interval, default 6h)
- Detects drift: "was L5 yesterday, L2 today" → emits RegressionAlert (CRITICAL)
- Ring buffer history (max 100 per projection)
- Journal entries: VERIFICATION_COMPLETED, CORRESPONDENCE_CHECKED

### C26E — Trust Engine (8 tasks, 27 tests)

**File:** `substrate/organism/trust_score.py` — NEW

Composite trust scoring where weakest link determines confidence:

```
composite_trust = min(claim_confidence, verification_confidence, reality_confidence)
```

This is the mechanical gate. 100% claim + 0% verification = 0% trust.

**C25 retroactive (if this had existed):**
```
"EOS Deployed"
  claim_confidence:        1.0   (tasks all passed)
  verification_confidence: 0.0   (no bundle check)
  reality_confidence:      0.0   (white screen)
  composite_trust:         0.0   → UNTRUSTED → BLOCKED
```

Trust levels: UNTRUSTED (0.0) / LOW (0.25) / MEDIUM (0.5) / HIGH (0.75) / FULL (1.0)

Only HIGH or FULL can promote claims to canonical reality. Gate integrated into CanonicalRealityWritePath — low-trust mutations rejected before reaching InstanceRealityModel.

Cockpit API endpoint: `/api/trust/scores`

### C26F — Reality Challenge Benchmark (8 tasks, 15 tests)

**File:** `substrate/organism/benchmarks/reality_correspondence.py` — NEW

50 deterministic failure scenarios across 5 domains (10 each):

| Domain | Example Scenarios |
|--------|-----------------|
| BUILD (10) | Env var undefined (C25 bug), wrong node version, missing dep, empty bundle, wrong entry point |
| DEPLOY (10) | Health 200 but non-functional, wrong port, suspended machine, wrong region, TLS expired |
| AUTH (10) | Wrong Clerk key, secret missing, key expired, CORS blocks, JWT mismatch |
| DATA (10) | Wrong DATABASE_URL, schema mismatch, pool exhausted, RLS blocks, index missing |
| INTEGRATION (10) | API key rotated, webhook wrong host, rate limited, OAuth expired, downstream down |

**Results:**
- Detection rate: **100%** (50/50 detected)
- Classification accuracy: **78%** (39/50 severity matches)
- C25 scenario (BUILD-01): **DETECTED**

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| substrate/organism/outcome_verification.py | ~450 | Graduated outcome verification |
| substrate/organism/deploy_verification_worker.py | ~300 | Post-deploy health/HTML/bundle checks |
| substrate/organism/projection_certification.py | ~430 | L0-L5 projection certification |
| substrate/organism/correspondence_scheduler.py | ~250 | Periodic drift detection |
| substrate/organism/trust_score.py | ~220 | Composite trust scoring |
| substrate/organism/benchmarks/reality_correspondence.py | ~600 | 50-scenario benchmark |
| data/umh/projection_registry.json | 24 | Per-projection config |
| data/umh/verification_plans.json | ~40 | Verification plan configs |
| scripts/verify_deploy.py | ~50 | Standalone deploy verification |
| tests/test_outcome_verification.py | — | C26A tests |
| tests/test_deploy_verification_worker.py | — | C26B tests |
| tests/test_projection_certification.py | 22 tests | C26C tests |
| tests/test_reality_ambush.py | 16 tests | 9/9 ambush tests |
| tests/test_correspondence_ledger.py | 26 tests | C26D tests |
| tests/test_trust_score.py | 27 tests | C26E tests |
| tests/test_reality_benchmark.py | 15 tests | C26F tests |

## Files Modified

| File | Change |
|------|--------|
| substrate/canonical_types.py | +12 type registrations |
| substrate/meta_ide/engineering_execution.py | Proof package outcome_verification field |
| substrate/meta_ide/review_package_builder.py | Outcome verification gate in compute_recommendation |
| substrate/operator/operator_context_engine.py | projection_certifications() + trust_scores() methods |
| substrate/organism/execution_journal.py | VERIFICATION_COMPLETED + CORRESPONDENCE_CHECKED |
| substrate/organism/executors/execution_telemetry.py | DEPLOY_VERIFICATION_* events |
| substrate/organism/governed_spine.py | VerificationStrategy from registry |
| substrate/organism/production_truth_delta.py | CorrespondenceStatus/Result/Checker |
| substrate/organism/reality_graph.py | Projection entities + certification_level |
| substrate/reality_model/canonical_reality_write.py | Trust gate (blocks low-trust promotion) |
| transports/api/app.py | /api/projections/certification + /api/trust/scores |
| cockpit/deploy.sh | Post-deploy verification call |

---

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| test_outcome_verification.py | — | PASS |
| test_deploy_verification_worker.py | — | PASS |
| test_projection_certification.py | 22 | PASS |
| test_reality_ambush.py | 16 | PASS |
| test_correspondence_ledger.py | 26 | PASS |
| test_trust_score.py | 27 | PASS |
| test_reality_benchmark.py | 15 | PASS |
| **TOTAL** | **106** | **ALL PASS** |

---

## Done Criteria Verification

### Phase 1 ✓
- [x] Outcome verification prevents unverified tasks from marking complete
- [x] All 3 projections have certification levels (all L5 CERTIFIED)
- [x] Post-deploy verification catches broken deploys automatically
- [x] EOS and COS genuinely certified through automated verification
- [x] Reality Ambush Test: 9/9 intentional breakages detected

### Phase 2 ✓
- [x] Execution journal includes verification + correspondence entries
- [x] Continuous drift detection catches state regressions
- [x] Composite trust score gates canonical reality promotion
- [x] UMH detects reality divergence before operator discovery (100% detection rate)

---

## Strategic Outcome

```
C24: UMH can produce software                          ✓
C25: UMH can operate through its cockpit loop           ✓
C25: UMH can coordinate parallel productions            ✓
C26 Phase 1: UMH verifies whether its output works      ✓
C26 Phase 2: UMH detects divergence before the operator  ✓
```

The central thesis:

```
Governed Autonomy → Production → Verification → Correspondence → Trust → Scale
```

C25 stopped at Production. C26 closes the loop through Trust.

The organism can no longer believe its own paperwork.
