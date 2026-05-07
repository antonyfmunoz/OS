---
type: codebase-file
path: eos_ai/substrate/governance_gate_contracts.py
module: eos_ai.substrate.governance_gate_contracts
lines: 173
size: 5384
generated: 2026-05-07
---

# eos_ai/substrate/governance_gate_contracts.py

Governance gate contracts for Phase 94D.4.

Every action passes through governance before execution.
Gates produce ALLOW, REQUIRE_ADVISOR_APPROVAL, BLOCK, or PAUSE_FOR_HUMAN.

...

**Lines:** 173 | **Size:** 5,384 bytes

## Used By

- [[eos_ai-substrate-local_worker_relay_packets-py]]
- [[eos_ai-substrate-worker_node_runtime-py]]

## Contains

- **class** [[eos_ai-substrate-governance_gate_contracts-py-RiskLevel]] — 0 methods
- **class** [[eos_ai-substrate-governance_gate_contracts-py-GateDecision]] — 0 methods
- **class** [[eos_ai-substrate-governance_gate_contracts-py-GovernanceGate]] — 1 methods
- **class** [[eos_ai-substrate-governance_gate_contracts-py-GovernancePolicy]] — 1 methods
- **fn** [[eos_ai-substrate-governance_gate_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-governance_gate_contracts-py-evaluate_action_gate]]`(action_type, policy) → GovernanceGate`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
