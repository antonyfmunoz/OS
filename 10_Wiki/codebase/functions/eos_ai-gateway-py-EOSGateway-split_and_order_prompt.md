---
type: codebase-function
file: eos_ai/gateway.py
line: 1714
generated: 2026-04-12
---

# EOSGateway.split_and_order_prompt

**File:** [[eos_ai-gateway-py]] | **Line:** 1714
**Signature:** `split_and_order_prompt(text) → list[str]`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Detect whether a prompt contains multiple distinct instructions and
        return them as an ordered list.  Single-part prompts return [text].

        Detection priority:
          1. Numbered list  — "1. ...
...

## Called By

- [[eos_ai-gateway-py-EOSGateway-handle_ordered]]
