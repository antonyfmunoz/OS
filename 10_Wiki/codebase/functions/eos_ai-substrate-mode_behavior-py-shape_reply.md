---
type: codebase-function
file: eos_ai/substrate/mode_behavior.py
line: 212
generated: 2026-04-12
---

# shape_reply

**File:** [[eos_ai-substrate-mode_behavior-py]] | **Line:** 212
**Signature:** `shape_reply(text) → str`

Apply mode-appropriate shaping to a router reply.

Args:
    text: Raw reply text from the router/Claude session.
    mode: "builder" | "product" | "unknown" | None.
...

## Calls

- [[eos_ai-substrate-mode_behavior-py-_enforce_builder_structure]]
- [[eos_ai-substrate-mode_behavior-py-_log]]
- [[eos_ai-substrate-mode_behavior-py-_shape_product]]
