---
type: codebase-file
path: core/adapter_package_manager/google_workspace_api_contract_mapping.py
module: core.adapter_package_manager.google_workspace_api_contract_mapping
lines: 207
size: 7124
generated: 2026-05-07
---

# core/adapter_package_manager/google_workspace_api_contract_mapping.py

Canonical Contract Mapping for W-GWS-API-001.

Maps Google Docs/Drive API output into CanonicalSourceRecord fields.
Encodes the tab-aware extraction requirements as verifiable constraints.

...

**Lines:** 207 | **Size:** 7,124 bytes

## Contains

- **class** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-ApiContractRequirement]] — 1 methods
- **class** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-W0001ExpectedCoverageContract]] — 1 methods
- **class** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-GoogleWorkspaceApiContractMapping]] — 1 methods
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-build_w_gws_api_001_contract_mapping]]`() → GoogleWorkspaceApiContractMapping`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-api_mapping_requires_include_tabs_content]]`(mapping) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-api_mapping_requires_document_tabs_traversal]]`(mapping) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-api_mapping_requires_child_tabs_recursion]]`(mapping) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-api_mapping_preserves_per_tab_provenance]]`(mapping) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-api_mapping_rejects_first_tab_only]]`(mapping) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_api_contract_mapping-py-build_w0_001_expected_coverage_contract]]`() → W0001ExpectedCoverageContract`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
