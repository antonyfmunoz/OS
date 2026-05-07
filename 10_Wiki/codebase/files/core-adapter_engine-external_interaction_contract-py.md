---
type: codebase-file
path: core/adapter_engine/external_interaction_contract.py
module: core.adapter_engine.external_interaction_contract
lines: 199
size: 7593
generated: 2026-05-07
---

# core/adapter_engine/external_interaction_contract.py

External interaction contract for the UMH Adapter Engine.

Every interaction with an external system must be represented as an
ExternalInteraction record. This contract enforces that all external
interactions have an adapter, governance, proof requirements, and
...

**Lines:** 199 | **Size:** 7,593 bytes

## Contains

- **class** [[core-adapter_engine-external_interaction_contract-py-ExternalInteractionStatus]] — 0 methods
- **class** [[core-adapter_engine-external_interaction_contract-py-ExternalInteractionRisk]] — 0 methods
- **class** [[core-adapter_engine-external_interaction_contract-py-ExternalInteraction]] — 1 methods
- **fn** [[core-adapter_engine-external_interaction_contract-py-build_external_interaction]]`(interaction_id, intent_summary, external_system, external_system_type, adapter_category, required_adapter_package, required_adapter_family, capability_contract, target_environment, required_worker_runtime, work_packet_id, governance_policy, mastery_requirements, proof_requirements, maturity_gate, risk_level, approval_required) → ExternalInteraction`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_adapter]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_governance]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_proof_requirements]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_maturity_gate]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_mastery_requirements]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_capability_contract]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_environment_when_required]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_has_worker_when_required]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-external_interaction_is_validated]]`(interaction) → bool`
- **fn** [[core-adapter_engine-external_interaction_contract-py-summarize_external_interaction]]`(interaction) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
