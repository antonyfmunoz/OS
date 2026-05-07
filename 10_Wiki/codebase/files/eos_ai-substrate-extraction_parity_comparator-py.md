---
type: codebase-file
path: eos_ai/substrate/extraction_parity_comparator.py
module: eos_ai.substrate.extraction_parity_comparator
lines: 326
size: 11171
generated: 2026-05-07
---

# eos_ai/substrate/extraction_parity_comparator.py

Extraction parity comparator for Phase 96.0.

Compares extraction outputs across backends (API, CLI, Computer Use)
to measure parity: same tabs, same text, same coverage.

...

**Lines:** 326 | **Size:** 11,171 bytes

## Depends On

- [[eos_ai-substrate-canonical_source_record-py]]
- [[eos_ai-substrate-extraction_backend_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-extraction_parity_comparator-py-TabParityResult]] — 1 methods
- **class** [[eos_ai-substrate-extraction_parity_comparator-py-TextParityResult]] — 1 methods
- **class** [[eos_ai-substrate-extraction_parity_comparator-py-ParityReport]] — 1 methods
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-_normalize]]`(text) → str`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compare_tab_coverage]]`(reference, candidate) → TabParityResult`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compare_text_coverage]]`(reference, candidate, threshold) → TextParityResult`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compute_word_recall]]`(reference_text, candidate_text) → float`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compute_tab_recall]]`(reference_tabs, candidate_tabs) → float`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compute_precision]]`(reference_tabs, candidate_tabs) → float`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-identify_missing_tabs]]`(reference, candidate) → list[str]`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-identify_missing_text_sections]]`(reference, candidate) → list[str]`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-compare_document_records]]`(api_record, cu_record) → ParityReport`
- **fn** [[eos_ai-substrate-extraction_parity_comparator-py-build_parity_report]]`(reference_backend, candidate_backend, reference_records, candidate_records) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.canonical_source_record import DocumentSourceRecord
from eos_ai.substrate.canonical_source_record import TabSourceRecord
from eos_ai.substrate.extraction_backend_contracts import ExtractionBackendType
from eos_ai.substrate.extraction_backend_contracts import ExtractionCoverageStatus
```
