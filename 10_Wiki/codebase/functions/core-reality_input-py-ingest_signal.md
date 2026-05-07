---
type: codebase-function
file: core/reality_input.py
line: 204
generated: 2026-05-07
---

# ingest_signal

**File:** [[core-reality_input-py]] | **Line:** 204
**Signature:** `ingest_signal(raw_input) → RealitySignal`

Parse raw external input into a RealitySignal with primitive tags.

This is the primary entry point for the reality input layer.
Every external signal the system receives should pass through here.

...

## Calls

- [[core-reality_input-py-_classify_text]]
- [[core-reality_input-py-_store_signal]]
