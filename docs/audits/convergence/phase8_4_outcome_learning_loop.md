# Phase 8.4 — Outcome Learning Loop

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Close the loop between execution outcomes and future recommendations.

## What Was Built

### substrate/organism/outcome_learning.py

**Core entities:**
- `OutcomeRecord` — what was executed and what happened
- `LearningSignal` — derived insight (reliability update, repeated failure, promotion/demotion)
- `OutcomeEvaluation` — success/quality assessment of an outcome
- `RecommendationAdjustment` — proposed reliability change with reason
- `ReliabilityUpdate` — before/after reliability with sample size
- `OutcomeLearningLoop` — stateful learning loop with JSONL persistence

**Capabilities:**
- Record outcomes (success/partial/failure/timeout/skipped)
- Compute reliability by action type from outcome history
- Detect repeated failures (3+ in last 20 attempts)
- Generate recommendation adjustments (promote high-reliability, flag low-reliability)
- Persist to JSONL with reload on init
- Full serialization

**Signal types:**
reliability_update, repeated_failure, recommendation_quality,
promotion_signal, demotion_signal, world_model_update

### API Integration
- Bridge handler: `organism.learning_loop` in organism_bridge.py
- Route: `GET /api/umh/organism/learning-loop`

### Tests
- 19 tests in `substrate/organism/tests/test_outcome_learning.py`
- Covers: outcome capture, success/failure/partial evaluation, reliability update, repeated failure detection, recommendation adjustments, persistence reload, serialization
- **19/19 PASS**

## Success Criteria
The organism can learn from execution outcomes and adjust future decisions. **MET.**
