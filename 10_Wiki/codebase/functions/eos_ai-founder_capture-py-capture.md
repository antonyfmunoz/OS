---
type: codebase-function
file: eos_ai/founder_capture.py
line: 189
generated: 2026-04-12
---

# capture

**File:** [[eos_ai-founder_capture-py]] | **Line:** 189
**Signature:** `capture(text, ctx, venture_id) → dict`

Main entry point. Assess, capture to Neon and Notion if warranted.
Returns dict with captured, type, neon_ok, notion_ok.

## Calls

- [[eos_ai-founder_capture-py-_classify_venture]]
- [[eos_ai-founder_capture-py-capture_to_neon]]
- [[eos_ai-founder_capture-py-capture_to_notion]]
- [[eos_ai-founder_capture-py-should_capture]]
