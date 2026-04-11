---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1776
generated: 2026-04-11
---

# refresh_ambient_state

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1776
**Signature:** `refresh_ambient_state(ctx) → None`

Compute a fresh reality snapshot and cache it as ambient state.
Called every morning by run_morning_cycle() and on first startup.
The cached state is consumed by CognitiveLoop PERCEIVE (step 1e) so
reality context is always available without a fresh LLM call per message.

## Called By

- [[eos_ai-orchestrator-py-EOSOrchestrator-run_morning_cycle]]
- [[eos_ai-orchestrator-py-start_ambient_refresh_loop]]
