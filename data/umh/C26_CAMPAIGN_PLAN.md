# C26 — Reality Correspondence Certification

**Date:** 2026-06-22
**Status:** APPROVED — Ready for cockpit execution
**Predecessor:** C25 (Meta IDE Certification + Parallel Projection Production)
**Trigger:** C25 white screen postmortem — UMH can produce artifacts without proving outcomes

---

## Campaign Question

**Can UMH reliably distinguish between what it thinks happened and what actually happened?**

---

## Why This Campaign

C25 exposed the actual bottleneck:

```
UMH Belief:     EOS Operational ✅    COS Operational ✅
Reality:         EOS Broken ❌         COS Broken ❌
```

If UMH cannot reliably determine reality, memory, learning, compounding, governance, and trust all become corrupted. Every future layer depends on correspondence:

```
Reality Model → Memory → Learning → Capability → Compounding → Trust → Dependence → Scale
```

C25 proved UMH can: **Understand, Plan, Execute, Produce**
C26 must prove UMH can: **Verify, Validate, Reconcile, Certify**

```
Production Organism → Reality-Correspondent Organism
```

---

## Execution Model — Cockpit Pipeline (NON-NEGOTIABLE)

Every task executes through:

```
Cockpit Chat → Intent Classification → Engineering Plan → Approval → Dispatch → Beast Execution → Proof Package → Operator Recommendation
```

No direct execution. No bypasses. No manual code edits.

**Self-referential:** C26 builds verification. Later tasks verified by earlier infrastructure.

**52 cockpit tasks (28 Phase 1 + 24 Phase 2) + 9 Reality Ambush Tests**

---

## Two Phases, Two Victory Conditions

### Phase 1 — Outcome Correspondence

Fix the exact class of failure exposed by C25. Build verification. Prove it works on the actual broken projections.

**Acceptance:** All 3 projections L5 CERTIFIED through automated verification + 9/9 Reality Ambush Tests pass.

### Phase 2 — Correspondence Infrastructure

Make correspondence a permanent property of the organism.

**Acceptance:** UMH detects reality divergence before operator discovery.

Phase 2 begins only after Phase 1 acceptance is met.

---

## Phase 1 Detail

### C26A — Outcome Verification Runtime (10 tasks)

Replace "Task Complete" with "Outcome Verified."

Graduated verification:
- `artifact_exists` → `build_passes` → `deploy_healthy` → `ui_operational` → `workflow_operational`

**Old (C25):** `Dockerfile created → PASS`
**New (C26):** `Dockerfile created → Build → Deploy → Render → Clerk init → Login → PASS`

New: `substrate/organism/outcome_verification.py`
Wires into: GovernedSpine._verify(), EngineeringProofPackage, OutcomeLearningLoop

### C26B — Post-Deploy Verification Worker (8 tasks)

No human should discover a white screen. UMH should.

Reordered before Certification: Verify → Observe → Certify.

```
Health poll → HTML check → Bundle check → Browser check → Telemetry → Reality write → CRITICAL on failure
```

New: `substrate/organism/deploy_verification_worker.py`
Extends: cockpit/deploy.sh + scripts/verify_deploy.py

### C26C — Projection Certification Framework (10 tasks)

Reporting layer over verified observations. Built on C26A + C26B.

Graduated certification levels:

| Level | Gate | Evidence |
|-------|------|----------|
| L0 ARTIFACT | Code exists | Fly app running |
| L1 BUILD | Builds | Last build passed |
| L2 DEPLOY | Health 200 | curl health |
| L3 UI | Frontend loads | Bundle has expected values |
| L4 WORKFLOW | Core workflow | Login renders |
| L5 OUTCOME | E2E verified | User accomplishes purpose |

Current reality:
```
LyfeOS:  L5    EOS:  L2 (L3 FAILED)    COS:  L2 (L3 FAILED)
```

New: `substrate/organism/projection_certification.py`
Config: `data/umh/projection_registry.json` (data-driven)

### Phase 1 Exit Gate — EOS + COS Rerun

