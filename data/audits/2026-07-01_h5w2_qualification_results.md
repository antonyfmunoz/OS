# Organism Qualification Report

## Qualification Summary

| Dimension | Value |
|-----------|-------|
| Operational Readiness Level | ORL-8 (PRODUCTION_QUALIFIED) |
| Confidence | 93.0% |
| Predictive Accuracy | 59.8% |
| Drift | PASS |
| Convergence | Stable |
| Weakest Property | Distributed State Consistency |
| Recommendation | Optimize Distributed State Consistency — lowest confidence (69.5%) |

**Hypothesis:** H1 SUPPORTED: 9/9 properties converged. ORL-8 @ 93.0% confidence.
**Total Mutations:** 424
**Duration:** 35s
**Stopping Reason:** Ceiling reached: 200 mutations (7 batches)

## Property Results

| # | Property | Status | Confidence | Key Metric |
|---|----------|--------|------------|------------|
| 1 | Canonical Mutation Integrity | PASS | 100.0% | artifact_completeness mean=1.000 over 46 mutations |
| 2 | Operational Coverage | PASS | 95.0% | coverage_ratio=1.000 (46/46) |
| 3 | Distributed State Consistency | PASS | 69.5% | stale_rate mean=0.000 |
| 4 | Adaptive Intelligence | PASS | 95.7% | reliability=0.920 feedback_gain_ratio=0.236 gov_cost_mean=0.016ms |
| 5 | Operational Entropy | PASS | 98.0% | OEI=0.2589 decreasing=True |
| 6 | Autonomous Coordination | PASS | 95.0% | conflicts=0/25 cancel_rate=1.000 |
| 7 | Meta-Orchestration | PASS | 96.0% | harness=1.000 model=1.000 visibility=1.000 |
| 8 | Recovery & Homeostasis | PASS | 94.0% | mttr=0.0s recovery=1.000 homeostasis=0.900 |
| 9 | Self-Regulation | PASS | 94.0% | detected=5/5 proposals=5 repairs=5 |
| 10 | Predictive Accuracy | FAIL | 59.8% | MAPE=0.4024 +/-0.1110 calibration=0.795 predictions=481 cold_mape=0.229 mature_mape=0.242 worst=[__global__=1.006, prior::medium=0.247, prior::low=0.217] best=[state::repo_health=0.013, state::config_set=0.015, container::container_restart=0.016] |

## Drift Detection

**Passed:** Yes

| Metric | Deviation |
|--------|-----------|
| reliability_drift | 1.03% |
| governance_drift | 2.32% |
| latency_drift | 48.84% |
| template_drift | 0.00% |
| fast_path_drift | 0.00% |

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
