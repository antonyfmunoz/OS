---
type: codebase-function
file: eos_ai/substrate/backend_selection_engine.py
line: 66
generated: 2026-05-07
---

# detect_when_backend_is_interface_only

**File:** [[eos_ai-substrate-backend_selection_engine-py]] | **Line:** 66
**Signature:** `detect_when_backend_is_interface_only(profile) → bool`

Interface-only wrappers share failure domain with their underlying backend.

## Called By

- [[eos_ai-substrate-backend_selection_engine-py-detect_when_backend_is_true_fallback]]
- [[eos_ai-substrate-backend_selection_engine-py-select_best_backend]]
