---
type: codebase-file
path: eos_ai/platforms/eos/execution_bridge.py
module: eos_ai.platforms.eos.execution_bridge
lines: 317
size: 11812
generated: 2026-05-07
---

# eos_ai/platforms/eos/execution_bridge.py

ExecutionBridge — immediate task/pipeline execution from EAResponse.

Bridges the EOS platform layer into substrate task_execution and
pipeline_execution.  Called after EA creates work items so they begin
executing without waiting for the next scheduler tick.
...

**Lines:** 317 | **Size:** 11,812 bytes

## Contains

- **class** [[eos_ai-platforms-eos-execution_bridge-py-ExecutionBridgeResult]] — 1 methods
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_stream]]`(event_type_name, message) → None`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_is_local_available]]`() → bool`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_get_routing_decision]]`() → 'tuple[bool, dict]'`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_get_operator_session]]`()`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_execute_single_task]]`(task_id, result) → None`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-_execute_single_pipeline]]`(pipeline_id, result) → None`
- **fn** [[eos_ai-platforms-eos-execution_bridge-py-execute_created_work_immediately]]`(task_ids, pipeline_ids) → ExecutionBridgeResult`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from dataclasses import field
```
