---
type: codebase-function
file: eos_ai/substrate/chrome_profile_resolver.py
line: 186
generated: 2026-05-07
---

# build_safe_profile_inventory_result

**File:** [[eos_ai-substrate-chrome_profile_resolver-py]] | **Line:** 186
**Signature:** `build_safe_profile_inventory_result(profiles, target_email, matches) → dict[str, Any]`

Build the safe profile inventory result.

Includes only non-sensitive metadata.
Never includes credentials, cookies, or tokens.

## Calls

- [[eos_ai-substrate-chrome_profile_resolver-py-classify_profile_resolution_status]]
