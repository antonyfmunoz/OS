# Phase 57 — Controlled Feedback Selection Integration Layer v1

## Audit Report

**Date:** 2026-05-01
**Phase:** 57 of UMH runtime build
**Status:** COMPLETE

---

## What changed after Phase 56

Phase 56 introduced attribution-guided feedback factors — bounded, confidence-gated multipliers that express how contextual dimensions correlate with outcomes. But these factors had no path to influence candidate selection. Phase 57 introduces a controlled selection integration layer that can apply feedback-informed ranking adjustments to candidates without destabilizing base scoring. The integration is opt-in, bounded, confidence-gated, and preserves base score authority via a configurable margin check.

---

## What was built

### New files
- `umh/runtime/feedback_selection.py` — FeedbackSelectionPolicy, FeedbackAdjustedCandidate, FeedbackSelectionResult, select_with_feedback

### Modified files
- `umh/runtime/__init__.py` — 4 new exports, updated docstring

### Test file
- `tests/unit/test_phase57_feedback_selection.py` — 194 tests across 68 sections

### Not modified
- `umh/runtime/meta_planner.py` — integration deferred (see Known Limitations)

---

## Architecture

### Feedback selection policy

**FeedbackSelectionPolicy** (frozen dataclass):

| Field | Default | Bounds |
|-------|---------|--------|
| enabled | False | — |
| min_confidence | 0.6 | [0.0, 1.0] |
| max_adjustment | 0.12 | [0.0, 0.30] |
| preserve_top_margin | 0.15 | [0.0, 1.0] |
| require_valid_candidate | True | — |

Disabled by default — returns base-score winner unless explicitly enabled.

### Selection adjustment model

`select_with_feedback(candidates, base_scores, feedback_factors, confidences, policy, valid_flags, safe_flags)`:

1. **Disabled** → return base-score winner, no adjustment
2. **Missing feedback** → all factors default to 1.0 (neutral)
3. **Low confidence** → factor forced to 1.0 for that candidate
4. **Factor clamped** → enforced within [1.0 - max_adjustment, 1.0 + max_adjustment]
5. **Adjusted score** = base_score × clamped_factor
6. **Validity filter** → invalid/unsafe candidates never selected
7. **Adjusted best** computed from valid candidates only
8. **Preserve_top_margin** check → if base leader exceeds adjusted challenger by margin, keep base leader
9. **Result** includes full explanation, all adjusted candidates, and whether selection changed

### Adjusted score formula

```
clamped_factor = clamp(feedback_factor, 1.0 - max_adjustment, 1.0 + max_adjustment)
adjusted_score = base_score × clamped_factor
```

With default max_adjustment=0.12: factor always within [0.88, 1.12].

### Preserve top margin logic

After computing the adjusted best candidate:

```
if adj_best != base_best:
    margin = base_top_score - adj_challenger_score
    if margin >= preserve_top_margin:
        keep base leader (feedback cannot overturn clearly superior candidate)
    else:
        allow reordering (candidates are close enough for feedback to matter)
```

This ensures feedback can only reorder candidates that are already close in base score. A dominant base leader cannot be dethroned by feedback.

### Safety filtering

- `valid_flags`: invalid candidates excluded from selection
- `safe_flags`: unsafe candidates excluded from selection
- Combined: `effective_valid = valid AND safe`
- If all candidates are invalid/unsafe: return empty selection with explanation
- Legacy candidates (no flags provided) default to valid and safe

### Determinism / tie-breaking

- No randomness (no `import random`)
- Ties broken by candidate_id (lexicographic, ascending)
- Same inputs always produce same outputs
- Candidate order in adjusted_candidates matches input order

### Explainability

Every `FeedbackSelectionResult` includes:
- `selected_candidate`: the final selection
- `original_best`: who would have won without feedback
- `adjusted_best`: who won after feedback adjustment
- `changed_selection`: whether feedback changed the outcome
- `explanation`: human-readable reason for the decision
- Per-candidate reasons: boosted/penalized/neutral/below-threshold/disabled

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 225 | Feedback selection integration opt-in only | Sections 12, 59, 65 |
| 226 | Default selection behavior unchanged | Sections 12, 14, 58 |
| 227 | Feedback adjusts ranking within bounded limits | Sections 16, 17, 18 |
| 228 | Low-confidence feedback does not affect selection | Sections 15, 42, 43 |
| 229 | Base score remains primary authority | Sections 19, 29 |
| 230 | Feedback integration deterministic | Sections 24, 25, 57 |
| 231 | Feedback integration explainable | Sections 26, 27, 28, 40, 41 |
| 232 | Invalid/unsafe candidates never selected via feedback | Sections 20, 21, 22, 67 |

---

## Test coverage

