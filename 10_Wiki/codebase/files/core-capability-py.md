---
type: codebase-file
path: core/capability.py
module: core.capability
lines: 511
size: 16799
generated: 2026-05-07
---

# core/capability.py

capability.py — Permission + risk matrix for the unified EOS AI OS.

Every agent carries a CapabilityProfile describing which operations it can
perform. Every step or action is mapped to a required Capability + RiskLevel.
The CapabilityEnforcer answers one question: `may(agent, operation) → bool`.
...

**Lines:** 511 | **Size:** 16,799 bytes

## Used By

- [[core-advisor-py]]
- [[core-agent_harness-py]]
- [[core-security-context-py]]
- [[core-security-environments-py]]
- [[core-security-rbac-py]]
- [[scripts-action_system-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-capability-py-Capability]] — 1 methods
- **class** [[core-capability-py-OperationKind]] — 0 methods
- **class** [[core-capability-py-RiskTier]] — 1 methods
- **class** [[core-capability-py-CapabilityProfile]] — 1 methods
- **class** [[core-capability-py-Decision]] — 0 methods
- **class** [[core-capability-py-CapabilityEnforcer]] — 2 methods
- **fn** [[core-capability-py-cap_implies]]`(have, need) → bool`
- **fn** [[core-capability-py-required_capability]]`(kind) → Capability`
- **fn** [[core-capability-py-coerce_risk]]`(value) → RiskTier`
- **fn** [[core-capability-py-_profile]]`(name, cap, risk) → CapabilityProfile`
- **fn** [[core-capability-py-get_profile]]`(name) → CapabilityProfile`
- **fn** [[core-capability-py-operation_for_action_type]]`(action_type) → OperationKind`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Iterable
```
