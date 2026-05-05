---
type: codebase-function
file: services/handlers/pipeline_handler.py
line: 105
generated: 2026-04-12
---

# handle_pipeline_update

**File:** [[services-handlers-pipeline_handler-py]] | **Line:** 105
**Signature:** `handle_pipeline_update(message, text) → bool`

Check for pipeline update in message text.
If detected, update Notion and send confirmation.
Returns True if handled, False otherwise.

## Calls

- [[services-handlers-pipeline_handler-py-detect_pipeline_update]]
