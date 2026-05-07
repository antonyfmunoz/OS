---
type: codebase-function
file: eos_ai/founder_rate.py
line: 257
generated: 2026-05-07
---

# detect_delegation_threshold

**File:** [[eos_ai-founder_rate-py]] | **Line:** 257
**Signature:** `detect_delegation_threshold(ctx) → list[dict]`

Detect tasks Antony is repeatedly handling himself
that should be delegated. Returns list of violations.
Looks for dex_task events appearing 3+ times in 30 days.
