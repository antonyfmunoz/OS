---
type: codebase-function
file: eos_ai/substrate/secret_redaction.py
line: 69
generated: 2026-05-07
---

# redact_secret_values

**File:** [[eos_ai-substrate-secret_redaction-py]] | **Line:** 69
**Signature:** `redact_secret_values(text, known_secret_values) → str`

Replace any occurrence of known secret values in text with [REDACTED].

This is the nuclear option — if a secret value somehow appears in output,
this catches it before it reaches any observable channel.
