---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1799
generated: 2026-04-12
---

# start_ambient_refresh_loop

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1799
**Signature:** `start_ambient_refresh_loop(ctx) → None`

Start a background daemon thread that refreshes ambient state every
30 minutes. Safe to call from any long-running process (Telegram bot,
API server). The thread is daemonized — it exits when the main process
exits.

...

## Calls

- [[eos_ai-orchestrator-py-refresh_ambient_state]]
