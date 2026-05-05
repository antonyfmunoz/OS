# Adapter Quality Gate — Policy v1

**Phase**: 96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Rule

No adapter is promotable until it passes all 6 mandatory checks. There are no exceptions, no waivers, no "we'll add it later." An adapter that fails any single check is not ready for production use.

## 6 Mandatory Checks

| # | Check | What It Validates |
|---|-------|-------------------|
| 1 | `has_contracts` | Typed interface contracts exist for every capability — inputs, outputs, errors, invariants |
| 2 | `has_tests` | Contract tests, parity tests (if reference backend exists), and smoke tests are present and passing |
| 3 | `has_safety_policy` | Rate limits, cost ceilings, blast radius constraints, rollback procedures are documented and enforced |
| 4 | `has_no_secret_policy` | No hardcoded secrets in any file, no secrets in logs, no secrets in URLs, credentials via env/broker only |
| 5 | `has_docs` | Capability map, failure modes, configuration reference, operational notes exist |
| 6 | `has_tool_mastery` | Tool Mastery Pack is present with best practices, workflows, failure modes, edge cases, quality standards |

## Quality Report Format

```python
{
    "adapter_name": "google_docs_api",
    "checks": [
        {"name": "has_contracts", "passed": True, "reason": "3 contracts defined"},
        {"name": "has_tests", "passed": True, "reason": "12 tests passing"},
        {"name": "has_safety_policy", "passed": True, "reason": "rate limit + cost ceiling set"},
        {"name": "has_no_secret_policy", "passed": True, "reason": "no secrets detected"},
        {"name": "has_docs", "passed": True, "reason": "capability map + ops notes present"},
        {"name": "has_tool_mastery", "passed": False, "reason": "mastery pack missing failure_modes"}
    ],
    "overall_passed": False,
    "promotable": False
}
```

## Promotion Rules

- **`overall_passed`** = all 6 checks are `True`. No partial credit.
- **`promotable`** = `overall_passed`. These are the same value. There is no promotable-but-not-passed state.
- A failing adapter stays at its current lifecycle stage until repairs are made and the gate is re-run.
- Re-running the gate after repairs does not require restarting the entire adapter factory lifecycle.

## Tool Mastery Check (Check #6) — Details

The `has_tool_mastery` check validates that the adapter's mastery pack contains substantive operational expertise:

- **Best practices** — at least 3 non-trivial practices specific to the tool (not generic advice).
- **Failure modes** — at least 2 documented failure modes with symptoms and remediation.
- **Edge cases** — at least 1 edge case that would not be obvious from the API docs alone.
- **Quality standards** — criteria for distinguishing good adapter usage from bad.

A mastery pack that is a copy of the vendor README fails this check. Mastery encodes operational expertise learned from real usage, not marketing documentation.

## Hard Rules

- Never promote an adapter with any check failing.
- Never remove a check from the gate. The 6 checks are the minimum, not the maximum.
- Never treat the tool mastery check as less important than the others. Technical connectivity without operational mastery is a liability.
- Never auto-pass the no-secret check — scan every file in the adapter package.

## Phase 96.6 Update — Mastery Maturity

The quality gate now includes a **7th check**: `tool_mastery_is_mature`. This extends the existing `has_tool_mastery` check (which validates presence) with a maturity validation (which validates completeness).

A Tool Mastery Pack must contain all 4 critical sections to pass the maturity check:

1. **completeness_requirements** — what "complete" means for this tool
2. **failure_modes** — documented failure modes with symptoms and remediation
3. **anti_patterns** — common mistakes that produce silently wrong results
4. **validation_checklist** — ordered verification steps

An adapter that has `has_tool_mastery=True` but an empty or incomplete mastery pack **fails** the maturity check. This is worse than `has_tool_mastery=False` because it creates false confidence — the system believes mastery exists when it does not.

The `evaluate_adapter_maturity()` function in `adapter_quality_gate.py` runs `tool_mastery_is_mature()` as the 7th gate. All 7 checks must pass for promotion. There is no partial credit.

## References

- `eos_ai/adapter_quality_gate.py` — gate implementation (7 checks)
- `eos_ai/adapter_factory.py` — stage 9 invokes the gate
- `eos_ai/adapter_registry.py` — stage 10 reads the gate result
- `docs/operations/adapter_engine_doctrine_v1.md` — 8-layer model
- `docs/operations/adapter_construction_best_practices_policy_v1.md` — construction standards
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery pack requirements
- `docs/operations/mature_adapter_requires_tool_mastery_v1.md` — maturity doctrine
