---
type: codebase-function
file: eos_ai/substrate/substrate_projection_boundaries.py
line: 178
generated: 2026-05-07
---

# detect_umh_eos_confusion

**File:** [[eos_ai-substrate-substrate_projection_boundaries-py]] | **Line:** 178
**Signature:** `detect_umh_eos_confusion(text) → list[str]`

Detect statements that collapse EOS into UMH or reverse the relationship.

Returns list of warning messages. Empty list means no confusion detected.
