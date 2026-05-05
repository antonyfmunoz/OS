# Phase 78: Trace → Outcome → Memory Loop v1

**Status**: Complete
**Date**: 2026-05-03
**Tests**: 110 passed, 0 failed
**Regression**: 260 prior tests (75B + 76 + 77) pass

## Purpose

Close the MVP feedback loop. Every governed execution now produces:
1. An interpretable **OutcomeRecord** (trace-derived, never invented)
2. An append-only **FeedbackRecord** (system or user sourced)
3. A conservative **MemoryCandidate** (never auto-promoted)

The loop is an **observer, not a participant** — failures in feedback
processing never break execution.

## Architecture

```
Trace → TraceAnalysis → OutcomeClassifier → OutcomeRecord
                                              ↓
                                        FeedbackRecord
                                              ↓
                                        MemoryCandidate
                                              ↓
                                        FeedbackStore (append-only)
```

## Files Created (7)

| File | Purpose |
|------|---------|
| `umh/feedback/outcome.py` | OutcomeStatus (9), OutcomeRecord, score clamping |
| `umh/feedback/records.py` | FeedbackSignalType (9), FeedbackRecord, outcome→feedback mapping |
| `umh/feedback/memory_bridge.py` | MemoryCandidate, MemoryPromotionStatus, conservative creation |
| `umh/feedback/trace_analyzer.py` | TraceAnalysis, deterministic evidence extraction from traces |
| `umh/feedback/classifier.py` | OutcomeClassifier, rule-based cascade (no LLM) |
| `umh/feedback/store.py` | FeedbackStore, thread-safe append-only with global singleton |
| `umh/feedback/feedback_loop.py` | process_trace_feedback(), full pipeline orchestrator |

## Files Modified (5)

| File | Change |
|------|--------|
| `umh/feedback/__init__.py` | Docstring updated for Phase 78 |
| `umh/run.py` | `_attach_phase78_feedback()` in both return paths |
| `umh/workstation/resume.py` | Feedback-aware fields + `feedback_store` parameter |
| `umh/control/api.py` | 5 feedback endpoints (GET outcomes/records/candidates, POST user feedback) |
| `umh/control/cli.py` | 4 CLI commands (feedback-outcomes, feedback-records, feedback-candidates, feedback-add) |

## Invariants Honored

All 20 hard invariants (421-440) verified by test suite:

- **421**: Outcome status is trace-derived (classifier uses only trace data)
- **422**: Feedback records append-only (no delete/clear/pop on FeedbackStore)
- **423**: Memory candidates never auto-promoted (default = CANDIDATE)
- **424-425**: No subprocess, shell exec, requests, or browser imports in feedback modules
- **426**: No governance behavior changes from feedback
- **427**: No execution behavior changes from feedback
- **428**: No routing behavior changes from feedback
- **429**: DENIED = safety behavior, not execution failure
- **430-432**: All paths produce outcome artifacts (success, failure, denied)
- **433-440**: Score bounds, confidence bounds, source labeling, etc.

## Test Coverage

110 tests across 11 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| TestOutcomeStatus | 4 | Status enum, normalization |
| TestClampScore | 5 | Score boundary clamping |
| TestOutcomeRecord | 4 | Serialization, denied != failure |
| TestFeedbackSignalType | 2 | Signal normalization |
| TestFeedbackRecord | 3 | Serialization, score clamp, source |
| TestFeedbackFromOutcome | 6 | All outcome to signal mappings |
| TestMemoryCandidate | 3 | Round-trip, defaults, promotion |
| TestShouldCreateMemoryCandidate | 5 | Conservative creation rules |
| TestCreateMemoryCandidateFromOutcome | 6 | Type mapping, no auto-promote |
| TestSummarizeOutput/Error | 5 | Output truncation, error extraction |
| TestExtractFunctions | 4 | Dict/object extraction, governance |
| TestAnalyzeTrace | 6 | Confidence, evidence, sparse safety |
| TestOutcomeClassifier | 14 | Full cascade, DENIED safety, timeout |
| TestFeedbackStore | 11 | Append-only, filters, singleton |
| TestFeedbackLoop | 8 | Full pipeline, partial failure, store |
| TestRunLoopFeedbackIntegration | 4 | Run metadata, failure isolation |
| TestResumeWithFeedback | 4 | With/without store, no invention |
| TestFeedbackInvariants | 6 | Forbidden imports, no mutation |
| TestPhase78Exports | 7 | All module imports clean |

## Design Decisions

1. **Coexistence**: Phase 78 files use distinct names from existing feedback module files (outcome.py vs outcome_feedback.py, feedback_loop.py vs loop.py)
2. **Observer pattern**: `_attach_phase78_feedback()` wraps in try/except — feedback failure never propagates to execution result
3. **No LLM dependency**: OutcomeClassifier is pure rule-based cascade
4. **Additive integration**: All new parameters have defaults that preserve existing behavior
5. **DENIED handling**: Governance denial produces an outcome artifact via the early-return path in run.py, honoring invariant 432
