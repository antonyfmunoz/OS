---
type: codebase-function
file: eos_ai/reality_context.py
line: 93
generated: 2026-05-07
---

# RealityContext.get_current_reality

**File:** [[eos_ai-reality_context-py]] | **Line:** 93
**Signature:** `get_current_reality() → dict`

**Class:** [[eos_ai-reality_context-py-RealityContext]]

Scan all ventures for current market signals and return a structured dict.

Returns:
    {venture_id: [signal_dict, ...]}  — top 3 signals per venture.
    Empty dict on any failure (never blocks callers).

## Calls

- [[eos_ai-reality_context-py-RealityContext-_get_founder_pattern]]
