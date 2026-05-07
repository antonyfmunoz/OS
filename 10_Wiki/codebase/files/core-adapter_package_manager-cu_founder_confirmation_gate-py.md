---
type: codebase-file
path: core/adapter_package_manager/cu_founder_confirmation_gate.py
module: core.adapter_package_manager.cu_founder_confirmation_gate
lines: 116
size: 3984
generated: 2026-05-07
---

# core/adapter_package_manager/cu_founder_confirmation_gate.py

CU Founder Confirmation Gate.

When CU acts through a local visible GUI and the remote orchestrator
cannot independently verify the visible result, founder visual
confirmation can be required before final maturity is accepted.
...

**Lines:** 116 | **Size:** 3,984 bytes

## Contains

- **class** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-FounderConfirmationStatus]] — 0 methods
- **class** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-FounderConfirmationGate]] — 1 methods
- **fn** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-build_w_gdrive_cu_founder_confirmation_gate]]`() → FounderConfirmationGate`
- **fn** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-founder_confirmation_required_for_cu]]`(audit_result) → bool`
- **fn** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-apply_founder_confirmation]]`(gate, confirmation_status, founder_response) → FounderConfirmationGate`
- **fn** [[core-adapter_package_manager-cu_founder_confirmation_gate-py-founder_confirmation_blocks_final_maturity]]`(gate) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from cu_proof_audit import CUProofAuditResult
from cu_proof_audit import CUProofQualityStatus
```
