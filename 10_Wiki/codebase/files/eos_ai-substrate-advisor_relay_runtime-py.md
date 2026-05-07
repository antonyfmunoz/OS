---
type: codebase-file
path: eos_ai/substrate/advisor_relay_runtime.py
module: eos_ai.substrate.advisor_relay_runtime
lines: 258
size: 8289
generated: 2026-05-07
---

# eos_ai/substrate/advisor_relay_runtime.py

Advisor relay runtime for Phase 94D.4.

Pure/adaptive relay scaffolding that uses message bus contracts from
Phase 94D.3. Creates, correlates, and routes messages between workers,
the advisor session, and interface projections.
...

**Lines:** 258 | **Size:** 8,289 bytes

## Depends On

- [[eos_ai-substrate-message_bus_contracts-py]]
- [[eos_ai-substrate-worker_node_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-create_approval_request_message]]`(action, worker_state, work_order_id, session_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-create_approval_response_message]]`(approval_request_id, decision, work_order_id, source_interface, reason, modifications, correlation_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-route_message_to_interface]]`(message, interface_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-route_message_to_worker]]`(message, worker_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-correlate_response_to_request]]`(response, pending_requests) → MessageEnvelope | None`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-build_worker_status_message]]`(worker_state, work_order_id, detail, session_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-build_worker_result_message]]`(worker_state, work_order_id, status, summary, result_path, session_id) → MessageEnvelope`
- **fn** [[eos_ai-substrate-advisor_relay_runtime-py-apply_human_response_to_worker_state]]`(response, worker_state) → WorkerRuntimeState`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.message_bus_contracts import MessageEnvelope
from eos_ai.substrate.message_bus_contracts import MessagePriority
from eos_ai.substrate.message_bus_contracts import MessageStatus
from eos_ai.substrate.message_bus_contracts import MessageType
from eos_ai.substrate.worker_node_contracts import WorkerAction
from eos_ai.substrate.worker_node_contracts import WorkerRuntimeState
from eos_ai.substrate.worker_node_contracts import WorkerState
```
