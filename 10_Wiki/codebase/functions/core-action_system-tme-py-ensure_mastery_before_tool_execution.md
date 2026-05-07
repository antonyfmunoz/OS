---
type: codebase-function
file: core/action_system/tme.py
line: 80
generated: 2026-05-07
---

# ensure_mastery_before_tool_execution

**File:** [[core-action_system-tme-py]] | **Line:** 80
**Signature:** `ensure_mastery_before_tool_execution(tool_name) → dict[str, Any]`

Mastery Assurance Gate — blocks tool execution without a fresh pack.

Combines the existing ensure_tool_mastery flow with the new
mastery_assurance contract. Returns the MasteryAssuranceDecision
as a dict, or ``{"ok": False, "error": ...}`` on failure.
...
