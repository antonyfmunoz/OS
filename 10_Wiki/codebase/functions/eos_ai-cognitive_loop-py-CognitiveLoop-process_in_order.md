---
type: codebase-function
file: eos_ai/cognitive_loop.py
line: 1230
generated: 2026-04-12
---

# CognitiveLoop.process_in_order

**File:** [[eos_ai-cognitive_loop-py]] | **Line:** 1230
**Signature:** `process_in_order(input, agent, task_type, venture_id) → 'CognitiveResult'`

**Class:** [[eos_ai-cognitive_loop-py-CognitiveLoop]]

Process a message and attach a monotonic turn number to the result.

Callers that need strict ordering (e.g. the Telegram handler after
the per-chat lock is acquired) should use this instead of run() so
the result carries a turn_number they can use for logging / ordering
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
