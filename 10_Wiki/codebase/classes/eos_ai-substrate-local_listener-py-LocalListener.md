---
type: codebase-class
file: eos_ai/substrate/local_listener.py
line: 177
generated: 2026-04-12
---

# LocalListener

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 177

Bounded local activation runtime.

The listener accepts a `LocalTrigger`, performs safety checks (node exists
and isn't UNAVAILABLE), and delegates to `start_open_day(...)` so the
existing ritual body computes readiness, infers a scene, and proposes only
...

## Methods

- [[eos_ai-substrate-local_listener-py-LocalListener-__init__]]`(history) → None` — 
- [[eos_ai-substrate-local_listener-py-LocalListener-emit]]`(trigger) → LocalTrigger` — Emit a trigger and attempt activation. Always returns the trigger
- [[eos_ai-substrate-local_listener-py-LocalListener-manual_activate]]`(node_id, requested_mode, metadata) → LocalTrigger` — 
- [[eos_ai-substrate-local_listener-py-LocalListener-hotkey_activate]]`(node_id) → LocalTrigger` — 
- [[eos_ai-substrate-local_listener-py-LocalListener-simulate_wake_word]]`(node_id) → LocalTrigger` — 
- [[eos_ai-substrate-local_listener-py-LocalListener-simulate_clap]]`(node_id) → LocalTrigger` — 
- [[eos_ai-substrate-local_listener-py-LocalListener-start_voice_session]]`(node_id, role_slug)` — Start a bounded voice session on `node_id` with `role_slug`.
- [[eos_ai-substrate-local_listener-py-LocalListener-_activate]]`(trigger) → None` — 
