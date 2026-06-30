# Organism Qualification Report

## Qualification Summary

| Dimension | Value |
|-----------|-------|
| Operational Readiness Level | ORL-8 (PRODUCTION_QUALIFIED) |
| Confidence | 95.8% |
| Predictive Accuracy | 20.4% |
| Drift | PASS |
| Convergence | Stable |
| Weakest Property | Recovery & Homeostasis |
| Recommendation | Optimize Recovery & Homeostasis — lowest confidence (94.0%) |

**Hypothesis:** H1 SUPPORTED: 9/9 properties converged. ORL-8 @ 95.8% confidence.
**Total Mutations:** 312
**Duration:** 28s
**Stopping Reason:** Converged after 200 mutations (8 batches)

## Property Results

| # | Property | Status | Confidence | Key Metric |
|---|----------|--------|------------|------------|
| 1 | Canonical Mutation Integrity | PASS | 100.0% | artifact_completeness mean=1.000 over 46 mutations |
| 2 | Operational Coverage | PASS | 95.0% | coverage_ratio=1.000 (46/46) |
| 3 | Distributed State Consistency | PASS | 94.9% | stale_rate mean=0.000 |
| 4 | Adaptive Intelligence | PASS | 95.1% | reliability=0.900 feedback_gain_ratio=0.250 gov_cost_mean=0.016ms |
| 5 | Operational Entropy | PASS | 98.0% | OEI=0.2371 decreasing=True |
| 6 | Autonomous Coordination | PASS | 95.0% | conflicts=0/25 cancel_rate=1.000 |
| 7 | Meta-Orchestration | PASS | 96.0% | harness=1.000 model=1.000 visibility=1.000 |
| 8 | Recovery & Homeostasis | PASS | 94.0% | mttr=0.1s recovery=1.000 homeostasis=0.900 |
| 9 | Self-Regulation | PASS | 94.0% | detected=5/5 proposals=5 repairs=5 |
| 10 | Predictive Accuracy | FAIL | 20.4% | MAPE=0.7955 +/-0.2232 calibration=0.599 predictions=566 |

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
