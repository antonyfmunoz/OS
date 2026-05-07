---
type: codebase-file
path: core/environment_bridge/execution_binding_validator.py
module: core.environment_bridge.execution_binding_validator
lines: 282
size: 11177
generated: 2026-05-07
---

# core/environment_bridge/execution_binding_validator.py

Execution Binding Validator for the Environment Bridge.

Validates that an ExecutionBinding has all 6 layers properly bound
before execution is allowed. Rejects ambiguous, incomplete, or
architecturally invalid bindings.
...

**Lines:** 282 | **Size:** 11,177 bytes

## Used By

- [[scripts-validate_w0_coherence_dry-py]]

## Contains

- **class** [[core-environment_bridge-execution_binding_validator-py-BindingValidationResult]] — 1 methods
- **fn** [[core-environment_bridge-execution_binding_validator-py-validate_execution_binding]]`(binding) → BindingValidationResult`
- **fn** [[core-environment_bridge-execution_binding_validator-py-validate_execution_binding_dict]]`(binding_dict) → BindingValidationResult`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_environment]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_execution_surfaces]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_application]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_target_services]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_capabilities]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_proof]]`(binding, result) → None`
- **fn** [[core-environment_bridge-execution_binding_validator-py-_validate_cross_layer_rules]]`(binding, result) → None`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from execution_binding_contracts import DISALLOWED_CHROME_LAUNCH_METHODS
from execution_binding_contracts import WSL_TMUX_SURFACE_TYPES
from execution_binding_contracts import ApplicationLaunchMethod
from execution_binding_contracts import EvidenceType
from execution_binding_contracts import ExecutionBinding
from execution_binding_contracts import ExecutionSurfaceRole
from execution_binding_contracts import ExecutionSurfaceType
from execution_binding_contracts import ProofLevel
from execution_binding_contracts import TargetServiceFamily
```
