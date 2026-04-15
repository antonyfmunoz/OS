---
type: codebase-function
file: eos_ai/substrate/control_commands.py
line: 78
generated: 2026-04-12
---

# validate

**File:** [[eos_ai-substrate-control_commands-py]] | **Line:** 78
**Signature:** `validate(cmd) → tuple[bool, str]`

Shallow envelope validation. Returns (ok, reason).
Never raises. Action-specific rules live in the executor.
