---
type: codebase-function
file: eos_ai/substrate/target_policy.py
line: 169
generated: 2026-04-12
---

# should_delegate_product_to_local

**File:** [[eos_ai-substrate-target_policy-py]] | **Line:** 169
**Signature:** `should_delegate_product_to_local(text, metadata) → bool`

Check whether product mode should delegate to local execution.

Returns ``True`` only when ALL of:
  1. ``EOS_PRODUCT_ALLOW_LOCAL_DELEGATION`` is truthy.
  2. A deterministic trigger fires (keyword match in *text* or
...

## Calls

- [[eos_ai-substrate-target_policy-py-_check_delegation]]

## Called By

- [[eos_ai-substrate-target_policy-py-resolve_execution_target]]
