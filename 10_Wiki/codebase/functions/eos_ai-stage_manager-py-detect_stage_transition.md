---
type: codebase-function
file: eos_ai/stage_manager.py
line: 67
generated: 2026-04-11
---

# detect_stage_transition

**File:** [[eos_ai-stage_manager-py]] | **Line:** 67
**Signature:** `detect_stage_transition(text) → dict`

Detect if founder's message signals a stage transition.
Returns {'detected': bool, 'transition': str, 'new_stage': int}.
Called by gateway.py before routing.
