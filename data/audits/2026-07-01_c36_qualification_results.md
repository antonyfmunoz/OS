# Organism Qualification Report

## Qualification Summary

| Dimension | Value |
|-----------|-------|
| Operational Readiness Level | ORL-8 (PRODUCTION_QUALIFIED) |
| Confidence | 93.1% |
| Predictive Accuracy | 0.0% |
| Drift | PASS |
| Convergence | Stable |
| Weakest Property | Distributed State Consistency |
| Recommendation | Optimize Distributed State Consistency — lowest confidence (74.1%) |

**Hypothesis:** H1 SUPPORTED: 9/9 properties converged. ORL-8 @ 93.1% confidence.
**Total Mutations:** 162
**Duration:** 12s
**Stopping Reason:** Ceiling reached: 50 mutations (5 batches)

## Property Results

| # | Property | Status | Confidence | Key Metric |
|---|----------|--------|------------|------------|
| 1 | Canonical Mutation Integrity | PASS | 100.0% | artifact_completeness mean=1.000 over 46 mutations |
| 2 | Operational Coverage | PASS | 95.0% | coverage_ratio=1.000 (46/46) |
| 3 | Distributed State Consistency | PASS | 74.1% | stale_rate mean=0.000 |
| 4 | Adaptive Intelligence | PASS | 93.9% | reliability=0.920 feedback_gain_ratio=0.205 gov_cost_mean=0.014ms |
| 5 | Operational Entropy | PASS | 96.0% | OEI=0.3122 decreasing=True |
| 6 | Autonomous Coordination | PASS | 95.0% | conflicts=0/25 cancel_rate=1.000 |
| 7 | Meta-Orchestration | PASS | 96.0% | harness=1.000 model=1.000 visibility=1.000 |
| 8 | Recovery & Homeostasis | PASS | 94.0% | mttr=0.0s recovery=1.000 homeostasis=0.900 |
| 9 | Self-Regulation | PASS | 94.0% | detected=5/5 proposals=5 repairs=5 |
| 10 | Predictive Accuracy | FAIL | — | MAPE=1.6370 +/-0.5923 calibration=0.855 predictions=120 cold_mape=0.350 mature_mape=1.052 worst=[__global__=1.785, prior::medium=0.478, prior::low=0.265] best=[cleanup=0.079, state=0.156, prior::low=0.265] |

## Drift Detection

**Passed:** Yes

| Metric | Deviation |
|--------|-----------|

## ORL Scale

| ORL | Meaning | Status |
|-----|---------|--------|
| ORL-1 | COMPONENTS_EXIST | ACHIEVED |
| ORL-2 | COMPONENTS_CONNECTED | ACHIEVED |
| ORL-3 | CANONICAL_MUTATION_ENFORCED | ACHIEVED |
| ORL-4 | STABLE_UNDER_LOAD | ACHIEVED |
| ORL-5 | ADAPTIVE_LEARNING | ACHIEVED |
| ORL-6 | AUTONOMOUS_COORDINATION | ACHIEVED |
| ORL-7 | SELF_REGULATING | ACHIEVED |
| ORL-8 | PRODUCTION_QUALIFIED | ACHIEVED |
