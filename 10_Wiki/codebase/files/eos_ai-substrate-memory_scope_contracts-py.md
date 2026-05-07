---
type: codebase-file
path: eos_ai/substrate/memory_scope_contracts.py
module: eos_ai.substrate.memory_scope_contracts
lines: 97
size: 3229
generated: 2026-05-07
---

# eos_ai/substrate/memory_scope_contracts.py

Memory scope contracts for Phase 96.4.

W0-001 data defaults to instance memory, not global UMH canon.
CanonicalSourceRecord means normalized schema, not universal truth.
No user-account source may be promoted to global canon without
...

**Lines:** 97 | **Size:** 3,229 bytes

## Used By

- [[eos_ai-substrate-instance_ingestion_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-memory_scope_contracts-py-MemoryScope]] — 0 methods
- **class** [[eos_ai-substrate-memory_scope_contracts-py-PromotionPath]] — 0 methods
- **class** [[eos_ai-substrate-memory_scope_contracts-py-MemoryScopeAssignment]] — 2 methods
- **fn** [[eos_ai-substrate-memory_scope_contracts-py-raw_account_data_default_scope]]`() → MemoryScope`
- **fn** [[eos_ai-substrate-memory_scope_contracts-py-canonical_source_record_is_not_global_canon]]`() → bool`
- **fn** [[eos_ai-substrate-memory_scope_contracts-py-can_promote_to_global_canon]]`(current_scope, abstracted, founder_approved) → bool`
- **fn** [[eos_ai-substrate-memory_scope_contracts-py-requires_abstraction_for_global]]`(scope) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
