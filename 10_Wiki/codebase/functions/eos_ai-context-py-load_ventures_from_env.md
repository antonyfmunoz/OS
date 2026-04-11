---
type: codebase-function
file: eos_ai/context.py
line: 21
generated: 2026-04-11
---

# load_ventures_from_env

**File:** [[eos_ai-context-py]] | **Line:** 21
**Signature:** `load_ventures_from_env() → list`

Load venture/company primitives from environment.
Falls back to empty list if not configured.
Format: VENTURES_JSON env var containing JSON array.

## Called By

- [[eos_ai-context-py-load_context_from_env]]
