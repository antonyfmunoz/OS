---
type: codebase-function
file: eos_ai/substrate/target_policy.py
line: 91
generated: 2026-04-11
---

# resolve_execution_target

**File:** [[eos_ai-substrate-target_policy-py]] | **Line:** 91
**Signature:** `resolve_execution_target(mode, metadata) → str`

Return ``"local"`` or ``"vps"`` for *mode* + optional *metadata*.

Resolution order:
  1. Product-mode delegation check (if enabled + keyword match).
  2. Env-var override for the mode's default target.
...

## Calls

- [[eos_ai-substrate-target_policy-py-_clamp_target]]
- [[eos_ai-substrate-target_policy-py-_mode_default]]
- [[eos_ai-substrate-target_policy-py-should_delegate_product_to_local]]
