---
type: codebase-file
path: core/adapter_package_manager/google_docs_cu_package.py
module: core.adapter_package_manager.google_docs_cu_package
lines: 130
size: 4316
generated: 2026-05-07
---

# core/adapter_package_manager/google_docs_cu_package.py

Google Docs Computer Use Adapter Package (W-GDOCS-CU-001).

Visible GUI / Computer Use Google Docs tab-aware navigation and
content extraction path for W0-001.
NOT 100% mature — requires CU infrastructure proof.
...

**Lines:** 130 | **Size:** 4,316 bytes

## Contains

- **class** [[core-adapter_package_manager-google_docs_cu_package-py-GoogleDocsCuPackage]] — 1 methods
- **fn** [[core-adapter_package_manager-google_docs_cu_package-py-build_google_docs_cu_package]]`() → GoogleDocsCuPackage`
- **fn** [[core-adapter_package_manager-google_docs_cu_package-py-docs_cu_is_mature]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_cu_package-py-docs_cu_has_hardening_gaps]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_cu_package-py-docs_cu_blocks_w0_001]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_docs_cu_package-py-docs_cu_requires_api_parity]]`(pkg) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
