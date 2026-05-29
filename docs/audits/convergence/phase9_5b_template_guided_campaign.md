# Phase 9.5B — Real Template-Guided Improvement Campaign

**Date**: 2026-05-29
**Campaign ID**: f567b9d9
**Status**: COMPLETE
**PR**: (pending)

## Objective

Execute a real template-guided improvement campaign that runs entirely
through spine-native propagation. Prove template lifecycle (raw ->
approved -> promoted), confidence tracking, find_matching discovery,
agent capability profiles, memory candidates, and outcome learning —
all generated automatically from GovernedExecutionSpine propagation
with zero manual propagation calls.

## Results

| Metric | Target | Actual |
|--------|--------|--------|
| Campaign trials | >= 6 | 6 |
| Success rate | > 0% | 100% |
| Propagation events | > 0 | 17 |
| Template candidates | > 0 | 17 |
| Templates promoted | >= 1 | 1 |
| Template lifecycle | raw -> approved -> promoted | Verified |
| Template confidence | Updates on reuse | 0.2 -> 0.67 |
| find_matching() | Returns promoted | Verified |
| Agent capability profile | Created | developer_agent (2 capabilities) |
| Outcome records | > 0 | 17 |
| Memory candidates | > 0 | 34 |
| Manual propagation calls | 0 | 0 (verified by source inspection) |
| Idempotency protection | Active | Verified |
| Failure isolation | Intact | Verified |

## Test Coverage

- `tests/test_phase9_5b_template_campaign.py` — 19 tests
  - TestCampaignExecution: campaign completes, propagation fires, no manual propagation
  - TestTemplateGeneration: templates generated, correct initial status (RAW)
  - TestTemplateLifecycle: approve/promote lifecycle, confidence updates, find_matching
  - TestAgentCapability: profile created, capabilities tracked
  - TestOutcomeLearning: outcomes recorded
  - TestMemoryPromotion: memory candidates created
  - TestCandidateQueue: builds from codebase, ranked, filtered, required fields
  - TestSafetyGates: high risk blocked, blocked keywords rejected
  - TestDaemonCampaignIntegration: full daemon E2E

## Regression

- `substrate/organism/tests/` — 1159 tests, 0 failures
- `tests/test_phase9_5_spine_native_propagation.py` — 65 tests, 0 failures
- `tests/test_phase9_5b_template_campaign.py` — 19 tests, 0 failures

Total: 1243 tests passing.

## Security Fixes (from Phase 9.5A, committed in this branch)

1. **Enum deserialization fail-closed**: `OutcomeRecord.status` and
   `LearningSignal.signal_type` now skip records with unknown values
   instead of defaulting to SUCCESS (fail-open).

2. **API response redaction**: `organism_bridge.py` now uses
   `_redact_outcome()` and `_redact_failure()` to strip internal
   evidence. Failure reasons classified into categories (auth_error,
   timeout, quota_error, other) instead of exposing raw strings.

## Architecture

```
ReliabilityCampaignRunner
  -> PlanExecutionAdapter.execute_plan()
    -> GovernedExecutionSpine.submit()
      -> _emit_outcome() [automatic]
        -> ParallelPropagationEngine.handle_outcome()
          -> Wave 1: outcome_learning, template_generation,
                     memory_generation, agent_capability_update,
                     world_model_evidence
          -> Wave 2: contradiction_recheck, readiness_recalculate,
                     bottleneck_recalculate, composition_template_refresh,
                     dependency_recompute
```

Zero manual propagation calls in trial_runner.py (verified by source inspection).

## Proof File

`data/umh/trials/phase9_5b_campaign_results.json`
