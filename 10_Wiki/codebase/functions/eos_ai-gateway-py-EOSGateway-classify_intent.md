---
type: codebase-function
file: eos_ai/gateway.py
line: 1762
generated: 2026-04-12
---

# EOSGateway.classify_intent

**File:** [[eos_ai-gateway-py]] | **Line:** 1762
**Signature:** `classify_intent(text) → str`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Classify a natural language message into one of the known intents.
Single Haiku call. Returns the intent word in uppercase.
Falls back to 'UNKNOWN' on any failure.