Fix Dockerfiles (add ARG VITE_CLERK_PUBLISHABLE_KEY), redeploy, verify:
```
EOS:  Build ✅ → Deploy ✅ → Health ✅ → Bundle ✅ → UI ✅ → Login ✅ → L5
COS:  Build ✅ → Deploy ✅ → Health ✅ → Bundle ✅ → UI ✅ → Login ✅ → L5
```

### Reality Ambush Test (Mandatory Final Gate)

The campaign exists because Antony discovered reality first. It does not pass until UMH discovers reality first.

After all 3 projections reach L5, **intentionally break things:**

| # | Ambush | What Breaks | UMH Must Detect |
|---|--------|-------------|-----------------|
| 1 | Remove Clerk build arg from fly.toml | White screen (C25 bug) | L3 failure, CRITICAL |
| 2 | Health endpoint returns 500 | Deploy unhealthy | L2 failure, CRITICAL |
| 3 | Remove critical API route | API broken | Post-deploy check |
| 4 | Wrong DATABASE_URL | DB connection fails | Server errors |
| 5 | DNS points to wrong IP | Site unreachable | L2 failure (timeout) |
| 6 | Wrong internal_port in fly.toml | Proxy can't reach container | L2 failure (timeout) |
| 7 | Remove Clerk secret key (server) | Auth middleware crashes | API/L4 failure |
| 8 | Wrong app's Clerk publishable key | Auth loads but fails | L4 failure (workflow) |
| 9 | False-success proof package (claims "Deployed ✅") while UI failed | Organism believes its own paperwork | Reject proof, downgrade trust, flag contradiction, prevent certification |

**Protocol:** Break one thing → run verification stack → UMH must detect + classify + emit CRITICAL → restore → next.

**Acceptance:** 9/9 detected by UMH before operator check.

---

## Phase 2 Detail

### C26D — Reality Correspondence Ledger (8 tasks)

Extend execution journal: `Intent → Plan → Execution → Artifact → Verification → Outcome → Reality Status`

New: correspondence_check() on ProductionTruthDelta + CorrespondenceScheduler (every 6h, drift detection)

### C26E — Trust Engine (8 tasks)

```
claim_confidence:        1.0  (proof says deployed)
verification_confidence: 0.3  (only health check)
reality_confidence:      0.0  (white screen)
composite_trust:         0.0  → NOT CERTIFIED
```

`composite_trust = min(claim, verification, reality)` — mechanical gate.

New: `substrate/organism/trust_score.py`

### C26F — Reality Challenge Benchmark (8 tasks)

50 scenarios × 5 domains:

| Domain | Example |
|--------|---------|
| Build | Env var undefined (C25 bug) |
| Deploy | Health 200 but non-functional |
| Auth | Wrong Clerk app key |
| Data | Schema mismatch |
| Integration | Rotated API key |

Proves the invariant: UMH detects divergence before operator discovery.

---

## Done Criteria

### Phase 1
1. Outcome verification prevents unverified completion
2. All 3 projections L5 CERTIFIED
3. Post-deploy verification catches broken deploys
4. EOS and COS genuinely operational
5. **Reality Ambush Test: 9/9 detected by UMH before operator**

### Phase 2
1. Continuous drift detection catches regressions
2. Composite trust gates canonical promotion
3. **UMH detects reality divergence before operator discovery**

---

## After C26

```
C24: UMH can produce software                          ✅
C25: UMH can operate through its cockpit loop           ✅
C25: UMH can coordinate parallel productions            ✅
C26 Phase 1: UMH verifies whether its output works      ⬜
C26 Phase 2: UMH detects divergence before the operator  ⬜
```

If C26 succeeds:
```
C27: Daily Driver Certification (30-day Antony usage)
C28: Antony Instance (personal operating infrastructure)
C29: LyfeOS Dogfood
C30: External User Instance Architecture
```

Because once correspondence is proven, the question shifts from "Can UMH know reality?" to "Can Antony actually live inside it?"

```
Governed Autonomy → Production → Verification → Correspondence → Trust → Scale
```

C25 stopped at Production. C26 closes the loop through Trust.