- **194 tests** across 68 sections
- Policy defaults/bounds/dict/frozen: Sections 1-4 (14 tests)
- Candidate defaults/bounds/dict/frozen: Sections 5-8 (18 tests)
- Result defaults/dict/frozen: Sections 9-11 (10 tests)
- Disabled policy: Section 12 (6 tests)
- Empty candidates: Section 13 (3 tests)
- Missing feedback: Section 14 (3 tests)
- Low confidence: Section 15 (4 tests)
- Positive boost: Section 16 (3 tests)
- Negative penalty: Section 17 (3 tests)
- Factor clamping: Section 18 (3 tests)
- Preserve top margin: Section 19 (4 tests)
- Invalid candidates: Section 20 (3 tests)
- Unsafe candidates: Section 21 (3 tests)
- All invalid: Section 22 (3 tests)
- Legacy candidates: Section 23 (2 tests)
- Tie breaking: Section 24 (3 tests)
- Determinism: Section 25 (2 tests)
- Original best: Section 26 (2 tests)
- Adjusted best: Section 27 (2 tests)
- Changed selection: Section 28 (3 tests)
- Base authority: Section 29 (3 tests)
- Neutral factor: Section 30 (2 tests)
- Length mismatches: Section 31 (6 tests)
- Single candidate: Section 32 (3 tests)
- Many candidates: Section 33 (2 tests)
- Enabled policy: Section 34 (3 tests)
- Selection change: Section 35 (2 tests)
- Boundary compliance: Section 36 (4 tests)
- No execution: Section 37 (4 tests)
- Import surface: Section 38 (1 test)
- No input mutation: Section 39 (6 tests)
- Explanation populated: Section 40 (4 tests)
- Candidate reason: Section 41 (5 tests)
- Mixed confidence: Section 42 (2 tests)
- Zero confidence: Section 43 (2 tests)
- Full confidence: Section 44 (2 tests)
- Zero base score: Section 45 (2 tests)
- Custom policy: Section 46 (4 tests)
- Roundtrips: Section 47 (3 tests)
- Margin edge: Section 48 (2 tests)
- Multiple invalid: Section 49 (2 tests)
- require_valid=False: Section 50 (1 test)
- Three-way: Section 51 (2 tests)
- Immutability: Section 52 (2 tests)
- Confidence threshold: Section 53 (2 tests)
- Zero adjustment: Section 54 (1 test)
- Extreme factors: Section 55 (3 tests)
- Extreme scores: Section 56 (3 tests)
- No randomness: Section 57 (2 tests)
- Meta planner unchanged: Section 58 (2 tests)
- Disabled with flags: Section 59 (2 tests)
- Attribution integration: Section 60 (1 test)
- Candidate order: Section 61 (2 tests)
- Best fields: Section 62 (3 tests)
- Mixed flags: Section 63 (2 tests)
- Stress 100 candidates: Section 64 (2 tests)
- Margin disabled: Section 65 (1 test)
- Empty lists: Section 66 (2 tests)
- Feedback cannot override validity: Section 67 (2 tests)
- Adjusted accuracy: Section 68 (3 tests)

---

## Boundary compliance

- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- No `import os`, `import subprocess`, `import random`, or `docker` references
- Pure computation module — no I/O
- No mutation of input lists or candidate data

---

## Meta planner integration (deferred)

Integration with `meta_planner.py` is deferred to a future phase. Rationale:

1. MetaPlanner already has 8 scorer integrations — adding feedback selection inline would increase coupling risk
2. Phase 57 as a standalone utility is safer and independently testable
3. MetaPlanner signature and behavior are verified unchanged (Section 58)
4. The caller can compose `select_with_feedback` with planner output at the call site

---

## Known limitations

- Feedback selection is correlation-based, not causal
- No adaptive preserve_top_margin (fixed value)
- No contextual bandit integration yet
- No sequence-level feedback selection
- No automatic policy tuning
- Meta planner integration deferred to future phase
- No cross-strategy feedback comparison
- Factor clamp is uniform (same max_adjustment for all candidates)

---

## Regression

- Phase 50: 161 passed, 0 failed
- Phase 51-54: 198 passed, 0 failed
- Phase 55: 151 passed, 0 failed
- Phase 56: 179 passed, 0 failed
- Phase 57: 194 passed, 0 failed
- Phase 50-57 combined: 883 passed, 0 failed

---

## Is Phase 58 safe?

Yes. Phase 57:
- Added one new module (`feedback_selection.py`) with no modifications to existing runtime modules
- Exports are purely additive (4 new symbols in `__init__.py`)
- All data structures are frozen dataclasses
- Meta planner behavior completely unchanged
- Default system behavior completely unchanged (selection integration disabled by default)
- No dependency on any external library

Phase 58 can safely build on feedback-integrated selection to introduce:
- Adaptive preserve_top_margin based on confidence distribution
- Meta planner wiring (opt-in parameter threading)
- Contextual bandit exploration with feedback-informed priors
- Feedback persistence for cross-session ranking memory
- Multi-objective feedback selection (multiple feedback dimensions)
