---
type: codebase-class
file: core/advisor.py
line: 83
generated: 2026-04-12
---

# AdvisorResult

**File:** [[core-advisor-py]] | **Line:** 83

Structured output from an advisor call.

decision:          approve / modify / reject
reasoning:         why the advisor made this decision
suggested_changes: concrete refinements (only meaningful for MODIFY)
...

## Methods

- [[core-advisor-py-AdvisorResult-to_dict]]`() → dict[str, Any]` — 
- [[core-advisor-py-AdvisorResult-to_canonical]]`() → dict[str, Any]` — Return the canonical schema: {decision, reason, modifications}.

## Decorators

- `@dataclass`
