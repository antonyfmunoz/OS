---
type: codebase-file
path: eos_ai/substrate/google_docs_tab_extractor.py
module: eos_ai.substrate.google_docs_tab_extractor
lines: 171
size: 4784
generated: 2026-05-07
---

# eos_ai/substrate/google_docs_tab_extractor.py

Google Docs tab-aware content extractor for W0-001R.

Extracts text from ALL tabs in a Google Doc, preserving tab provenance
(tab ID, title, hierarchy depth, parent path).

...

**Lines:** 171 | **Size:** 4,784 bytes

## Depends On

- [[eos_ai-substrate-google_docs_tab_audit-py]]

## Contains

- **class** [[eos_ai-substrate-google_docs_tab_extractor-py-TabExtraction]] — 1 methods
- **class** [[eos_ai-substrate-google_docs_tab_extractor-py-DocTabExtraction]] — 2 methods
- **fn** [[eos_ai-substrate-google_docs_tab_extractor-py-extract_all_tabs]]`(file_id, title, doc_json) → DocTabExtraction`
- **fn** [[eos_ai-substrate-google_docs_tab_extractor-py-_extract_tabs_recursive]]`(tabs_list, parent_path, depth) → list[TabExtraction]`
- **fn** [[eos_ai-substrate-google_docs_tab_extractor-py-compare_first_tab_vs_all]]`(extraction) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.google_docs_tab_audit import extract_text_from_body
```
