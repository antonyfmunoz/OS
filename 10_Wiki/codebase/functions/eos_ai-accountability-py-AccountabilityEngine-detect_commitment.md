---
type: codebase-function
file: eos_ai/accountability.py
line: 52
generated: 2026-04-12
---

# AccountabilityEngine.detect_commitment

**File:** [[eos_ai-accountability-py]] | **Line:** 52
**Signature:** `detect_commitment(text, venture_id) → Commitment | None`

**Class:** [[eos_ai-accountability-py-AccountabilityEngine]]

Detect if the text contains a commitment signal.
If yes, log it and return the Commitment object.
If no, return None.

## Calls

- [[eos_ai-accountability-py-AccountabilityEngine-_save_commitment]]
