# C35 — Organism Stress Campaign

**Date**: 2026-06-29
**Status**: INFRASTRUCTURE COMPLETE — QUALIFICATION READY
**Objective**: Prove the organism converges toward stable, adaptive, self-maintaining
operation under production stress

## Executive Summary

C35 is the first qualification campaign. C31-C34 were construction campaigns
(design, connect, enforce). C35 proves the organism's operational properties
through sustained load, convergence measurement, failure injection, and drift
detection.

The qualification harness, self-maintenance bridge, mutation CLI, and full test
suite are complete. The organism is ready for qualification runs.

## Engineering Hypothesis

**H0 (null):** The organism is a governed wrapper that adds overhead without
compounding value. Repeated use doesn't improve it. Load degrades it.

**H1 (alternative):** Repeated production use causes measurable convergence:
reliability stabilizes, governance cost decreases, template reuse plateaus,
entropy per mutation decreases, the organism recovers from failures, and
proposes its own repairs.

## What Was Built

### Qualification Harness (`substrate/organism/qualification_harness.py`, ~1020 lines)
- 9 property validators (Mutation Integrity, Operational Coverage, State
  Consistency, Adaptive Intelligence, Operational Entropy, Autonomous
  Coordination, Meta-Orchestration, Recovery & Homeostasis, Self-Maintenance)
- Convergence math: rolling windows, coefficient of variation, consecutive
  convergence detection (stddev < 10% of mean for 3 consecutive windows)
- Drift detection: first-100 vs last-100 mutation comparison across 5 metrics
  (reliability, governance cost, latency, template match rate, fast path rate)
- ORL scoring: ORL-1 through ORL-8, each level gates on specific properties
- JSONL persistence for mutation records and qualification results
- Markdown report generation

### Self-Maintenance Bridge (`substrate/organism/self_maintenance_bridge.py`, 90 lines)
- Wires OutcomeLearningLoop degradation detection → WorkPacketEngine
- When reliability drops below threshold (default 0.7) after 3+ failures,
  auto-creates work packet with source_type="self_maintenance"
- Evidence chain: failure signals → work packet → operator approval → repair

### Degradation Callback (`substrate/organism/outcome_learning.py`, +32 lines)
- Added `register_degradation_callback()` method to OutcomeLearningLoop
- Fires when REPEATED_FAILURE signal + reliability < threshold
- One-shot per action_type (prevents duplicate work packets)

### Mutation CLI (`scripts/organism_mutation_cli.py`, 267 lines)
- 8 commands: submit, pending, approve, reject, journal, specs, status, qualify
- Provides CLI surface for Property 3 (Distributed State Consistency)
- Operator can interact with governed spine without cockpit or Discord

### Test Suite (`tests/test_c35_qualification.py`, 37 tests)
- Convergence math (8 tests)
- Mutation records (2 tests)
- Property results (2 tests)
- Drift detection (4 tests)
- ORL scoring (4 tests)
- Property validators (10 tests — all 9 properties + regression)
- Self-maintenance bridge (4 tests)
- Report generation (3 tests)

## Metrics

| Metric | Value |
|--------|-------|
| New files | 4 |
| Modified files | 1 (outcome_learning.py) |
| New lines of code | ~1,400 |
| Test cases | 37 (all passing) |
| C34 regression tests | 30 (all passing) |
| Architecture violations | 0 |
| CPU gate violations | 0 |
| Type coherence violations | 0 |
| Current ORL | ORL-3 (CANONICAL_MUTATION_ENFORCED) |

## ORL Scale

| ORL | Meaning | Gate | Status |
|-----|---------|------|--------|
| ORL-1 | Components exist | C31 | ACHIEVED |
| ORL-2 | Components connected | C33 | ACHIEVED |
| ORL-3 | Canonical mutation enforced | C34 | ACHIEVED |
| ORL-4 | Stable under sustained load | Properties 1-3 | READY TO VALIDATE |
| ORL-5 | Adaptive learning demonstrated | Properties 4-5 | READY TO VALIDATE |
| ORL-6 | Autonomous coordination | Properties 6-7 | READY TO VALIDATE |
| ORL-7 | Self-maintaining under stress | Properties 8-9 | READY TO VALIDATE |
| ORL-8 | Production-qualified organism | All + drift = 0 | READY TO VALIDATE |

## The 9 System Properties

| # | Property | Validator | Data Source |
|---|----------|-----------|-------------|
| 1 | Canonical Mutation Integrity | validate_mutation_integrity() | Journal + Events + Learning |
| 2 | Operational Coverage | validate_operational_coverage() | governed_mutation() attempts |
| 3 | Distributed State Consistency | validate_state_consistency() | 7 projection checkers |
| 4 | Adaptive Intelligence | validate_adaptive_intelligence() | OutcomeLearningLoop + SpineTimingData |
| 5 | Operational Entropy | validate_operational_entropy() | Journal + Events + MutationRecords |
| 6 | Autonomous Coordination | validate_autonomous_coordination() | Concurrent mutation results |
| 7 | Meta-Orchestration | validate_meta_orchestration() | Routing decision records |
| 8 | Recovery & Homeostasis | validate_recovery_homeostasis() | Failure injection results |
| 9 | Self-Maintenance | validate_self_maintenance() | Degradation → work packet chain |

## Files Created/Modified

### New files
- `substrate/organism/qualification_harness.py` — qualification engine
- `substrate/organism/self_maintenance_bridge.py` — degradation → work packet wiring
- `scripts/organism_mutation_cli.py` — CLI for governed mutations
- `tests/test_c35_qualification.py` — 37 test cases

### Modified files
- `substrate/organism/outcome_learning.py` — degradation callback registration

## What Happens Next

The harness is infrastructure. Qualification runs are the next step:
1. Execute 500+ governed mutations across all spec types
2. Measure convergence across all 9 properties
3. Inject 50+ failures for recovery/homeostasis
4. Compute drift across first-100 vs last-100
5. Score ORL — target ORL-8

Each property validation requires real organism state — journal entries,
events, learning signals, work packets. The harness reads from the same
JSONL stores the governed spine writes to. No synthetic data.

## Constraints Verified

- [x] No substrate → transports/services imports
- [x] No Python file over 3,000 lines (max: 1,020)
- [x] No silent except-pass
- [x] No raw subprocess calls
- [x] No type coherence violations
- [x] All 37 C35 tests passing
- [x] All 30 C34 tests passing (no regressions)
- [x] Docker Python 3.11 compatible (no 3.12+ syntax)
