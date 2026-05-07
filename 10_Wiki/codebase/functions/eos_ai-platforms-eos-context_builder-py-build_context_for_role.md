---
type: codebase-function
file: eos_ai/platforms/eos/context_builder.py
line: 359
generated: 2026-05-07
---

# build_context_for_role

**File:** [[eos_ai-platforms-eos-context_builder-py]] | **Line:** 359
**Signature:** `build_context_for_role(role) → dict[str, Any]`

Build context for any EOS role.

Falls back to EA context for GENERAL or unknown roles.

## Called By

- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_portfolio]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_strategy]]
