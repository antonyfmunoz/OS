---
type: codebase-function
file: eos_ai/higgsfield_client.py
line: 45
generated: 2026-05-07
---

# generate

**File:** [[eos_ai-higgsfield_client-py]] | **Line:** 45
**Signature:** `generate(venture, model_id) → str`

Submit a Higgsfield generation and return the request_id.

Writes a row into `higgsfield_jobs` before submitting so the webhook
handler can validate the `request_id` belongs to EOS. Caller should
NOT poll — the webhook handler owns terminal state.
...

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[scripts-higgsfield_smoke_test-py-main]]
