---
type: codebase-function
file: eos_ai/substrate/execution_trace.py
line: 68
generated: 2026-05-07
---

# new_trace

**File:** [[eos_ai-substrate-execution_trace-py]] | **Line:** 68
**Signature:** `new_trace(source, mode, session_name) → dict`

Create a new trace dict with defaults for the full request lifecycle.

Args:
    source: Origin channel — "discord_text", "discord_voice", etc.
    mode: Routing mode — "builder", "product", "unknown".
...

## Called By

- [[core-execution_contract-py-run_task]]
