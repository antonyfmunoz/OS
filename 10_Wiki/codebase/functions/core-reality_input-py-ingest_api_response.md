---
type: codebase-function
file: core/reality_input.py
line: 284
generated: 2026-05-07
---

# ingest_api_response

**File:** [[core-reality_input-py]] | **Line:** 284
**Signature:** `ingest_api_response(endpoint, status_code, body) → RealitySignal`

Convenience: ingest an API response as a reality signal.

Classifies based on status code and body content.

## Calls

- [[core-reality_input-py-_classify_text]]
- [[core-reality_input-py-_store_signal]]
