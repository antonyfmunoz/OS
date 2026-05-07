---
type: codebase-file
path: eos_ai/substrate/google_docs_tab_audit.py
module: eos_ai.substrate.google_docs_tab_audit
lines: 180
size: 6078
generated: 2026-05-07
---

# eos_ai/substrate/google_docs_tab_audit.py

Google Docs tab coverage audit for W0-001R.

Audits whether a Google Docs API extraction captured all document tabs
or only the first/default tab. Google Docs supports multiple tabs per
document (introduced 2024), and the default API call without
...

**Lines:** 180 | **Size:** 6,078 bytes

## Used By

- [[eos_ai-substrate-google_docs_tab_extractor-py]]

## Contains

- **class** [[eos_ai-substrate-google_docs_tab_audit-py-TabCoverageStatus]] — 0 methods
- **class** [[eos_ai-substrate-google_docs_tab_audit-py-TabInfo]] — 1 methods
- **class** [[eos_ai-substrate-google_docs_tab_audit-py-DocTabAuditResult]] — 1 methods
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-classify_prior_coverage]]`(total_tabs) → TabCoverageStatus`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-extract_tabs_from_doc_json]]`(doc_json) → list[TabInfo]`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-_process_tabs_recursive]]`(tabs_list, depth) → list[TabInfo]`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-count_body_words]]`(body) → int`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-extract_text_from_body]]`(body) → str`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-build_tab_audit_result]]`(file_id, title, doc_json) → DocTabAuditResult`
- **fn** [[eos_ai-substrate-google_docs_tab_audit-py-compute_audit_summary]]`(results) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
