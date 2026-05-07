---
type: codebase-file
path: core/adapter_engine/adapter_boundary_validator.py
module: core.adapter_engine.adapter_boundary_validator
lines: 245
size: 8691
generated: 2026-05-07
---

# core/adapter_engine/adapter_boundary_validator.py

Adapter boundary validator for the UMH Adapter Engine.

Validates that external interactions have proper adapter boundaries.
Detects direct external use, missing environment adapters, missing
human approval adapters, missing model adapters, and missing data
...

**Lines:** 245 | **Size:** 8,691 bytes

## Contains

- **class** [[core-adapter_engine-adapter_boundary_validator-py-AdapterBoundaryValidationStatus]] — 0 methods
- **class** [[core-adapter_engine-adapter_boundary_validator-py-AdapterBoundaryValidationResult]] — 1 methods
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_adapter_boundary]]`(interaction) → AdapterBoundaryValidationResult`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_no_direct_external_use]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_environment_adapter_present]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_human_approval_adapter_present]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_model_adapter_present]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_data_source_adapter_present]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-validate_mastery_requirements_present]]`(interaction, result) → None`
- **fn** [[core-adapter_engine-adapter_boundary_validator-py-adapter_boundary_blocks_execution]]`(result) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from adapter_taxonomy import AdapterCategory
from adapter_taxonomy import classify_external_system
from adapter_taxonomy import ExternalSystemType
from adapter_taxonomy import adapter_category_requires_tool_mastery
from external_interaction_contract import ExternalInteraction
from external_interaction_contract import external_interaction_has_adapter
from external_interaction_contract import external_interaction_has_environment_when_required
from external_interaction_contract import external_interaction_has_governance
from external_interaction_contract import external_interaction_has_mastery_requirements
from external_interaction_contract import external_interaction_has_maturity_gate
from external_interaction_contract import external_interaction_has_proof_requirements
from external_interaction_contract import external_interaction_has_worker_when_required
from external_interaction_contract import external_interaction_is_validated
```
