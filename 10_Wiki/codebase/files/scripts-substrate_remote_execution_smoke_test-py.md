---
type: codebase-file
path: scripts/substrate_remote_execution_smoke_test.py
module: scripts.substrate_remote_execution_smoke_test
lines: 234
size: 7639
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_remote_execution_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Control Layer v2 — Remote Execution smoke test.

Verifies the queue→daemon→executor→ack loop end-to-end without ever
introducing networking, threads, or a second pipeline.

...

**Lines:** 234 | **Size:** 7,639 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-remote_executor-py]]

## Contains

- **fn** [[scripts-substrate_remote_execution_smoke_test-py-check]]`(name, ok, detail) → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-_fresh_node]]`() → str`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_enqueue_and_run_once]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_invalid_node_skipped]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_malformed_rejected]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_queue_cap]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_batch_processing]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_idempotent_ack]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_hot_path_imports]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-test_identity]]`() → None`
- **fn** [[scripts-substrate_remote_execution_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import uuid
from eos_ai.substrate import control_bridge as bridge
from eos_ai.substrate import control_commands as cc
from eos_ai.substrate.remote_executor import RemoteExecutor
from eos_ai.substrate import remote_identity
```
