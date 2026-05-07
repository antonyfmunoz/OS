---
type: codebase-file
path: core/adapter_package_manager/google_docs_api_package.py
module: core.adapter_package_manager.google_docs_api_package
lines: 153
size: 4930
generated: 2026-05-07
---

# core/adapter_package_manager/google_docs_api_package.py

Google Docs API Adapter Package (W-GDOCS-API-001).

Tab-aware document extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

...

**Lines:** 153 | **Size:** 4,930 bytes

## Contains

- **class** [[core-adapter_package_manager-google_docs_api_package-py-GoogleDocsApiPackage]] — 1 methods
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-build_google_docs_api_package]]`() → GoogleDocsApiPackage`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_requires_include_tabs_content]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_requires_tabs_traversal]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_requires_child_tabs_recursion]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_rejects_first_tab_only]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_has_w0_001_coverage]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_is_read_only]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_api_package-py-docs_api_inherits_from_legacy]]`(pkg) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
