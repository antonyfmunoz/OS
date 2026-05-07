---
type: codebase-function
file: services/higgsfield_webhook.py
line: 57
generated: 2026-05-07
---

# handle_webhook

**File:** [[services-higgsfield_webhook-py]] | **Line:** 57
**Signature:** `handle_webhook(payload) → tuple[dict, int]`

Pure function — useful for tests. Called by the Flask route.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[services-higgsfield_webhook-py-_download]]
- [[services-higgsfield_webhook-py-_extract_output_url]]

## Called By

- [[services-higgsfield_webhook-py-register]]
