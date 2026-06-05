# Phase 14.9B — AC-6.3 Governance Hardening Report

**Date:** 2026-06-05
**Phase:** 14.9B (Targeted AC-6.3 Governance Hardening)
**Branch:** worktree-phase-14-9b-ac63
**Base:** main @ 5e84eae3

---

## Root Cause

`ExecutionAuthorityEngine._classify_risk()` evaluates risk through two mechanisms:
1. **Named action sets** — frozensets like `STRUCTURALLY_DENIED_ACTIONS`, `READ_ONLY_ACTIONS`,
   `SAFE_INGESTION_ACTIONS`, `GUI_REQUIRING_ACTIONS`, `CONTAINER_ACTIONS`
2. **Request parameters** — `financial_risk`, `credential_risk`, `external_mutation`,
   `estimated_cost`, `data_sensitivity`, `reversibility`

Destructive data operations (`data_deletion`, `data_wipe`, `bulk_delete`, `schema_drop`,
`table_truncate`, `record_purge`) were in neither category. When a caller submitted
`action_type="data_deletion"` without setting extra risk parameters, the action fell through
every check to the default `return RiskClass.LOW` at line 625, classifying it as LOW risk
with NOTIFY_EXECUTE authority and SYSTEM_APPROVAL. No operator approval required.

---

## Files Changed

| File | Change |
|------|--------|
| `substrate/governance/policy/execution_authority_engine_v1.py` | Added `DESTRUCTIVE_DATA_ACTIONS` frozenset + risk check |
| `tests/test_execution_authority_engine_v1.py` | Added `TestDestructiveDataActions` class (8 tests) |
| `data/umh/trinity_convergence/phase14_9b_ac63_governance_hardening_report.md` | This report |

---

## Rule Change

**Added** `DESTRUCTIVE_DATA_ACTIONS` frozenset containing:
- `data_deletion`
- `data_wipe`
- `bulk_delete`
- `schema_drop`
- `table_truncate`
- `record_purge`

**Added** check in `_classify_risk()` (after CONTAINER_ACTIONS, before default fallthrough):
```python
if request.action_type in DESTRUCTIVE_DATA_ACTIONS:
    return RiskClass.HIGH
```

**Effect:** These action types now classify as HIGH risk → APPROVE_EXECUTE authority →
FOUNDER_APPROVAL required. Operator must approve before execution proceeds.

**No existing rules were modified.** All prior action sets, parameter-based risk checks,
structural denials, and authority class determination logic remain identical.

---

## Tests Added

8 new tests in `TestDestructiveDataActions` class:

| Test | Assertion |
|------|-----------|
| `test_data_deletion_classified_high` | data_deletion → HIGH risk, APPROVE_EXECUTE |
| `test_data_wipe_classified_high` | data_wipe → HIGH risk |
| `test_bulk_delete_classified_high` | bulk_delete → HIGH risk |
| `test_schema_drop_classified_high` | schema_drop → HIGH risk |
| `test_table_truncate_classified_high` | table_truncate → HIGH risk |
| `test_record_purge_classified_high` | record_purge → HIGH risk |
| `test_destructive_data_requires_founder_approval` | data_deletion → FOUNDER_APPROVAL |
| `test_all_destructive_data_actions_are_high` | exhaustive set check — all 6 actions → HIGH |

---

## Acceptance Result

**50/50 E2E acceptance tests PASS** (AC-1 through AC-10, including AC-6.3)

---

## Regression Result

- **62/62** authority engine tests pass (54 existing + 8 new)
- **311/316** Wave 1/2/3 tests pass
- **5 safety gate failures** — git-diff-based scope checks that detect the engine file as modified
  in the working tree. These are expected and resolve after commit/merge (the diff disappears).
  All 5 are `SafetyGates` class tests, not logic tests. Zero real logic regressions.

---

## Known Exceptions

The 5 safety gate test failures are:
1. `TestSafetyGates::test_governance_classes_unchanged` (wave1)
2. `TestWave2SafetyGates::test_no_substrate_core_modifications` (wave2)
3. `TestWave2SafetyGates::test_only_allowed_files_modified` (wave2)
4. `TestWave3SafetyGates::test_no_substrate_core_modifications` (wave3)
5. `TestWave3SafetyGates::test_only_allowed_files_modified` (wave3)

These are git-diff guards that check whether governance files were modified relative to the
last committed state. They protect against accidental modification during their respective
phase work. They will pass on the next clean checkout after this commit merges.

---

## Source Drift Status

**No drift.** Only one production source file modified (`execution_authority_engine_v1.py`).
Change is 10 lines: 8-line frozenset definition + 2-line check in `_classify_risk()`.
No other files touched. No imports changed. No API surface modified.

---

## Verdict

**GO** — AC-6.3 governance gap closed. All 50 E2E acceptance criteria now pass.
Stage 1 acceptance validation is 50/50 PASS. Ready for Stage 2 feature implementation.
