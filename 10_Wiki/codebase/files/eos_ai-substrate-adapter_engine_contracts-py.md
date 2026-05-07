---
type: codebase-file
path: eos_ai/substrate/adapter_engine_contracts.py
module: eos_ai.substrate.adapter_engine_contracts
lines: 381
size: 14462
generated: 2026-05-07
---

# eos_ai/substrate/adapter_engine_contracts.py

Adapter Engine contracts for Phase 96.5 + 96.6.

The Adapter Engine is the UMH subsystem that makes external tools,
SaaS platforms, sources, protocols, runtimes, and backends usable
by UMH. It does not merely connect — it integrates operationally.
...

**Lines:** 381 | **Size:** 14,462 bytes

## Used By

- [[eos_ai-substrate-adapter_quality_gate-py]]

## Contains

- **class** [[eos_ai-substrate-adapter_engine_contracts-py-InterfaceType]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AccessPathType]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-ExecutionEnvironmentType]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-CapabilityType]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterType]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterStatus]] — 0 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterProfile]] — 1 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterCapabilityMap]] — 1 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterSafetyPolicy]] — 1 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-ToolMasteryPack]] — 1 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterRegistryEntry]] — 1 methods
- **class** [[eos_ai-substrate-adapter_engine_contracts-py-AdapterPackage]] — 1 methods
- **fn** [[eos_ai-substrate-adapter_engine_contracts-py-tool_mastery_has_completeness_requirements]]`(pack) → bool`
- **fn** [[eos_ai-substrate-adapter_engine_contracts-py-tool_mastery_has_failure_modes]]`(pack) → bool`
- **fn** [[eos_ai-substrate-adapter_engine_contracts-py-tool_mastery_has_anti_patterns]]`(pack) → bool`
- **fn** [[eos_ai-substrate-adapter_engine_contracts-py-tool_mastery_has_validation_checklist]]`(pack) → bool`
- **fn** [[eos_ai-substrate-adapter_engine_contracts-py-tool_mastery_is_mature]]`(pack) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
