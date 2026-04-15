---
type: codebase-function
file: services/handlers/pipeline_handler.py
line: 18
generated: 2026-04-12
---

# detect_pipeline_update

**File:** [[services-handlers-pipeline_handler-py]] | **Line:** 18
**Signature:** `detect_pipeline_update(text) → tuple[str, str] | None`

Detect natural language pipeline stage updates.
Returns (stage, lead_hint) or None if not a pipeline update.

Examples:
  "just closed that lead" → ("Won", "")
...

## Called By

- [[services-handlers-pipeline_handler-py-handle_pipeline_update]]
