---
type: codebase-function
file: eos_ai/os_trinity.py
line: 362
generated: 2026-05-07
---

# OSTrinity.sync_from_user_model

**File:** [[eos_ai-os_trinity-py]] | **Line:** 362
**Signature:** `sync_from_user_model(user_id) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

Read the EOS-specific user_profiles row and promote relevant fields
to the harness-level user_intelligence_profiles table.

Syncs: communication_style, north_star, decision_patterns.
Returns True if sync succeeded (even partially).

## Calls

- [[eos_ai-os_trinity-py-OSTrinity-update_intelligence_profile]]
