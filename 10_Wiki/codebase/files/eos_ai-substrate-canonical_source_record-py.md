---
type: codebase-file
path: eos_ai/substrate/canonical_source_record.py
module: eos_ai.substrate.canonical_source_record
lines: 286
size: 10165
generated: 2026-05-07
---

# eos_ai/substrate/canonical_source_record.py

Canonical source record for Phase 96.0.

Shared output schema used by ALL extraction backends (API, CLI, Computer Use).
Every backend must normalize its output into this format regardless of mechanism.

...

**Lines:** 286 | **Size:** 10,165 bytes

## Depends On

- [[eos_ai-substrate-extraction_backend_contracts-py]]

## Used By

- [[eos_ai-substrate-extraction_parity_comparator-py]]

## Contains

- **class** [[eos_ai-substrate-canonical_source_record-py-TabSourceRecord]] — 1 methods
- **class** [[eos_ai-substrate-canonical_source_record-py-ProvenanceRecord]] — 1 methods
- **class** [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord]] — 8 methods
- **fn** [[eos_ai-substrate-canonical_source_record-py-build_api_source_record]]`(file_id, title, tabs, source_account) → DocumentSourceRecord`
- **fn** [[eos_ai-substrate-canonical_source_record-py-build_cli_source_record]]`(file_id, title, tabs, cli_tool, source_account) → DocumentSourceRecord`
- **fn** [[eos_ai-substrate-canonical_source_record-py-build_cu_source_record]]`(file_id, title, tabs, extraction_method, any_inaccessible, inaccessible_reason) → DocumentSourceRecord`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
```
