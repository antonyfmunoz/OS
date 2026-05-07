---
type: codebase-file
path: eos_ai/substrate/adapter_quality_gate.py
module: eos_ai.substrate.adapter_quality_gate
lines: 195
size: 6399
generated: 2026-05-07
---

# eos_ai/substrate/adapter_quality_gate.py

Adapter quality gate for Phase 96.5 + 96.6.

An adapter cannot be promoted to the registry unless it passes
all quality checks: contracts, tests, safety policy, no-secret
policy, documentation, tool mastery, parity/completeness.
...

**Lines:** 195 | **Size:** 6,399 bytes

## Depends On

- [[eos_ai-substrate-adapter_engine_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-adapter_quality_gate-py-QualityCheckResult]] — 1 methods
- **class** [[eos_ai-substrate-adapter_quality_gate-py-AdapterQualityReport]] — 1 methods
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_required_contracts]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_tests]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_safety_policy]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_no_secret_policy]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_docs]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_tool_mastery]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_is_promotable]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-_score_and_gaps]]`(checks) → tuple[float, list[str]]`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-evaluate_adapter_quality]]`(entry) → AdapterQualityReport`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-adapter_tool_mastery_is_mature]]`(entry) → bool`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-evaluate_adapter_maturity]]`(entry) → AdapterQualityReport`
- **fn** [[eos_ai-substrate-adapter_quality_gate-py-build_adapter_quality_report]]`(entry) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.adapter_engine_contracts import AdapterRegistryEntry
from eos_ai.substrate.adapter_engine_contracts import ToolMasteryPack
from eos_ai.substrate.adapter_engine_contracts import tool_mastery_is_mature
```
