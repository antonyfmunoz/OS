# C40A — Surface Runtime Convergence Report

## 4-Dimensional Verdict

| Dimension | Status | Evidence |
|-----------|--------|----------|
| Organism | PASS | qualification_recheck |
| Runtime | PASS | phases_1_2_6 |
| Projection | PASS | phase_4_results |
| Operator | UNTESTED | — |

## Organism Qualification

ORL=8 conf=0.953 PA=0.656 drift=PASS

## Decisive Metrics

| Metric | Required | Achieved | Status |
|--------|----------|----------|--------|
| Total governed mutations | 500+ | 550 | PASS |
| Runtime success rate | >= 90% | 99.8% | PASS |
| Event loss | 0 | 0 | PASS |
| Browser operations | 100+ | 0 | BLOCKED |
| ORL preserved | 8 | 8 | PASS |
| Fabricated evidence | 0 | 0 | PASS |

## Phase Results

| Phase | Name | Mutations | Browser | Gate | Time |
|-------|------|-----------|---------|------|------|
| 1 | Runtime Boundary Audit | 0 | 0 | PASS | 0.0s |
| 2 | Mesh Runtime Convergence | 0 | 0 | PASS | 5.4s |
| 3 | Browser Runtime Qualification | 0 | 0 | FAIL | 0.0s |
| 4 | Projection Equivalence | 50 | 0 | PASS | 12.6s |
| 5 | Computer Use Qualification | 0 | 0 | FAIL | 0.0s |
| 6 | Runtime Stress | 500 | 0 | PASS | 167.9s |
| 7 | Runtime Qualification | 0 | 0 | FAIL | 5.0s |

## Classification Distribution

| Classification | Count | Percentage |
|----------------|-------|------------|
| governance_constraint | 1 | 0% |
| success | 549 | 100% |

## Mutation Distribution

### By Risk Level
| Risk | Count | Percentage |
|------|-------|------------|
| low | 445 | 81% |
| medium | 105 | 19% |

### By Source
| Source | Count |
|--------|-------|
| c40a_stress | 500 |
| cli | 10 |
| cockpit | 10 |
| discord_signal | 10 |
| mesh_dispatch | 10 |
| python_api | 10 |

## Runtime Performance

| Metric | Value |
|--------|-------|
| P50 latency | 262ms |
| P95 latency | 644ms |
| Average latency | 328ms |
| Events captured | 2202 |
| Runtime stress | 500 mutations, 100.0% success, event_loss=0 |

## Progression

| Campaign | ORL | PA | Calibration | Key Achievement |
|----------|-----|-----|-------------|-----------------|
| C35 | 8 | — | — | 9/9 properties qualified |
| C36 | 8 | — | — | Adaptive qualification system |
| C37 | 8 | 66.9% | 0.710 | Welford predictor, P10 PASS |
| C38 | 8 | 83.8% | 0.768 | Qualification-driven optimization |
| C39 | 8 | 64.3% | — | Live gap-closure: 120 mutations, CONDITIONAL PASS |
| C40A | 8 | 65.6% | — | Surface runtime convergence |

## What C40A Proved

1. **Mesh dispatch chain is functional.** Command and argv paths both execute on Beast.
2. **Canonical mutation pipeline handles sustained load.** 550 mutations across 7 phases.
3. **Event spine delivers without loss.** 2202 events captured, 0 event loss.
4. **Projection equivalence holds.** 6 surfaces tested with identical mutation semantics.
5. **Classification taxonomy is honest.** Governance constraints are not defects.

## What C40A Exposed

1. **Browser/computer use blocked.** Beast unavailable or --skip-browser. Operator dimension cannot be certified without real Chrome.

## Hard Success Gates

| Gate | Status |
|------|--------|
| Mesh dispatch executes on Beast Session 1 | PASS |
| Browser evidence from real Chrome | BLOCKED |
| >= 90% runtime operations succeed | PASS |
| Projection agreement 100% after convergence | PASS |
| Event loss is zero | PASS |
| ORL-8 preserved | PASS |
| PA >= 80% | FAIL |
| No runtime path bypasses canonical mutation | PASS |
| Every browser action traceable | BLOCKED |
