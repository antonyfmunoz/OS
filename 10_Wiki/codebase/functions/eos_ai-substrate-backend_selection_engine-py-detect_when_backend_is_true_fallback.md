---
type: codebase-function
file: eos_ai/substrate/backend_selection_engine.py
line: 71
generated: 2026-05-07
---

# detect_when_backend_is_true_fallback

**File:** [[eos_ai-substrate-backend_selection_engine-py]] | **Line:** 71
**Signature:** `detect_when_backend_is_true_fallback(profile) → bool`

A true fallback has independence > LEVEL_0 and is not interface-only.

## Calls

- [[eos_ai-substrate-backend_selection_engine-py-detect_when_backend_is_interface_only]]

## Called By

- [[eos_ai-substrate-backend_selection_engine-py-_score_backend]]
- [[eos_ai-substrate-backend_selection_engine-py-filter_backends_by_policy]]
