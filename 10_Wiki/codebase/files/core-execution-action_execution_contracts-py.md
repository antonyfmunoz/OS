---
type: codebase-file
path: core/execution/action_execution_contracts.py
module: core.execution.action_execution_contracts
lines: 236
size: 8232
generated: 2026-05-07
---

# core/execution/action_execution_contracts.py

Action / Execution Separation Law contracts.

Action = intended state transformation.
Capability = abstract ability required.
Adapter = connection/translation boundary.
...

**Lines:** 236 | **Size:** 8,232 bytes

## Contains

- **class** [[core-execution-action_execution_contracts-py-ActionType]] — 0 methods
- **class** [[core-execution-action_execution_contracts-py-ExecutionSeparationStatus]] — 0 methods
- **class** [[core-execution-action_execution_contracts-py-ActionContract]] — 1 methods
- **class** [[core-execution-action_execution_contracts-py-ExecutionBinding]] — 1 methods
- **fn** [[core-execution-action_execution_contracts-py-build_action_contract]]`(action_id, action_type, intended_state_change, required_capabilities, required_adapters, required_environments, required_workers, required_mastery, governance_policy, risk_level, authority_required, success_criteria, failure_modes, proof_requirements, idempotency_key) → ActionContract`
- **fn** [[core-execution-action_execution_contracts-py-build_execution_binding]]`(action_id, work_packet_id, environment_id, worker_runtime_id, adapter_boundaries, actuator_type, trace_id) → ExecutionBinding`
- **fn** [[core-execution-action_execution_contracts-py-action_contract_is_complete]]`(action) → bool`
- **fn** [[core-execution-action_execution_contracts-py-execution_binding_is_complete]]`(binding) → bool`
- **fn** [[core-execution-action_execution_contracts-py-validate_action_execution_separation]]`(action, binding) → ExecutionSeparationStatus`
- **fn** [[core-execution-action_execution_contracts-py-summarize_action_execution_contract]]`(action, binding) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
