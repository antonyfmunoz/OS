---
type: codebase-file
path: core/adapter_engine/external_boundary_law.py
module: core.adapter_engine.external_boundary_law
lines: 227
size: 8562
generated: 2026-05-07
---

# core/adapter_engine/external_boundary_law.py

UMH External Boundary Law.

No external system, tool, SaaS, model, runtime, environment, human
approval process, data source, filesystem, browser, operating system,
or physical-world actor may be accessed directly by UMH.
...

**Lines:** 227 | **Size:** 8,562 bytes

## Contains

- **class** [[core-adapter_engine-external_boundary_law-py-BoundaryLawStatus]] — 0 methods
- **class** [[core-adapter_engine-external_boundary_law-py-BoundaryLawDecision]] — 1 methods
- **fn** [[core-adapter_engine-external_boundary_law-py-evaluate_external_boundary_law]]`(interaction) → BoundaryLawDecision`
- **fn** [[core-adapter_engine-external_boundary_law-py-external_boundary_blocks_execution]]`(decision) → bool`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_adapter_for_external_system]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_contract_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_governance_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_proof_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_mastery_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_maturity_gate_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_environment_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-require_worker_for_external_interaction]]`(interaction, decision) → None`
- **fn** [[core-adapter_engine-external_boundary_law-py-summarize_boundary_law_decision]]`(decision) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from external_interaction_contract import ExternalInteraction
from external_interaction_contract import external_interaction_has_adapter
from external_interaction_contract import external_interaction_has_capability_contract
from external_interaction_contract import external_interaction_has_environment_when_required
from external_interaction_contract import external_interaction_has_governance
from external_interaction_contract import external_interaction_has_mastery_requirements
from external_interaction_contract import external_interaction_has_maturity_gate
from external_interaction_contract import external_interaction_has_proof_requirements
from external_interaction_contract import external_interaction_has_worker_when_required
```
