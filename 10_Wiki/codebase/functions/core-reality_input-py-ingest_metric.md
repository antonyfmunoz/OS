---
type: codebase-function
file: core/reality_input.py
line: 237
generated: 2026-05-07
---

# ingest_metric

**File:** [[core-reality_input-py]] | **Line:** 237
**Signature:** `ingest_metric(name, value) → RealitySignal`

Convenience: ingest a numeric metric as a reality signal.

Automatically classifies with OUTCOME, SIGNAL, and adds GOAL
if a target is provided, FEEDBACK if value < target.

## Calls

- [[core-reality_input-py-_store_signal]]
