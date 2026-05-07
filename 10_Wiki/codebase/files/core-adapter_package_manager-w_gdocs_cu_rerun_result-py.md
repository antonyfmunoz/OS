---
type: codebase-file
path: core/adapter_package_manager/w_gdocs_cu_rerun_result.py
module: core.adapter_package_manager.w_gdocs_cu_rerun_result
lines: 254
size: 9462
generated: 2026-05-07
---

# core/adapter_package_manager/w_gdocs_cu_rerun_result.py

W-GDOCS-CU-001 Rerun Result Contract.

Defines the result structure for a Docs CU rerun while founder is
present. Evaluates whether the rerun proof closes all 7 gaps and
reaches final 100%.
...

**Lines:** 254 | **Size:** 9,462 bytes

## Contains

- **class** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-WDocsCURerunStatus]] — 0 methods
- **class** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-WDocsCURerunResult]] — 1 methods
- **fn** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-build_w_gdocs_cu_rerun_result]]`(founder_present, founder_confirmed, docs_openable, tabs_detectable, child_tabs_supported, content_extractable, scrolling_complete, per_doc_provenance, per_tab_provenance, empty_tabs_marked, inaccessible_tabs_marked, parity_against_api, actual_docs, actual_tabs, actual_child_tabs, actual_words, method_cu_only, governance_clean) → WDocsCURerunResult`
- **fn** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-evaluate_w_gdocs_cu_rerun_result]]`(result) → WDocsCURerunResult`
- **fn** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-rerun_result_finalizes_docs_cu]]`(result) → bool`
- **fn** [[core-adapter_package_manager-w_gdocs_cu_rerun_result-py-summarize_w_gdocs_cu_rerun_result]]`(result) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
