---
type: codebase-function
file: core/advisor.py
line: 108
generated: 2026-04-12
---

# AdvisorResult.to_canonical

**File:** [[core-advisor-py]] | **Line:** 108
**Signature:** `to_canonical() → dict[str, Any]`

**Class:** [[core-advisor-py-AdvisorResult]]

Return the canonical schema: {decision, reason, modifications}.

This is the shape that callers and the optimizer expect. Always
returns valid structured output regardless of LLM response quality.

## Called By

- [[core-advisor-py-run_with_advisor]]
