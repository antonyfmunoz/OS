---
type: codebase-function
file: eos_ai/error_handler.py
line: 147
generated: 2026-04-12
---

# ErrorHandler.classify_error

**File:** [[eos_ai-error_handler-py]] | **Line:** 147
**Signature:** `classify_error(error, context) → str`

**Class:** [[eos_ai-error_handler-py-ErrorHandler]]

Map an exception to a policy key. Rules-based — no LLM call.
Order matters: more specific checks first.

## Called By

- [[eos_ai-error_handler-py-ErrorHandler-handle]]
