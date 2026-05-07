---
type: codebase-file
path: eos_ai/substrate/worker_node_runtime.py
module: eos_ai.substrate.worker_node_runtime
lines: 208
size: 7681
generated: 2026-05-07
---

# eos_ai/substrate/worker_node_runtime.py

Worker node organism runtime for Phase 94D.4.

Pure functions implementing worker lifecycle logic. No network calls.
No computer-use execution. No side effects.

...

**Lines:** 208 | **Size:** 7,681 bytes

## Depends On

- [[eos_ai-substrate-governance_gate_contracts-py]]
- [[eos_ai-substrate-message_bus_contracts-py]]
- [[eos_ai-substrate-work_order_contracts-py]]
- [[eos_ai-substrate-worker_node_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-worker_node_runtime-py-validate_worker_can_claim]]`(work_order, worker_profile) → tuple[bool, str]`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-_infer_required_capabilities]]`(work_order) → list[str]`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-create_worker_execution_plan]]`(work_order, worker_profile) → list[WorkerAction]`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-next_worker_state]]`(current_state, event, mode) → WorkerState`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-should_request_advisor_approval]]`(action, governance_policy) → bool`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-build_approval_request_for_action]]`(action, work_order_id, worker_state) → MessageEnvelope`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-apply_advisor_response]]`(response, worker_state) → WorkerRuntimeState`
- **fn** [[eos_ai-substrate-worker_node_runtime-py-create_worker_feedback_event]]`(worker_id, work_order_id, event_type, detail, data) → WorkerFeedbackEvent`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.governance_gate_contracts import GateDecision
from eos_ai.substrate.governance_gate_contracts import GovernancePolicy
from eos_ai.substrate.governance_gate_contracts import evaluate_action_gate
from eos_ai.substrate.message_bus_contracts import MessageEnvelope
from eos_ai.substrate.message_bus_contracts import MessagePriority
from eos_ai.substrate.message_bus_contracts import MessageType
from eos_ai.substrate.work_order_contracts import WorkOrder
from eos_ai.substrate.worker_node_contracts import WorkerAction
from eos_ai.substrate.worker_node_contracts import WorkerFeedbackEvent
from eos_ai.substrate.worker_node_contracts import WorkerMode
from eos_ai.substrate.worker_node_contracts import WorkerProfile
from eos_ai.substrate.worker_node_contracts import WorkerRuntimeState
from eos_ai.substrate.worker_node_contracts import WorkerState
```
