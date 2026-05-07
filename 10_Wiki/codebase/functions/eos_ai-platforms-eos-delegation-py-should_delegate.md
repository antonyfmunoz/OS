---
type: codebase-function
file: eos_ai/platforms/eos/delegation.py
line: 43
generated: 2026-05-07
---

# should_delegate

**File:** [[eos_ai-platforms-eos-delegation-py]] | **Line:** 43
**Signature:** `should_delegate(intent) → bool`

Return True if this intent should be delegated to a specialist role.

EA handles: status, review, execution intake, direct communication, unknown.
Delegates: strategy → CEO, portfolio → Portfolio Advisor.
