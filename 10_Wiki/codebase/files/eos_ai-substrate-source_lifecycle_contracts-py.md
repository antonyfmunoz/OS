---
type: codebase-file
path: eos_ai/substrate/source_lifecycle_contracts.py
module: eos_ai.substrate.source_lifecycle_contracts
lines: 136
size: 4537
generated: 2026-05-07
---

# eos_ai/substrate/source_lifecycle_contracts.py

Source lifecycle contracts for Phase 96.3.

Ingest-first / review-after lifecycle:
1. Discover → 2. Authorize → 3. Ingest raw → 4. Normalize →
5. Validate coverage → 6. Parity validate → 7. Review →
...

**Lines:** 136 | **Size:** 4,537 bytes

## Contains

- **class** [[eos_ai-substrate-source_lifecycle_contracts-py-SourceLifecycleStage]] — 0 methods
- **class** [[eos_ai-substrate-source_lifecycle_contracts-py-SourceReviewType]] — 0 methods
- **class** [[eos_ai-substrate-source_lifecycle_contracts-py-SourceIngestionRule]] — 0 methods
- **class** [[eos_ai-substrate-source_lifecycle_contracts-py-SourceLifecycleRecord]] — 3 methods
- **fn** [[eos_ai-substrate-source_lifecycle_contracts-py-can_ingest_without_review]]`(stage) → bool`
- **fn** [[eos_ai-substrate-source_lifecycle_contracts-py-requires_review_before_promotion]]`(stage) → bool`
- **fn** [[eos_ai-substrate-source_lifecycle_contracts-py-requires_safety_auth_before_ingestion]]`() → bool`
- **fn** [[eos_ai-substrate-source_lifecycle_contracts-py-is_raw_record_immutable]]`() → bool`
- **fn** [[eos_ai-substrate-source_lifecycle_contracts-py-is_interpretation_separate_from_raw]]`() → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
