---
type: codebase-function
file: eos_ai/cc_sdk.py
line: 64
generated: 2026-04-11
---

# query_cc

**File:** [[eos_ai-cc_sdk-py]] | **Line:** 64
**Signature:** `query_cc(prompt, system, task_type, session_id, max_budget_usd, agent_id, timeout) → CCResult | None`

Query Claude Code via the Agent SDK.

Args:
    prompt: The user prompt to send.
    system: Optional system prompt.
...

## Calls

- [[eos_ai-cc_sdk-py-_is_nested_cc_session]]

## Called By

- [[eos_ai-cc_sdk-py-query_cc_sync]]
