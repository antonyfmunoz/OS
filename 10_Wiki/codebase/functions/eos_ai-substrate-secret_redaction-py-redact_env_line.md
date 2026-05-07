---
type: codebase-function
file: eos_ai/substrate/secret_redaction.py
line: 56
generated: 2026-05-07
---

# redact_env_line

**File:** [[eos_ai-substrate-secret_redaction-py]] | **Line:** 56
**Signature:** `redact_env_line(line) → str`

Redact the value portion of a KEY=VALUE line if key looks secret.

## Calls

- [[eos_ai-substrate-secret_redaction-py-looks_like_secret_key]]

## Called By

- [[eos_ai-substrate-secret_redaction-py-redact_potential_secrets_in_output]]
