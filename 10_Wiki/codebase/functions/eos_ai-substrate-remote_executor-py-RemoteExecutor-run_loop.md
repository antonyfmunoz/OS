---
type: codebase-function
file: eos_ai/substrate/remote_executor.py
line: 164
generated: 2026-04-12
---

# RemoteExecutor.run_loop

**File:** [[eos_ai-substrate-remote_executor-py]] | **Line:** 164
**Signature:** `run_loop(node_id, interval_s, max_batch) → dict[str, Any]`

**Class:** [[eos_ai-substrate-remote_executor-py-RemoteExecutor]]

Run poll_once on a fixed interval until stop() is called.

max_batch is clamped to <= HARD_BATCH_CAP. Loop body is wrapped so a
single bad iteration cannot kill the daemon — failures are recorded
and the loop continues after the configured interval.

## Calls

- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-poll_once]]

## Called By

- [[scripts-substrate_remote_executor_daemon-py-_cmd_run]]
