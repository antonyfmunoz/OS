---
type: codebase-function
file: eos_ai/cc_sdk.py
line: 259
generated: 2026-04-12
---

# query_cc_sync

**File:** [[eos_ai-cc_sdk-py]] | **Line:** 259
**Signature:** `query_cc_sync(prompt, system, task_type, session_id, max_budget_usd, agent_id, timeout) → CCResult | None`

Synchronous wrapper around query_cc().

Safe to call from model_router and other sync code.
Creates a new event loop if none is running.

## Calls

- [[eos_ai-cc_sdk-py-_get_claude_pids]]
- [[eos_ai-cc_sdk-py-_is_nested_cc_session]]
- [[eos_ai-cc_sdk-py-_kill_orphaned_claude_procs]]
- [[eos_ai-cc_sdk-py-query_cc]]

## Called By

- [[eos_ai-model_router-py-call_with_fallback]]
