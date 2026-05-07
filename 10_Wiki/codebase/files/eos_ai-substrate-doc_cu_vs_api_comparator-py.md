---
type: codebase-file
path: eos_ai/substrate/doc_cu_vs_api_comparator.py
module: eos_ai.substrate.doc_cu_vs_api_comparator
lines: 164
size: 4942
generated: 2026-05-07
---

# eos_ai/substrate/doc_cu_vs_api_comparator.py

Document CU vs API comparator for W0-001R.

Compares text extracted via computer-use (accessibility tree / scrolling)
against the tab-aware API extraction for coverage assessment.

**Lines:** 164 | **Size:** 4,942 bytes

## Contains

- **class** [[eos_ai-substrate-doc_cu_vs_api_comparator-py-DocComparisonResult]] — 1 methods
- **fn** [[eos_ai-substrate-doc_cu_vs_api_comparator-py-normalize_text]]`(text) → str`
- **fn** [[eos_ai-substrate-doc_cu_vs_api_comparator-py-extract_unique_phrases]]`(text, phrase_length) → list[str]`
- **fn** [[eos_ai-substrate-doc_cu_vs_api_comparator-py-compute_phrase_recall]]`(api_text, cu_text, phrase_length, max_phrases) → tuple[int, int]`
- **fn** [[eos_ai-substrate-doc_cu_vs_api_comparator-py-compare_doc_extraction]]`(file_id, title, api_text, api_total_tabs, cu_text, cu_tabs_read) → DocComparisonResult`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
```
