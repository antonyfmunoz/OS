---
type: codebase-function
file: eos_ai/platforms/eos/delegation.py
line: 53
generated: 2026-05-07
---

# choose_delegate

**File:** [[eos_ai-platforms-eos-delegation-py]] | **Line:** 53
**Signature:** `choose_delegate(intent) → EOSRole | None`

Return the specialist role to delegate to, or None if EA handles directly.

Never returns EOSRole.GENERAL or any builder-type role.
