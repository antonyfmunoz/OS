---
type: codebase-class
file: eos_ai/substrate/remote_executor.py
line: 35
generated: 2026-05-07
---

# RemoteExecutor

**File:** [[eos_ai-substrate-remote_executor-py]] | **Line:** 35

Polling reader that converts queued commands into local executions.

## Methods

- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-__init__]]`() → None` — 
- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-stop]]`() → None` — Cooperatively halt run_loop on its next iteration.
- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-status]]`(node_id) → dict[str, Any]` — Inspect-only summary. Never raises.
- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-poll_once]]`(node_id) → dict[str, Any]` — Drain up to HARD_BATCH_CAP pending commands for `node_id` once.
- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-run_loop]]`(node_id, interval_s, max_batch) → dict[str, Any]` — Run poll_once on a fixed interval until stop() is called.
