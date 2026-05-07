---
type: codebase-function
file: eos_ai/substrate/remote_executor.py
line: 69
generated: 2026-05-07
---

# RemoteExecutor.poll_once

**File:** [[eos_ai-substrate-remote_executor-py]] | **Line:** 69
**Signature:** `poll_once(node_id) → dict[str, Any]`

**Class:** [[eos_ai-substrate-remote_executor-py-RemoteExecutor]]

Drain up to HARD_BATCH_CAP pending commands for `node_id` once.

Returns:
    {
        "ok": bool,
...

## Called By

- [[eos_ai-substrate-remote_executor-py-RemoteExecutor-run_loop]]
- [[scripts-substrate_remote_execution_smoke_test-py-test_batch_processing]]
- [[scripts-substrate_remote_execution_smoke_test-py-test_enqueue_and_run_once]]
- [[scripts-substrate_remote_execution_smoke_test-py-test_invalid_node_skipped]]
- [[scripts-substrate_remote_execution_smoke_test-py-test_malformed_rejected]]
- [[scripts-substrate_remote_executor_daemon-py-_cmd_run_once]]
